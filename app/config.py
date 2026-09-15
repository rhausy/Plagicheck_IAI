"""
Configuration centrale de PlagiCheck.
Toutes les valeurs modifiables (seuils, chemins, clé secrète) sont
regroupées ici plutôt que dispersées dans le code.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Base de données
CHEMIN_BASE_DONNEES = os.getenv("CHEMIN_BASE_DONNEES", "sqlite:///./plagicheck.db")

# Sécurité
CLE_SECRETE = os.getenv("CLE_SECRETE", "change-moi-avant-la-mise-en-production")
ALGORITHME_JWT = "HS256"
DUREE_SESSION_MINUTES = 60 * 24  # 24h

# Stockage des fichiers
DOSSIER_DOCUMENTS_REFERENCE = "data/stockage/reference"
DOSSIER_DOCUMENTS_SOUMISSIONS = "data/stockage/soumissions"
DOSSIER_RAPPORTS_GENERES = "data/rapports_generes"

# Seuils de détection (valeurs par défaut)
SEUIL_ALERTE_DEFAUT = 30.0
SEUIL_CRITIQUE_DEFAUT = 70.0

# Pondération du score final (doit rester cohérent avec similarite.py)
POIDS_LEXICAL = 0.4
POIDS_SEMANTIQUE = 0.6

NOM_APPLICATION = "PlagiCheck"