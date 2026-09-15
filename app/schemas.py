"""
Schémas Pydantic : définissent la forme des données que l'API accepte
en entrée et renvoie en sortie (validation automatique par FastAPI).
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr


# Ce que l'API renvoie après un upload réussi
class DocumentReponse(BaseModel):
    id: int
    titre: str
    type_document: str
    date_upload: datetime

    class Config:
        from_attributes = True


# Ce que le client envoie pour créer un compte
class InscriptionEntree(BaseModel):
    nom: str
    email: EmailStr
    mot_de_passe: str
    role: str  # "etudiant" | "encadrant" | "administrateur"


# Ce que le client envoie pour se connecter
class ConnexionEntree(BaseModel):
    email: EmailStr
    mot_de_passe: str


# Ce que l'API renvoie après une inscription ou une connexion réussie
class UtilisateurReponse(BaseModel):
    id: int
    nom: str
    email: str
    role: str

    class Config:
        from_attributes = True


# Ce que l'API renvoie après une connexion réussie (utilisateur + jeton)
class ConnexionReponse(BaseModel):
    utilisateur: UtilisateurReponse
    jeton_acces: str
    # Ce que l'API renvoie après une analyse terminée
class AnalyseReponse(BaseModel):
    analyse_id: int
    score_global: float
    statut: str
    # Le détail d'une comparaison avec un document précis, pour une section donnée
class CorrespondanceReponse(BaseModel):
    document_reference_id: int
    section: str
    score_lexical: float
    score_semantique: float
    score_final: float
    type_comparaison: str

    class Config:
        from_attributes = True


# Le détail complet d'une analyse, avec toutes ses correspondances
class AnalyseDetailReponse(BaseModel):
    analyse_id: int
    score_global: float
    statut: str
    correspondances: list[CorrespondanceReponse]
    # Ce que l'API renvoie pour les statistiques globales du tableau de bord admin
class StatistiquesReponse(BaseModel):
    total_utilisateurs: int
    total_rapports: int
    total_analyses: int


# Ce que l'API renvoie pour chaque utilisateur dans la liste admin
class UtilisateurAdminReponse(BaseModel):
    id: int
    nom: str
    email: str
    role: str
    est_actif: bool

    class Config:
        from_attributes = True
        # Ce que l'API renvoie après la génération d'un rapport PDF
class RapportReponse(BaseModel):
    rapport_id: int
    chemin_pdf: str
    # Ce que l'encadrant envoie pour commenter/décider d'une analyse
class CommentaireEntree(BaseModel):
    encadrant_id: int
    contenu: str
    decision: str  # "valide" | "a_revoir" | "suspect_confirme"


# Ce que l'API renvoie après l'ajout d'un commentaire
class CommentaireReponse(BaseModel):
    id: int
    contenu: str
    decision: str
    date_commentaire: datetime

    class Config:
        from_attributes = True
        # Ce que l'admin envoie pour créer un compte manuellement
class CreationUtilisateurAdmin(BaseModel):
    nom: str
    email: EmailStr
    mot_de_passe: str
    role: str  # "etudiant" | "encadrant" | "administrateur"
    
    # Ce que l'API renvoie pour l'historique des analyses d'un étudiant
class AnalyseHistoriqueReponse(BaseModel):
    analyse_id: int
    titre_document: str
    score_global: float | None
    statut: str
    date_analyse: datetime