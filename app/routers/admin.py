"""
Routes réservées à l'administrateur :
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as SessionBDD

from app.database import obtenir_session
from app.models import Utilisateur, Document, Analyse, Configuration
from app.schemas import StatistiquesReponse, UtilisateurAdminReponse, CreationUtilisateurAdmin
from app.securite import hacher_mot_de_passe, exiger_role
from app.config import SEUIL_ALERTE_DEFAUT

router = APIRouter(prefix="/admin", tags=["Administration"])


# Statistiques globales pour le tableau de bord (CU24)
@router.get("/statistiques", response_model=StatistiquesReponse)
def obtenir_statistiques(
    session: SessionBDD = Depends(obtenir_session),
    administrateur: Utilisateur = Depends(exiger_role("administrateur"))
):
    return {
        "total_utilisateurs": session.query(Utilisateur).count(),
        "total_rapports": session.query(Document).count(),
        "total_analyses": session.query(Analyse).count(),
    }


# Liste de tous les comptes utilisateurs (CU14)
@router.get("/utilisateurs", response_model=list[UtilisateurAdminReponse])
def lister_utilisateurs(
    session: SessionBDD = Depends(obtenir_session),
    administrateur: Utilisateur = Depends(exiger_role("administrateur"))
):
    return session.query(Utilisateur).all()


# Créer un compte utilisateur manuellement (CU14)
@router.post("/utilisateurs", response_model=UtilisateurAdminReponse)
def creer_utilisateur(
    donnees: CreationUtilisateurAdmin,
    session: SessionBDD = Depends(obtenir_session),
    administrateur: Utilisateur = Depends(exiger_role("administrateur"))
):

    email_existe = session.query(Utilisateur).filter(Utilisateur.email == donnees.email).first()
    if email_existe:
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé.")

    nouvel_utilisateur = Utilisateur(
        nom=donnees.nom,
        email=donnees.email,
        mot_de_passe_hash=hacher_mot_de_passe(donnees.mot_de_passe),
        role=donnees.role,
        est_actif=True,
    )
    session.add(nouvel_utilisateur)
    session.commit()
    session.refresh(nouvel_utilisateur)

    return nouvel_utilisateur


# Activer ou désactiver un compte (CU14)
@router.put("/utilisateurs/{utilisateur_id}/statut")
def modifier_statut_utilisateur(
    utilisateur_id: int,
    est_actif: bool,
    session: SessionBDD = Depends(obtenir_session),
    administrateur: Utilisateur = Depends(exiger_role("administrateur"))
):
    utilisateur = session.query(Utilisateur).filter(Utilisateur.id == utilisateur_id).first()
    if not utilisateur:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    # Empêcher l'admin de se bloquer lui-même (verrouillage du système)
    if utilisateur.id == administrateur.id and not est_actif:
        raise HTTPException(
            status_code=400,
            detail="Vous ne pouvez pas désactiver votre propre compte administrateur."
        )

    utilisateur.est_actif = est_actif
    session.commit()

    return {"id": utilisateur.id, "est_actif": utilisateur.est_actif}


# Consulter le seuil d'alerte actuellement configuré (CU15)
@router.get("/seuil")
def obtenir_seuil(
    session: SessionBDD = Depends(obtenir_session),
    administrateur: Utilisateur = Depends(exiger_role("administrateur"))
):
    config = session.query(Configuration).filter(Configuration.cle == "seuil_alerte").first()
    return {"seuil": float(config.valeur) if config else SEUIL_ALERTE_DEFAUT}


# Modifier le seuil d'alerte (CU15)
@router.put("/seuil")
def modifier_seuil(
    seuil: float,
    session: SessionBDD = Depends(obtenir_session),
    administrateur: Utilisateur = Depends(exiger_role("administrateur"))
):
    if seuil < 0 or seuil > 100:
        raise HTTPException(status_code=400, detail="Le seuil doit être compris entre 0 et 100.")

    config = session.query(Configuration).filter(Configuration.cle == "seuil_alerte").first()

    if config:
        config.valeur = str(seuil)
    else:
        config = Configuration(cle="seuil_alerte", valeur=str(seuil), description="Seuil d'alerte de similarité")
        session.add(config)

    session.commit()
    return {"seuil": seuil}