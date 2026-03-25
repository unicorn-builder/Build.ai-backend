"""
generate_plans_v3.py — Planches BA Tijan AI
Plans structurels : coffrage, ferraillage, fondations
Branché directement sur ResultatsCalcul (moteur v3)
Charte : blanc/noir/gris, touches vert #43A956
"""

from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.pdfgen import canvas as pdfcanvas
from datetime import datetime
import math, io

# ── Charte ──
NOIR       = colors.HexColor("#111111")
GRIS_FONCE = colors.HexColor("#555555")
GRIS       = colors.HexColor("#888888")
GRIS_CLAIR = colors.HexColor("#E5E5E5")
FOND       = colors.HexColor("#FAFAFA")
BLANC      = colors.white
VERT       = colors.HexColor("#43A956")
VERT_PALE  = colors.HexColor("#F0FAF1")

W, H = landscape(A3)  # 420 × 297 mm en paysage


# ══════════════════════════════════════════════════════════════
# CARTOUCHE
# ══════════════════════════════════════════════════════════════
def draw_cartouche(c, params, planche_num, planche_titre, date_str, echelle="1/100"):
    """Cartouche en bas à droite — style BET sobre."""
    cw, ch = 110*mm, 35*mm
    cx = W - cw - 10*mm
    cy = 8*mm

    # Fond
    c.setFillColor(BLANC)
    c.setStrokeColor(NOIR)
    c.setLineWidth(0.5)
    c.rect(cx, cy, cw, ch, fill=1, stroke=1)

    # Ligne de séparation verticale
    c.line(cx + 35*mm, cy, cx + 35*mm, cy + ch)

    # Logo/marque
    c.setFillColor(VERT)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(cx + 3*mm, cy + ch - 8*mm, "TIJAN AI")
    c.setFillColor(GRIS_FONCE)
    c.setFont("Helvetica", 6.5)
    c.drawString(cx + 3*mm, cy + ch - 14*mm, "Engineering Intelligence")
    c.drawString(cx + 3*mm, cy + ch - 19*mm, "for Africa")

    # Separateur horizontal gauche
    c.setStrokeColor(GRIS_CLAIR)
    c.line(cx, cy + ch - 22*mm, cx + 35*mm, cy + ch - 22*mm)
    c.setFillColor(GRIS)
    c.setFont("Helvetica", 6)
    c.drawString(cx + 3*mm, cy + 10*mm, f"Ref: TIJAN-STR")
    c.drawString(cx + 3*mm, cy + 5*mm, f"Rev: 0 | {date_str}")

    # Infos droite
    c.setFillColor(NOIR)
    c.setFont("Helvetica-Bold", 8)
    nom = params.get('nom', 'Projet Tijan')[:30]
    c.drawString(cx + 38*mm, cy + ch - 8*mm, nom)

    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(VERT)
    c.drawString(cx + 38*mm, cy + ch - 17*mm, planche_titre)

    c.setFont("Helvetica", 7)
    c.setFillColor(GRIS_FONCE)
    ville = params.get('ville', 'Dakar').capitalize()
    nb_n = params.get('nb_niveaux', 5)
    c.drawString(cx + 38*mm, cy + ch - 24*mm, f"{ville} — R+{nb_n-1}")

    c.setFont("Helvetica", 6.5)
    c.setFillColor(GRIS)
    c.drawString(cx + 38*mm, cy + 14*mm, f"Echelle : {echelle}")
    c.drawString(cx + 38*mm, cy + 8*mm, f"Pl. {planche_num}")
    c.drawString(cx + 38*mm, cy + 3*mm, "A verifier par ingenieur agree")


def draw_border(c):
    """Cadre de planche."""
    c.setStrokeColor(NOIR)
    c.setLineWidth(0.8)
    c.rect(8*mm, 8*mm, W - 16*mm, H - 16*mm, fill=0)
    c.setLineWidth(0.3)
    c.rect(10*mm, 10*mm, W - 20*mm, H - 20*mm, fill=0)


# ══════════════════════════════════════════════════════════════
# PL.1 — PLAN DE COFFRAGE
# ══════════════════════════════════════════════════════════════
def planche_coffrage(c, r, p, date_str):
    c.setPageSize((W, H))
    draw_border(c)

    # Titre
    c.setFillColor(NOIR)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(15*mm, H - 22*mm, "PLAN DE COFFRAGE — NIVEAU COURANT")
    c.setFont("Helvetica", 8)
    c.setFillColor(GRIS_FONCE)
    c.drawString(15*mm, H - 29*mm, "Poteaux, poutres, dalles — Dimensions en mm")
    c.setStrokeColor(GRIS_CLAIR)
    c.line(15*mm, H - 31*mm, W - 130*mm, H - 31*mm)

    # Grille structurelle
    nx = p.get('nb_travees_x', 4) + 1
    ny = p.get('nb_travees_y', 3) + 1
    portee_x = p.get('portee_max_m', 6.0)
    portee_y = p.get('portee_min_m', 4.5)
    echelle = 100

    # Zone dessin
    marge_g = 25*mm
    marge_b = 55*mm
    zone_w = W - marge_g - 130*mm
    zone_h = H - marge_b - 35*mm

    # Calcul du facteur d'échelle
    total_x = nx * portee_x * 1000 / echelle
    total_y = ny * portee_y * 1000 / echelle
    scale_x = zone_w / total_x if total_x > 0 else 1
    scale_y = zone_h / total_y if total_y > 0 else 1
    sc = min(scale_x, scale_y) * 0.85

    ox = marge_g + 10*mm
    oy = marge_b + 10*mm

    # Axes
    labels_x = [chr(65 + i) for i in range(nx)]  # A, B, C...
    labels_y = [str(i + 1) for i in range(ny)]

    # Lignes axes X
    c.setStrokeColor(colors.HexColor("#CCCCCC"))
    c.setDash(3, 2)
    c.setLineWidth(0.3)
    for i in range(nx):
        x = ox + i * portee_x * 1000 / echelle * sc
        c.line(x, oy - 5*mm, x, oy + ny * portee_y * 1000 / echelle * sc + 5*mm)
        # Bulle axe
        c.setDash()
        c.setFillColor(VERT)
        c.circle(x, oy - 8*mm, 4*mm, fill=1, stroke=0)
        c.setFillColor(BLANC)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(x, oy - 9.5*mm, labels_x[i])
        c.setDash(3, 2)

    # Lignes axes Y
    for j in range(ny):
        y = oy + j * portee_y * 1000 / echelle * sc
        c.line(ox - 5*mm, y, ox + nx * portee_x * 1000 / echelle * sc + 5*mm, y)
        c.setDash()
        c.setFillColor(VERT)
        c.circle(ox - 8*mm, y, 4*mm, fill=1, stroke=0)
        c.setFillColor(BLANC)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(ox - 8*mm, y - 1.5*mm, labels_y[j])
        c.setDash(3, 2)

    c.setDash()

    # Poteaux
    rdc = r.poteaux_par_niveau[0] if r.poteaux_par_niveau else None
    section_mm = rdc.section_mm if rdc else 300
    s = section_mm / echelle * sc

    for i in range(nx):
        for j in range(ny):
            x = ox + i * portee_x * 1000 / echelle * sc - s/2
            y = oy + j * portee_y * 1000 / echelle * sc - s/2
            c.setFillColor(colors.HexColor("#CCCCCC"))
            c.setStrokeColor(NOIR)
            c.setLineWidth(0.6)
            c.rect(x, y, s, s, fill=1, stroke=1)
            # Hachures béton (2 lignes diagonales)
            c.setStrokeColor(NOIR)
            c.setLineWidth(0.2)
            c.line(x, y, x + s, y + s)
            c.line(x, y + s, x + s, y)

    # Poutres
    pt = r.poutre_type
    b_mm = pt.b_mm if pt else 250
    h_mm = pt.h_mm if pt else 500
    b = b_mm / echelle * sc

    c.setFillColor(colors.HexColor("#EEEEEE"))
    c.setStrokeColor(NOIR)
    c.setLineWidth(0.4)

    # Poutres horizontales (X)
    for j in range(ny):
        y_p = oy + j * portee_y * 1000 / echelle * sc - b/2
        for i in range(nx - 1):
            x1 = ox + i * portee_x * 1000 / echelle * sc + s/2
            x2 = ox + (i+1) * portee_x * 1000 / echelle * sc - s/2
            c.rect(x1, y_p, x2 - x1, b, fill=1, stroke=1)

    # Poutres verticales (Y)
    for i in range(nx):
        x_p = ox + i * portee_x * 1000 / echelle * sc - b/2
        for j in range(ny - 1):
            y1 = oy + j * portee_y * 1000 / echelle * sc + s/2
            y2 = oy + (j+1) * portee_y * 1000 / echelle * sc - s/2
            c.rect(x_p, y1, b, y2 - y1, fill=1, stroke=1)

    # Cotations portée X
    c.setStrokeColor(NOIR)
    c.setFillColor(NOIR)
    c.setLineWidth(0.3)
    c.setFont("Helvetica", 6)
    y_cote = oy + ny * portee_y * 1000 / echelle * sc + 10*mm
    for i in range(nx - 1):
        x1 = ox + i * portee_x * 1000 / echelle * sc
        x2 = ox + (i+1) * portee_x * 1000 / echelle * sc
        c.line(x1, y_cote - 2*mm, x1, y_cote + 2*mm)
        c.line(x2, y_cote - 2*mm, x2, y_cote + 2*mm)
        c.line(x1, y_cote, x2, y_cote)
        c.drawCentredString((x1+x2)/2, y_cote + 2*mm, f"{portee_x*1000:.0f}")

    # Cotations portée Y
    x_cote = ox + nx * portee_x * 1000 / echelle * sc + 10*mm
    for j in range(ny - 1):
        y1 = oy + j * portee_y * 1000 / echelle * sc
        y2 = oy + (j+1) * portee_y * 1000 / echelle * sc
        c.line(x_cote - 2*mm, y1, x_cote + 2*mm, y1)
        c.line(x_cote - 2*mm, y2, x_cote + 2*mm, y2)
        c.line(x_cote, y1, x_cote, y2)
        c.saveState()
        c.translate(x_cote + 4*mm, (y1+y2)/2)
        c.rotate(90)
        c.drawCentredString(0, 0, f"{portee_y*1000:.0f}")
        c.restoreState()

    # Légende
    lx = W - 125*mm
    ly = H - 80*mm
    c.setFillColor(NOIR)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(lx, ly, "LEGENDE")
    c.setStrokeColor(GRIS_CLAIR)
    c.line(lx, ly - 2*mm, lx + 45*mm, ly - 2*mm)

    items = [
        (colors.HexColor("#CCCCCC"), f"Poteau {section_mm}x{section_mm} mm (RDC)"),
        (colors.HexColor("#EEEEEE"), f"Poutre {b_mm}x{h_mm} mm"),
    ]
    for k, (col, label) in enumerate(items):
        yy = ly - 8*mm - k*7*mm
        c.setFillColor(col)
        c.setStrokeColor(NOIR)
        c.setLineWidth(0.4)
        c.rect(lx, yy, 8*mm, 5*mm, fill=1, stroke=1)
        c.setFillColor(NOIR)
        c.setFont("Helvetica", 6.5)
        c.drawString(lx + 10*mm, yy + 1*mm, label)

    # Note section variable
    c.setFillColor(GRIS_FONCE)
    c.setFont("Helvetica", 6)
    c.drawString(lx, ly - 28*mm, f"Note : sections variables RDC->{r.poteaux_par_niveau[-1].section_mm if r.poteaux_par_niveau else 200}mm (toiture)")

    draw_cartouche(c, p, "1/8", "PLAN DE COFFRAGE", date_str, "1/100")
    c.showPage()


# ══════════════════════════════════════════════════════════════
# PL.2 — FERRAILLAGE POTEAUX
# ══════════════════════════════════════════════════════════════
def planche_ferraillage_poteaux(c, r, p, date_str):
    c.setPageSize((W, H))
    draw_border(c)

    c.setFillColor(NOIR)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(15*mm, H - 22*mm, "FERRAILLAGE POTEAUX — COUPES ET ELEVATIONS")
    c.setFont("Helvetica", 8)
    c.setFillColor(GRIS_FONCE)
    c.drawString(15*mm, H - 29*mm, "Armatures longitudinales et transversales par niveau")
    c.setStrokeColor(GRIS_CLAIR)
    c.line(15*mm, H - 31*mm, W - 130*mm, H - 31*mm)

    poteaux = r.poteaux_par_niveau
    if not poteaux:
        draw_cartouche(c, p, "2/8", "FERRAILLAGE POTEAUX", date_str)
        c.showPage()
        return

    # Dessiner les coupes transversales pour chaque groupe de section
    sections_vues = {}
    for p_obj in poteaux:
        key = (p_obj.section_mm, p_obj.nb_barres, p_obj.diametre_mm)
        if key not in sections_vues:
            sections_vues[key] = p_obj

    n_coupes = len(sections_vues)
    coupe_w = min(60*mm, (W - 160*mm) / max(n_coupes, 1))
    ox = 20*mm
    oy = H - 100*mm

    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(VERT)
    c.drawString(ox, oy + 5*mm, "COUPES TRANSVERSALES")
    c.setStrokeColor(GRIS_CLAIR)
    c.line(ox, oy + 3*mm, ox + 120*mm, oy + 3*mm)

    for idx, (key, p_obj) in enumerate(sections_vues.items()):
        cx_c = ox + idx * (coupe_w + 10*mm) + coupe_w/2
        cy_c = oy - 30*mm
        s = min(45*mm, coupe_w * 0.8)

        # Section béton
        c.setFillColor(colors.HexColor("#F0F0F0"))
        c.setStrokeColor(NOIR)
        c.setLineWidth(0.8)
        c.rect(cx_c - s/2, cy_c - s/2, s, s, fill=1, stroke=1)

        # Hachures béton
        c.setStrokeColor(GRIS)
        c.setLineWidth(0.15)
        pas = 4*mm
        for k in range(-int(s/pas)-1, int(s/pas)+2):
            x1 = cx_c - s/2 + k*pas
            c.line(max(cx_c-s/2, x1), cy_c - s/2 + max(0, -k*pas),
                   min(cx_c+s/2, x1+s), cy_c - s/2 + min(s, s - k*pas))

        # Armatures longitudinales
        nb = p_obj.nb_barres
        d_barre = p_obj.diametre_mm / 1000 * s * 15
        d_barre = max(2*mm, min(5*mm, d_barre))
        enr = 6*mm

        positions = []
        if nb == 4:
            positions = [
                (cx_c - s/2 + enr, cy_c - s/2 + enr),
                (cx_c + s/2 - enr, cy_c - s/2 + enr),
                (cx_c - s/2 + enr, cy_c + s/2 - enr),
                (cx_c + s/2 - enr, cy_c + s/2 - enr),
            ]
        elif nb == 6:
            positions = [
                (cx_c - s/2 + enr, cy_c - s/2 + enr),
                (cx_c, cy_c - s/2 + enr),
                (cx_c + s/2 - enr, cy_c - s/2 + enr),
                (cx_c - s/2 + enr, cy_c + s/2 - enr),
                (cx_c, cy_c + s/2 - enr),
                (cx_c + s/2 - enr, cy_c + s/2 - enr),
            ]
        else:
            n_side = nb // 4
            for si in range(4):
                for ki in range(n_side):
                    t = ki / max(n_side - 1, 1)
                    if si == 0: px, py = cx_c - s/2 + enr, cy_c - s/2 + enr + t*(s - 2*enr)
                    elif si == 1: px, py = cx_c + s/2 - enr, cy_c - s/2 + enr + t*(s - 2*enr)
                    elif si == 2: px, py = cx_c - s/2 + enr + t*(s - 2*enr), cy_c - s/2 + enr
                    else: px, py = cx_c - s/2 + enr + t*(s - 2*enr), cy_c + s/2 - enr
                    positions.append((px, py))

        c.setFillColor(NOIR)
        c.setStrokeColor(BLANC)
        c.setLineWidth(0.3)
        for (px, py) in positions[:nb]:
            c.circle(px, py, d_barre/2, fill=1, stroke=1)

        # Cadre
        c.setStrokeColor(NOIR)
        c.setLineWidth(0.4)
        c.setFillColor(colors.Color(0, 0, 0, 0))
        c.rect(cx_c - s/2 + 4*mm, cy_c - s/2 + 4*mm, s - 8*mm, s - 8*mm, fill=0, stroke=1)

        # Annotations
        c.setFillColor(NOIR)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(cx_c, cy_c - s/2 - 6*mm, f"{p_obj.section_mm}x{p_obj.section_mm}")
        c.setFont("Helvetica", 6.5)
        c.drawCentredString(cx_c, cy_c - s/2 - 11*mm, f"{p_obj.nb_barres}HA{p_obj.diametre_mm}")
        c.setFillColor(GRIS_FONCE)
        c.drawCentredString(cx_c, cy_c - s/2 - 16*mm, p_obj.label)

    # Tableau récapitulatif
    ty = oy - 90*mm
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(VERT)
    c.drawString(ox, ty + 5*mm, "TABLEAU DES SECTIONS PAR NIVEAU")
    c.setStrokeColor(GRIS_CLAIR)
    c.line(ox, ty + 3*mm, ox + 150*mm, ty + 3*mm)

    # En-tête tableau
    headers = ["Niveau", "NEd (kN)", "Section (mm)", "Long.", "Cadres", "Taux (%)"]
    col_w_t = [25*mm, 28*mm, 32*mm, 28*mm, 28*mm, 22*mm]
    x_cols = [ox]
    for w in col_w_t[:-1]:
        x_cols.append(x_cols[-1] + w)

    row_h = 7*mm
    ty_r = ty - 5*mm

    # Header
    c.setFillColor(VERT)
    c.rect(ox, ty_r, sum(col_w_t), row_h, fill=1, stroke=0)
    c.setFillColor(BLANC)
    c.setFont("Helvetica-Bold", 7)
    for i, (hdr, xc) in enumerate(zip(headers, x_cols)):
        c.drawString(xc + 2*mm, ty_r + 2*mm, hdr)

    # Lignes
    for row_i, p_obj in enumerate(poteaux):
        row_y = ty_r - (row_i + 1) * row_h
        bg = BLANC if row_i % 2 == 0 else FOND
        c.setFillColor(bg)
        c.rect(ox, row_y, sum(col_w_t), row_h, fill=1, stroke=0)
        c.setStrokeColor(GRIS_CLAIR)
        c.setLineWidth(0.2)
        c.line(ox, row_y, ox + sum(col_w_t), row_y)

        cadre_d = 10 if p_obj.section_mm > 300 else 8
        esp = min(20 * p_obj.diametre_mm, p_obj.section_mm, 400)
        esp = (esp // 25) * 25

        vals = [
            p_obj.label,
            f"{p_obj.NEd_kN:.0f}",
            f"{p_obj.section_mm}x{p_obj.section_mm}",
            f"{p_obj.nb_barres}HA{p_obj.diametre_mm}",
            f"HA{cadre_d}/{esp}",
            f"{p_obj.taux_armature_pct:.2f}%",
        ]
        c.setFillColor(NOIR)
        c.setFont("Helvetica", 7)
        for i, (val, xc) in enumerate(zip(vals, x_cols)):
            c.drawString(xc + 2*mm, row_y + 2*mm, val)

    draw_cartouche(c, p, "2/8", "FERRAILLAGE POTEAUX", date_str)
    c.showPage()


# ══════════════════════════════════════════════════════════════
# PL.3 — FERRAILLAGE POUTRES
# ══════════════════════════════════════════════════════════════
def planche_ferraillage_poutres(c, r, p, date_str):
    c.setPageSize((W, H))
    draw_border(c)

    c.setFillColor(NOIR)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(15*mm, H - 22*mm, "FERRAILLAGE POUTRES — COUPE ET ELEVATION")
    c.setFont("Helvetica", 8)
    c.setFillColor(GRIS_FONCE)
    c.drawString(15*mm, H - 29*mm, "Armatures inferieures, superieures et etriers")
    c.setStrokeColor(GRIS_CLAIR)
    c.line(15*mm, H - 31*mm, W - 130*mm, H - 31*mm)

    pt = r.poutre_type
    if not pt:
        draw_cartouche(c, p, "3/8", "FERRAILLAGE POUTRES", date_str)
        c.showPage()
        return

    portee = p.get('portee_max_m', 6.0)
    echelle = 50
    ox = 25*mm
    oy = H - 120*mm

    # ── Coupe transversale ──
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(VERT)
    c.drawString(ox, oy + 5*mm, "COUPE A-A")

    b = pt.b_mm / echelle * mm
    h = pt.h_mm / echelle * mm
    cx_p = ox + 40*mm
    cy_p = oy - h

    c.setFillColor(colors.HexColor("#F0F0F0"))
    c.setStrokeColor(NOIR)
    c.setLineWidth(0.8)
    c.rect(cx_p, cy_p, b, h, fill=1, stroke=1)

    # Hachures
    c.setStrokeColor(GRIS)
    c.setLineWidth(0.15)
    for k in range(-int(h/4/mm), int((b+h)/4/mm)+2):
        x1 = cx_p + k*4*mm
        c.line(max(cx_p, x1), cy_p + max(0, -k*4*mm),
               min(cx_p+b, x1+h), cy_p + min(h, h-k*4*mm))

    # Armatures inférieures
    n_inf = max(2, round(pt.As_inf_cm2 / (math.pi * 8**2 / 4 / 100)))
    n_inf = min(n_inf, 6)
    d_b = 4*mm
    enr = 6*mm
    spacing_inf = (b - 2*enr) / max(n_inf - 1, 1)
    c.setFillColor(NOIR)
    for k in range(n_inf):
        bx = cx_p + enr + k * spacing_inf
        by = cy_p + enr
        c.circle(bx, by, d_b/2, fill=1, stroke=0)

    # Armatures supérieures
    n_sup = max(2, round(pt.As_sup_cm2 / (math.pi * 8**2 / 4 / 100)))
    n_sup = min(n_sup, 6)
    for k in range(n_sup):
        bx = cx_p + enr + k * (b - 2*enr) / max(n_sup - 1, 1)
        by = cy_p + h - enr
        c.circle(bx, by, d_b/2, fill=1, stroke=0)

    # Cotations section
    c.setStrokeColor(NOIR)
    c.setFillColor(NOIR)
    c.setLineWidth(0.3)
    c.setFont("Helvetica", 6)
    c.drawCentredString(cx_p + b/2, cy_p - 5*mm, f"b = {pt.b_mm} mm")
    c.saveState()
    c.translate(cx_p - 6*mm, cy_p + h/2)
    c.rotate(90)
    c.drawCentredString(0, 0, f"h = {pt.h_mm} mm")
    c.restoreState()

    # ── Élévation longitudinale ──
    echelle_el = 100
    ox_el = ox + 80*mm
    L = portee * 1000 / echelle_el * mm
    b_el = pt.b_mm / echelle_el * mm * 3
    h_el = pt.h_mm / echelle_el * mm * 3

    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(VERT)
    c.drawString(ox_el, oy + 5*mm, "ELEVATION — COUPE LONGITUDINALE")

    cy_el = oy - h_el
    c.setFillColor(colors.HexColor("#F0F0F0"))
    c.setStrokeColor(NOIR)
    c.setLineWidth(0.6)
    c.rect(ox_el, cy_el, L, h_el, fill=1, stroke=1)

    # Armatures longit. inf
    enr_el = 5*mm
    c.setFillColor(NOIR)
    c.setLineWidth(1.2)
    c.setStrokeColor(NOIR)
    c.line(ox_el + enr_el, cy_el + enr_el, ox_el + L - enr_el, cy_el + enr_el)
    c.line(ox_el + enr_el, cy_el + h_el - enr_el, ox_el + L - enr_el, cy_el + h_el - enr_el)

    # Étriers
    c.setLineWidth(0.5)
    esp_et = pt.etrier_esp_mm / echelle_el * mm * 3
    nb_et = int(L / esp_et)
    for k in range(nb_et + 1):
        x_et = ox_el + k * esp_et
        if x_et <= ox_el + L:
            c.rect(x_et + 1*mm, cy_el + 2*mm, esp_et * 0.6, h_el - 4*mm, fill=0, stroke=1)

    # Cotations
    c.setFont("Helvetica", 6)
    c.setFillColor(NOIR)
    c.setLineWidth(0.3)
    c.line(ox_el, cy_el - 5*mm, ox_el + L, cy_el - 5*mm)
    c.drawCentredString(ox_el + L/2, cy_el - 8*mm, f"L = {portee*1000:.0f} mm")

    # Annotations armatures
    c.setFont("Helvetica", 6.5)
    c.drawString(ox_el + 2*mm, cy_el + enr_el + 2*mm, f"{n_inf}HA{round(math.sqrt(pt.As_inf_cm2*100/n_inf/math.pi)*2)}")
    c.drawString(ox_el + 2*mm, cy_el + h_el - enr_el - 6*mm, f"{n_sup}HA{round(math.sqrt(pt.As_sup_cm2*100/n_sup/math.pi)*2)}")
    c.drawString(ox_el + L/2, cy_el + h_el/2, f"HA{pt.etrier_diam_mm}/{pt.etrier_esp_mm}")

    # Tableau récap poutre
    ty = cy_el - 30*mm
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(VERT)
    c.drawString(ox, ty + 3*mm, "CARACTERISTIQUES POUTRE TYPE")

    data = [
        ["Section", f"{pt.b_mm} x {pt.h_mm} mm"],
        ["As inferieur (travee)", f"{pt.As_inf_cm2} cm² — {n_inf} barres"],
        ["As superieur (appuis)", f"{pt.As_sup_cm2} cm² — {n_sup} barres"],
        ["Etriers", f"HA{pt.etrier_diam_mm} / {pt.etrier_esp_mm} mm"],
        ["Portee de calcul", f"{portee} m"],
        ["Beton", p.get('classe_beton', 'C30/37')],
    ]
    for k, (label, val) in enumerate(data):
        y_row = ty - k * 7*mm
        c.setFillColor(FOND if k % 2 == 0 else BLANC)
        c.rect(ox, y_row - 5*mm, 130*mm, 6*mm, fill=1, stroke=0)
        c.setStrokeColor(GRIS_CLAIR)
        c.setLineWidth(0.2)
        c.line(ox, y_row - 5*mm, ox + 130*mm, y_row - 5*mm)
        c.setFillColor(VERT)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(ox + 2*mm, y_row - 3*mm, label)
        c.setFillColor(NOIR)
        c.setFont("Helvetica", 7)
        c.drawString(ox + 55*mm, y_row - 3*mm, val)

    draw_cartouche(c, p, "3/8", "FERRAILLAGE POUTRES", date_str)
    c.showPage()


# ══════════════════════════════════════════════════════════════
# PL.4 — PLAN DE FONDATIONS
# ══════════════════════════════════════════════════════════════
def planche_fondations(c, r, p, date_str):
    c.setPageSize((W, H))
    draw_border(c)

    c.setFillColor(NOIR)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(15*mm, H - 22*mm, "PLAN DE FONDATIONS — PIEUX ET LONGRINES")
    c.setFont("Helvetica", 8)
    c.setFillColor(GRIS_FONCE)
    c.drawString(15*mm, H - 29*mm, "Implantation des pieux et longrines de liaison")
    c.setStrokeColor(GRIS_CLAIR)
    c.line(15*mm, H - 31*mm, W - 130*mm, H - 31*mm)

    fd = r.fondation
    nx = p.get('nb_travees_x', 4) + 1
    ny = p.get('nb_travees_y', 3) + 1
    portee_x = p.get('portee_max_m', 6.0)
    portee_y = p.get('portee_min_m', 4.5)
    echelle = 100

    marge_g = 25*mm
    marge_b = 55*mm
    zone_w = W - marge_g - 130*mm
    zone_h = H - marge_b - 35*mm
    total_x = nx * portee_x * 1000 / echelle
    total_y = ny * portee_y * 1000 / echelle
    sc = min(zone_w/total_x, zone_h/total_y) * 0.85
    ox = marge_g + 10*mm
    oy = marge_b + 10*mm

    # Longrines
    c.setStrokeColor(colors.HexColor("#AAAAAA"))
    c.setLineWidth(2.5)
    for j in range(ny):
        y_l = oy + j * portee_y * 1000 / echelle * sc
        c.line(ox, y_l, ox + (nx-1) * portee_x * 1000 / echelle * sc, y_l)
    for i in range(nx):
        x_l = ox + i * portee_x * 1000 / echelle * sc
        c.line(x_l, oy, x_l, oy + (ny-1) * portee_y * 1000 / echelle * sc)

    # Chapeaux de pieux
    if fd and fd.nb_pieux > 0:
        nb_p = fd.nb_pieux
        diam_affiche = fd.diam_pieu_mm / echelle * sc
        offset = 600 / echelle * sc  # offset ±600mm des pieux

        for i in range(nx):
            for j in range(ny):
                cx_fond = ox + i * portee_x * 1000 / echelle * sc
                cy_fond = oy + j * portee_y * 1000 / echelle * sc

                # Chapeau
                cap_size = (fd.diam_pieu_mm * 2.5) / echelle * sc
                c.setFillColor(colors.HexColor("#E8E8E8"))
                c.setStrokeColor(NOIR)
                c.setLineWidth(0.6)
                c.rect(cx_fond - cap_size/2, cy_fond - cap_size/2,
                       cap_size, cap_size, fill=1, stroke=1)

                # Pieux
                offsets_4 = [(-offset, -offset), (offset, -offset),
                              (-offset, offset), (offset, offset)]
                offsets_2 = [(-offset, 0), (offset, 0)]
                positions = offsets_4 if nb_p >= 4 else offsets_2

                c.setFillColor(NOIR)
                c.setStrokeColor(BLANC)
                c.setLineWidth(0.2)
                for (dx, dy) in positions[:nb_p]:
                    c.circle(cx_fond + dx, cy_fond + dy,
                             diam_affiche/2, fill=1, stroke=1)

        # Annotation
        c.setFillColor(NOIR)
        c.setFont("Helvetica", 6.5)
        sample_x = ox + portee_x * 1000 / echelle * sc
        sample_y = oy
        c.drawString(sample_x + 3*mm, sample_y + 3*mm,
                     f"o{fd.diam_pieu_mm} L={fd.longueur_pieu_m}m")
    else:
        # Semelles
        for i in range(nx):
            for j in range(ny):
                cx_s = ox + i * portee_x * 1000 / echelle * sc
                cy_s = oy + j * portee_y * 1000 / echelle * sc
                sem_size = 1500 / echelle * sc
                c.setFillColor(colors.HexColor("#E8E8E8"))
                c.setStrokeColor(NOIR)
                c.setLineWidth(0.6)
                c.rect(cx_s - sem_size/2, cy_s - sem_size/2,
                       sem_size, sem_size, fill=1, stroke=1)

    # Axes
    labels_x = [chr(65 + i) for i in range(nx)]
    for i in range(nx):
        x = ox + i * portee_x * 1000 / echelle * sc
        c.setFillColor(VERT)
        c.circle(x, oy - 8*mm, 4*mm, fill=1, stroke=0)
        c.setFillColor(BLANC)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(x, oy - 9.5*mm, labels_x[i])

    for j in range(ny):
        y = oy + j * portee_y * 1000 / echelle * sc
        c.setFillColor(VERT)
        c.circle(ox - 8*mm, y, 4*mm, fill=1, stroke=0)
        c.setFillColor(BLANC)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(ox - 8*mm, y - 1.5*mm, str(j+1))

    # Tableau fondation
    lx = W - 125*mm
    ly = H - 60*mm
    c.setFillColor(VERT)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(lx, ly, "FONDATIONS")
    c.setStrokeColor(GRIS_CLAIR)
    c.line(lx, ly - 2*mm, lx + 60*mm, ly - 2*mm)

    if fd:
        infos = [
            ("Type", fd.type_fond),
            ("Diametre", f"o{fd.diam_pieu_mm} mm" if fd.nb_pieux > 0 else f"{getattr(fd,'section_semelle_m',1.5)} m"),
            ("Longueur", f"{fd.longueur_pieu_m} m" if fd.nb_pieux > 0 else "—"),
            ("Nb/poteau", str(fd.nb_pieux) if fd.nb_pieux > 0 else "1"),
            ("Armatures", f"{fd.As_cm2} cm²"),
            ("Beton", p.get('classe_beton', 'C30/37')),
        ]
        for k, (lbl, val) in enumerate(infos):
            yy = ly - 7*mm - k*6*mm
            c.setFillColor(GRIS_FONCE)
            c.setFont("Helvetica-Bold", 6.5)
            c.drawString(lx, yy, lbl + " :")
            c.setFillColor(NOIR)
            c.setFont("Helvetica", 6.5)
            c.drawString(lx + 22*mm, yy, val[:25])

    draw_cartouche(c, p, "4/8", "PLAN DE FONDATIONS", date_str)
    c.showPage()


# ══════════════════════════════════════════════════════════════
# PL.5-8 — PLANCHES SUPPLÉMENTAIRES (tableau façonnage, dalle, etc.)
# ══════════════════════════════════════════════════════════════
def planche_facade_acrotere(c, r, p, date_str, pl_num, pl_titre):
    """Planche générique pour façades/acrotères/escaliers."""
    c.setPageSize((W, H))
    draw_border(c)

    c.setFillColor(NOIR)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(15*mm, H - 22*mm, pl_titre.upper())
    c.setFont("Helvetica", 8)
    c.setFillColor(GRIS_FONCE)
    c.drawString(15*mm, H - 29*mm, "Note de calcul structurelle — Tijan AI")
    c.setStrokeColor(GRIS_CLAIR)
    c.line(15*mm, H - 31*mm, W - 130*mm, H - 31*mm)

    # Élévation façade schématique
    nb_n = p.get('nb_niveaux', 5)
    hauteur = p.get('hauteur_etage_m', 3.0)
    portee_x = p.get('portee_max_m', 6.0)
    echelle = 100
    ox = 30*mm
    oy = 50*mm
    h_etage = hauteur * 1000 / echelle * mm * 0.8
    L_facade = portee_x * 2 * 1000 / echelle * mm * 0.8

    # Dessiner les niveaux
    poteaux = r.poteaux_par_niveau
    for etage in range(nb_n):
        y_etage = oy + etage * h_etage
        # Dalle
        c.setFillColor(colors.HexColor("#DDDDDD"))
        c.setStrokeColor(NOIR)
        c.setLineWidth(0.4)
        c.rect(ox, y_etage, L_facade, 3*mm, fill=1, stroke=1)
        # Poteaux
        p_obj = poteaux[min(nb_n - 1 - etage, len(poteaux)-1)] if poteaux else None
        s = (p_obj.section_mm if p_obj else 300) / echelle * mm * 0.8
        c.setFillColor(colors.HexColor("#BBBBBB"))
        c.rect(ox - s/2, y_etage + 3*mm, s, h_etage - 3*mm, fill=1, stroke=1)
        c.rect(ox + L_facade/2 - s/2, y_etage + 3*mm, s, h_etage - 3*mm, fill=1, stroke=1)
        c.rect(ox + L_facade - s/2, y_etage + 3*mm, s, h_etage - 3*mm, fill=1, stroke=1)
        # Label niveau
        c.setFont("Helvetica", 6)
        c.setFillColor(GRIS_FONCE)
        label = "RDC" if etage == 0 else (f"N{etage}" if etage < nb_n-1 else "Toiture")
        c.drawString(ox - 15*mm, y_etage + h_etage/2, label)
        # Cote hauteur
        c.setStrokeColor(GRIS)
        c.setLineWidth(0.2)
        c.line(ox + L_facade + 5*mm, y_etage, ox + L_facade + 5*mm, y_etage + h_etage)
        c.drawString(ox + L_facade + 7*mm, y_etage + h_etage/2 - 2*mm, f"{hauteur*1000:.0f}")

    # Acrotère
    y_top = oy + nb_n * h_etage
    c.setFillColor(colors.HexColor("#999999"))
    c.rect(ox - 3*mm, y_top, 6*mm, 8*mm, fill=1, stroke=1)
    c.rect(ox + L_facade - 3*mm, y_top, 6*mm, 8*mm, fill=1, stroke=1)
    c.setFont("Helvetica", 6)
    c.setFillColor(GRIS_FONCE)
    c.drawString(ox + L_facade/2 - 10*mm, y_top + 5*mm, "Acrotere h=1.0m")

    draw_cartouche(c, p, pl_num, pl_titre, date_str)
    c.showPage()


def planche_tableau_faconnage(c, r, p, date_str):
    """Pl.5 — Tableau de façonnage des armatures."""
    c.setPageSize((W, H))
    draw_border(c)

    c.setFillColor(NOIR)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(15*mm, H - 22*mm, "TABLEAU DE FACONNAGE — ARMATURES")
    c.setFont("Helvetica", 8)
    c.setFillColor(GRIS_FONCE)
    c.drawString(15*mm, H - 29*mm, "Nomenclature des barres — longueurs developpees")
    c.setStrokeColor(GRIS_CLAIR)
    c.line(15*mm, H - 31*mm, W - 130*mm, H - 31*mm)

    # En-tête tableau
    ox = 15*mm
    oy = H - 50*mm
    headers = ["Repere", "Type", "Diam.", "Nb total", "Long. coupe (mm)", "Long. dev. (mm)", "Masse (kg)", "Usage"]
    col_widths = [20*mm, 35*mm, 15*mm, 20*mm, 35*mm, 35*mm, 25*mm, 50*mm]

    # Header fond vert
    c.setFillColor(VERT)
    c.rect(ox, oy, sum(col_widths), 8*mm, fill=1, stroke=0)
    c.setFillColor(BLANC)
    c.setFont("Helvetica-Bold", 7)
    x_cur = ox
    for hdr, cw in zip(headers, col_widths):
        c.drawString(x_cur + 2*mm, oy + 2.5*mm, hdr)
        x_cur += cw

    # Lignes de données
    poteaux = r.poteaux_par_niveau
    pt = r.poutre_type
    nb_travees_x = p.get('nb_travees_x', 4)
    nb_travees_y = p.get('nb_travees_y', 3)
    nb_poteaux = (nb_travees_x + 1) * (nb_travees_y + 1)
    hauteur = p.get('hauteur_etage_m', 3.0)

    rows = []
    repere = 1
    for p_obj in poteaux:
        L_dev = int(hauteur * 1000 + 2 * 40 * p_obj.diametre_mm)
        masse = p_obj.nb_barres * math.pi * (p_obj.diametre_mm/2)**2 / 1e6 * 7850 * hauteur * nb_poteaux
        rows.append([
            str(repere), f"Long. poteau {p_obj.label}", f"HA{p_obj.diametre_mm}",
            str(p_obj.nb_barres * nb_poteaux),
            str(int(hauteur * 1000)), str(L_dev),
            f"{masse:.0f}", f"Poteaux {p_obj.label}"
        ])
        repere += 1

        # Cadres
        per_cadre = 2 * (p_obj.section_mm + p_obj.section_mm) + 8 * 10
        nb_cadres = int(hauteur * 1000 / p_obj.cadre_diam_mm) * nb_poteaux
        masse_c = nb_cadres * per_cadre / 1000 * math.pi * (p_obj.cadre_diam_mm/2)**2 / 1e6 * 7850 * 1000
        rows.append([
            str(repere), f"Cadre poteau {p_obj.label}", f"HA{p_obj.cadre_diam_mm}",
            str(nb_cadres), str(per_cadre), str(per_cadre + 100),
            f"{masse_c:.0f}", f"Cadres {p_obj.label}"
        ])
        repere += 1

    if pt:
        portee = p.get('portee_max_m', 6.0)
        nb_poutres = (nb_travees_x + nb_travees_y) * len(poteaux)
        masse_inf = pt.As_inf_cm2 / 100 * portee * 7850 * nb_poutres / 1000
        rows.append([
            str(repere), "Long. poutre inf.", f"HA{round(math.sqrt(pt.As_inf_cm2*100/4/math.pi)*2)}",
            str(int(nb_poutres * 4)),
            str(int(portee * 1000)), str(int(portee * 1000 + 1200)),
            f"{masse_inf:.0f}", "Armatures inf. poutres"
        ])
        repere += 1

    for row_i, row in enumerate(rows[:20]):
        row_y = oy - (row_i + 1) * 7*mm
        c.setFillColor(BLANC if row_i % 2 == 0 else FOND)
        c.rect(ox, row_y, sum(col_widths), 7*mm, fill=1, stroke=0)
        c.setStrokeColor(GRIS_CLAIR)
        c.setLineWidth(0.2)
        c.line(ox, row_y, ox + sum(col_widths), row_y)
        x_cur = ox
        c.setFillColor(NOIR)
        c.setFont("Helvetica", 6.5)
        for val, cw in zip(row, col_widths):
            c.drawString(x_cur + 2*mm, row_y + 2*mm, str(val)[:20])
            x_cur += cw

    draw_cartouche(c, p, "5/8", "TABLEAU DE FACONNAGE", date_str)
    c.showPage()


# ══════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE
# ══════════════════════════════════════════════════════════════
def generer_dossier_ba(output_path: str, resultats=None, params: dict = None):
    """
    Génère le dossier BA complet — 8 planches A3 paysage.
    output_path : chemin du PDF de sortie
    resultats : ResultatsCalcul (moteur v3)
    params : dict des paramètres projet
    """
    if params is None:
        params = {}
    if hasattr(params, '__dict__'):
        params = {k: v for k, v in vars(params).items() if not k.startswith('_')}

    date_str = datetime.now().strftime("%d/%m/%Y")

    c = pdfcanvas.Canvas(output_path, pagesize=landscape(A3))
    c.setTitle(f"Dossier BA — {params.get('nom', 'Projet Tijan')}")
    c.setAuthor("Tijan AI")

    if resultats is None:
        # Mode demo sans résultats
        from dataclasses import dataclass, field as dc_field
        from typing import List, Optional

        @dataclass
        class _RP:
            label: str = "RDC"; niveau: int = 0; NEd_kN: float = 1000
            section_mm: int = 300; nb_barres: int = 4; diametre_mm: int = 20
            cadre_diam_mm: int = 10; espacement_cadres_mm: int = 200
            taux_armature_pct: float = 1.5; NRd_kN: float = 1500; verif_ok: bool = True

        @dataclass
        class _RT:
            b_mm: int = 250; h_mm: int = 500; As_inf_cm2: float = 10.0
            As_sup_cm2: float = 12.0; etrier_diam_mm: int = 8; etrier_esp_mm: int = 200
            portee_m: float = 5.5

        @dataclass
        class _RF:
            type_fond: str = "Pieux fores"; nb_pieux: int = 4
            diam_pieu_mm: int = 800; longueur_pieu_m: float = 10.0
            As_cm2: float = 25.0; section_semelle_m: Optional[float] = None

        @dataclass
        class _RB:
            beton_total_m3: float = 500; acier_total_kg: float = 50000
            cout_total_bas: int = 500_000_000; cout_total_haut: int = 600_000_000
            ratio_fcfa_m2: int = 130_000; detail_lots: dict = dc_field(default_factory=dict)

        @dataclass
        class _RC:
            poteaux_par_niveau: List = dc_field(default_factory=lambda: [_RP()])
            poutre_type: _RT = dc_field(default_factory=_RT)
            fondation: _RF = dc_field(default_factory=_RF)
            boq: _RB = dc_field(default_factory=_RB)

        resultats = _RC()

    planche_coffrage(c, resultats, params, date_str)
    planche_ferraillage_poteaux(c, resultats, params, date_str)
    planche_ferraillage_poutres(c, resultats, params, date_str)
    planche_fondations(c, resultats, params, date_str)
    planche_tableau_faconnage(c, resultats, params, date_str)
    planche_facade_acrotere(c, resultats, params, date_str, "6/8", "Dalle et escaliers")
    planche_facade_acrotere(c, resultats, params, date_str, "7/8", "Facades et acroteres")
    planche_facade_acrotere(c, resultats, params, date_str, "8/8", "Details constructifs")

    c.save()
    return output_path


def generer_planches(resultats, output_path: str, params: dict = None):
    """Alias pour compatibilité main.py."""
    return generer_dossier_ba(output_path, resultats, params)
