"""
Génération du rapport PDF (CU10) : assemble le score global, le détail
par section et les correspondances dans un document téléchargeable.
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


class GenerateurRapport:

    def __init__(self, dossier_sortie: str = "data/rapports_generes"):
        self.dossier_sortie = dossier_sortie
        os.makedirs(self.dossier_sortie, exist_ok=True)
        self.styles = getSampleStyleSheet()

    # Point d'entrée : construit le PDF à partir des données d'une analyse
    def generer(self, analyse_id: int, titre_document: str, score_global: float, correspondances: list) -> str:
        nom_fichier = f"rapport_analyse_{analyse_id}.pdf"
        chemin_complet = os.path.join(self.dossier_sortie, nom_fichier)

        document = SimpleDocTemplate(chemin_complet, pagesize=A4,
                                      topMargin=2*cm, bottomMargin=2*cm)
        elements = []

        # En-tête du rapport
        style_titre = ParagraphStyle("TitreRapport", parent=self.styles["Title"], textColor=colors.HexColor("#14213D"))
        elements.append(Paragraph("PlagiCheck — Rapport de similarité", style_titre))
        elements.append(Spacer(1, 0.3*cm))
        elements.append(Paragraph(f"Document analysé : <b>{titre_document}</b>", self.styles["Normal"]))
        elements.append(Paragraph(f"Date de génération : {datetime.now().strftime('%d/%m/%Y à %H:%M')}", self.styles["Normal"]))
        elements.append(Spacer(1, 0.5*cm))

        # Score global, mis en évidence avec une couleur selon le niveau de risque
        couleur_score = colors.HexColor("#0E7C7B") if score_global < 30 else (
            colors.HexColor("#C99A2E") if score_global < 70 else colors.HexColor("#B3413E")
        )
        style_score = ParagraphStyle("Score", parent=self.styles["Heading1"], textColor=couleur_score)
        elements.append(Paragraph(f"Score global de similarité : {score_global}%", style_score))
        elements.append(Spacer(1, 0.6*cm))

        # Tableau détaillé des correspondances, section par section
        elements.append(Paragraph("Détail par dossier et par comparaison", self.styles["Heading2"]))
        elements.append(Spacer(1, 0.2*cm))

        entetes = ["Section", "Type", "Lexical", "Sémantique", "Score final"]
        lignes = [entetes]
        for correspondance in correspondances:
            lignes.append([
                correspondance["section"],
                "Auto-réutilisation" if correspondance["type_comparaison"] == "auto_reutilisation" else "Référence générale",
                f"{correspondance['score_lexical']}%",
                f"{correspondance['score_semantique']}%",
                f"{correspondance['score_final']}%",
            ])

        tableau = Table(lignes, colWidths=[3.5*cm, 3.8*cm, 2.3*cm, 2.7*cm, 2.7*cm])
        tableau.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14213D")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E7E3D8")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2EEE2")]),
        ]))
        elements.append(tableau)

        elements.append(Spacer(1, 0.8*cm))
        note = ("Ce rapport signale des similarités textuelles ; il assiste l'évaluation "
                "de l'encadrant mais ne constitue pas une décision automatique de plagiat.")
        elements.append(Paragraph(f"<i>{note}</i>", self.styles["Normal"]))

        document.build(elements)
        return chemin_complet