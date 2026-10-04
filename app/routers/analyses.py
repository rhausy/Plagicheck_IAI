"""
Routes de gestion des analyses de similarité.
Sécurité :
- Authentification obligatoire pour toutes les routes.
- Contrôle de propriété strict (un étudiant ne voit/analyse que ses documents).
- Limitation de débit pour protéger le CPU (l'analyse est coûteuse).
- Messages d'erreur génériques pour éviter les fuites d'informations internes.
- Analyse exécutée de manière non bloquante (thread pool).
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as SessionBDD

from app.config import SEUIL_ALERTE_DEFAUT
from app.database import obtenir_session
from app.models import (
    Analyse, Correspondance, Document, 
    ROLE_ENCADRANT, ROLE_ADMINISTRATEUR, ROLE_ETUDIANT, STATUT_ANALYSE_TERMINEE
)
from app.schemas import AnalyseReponse, AnalyseDetailReponse, AnalyseHistoriqueReponse
from app.securite import (
    obtenir_utilisateur_courant, limiter_action
)
from app.services.analyse import OrchestrateurAnalyse
from app.services.extraction import ErreurExtractionTexte

router = APIRouter(prefix="/analyses", tags=["Analyses"])
orchestrateur = OrchestrateurAnalyse()
logger = logging.getLogger("plagicheck.analyses")


def _verifier_propriete_document(utilisateur, document: Document):
    """Vérifie que l'utilisateur a le droit d'analyser ce document."""
    if utilisateur.role == ROLE_ETUDIANT:
        if document.utilisateur_id != utilisateur.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'avez pas accès à ce document."
            )


@router.post("/{document_id}", response_model=AnalyseReponse)
async def lancer_analyse(
    document_id: int,
    request: Request,
    session: SessionBDD = Depends(obtenir_session),
    utilisateur = Depends(obtenir_utilisateur_courant),
):
    # Protection contre le DoS : max 3 analyses par minute par utilisateur
    limiter_action("analyse_lancement", limite=3, fenetre=60)(utilisateur)

    document = session.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable.")

    if document.type_document != "soumission":
        raise HTTPException(status_code=400, detail="Seuls les documents de type 'soumission' peuvent être analysés.")

    # Vérification de propriété
    _verifier_propriete_document(utilisateur, document)

    # Extraction des données AVANT l'exécution asynchrone pour éviter 
    # tout accès ORM concurrent dans le thread pool
    chemin_document = document.chemin_fichier
    utilisateur_id_document = document.utilisateur_id

    # Chargement du gabarit (tolérant aux erreurs pour ne pas bloquer l'analyse)
    texte_gabarit = ""
    try:
        document_gabarit = (
            session.query(Document)
            .filter(Document.type_document == "gabarit")
            .order_by(Document.date_upload.desc())
            .first()
        )
        if document_gabarit:
            texte_gabarit = orchestrateur.extracteur.extraire(document_gabarit.chemin_fichier)
    except Exception as e:
        logger.warning(f"Erreur lors du chargement du gabarit : {e}")

    # Récupération des documents de comparaison (données brutes)
    documents_reference = [
        {"id": doc.id, "chemin": doc.chemin_fichier}
        for doc in session.query(Document).filter(Document.type_document == "reference").all()
    ]

    documents_meme_etudiant = [
        {"id": doc.id, "chemin": doc.chemin_fichier}
        for doc in session.query(Document).filter(
            Document.utilisateur_id == utilisateur_id_document, 
            Document.id != document.id
        ).all()
    ]

    # Création de l'entrée d'analyse
    analyse = Analyse(
        document_id=document.id, 
        statut="en_cours",
        seuil_utilise=SEUIL_ALERTE_DEFAUT,
        declenche_par_id=utilisateur.id
    )
    session.add(analyse)
    session.commit()
    session.refresh(analyse)
    analyse_id = analyse.id  # On garde l'ID en local

    # Exécution de l'orchestrateur dans un thread séparé (non bloquant)
    loop = asyncio.get_event_loop()
    try:
        resultat = await loop.run_in_executor(
            None,
            lambda: orchestrateur.analyser(
                chemin_document, 
                documents_reference, 
                documents_meme_etudiant,
                texte_gabarit=texte_gabarit  # ← Passage du gabarit en paramètre
            )
        )
    except ErreurExtractionTexte:
        analyse.statut = "echouee"
        analyse.message_erreur = "Erreur d'extraction"
        session.commit()
        logger.error(f"Erreur d'extraction pour le document {document_id} par l'utilisateur {utilisateur.id}")
        raise HTTPException(status_code=422, detail="Le document ne peut pas être analysé (format illisible).")
    except Exception as e:
        analyse.statut = "echouee"
        analyse.message_erreur = "Erreur interne"
        session.commit()
        logger.error(f"Erreur inattendue lors de l'analyse {document_id} : {e}")
        raise HTTPException(status_code=500, detail="Erreur interne lors de l'analyse.")

    # Enregistrement des correspondances
    for nom_section, donnees_section in resultat["sections"].items():
        for correspondance in donnees_section["correspondances"]:
            session.add(Correspondance(
                analyse_id=analyse_id,
                document_reference_id=correspondance["document_reference_id"],
                section=nom_section,
                score_lexical=correspondance["score_lexical"],
                score_semantique=correspondance["score_semantique"],
                score_final=correspondance["score_final"],
                type_comparaison=correspondance["type_comparaison"],
            ))

    analyse.score_global = resultat["score_global"]
    analyse.statut = STATUT_ANALYSE_TERMINEE
    session.commit()

    return {
        "analyse_id": analyse.id,
        "score_global": analyse.score_global,
        "statut": analyse.statut,
    }


@router.get("/{analyse_id}", response_model=AnalyseDetailReponse)
def consulter_analyse(
    analyse_id: int,
    session: SessionBDD = Depends(obtenir_session),
    utilisateur = Depends(obtenir_utilisateur_courant),
):
    analyse = session.query(Analyse).filter(Analyse.id == analyse_id).first()
    if not analyse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyse introuvable.")

    # Vérification de propriété sur le document lié à l'analyse
    _verifier_propriete_document(utilisateur, analyse.document)

    correspondances = (
        session.query(Correspondance)
        .filter(Correspondance.analyse_id == analyse_id)
        .all()
    )

    return {
        "analyse_id": analyse.id,
        "score_global": analyse.score_global,
        "statut": analyse.statut,
        "correspondances": correspondances,
    }


@router.get("/etudiant/{utilisateur_id}", response_model=list[AnalyseHistoriqueReponse])
def lister_analyses_etudiant(
    utilisateur_id: int,
    session: SessionBDD = Depends(obtenir_session),
    utilisateur = Depends(obtenir_utilisateur_courant),
):
    # Un étudiant ne peut voir que son propre historique
    if utilisateur.role == ROLE_ETUDIANT and utilisateur.id != utilisateur_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès refusé : vous ne pouvez consulter que votre propre historique."
        )

    analyses = (
        session.query(Analyse)
        .join(Document)
        .filter(Document.utilisateur_id == utilisateur_id)
        .order_by(Analyse.date_analyse.desc())
        .all()
    )

    return [
        {
            "analyse_id": a.id,
            "titre_document": a.document.titre,
            "score_global": a.score_global,
            "statut": a.statut,
            "date_analyse": a.date_analyse,
        }
        for a in analyses
    ]