"""
Connexion à la base de données SQLite via SQLAlchemy.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import CHEMIN_BASE_DONNEES

moteur = create_engine(
    CHEMIN_BASE_DONNEES,
    connect_args={"check_same_thread": False},  # nécessaire pour SQLite + FastAPI
)

SessionLocale = sessionmaker(autocommit=False, autoflush=False, bind=moteur)

Base = declarative_base()


def obtenir_session():
    """Fournit une session de base de données à chaque requête, et la ferme après."""
    session = SessionLocale()
    try:
        yield session
    finally:
        session.close()