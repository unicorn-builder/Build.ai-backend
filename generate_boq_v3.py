"""
generate_boq_v3.py — BOQ Tijan AI
Bordereau des Quantités et Prix — Structure béton armé
Branché directement sur ResultatsCalcul (moteur v3)
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from datetime import datetime
import io

NOIR       = colors.HexColor("#111111")
GRIS_FONCE = colors.HexColor("#555555")
GRIS       = colors.HexColor("#888888")
GRIS_CLAIR = colors.HexColor("#E5E5E5")
FOND       = colors.HexColor("#FAFAFA")
BLANC      = colors.white
VERT       = colors.HexColor("#43A956")
VERT_PALE  = colors.HexColor("#F0FAF1")


def get_styles():
    base = getSampleStyleSheet()
    return {
        'brand':   ParagraphStyle('brand', fontSize=8, textColor=VERT, fontName='Helvetica-Bold', spaceAfter=2),
        'title':   ParagraphStyle('title', fontSize=16, textColor=NOIR, fontName='Helvetica-Bold', spaceAfter=4),
        'subtitle':ParagraphStyle('subtitle', fontSize=9, textColor=GRIS_FONCE, spaceAfter=8),
        'h2':      ParagraphStyle('h2', fontSize=11, textColor=VERT, fontName='Helvetica-Bold', spaceBefore=8, spaceAfter=5),
        'h3':      ParagraphStyle('h3', fontSize=9, textColor=NOIR, fontName='Helvetica-Bold', spaceBefore=5, spaceAfter=3),
        'normal':  ParagraphStyle('normal', fontSize=9, textColor=NOIR, spaceAfter=3),
        'small':   ParagraphStyle('small', fontSize=7.5, textColor=GRIS_FONCE, spaceAfter=2),
        'disclaimer': ParagraphStyle('disc', fontSize=7, textColor=GRIS, spaceAfter=2),
    }


def build_header_footer(canvas, doc, nom, date_str):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(VERT)
    canvas.setFont('Helvetica-Bold', 8)
    canvas.drawString(15*mm, h - 12*mm, "TIJAN AI")
    canvas.setFillColor(GRIS)
    canvas.setFont('Helvetica', 7.5)
    canvas.drawString(15*mm, h - 17*mm, f"{nom}  —  BOQ Structure Beton Arme  —  Ref. Tijan AI")
    canvas.setStrokeColor(GRIS_CLAIR)
    canvas.line(15*mm, h - 19*mm, w - 15*mm, h - 19*mm)
    canvas.line(15*mm, 14*mm, w - 15*mm, 14*mm)
    canvas.setFont('Helvetica', 7)
    canvas.setFillColor(GRIS)
    canvas.drawString(15*mm, 10*mm, f"Tijan AI — {date_str} | Prix estimatifs marche Dakar. A verifier avant usage contractuel.")
    canvas.drawRightString(w - 15*mm, 10*mm, f"Page {doc.page}")
    canvas.restoreState()


def lot_table(data, col_widths):
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), VERT),
        ('TEXTCOLOR', (0,0), (-1,0), BLANC),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.3, GRIS_CLAIR),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [BLANC, FOND]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
    ]))
    return t


def generer_boq(resultats, buf, params_dict=None):
    """Interface principale — résultats v3 → PDF BOQ."""
    params = {}
    if params_dict:
        if hasattr(params_dict, '__dict__'):
            params = {k: v for k, v in vars(params_dict).items() if not k.startswith('_')}
        elif isinstance(params_dict, dict):
            params = params_dict

    date_str = datetime.now().strftime("%d/%m/%Y")
    nom = params.get('nom', 'Projet Tijan')
    ville = params.get('ville', 'Dakar')
    nb_niveaux = params.get('nb_niveaux', len(resultats.poteaux_par_niveau) if resultats.poteaux_par_niveau else 5)
    surface_emprise = params.get('surface_emprise_m2', 500)
    beton = params.get('classe_beton', 'C30/37')
    pression = params.get('pression_sol_MPa', 0.15)
    surface_totale = surface_emprise * nb_niveaux

    bq = resultats.boq
    fd = resultats.fondation
    pt = resultats.poutre_type
    poteaux = resultats.poteaux_par_niveau

    doc = SimpleDocTemplate(buf, pagesize=A4,
        rightMargin=15*mm, leftMargin=15*mm,
        topMargin=25*mm, bottomMargin=20*mm,
        title=f"BOQ Structure — {nom}", author="Tijan AI")

    def hf(canvas, doc):
        build_header_footer(canvas, doc, nom, date_str)

    styles = get_styles()
    story = []

    # ── Page de garde ──
    story.append(Spacer(1, 10*mm))
    story.append(Paragraph("TIJAN AI", styles['brand']))
    story.append(Paragraph("BOQ — BORDEREAU DES QUANTITES ET PRIX", styles['title']))
    story.append(Paragraph("Structure Beton Arme | Fondations | Maconnerie | Etancheite", styles['subtitle']))
    story.append(HRFlowable(width="100%", thickness=1.5, color=VERT))
    story.append(Spacer(1, 6*mm))

    entete = [
        ["Projet", nom],
        ["Localisation", f"{ville.capitalize()}, Senegal"],
        ["Description", f"R+{nb_niveaux-1} — {nb_niveaux} niveaux"],
        ["Surface emprise", f"{surface_emprise:,} m²"],
        ["Surface totale (SHON)", f"{surface_totale:,} m²"],
        ["Beton / Acier", f"{beton} / HA500"],
        ["Date", date_str],
    ]
    t_head = Table(entete, colWidths=[50*mm, 125*mm])
    t_head.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,0), (0,-1), VERT),
        ('GRID', (0,0), (-1,-1), 0.3, GRIS_CLAIR),
        ('BACKGROUND', (0,0), (-1,-1), FOND),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_head)
    story.append(Spacer(1, 6*mm))

    # Note prix acier
    story.append(Paragraph(
        "Prix unitaires : marche Dakar 2024-2025. Acier : LME lamine 680-750 USD/t + transport + "
        "dedouanement + façonnage + marge negoce. Volatilite ±15% — a verifier aupres de CIMAF Senegal, "
        "CFAO Materials, SONACOS avant tout appel d'offres.",
        styles['small']))
    story.append(Spacer(1, 4*mm))

    # ── Synthèse par lot ──
    story.append(Paragraph("SYNTHESE PAR LOT", styles['h2']))

    # Calculs des lots
    V_fond = 0
    if fd and fd.nb_pieux > 0:
        import math
        nb_poteaux = (params.get('nb_travees_x', 4) + 1) * (params.get('nb_travees_y', 3) + 1)
        V_fond = math.pi * (fd.diam_pieu_mm/2000)**2 * fd.longueur_pieu_m * fd.nb_pieux * nb_poteaux

    V_superstructure = bq.beton_total_m3 - V_fond if bq else 500

    lot1_bas = int(surface_emprise * 1.5 * 7500)
    lot1_haut = int(lot1_bas * 1.35)
    lot2_bas = int(V_fond * 185000 + V_fond * 110 * 1850) if V_fond > 0 else int(bq.beton_total_m3 * 0.1 * 185000)
    lot2_haut = int(lot2_bas * 1.25)
    lot3_bas = int(V_superstructure * 185000 + bq.acier_total_kg * 1850) if bq else 0
    lot3_haut = int(lot3_bas * 1.15)
    lot4_bas = int(surface_totale * 8500)
    lot4_haut = int(lot4_bas * 1.45)
    lot5_bas = int(surface_emprise * 2 * 18000 + surface_emprise * 12000)
    lot5_haut = int(lot5_bas * 1.45)
    lot6_bas = int((lot1_bas + lot2_bas + lot3_bas + lot4_bas + lot5_bas) * 0.035)
    lot6_haut = int(lot6_bas * 1.5)
    total_bas = lot1_bas + lot2_bas + lot3_bas + lot4_bas + lot5_bas + lot6_bas
    total_haut = lot1_haut + lot2_haut + lot3_haut + lot4_haut + lot5_haut + lot6_haut

    synthese_data = [
        ["N°", "Lot", "Total bas (FCFA)", "Total haut (FCFA)"],
        ["1", "TERRASSEMENT & INFRASTRUCTURE", f"{lot1_bas:,}", f"{lot1_haut:,}"],
        ["2", "FONDATIONS", f"{lot2_bas:,}", f"{lot2_haut:,}"],
        ["3", "BETON ARME SUPERSTRUCTURE", f"{lot3_bas:,}", f"{lot3_haut:,}"],
        ["4", "COFFRAGES", f"{lot4_bas:,}", f"{lot4_haut:,}"],
        ["5", "MACONNERIE, ENDUITS & ETANCHEITE", f"{lot5_bas:,}", f"{lot5_haut:,}"],
        ["6", "INSTALLATIONS DE CHANTIER & DIVERS", f"{lot6_bas:,}", f"{lot6_haut:,}"],
        ["", "TOTAL GENERAL", f"{total_bas:,}", f"{total_haut:,}"],
    ]
    t_syn = Table(synthese_data, colWidths=[12*mm, 95*mm, 38*mm, 38*mm])
    t_syn.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), VERT),
        ('TEXTCOLOR', (0,0), (-1,0), BLANC),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('GRID', (0,0), (-1,-1), 0.3, GRIS_CLAIR),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [BLANC, FOND]),
        ('BACKGROUND', (0,-1), (-1,-1), VERT_PALE),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,-1), (-1,-1), NOIR),
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_syn)
    story.append(Spacer(1, 4*mm))

    ratio_bas = int(total_bas / surface_totale)
    ratio_haut = int(total_haut / surface_totale)
    verdict = "DANS LA CIBLE" if 100000 <= ratio_bas <= 200000 else "A VERIFIER"
    story.append(Paragraph(
        f"Ratio structure : {ratio_bas:,} – {ratio_haut:,} FCFA/m² (SHON totale = {surface_totale:,} m²) | "
        f"Cible marche Dakar R+{nb_niveaux-1} : 130 000 – 160 000 FCFA/m² — {verdict}",
        styles['small']))
    story.append(PageBreak())

    # ── LOT 2 — Fondations détaillées ──
    story.append(Paragraph("LOT 2 — FONDATIONS", styles['h2']))
    if fd and fd.nb_pieux > 0:
        nb_poteaux = (params.get('nb_travees_x', 4) + 1) * (params.get('nb_travees_y', 3) + 1)
        nb_pieux_total = fd.nb_pieux * nb_poteaux
        L_total = nb_pieux_total * fd.longueur_pieu_m
        kg_arma_pieux = nb_pieux_total * fd.As_cm2 / 100 * fd.longueur_pieu_m * 7850 / 1000

        fond_data = [
            ["N°", "Designation", "Unite", "Quantite", "P.U. bas\n(FCFA)", "Montant bas\n(FCFA)"],
            ["2.1", f"Pieux fores o{fd.diam_pieu_mm}mm L={fd.longueur_pieu_m}m — beton {beton}",
             "ml", f"{L_total:.0f}", "85 000", f"{int(L_total*85000):,}"],
            ["2.2", "Armature longitudinale pieux", "kg", f"{kg_arma_pieux:.0f}", "1 750", f"{int(kg_arma_pieux*1750):,}"],
            ["2.3", f"Longrines BA 40x60cm — beton {beton}", "ml",
             f"{surface_emprise**0.5 * 4:.0f}", "125 000", f"{int(surface_emprise**0.5*4*125000):,}"],
            ["2.4", f"Chapeaux de pieux (1.5x1.5x0.6m) — {nb_poteaux} chapeaux", "m³",
             f"{nb_poteaux*1.5*1.5*0.6:.1f}", "185 000", f"{int(nb_poteaux*1.5*1.5*0.6*185000):,}"],
        ]
    else:
        fond_data = [
            ["N°", "Designation", "Unite", "Quantite", "P.U. bas\n(FCFA)", "Montant bas\n(FCFA)"],
            ["2.1", f"Semelles isolees beton {beton}", "m³", f"{bq.beton_total_m3*0.1:.1f}", "185 000",
             f"{int(bq.beton_total_m3*0.1*185000):,}"],
            ["2.2", "Armatures semelles HA16/12", "kg", f"{bq.acier_total_kg*0.05:.0f}", "1 750",
             f"{int(bq.acier_total_kg*0.05*1750):,}"],
        ]
    story.append(lot_table(fond_data, [12*mm, 80*mm, 15*mm, 20*mm, 25*mm, 28*mm]))
    story.append(Spacer(1, 5*mm))

    # ── LOT 3 — Béton armé superstructure ──
    story.append(Paragraph("LOT 3 — BETON ARME SUPERSTRUCTURE", styles['h2']))

    ba_data = [["N°", "Designation", "Unite", "Quantite", "P.U. bas\n(FCFA)", "Montant bas\n(FCFA)"]]
    i = 1
    for p_obj in poteaux:
        v_beton = (p_obj.section_mm/1000)**2 * 3.0 * (params.get('nb_travees_x',4)+1) * (params.get('nb_travees_y',3)+1)
        kg_acier = v_beton * 100
        ba_data.append([
            f"3.{i}",
            f"Poteaux {p_obj.section_mm}x{p_obj.section_mm}mm — {p_obj.label} — beton {beton}",
            "m³", f"{v_beton:.1f}", "185 000", f"{int(v_beton*185000):,}"
        ])
        i += 1
        ba_data.append([
            f"3.{i}",
            f"Armature poteaux {p_obj.section_mm}x{p_obj.section_mm} — {p_obj.nb_barres}HA{p_obj.diametre_mm}",
            "kg", f"{kg_acier:.0f}", "1 700", f"{int(kg_acier*1700):,}"
        ])
        i += 1

    if pt:
        v_poutres = (pt.b_mm/1000) * (pt.h_mm/1000) * params.get('portee_max_m', 6.0) * \
                    (params.get('nb_travees_x',4) + params.get('nb_travees_y',3)) * nb_niveaux
        kg_poutres = v_poutres * 120
        v_dalles = surface_emprise * 0.22 * nb_niveaux
        kg_dalles = v_dalles * 90

        ba_data += [
            [f"3.{i}", f"Poutres {pt.b_mm}x{pt.h_mm}mm — beton {beton}", "m³",
             f"{v_poutres:.1f}", "185 000", f"{int(v_poutres*185000):,}"],
            [f"3.{i+1}", f"Armature poutres HA12/16/20 + etriers HA{pt.etrier_diam_mm}", "kg",
             f"{kg_poutres:.0f}", "1 650", f"{int(kg_poutres*1650):,}"],
            [f"3.{i+2}", f"Dalles BA ep.22cm — beton {beton}", "m³",
             f"{v_dalles:.1f}", "185 000", f"{int(v_dalles*185000):,}"],
            [f"3.{i+3}", "Treillis soude dalles HA12/150 (2 nappes croisees)", "kg",
             f"{kg_dalles:.0f}", "1 600", f"{int(kg_dalles*1600):,}"],
        ]

    story.append(lot_table(ba_data, [12*mm, 80*mm, 15*mm, 20*mm, 25*mm, 28*mm]))
    story.append(PageBreak())

    # ── RÉCAPITULATIF FINANCIER ──
    story.append(Paragraph("RECAPITULATIF FINANCIER", styles['h2']))

    recap_data = [
        ["Indicateur", "Valeur bas", "Valeur haut", "Commentaire"],
        ["Beton total structure", f"{bq.beton_total_m3:.1f} m³", "—", "Hors beton maigre"],
        ["Acier total structure", f"{bq.acier_total_kg:.0f} kg", f"{bq.acier_total_kg:.0f} kg",
         f"Ratio {bq.acier_total_kg/max(surface_totale,1):.1f} kg/m²"],
        ["Cout structure", f"{total_bas:,} FCFA", f"{total_haut:,} FCFA", "Lots 1 a 6"],
        ["Ratio FCFA/m² SHON", f"{ratio_bas:,}", f"{ratio_haut:,}",
         f"Cible Dakar : 130 000 – 160 000 FCFA/m²"],
        ["Verdict marche", verdict, "—", "Base moteur Eurocodes v3"],
    ]
    t_rec = Table(recap_data, colWidths=[50*mm, 35*mm, 35*mm, 60*mm])
    t_rec.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), VERT),
        ('TEXTCOLOR', (0,0), (-1,0), BLANC),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('GRID', (0,0), (-1,-1), 0.3, GRIS_CLAIR),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [BLANC, FOND]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_rec)
    story.append(Spacer(1, 6*mm))

    # Tableau prix acier référence
    story.append(Paragraph("REFERENTIEL PRIX ACIER — MARCHE DAKAR 2024-2025", styles['h3']))
    acier_data = [
        ["Diametre", "Poids (kg/ml)", "P.U. bas (FCFA/kg)", "P.U. haut (FCFA/kg)", "Usage principal"],
        ["HA8",  "0.395", "1 550", "1 750", "Cadres, etriers secondaires"],
        ["HA10", "0.617", "1 550", "1 750", "Cadres poteaux, repartition"],
        ["HA12", "0.888", "1 600", "1 800", "Dalles, escaliers, longrines"],
        ["HA16", "1.578", "1 650", "1 850", "Poutres, semelles superficielles"],
        ["HA20", "2.466", "1 700", "1 900", "Poteaux niveaux courants"],
        ["HA25", "3.854", "1 750", "1 950", "Poteaux RDC + niveaux bas, pieux"],
        ["HA32", "6.313", "1 800", "2 000", "Poteaux tres fort charges"],
    ]
    story.append(lot_table(acier_data, [15*mm, 25*mm, 30*mm, 30*mm, 75*mm]))
    story.append(Spacer(1, 6*mm))

    # Zone signature
    sig_data = [
        ["Etabli par", "Controle par", "Valide par (BET agree)"],
        ["Tijan AI v3\n\n" + date_str, "________________\n\nDate : ___/___/___", "________________\n\nDate : ___/___/___"],
    ]
    t_sig = Table(sig_data, colWidths=[60*mm, 60*mm, 57*mm])
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
        ('MINROWHEIGHT', (0,1), (-1,1), 20*mm),
    ]))
    story.append(t_sig)
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(
        "Prix estimatifs — marche Dakar 2024-2025. A verifier aupres de CIMAF Senegal, "
        "CFAO Materials, SONACOS avant signature de marche.",
        styles['disclaimer']))

    doc.build(story, onFirstPage=hf, onLaterPages=hf)
