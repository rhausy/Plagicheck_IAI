"""
Script temporaire pour créer des comptes de test.
À SUPPRIMER après utilisation pour des raisons de sécurité.
"""
from app.database import moteur, SessionLocale, Base
from app.models import Utilisateur
from app.securite import hacher_mot_de_passe

# S'assurer que les tables existent
Base.metadata.create_all(bind=moteur)

# Comptes à créer
comptes = [
    {
        "nom": "Administrateur Test",
        "email": "admin@test.com",
        "mot_de_passe": "Admin@2026Test!",
        "role": "administrateur"
    },
    {
        "nom": "Enseignant Test",
        "email": "enseignant@test.com",
        "mot_de_passe": "Enseignant@2026Test!",
        "role": "encadrant"
    },
    {
        "nom": "Étudiant Test",
        "email": "etudiant@test.com",
        "mot_de_passe": "Etudiant@2026Test!",
        "role": "etudiant"
    }
]

db = SessionLocale()

print("🔧 Création des comptes de test...\n")

for compte in comptes:
    # Vérifier si le compte existe déjà
    existant = db.query(Utilisateur).filter(Utilisateur.email == compte["email"]).first()
    
    if existant:
        print(f"⚠️  {compte['email']} existe déjà, ignoré.")
    else:
        # Créer le compte
        utilisateur = Utilisateur(
            nom=compte["nom"],
            email=compte["email"],
            mot_de_passe_hash=hacher_mot_de_passe(compte["mot_de_passe"]),
            role=compte["role"],
            est_actif=True
        )
        db.add(utilisateur)
        print(f"✅ {compte['role'].capitalize()} créé : {compte['email']}")

db.commit()
db.close()

print("\n" + "="*50)
print("📋 COMPTES CRÉÉS :")
print("="*50)
for compte in comptes:
    print(f"\n{compte['role'].upper()}")
    print(f"  Email    : {compte['email']}")
    print(f"  Mot de passe : {compte['mot_de_passe']}")
print("="*50)
print("\n⚠️  IMPORTANT : Supprime ce fichier après utilisation !")
print("   Commande : Remove-Item creer_comptes_test.py")