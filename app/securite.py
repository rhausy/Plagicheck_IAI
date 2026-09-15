"""
Fonctions de sécurité : hachage des mots de passe et création des jetons
de connexion (utilisées par les routes d'authentification).
"""

from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt

from app.config import CLE_SECRETE, ALGORITHME_JWT, DUREE_SESSION_MINUTES

# Configurer l'algorithme de hachage des mots de passe
contexte_hachage = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Transformer un mot de passe en clair en hachage sécurisé (à l'inscription)
def hacher_mot_de_passe(mot_de_passe: str) -> str:
    return contexte_hachage.hash(mot_de_passe)


# Vérifier qu'un mot de passe saisi correspond au hachage stocké (à la connexion)
def verifier_mot_de_passe(mot_de_passe_clair: str, mot_de_passe_hash: str) -> bool:
    return contexte_hachage.verify(mot_de_passe_clair, mot_de_passe_hash)


# Générer un jeton de connexion valable pour une durée limitée
def creer_jeton_acces(utilisateur_id: int) -> tuple[str, datetime]:
    date_expiration = datetime.utcnow() + timedelta(minutes=DUREE_SESSION_MINUTES)
    donnees = {"sub": str(utilisateur_id), "exp": date_expiration}
    jeton = jwt.encode(donnees, CLE_SECRETE, algorithm=ALGORITHME_JWT)
    return jeton, date_expiration