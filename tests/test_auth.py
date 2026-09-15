"""
Tests fonctionnels de la route d'authentification /auth/connexion.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_connexion_reussie():
    client.post("/auth/inscription", json={
        "nom": "Test Utilisateur",
        "email": "test.connexion@iai-cameroun.com",
        "mot_de_passe": "MotDePasse123",
        "role": "etudiant",
})

    reponse = client.post("/auth/connexion", json={
        "email": "test.connexion@iai-cameroun.com",
        "mot_de_passe": "MotDePasse123",
    })

    assert reponse.status_code == 200
    assert "jeton_acces" in reponse.json()


def test_connexion_mot_de_passe_incorrect():
    reponse = client.post("/auth/connexion", json={
        "email": "test.connexion@iai-cameroun.com",
        "mot_de_passe": "MauvaisMotDePasse",
    })

    assert reponse.status_code == 401


def test_connexion_utilisateur_introuvable():
    reponse = client.post("/auth/connexion", json={
        "email": "inconnu@iai-cameroun.com",
        "mot_de_passe": "PeuImporte123",
    })

    assert reponse.status_code == 401