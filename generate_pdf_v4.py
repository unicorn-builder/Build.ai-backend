"""
generate_pdf_v4.py — Note de calcul structurelle Tijan AI
Format A4 paysage, ReportLab Platypus
BOQ avec vrais prix marché Dakar 2026
"""
import io
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.lib.units import mm
from reportlab.lib import colors
from tijan_pdf_theme_v2 import (
    PAGE, CONTENT_W, VERT, NOIR, GRIS1, GRIS2, GRIS3, BLANC, VERT_L,
    STYLES, MARGIN_H, MARGIN_V,
    table_style_base, table_style_total,
    creer_doc, fmt_fcfa, fmt_num, section_header, beta_banner
)
from reportlab.lib.pagesizes import landscape, A4

# ── PRIX MARCHÉ DAKAR 2026 ────────────────────────────────────
PRIX_BETON_DALLE   = 185_000   # FCFA/m³
PRIX_BETON_FOND    = 195_000   # FCFA/m³
PRIX_BETON_POTEAU  = 195_000   # FCFA/m³
PRIX_ACIER_POSE    = 810       # FCFA/kg (fourni + façonné + posé)
PRIX_COFFRAGE      = 18_000    # FCFA/m²
PRIX_PIEU_ML       = 285_000   # FCFA/ml (ø800mm foré)
PRIX_MACO_M2       = 28_000    # FCFA/m²
PRIX_ETANCH_M2     = 18_500    # FCFA/m²
PRIX_TERR_M3       = 8_500     # FCFA/m³
COEFF_STRUCT       = 1.60      # multiplicateur BA → structure complète


def _calcul_boq_complet(resultats):
    """Calcule le BOQ complet structure avec vrais prix Dakar 2026"""
    boq = resultats.get("boq_resume", {})
    params = resultats.get("params", {})

    beton_m3  = boq.get("beton_m3", 0)
    acier_kg  = boq.get("acier_kg", 0)
    surface   = params.get("surface_emprise_m2", 500) if params else 500
    niveaux   = params.get("nb_niveaux", 5) if params else 5

    # Coffrage estimé : 4× volume béton
    coffrage_m2 = beton_m3 * 4

    # Sous-total BA (structure porteuse)
    cout_beton   = beton_m3  * PRIX_BETON_DALLE
    cout_acier   = acier_kg  * PRIX_ACIER_POSE
    cout_coffrage = coffrage_m2 * PRIX_COFFRAGE
    sous_total_ba = cout_beton + cout_acier + cout_coffrage

    # Lots complémentaires
    lot_terr  = round(surface * 1.5 * PRIX_TERR_M3)        # terrassement
    lot_fond  = round(sous_total_ba * 0.22)                 # fondations
    lot_maco  = round(surface * niveaux * 0.15 * PRIX_MACO_M2 / 10)
    lot_etanch = round(surface * PRIX_ETANCH_M2)
    lot_divers = round(sous_total_ba * 0.05)

    total_bas  = round(sous_total_ba + lot_terr + lot_fond + lot_maco + lot_etanch + lot_divers)
    total_haut = round(total_bas * 1.15)  # +15% aléas/révision prix

    surface_batie = surface * niveaux
    ratio_bas  = round(total_bas / surface_batie) if surface_batie else 0
    ratio_haut = round(total_haut / surface_batie) if surface_batie else 0

    return {
        "beton_m3": round(beton_m3),
        "acier_kg": round(acier_kg),
        "coffrage_m2": round(coffrage_m2),
        "cout_beton": cout_beton,
        "cout_acier": cout_acier,
        "cout_coffrage": cout_coffrage,
        "sous_total_ba": sous_total_ba,
        "lot_terrassement": lot_terr,
        "lot_fondations": lot_fond,
        "lot_maconnerie": lot_maco,
        "lot_etancheite": lot_etanch,
        "lot_divers": lot_divers,
        "total_bas": total_bas,
        "total_haut": total_haut,
        "surface_batie_m2": round(surface_batie),
        "ratio_bas_m2": ratio_bas,
        "ratio_haut_m2": ratio_haut,
    }


def generer_note_structure(resultats: dict, params: dict) -> bytes:
    """Génère la note de calcul structure complète en PDF paysage"""
    resultats["params"] = params
    buf = io.BytesIO()

    nom     = params.get("nom", "Projet")
    ville   = params.get("ville", "Dakar")
    nb_niv  = params.get("nb_niveaux", 5)
    surf    = params.get("surface_emprise_m2", 500)
    beton   = params.get("classe_beton", "C30/37")
    acier   = params.get("classe_acier", "HA500")
    portee  = params.get("portee_max_m", 6.0)

    doc, on_page = creer_doc(buf, nom, "Note de Calcul Structure", "STR")

    story = []
    S = STYLES

    # ── PAGE DE GARDE ──────────────────────────────────────────
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph(nom, S['title']))
    story.append(Paragraph(f"{ville} — Bâtiment R+{nb_niv-1}", S['subtitle']))
    story.append(Spacer(1, 2*mm))
    story.append(beta_banner())
    story.append(Spacer(1, 4*mm))

    # Fiche projet
    fiche = [
        [Paragraph("PARAMÈTRE", S['table_header']),
         Paragraph("VALEUR", S['table_header']),
         Paragraph("PARAMÈTRE", S['table_header']),
         Paragraph("VALEUR", S['table_header'])],
        ["Ville", ville, "Classe béton", beton],
        ["Niveaux", f"R+{nb_niv-1} ({nb_niv} niveaux)", "Classe acier", acier],
        ["Surface emprise", f"{surf:,.0f} m²*".replace(',', ' '), "Portée max", f"{portee} m"],
        ["Hauteur étage", f"{params.get('hauteur_etage_m', 3.0)} m",
         "Pression sol", f"{params.get('pression_sol_MPa', 0.15)} MPa"],
    ]
    cw = CONTENT_W / 4
    t = Table(fiche, colWidths=[cw*1.2, cw*0.8, cw*1.2, cw*0.8], repeatRows=1)
    t.setStyle(table_style_base())
    story.append(t)
    story.append(Paragraph("* Surface emprise extraite automatiquement. À confirmer avec l'architecte (marge ±10%).", S['small']))
    story.append(Spacer(1, 3*mm))

    # ── SECTION 1 — DESCENTE DE CHARGES ───────────────────────
    story += section_header("1. DESCENTE DE CHARGES — POTEAUX (EC2/EC8)")

    poteaux = resultats.get("poteaux", [])
    if poteaux:
        cols = ["Niveau", "NEd (kN)", "Section (mm)", "Nb barres",
                "Ø barres (mm)", "Ø cadres (mm)", "Esp. cadres (mm)",
                "Taux arm. (%)", "NRd (kN)", "Vérif."]
        widths = [
            CONTENT_W * w for w in
            [0.07, 0.09, 0.09, 0.07, 0.08, 0.08, 0.10, 0.09, 0.09, 0.07]
        ]

        rows = [[Paragraph(c, S['table_header']) for c in cols]]
        for p in poteaux:
            ok = p.get("verif_ok", True)
            rows.append([
                Paragraph(p.get("label",""), S['table_cell']),
                Paragraph(fmt_num(p.get("NEd_kN",0), 1), S['table_cell_r']),
                Paragraph(f"{p.get('section_mm',0)}×{p.get('section_mm',0)}", S['table_cell_r']),
                Paragraph(str(p.get("nb_barres",0)), S['table_cell_r']),
                Paragraph(str(p.get("diametre_mm",0)), S['table_cell_r']),
                Paragraph(str(p.get("cadre_diam_mm",0)), S['table_cell_r']),
                Paragraph(str(p.get("espacement_cadres_mm",0)), S['table_cell_r']),
                Paragraph(fmt_num(p.get("taux_armature_pct",0), 1), S['table_cell_r']),
                Paragraph(fmt_num(p.get("NRd_kN",0), 1), S['table_cell_r']),
                Paragraph("✓ OK" if ok else "⚠ NOK",
                          S['badge_ok'] if ok else S['badge_warn']),
            ])

        t = Table(rows, colWidths=widths, repeatRows=1)
        ts = table_style_base()
        # Colorier NOK en orange
        for i, p in enumerate(poteaux):
            if not p.get("verif_ok", True):
                ts.add('BACKGROUND', (0, i+1), (-1, i+1),
                       colors.HexColor('#FFF3E0'))
        t.setStyle(ts)
        story.append(t)
    else:
        story.append(Paragraph("Données poteaux non disponibles.", S['body']))

    story.append(Spacer(1, 3*mm))

    # ── SECTION 2 — FONDATIONS ─────────────────────────────────
    story += section_header("2. FONDATIONS")
    fond = resultats.get("fondation", {})
    if fond:
        fdata = [
            [Paragraph("TYPE", S['table_header']),
             Paragraph("QUANTITÉ", S['table_header']),
             Paragraph("DIMENSIONNEMENT", S['table_header']),
             Paragraph("REMARQUE", S['table_header'])],
            [
                Paragraph(fond.get("type_fond", "Pieux forés"), S['table_cell']),
                Paragraph(f"{fond.get('nb_pieux', '-')} pieux", S['table_cell']),
                Paragraph(
                    f"Ø{fond.get('diam_pieu_mm',800)}mm — L={fond.get('longueur_pieu_m',12)}m — "
                    f"As={fond.get('As_cm2',0):.1f} cm²", S['table_cell']),
                Paragraph(
                    f"Pression sol : {params.get('pression_sol_MPa',0.15)} MPa", S['small']),
            ]
        ]
        t = Table(fdata, colWidths=[
            CONTENT_W*0.20, CONTENT_W*0.15,
            CONTENT_W*0.40, CONTENT_W*0.25], repeatRows=1)
        t.setStyle(table_style_base())
        story.append(t)

    story.append(Spacer(1, 3*mm))

    # ── SECTION 3 — ANALYSE CLAUDE ────────────────────────────
    analyse = resultats.get("analyse_claude", {})
    if analyse:
        story += section_header("3. ANALYSE ET RECOMMANDATIONS")
        commentaire = analyse.get("commentaire_global", "")
        if commentaire:
            story.append(Paragraph(commentaire, S['body']))
            story.append(Spacer(1, 2*mm))

        recs = analyse.get("recommandations", [])
        if recs:
            story.append(Paragraph("Recommandations :", S['h2']))
            for r in recs:
                story.append(Paragraph(f"• {r}", S['body']))

        alertes = analyse.get("alertes", [])
        if alertes:
            story.append(Spacer(1, 2*mm))
            story.append(Paragraph("Points d'attention :", S['h2']))
            for a in alertes:
                story.append(Paragraph(f"⚠ {a}", S['badge_warn']))

    # ── PAGE 2 — BOQ STRUCTURE ────────────────────────────────
    story.append(PageBreak())
    story += section_header("4. BORDEREAU DES QUANTITÉS ET DES PRIX — STRUCTURE")
    story.append(Paragraph(
        "Estimation basée sur descente de charges EC2/EC8. "
        "Prix unitaires marché Dakar 2026 (fournis-posés). Marge ±15%.",
        S['small']))
    story.append(Spacer(1, 2*mm))

    boq = _calcul_boq_complet(resultats)

    # Tableau BOQ détaillé
    boq_rows = [
        [Paragraph(h, S['table_header']) for h in
         ["LOT", "DÉSIGNATION", "QUANTITÉ", "UNITÉ",
          "P.U. (FCFA)", "MONTANT BAS (FCFA)", "MONTANT HAUT (FCFA)"]],

        # Lot 1 — Terrassement
        [Paragraph("1", S['table_cell']),
         Paragraph("Terrassement général — décapage + fouilles", S['table_cell']),
         Paragraph(fmt_num(surf * 1.5, 0), S['table_cell_r']),
         Paragraph("m³", S['table_cell']),
         Paragraph(fmt_num(PRIX_TERR_M3, 0), S['table_cell_r']),
         Paragraph(fmt_fcfa(boq['lot_terrassement']), S['table_cell_r']),
         Paragraph(fmt_fcfa(round(boq['lot_terrassement']*1.10)), S['table_cell_r'])],

        # Lot 2 — Fondations
        [Paragraph("2", S['table_cell']),
         Paragraph(f"Fondations spéciales — pieux forés ø800mm", S['table_cell']),
         Paragraph("Forfait", S['table_cell_r']),
         Paragraph("—", S['table_cell']),
         Paragraph("—", S['table_cell_r']),
         Paragraph(fmt_fcfa(boq['lot_fondations']), S['table_cell_r']),
         Paragraph(fmt_fcfa(round(boq['lot_fondations']*1.20)), S['table_cell_r'])],

        # Lot 3 — Béton armé
        [Paragraph("3a", S['table_cell']),
         Paragraph(f"Béton armé — béton C30/37 BPE", S['table_cell']),
         Paragraph(fmt_num(boq['beton_m3'], 0), S['table_cell_r']),
         Paragraph("m³", S['table_cell']),
         Paragraph(fmt_num(PRIX_BETON_DALLE, 0), S['table_cell_r']),
         Paragraph(fmt_fcfa(boq['cout_beton']), S['table_cell_r']),
         Paragraph(fmt_fcfa(round(boq['cout_beton']*1.10)), S['table_cell_r'])],

        [Paragraph("3b", S['table_cell']),
         Paragraph(f"Béton armé — acier HA500B fourni-posé", S['table_cell']),
         Paragraph(fmt_num(boq['acier_kg'], 0), S['table_cell_r']),
         Paragraph("kg", S['table_cell']),
         Paragraph(fmt_num(PRIX_ACIER_POSE, 0), S['table_cell_r']),
         Paragraph(fmt_fcfa(boq['cout_acier']), S['table_cell_r']),
         Paragraph(fmt_fcfa(round(boq['cout_acier']*1.10)), S['table_cell_r'])],

        [Paragraph("3c", S['table_cell']),
         Paragraph("Béton armé — coffrage toutes faces", S['table_cell']),
         Paragraph(fmt_num(boq['coffrage_m2'], 0), S['table_cell_r']),
         Paragraph("m²", S['table_cell']),
         Paragraph(fmt_num(PRIX_COFFRAGE, 0), S['table_cell_r']),
         Paragraph(fmt_fcfa(boq['cout_coffrage']), S['table_cell_r']),
         Paragraph(fmt_fcfa(round(boq['cout_coffrage']*1.10)), S['table_cell_r'])],

        # Lot 4 — Maçonnerie
        [Paragraph("4", S['table_cell']),
         Paragraph("Maçonnerie — agglos 15cm enduits 2 faces", S['table_cell']),
         Paragraph("Forfait", S['table_cell_r']),
         Paragraph("—", S['table_cell']),
         Paragraph("—", S['table_cell_r']),
         Paragraph(fmt_fcfa(boq['lot_maconnerie']), S['table_cell_r']),
         Paragraph(fmt_fcfa(round(boq['lot_maconnerie']*1.15)), S['table_cell_r'])],

        # Lot 5 — Étanchéité
        [Paragraph("5", S['table_cell']),
         Paragraph("Étanchéité toiture-terrasse + sous-sol", S['table_cell']),
         Paragraph(fmt_num(surf, 0), S['table_cell_r']),
         Paragraph("m²", S['table_cell']),
         Paragraph(fmt_num(PRIX_ETANCH_M2, 0), S['table_cell_r']),
         Paragraph(fmt_fcfa(boq['lot_etancheite']), S['table_cell_r']),
         Paragraph(fmt_fcfa(round(boq['lot_etancheite']*1.10)), S['table_cell_r'])],

        # Lot 6 — Divers
        [Paragraph("6", S['table_cell']),
         Paragraph("Divers structure — joints, acrotères, réservations", S['table_cell']),
         Paragraph("Forfait", S['table_cell_r']),
         Paragraph("—", S['table_cell']),
         Paragraph("—", S['table_cell_r']),
         Paragraph(fmt_fcfa(boq['lot_divers']), S['table_cell_r']),
         Paragraph(fmt_fcfa(round(boq['lot_divers']*1.10)), S['table_cell_r'])],

        # TOTAL
        [Paragraph("TOTAL", S['table_cell_bold']),
         Paragraph("COÛT TOTAL STRUCTURE", S['table_cell_bold']),
         Paragraph("", S['table_cell']),
         Paragraph("", S['table_cell']),
         Paragraph("", S['table_cell']),
         Paragraph(fmt_fcfa(boq['total_bas']), S['table_cell_bold']),
         Paragraph(fmt_fcfa(boq['total_haut']), S['table_cell_bold'])],
    ]

    col_w = [
        CONTENT_W * w for w in
        [0.05, 0.30, 0.10, 0.05, 0.13, 0.18, 0.18]
    ]
    t = Table(boq_rows, colWidths=col_w, repeatRows=1)
    ts = table_style_base()
    ts.add('ALIGN', (2,1), (-1,-1), 'RIGHT')
    for cmd in table_style_total():
        ts.add(*cmd)
    t.setStyle(ts)
    story.append(t)

    # Ratios
    story.append(Spacer(1, 3*mm))
    surf_batie = boq['surface_batie_m2']
    ratio_rows = [
        [Paragraph(h, S['table_header']) for h in
         ["INDICATEUR", "VALEUR BASSE", "VALEUR HAUTE", "NOTE"]],
        ["Surface bâtie totale",
         fmt_num(surf_batie, 0, "m²"),
         "—",
         f"Emprise {surf:,.0f} m² × {nb_niv} niveaux*".replace(',', ' ')],
        ["Coût / m² bâti",
         fmt_num(boq['ratio_bas_m2'], 0, "FCFA/m²"),
         fmt_num(boq['ratio_haut_m2'], 0, "FCFA/m²"),
         "Structure seule (hors MEP, finitions, VRD)"],
    ]
    t2 = Table(ratio_rows,
               colWidths=[CONTENT_W*0.25, CONTENT_W*0.20,
                          CONTENT_W*0.20, CONTENT_W*0.35],
               repeatRows=1)
    t2.setStyle(table_style_base())
    story.append(t2)
    story.append(Paragraph(
        "* Surface bâtie = emprise × nb niveaux. "
        "La surface utile habitable est estimée à ~78% de la surface bâtie. "
        "À affiner avec les métrés architecte définitifs.",
        S['small']))

    doc.build(story)
    return buf.getvalue()


# ── POINT D'ENTRÉE BACKEND ────────────────────────────────────
def generer(params: dict) -> bytes:
    """Appelé depuis main.py via get_generateur()"""
    from engine_structural_v3 import DonneesProjet, calculer_projet as calculer
    d = DonneesProjet(
        nom=params.get("nom", "Projet"),
        ville=params.get("ville", "Dakar"),
        nb_niveaux=params.get("nb_niveaux", 5),
        hauteur_etage_m=params.get("hauteur_etage_m", 3.0),
        surface_emprise_m2=params.get("surface_emprise_m2", 500),
        portee_max_m=params.get("portee_max_m", 6.0),
        portee_min_m=params.get("portee_min_m", 4.5),
        nb_travees_x=params.get("nb_travees_x", 4),
        nb_travees_y=params.get("nb_travees_y", 3),
        classe_beton=params.get("classe_beton", "C30/37"),
        classe_acier=params.get("classe_acier", "HA500"),
        pression_sol_MPa=params.get("pression_sol_MPa", 0.15),
    )
    resultats = calculer(d)
    import dataclasses
    res_dict = dataclasses.asdict(resultats) if hasattr(resultats, '__dataclass_fields__') else resultats
    return generer_note_structure(res_dict, params)
