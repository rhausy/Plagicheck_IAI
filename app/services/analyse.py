"""
Orchestrateur de l'analyse : enchaîne extraction, découpage en sections,
prétraitement et calcul de similarité pour produire un résultat complet.

Sécurité : chaque analyse crée ses propres instances de traitement pour
éviter les interférences entre requêtes simultanées (thread-safety).
"""

from app.services.extraction import ExtracteurTexte, ErreurExtractionTexte
from app.services.decoupage_sections import DecoupeurSections
from app.services.pretraitement import Pretraiteur
from app.services.similarite import CalculateurSimilarite
from app.services.neutraliseur_gabarit import NeutraliseurGabarit


class OrchestrateurAnalyse:
    """Point d'entrée unique pour lancer une analyse complète sur un document."""

    def __init__(self):
        # Extracteur et découpeur sont sans état interne : partagés sans risque
        self.extracteur = ExtracteurTexte()
        self.decoupeur = DecoupeurSections()
        # Le calculateur de similarité contient un modèle lourd, on le partage
        # car il est en lecture seule après initialisation.
        self.calculateur = CalculateurSimilarite()
        # ATTENTION : pas de neutraliseur partagé ici !

    def analyser(
        self,
        chemin_document_soumis: str,
        documents_reference: list[dict],
        documents_meme_etudiant: list[dict],
        texte_gabarit: str = "",
    ) -> dict:
        """
        Analyse un document soumis : le compare section par section à la
        base de référence générale, puis aux anciens documents du même étudiant.
        
        Args:
            texte_gabarit: Texte du gabarit déjà extrait (vide si aucun gabarit).
                           Un neutraliseur local est créé pour cette analyse uniquement.
        """
        texte_brut = self.extracteur.extraire(chemin_document_soumis)
        sections_soumises = self.decoupeur.decouper(texte_brut)

        # Création d'un neutraliseur LOCAL à cette analyse (évite les courses critiques)
        neutraliseur_local = NeutraliseurGabarit()
        if texte_gabarit:
            neutraliseur_local.charger_gabarit(texte_gabarit)

        resultats_par_section = {}

        for nom_section, texte_section in sections_soumises.items():
            texte_section_neutralise = neutraliseur_local.neutraliser(texte_section)
            texte_section_propre = self.pretraiteur.pretraiter(
                texte_section_neutralise
            )

            correspondances_reference = self._comparer_a_une_liste(
                texte_section_propre,
                documents_reference,
                nom_section,
                "reference_generale",
            )
            correspondances_auto = self._comparer_a_une_liste(
                texte_section_propre,
                documents_meme_etudiant,
                nom_section,
                "auto_reutilisation",
            )

            toutes = correspondances_reference + correspondances_auto
            meilleur_score = max((c["score_final"] for c in toutes), default=0.0)

            resultats_par_section[nom_section] = {
                "score_section": meilleur_score,
                "correspondances": toutes,
            }

        score_global = self._calculer_score_global(resultats_par_section)
        return {"score_global": score_global, "sections": resultats_par_section}

    def _comparer_a_une_liste(
        self,
        texte_propre: str,
        documents: list[dict],
        nom_section: str,
        type_comparaison: str,
    ) -> list[dict]:
        """Compare une section à chaque document d'une liste (référence ou auto)."""
        resultats = []
        for document in documents:
            try:
                texte_reference_brut = self.extracteur.extraire(document["chemin"])
            except ErreurExtractionTexte:
                continue  # document illisible : on l'ignore, pas bloquant

            sections_reference = self.decoupeur.decouper(texte_reference_brut)
            texte_section_reference = sections_reference.get(nom_section, "")
            if not texte_section_reference:
                continue  # ce document n'a pas cette section

            texte_reference_propre = self.pretraiteur.pretraiter(
                texte_section_reference
            )
            scores = self.calculateur.calculer_score_final(
                texte_propre, texte_reference_propre
            )

            resultats.append(
                {
                    "document_reference_id": document["id"],
                    "type_comparaison": type_comparaison,
                    **scores,
                }
            )
        return resultats

    def _calculer_score_global(self, resultats_par_section: dict) -> float:
        """Le score global = le score de section le plus élevé."""
        scores = [
            donnees["score_section"] for donnees in resultats_par_section.values()
        ]
        return round(max(scores), 2) if scores else 0.0