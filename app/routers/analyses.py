"""
Route de déclenchement d'une analyse (CU3) : relie le document soumis
à l'orchestrateur (extraction, découpage, prétraitement, similarité),
puis enregistre les résultats en base de données.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as SessionBDD

from app.database import obtenir_session
from app.models import Document, Analyse, Correspondance
from app.schemas import AnalyseReponse, AnalyseDetailReponse, AnalyseHistoriqueReponse
from app.services.analyse import OrchestrateurAnalyse
from app.services.extraction import ErreurExtractionTexte

router = APIRouter(prefix="/analyses", tags=["Analyses"])
orchestrateur = OrchestrateurAnalyse()


@router.post("/{document_id}", response_model=AnalyseReponse)
def lancer_analyse(document_id: int, session: SessionBDD = Depends(obtenir_session)):

    document = session.query(Document).filter(Document.id == document_id).first()

    document_gabarit = (
        session.query(Document)
        .filter(Document.type_document == "gabarit")
        .order_by(Document.date_upload.desc())
        .first()
    )
    if document_gabarit:
        texte_gabarit = orchestrateur.extracteur.extraire(document_gabarit.chemin_fichier)
        orchestrateur.neutraliseur.charger_gabarit(texte_gabarit)

    if not document:
        raise HTTPException(status_code=404, detail="Document introuvable.")
        
    documents_reference = [
        {"id": doc.id, "chemin": doc.chemin_fichier}
        for doc in session.query(Document).filter(Document.type_document == "reference").all()
    ]

    documents_meme_etudiant = [
        {"id": doc.id, "chemin": doc.chemin_fichier}
        for doc in session.query(Document)
        .filter(Document.utilisateur_id == document.utilisateur_id, Document.id != document.id)
        .all()
    ]

    analyse = Analyse(document_id=document.id, statut="en_cours")
    session.add(analyse)
    session.commit()
    session.refresh(analyse)

    try:
        resultat = orchestrateur.analyser(
            document.chemin_fichier, documents_reference, documents_meme_etudiant
        )
    except ErreurExtractionTexte as erreur:
        analyse.statut = "echouee"
        session.commit()
        raise HTTPException(status_code=422, detail=str(erreur))

    for nom_section, donnees_section in resultat["sections"].items():
        for correspondance in donnees_section["correspondances"]:
            session.add(Correspondance(
                analyse_id=analyse.id,
                document_reference_id=correspondance["document_reference_id"],
                section=nom_section,
                score_lexical=correspondance["score_lexical"],
                score_semantique=correspondance["score_semantique"],
                score_final=correspondance["score_final"],
                type_comparaison=correspondance["type_comparaison"],
            ))

    analyse.score_global = resultat["score_global"]
    analyse.statut = "terminee"
    session.commit()

    return {
        "analyse_id": analyse.id,
        "score_global": analyse.score_global,
        "statut": analyse.statut,
    }


@router.get("/{analyse_id}", response_model=AnalyseDetailReponse)
def consulter_analyse(analyse_id: int, session: SessionBDD = Depends(obtenir_session)):

    analyse = session.query(Analyse).filter(Analyse.id == analyse_id).first()
    if not analyse:
        raise HTTPException(status_code=404, detail="Analyse introuvable.")

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
def lister_analyses_etudiant(utilisateur_id: int, session: SessionBDD = Depends(obtenir_session)):
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