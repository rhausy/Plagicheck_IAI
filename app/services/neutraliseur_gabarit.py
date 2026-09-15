"""
Neutralisation du gabarit institutionnel  retire les
phrases d'un texte qui correspondent au canevas officiel de l'IAI,
pour qu'elles ne soient jamais comptées comme suspectes.
"""

import re
import difflib


class NeutraliseurGabarit:

    def __init__(self):
        self.phrases_gabarit = []

    # Charge le gabarit une fois, à partir de son texte déjà extrait
    def charger_gabarit(self, texte_gabarit: str):
        self.phrases_gabarit = self._decouper_en_phrases(texte_gabarit)

    # Découpe un texte en phrases simples
    def _decouper_en_phrases(self, texte: str) -> list[str]:
        phrases = re.split(r"(?<=[.!?])\s+", texte)
        return [p.strip() for p in phrases if len(p.strip()) > 15]

    # Retire du texte toute phrase trop proche d'une phrase du gabarit
    def neutraliser(self, texte: str, seuil: float = 0.85) -> str:
        if not self.phrases_gabarit:
            return texte

        phrases_texte = self._decouper_en_phrases(texte)
        phrases_conservees = []

        for phrase in phrases_texte:
            appartient_au_gabarit = any(
                difflib.SequenceMatcher(None, phrase.lower(), phrase_gabarit.lower()).ratio() >= seuil
                for phrase_gabarit in self.phrases_gabarit
            )
            if not appartient_au_gabarit:
                phrases_conservees.append(phrase)

        return " ".join(phrases_conservees)