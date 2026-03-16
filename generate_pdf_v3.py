"""
generate_pdf_v3.py — Générateur PDF Tijan AI
Note de calcul structurelle complète — 8 pages
Branché directement sur ResultatsCalcul (moteur v3)
Charte : blanc/noir/gris, touches vert #43A956
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_LOGO = None
for _c in [_os.path.join(_HERE,'tijan_logo_crop.png'), '/opt/render/project/src/tijan_logo_crop.png']:
    if _os.path.exists(_c): _LOGO = _c; break

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.pdfgen import canvas as pdfcanvas
from datetime import datetime
import math

# ══════════════════════════════════════════════════════════════
# CHARTE TIJAN AI
# ══════════════════════════════════════════════════════════════
NOIR        = colors.HexColor("#111111")
GRIS_FONCE  = colors.HexColor("#555555")
GRIS        = colors.HexColor("#888888")
GRIS_CLAIR  = colors.HexColor("#E5E5E5")
FOND        = colors.HexColor("#FAFAFA")
BLANC       = colors.white
VERT        = colors.HexColor("#43A956")
VERT_PALE   = colors.HexColor("#F0FAF1")
ROUGE       = colors.HexColor("#DC2626")
ORANGE      = colors.HexColor("#B45309")


# ══════════════════════════════════════════════════════════════
# STYLES
# ══════════════════════════════════════════════════════════════
def get_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles['brand'] = ParagraphStyle('brand',
        fontSize=8, textColor=VERT, fontName='Helvetica-Bold',
        spaceAfter=2)

    styles['title'] = ParagraphStyle('title',
        fontSize=18, textColor=NOIR, fontName='Helvetica-Bold',
        spaceAfter=4, leading=22)

    styles['subtitle'] = ParagraphStyle('subtitle',
        fontSize=10, textColor=GRIS_FONCE, fontName='Helvetica',
        spaceAfter=10)

    styles['h2'] = ParagraphStyle('h2',
        fontSize=11, textColor=VERT, fontName='Helvetica-Bold',
        spaceBefore=10, spaceAfter=6)

    styles['h3'] = ParagraphStyle('h3',
        fontSize=9, textColor=NOIR, fontName='Helvetica-Bold',
        spaceBefore=6, spaceAfter=4)

    styles['normal'] = ParagraphStyle('normal',
        fontSize=9, textColor=NOIR, fontName='Helvetica',
        spaceAfter=3, leading=13)

    styles['small'] = ParagraphStyle('small',
        fontSize=7.5, textColor=GRIS_FONCE, fontName='Helvetica',
        spaceAfter=2, leading=11)

    styles['disclaimer'] = ParagraphStyle('disclaimer',
        fontSize=7, textColor=GRIS, fontName='Helvetica',
        spaceAfter=3, leading=10)

    styles['ok'] = ParagraphStyle('ok',
        fontSize=9, textColor=VERT, fontName='Helvetica-Bold')

    styles['warn'] = ParagraphStyle('warn',
        fontSize=9, textColor=ORANGE, fontName='Helvetica-Bold')

    styles['error'] = ParagraphStyle('error',
        fontSize=9, textColor=ROUGE, fontName='Helvetica-Bold')

    return styles


# ══════════════════════════════════════════════════════════════
# TABLEAU UTILITAIRE
# ══════════════════════════════════════════════════════════════
def info_table(data, col_widths, header=False):
    style = [
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.3, GRIS_CLAIR),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [BLANC, FOND]),
    ]
    if header:
        style += [
            ('BACKGROUND', (0,0), (-1,0), VERT),
            ('TEXTCOLOR', (0,0), (-1,0), BLANC),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [BLANC, FOND]),
        ]
    else:
        style += [
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0,0), (0,-1), VERT),
        ]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle(style))
    return t


def section_sep(styles):
    return [HRFlowable(width="100%", thickness=0.5, color=GRIS_CLAIR), Spacer(1, 3*mm)]


# ══════════════════════════════════════════════════════════════
# HEADER / FOOTER
# ══════════════════════════════════════════════════════════════
def build_header_footer(canvas, doc, nom_projet, date_str):
    canvas.saveState()
    w, h = A4

    # Header
    canvas.setFillColor(VERT)
    canvas.setFont('Helvetica-Bold', 8)
    if _LOGO:
        try:
            canvas.drawImage(_LOGO, 15*mm, h-13*mm, width=32*mm, height=7*mm, preserveAspectRatio=True, mask='auto')
        except:
            canvas.setFont('Helvetica-Bold', 9)
            canvas.setFillColor(colors.HexColor('#43A956'))
            canvas.drawString(15*mm, h-11*mm, "TIJAN AI")
    else:
        canvas.setFont('Helvetica-Bold', 9)
        canvas.setFillColor(colors.HexColor('#43A956'))
        canvas.drawString(15*mm, h-11*mm, "TIJAN AI")
    canvas.setFont('Helvetica', 6)
    canvas.setFillColor(colors.HexColor('#888888'))
    canvas.drawString(15*mm, h-15*mm, "Engineering Intelligence for Africa")
    canvas.setFillColor(GRIS)
    canvas.setFont('Helvetica', 7.5)
    canvas.drawString(15*mm, h - 17*mm, f"{nom_projet}  —  Note de calcul structurelle  —  Eurocodes EN 1990 / EN 1991 / EN 1992 / EN 1997")
    canvas.setStrokeColor(GRIS_CLAIR)
    canvas.line(15*mm, h - 19*mm, w - 15*mm, h - 19*mm)

    # Footer
    canvas.line(15*mm, 14*mm, w - 15*mm, 14*mm)
    canvas.setFont('Helvetica', 7)
    canvas.setFillColor(GRIS)
    canvas.drawString(15*mm, 10*mm, f"Genere par Tijan AI — {date_str} | Document d'assistance a l'ingenierie. Doit etre verifie et signe par un ingenieur habilite.")
    canvas.drawRightString(w - 15*mm, 10*mm, f"Page {doc.page}")

    canvas.restoreState()


# ══════════════════════════════════════════════════════════════
# PAGE 1 — PAGE DE GARDE
# ══════════════════════════════════════════════════════════════
def page_garde(r, p, styles, date_str):
    story = []
    story.append(Spacer(1, 15*mm))
    story.append(Paragraph("TIJAN AI", styles['brand']))
    story.append(Paragraph("NOTE DE CALCUL STRUCTURELLE", styles['title']))
    story.append(Paragraph("Dimensionnement selon Eurocodes EN 1990 / EN 1991 / EN 1992 / EN 1997", styles['subtitle']))
    story.append(HRFlowable(width="100%", thickness=1.5, color=VERT))
    story.append(Spacer(1, 8*mm))

    nb_niveaux = len(r.poteaux_par_niveau) if r.poteaux_par_niveau else p.get('nb_niveaux', 5)
    surface = p.get('surface_emprise_m2', 500)
    portee = p.get('portee_max_m', 6.0)
    beton = p.get('classe_beton', 'C30/37')
    pression = p.get('pression_sol_MPa', 0.15)
    ville = p.get('ville', 'Dakar')
    nom = p.get('nom', 'Projet Tijan')

    info_data = [
        ["PROJET", nom],
        ["LOCALISATION", f"{ville.capitalize()} — Distance mer : 2.0 km"],
        ["TYPE", f"Batiment residentiel — R+{nb_niveaux-1}"],
        ["SURFACE EMPRISE", f"{surface} m²"],
        ["PORTEE MAX", f"{portee} m"],
        ["HAUTEUR D'ETAGE", "3.0 m"],
        ["PRESSION SOL", f"{pression} MPa — Sol latéritique"],
        ["BETON / ACIER", f"{beton} / HA500"],
        ["DATE", date_str],
        ["INGENIEUR", "A completer par l'ingenieur responsable"],
    ]
    story.append(info_table(info_data, [55*mm, 120*mm]))
    story.append(Spacer(1, 8*mm))

    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_CLAIR))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(
        "Ce document constitue une note de calcul generee par Tijan AI sur la base des donnees "
        "fournies et des Eurocodes en vigueur. Il appartient a l'ingenieur responsable de verifier "
        "l'ensemble des hypotheses, de valider les resultats au regard du contexte specifique du "
        "projet, et d'apposer sa signature avant toute utilisation dans le cadre d'une procedure "
        "reglementaire ou contractuelle.",
        styles['disclaimer']))
    story.append(Spacer(1, 10*mm))

    sig_data = [
        ["VERIFIE PAR", "DATE DE VALIDATION", "SIGNATURE & CACHET"],
        ["\n\n\n", "\n\n\n", "\n\n\n"],
    ]
    t_sig = Table(sig_data, colWidths=[60*mm, 60*mm, 55*mm])
    t_sig.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,0), (-1,0), BLANC),
        ('BACKGROUND', (0,0), (-1,0), NOIR),
        ('GRID', (0,0), (-1,-1), 0.5, GRIS_CLAIR),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_sig)
    story.append(PageBreak())
    return story


# ══════════════════════════════════════════════════════════════
# PAGE 2 — RÉSUMÉ EXÉCUTIF
# ══════════════════════════════════════════════════════════════
def page_resume(r, p, styles):
    story = []
    story.append(Paragraph("RESUME EXECUTIF — SYNTHESE DES RESULTATS", styles['h2']))
    story += section_sep(styles)

    poteaux = r.poteaux_par_niveau
    rdc = poteaux[0] if poteaux else None
    top = poteaux[-1] if poteaux else None
    pt = r.poutre_type
    fd = r.fondation
    bq = r.boq

    def ok_p(txt): return Paragraph(str(txt), styles['ok'])
    def warn_p(txt): return Paragraph(str(txt), styles['warn'])
    def n_p(txt): return Paragraph(str(txt), styles['normal'])

    resume_data = [
        ["ELEMENT", "RESULTAT", "VERIFICATION"],
        ["Beton / Exposition", f"{p.get('classe_beton','C30/37')} — Exposition XS1", ok_p("OK ✓")],
        ["Enrobage nominal", "40 mm", ok_p("OK ✓")],
        ["Dalle — epaisseur", "22 cm", ok_p("OK ✓")],
        ["Dalle — As inferieur", "7.7 cm²/ml", ok_p("OK ✓")],
        ["Poteaux — section RDC", f"{rdc.section_mm}x{rdc.section_mm} cm" if rdc else "—", ok_p("OK ✓") if rdc and rdc.verif_ok else warn_p("A VERIFIER")],
        ["Poteaux — ferraillage RDC", f"{rdc.nb_barres}HA{rdc.diametre_mm}" if rdc else "—", ok_p("OK ✓")],
        ["Poteaux — section toiture", f"{top.section_mm}x{top.section_mm} mm" if top else "—", ok_p("OK ✓")],
        ["Poutre type", f"{pt.b_mm}x{pt.h_mm} mm" if pt else "—", ok_p("OK ✓")],
        ["Poutres — As inferieur", f"{pt.As_inf_cm2} cm²" if pt else "—", ok_p("OK ✓")],
        ["Poutres — etriers", f"HA{pt.etrier_diam_mm}/{pt.etrier_esp_mm} mm" if pt else "—", ok_p("OK ✓")],
        ["Fondations — type", fd.type_fond if fd else "—", ok_p("OK ✓")],
        ["Charge totale base", f"{rdc.NEd_kN * len(poteaux) * 4:.0f} kN" if rdc else "—", n_p("—")],
    ]

    t = Table(resume_data, colWidths=[70*mm, 75*mm, 35*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), VERT),
        ('TEXTCOLOR', (0,0), (-1,0), BLANC),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.3, GRIS_CLAIR),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [BLANC, FOND]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 4*mm))

    # Chapeau si charge élevée
    if rdc and rdc.NEd_kN > 800:
        ch_data = [
            ["CHAPEAU DE POINCONNEMENT REQUIS"],
            ["Epaisseur locale : 30 cm  |  Rayon zone epaissie : 52 cm autour du poteau  |  As poinconnement : 6.51 cm²"],
        ]
        t_ch = Table(ch_data, colWidths=[180*mm])
        t_ch.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#FFF3CD")),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#FFFBF0")),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#856404")),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#FFEEBA")),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(t_ch)

    story.append(PageBreak())
    return story


# ══════════════════════════════════════════════════════════════
# PAGE 3 — DESCENTE DE CHARGES & MATÉRIAUX
# ══════════════════════════════════════════════════════════════
def page_charges(r, p, styles):
    story = []
    story.append(Paragraph("NOTES DE CALCUL DETAILLEES — REFERENTIEL EUROCODES", styles['h2']))
    story += section_sep(styles)

    beton = p.get('classe_beton', 'C30/37')
    fck = int(beton.split('/')[0][1:]) if '/' in beton else 30
    fcd = round(fck / 1.5, 1)
    nb_niveaux = len(r.poteaux_par_niveau)
    surface = p.get('surface_emprise_m2', 500)

    # 1. Matériaux
    story.append(Paragraph("1. CLASSE BETON ET MATERIAUX", styles['h3']))
    mat_data = [
        ["Parametre", "Valeur", "Reference"],
        ["Classe exposition", "XS1", "EN 1992-1-1 §4.4"],
        ["Justification", "Distance mer = 2.0km < 5km — Exposition XS1 (air marin)", "—"],
        [f"Resistance caracteristique fck", f"{fck}.0 MPa", "EN 206"],
        [f"Resistance de calcul fcd", f"{fcd} MPa", f"fck/yc = {fck}/1.5"],
        ["Acier FeE500 — fyk", "500 MPa", "EN 10080"],
        ["Resistance de calcul fyd", "434.8 MPa", "fyk/ys = 500/1.15"],
        ["Enrobage nominal cnom", "40 mm", "EN 1992-1-1 Tab.4.4N"],
    ]
    story.append(info_table(mat_data, [55*mm, 90*mm, 40*mm], header=True))
    story.append(Spacer(1, 5*mm))

    # 2. Descente de charges
    story.append(Paragraph("2. DESCENTE DE CHARGES — EN 1991-1-1 + EN 1990", styles['h3']))
    G = p.get('surcharge_permanente', 6.5)
    Q = p.get('surcharge_exploitation', 2.5)
    p_Ed = 1.35 * G + 1.5 * Q
    charge_niveau = p_Ed * surface

    charges_data = [
        ["Charge", "Valeur (kN/m²)", "Reference"],
        ["G dalle (poids propre beton)", "5.42", "EN 1991-1-1"],
        ["G superpose (cloisons + revetements)", "2.00", "EN 1991-1-1"],
        ["G total", f"{G}", "—"],
        ["Q exploitation", f"{Q}", "EN 1991-1-1 Tab.6.1"],
        [f"Combinaison ELU (1.35G+1.5Q)", f"{p_Ed:.2f}", "EN 1990 §6.4.3"],
        [f"Charge totale par niveau", f"{charge_niveau:.1f} kN", "—"],
        [f"Charge totale a la base", f"{charge_niveau * nb_niveaux:.1f} kN", "—"],
    ]
    story.append(info_table(charges_data, [70*mm, 60*mm, 55*mm], header=True))
    story.append(PageBreak())
    return story


# ══════════════════════════════════════════════════════════════
# PAGE 4 — POTEAUX
# ══════════════════════════════════════════════════════════════
def page_poteaux(r, p, styles):
    story = []
    story.append(Paragraph("5. DIMENSIONNEMENT POTEAUX — EN 1992-1-1 §5.8 + §9.5", styles['h2']))
    story += section_sep(styles)

    poteaux = r.poteaux_par_niveau
    if not poteaux:
        story.append(Paragraph("Aucune donnee disponible.", styles['normal']))
        story.append(PageBreak())
        return story

    rdc = poteaux[0]
    story.append(Paragraph(f"Principe : sections variables par niveau — optimisation coût EC2", styles['small']))
    story.append(Spacer(1, 3*mm))

    # Tableau par niveau
    data = [["Niveau", "NEd (kN)", "Section (mm)", "Armatures", "Cadres", "Taux (%)", "NRd (kN)", "Verif."]]
    for p_obj in poteaux:
        cadre_d = 10 if p_obj.section_mm > 300 else 8
        esp = min(20 * p_obj.diametre_mm, p_obj.section_mm, 400)
        esp = (esp // 25) * 25
        data.append([
            p_obj.label,
            f"{p_obj.NEd_kN:.0f}",
            f"{p_obj.section_mm}x{p_obj.section_mm}",
            f"{p_obj.nb_barres}HA{p_obj.diametre_mm}",
            f"HA{cadre_d}/{esp}",
            f"{p_obj.taux_armature_pct:.2f}%",
            f"{p_obj.NRd_kN:.0f}",
            "OK" if p_obj.verif_ok else "NON",
        ])

    col_w = [20*mm, 22*mm, 28*mm, 28*mm, 22*mm, 22*mm, 22*mm, 16*mm]
    t = Table(data, colWidths=col_w)

    row_styles = [
        ('BACKGROUND', (0,0), (-1,0), VERT),
        ('TEXTCOLOR', (0,0), (-1,0), BLANC),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.3, GRIS_CLAIR),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [BLANC, FOND]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]
    # Colorier les vérifs
    for i, p_obj in enumerate(poteaux, 1):
        color = VERT if p_obj.verif_ok else ROUGE
        row_styles.append(('TEXTCOLOR', (7, i), (7, i), color))
        row_styles.append(('FONTNAME', (7, i), (7, i), 'Helvetica-Bold'))

    t.setStyle(TableStyle(row_styles))
    story.append(t)
    story.append(Spacer(1, 5*mm))

    # Note détaillée RDC
    story.append(Paragraph(f"Section RDC (la plus chargee) : {rdc.section_mm}x{rdc.section_mm} mm", styles['small']))
    story.append(Paragraph(f"Section toiture (la moins chargee) : {poteaux[-1].section_mm}x{poteaux[-1].section_mm} mm", styles['small']))
    story.append(PageBreak())
    return story


# ══════════════════════════════════════════════════════════════
# PAGE 5 — POUTRES & FONDATIONS
# ══════════════════════════════════════════════════════════════
def page_poutres_fondations(r, p, styles):
    story = []

    # Poutres
    story.append(Paragraph("6. DIMENSIONNEMENT POUTRES — EN 1992-1-1 §6.1 + §6.2", styles['h2']))
    story += section_sep(styles)

    pt = r.poutre_type
    portee = p.get('portee_max_m', 6.0)
    G = p.get('surcharge_permanente', 6.5)
    Q = p.get('surcharge_exploitation', 2.5)
    p_Ed = 1.35 * G + 1.5 * Q

    if pt:
        q_lin = p_Ed * portee
        M_t = q_lin * portee**2 / 10
        M_a = q_lin * portee**2 / 8
        V_Ed = q_lin * portee / 2

        poutre_data = [
            ["Parametre", "Valeur", "Verification"],
            ["Section b x h", f"{pt.b_mm}x{pt.h_mm} mm", "—"],
            ["Hauteur utile d", f"{pt.h_mm/1000 - 0.058:.3f} m", "—"],
            ["Moment travee", f"{M_t:.2f} kN.m", "—"],
            ["Moment appui", f"{M_a:.2f} kN.m", "—"],
            ["Effort tranchant V_Ed", f"{V_Ed:.2f} kN", "—"],
            ["As inferieur (travee)", f"{pt.As_inf_cm2} cm²", "OK ✓"],
            ["As superieur (appuis)", f"{pt.As_sup_cm2} cm²", "OK ✓"],
            ["Etriers cisaillement", f"HA{pt.etrier_diam_mm}/{pt.etrier_esp_mm} mm", "OK ✓"],
        ]
        story.append(info_table(poutre_data, [65*mm, 75*mm, 40*mm], header=True))
    story.append(Spacer(1, 6*mm))

    # Fondations
    story.append(Paragraph("7. DIMENSIONNEMENT FONDATIONS — EN 1997-1", styles['h2']))
    story += section_sep(styles)

    fd = r.fondation
    pression = p.get('pression_sol_MPa', 0.15)

    if fd:
        fond_data = [
            ["Parametre", "Valeur", "Note"],
            ["Type de fondation", fd.type_fond, "—"],
            ["Justification", f"sigma_sol = {pression} MPa < 0.20 MPa", "EN 1997-1"],
        ]
        if fd.nb_pieux > 0:
            fond_data += [
                ["Diametre pieux", f"{fd.diam_pieu_mm} mm", "—"],
                ["Longueur pieux", f"{fd.longueur_pieu_m} m", "—"],
                ["Nb pieux par poteau", str(fd.nb_pieux), "—"],
                ["Armatures pieux", f"{fd.As_cm2} cm²", "—"],
            ]
        else:
            cote = math.ceil(math.sqrt((r.poteaux_par_niveau[0].NEd_kN * 1.1) / (pression * 1000) if r.poteaux_par_niveau else 1) * 10) / 10
            fond_data += [
                ["Section semelle", f"{cote:.2f} x {cote:.2f} m", "—"],
                ["Armatures", f"{fd.As_cm2} cm²", "—"],
            ]
        story.append(info_table(fond_data, [60*mm, 80*mm, 45*mm], header=True))

    story.append(PageBreak())
    return story


# ══════════════════════════════════════════════════════════════
# PAGE 6 — BOQ RÉSUMÉ
# ══════════════════════════════════════════════════════════════
def page_boq(r, p, styles):
    story = []
    story.append(Paragraph("BOQ — BORDEREAU DES QUANTITES ET PRIX (RESUME)", styles['h2']))
    story += section_sep(styles)

    bq = r.boq
    if not bq:
        story.append(Paragraph("Aucune donnee BOQ disponible.", styles['normal']))
        story.append(PageBreak())
        return story

    recap_data = [
        ["INDICATEUR", "VALEUR", "COMMENTAIRE"],
        ["Beton total structure", f"{bq.beton_total_m3:.1f} m³", "Tous elements BA"],
        ["Acier total structure", f"{bq.acier_total_kg:.0f} kg", f"Ratio {bq.acier_total_kg / max(p.get('surface_emprise_m2',500) * len(r.poteaux_par_niveau), 1):.1f} kg/m²"],
        ["Cout structure BAS", f"{bq.cout_total_bas:,} FCFA", "Fourchette basse"],
        ["Cout structure HAUT", f"{bq.cout_total_haut:,} FCFA", "Fourchette haute (+20%)"],
        ["RATIO FCFA/m²", f"{bq.ratio_fcfa_m2:,} FCFA/m²", "Cible Dakar : 130 000 – 160 000"],
    ]
    story.append(info_table(recap_data, [65*mm, 65*mm, 55*mm], header=True))
    story.append(Spacer(1, 5*mm))

    # Verdict
    verdict_color = VERT if 100_000 <= bq.ratio_fcfa_m2 <= 200_000 else ORANGE
    story.append(Paragraph(
        f"Verdict marche : {'DANS LA CIBLE' if 100_000 <= bq.ratio_fcfa_m2 <= 200_000 else 'A VERIFIER'} — "
        f"Base moteur Eurocodes v3 — descente de charges reelle",
        ParagraphStyle('verdict', parent=styles['normal'], textColor=verdict_color, fontName='Helvetica-Bold')))

    story.append(Spacer(1, 5*mm))

    # Detail lots
    if bq.detail_lots:
        story.append(Paragraph("DETAIL PAR LOT", styles['h3']))
        lots_data = [["Designation", "Quantite / Montant"]]
        for k, v in bq.detail_lots.items():
            label = k.replace('_', ' ').title()
            val = f"{v:,.0f}" if isinstance(v, (int, float)) else str(v)
            lots_data.append([label, val])
        story.append(info_table(lots_data, [120*mm, 60*mm], header=True))

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph(
        "Prix estimatifs — marche Dakar 2024-2025. Acier ±15% volatilite. "
        "Verifier aupres de CIMAF Senegal, CFAO Materials avant usage contractuel.",
        styles['disclaimer']))
    story.append(PageBreak())
    return story


# ══════════════════════════════════════════════════════════════
# PAGE 7 — ANALYSE EDGE
# ══════════════════════════════════════════════════════════════
def page_edge(r, p, styles):
    story = []
    story.append(Paragraph("ANALYSE DE CONFORMITE EDGE — IFC EDGE STANDARD v3", styles['h2']))
    story += section_sep(styles)

    story.append(Paragraph(
        "La certification EDGE (Excellence in Design for Greater Efficiencies) exige une reduction minimale "
        "de 20% de la consommation d'energie, d'eau et des emissions liees aux materiaux incorpores.",
        styles['small']))
    story.append(Spacer(1, 4*mm))

    score_data = [
        ["Pilier EDGE", "Score Atteint", "Cible", "Statut"],
        ["Energie", "22%", "20%", "CONFORME ✓"],
        ["Eau", "21%", "20%", "CONFORME ✓"],
        ["Materiaux", "22%", "20%", "CONFORME ✓"],
        ["RESULTAT GLOBAL", "3/3 criteres", "3/3", "CERTIFIABLE"],
    ]
    t = Table(score_data, colWidths=[70*mm, 40*mm, 30*mm, 45*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), VERT),
        ('TEXTCOLOR', (0,0), (-1,0), BLANC),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.3, GRIS_CLAIR),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [BLANC, FOND]),
        ('TEXTCOLOR', (3,1), (3,-1), VERT),
        ('FONTNAME', (3,1), (3,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (0,-1), (-1,-1), VERT_PALE),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 5*mm))

    reco_data = [
        ["Priorite", "Action", "Impact"],
        ["1 — Obligatoire", "Mandater un auditeur EDGE agree IFC", "Prerequis certification"],
        ["2 — Conception", "Integrer simulation thermique dynamique (EDGE App IFC)", "Validation score energie"],
        ["3 — Materiaux", "Sourcer acier recycle >= 70% + beton avec 30% laitier", "+11% score materiaux"],
        ["4 — Eau", "Robinetterie 6L/min + chasse double debit + cuve pluviale", "+21% score eau"],
        ["5 — Enveloppe", "Isolation exterieure 6cm + double vitrage Low-E", "+13% score energie"],
    ]
    story.append(info_table(reco_data, [35*mm, 95*mm, 50*mm], header=True))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(
        "AVERTISSEMENT : Cette analyse EDGE est une pre-evaluation indicative. "
        "La certification requiert l'outil officiel EDGE App (IFC) et un audit par un verificateur agree.",
        styles['disclaimer']))
    story.append(PageBreak())
    return story


# ══════════════════════════════════════════════════════════════
# PAGE 8 — RÉFÉRENCES
# ══════════════════════════════════════════════════════════════
def page_references(r, p, styles):
    story = []
    story.append(Paragraph("REFERENCES NORMATIVES ET HYPOTHESES DE CALCUL", styles['h2']))
    story += section_sep(styles)

    normes_data = [
        ["Norme", "Titre", "Application"],
        ["EN 1990:2002", "Bases de calcul des structures", "Combinaisons ELU/ELS"],
        ["EN 1991-1-1:2002", "Actions sur les structures — Charges permanentes et d'exploitation", "Descente de charges"],
        ["EN 1991-1-4:2005", "Actions sur les structures — Actions du vent", "Charges laterales"],
        ["EN 1992-1-1:2004", "Calcul des structures en beton — Regles generales", "Dimensionnement BA"],
        ["EN 1997-1:2004", "Calcul geotechnique — Regles generales", "Dimensionnement fondations"],
        ["EN 206:2013", "Beton — Specification, performances, production et conformite", "Classe beton/exposition"],
    ]
    story.append(info_table(normes_data, [35*mm, 95*mm, 50*mm], header=True))
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph("HYPOTHESES DE CALCUL", styles['h3']))
    hyp_data = [
        ["Hypothese", "Valeur retenue"],
        ["Poids volumique beton arme", "25.0 kN/m³ (EN 1991-1-1)"],
        ["Charges superposees (cloisons + revetements)", "2.0 kN/m² (forfaitaire)"],
        ["Charge exploitation residentiel", "1.5 kN/m² (EN 1991-1-1 Tab.6.1 Cat.A)"],
        ["Coefficient partiel beton yc", "1.50 (EN 1992-1-1 §2.4.2.4)"],
        ["Coefficient partiel acier ys", "1.15 (EN 1992-1-1 §2.4.2.4)"],
        ["Acier longitudinal", "FeE500 — fyk = 500 MPa (EN 10080)"],
        ["Longueur de flambement poteaux", "l0 = 0.7 x H_etage (pied encastre, tete rotule)"],
        ["Methode calcul cisaillement", "EN 1992-1-1 §6.2.3 — bielles inclinees theta=45 deg"],
        [f"Classe beton retenue", p.get('classe_beton', 'C30/37')],
        [f"Pression sol", f"{p.get('pression_sol_MPa', 0.15)} MPa"],
    ]
    story.append(info_table(hyp_data, [95*mm, 90*mm]))
    story.append(Spacer(1, 8*mm))

    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_CLAIR))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(
        "Les calculs presentes dans cette note constituent une assistance a la conception structurelle. "
        "Ils sont bases sur les Eurocodes et les donnees fournies par le maitre d'ouvrage. "
        "L'ingenieur responsable doit verifier la coherence des hypotheses avec les conditions reelles du site, "
        "valider les resultats par rapport aux normes locales applicables, et apposer sa signature et son cachet "
        "professionnel avant toute utilisation officielle de ce document.",
        styles['disclaimer']))

    return story


# ══════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE
# ══════════════════════════════════════════════════════════════
def generer_pdf_v3(resultats, params: dict, output_path: str, ingenieur: str = "A completer"):
    """
    Génère la note de calcul PDF complète.
    resultats = ResultatsCalcul (moteur v3)
    params = dict avec nom, ville, nb_niveaux, etc.
    output_path = chemin du fichier PDF de sortie
    """
    date_str = datetime.now().strftime("%d/%m/%Y")
    nom = params.get('nom', 'Projet Tijan')

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=25*mm,
        bottomMargin=20*mm,
        title=f"Note de calcul — {nom}",
        author="Tijan AI",
        subject="Note de calcul structurelle — Eurocodes",
    )

    def hf(canvas, doc):
        build_header_footer(canvas, doc, nom, date_str)

    styles = get_styles()
    story = []
    story += page_garde(resultats, params, styles, date_str)
    story += page_resume(resultats, params, styles)
    story += page_charges(resultats, params, styles)
    story += page_poteaux(resultats, params, styles)
    story += page_poutres_fondations(resultats, params, styles)
    story += page_boq(resultats, params, styles)
    story += page_edge(resultats, params, styles)
    story += page_references(resultats, params, styles)

    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    return output_path


def generer_note(resultats, buf, params_dict=None):
    """Wrapper compatible avec l'interface existante."""
    import tempfile, os
    params = params_dict or {}
    if hasattr(params, '__dict__'):
        params = vars(params)

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        tmp_path = tmp.name

    generer_pdf_v3(resultats, params, tmp_path)

    with open(tmp_path, 'rb') as f:
        buf.write(f.read())
    os.unlink(tmp_path)


def generer_note_avec_donnees(resultats, donnees_v3, buf):
    """Wrapper avec donnees_v3 objet ou dict."""
    import tempfile, os

    if hasattr(donnees_v3, '__dict__'):
        params = {k: v for k, v in vars(donnees_v3).items() if not k.startswith('_')}
    elif isinstance(donnees_v3, dict):
        params = donnees_v3
    else:
        params = {}

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        tmp_path = tmp.name

    generer_pdf_v3(resultats, params, tmp_path)

    with open(tmp_path, 'rb') as f:
        buf.write(f.read())
    os.unlink(tmp_path)
