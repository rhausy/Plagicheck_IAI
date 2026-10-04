"""
Routes de génération et téléchargement du rapport PDF.
Sécurité :
- Authentification obligatoire.
- Contrôle de propriété (un étudiant ne peut télécharger que son propre rapport).
- Limitation de débit (la génération PDF est coûteuse).
- Ne renvoie jamais le chemin disque interne au client.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as SessionBDD

from app.config import DOSSIER_RAPPORTS_GENERES
from app.database import obtenir_session
from app.models import (
    Analyse, Correspondance, Document, Rapport,
    ROLE_ENCADRANT, ROLE_ADMINISTRATEUR, ROLE_ETUDIANT, STATUT_ANALYSE_TERMINEE
)
from app.schemas import RapportReponse
from app.securite import obtenir_utilisateur_courant, limiter_action
from app.services.generateur_rapport import GenerateurRapport

router = APIRouter(prefix="/rapports", tags=["Rapports"])
generateur = GenerateurRapport()


def _verifier_acces_rapport(utilisateur, analyse: Analyse):
    """Vérifie que l'utilisateur a le droit de générer/télécharger ce rapport."""
    document = analyse.document
    if utilisateur.role == ROLE_ETUDIANT:
        if document.utilisateur_id != utilisateur.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'avez pas accès à ce rapport."
            )
    # Encadrants et administrateurs peuvent accéder à tous les rapports


@router.post("/{analyse_id}", response_model=RapportReponse)
def generer_rapport(
    analyse_id: int,
    session: SessionBDD = Depends(obtenir_session),
    utilisateur = Depends(obtenir_utilisateur_courant),
):
    # Protection DoS : max 5 générations de rapport par minute
    limiter_action("rapport_generation", limite=5, fenetre=60)(utilisateur)

    analyse = session.query(Analyse).filter(Analyse.id == analyse_id).first()
    if not analyse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyse introuvable.")
    if analyse.statut != STATUT_ANALYSE_TERMINEE:
        raise HTTPException(status_code=400, detail="L'analyse n'est pas encore terminée.")

    # Contrôle de propriété
    _verifier_acces_rapport(utilisateur, analyse)

    # Vérifier si un rapport existe déjà (on ne régénère pas inutilement)
    rapport_existant = session.query(Rapport).filter(Rapport.analyse_id == analyse_id).first()
    if rapport_existant:
        return {
            "rapport_id": rapport_existant.id,
            "url_telechargement": f"/rapports/{rapport_existant.id}/telecharger"
        }

    document = session.query(Document).filter(Document.id == analyse.document_id).first()
    correspondances = session.query(Correspondance).filter(Correspondance.analyse_id == analyse_id).all()

    correspondances_donnees = [
        {
            "section": c.section,
            "type_comparaison": c.type_comparaison,
            "score_lexical": c.score_lexical,
            "score_semantique": c.score_semantique,
            "score_final": c.score_final,
        }
        for c in correspondances
    ]

    # Génération du PDF dans le dossier sécurisé
    chemin_pdf = generateur.generer(
        analyse_id=analyse.id,
        titre_document=document.titre,
        score_global=analyse.score_global,
        correspondances=correspondances_donnees,
    )

    # Vérification de sécurité : le PDF doit bien être dans le dossier autorisé
    chemin_pdf_path = Path(chemin_pdf).resolve()
    dossier_autorise = Path(DOSSIER_RAPPORTS_GENERES).resolve()
    if not str(chemin_pdf_path).startswith(str(dossier_autorise)):
        raise HTTPException(status_code=500, detail="Chemin de rapport invalide.")

    nouveau_rapport = Rapport(analyse_id=analyse.id, chemin_pdf=str(chemin_pdf_path))
    session.add(nouveau_rapport)
    session.commit()
    session.refresh(nouveau_rapport)

    # On renvoie une URL de téléchargement, jamais le chemin disque
    return {
        "rapport_id": nouveau_rapport.id,
        "url_telechargement": f"/rapports/{nouveau_rapport.id}/telecharger"
    }


@router.get("/{rapport_id}/telecharger")
def telecharger_rapport(
    rapport_id: int,
    session: SessionBDD = Depends(obtenir_session),
    utilisateur = Depends(obtenir_utilisateur_courant),
):
    rapport = session.query(Rapport).filter(Rapport.id == rapport_id).first()
    if not rapport:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rapport introuvable.")

    # Contrôle de propriété via l'analyse liée
    analyse = session.query(Analyse).filter(Analyse.id == rapport.analyse_id).first()
    if not analyse:
        raise HTTPException(status_code=404, detail="Analyse liée introuvable.")
    _verifier_acces_rapport(utilisateur, analyse)

    # Vérification que le fichier existe physiquement
    chemin = Path(rapport.chemin_pdf)
    if not chemin.exists():
        raise HTTPException(status_code=404, detail="Fichier PDF introuvable sur le serveur.")

    return FileResponse(
        str(chemin),
        media_type="application/pdf",
        filename=f"rapport_plagicheck_{rapport.id}.pdf"
    )