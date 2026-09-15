"""
Routes de commentaire/décision de l'encadrant sur une analyse (CU12).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as SessionBDD

from app.database import obtenir_session
from app.models import Analyse, Commentaire
from app.schemas import CommentaireEntree, CommentaireReponse

router = APIRouter(prefix="/commentaires", tags=["Commentaires"])


# Ajouter un commentaire/décision sur une analyse
@router.post("/{analyse_id}", response_model=CommentaireReponse)
def ajouter_commentaire(
    analyse_id: int, donnees: CommentaireEntree, session: SessionBDD = Depends(obtenir_session)
):
    analyse = session.query(Analyse).filter(Analyse.id == analyse_id).first()
    if not analyse:
        raise HTTPException(status_code=404, detail="Analyse introuvable.")

    nouveau_commentaire = Commentaire(
        analyse_id=analyse_id,
        encadrant_id=donnees.encadrant_id,
        contenu=donnees.contenu,
        decision=donnees.decision,
    )
    session.add(nouveau_commentaire)
    session.commit()
    session.refresh(nouveau_commentaire)

    return nouveau_commentaire


# Consulter tous les commentaires d'une analyse
@router.get("/{analyse_id}", response_model=list[CommentaireReponse])
def lister_commentaires(analyse_id: int, session: SessionBDD = Depends(obtenir_session)):
    return session.query(Commentaire).filter(Commentaire.analyse_id == analyse_id).all()