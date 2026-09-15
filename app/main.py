"""
Point d'entrée de l'application PlagiCheck.

Pour lancer le serveur :
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import moteur, Base
from app.config import NOM_APPLICATION
from app.routers import documents, auth, analyses, admin, rapports, commentaires
from fastapi.staticfiles import StaticFiles

# Créer les tables de la base de données si elles n'existent pas encore
Base.metadata.create_all(bind=moteur)

# Initialiser l'application FastAPI
app = FastAPI(
    title=NOM_APPLICATION,
    description="Système intelligent de détection des plagiats dans les rapports académiques",
    version="0.1.0",
)

# Autoriser les pages HTML (frontend) à communiquer avec cette API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Relier les routes des dossiers "routers" à l'application
app.include_router(documents.router)
app.include_router(auth.router)
app.include_router(analyses.router)
app.include_router(admin.router)
app.include_router(rapports.router)
app.include_router(commentaires.router)
app.mount("/app", StaticFiles(directory="app/Frontend", html=True), name="frontend")


# Route de vérification simple : confirme que le serveur tourne bien
@app.get("/")
def etat_du_service():
    return {"application": NOM_APPLICATION, "statut": "en ligne"}