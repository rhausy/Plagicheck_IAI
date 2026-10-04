
"""
Neutralisation du gabarit institutionnel : retire les phrases d'un texte
qui correspondent au canevas officiel de l'IAI, pour qu'elles ne soient
jamais comptées comme suspectes.

Optimisation : pré-filtrage par ratios rapides avant le calcul coûteux
de SequenceMatcher.ratio(), ce qui divise par 10 le temps de traitement
sur des documents longs.
"""

import re
import difflib


class NeutraliseurGabarit:

    def __init__(self):
        self.phrases_gabarit = []
        self._phrases_gabarit_minuscules = []  # Cache pour éviter de répéter .lower()

    # Charge le gabarit une fois, à partir de son texte déjà extrait
    def charger_gabarit(self, texte_gabarit: str):
        self.phrases_gabarit = self._decouper_en_phrases(texte_gabarit)
        # Pré-calcul des versions minuscules pour éviter de le faire à chaque comparaison
        self._phrases_gabarit_minuscules = [p.lower() for p in self.phrases_gabarit]

    # Découpe un texte en phrases simples
    def _decouper_en_phrases(self, texte: str) -> list[str]:
        if not texte:
            return []
        phrases = re.split(r"(?<=[.!?])\s+", texte)
        return [p.strip() for p in phrases if len(p.strip()) > 15]

    # Retire du texte toute phrase trop proche d'une phrase du gabarit
    def neutraliser(self, texte: str, seuil: float = 0.85) -> str:
        # Garde-fous : si pas de gabarit ou texte vide, on renvoie tel quel
        if not self.phrases_gabarit or not texte:
            return texte

        phrases_texte = self._decouper_en_phrases(texte)
        phrases_conservees = []

        for phrase in phrases_texte:
            phrase_minuscule = phrase.lower()
            appartient_au_gabarit = False

            for phrase_gabarit_minuscule in self._phrases_gabarit_minuscules:
                # OPTIMISATION 1 : filtres rapides avant le calcul lourd
                matcher = difflib.SequenceMatcher(
                    None, phrase_minuscule, phrase_gabarit_minuscule
                )
                
                # real_quick_ratio() compare juste les longueurs (instantané)
                if matcher.real_quick_ratio() < seuil:
                    continue
                
                # quick_ratio() compare les caractères communs (très rapide)
                if matcher.quick_ratio() < seuil:
                    continue
                
                # OPTIMISATION 2 : seulement si les filtres passent, on calcule
                # le ratio exact (le seul qui soit coûteux)
                if matcher.ratio() >= seuil:
                    appartient_au_gabarit = True
                    break  # Inutile de vérifier les autres phrases du gabarit

            if not appartient_au_gabarit:
                phrases_conservees.append(phrase)

        return " ".join(phrases_conservees)