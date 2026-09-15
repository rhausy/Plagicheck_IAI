"""
Routes d'authentification : inscription (CU1) et connexion.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as SessionBDD

from app.database import obtenir_session
from app.models import Utilisateur, Session as SessionModele
from app.schemas import InscriptionEntree, ConnexionEntree, UtilisateurReponse, ConnexionReponse
from app.securite import hacher_mot_de_passe, verifier_mot_de_passe, creer_jeton_acces

router = APIRouter(prefix="/auth", tags=["Authentification"])


# Créer un nouveau compte utilisateur
@router.post("/inscription", response_model=UtilisateurReponse)
def inscription(donnees: InscriptionEntree, session: SessionBDD = Depends(obtenir_session)):

    # Vérifier que l'email n'est pas déjà utilisé
    email_existe = session.query(Utilisateur).filter(Utilisateur.email == donnees.email).first()
    if email_existe:
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé.")

    # Créer l'utilisateur avec le mot de passe haché (jamais en clair)
    nouvel_utilisateur = Utilisateur(
        nom=donnees.nom,
        email=donnees.email,
        mot_de_passe_hash=hacher_mot_de_passe(donnees.mot_de_passe),
        role=donnees.role,
    )
    session.add(nouvel_utilisateur)
    session.commit()
    session.refresh(nouvel_utilisateur)

    return nouvel_utilisateur


# Connecter un utilisateur existant et lui fournir un jeton d'accès
@router.post("/connexion", response_model=ConnexionReponse)
def connexion(donnees: ConnexionEntree, session: SessionBDD = Depends(obtenir_session)):

    # Retrouver l'utilisateur par son email
    utilisateur = session.query(Utilisateur).filter(Utilisateur.email == donnees.email).first()
    if not utilisateur or not verifier_mot_de_passe(donnees.mot_de_passe, utilisateur.mot_de_passe_hash):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")

    # Générer et enregistrer le jeton de session
    jeton, date_expiration = creer_jeton_acces(utilisateur.id)
    session.add(SessionModele(
        utilisateur_id=utilisateur.id,
        token=jeton,
        date_expiration=date_expiration,
    ))
    session.commit()

    return {"utilisateur": utilisateur, "jeton_acces": jeton}