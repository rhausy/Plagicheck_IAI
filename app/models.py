"""
Modèles SQLAlchemy de PlagiCheck.

Ce fichier définit toutes les tables SQLite et leurs relations :
- utilisateurs et profils par rôle ;
- sessions JWT révocables ;
- documents déposés, références et gabarits ;
- analyses et correspondances ;
- rapports PDF ;
- commentaires des encadrants ;
- configuration ;
- journal d'audit.

Les mots de passe et les jetons ne sont jamais stockés en clair.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


# -------------------------------------------------------------------
# Constantes métier
# -------------------------------------------------------------------

def maintenant_utc() -> datetime:
    """Retourne une date UTC sans information de fuseau pour SQLite."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


ROLE_ETUDIANT = "etudiant"
ROLE_ENCADRANT = "encadrant"
ROLE_ADMINISTRATEUR = "administrateur"

ROLES_VALIDES = (
    ROLE_ETUDIANT,
    ROLE_ENCADRANT,
    ROLE_ADMINISTRATEUR,
)

TYPE_SOUMISSION = "soumission"
TYPE_REFERENCE = "reference"
TYPE_GABARIT = "gabarit"

TYPES_DOCUMENT_VALIDES = (
    TYPE_SOUMISSION,
    TYPE_REFERENCE,
    TYPE_GABARIT,
)

COMPARAISON_REFERENCE_GENERALE = "reference_generale"
COMPARAISON_AUTO_REUTILISATION = "auto_reutilisation"

TYPES_COMPARAISON_VALIDES = (
    COMPARAISON_REFERENCE_GENERALE,
    COMPARAISON_AUTO_REUTILISATION,
)

STATUT_ANALYSE_EN_COURS = "en_cours"
STATUT_ANALYSE_TERMINEE = "terminee"
STATUT_ANALYSE_ECHOUEE = "echouee"

STATUTS_ANALYSE_VALIDES = (
    STATUT_ANALYSE_EN_COURS,
    STATUT_ANALYSE_TERMINEE,
    STATUT_ANALYSE_ECHOUEE,
)

DECISION_VALIDE = "valide"
DECISION_A_REVOIR = "a_revoir"
DECISION_SUSPECT_CONFIRME = "suspect_confirme"

DECISIONS_VALIDES = (
    DECISION_VALIDE,
    DECISION_A_REVOIR,
    DECISION_SUSPECT_CONFIRME,
)


# -------------------------------------------------------------------
# Utilisateurs et profils associés aux rôles
# -------------------------------------------------------------------

class Utilisateur(Base):
    """Compte utilisateur principal."""

    __tablename__ = "utilisateurs"

    __table_args__ = (
        CheckConstraint(
            "role IN ('etudiant', 'encadrant', 'administrateur')",
            name="ck_utilisateurs_role",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    nom = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)

    # Mot de passe bcrypt uniquement, jamais le mot de passe en clair.
    mot_de_passe_hash = Column(String(255), nullable=False)

    role = Column(String(20), nullable=False, default=ROLE_ETUDIANT)
    est_actif = Column(Boolean, nullable=False, default=True)

    date_creation = Column(DateTime, nullable=False, default=maintenant_utc)
    date_modification = Column(
        DateTime,
        nullable=False,
        default=maintenant_utc,
        onupdate=maintenant_utc,
    )

    # Profils spécifiques aux rôles.
    etudiant = relationship(
        "Etudiant",
        back_populates="utilisateur",
        uselist=False,
        cascade="all, delete-orphan",
    )

    encadrant = relationship(
        "Encadrant",
        back_populates="utilisateur",
        uselist=False,
        cascade="all, delete-orphan",
    )

    administrateur = relationship(
        "Administrateur",
        back_populates="utilisateur",
        uselist=False,
        cascade="all, delete-orphan",
    )

    sessions = relationship(
        "SessionUtilisateur",
        back_populates="utilisateur",
        cascade="all, delete-orphan",
    )

    documents = relationship(
        "Document",
        back_populates="utilisateur",
        cascade="all, delete-orphan",
    )

    notifications = relationship(
        "Notification",
        back_populates="utilisateur",
        cascade="all, delete-orphan",
    )


class Etudiant(Base):
    """Informations complémentaires d'un utilisateur étudiant."""

    __tablename__ = "etudiants"

    id = Column(Integer, primary_key=True, index=True)

    utilisateur_id = Column(
        Integer,
        ForeignKey("utilisateurs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    matricule = Column(String(30), nullable=False, unique=True, index=True)
    filiere = Column(String(100), nullable=False, default="")
    niveau = Column(String(20), nullable=False, default="")

    date_creation = Column(DateTime, nullable=False, default=maintenant_utc)

    utilisateur = relationship("Utilisateur", back_populates="etudiant")


class Encadrant(Base):
    """Informations complémentaires d'un encadrant."""

    __tablename__ = "encadrants"

    id = Column(Integer, primary_key=True, index=True)

    utilisateur_id = Column(
        Integer,
        ForeignKey("utilisateurs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    departement = Column(String(100), nullable=False, default="")
    specialite = Column(String(150), nullable=False, default="")

    date_creation = Column(DateTime, nullable=False, default=maintenant_utc)

    utilisateur = relationship("Utilisateur", back_populates="encadrant")


class Administrateur(Base):
    """Informations complémentaires d'un administrateur."""

    __tablename__ = "administrateurs"

    id = Column(Integer, primary_key=True, index=True)

    utilisateur_id = Column(
        Integer,
        ForeignKey("utilisateurs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    fonction = Column(String(100), nullable=False, default="")

    date_creation = Column(DateTime, nullable=False, default=maintenant_utc)

    utilisateur = relationship("Utilisateur", back_populates="administrateur")


# -------------------------------------------------------------------
# Sessions et réinitialisation de mot de passe
# -------------------------------------------------------------------

class SessionUtilisateur(Base):
    """
    Session serveur liée à un JWT.

    jti_hash contient l'empreinte SHA-256 du jti JWT, jamais le jeton brut.
    Cela permet une déconnexion et révocation immédiate côté serveur.
    """

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)

    utilisateur_id = Column(
        Integer,
        ForeignKey("utilisateurs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    jti_hash = Column(String(64), nullable=False, unique=True, index=True)

    date_creation = Column(DateTime, nullable=False, default=maintenant_utc)
    date_expiration = Column(DateTime, nullable=False, index=True)

    est_revoquee = Column(Boolean, nullable=False, default=False)

    adresse_ip = Column(String(45), nullable=True)
    agent_utilisateur = Column(String(255), nullable=True)

    utilisateur = relationship("Utilisateur", back_populates="sessions")


class JetonReinitialisation(Base):
    """
    Jeton de réinitialisation de mot de passe.

    Le jeton réel sera envoyé par email plus tard.
    Seule son empreinte SHA-256 est enregistrée en base.
    """

    __tablename__ = "jetons_reinitialisation"

    id = Column(Integer, primary_key=True, index=True)

    utilisateur_id = Column(
        Integer,
        ForeignKey("utilisateurs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    jeton_hash = Column(String(64), nullable=False, unique=True, index=True)

    date_creation = Column(DateTime, nullable=False, default=maintenant_utc)
    date_expiration = Column(DateTime, nullable=False, index=True)

    utilise = Column(Boolean, nullable=False, default=False)


# -------------------------------------------------------------------
# Configuration de la plateforme
# -------------------------------------------------------------------

class Configuration(Base):
    """Paramètres modifiables par un administrateur."""

    __tablename__ = "configuration"

    id = Column(Integer, primary_key=True, index=True)

    cle = Column(String(100), nullable=False, unique=True, index=True)
    valeur = Column(Text, nullable=False)

    description = Column(String(255), nullable=True)

    modifie_par_id = Column(
        Integer,
        ForeignKey("utilisateurs.id", ondelete="SET NULL"),
        nullable=True,
    )

    date_modification = Column(
        DateTime,
        nullable=False,
        default=maintenant_utc,
        onupdate=maintenant_utc,
    )


# -------------------------------------------------------------------
# Documents
# -------------------------------------------------------------------

class Document(Base):
    """
    Document importé dans PlagiCheck.

    type_document :
    - soumission : rapport d'un étudiant ;
    - reference : ancien document servant à la comparaison ;
    - gabarit : canevas institutionnel à neutraliser.
    """

    __tablename__ = "documents"

    __table_args__ = (
        CheckConstraint(
            "type_document IN ('soumission', 'reference', 'gabarit')",
            name="ck_documents_type_document",
        ),
        Index("ix_documents_utilisateur_type", "utilisateur_id", "type_document"),
    )

    id = Column(Integer, primary_key=True, index=True)

    utilisateur_id = Column(
        Integer,
        ForeignKey("utilisateurs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    titre = Column(String(200), nullable=False)

    # Nom original fourni par le navigateur, jamais utilisé comme chemin disque.
    nom_fichier_original = Column(String(255), nullable=True)

    # Nom généré par le serveur dans data/stockage/.
    chemin_fichier = Column(String(500), nullable=False)

    type_document = Column(String(20), nullable=False, index=True)

    # Ces champs seront remplis par le router documents sécurisé.
    taille_octets = Column(Integer, nullable=True)
    empreinte_sha256 = Column(String(64), nullable=True, index=True)

    date_upload = Column(DateTime, nullable=False, default=maintenant_utc)

    utilisateur = relationship("Utilisateur", back_populates="documents")

    analyses = relationship(
        "Analyse",
        back_populates="document",
        cascade="all, delete-orphan",
    )


# -------------------------------------------------------------------
# Analyses et correspondances
# -------------------------------------------------------------------

class Analyse(Base):
    """Résultat global d'une analyse de similarité d'un document."""

    __tablename__ = "analyses"

    __table_args__ = (
        CheckConstraint(
            "statut IN ('en_cours', 'terminee', 'echouee')",
            name="ck_analyses_statut",
        ),
        Index("ix_analyses_document_statut", "document_id", "statut"),
    )

    id = Column(Integer, primary_key=True, index=True)

    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    score_global = Column(Float, nullable=True)

    statut = Column(
        String(20),
        nullable=False,
        default=STATUT_ANALYSE_EN_COURS,
    )

    seuil_utilise = Column(Float, nullable=False, default=30.0)

    # Message interne limité ; ne pas exposer directement au frontend.
    message_erreur = Column(String(500), nullable=True)

    date_analyse = Column(DateTime, nullable=False, default=maintenant_utc)

    declenche_par_id = Column(
        Integer,
        ForeignKey("utilisateurs.id", ondelete="SET NULL"),
        nullable=True,
    )

    document = relationship("Document", back_populates="analyses")

    correspondances = relationship(
        "Correspondance",
        back_populates="analyse",
        cascade="all, delete-orphan",
    )

    rapport = relationship(
        "Rapport",
        back_populates="analyse",
        uselist=False,
        cascade="all, delete-orphan",
    )

    commentaires = relationship(
        "Commentaire",
        back_populates="analyse",
        cascade="all, delete-orphan",
    )


class Correspondance(Base):
    """
    Similarité entre une section analysée et un document de référence.

    type_comparaison :
    - reference_generale ;
    - auto_reutilisation.
    """

    __tablename__ = "correspondances"

    __table_args__ = (
        CheckConstraint(
            "type_comparaison IN ('reference_generale', 'auto_reutilisation')",
            name="ck_correspondances_type_comparaison",
        ),
        Index(
            "ix_correspondances_analyse_type",
            "analyse_id",
            "type_comparaison",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    analyse_id = Column(
        Integer,
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_reference_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    section = Column(String(50), nullable=False)

    score_lexical = Column(Float, nullable=False, default=0.0)
    score_semantique = Column(Float, nullable=False, default=0.0)
    score_final = Column(Float, nullable=False, default=0.0)

    type_comparaison = Column(String(30), nullable=False)

    # Liste JSON de passages potentiellement similaires.
    passages_json = Column(Text, nullable=False, default="[]")

    analyse = relationship("Analyse", back_populates="correspondances")

    document_reference = relationship(
        "Document",
        foreign_keys=[document_reference_id],
    )


# -------------------------------------------------------------------
# Rapports PDF
# -------------------------------------------------------------------

class Rapport(Base):
    """Rapport PDF généré à partir d'une analyse terminée."""

    __tablename__ = "rapports"

    id = Column(Integer, primary_key=True, index=True)

    # Une analyse ne doit produire qu'un seul rapport PDF actif.
    analyse_id = Column(
        Integer,
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    chemin_pdf = Column(String(500), nullable=False)

    date_generation = Column(DateTime, nullable=False, default=maintenant_utc)

    analyse = relationship("Analyse", back_populates="rapport")


# -------------------------------------------------------------------
# Commentaires et décisions des encadrants
# -------------------------------------------------------------------

class Commentaire(Base):
    """
    Décision prise par un encadrant.

    encadrant_id est obligatoirement défini côté serveur à partir de la
    session authentifiée ; le frontend ne doit jamais pouvoir le choisir.
    """

    __tablename__ = "commentaires"

    __table_args__ = (
        CheckConstraint(
            "decision IN ('valide', 'a_revoir', 'suspect_confirme')",
            name="ck_commentaires_decision",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    analyse_id = Column(
        Integer,
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    encadrant_id = Column(
        Integer,
        ForeignKey("utilisateurs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    contenu = Column(Text, nullable=False)
    decision = Column(String(30), nullable=False)

    date_commentaire = Column(DateTime, nullable=False, default=maintenant_utc)

    analyse = relationship("Analyse", back_populates="commentaires")


# -------------------------------------------------------------------
# Journal d'audit et événements de sécurité
# -------------------------------------------------------------------

class JournalAudit(Base):
    """
    Journal des opérations sensibles.

    Ne jamais y stocker :
    - mots de passe ;
    - JWT ;
    - cookies ;
    - clés secrètes ;
    - informations de connexion sensibles.
    """

    __tablename__ = "journal_audit"

    id = Column(Integer, primary_key=True, index=True)

    horodatage = Column(
        DateTime,
        nullable=False,
        default=maintenant_utc,
        index=True,
    )

    utilisateur_id = Column(
        Integer,
        ForeignKey("utilisateurs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    action = Column(String(100), nullable=False, index=True)
    resultat = Column(String(20), nullable=False)
    niveau = Column(String(10), nullable=False, default="INFO")

    adresse_ip = Column(String(45), nullable=True)

    # Données non sensibles uniquement, par exemple JSON sérialisé.
    details = Column(Text, nullable=True)


class Notification(Base):
    """
    Notifications envoyées aux utilisateurs.
    Peut être liée à une analyse, un document, ou être globale.
    """

    __tablename__ = "notifications"

    __table_args__ = (
        Index("ix_notifications_utilisateur_lue", "utilisateur_id", "est_lue"),
    )

    id = Column(Integer, primary_key=True, index=True)

    utilisateur_id = Column(
        Integer,
        ForeignKey("utilisateurs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    titre = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(20), nullable=False, default="info")  # info, success, warning, error

    # Lien optionnel vers l'objet concerné (ex: /analyses/12)
    lien = Column(String(500), nullable=True)

    est_lue = Column(Boolean, nullable=False, default=False)

    date_creation = Column(DateTime, nullable=False, default=maintenant_utc, index=True)

    # Relation vers l'utilisateur
    utilisateur = relationship("Utilisateur", back_populates="notifications")