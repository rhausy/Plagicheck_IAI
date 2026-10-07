"""
Schémas Pydantic : validation stricte des entrées et formatage des sorties.
Sécurité :
- extra="forbid" pour rejeter tout champ non déclaré.
- Pas de rôle dans l'inscription publique (anti-élévation de privilèges).
- Pas d'ID utilisateur dans les commentaires (anti-usurpation).
- Pas de chemins internes dans les réponses (anti-fuite d'info).
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
import re


# --- Constantes de validation ---
ROLES_AUTORISES = {"etudiant", "encadrant", "administrateur"}
DECISIONS_AUTORISEES = {"valide", "a_revoir", "suspect_confirme"}


# =====================================================================
# ENTRÉES (Ce que le client envoie)
# =====================================================================

class InscriptionEntree(BaseModel):
    """Inscription publique. Le rôle est FORCÉ à 'etudiant' côté serveur."""
    model_config = ConfigDict(extra="forbid")
    
    nom: str = Field(min_length=2, max_length=100)
    email: EmailStr
    mot_de_passe: str = Field(min_length=12, max_length=128)

    @field_validator("nom")
    @classmethod
    def valider_nom(cls, v: str) -> str:
        if not re.match(r"^[a-zA-ZÀ-ÿ\s'-]+$", v):
            raise ValueError("Nom invalide")
        return v.strip()

    @field_validator("mot_de_passe")
    @classmethod
    def valider_mot_de_passe(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Le mot de passe doit contenir une majuscule")
        if not re.search(r"[0-9]", v):
            raise ValueError("Le mot de passe doit contenir un chiffre")
        return v


class ConnexionEntree(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    mot_de_passe: str = Field(max_length=128)


class CommentaireEntree(BaseModel):
    """
    Décision d'un encadrant.
    L'encadrant_id est injecté par le serveur (via le JWT), pas par le client.
    """
    model_config = ConfigDict(extra="forbid")
    
    contenu: str = Field(min_length=5, max_length=2000)
    decision: str

    @field_validator("decision")
    @classmethod
    def valider_decision(cls, v: str) -> str:
        if v not in DECISIONS_AUTORISEES:
            raise ValueError(f"Décision invalide. Valeurs acceptées : {DECISIONS_AUTORISEES}")
        return v


class CreationUtilisateurAdmin(BaseModel):
    """Création de compte par un administrateur (rôle autorisé)."""
    model_config = ConfigDict(extra="forbid")
    
    nom: str = Field(min_length=2, max_length=100)
    email: EmailStr
    mot_de_passe: str = Field(min_length=12, max_length=128)
    role: str

    @field_validator("role")
    @classmethod
    def valider_role(cls, v: str) -> str:
        if v not in ROLES_AUTORISES:
            raise ValueError(f"Rôle invalide. Valeurs acceptées : {ROLES_AUTORISES}")
        return v.lower()


class MiseAJourSeuil(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seuil: float = Field(ge=0.0, le=100.0)


# =====================================================================
# SORTIES (Ce que l'API renvoie)
# =====================================================================

class UtilisateurReponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nom: str
    email: str
    role: str


class ConnexionReponse(BaseModel):
    utilisateur: UtilisateurReponse
    jeton_acces: str
    type_jeton: str = "bearer"
    duree_minutes: int


class DocumentReponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    titre: str
    type_document: str
    date_upload: datetime
    # On ne renvoie PAS le chemin_fichier (sécurité)


class AnalyseReponse(BaseModel):
    analyse_id: int
    score_global: Optional[float]
    statut: str


class CorrespondanceReponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    document_reference_id: int
    section: str
    score_lexical: float
    score_semantique: float
    score_final: float
    type_comparaison: str


class AnalyseDetailReponse(BaseModel):
    analyse_id: int
    score_global: Optional[float]
    statut: str
    correspondances: List[CorrespondanceReponse]


class StatistiquesReponse(BaseModel):
    total_utilisateurs: int
    total_rapports: int
    total_analyses: int


class UtilisateurAdminReponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nom: str
    email: str
    role: str
    est_actif: bool


class RapportReponse(BaseModel):
    """
    On renvoie une URL de téléchargement, jamais le chemin disque interne.
    """
    rapport_id: int
    url_telechargement: str


class CommentaireReponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    contenu: str
    decision: str
    date_commentaire: datetime


class AnalyseHistoriqueReponse(BaseModel):
    analyse_id: int
    titre_document: str
    score_global: Optional[float]
    statut: str
    date_analyse: datetime

    # =====================================================================
# NOTIFICATIONS
# =====================================================================

class NotificationReponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    titre: str
    message: str
    type: str
    lien: str | None = None
    est_lue: bool
    date_creation: datetime


class NotificationCompteur(BaseModel):
    non_lues: int