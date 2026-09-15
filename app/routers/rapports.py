"""
Routes de génération et téléchargement du rapport PDF (CU10, CU5).
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as SessionBDD

from app.database import obtenir_session
from app.models import Analyse, Correspondance, Rapport, Document
from app.schemas import RapportReponse
from app.services.generateur_rapport import GenerateurRapport

router = APIRouter(prefix="/rapports", tags=["Rapports"])
generateur = GenerateurRapport()


# Générer le PDF d'une analyse déjà terminée
@router.post("/{analyse_id}", response_model=RapportReponse)
def generer_rapport(analyse_id: int, session: SessionBDD = Depends(obtenir_session)):

    analyse = session.query(Analyse).filter(Analyse.id == analyse_id).first()
    if not analyse:
        raise HTTPException(status_code=404, detail="Analyse introuvable.")
    if analyse.statut != "terminee":
        raise HTTPException(status_code=400, detail="L'analyse n'est pas encore terminée.")

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

    chemin_pdf = generateur.generer(
        analyse_id=analyse.id,
        titre_document=document.titre,
        score_global=analyse.score_global,
        correspondances=correspondances_donnees,
    )

    nouveau_rapport = Rapport(analyse_id=analyse.id, chemin_pdf=chemin_pdf)
    session.add(nouveau_rapport)
    session.commit()
    session.refresh(nouveau_rapport)

    return {"rapport_id": nouveau_rapport.id, "chemin_pdf": nouveau_rapport.chemin_pdf}


# Télécharger le PDF déjà généré (CU5)
@router.get("/{rapport_id}/telecharger")
def telecharger_rapport(rapport_id: int, session: SessionBDD = Depends(obtenir_session)):

    rapport = session.query(Rapport).filter(Rapport.id == rapport_id).first()
    if not rapport:
        raise HTTPException(status_code=404, detail="Rapport introuvable.")

    return FileResponse(rapport.chemin_pdf, media_type="application/pdf", filename="rapport_plagicheck.pdf")