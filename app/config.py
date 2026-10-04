"""
Configuration centrale de PlagiCheck — chargement sécurisé des secrets.
Aucune valeur par défaut sensible n'est autorisée en production.
"""

import os
import secrets
import sys
from pathlib import Path

# Répertoire du projet (racine au-dessus de app/)
RACINE_PROJET = Path(__file__).resolve().parent.parent

# Chargement du .env (développement / test uniquement)
from dotenv import load_dotenv

load_dotenv(RACINE_PROJET / ".env")


# ---------- Validation stricte au démarrage ----------

def _exiger_cle():
    cle = os.getenv("CLE_SECRETE", "").strip()
    valeurs_interdites = {
        "change-moi-avant-la-mise-en-production",
        "secret", "secretkey", "changeme", "plagicheck", "test",
    }
    if not cle or cle.lower() in valeurs_interdites:
        if os.getenv("PLAGICHECK_ENV") == "production":
            print("ERREUR : CLE_SECRETE manquante ou par défaut en production.", file=sys.stderr)
            sys.exit(1)
        # Développement : générer une clé éphémère aléatoire (pas de valeur codée)
        cle = secrets.token_urlsafe(48)
        print("AVERTISSEMENT : CLE_SECRETE absente ou faible. Clé éphémère générée.")
    if len(cle) < 32:
        print("ERREUR : CLE_SECRETE doit avoir au moins 32 caractères.", file=sys.stderr)
        sys.exit(1)
    return cle


CLE_SECRETE = _exiger_cle()
ALGORITHME_JWT = "HS256"
DUREE_SESSION_MINUTES = int(os.getenv("DUREE_SESSION_MINUTES", "120"))

# Répertoires de données (hors racine publique)
DOSSIER_DATA = RACINE_PROJET / "data"
DOSSIER_DOCUMENTS_REFERENCE = DOSSIER_DATA / "stockage" / "reference"
DOSSIER_DOCUMENTS_SOUMISSIONS = DOSSIER_DATA / "stockage" / "soumissions"
DOSSIER_RAPPORTS_GENERES = DOSSIER_DATA / "rapports_generes"
DOSSIER_JOURNAUX = DOSSIER_DATA / "journaux"

# Création automatique au démarrage si absents
for d in [
    DOSSIER_DOCUMENTS_REFERENCE,
    DOSSIER_DOCUMENTS_SOUMISSIONS,
    DOSSIER_RAPPORTS_GENERES,
    DOSSIER_JOURNAUX,
]:
    d.mkdir(parents=True, exist_ok=True)

# Base de données
CHEMIN_BASE_DONNEES = os.getenv("CHEMIN_BASE_DONNEES", f"sqlite:///{DOSSIER_DATA / 'plagicheck.db'}")

# Seuils (configurables via admin)
SEUIL_ALERTE_DEFAUT = float(os.getenv("SEUIL_ALERTE_DEFAUT", "30.0"))
SEUIL_CRITIQUE_DEFAUT = float(os.getenv("SEUIL_CRITIQUE_DEFAUT", "70.0"))

# Pondération de fusion : doit rester cohérente avec similarite.py
POIDS_LEXICAL = float(os.getenv("POIDS_LEXICAL", "0.4"))
POIDS_SEMANTIQUE = float(os.getenv("POIDS_SEMANTIQUE", "0.6"))

NOM_APPLICATION = "PlagiCheck"

# Limitation de débit (par adresse IP et par compte)
LIMITE_GLOBALE_MINUTE = int(os.getenv("LIMITE_GLOBALE_MINUTE", "240"))