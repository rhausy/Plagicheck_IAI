import os
import shutil
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session as SessionBDD

from app.database import obtenir_session
from app.models import Document
from app.schemas import DocumentReponse
from app.config import DOSSIER_DOCUMENTS_SOUMISSIONS, DOSSIER_DOCUMENTS_REFERENCE

router = APIRouter(prefix="/documents", tags=["Documents"])

EXTENSIONS_AUTORISEES = (".pdf", ".docx")
TYPES_AUTORISES = ("soumission", "reference", "gabarit")


@router.post("/", response_model=DocumentReponse)
def deposer_document(
    utilisateur_id: int = Form(...),
    titre: str = Form(...),
    fichier: UploadFile = File(...),
    type_document: str = Form("soumission"),
    session: SessionBDD = Depends(obtenir_session),
):
    extension = os.path.splitext(fichier.filename)[1].lower()
    if extension not in EXTENSIONS_AUTORISEES:
        raise HTTPException(status_code=400, detail=f"Format non supporté. Formats acceptés : {EXTENSIONS_AUTORISEES}")

    if type_document not in TYPES_AUTORISES:
        raise HTTPException(status_code=400, detail=f"type_document invalide. Valeurs acceptées : {TYPES_AUTORISES}")

    dossier_cible = DOSSIER_DOCUMENTS_REFERENCE if type_document == "reference" else DOSSIER_DOCUMENTS_SOUMISSIONS
    os.makedirs(dossier_cible, exist_ok=True)

    nom_fichier_disque = f"{utilisateur_id}_{fichier.filename}"
    chemin_disque = os.path.join(dossier_cible, nom_fichier_disque)

    with open(chemin_disque, "wb") as destination:
        shutil.copyfileobj(fichier.file, destination)

    nouveau_document = Document(
        utilisateur_id=utilisateur_id,
        titre=titre,
        chemin_fichier=chemin_disque,
        type_document=type_document,
    )
    session.add(nouveau_document)
    session.commit()
    session.refresh(nouveau_document)

    return nouveau_document


@router.get("/reference", response_model=list[DocumentReponse])
def lister_documents_reference(session: SessionBDD = Depends(obtenir_session)):
    return session.query(Document).filter(Document.type_document == "reference").all()