"""
Extraction du texte brut d'un document PDF ou Word (CU7).
"""

import os
import fitz  # PyMuPDF
from docx import Document as DocumentWord


class ErreurExtractionTexte(Exception):
    """Levée quand un document ne peut pas être lu (CU18)."""
    pass


class ExtracteurTexte:

    FORMATS_AUTORISES = (".pdf", ".docx")

    # Point d'entrée : détecte le format et appelle la bonne méthode
    def extraire(self, chemin_fichier: str) -> str:
        if not os.path.exists(chemin_fichier):
            raise ErreurExtractionTexte(f"Fichier introuvable : {chemin_fichier}")

        extension = os.path.splitext(chemin_fichier)[1].lower()

        if extension == ".pdf":
            texte = self.extraire_depuis_pdf(chemin_fichier)
        elif extension == ".docx":
            texte = self.extraire_depuis_word(chemin_fichier)
        else:
            raise ErreurExtractionTexte(f"Format non supporté : {extension}")

        if not texte or len(texte.strip()) < 50:
            raise ErreurExtractionTexte("Aucun texte exploitable trouvé dans ce document.")

        return texte

    # Extraction spécifique aux fichiers PDF
    def extraire_depuis_pdf(self, chemin_fichier: str) -> str:
        texte_complet = []
        try:
            with fitz.open(chemin_fichier) as document:
                for page in document:
                    texte_complet.append(page.get_text())
        except Exception as erreur:
            raise ErreurExtractionTexte(f"Impossible de lire le PDF : {erreur}")
        return "\n".join(texte_complet)

    # Extraction spécifique aux fichiers Word
    def extraire_depuis_word(self, chemin_fichier: str) -> str:
        try:
            document = DocumentWord(chemin_fichier)
            paragraphes = [p.text for p in document.paragraphs]
        except Exception as erreur:
            raise ErreurExtractionTexte(f"Impossible de lire le fichier Word : {erreur}")
        return "\n".join(paragraphes)