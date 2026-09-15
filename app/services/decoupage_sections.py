"""
Module de découpage en sections — nouvelle étape du prétraitement (CU8 étendu),
qui répond à la recommandation de l'encadrant académique : analyser le
document dossier par dossier plutôt que dans son ensemble, en s'appuyant
sur le canevas officiel de l'IAI.

Ce découpage doit s'exécuter APRÈS l'extraction du texte brut (extraction.py)
et AVANT le nettoyage/lemmatisation classique (pretraitement.py) : chaque
section obtenue ici sera ensuite prétraitée et comparée séparément.
"""

import re


class DecoupeurSections:
    """
    Découpe un texte brut en sections, en repérant les titres officiels
    des dossiers du canevas IAI, quelle que soit leur casse ou leur
    numérotation exacte (romaine, arabe, avec ou sans "DOSSIER").
    """

    # Chaque section possède plusieurs façons possibles d'être écrite
    # dans un rapport réel (on l'a vérifié sur un vrai rapport IAI) :
    # "DOSSIER I: L'EXISTANT", "Dossier 1 : L'existant", etc.
    SECTIONS_CANEVAS = {
        "Existant": [
            r"dossier\s*(i|1)\s*:?\s*l.?existant",
        ],
        "Cahier de Charge": [
            r"dossier\s*(ii|2)\s*:?\s*cahier\s*(de|des)\s*charges?",
        ],
        "Analyse": [
            r"dossier\s*(iii|3)\s*:?\s*analyse",
        ],
        "Conception": [
            r"dossier\s*(iv|4)\s*:?\s*conception",
        ],
        "Realisation": [
            r"dossier\s*(v|5)\s*:?\s*realisation",
        ],
        "Tests": [
            r"dossier\s*(vi|6)\s*:?\s*tests?\s*(et\s*realisation)?",
        ],
        "Guide": [
            r"dossier\s*(vii|7)\s*:?\s*guide\s*d.?installation",
        ],
    }

    def _normaliser(self, texte: str) -> str:
        """Retire les accents pour fiabiliser la recherche des titres (ex: 'é' -> 'e')."""
        remplacements = {
            "é": "e", "è": "e", "ê": "e", "à": "a", "ù": "u",
            "ô": "o", "î": "i", "ç": "c", "'": ".", "’": ".",
        }
        texte_normalise = texte.lower()
        for accent, sans_accent in remplacements.items():
            texte_normalise = texte_normalise.replace(accent, sans_accent)
        return texte_normalise

    def decouper(self, texte_brut: str) -> dict:
        """
        Point d'entrée principal.
        Retourne un dictionnaire {nom_section: texte_de_la_section}.
        Une section absente du document (ex: rapport encore incomplet)
        est simplement absente du dictionnaire retourné.
        """
        texte_normalise = self._normaliser(texte_brut)

        # 1. On repère la position (index de caractère) où commence chaque section
        positions_trouvees = []  # liste de (position, nom_section)

        for nom_section, motifs in self.SECTIONS_CANEVAS.items():
            for motif in motifs:
                correspondance = re.search(motif, texte_normalise)
                if correspondance:
                    positions_trouvees.append((correspondance.start(), nom_section))
                    break  # on a trouvé cette section, pas besoin des autres motifs

        # 2. On trie les sections trouvées par ordre d'apparition dans le document
        positions_trouvees.sort(key=lambda paire: paire[0])

        # 3. On découpe le texte ORIGINAL (pas normalisé) entre chaque position trouvée
        sections = {}
        for index, (position_debut, nom_section) in enumerate(positions_trouvees):
            est_derniere_section = index == len(positions_trouvees) - 1
            position_fin = (
                len(texte_brut)
                if est_derniere_section
                else positions_trouvees[index + 1][0]
            )
            sections[nom_section] = texte_brut[position_debut:position_fin].strip()

        return sections


if __name__ == "__main__":
    # Petit test manuel : à lancer avec `python -m app.services.decoupage_sections`
    exemple = """
    Introduction générale du mémoire...

    DOSSIER I: L'EXISTANT
    Ce dossier présente l'analyse de l'existant...
    Beaucoup de texte ici sur le contexte...

    DOSSIER II : CAHIER DE CHARGE
    Le cahier des charges est un document contractuel...

    DOSSIER III : ANALYSE
    Cette section présente les diagrammes UML...
    """

    decoupeur = DecoupeurSections()
    resultat = decoupeur.decouper(exemple)

    for nom_section, contenu in resultat.items():
        print(f"--- {nom_section} ({len(contenu)} caractères) ---")
        print(contenu[:100], "...\n")