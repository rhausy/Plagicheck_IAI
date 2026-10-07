"""
Routes de gestion des notifications utilisateur.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as SessionBDD
from sqlalchemy import func

from app.database import obtenir_session
from app.models import Notification, Utilisateur
from app.schemas import NotificationReponse, NotificationCompteur
from app.securite import obtenir_utilisateur_courant

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def creer_notification(
    session: SessionBDD,
    utilisateur_id: int,
    titre: str,
    message: str,
    type_notif: str = "info",
    lien: str = None
) -> Notification:
    notif = Notification(
        utilisateur_id=utilisateur_id,
        titre=titre,
        message=message,
        type=type_notif,
        lien=lien,
    )
    session.add(notif)
    session.commit()
    session.refresh(notif)
    return notif


@router.get("", response_model=list[NotificationReponse])
def mes_notifications(
    non_lues_only: bool = False,
    limite: int = 50,
    session: SessionBDD = Depends(obtenir_session),
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant),
):
    query = session.query(Notification).filter(
        Notification.utilisateur_id == utilisateur.id
    )

    if non_lues_only:
        query = query.filter(Notification.est_lue == False)

    return query.order_by(Notification.date_creation.desc()).limit(limite).all()


@router.get("/compteur", response_model=NotificationCompteur)
def compteur_notifications(
    session: SessionBDD = Depends(obtenir_session),
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant),
):
    compte = session.query(func.count(Notification.id)).filter(
        Notification.utilisateur_id == utilisateur.id,
        Notification.est_lue == False
    ).scalar()
    return {"non_lues": compte or 0}


@router.put("/{notification_id}/lue")
def marquer_comme_lue(
    notification_id: int,
    session: SessionBDD = Depends(obtenir_session),
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant),
):
    notif = session.query(Notification).filter(
        Notification.id == notification_id,
        Notification.utilisateur_id == utilisateur.id
    ).first()

    if not notif:
        raise HTTPException(status_code=404, detail="Notification introuvable.")

    notif.est_lue = True
    session.commit()
    return {"message": "Marquée comme lue."}


@router.put("/tout-marquer-lues")
def marquer_toutes_lues(
    session: SessionBDD = Depends(obtenir_session),
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant),
):
    session.query(Notification).filter(
        Notification.utilisateur_id == utilisateur.id,
        Notification.est_lue == False
    ).update({Notification.est_lue: True}, synchronize_session=False)
    session.commit()
    return {"message": "Tout est marqué comme lu."}


@router.delete("/{notification_id}")
def supprimer_notification(
    notification_id: int,
    session: SessionBDD = Depends(obtenir_session),
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant),
):
    notif = session.query(Notification).filter(
        Notification.id == notification_id,
        Notification.utilisateur_id == utilisateur.id
    ).first()

    if not notif:
        raise HTTPException(status_code=404, detail="Notification introuvable.")

    session.delete(notif)
    session.commit()
    return {"message": "Supprimée."}