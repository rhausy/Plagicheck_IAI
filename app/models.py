"""
Modèles SQLAlchemy — traduction directe du schéma de base de données
qu'on a conçu dans le dossier d'analyse (utilisateurs spécialisés par
rôle, documents, analyses, correspondances par section, rapports...).
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    mot_de_passe_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # "etudiant" | "encadrant" | "administrateur"
    est_actif = Column(Boolean, default=True)
    date_creation = Column(DateTime, default=datetime.utcnow)

    documents = relationship("Document", back_populates="proprietaire")
    sessions = relationship("Session", back_populates="utilisateur")
    commentaires = relationship("Commentaire", back_populates="encadrant")

class Etudiant(Base):
    """Attributs spécifiques à un étudiant, reliés à Utilisateur."""
    __tablename__ = "etudiants"

    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"), primary_key=True)
    matricule = Column(String(50), unique=True, nullable=False)
    filiere = Column(String(100))
    niveau = Column(String(20))


class Encadrant(Base):
    """Attributs spécifiques à un encadrant, reliés à Utilisateur."""
    __tablename__ = "encadrants"

    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"), primary_key=True)
    departement = Column(String(100))
    titre_academique = Column(String(100))


class Administrateur(Base):
    """Attributs spécifiques à un administrateur, reliés à Utilisateur."""
    __tablename__ = "administrateurs"

    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"), primary_key=True)
    niveau_acces = Column(String(50))


class Document(Base):
    """Un fichier déposé : soumission d'étudiant, référence, ou gabarit officiel."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=False)
    titre = Column(String(255), nullable=False)
    chemin_fichier = Column(String(500), nullable=False)
    type_document = Column(String(20), nullable=False, default="soumission")  # soumission | reference | gabarit
    date_upload = Column(DateTime, default=datetime.utcnow)

    proprietaire = relationship("Utilisateur", back_populates="documents")
    analyse = relationship("Analyse", back_populates="document", uselist=False)


class Analyse(Base):
    """Une analyse lancée sur un document (résultat global)."""
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    score_global = Column(Float, nullable=True)
    statut = Column(String(20), default="en_cours")  # en_cours | terminee | echouee
    date_analyse = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="analyse")
    correspondances = relationship("Correspondance", back_populates="analyse")
    rapport = relationship("Rapport", back_populates="analyse", uselist=False)
    commentaires = relationship("Commentaire", back_populates="analyse")


class Correspondance(Base):
    """Résultat détaillé d'une comparaison, pour UNE section, avec UN document."""
    __tablename__ = "correspondances"

    id = Column(Integer, primary_key=True, index=True)
    analyse_id = Column(Integer, ForeignKey("analyses.id"), nullable=False)
    document_reference_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    section = Column(String(50), nullable=False)  # "Existant" | "Cahier de Charge" | "Analyse" | ...
    score_lexical = Column(Float, nullable=False)
    score_semantique = Column(Float, nullable=False)
    score_final = Column(Float, nullable=False)
    type_comparaison = Column(String(30), nullable=False, default="reference_generale")  # ou "auto_reutilisation"
    passages_json = Column(Text, nullable=True)

    analyse = relationship("Analyse", back_populates="correspondances")


class Rapport(Base):
    """Le PDF généré à la fin d'une analyse."""
    __tablename__ = "rapports"

    id = Column(Integer, primary_key=True, index=True)
    analyse_id = Column(Integer, ForeignKey("analyses.id"), nullable=False)
    chemin_pdf = Column(String(500), nullable=False)
    date_generation = Column(DateTime, default=datetime.utcnow)

    analyse = relationship("Analyse", back_populates="rapport")


class Commentaire(Base):
    """Décision ou remarque laissée par un encadrant sur une analyse."""
    __tablename__ = "commentaires"

    id = Column(Integer, primary_key=True, index=True)
    analyse_id = Column(Integer, ForeignKey("analyses.id"), nullable=False)
    encadrant_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=False)
    contenu = Column(Text)
    decision = Column(String(30))  # "valide" | "a_revoir" | "suspect_confirme"
    date_commentaire = Column(DateTime, default=datetime.utcnow)

    analyse = relationship("Analyse", back_populates="commentaires")
    encadrant = relationship("Utilisateur", back_populates="commentaires")


class Configuration(Base):
    """Paramètres système modifiables par l'administrateur (seuils, échéances)."""
    __tablename__ = "configuration"

    id = Column(Integer, primary_key=True, index=True)
    cle = Column(String(100), unique=True, nullable=False)
    valeur = Column(String(255), nullable=False)
    description = Column(String(255))
    modifie_par_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=True)
    date_modification = Column(DateTime, default=datetime.utcnow)


class Session(Base):
    """Jeton d'authentification actif pour un utilisateur connecté."""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=False)
    token = Column(String(500), unique=True, nullable=False)
    date_creation = Column(DateTime, default=datetime.utcnow)
    date_expiration = Column(DateTime, nullable=False)

    utilisateur = relationship("Utilisateur", back_populates="sessions")