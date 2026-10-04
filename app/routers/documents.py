"""
Routes de gestion des documents (dépôt et liste).
Sécurité :
- L'ID utilisateur est extrait du JWT (jamais du client).
- Les rôles "reference" et "gabarit" sont réservés aux administrateurs.
- Le nom de fichier sur le disque est généré aléatoirement (anti-traversée).
- La taille et l'extension sont strictement contrôlées.
- Détection des doublons par empreinte SHA-256.
"""

import os
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session as SessionBDD

from app.config import (
    DOSSIER_DOCUMENTS_REFERENCE, 
    DOSSIER_DOCUMENTS_SOUMISSIONS,
    DOSSIER_DATA
)
from app.database import obtenir_session
from app.models import Document, ROLE_ADMINISTRATEUR
from app.schemas import DocumentReponse
from app.securite import (
    obtenir_utilisateur_courant, 
    valider_extension, 
    nom_fichier_securise,
    verifier_entete_fichier,
    empreinte_fichier_sha256
)

router = APIRouter(prefix="/documents", tags=["Documents"])

# Limite stricte : 20 Mo maximum par document
TAILLE_MAX_FICHIER = 20 * 1024 * 1024 
EXTENSIONS_AUTORISEES = {".pdf", ".docx"}
TYPES_DOCUMENT = {"soumission", "reference", "gabarit"}


@router.post("/", response_model=DocumentReponse)
def deposer_document(
    titre: str = Form(..., min_length=3, max_length=200),
    type_document: str = Form("soumission"),
    fichier: UploadFile = File(...),
    session: SessionBDD = Depends(obtenir_session),
    utilisateur = Depends(obtenir_utilisateur_courant),
):
    """
    Dépose un document. 
    L'utilisateur est identifié par son jeton JWT (impossible d'usurper un ID).
    """
    # 1. Contrôle des rôles : seuls les admins peuvent uploader des références/gabarits
    if type_document in ("reference", "gabarit") and utilisateur.role != ROLE_ADMINISTRATEUR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Seuls les administrateurs peuvent déposer des documents de référence ou des gabarits."
        )

    if type_document not in TYPES_DOCUMENT:
        raise HTTPException(status_code=400, detail="Type de document invalide.")

    # 2. Validation de l'extension (anti-exécution de code malveillant)
    extension = valider_extension(fichier.filename)

    # 3. Génération d'un nom de fichier aléatoire et sûr (anti-traversée de répertoire)
    nom_fichier_disque = nom_fichier_securise("doc", extension)
    
    # Choix du dossier cible
    if type_document == "reference":
        dossier_cible = Path(DOSSIER_DOCUMENTS_REFERENCE)
    else:
        dossier_cible = Path(DOSSIER_DOCUMENTS_SOUMISSIONS)
        
    dossier_cible.mkdir(parents=True, exist_ok=True)
    chemin_complet = dossier_cible / nom_fichier_disque

    # 4. Lecture sécurisée du fichier avec limite de taille (anti-DoS)
    taille_totale = 0
    with open(chemin_complet, "wb") as buffer:
        while True:
            chunk = fichier.file.read(1024 * 1024) # Lit par blocs de 1 Mo
            if not chunk:
                break
            taille_totale += len(chunk)
            if taille_totale > TAILLE_MAX_FICHIER:
                buffer.close()
                chemin_complet.unlink(missing_ok=True) # Supprime le fichier partiel
                raise HTTPException(
                    status_code=413, 
                    detail=f"Fichier trop volumineux. Maximum {TAILLE_MAX_FICHIER // (1024*1024)} Mo."
                )
            buffer.write(chunk)

    # 5. Vérification de la signature binaire (le fichier est-il vraiment un PDF/DOCX ?)
    if not verifier_entete_fichier(chemin_complet):
        chemin_complet.unlink(missing_ok=True)
        raise HTTPException(
            status_code=422, 
            detail="Le contenu du fichier ne correspond pas à un PDF ou un DOCX valide."
        )

    # 6. Calcul de l'empreinte SHA-256
    empreinte = empreinte_fichier_sha256(chemin_complet)

    # 7. Détection des doublons : si ce même contenu a déjà été déposé par cet utilisateur
    doublon = session.query(Document).filter(
        Document.empreinte_sha256 == empreinte,
        Document.utilisateur_id == utilisateur.id
    ).first()

    if doublon:
        # On supprime le fichier qu'on vient d'écrire puisqu'il est identique
        chemin_complet.unlink(missing_ok=True)
        raise HTTPException(
            status_code=409,
            detail=f"Document déjà déposé sous le titre '{doublon.titre}'."
        )

    # 8. Enregistrement en base de données
    nouveau_document = Document(
        utilisateur_id=utilisateur.id, # ID sécurisé depuis le JWT
        titre=titre.strip(),
        nom_fichier_original=fichier.filename, # Gardé pour l'affichage uniquement
        chemin_fichier=str(chemin_complet),
        type_document=type_document,
        taille_octets=taille_totale,
        empreinte_sha256=empreinte,
    )
    
    session.add(nouveau_document)
    session.commit()
    session.refresh(nouveau_document)

    return nouveau_document


@router.get("/reference", response_model=list[DocumentReponse])
def lister_documents_reference(
    session: SessionBDD = Depends(obtenir_session),
    utilisateur = Depends(obtenir_utilisateur_courant),
):
    """
    Liste les documents de référence.
    Nécessite une authentification (étudiant, encadrant ou admin).
    """
    return session.query(Document).filter(Document.type_document == "reference").all()