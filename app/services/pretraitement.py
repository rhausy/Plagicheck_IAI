"""
Nettoyage du texte brut avant comparaison (CU8) : minuscules,
lemmatisation, retrait des mots vides, exclusion des sections
non pertinentes (bibliographie, annexes).

Prérequis : python -m spacy download fr_core_news_sm
"""

import re
import spacy


class Pretraiteur:

    # Sections à ignorer pour éviter les faux positifs de similarité
    MOTS_CLES_SECTIONS_A_EXCLURE = (
        "bibliographie",
        "références bibliographiques",
        "annexes",
        "table des matières",
    )

    def __init__(self, modele: str = "fr_core_news_sm"):
        try:
            self.nlp = spacy.load(modele)
        except OSError as erreur:
            raise OSError(
                f"Modèle spaCy '{modele}' manquant. "
                f"Lance : python -m spacy download {modele}"
            ) from erreur

    # Coupe le texte dès qu'une section à exclure est détectée
    def exclure_sections(self, texte: str) -> str:
        texte_minuscule = texte.lower()
        position_coupure = len(texte)

        for mot_cle in self.MOTS_CLES_SECTIONS_A_EXCLURE:
            position = texte_minuscule.find(f"\n{mot_cle}")
            if position != -1 and position < position_coupure:
                position_coupure = position

        return texte[:position_coupure]

    # Retire la ponctuation excessive et les caractères non pertinents
    def nettoyer(self, texte: str) -> str:
        texte = re.sub(r"\s+", " ", texte)
        texte = re.sub(r"[^\w\sÀ-ÿ]", " ", texte)
        return texte.strip().lower()

    # Lemmatise chaque mot et retire les mots vides (stopwords)
    def lemmatiser_et_retirer_stopwords(self, texte: str) -> str:
        document = self.nlp(texte)
        tokens_utiles = [
            token.lemma_
            for token in document
            if not token.is_stop and not token.is_punct and not token.is_space
            and len(token.lemma_) > 1
        ]
        return " ".join(tokens_utiles)

    # Point d'entrée : enchaîne toutes les étapes de nettoyage
    def pretraiter(self, texte_brut: str) -> str:
        texte = self.exclure_sections(texte_brut)
        texte = self.nettoyer(texte)
        texte = self.lemmatiser_et_retirer_stopwords(texte)
        return texte