"""
Calcul du score de similarité entre deux textes (CU9) : combine
une similarité lexicale (TF-IDF) et une similarité sémantique
(embeddings), pour aussi détecter les plagiats reformulés.

Les poids de fusion sont centralisés dans app/config.py pour éviter
toute divergence entre la configuration et le calcul réel.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer, util

from app.config import POIDS_LEXICAL, POIDS_SEMANTIQUE


class CalculateurSimilarite:

    # Les poids sont désormais importés depuis la configuration centrale.
    # Plus aucune valeur en dur : si l'admin change le .env, le calcul suit.
    # Exemple dans .env :
    #   POIDS_LEXICAL=0.4
    #   POIDS_SEMANTIQUE=0.6

    def __init__(self, modele_semantique: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.modele_semantique = SentenceTransformer(modele_semantique)

    # Similarité basée sur les mots exacts utilisés (TF-IDF + cosinus)
    def calculer_score_lexical(self, texte_a: str, texte_b: str) -> float:
        # Garde-fou : si un texte est vide, similarité nulle
        if not texte_a.strip() or not texte_b.strip():
            return 0.0

        vectoriseur = TfidfVectorizer()
        matrice_tfidf = vectoriseur.fit_transform([texte_a, texte_b])
        score = cosine_similarity(matrice_tfidf[0:1], matrice_tfidf[1:2])[0][0]
        return round(float(score) * 100, 2)

    # Similarité basée sur le sens des phrases (embeddings + cosinus)
    def calculer_score_semantique(self, texte_a: str, texte_b: str) -> float:
        # Garde-fou : si un texte est vide, similarité nulle
        if not texte_a.strip() or not texte_b.strip():
            return 0.0

        embedding_a = self.modele_semantique.encode(texte_a, convert_to_tensor=True)
        embedding_b = self.modele_semantique.encode(texte_b, convert_to_tensor=True)
        score = util.cos_sim(embedding_a, embedding_b).item()
        return round(score * 100, 2)

    # Point d'entrée : calcule les 2 scores puis les fusionne
    def calculer_score_final(self, texte_a: str, texte_b: str) -> dict:
        score_lexical = self.calculer_score_lexical(texte_a, texte_b)
        score_semantique = self.calculer_score_semantique(texte_a, texte_b)
        
        # Utilisation des poids importés depuis config.py
        score_final = round(
            POIDS_LEXICAL * score_lexical + POIDS_SEMANTIQUE * score_semantique,
            2,
        )
        
        return {
            "score_lexical": score_lexical,
            "score_semantique": score_semantique,
            "score_final": score_final,
        }