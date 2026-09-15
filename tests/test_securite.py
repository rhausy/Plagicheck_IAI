"""
Tests unitaires du module de sécurité (hachage des mots de passe).
"""

from app.securite import hacher_mot_de_passe, verifier_mot_de_passe


def test_verification_mot_de_passe_correct():
    mot_de_passe = "MotDePasse123"
    hachage = hacher_mot_de_passe(mot_de_passe)

    assert verifier_mot_de_passe(mot_de_passe, hachage) is True


def test_verification_mot_de_passe_incorrect():
    hachage = hacher_mot_de_passe("MotDePasse123")

    assert verifier_mot_de_passe("MauvaisMotDePasse", hachage) is False


def test_hachage_ne_stocke_jamais_le_mot_de_passe_en_clair():
    mot_de_passe = "MotDePasse123"
    hachage = hacher_mot_de_passe(mot_de_passe)

    assert mot_de_passe not in hachage