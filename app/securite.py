"""
Sécurité applicative : hachage, sessions révocables (JWT + table sessions),
autorisation par rôle, limitation de débit, validation des fichiers.
Aucun secret n'est jamais journalisé.
"""

import hashlib
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app import models
from app.config import CLE_SECRETE, ALGORITHME_JWT, DUREE_SESSION_MINUTES, DOSSIER_DATA
from app.database import obtenir_session

# ---------- Hachage ----------

contexte_hachage = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hacher_mot_de_passe(mot_de_passe: str) -> str:
    return contexte_hachage.hash(mot_de_passe)

def verifier_mot_de_passe(mot_de_passe: str, empreinte: str) -> bool:
    try:
        return contexte_hachage.verify(mot_de_passe, empreinte)
    except Exception:
        return False


# ---------- JWT + Sessions révocables ----------

def _hacher_jti(jti: str) -> str:
    return hashlib.sha256(jti.encode("utf-8")).hexdigest()

def _maintenant_utc_naif() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

def creer_jeton_acces(utilisateur_id: int, db: Session, adresse_ip: str = "", agent: str = "") -> tuple[str, datetime]:
    jti = secrets.token_urlsafe(32)
    expiration = _maintenant_utc_naif() + timedelta(minutes=DUREE_SESSION_MINUTES)

    # Stockage du hash du jti (jamais le jeton brut) pour permettre la révocation
    session_ligne = models.SessionUtilisateur(
        utilisateur_id=utilisateur_id,
        jti_hash=_hacher_jti(jti),
        date_expiration=expiration,
        adresse_ip=adresse_ip[:45] or None,
        agent_utilisateur=agent[:255] or None,
    )
    db.add(session_ligne)
    db.commit()

    maintenant = int(time.time())
    charge = {
        "sub": str(utilisateur_id),
        "jti": jti,
        "iat": maintenant,
        "exp": maintenant + (DUREE_SESSION_MINUTES * 60),
    }
    jeton = jwt.encode(charge, CLE_SECRETE, algorithm=ALGORITHME_JWT)
    return jeton, expiration

def revoquer_session(db: Session, jti_hash: str) -> None:
    session_obj = db.query(models.SessionUtilisateur).filter(
        models.SessionUtilisateur.jti_hash == jti_hash
    ).first()
    if session_obj:
        session_obj.est_revoquee = True
        db.commit()

def obtenir_utilisateur_courant(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(obtenir_session),
    request: Request = None,
) -> models.Utilisateur:
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentification requise")

    try:
        charge = jwt.decode(credentials.credentials, CLE_SECRETE, algorithms=[ALGORITHME_JWT])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide ou expirée")

    jti = charge.get("jti")
    sous = charge.get("sub")
    if not jti or not sous:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide")

    session_obj = db.query(models.SessionUtilisateur).filter(
        models.SessionUtilisateur.jti_hash == _hacher_jti(jti)
    ).first()

    maintenant = _maintenant_utc_naif()
    if session_obj is None or session_obj.est_revoquee or session_obj.date_expiration < maintenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide ou expirée")

    try:
        utilisateur_id = int(sous)
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide")

    utilisateur = db.get(models.Utilisateur, utilisateur_id)
    if utilisateur is None or not utilisateur.est_actif:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Compte indisponible")

    # Rotation douce : prolonger si proche de l'expiration
    reste = (session_obj.date_expiration - maintenant).total_seconds()
    if reste < (DUREE_SESSION_MINUTES * 60) / 2:
        session_obj.date_expiration = maintenant + timedelta(minutes=DUREE_SESSION_MINUTES)
        db.commit()

    return utilisateur

def exiger_role(*roles_autorises: str):
    def dependance(utilisateur: models.Utilisateur = Depends(obtenir_utilisateur_courant)):
        if utilisateur.role not in roles_autorises:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")
        return utilisateur
    return dependance


# ---------- Limitation de débit ----------

class LimiteurDebit:
    def __init__(self):
        self.verrou = threading.Lock()
        self.historique: dict[str, deque] = defaultdict(deque)

    def autoriser(self, cle: str, limite: int, fenetre_secondes: int) -> bool:
        maintenant = time.monotonic()
        with self.verrou:
            fenetre = self.historique[cle]
            while fenetre and maintenant - fenetre[0] > fenetre_secondes:
                fenetre.popleft()
            if len(fenetre) >= limite:
                return False
            fenetre.append(maintenant)
            # Garde-fou mémoire
            if len(self.historique) > 50000:
                self.historique.clear()
            return True

limiteur_global = LimiteurDebit()

def limiter_par_ip(action: str, limite: int = 60, fenetre: int = 60):
    """Limite par adresse IP (pour les routes publiques comme /connexion)."""
    def dependance(request: Request):
        cle = f"{action}:ip:{request.client.host if request.client else 'inconnu'}"
        if not limiteur_global.autoriser(cle, limite, fenetre):
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Trop de requêtes")
        return True
    return dependance

def limiter_action(action: str, limite: int = 60, fenetre: int = 60):
    """
    Retourne une fonction de vérification pour un utilisateur connecté.
    Utilisation dans les routers : limiter_action("nom_action", 3, 60)(utilisateur)
    """
    def _verifier(utilisateur):
        cle = f"{action}:user:{utilisateur.id}"
        if not limiteur_global.autoriser(cle, limite, fenetre):
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Trop de requêtes pour cette action")
        return True
    return _verifier


# ---------- Sécurité des fichiers ----------

EXTENSIONS_AUTORISEES = {".pdf", ".docx"}

def valider_extension(nom_fichier: str) -> str:
    extension = Path(nom_fichier).suffix.lower()
    if extension not in EXTENSIONS_AUTORISEES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Seuls PDF et DOCX acceptés")
    return extension

def nom_fichier_securise(prefixe: str, extension: str) -> str:
    return f"{prefixe}_{secrets.token_hex(16)}{extension}"

def verifier_entete_fichier(chemin: Path) -> bool:
    try:
        with open(chemin, "rb") as f:
            entete = f.read(8)
        return entete.startswith(b"%PDF-") or entete.startswith(b"PK\x03\x04")
    except Exception:
        return False

def empreinte_fichier_sha256(chemin: Path) -> str:
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloc)
    return h.hexdigest()