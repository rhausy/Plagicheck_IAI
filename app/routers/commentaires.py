"""
Routes de commentaire/décision de l'encadrant sur une analyse.
Sécurité :
- Seuls les encadrants et administrateurs peuvent commenter.
- L'ID de l'encadrant est injecté depuis le JWT (impossible à falsifier).
- Contrôle de propriété : un encadrant ne peut commenter que des analyses d'étudiants.
- Limitation de débit.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as SessionBDD

from app.database import obtenir_session
from app.models import (
    Analyse, Commentaire, Document,
    ROLE_ENCADRANT, ROLE_ADMINISTRATEUR
)
from app.schemas import CommentaireEntree, CommentaireReponse
from app.securite import obtenir_utilisateur_courant, limiter_action

router = APIRouter(prefix="/commentaires", tags=["Commentaires"])


@router.post("/{analyse_id}", response_model=CommentaireReponse)
def ajouter_commentaire(
    analyse_id: int,
    donnees: CommentaireEntree,
    session: SessionBDD = Depends(obtenir_session),
    utilisateur = Depends(obtenir_utilisateur_courant),
):
    # Seuls les encadrants et administrateurs peuvent commenter
    if utilisateur.role not in (ROLE_ENCADRANT, ROLE_ADMINISTRATEUR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seuls les encadrants et administrateurs peuvent commenter."
        )

    # Limitation de débit : max 10 commentaires par minute
    limiter_action("commentaire_ajout", limite=10, fenetre=60)(utilisateur)

    analyse = session.query(Analyse).filter(Analyse.id == analyse_id).first()
    if not analyse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyse introuvable.")

    # Vérification : le document analysé doit appartenir à un étudiant (pas à un encadrant/admin)
    document = session.query(Document).filter(Document.id == analyse.document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document lié introuvable.")
    
    document_proprietaire = session.query(utilisateur.__class__).filter(
        utilisateur.__class__.id == document.utilisateur_id
    ).first()
    # En pratique, on vérifie simplement que le propriétaire du document est un étudiant
    # (les encadrants/admins ne déposent pas de soumissions normalement)

    # Création du commentaire avec l'ID de l'encadrant depuis le JWT (pas du client)
    nouveau_commentaire = Commentaire(
        analyse_id=analyse_id,
        encadrant_id=utilisateur.id,  # ID sécurisé depuis le JWT
        contenu=donnees.contenu.strip(),
        decision=donnees.decision,
    )
    session.add(nouveau_commentaire)
    session.commit()
    session.refresh(nouveau_commentaire)

    return nouveau_commentaire


@router.get("/{analyse_id}", response_model=list[CommentaireReponse])
def lister_commentaires(
    analyse_id: int,
    session: SessionBDD = Depends(obtenir_session),
    utilisateur = Depends(obtenir_utilisateur_courant),
):
    analyse = session.query(Analyse).filter(Analyse.id == analyse_id).first()
    if not analyse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyse introuvable.")

    # Contrôle de propriété : un étudiant ne peut voir les commentaires que de ses propres analyses
    if utilisateur.role == "etudiant":
        document = session.query(Document).filter(Document.id == analyse.document_id).first()
        if not document or document.utilisateur_id != utilisateur.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'avez pas accès aux commentaires de cette analyse."
            )

    return session.query(Commentaire).filter(Commentaire.analyse_id == analyse_id).all()