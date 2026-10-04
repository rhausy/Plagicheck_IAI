"""
Routes d'authentification : inscription publique (étudiant uniquement)
et connexion sécurisée avec session révocable côté serveur.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as SessionBDD

from app.config import DUREE_SESSION_MINUTES, CLE_SECRETE
from app.database import obtenir_session
from app.models import Utilisateur
from app.schemas import InscriptionEntree, ConnexionEntree, UtilisateurReponse, ConnexionReponse
from app.securite import (
    hacher_mot_de_passe, verifier_mot_de_passe,
    creer_jeton_acces, revoquer_session,
    obtenir_utilisateur_courant, limiter_par_ip,
)

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/inscription", response_model=UtilisateurReponse)
def inscription(
    donnees: InscriptionEntree,
    session: SessionBDD = Depends(obtenir_session),
    request: Request = None,
):
    # Protection brute-force sur inscription
    limiter_par_ip("auth_inscription", limite=10, fenetre=300)(request)

    # Vérifier email unique
    existant = session.query(Utilisateur).filter(Utilisateur.email == donnees.email).first()
    if existant:
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé.")

    # RÔLE FORCÉ : inscription publique = étudiant uniquement.
    # Ignorer donnees.role ; il n'existe pas d'élévation de privilège via formulaire.
    nouvel_utilisateur = Utilisateur(
        nom=donnees.nom,
        email=donnees.email,
        mot_de_passe_hash=hacher_mot_de_passe(donnees.mot_de_passe),
        role="etudiant",  # FORCÉ
        est_actif=True,
    )
    session.add(nouvel_utilisateur)
    session.commit()
    session.refresh(nouvel_utilisateur)
    return nouvel_utilisateur


@router.post("/connexion", response_model=ConnexionReponse)
def connexion(
    donnees: ConnexionEntree,
    session: SessionBDD = Depends(obtenir_session),
    request: Request = None,
):
    limiter_par_ip("auth_connexion", limite=5, fenetre=300)(request)

    utilisateur = session.query(Utilisateur).filter(Utilisateur.email == donnees.email).first()
    if not utilisateur or not utilisateur.est_actif:
        # Message générique : ne révèle pas si le compte existe
        raise HTTPException(status_code=401, detail="Identifiants incorrects.")
    if not verifier_mot_de_passe(donnees.mot_de_passe, utilisateur.mot_de_passe_hash):
        raise HTTPException(status_code=401, detail="Identifiants incorrects.")

    # Création du jeton avec jti + session en base (révocation possible)
    adresse_ip = request.client.host if request and request.client else ""
    agent = request.headers.get("user-agent", "") if request else ""
    jeton, exp = creer_jeton_acces(utilisateur.id, session, adresse_ip, agent)

    # Nettoyer anciennes sessions expirées (léger)
    from sqlalchemy import delete
    from datetime import datetime, timezone
    from app import models
    session.execute(
        delete(models.SessionUtilisateur).where(
            models.SessionUtilisateur.utilisateur_id == utilisateur.id,
            models.SessionUtilisateur.date_expiration < datetime.now(timezone.utc).replace(tzinfo=None)
        )
    )

    return {
        "utilisateur": {
            "id": utilisateur.id,
            "nom": utilisateur.nom,
            "email": utilisateur.email,
            "role": utilisateur.role,
        },
        "jeton_acces": jeton,
        "type_jeton": "bearer",
        "duree_minutes": DUREE_SESSION_MINUTES,
    }


@router.get("/moi", response_model=UtilisateurReponse)
def moi(utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant)):
    """
    Retourne le profil de l'utilisateur actuellement connecté.
    Utilisé par le frontend pour vérifier la session au chargement des pages.
    """
    return utilisateur


@router.post("/deconnexion")
def deconnexion(
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant),
    session: SessionBDD = Depends(obtenir_session),
    request: Request = None,
):
    # Récupérer le jeton depuis l'en-tête Authorization
    authorization = (request.headers.get("authorization") if request else "") or ""
    if authorization.startswith("Bearer "):
        jeton_brut = authorization.split(" ", 1)[1]
        try:
            from jose import jwt
            charge = jwt.decode(jeton_brut, CLE_SECRETE, algorithms=["HS256"])
            jti = charge.get("jti")
            if jti:
                from app.securite import _hacher_jti
                revoquer_session(session, _hacher_jti(jti))
        except Exception:
            pass  # Même si le jeton est déjà expiré, la déconnexion est traitée

    return {"message": "Déconnexion réussie"}