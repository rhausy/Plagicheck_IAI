"""
Point d'entrée de l'application PlagiCheck.


"""

import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import moteur, Base
from app.config import NOM_APPLICATION, RACINE_PROJET
from app.routers import documents, auth, analyses, admin, rapports, commentaires
from fastapi.staticfiles import StaticFiles

# Créer les tables de la base de données si elles n'existent pas encore
Base.metadata.create_all(bind=moteur)

# Initialiser l'application FastAPI
app = FastAPI(
    title=NOM_APPLICATION,
    description="Système intelligent de détection des plagiats dans les rapports académiques",
    version="1.0.0",
    docs_url="/api/docs",        # Documentation Swagger déplacée
    redoc_url="/api/redoc",      # Documentation ReDoc
    openapi_url="/api/openapi.json"
)

# ---------- Middlewares de sécurité ----------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Ajoute des en-têtes de sécurité HTTP à chaque réponse."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# Hôtes de confiance (à adapter selon le déploiement)
# En développement, on autorise localhost et 127.0.0.1 sur tous les ports
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.localhost", "testserver"]
)

# CORS : uniquement si le frontend est servi depuis une origine différente.
# Comme le frontend est monté sur /app (même origine), on peut être strict.
# Pour le développement avec un serveur front séparé, décommenter :
"""
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
"""

# Relier les routes des dossiers "routers" à l'application
app.include_router(documents.router)
app.include_router(auth.router)
app.include_router(analyses.router)
app.include_router(admin.router)
app.include_router(rapports.router)
app.include_router(commentaires.router)

# Servir le frontend (pages HTML, JS, CSS, images)
app.mount(
    "/app", 
    StaticFiles(directory=RACINE_PROJET / "app" / "Frontend", html=True), 
    name="frontend"
)


# Route de vérification simple : confirme que le serveur tourne bien
@app.get("/")
def etat_du_service():
    return {
        "application": NOM_APPLICATION,
        "statut": "en ligne",
        "version": "1.0.0"
    }


@app.get("/sante")
def sante():
    """Health check pour monitoring."""
    return {"statut": "ok"}