"""
generate_plans_v4.py — Dossier BA Tijan AI
8 planches structure niveau BET sénégalais (format Innov' Structures)
Branché sur ResultatsStructure (moteur v2)

Planches :
  1. Plan de coffrage — grille 2D, poteaux, poutres, dalles (A3 paysage)
  2. Ferraillage poteaux — coupes + tableau sections par niveau (A4 portrait)
  3. Ferraillage poutre principale — élévation + coupe A-A + tableau (A4 portrait)
  4. Ferraillage poutre secondaire — idem (A4 portrait)
  5. Plan de fondations — pieux/semelles + longrines en plan (A3 paysage)
  6. Ferraillage longrines type — élévation + coupe + tableau (A4 portrait)
  7. Tableau de façonnage — nomenclature complète aciers (A4 portrait)
  8. Coupe générale bâtiment — élévation avec niveaux (A3 paysage)

Charte Tijan : fond blanc, traits noirs, texte gris foncé, accents vert #43A956
"""

import math
import os
from datetime import datetime
from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.pdfgen import canvas as pdfcanvas

# ══════════════════════════════════════════════════════════
# CHARTE GRAPHIQUE
# ══════════════════════════════════════════════════════════
NOIR = colors.HexColor("#111111")
GRIS_FONCE = colors.HexColor("#555555")
GRIS = colors.HexColor("#888888")
GRIS_CLAIR = colors.HexColor("#CCCCCC")
GRIS_TRES_CLAIR = colors.HexColor("#E8E8E8")
BLANC = colors.white
VERT = colors.HexColor("#43A956")
VERT_PALE = colors.HexColor("#E8F5E9")
ROUGE_ACIER = colors.HexColor("#CC3333")
BLEU_BETON = colors.HexColor("#D6E4F0")

A3L = landscape(A3)  # 420 × 297 mm
A4P = A4              # 210 × 297 mm


# ══════════════════════════════════════════════════════════
# CARTOUCHE BET
# ══════════════════════════════════════════════════════════
def draw_cartouche(c, w, h, params, titre_planche, page_num, total_pages,
                   echelle="1/100", lot="STR"):
    """Cartouche BET professionnel en bas de page."""
    cw = 180 * mm
    ch = 32 * mm
    cx = w - cw - 8 * mm
    cy = 6 * mm

    # Fond blanc + cadre
    c.setFillColor(BLANC)
    c.setStrokeColor(NOIR)
    c.setLineWidth(0.8)
    c.rect(cx, cy, cw, ch, fill=1, stroke=1)

    # Séparations verticales
    col1 = 40 * mm
    col2 = 110 * mm
    c.setLineWidth(0.4)
    c.line(cx + col1, cy, cx + col1, cy + ch)
    c.line(cx + col2, cy, cx + col2, cy + ch)

    # Séparation horizontale
    c.line(cx + col1, cy + ch / 2, cx + cw, cy + ch / 2)

    # Col 1 — Logo Tijan
    c.setFillColor(VERT)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(cx + 3 * mm, cy + ch - 10 * mm, "TIJAN AI")
    c.setFillColor(GRIS_FONCE)
    c.setFont("Helvetica", 6)
    c.drawString(cx + 3 * mm, cy + ch - 15 * mm, "Engineering Intelligence")
    c.drawString(cx + 3 * mm, cy + ch - 19 * mm, "for Africa")
    c.setFont("Helvetica", 5.5)
    c.drawString(cx + 3 * mm, cy + 8 * mm, f"Réf: TIJAN-{lot}")
    date_str = datetime.now().strftime("%d/%m/%Y")
    c.drawString(cx + 3 * mm, cy + 4 * mm, f"Date: {date_str}")

    # Col 2 haut — Nom projet
    nom = params.get("nom", "Projet Tijan")[:35]
    c.setFillColor(NOIR)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(cx + col1 + 3 * mm, cy + ch - 9 * mm, nom)

    # Col 2 bas — Titre planche
    c.setFillColor(VERT)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(cx + col1 + 3 * mm, cy + ch / 2 - 9 * mm, titre_planche)

    # Col 3 haut — Infos
    ville = params.get("ville", "Dakar")
    c.setFillColor(GRIS_FONCE)
    c.setFont("Helvetica", 6.5)
    c.drawString(cx + col2 + 3 * mm, cy + ch - 9 * mm, f"Échelle : {echelle}")
    c.drawString(cx + col2 + 3 * mm, cy + ch - 14 * mm, f"Dakar — {ville}")
    c.drawString(cx + col2 + 3 * mm, cy + ch - 19 * mm, f"Pl. {page_num}/{total_pages}")

    # Col 3 bas
    c.setFont("Helvetica", 5.5)
    c.drawString(cx + col2 + 3 * mm, cy + 8 * mm, "À vérifier par ingénieur signé")
    c.drawString(cx + col2 + 3 * mm, cy + 4 * mm, f"Lot: {lot}")


def draw_border(c, w, h):
    """Cadre de plan avec marge."""
    m = 8 * mm
    c.setStrokeColor(NOIR)
    c.setLineWidth(0.6)
    c.rect(m, m, w - 2 * m, h - 2 * m)


# ══════════════════════════════════════════════════════════
# HELPERS DESSIN
# ══════════════════════════════════════════════════════════
def draw_axis_label(c, x, y, label, vertical=False):
    """Cercle avec label d'axe (A, B, C... ou 1, 2, 3...)."""
    r = 4.5 * mm
    c.setStrokeColor(NOIR)
    c.setLineWidth(0.5)
    c.setFillColor(BLANC)
    c.circle(x, y, r, fill=1, stroke=1)
    c.setFillColor(NOIR)
    c.setFont("Helvetica-Bold", 8)
    tw = c.stringWidth(str(label), "Helvetica-Bold", 8)
    c.drawString(x - tw / 2, y - 3, str(label))


def draw_rebar_section(c, cx, cy, w_mm, h_mm, nb_barres, diam_mm, cadre_diam,
                       esp_cadres, scale=1.0):
    """Dessine une coupe transversale de section BA avec armatures."""
    w = w_mm * scale
    h = h_mm * scale
    enr = 3 * scale  # enrobage 30mm à l'échelle

    # Section béton
    c.setFillColor(BLEU_BETON)
    c.setStrokeColor(NOIR)
    c.setLineWidth(0.6)
    c.rect(cx - w / 2, cy - h / 2, w, h, fill=1, stroke=1)

    # Cadre
    c.setStrokeColor(GRIS_FONCE)
    c.setLineWidth(0.4)
    c.setDash(2, 1)
    c.rect(cx - w / 2 + enr, cy - h / 2 + enr, w - 2 * enr, h - 2 * enr)
    c.setDash()

    # Barres — réparties sur le périmètre
    bar_r = max(diam_mm * scale / 2, 1.5)
    positions = []
    inner_w = w - 2 * enr
    inner_h = h - 2 * enr
    ix = cx - w / 2 + enr
    iy = cy - h / 2 + enr

    if nb_barres <= 4:
        # 4 coins
        positions = [(ix, iy), (ix + inner_w, iy),
                     (ix, iy + inner_h), (ix + inner_w, iy + inner_h)]
    elif nb_barres <= 6:
        # 4 coins + 2 milieu bas/haut
        positions = [(ix, iy), (ix + inner_w / 2, iy), (ix + inner_w, iy),
                     (ix, iy + inner_h), (ix + inner_w / 2, iy + inner_h),
                     (ix + inner_w, iy + inner_h)]
    else:
        # Répartition régulière sur périmètre
        nb_bottom = max(nb_barres // 3, 2)
        nb_top = max(nb_barres // 3, 2)
        nb_side = max((nb_barres - nb_bottom - nb_top) // 2, 0)
        for i in range(nb_bottom):
            px = ix + inner_w * i / max(nb_bottom - 1, 1)
            positions.append((px, iy))
        for i in range(nb_top):
            px = ix + inner_w * i / max(nb_top - 1, 1)
            positions.append((px, iy + inner_h))
        for i in range(1, nb_side + 1):
            py = iy + inner_h * i / (nb_side + 1)
            positions.append((ix, py))
            positions.append((ix + inner_w, py))

    c.setFillColor(NOIR)
    for px, py in positions[:nb_barres]:
        c.circle(px, py, bar_r, fill=1, stroke=0)

    # Cotation section
    c.setFillColor(GRIS_FONCE)
    c.setFont("Helvetica", 6)
    c.drawCentredString(cx, cy - h / 2 - 8, f"{w_mm}")
    c.saveState()
    c.translate(cx - w / 2 - 8, cy)
    c.rotate(90)
    c.drawCentredString(0, 0, f"{h_mm}")
    c.restoreState()


def draw_beam_elevation(c, x, y, length_mm, h_mm, armatures, scale=0.5):
    """Dessine l'élévation longitudinale d'une poutre/longrine avec armatures."""
    L = length_mm * scale
    H = h_mm * scale
    enr = 3 * scale

    # Contour béton
    c.setFillColor(colors.Color(0.95, 0.95, 0.95))
    c.setStrokeColor(NOIR)
    c.setLineWidth(0.6)
    c.rect(x, y, L, H, fill=1, stroke=1)

    # Armatures longitudinales inf (trait continu)
    c.setStrokeColor(ROUGE_ACIER)
    c.setLineWidth(0.8)
    c.line(x + enr, y + enr, x + L - enr, y + enr)

    # Armatures longitudinales sup (trait continu)
    c.line(x + enr, y + H - enr, x + L - enr, y + H - enr)

    # Cadres/étriers
    nb_cadres = armatures.get("nb_cadres", int(length_mm / armatures.get("esp_cadres_mm", 200)))
    esp = L / max(nb_cadres, 1)
    c.setStrokeColor(GRIS_FONCE)
    c.setLineWidth(0.3)
    for i in range(nb_cadres + 1):
        cx_i = x + enr + i * (L - 2 * enr) / max(nb_cadres, 1)
        c.line(cx_i, y + enr, cx_i, y + H - enr)

    # Crochets aux extrémités
    hook = 5 * scale
    c.setStrokeColor(ROUGE_ACIER)
    c.setLineWidth(0.6)
    # Gauche bas
    c.line(x + enr, y + enr, x + enr - hook, y + enr + hook)
    # Gauche haut
    c.line(x + enr, y + H - enr, x + enr - hook, y + H - enr - hook)
    # Droite bas
    c.line(x + L - enr, y + enr, x + L - enr + hook, y + enr + hook)
    # Droite haut
    c.line(x + L - enr, y + H - enr, x + L - enr + hook, y + H - enr - hook)

    # Cotation portée
    c.setStrokeColor(GRIS)
    c.setLineWidth(0.3)
    cot_y = y - 8
    c.line(x, cot_y, x + L, cot_y)
    c.line(x, cot_y - 3, x, cot_y + 3)
    c.line(x + L, cot_y - 3, x + L, cot_y + 3)
    c.setFillColor(GRIS_FONCE)
    c.setFont("Helvetica", 6)
    c.drawCentredString(x + L / 2, cot_y - 8, f"{length_mm / 10:.0f}")

    # Cotation hauteur
    cot_x = x + L + 6
    c.line(cot_x, y, cot_x, y + H)
    c.line(cot_x - 3, y, cot_x + 3, y)
    c.line(cot_x - 3, y + H, cot_x + 3, y + H)
    c.drawString(cot_x + 4, y + H / 2 - 3, f"{h_mm}")

    return L, H


def draw_armatures_table(c, x, y, armatures_list, w=160 * mm):
    """Dessine le tableau d'armatures (format Innov' Structures)."""
    cols = [25 * mm, 45 * mm, 30 * mm, 25 * mm, 35 * mm]
    headers = ["Pos.", "Armature", "l (m)", "Code", "Forme"]
    row_h = 14

    # Header
    c.setFillColor(VERT_PALE)
    c.setStrokeColor(NOIR)
    c.setLineWidth(0.4)
    hx = x
    for i, (col_w, header) in enumerate(zip(cols, headers)):
        c.rect(hx, y, col_w, row_h, fill=1, stroke=1)
        c.setFillColor(NOIR)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(hx + col_w / 2, y + 4, header)
        c.setFillColor(VERT_PALE)
        hx += col_w

    # Rows
    for j, arm in enumerate(armatures_list):
        ry = y - (j + 1) * row_h
        hx = x
        c.setFillColor(BLANC)
        for i, col_w in enumerate(cols):
            c.rect(hx, ry, col_w, row_h, fill=1, stroke=1)
            hx += col_w

        c.setFillColor(NOIR)
        c.setFont("Helvetica", 6)
        hx = x

        # Pos — cercle avec numéro
        pos_cx = hx + cols[0] / 2
        pos_cy = ry + row_h / 2
        c.circle(pos_cx, pos_cy, 5, fill=0, stroke=1)
        c.drawCentredString(pos_cx, pos_cy - 2.5, str(arm.get("pos", j + 1)))
        hx += cols[0]

        # Armature
        c.drawString(hx + 3, ry + 4, arm.get("desc", ""))
        hx += cols[1]

        # Longueur
        c.drawCentredString(hx + cols[2] / 2, ry + 4,
                            f"l={arm.get('longueur', 0):.2f}")
        hx += cols[2]

        # Code
        c.drawCentredString(hx + cols[3] / 2, ry + 4, arm.get("code", "00"))
        hx += cols[3]

        # Forme (simplifié)
        c.drawCentredString(hx + cols[4] / 2, ry + 4,
                            f"{arm.get('longueur', 0):.2f}")

    return len(armatures_list) * row_h + row_h


# ══════════════════════════════════════════════════════════
# PLANCHE 1 — PLAN DE COFFRAGE (A3 paysage)
# ══════════════════════════════════════════════════════════
def planche_coffrage(c, r, p):
    """Plan de coffrage — grille 2D avec poteaux et poutres."""
    w, h = A3L
    c.setPageSize(A3L)
    draw_border(c, w, h)

    # Titre
    c.setFillColor(NOIR)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(15 * mm, h - 18 * mm, "PLAN DE COFFRAGE — NIVEAU COURANT")
    c.setFont("Helvetica", 8)
    c.setFillColor(GRIS_FONCE)
    c.drawString(15 * mm, h - 24 * mm, "Poteaux, poutres, dalles — Dimensions en mm")

    # Paramètres grille — limiter pour lisibilité
    nx_real = p.get("nb_travees_x", 4)
    ny_real = p.get("nb_travees_y", 3)
    nx = min(nx_real, 8)  # max 8 travées affichées en X
    ny = max(min(ny_real, 6), 2)  # min 2, max 6 en Y
    portee_x = r.poutre_principale.portee_m if hasattr(r, "poutre_principale") else p.get("portee_max_m", 5.0)
    portee_y = r.poutre_secondaire.portee_m if hasattr(r, "poutre_secondaire") and r.poutre_secondaire else p.get("portee_min_m", 4.0)
    if portee_y < 2.5:
        portee_y = portee_x * 0.7  # fallback ratio

    # Zone de dessin
    margin_l = 45 * mm
    margin_b = 55 * mm
    draw_w = w - margin_l - 70 * mm
    draw_h = h - margin_b - 35 * mm

    # Échelle
    total_x = portee_x * nx
    total_y = portee_y * ny
    scale = min(draw_w / (total_x * 1000), draw_h / (total_y * 1000))

    # Centrer la grille
    grid_w = total_x * 1000 * scale
    grid_h = total_y * 1000 * scale
    ox = margin_l + (draw_w - grid_w) / 2
    oy = margin_b + (draw_h - grid_h) / 2

    # Axes X labels (A, B, C, D...)
    x_labels = [chr(65 + i) for i in range(ny + 1)]  # A, B, C...
    # Axes Y labels (1, 2, 3...)
    y_labels = [str(i + 1) for i in range(nx + 1)]

    # Dessiner les axes
    c.setStrokeColor(GRIS_CLAIR)
    c.setLineWidth(0.3)
    c.setDash(6, 3)

    for i in range(nx + 1):
        x_pos = ox + i * portee_x * 1000 * scale
        c.line(x_pos, oy - 10 * mm, x_pos, oy + total_y * 1000 * scale + 10 * mm)
        draw_axis_label(c, x_pos, oy - 18 * mm, y_labels[i])
        # Cotation entre axes
        if i < nx:
            mid = x_pos + portee_x * 1000 * scale / 2
            c.setDash()
            c.setFillColor(GRIS_FONCE)
            c.setFont("Helvetica", 6)
            c.drawCentredString(mid, oy - 10 * mm, f"{portee_x * 1000:.0f}")
            c.setDash(6, 3)

    for j in range(ny + 1):
        y_pos = oy + j * portee_y * 1000 * scale
        c.line(ox - 10 * mm, y_pos, ox + total_x * 1000 * scale + 10 * mm, y_pos)
        draw_axis_label(c, ox - 18 * mm, y_pos, x_labels[j])

    c.setDash()

    # Poteaux aux intersections
    pot_section = r.poteaux[0].section_mm if hasattr(r, "poteaux") and r.poteaux else 300
    pot_draw = max(pot_section * scale, 4)

    for i in range(nx + 1):
        for j in range(ny + 1):
            px = ox + i * portee_x * 1000 * scale
            py = oy + j * portee_y * 1000 * scale
            c.setFillColor(GRIS_TRES_CLAIR)
            c.setStrokeColor(NOIR)
            c.setLineWidth(0.5)
            c.rect(px - pot_draw / 2, py - pot_draw / 2, pot_draw, pot_draw,
                   fill=1, stroke=1)

    # Poutres principales (direction X)
    pp_h = r.poutre_principale.h_mm if hasattr(r, "poutre_principale") else 500
    pp_b = r.poutre_principale.b_mm if hasattr(r, "poutre_principale") else 250
    beam_draw_h = max(pp_b * scale, 2)

    for j in range(ny + 1):
        for i in range(nx):
            x1 = ox + i * portee_x * 1000 * scale + pot_draw / 2
            x2 = ox + (i + 1) * portee_x * 1000 * scale - pot_draw / 2
            yp = oy + j * portee_y * 1000 * scale
            c.setFillColor(colors.Color(0.9, 0.9, 0.9, 0.5))
            c.setStrokeColor(NOIR)
            c.setLineWidth(0.3)
            c.rect(x1, yp - beam_draw_h / 2, x2 - x1, beam_draw_h, fill=1, stroke=1)

    # Poutres secondaires (direction Y)
    if r.poutre_secondaire:
        ps_b = r.poutre_secondaire.b_mm
    else:
        ps_b = 200
    beam_s_draw = max(ps_b * scale, 2)

    for i in range(nx + 1):
        for j in range(ny):
            xp = ox + i * portee_x * 1000 * scale
            y1 = oy + j * portee_y * 1000 * scale + pot_draw / 2
            y2 = oy + (j + 1) * portee_y * 1000 * scale - pot_draw / 2
            c.setFillColor(colors.Color(0.9, 0.9, 0.9, 0.3))
            c.setStrokeColor(GRIS)
            c.setLineWidth(0.2)
            c.rect(xp - beam_s_draw / 2, y1, beam_s_draw, y2 - y1, fill=1, stroke=1)

    # Dalles — hachures légères
    for i in range(nx):
        for j in range(ny):
            x1 = ox + i * portee_x * 1000 * scale + pot_draw / 2
            x2 = ox + (i + 1) * portee_x * 1000 * scale - pot_draw / 2
            y1 = oy + j * portee_y * 1000 * scale + pot_draw / 2
            y2 = oy + (j + 1) * portee_y * 1000 * scale - pot_draw / 2
            # Hachure diagonale légère
            c.setStrokeColor(GRIS_CLAIR)
            c.setLineWidth(0.1)
            step = 8
            for k in range(0, int(x2 - x1 + y2 - y1), step):
                lx1 = x1 + min(k, x2 - x1)
                ly1 = y1 + max(0, k - (x2 - x1))
                lx2 = x1 + max(0, k - (y2 - y1))
                ly2 = y1 + min(k, y2 - y1)
                c.line(lx1, ly1, lx2, ly2)

    # Note si grille tronquée
    if nx_real > nx or ny_real > ny:
        c.setFont("Helvetica-Oblique", 6)
        c.setFillColor(GRIS)
        c.drawString(15 * mm, h - 30 * mm,
                     f"Note : grille affichée {nx}×{ny} travées (projet réel : {nx_real}×{ny_real})")

    # Légende
    lx = w - 65 * mm
    ly = h - 35 * mm
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(NOIR)
    c.drawString(lx, ly, "LÉGENDE")
    ly -= 14
    c.setFont("Helvetica", 6.5)

    # Poteau
    c.setFillColor(GRIS_TRES_CLAIR)
    c.setStrokeColor(NOIR)
    c.setLineWidth(0.4)
    c.rect(lx, ly - 1, 8, 8, fill=1, stroke=1)
    c.setFillColor(NOIR)
    c.drawString(lx + 12, ly, f"Poteau {pot_section}x{pot_section} mm")
    ly -= 14

    # Poutre
    c.setFillColor(colors.Color(0.9, 0.9, 0.9))
    c.rect(lx, ly + 2, 20, 5, fill=1, stroke=1)
    c.setFillColor(NOIR)
    c.drawString(lx + 24, ly, f"Poutre {pp_b}x{pp_h} mm")

    # Note
    c.setFont("Helvetica-Oblique", 6)
    c.setFillColor(GRIS)
    c.drawString(lx - 15 * mm, ly - 25, f"Note : sections variables RDC→toiture")

    draw_cartouche(c, w, h, p, "PLAN DE COFFRAGE", 1, 8, echelle="1/100")
    c.showPage()


# ══════════════════════════════════════════════════════════
# PLANCHE 2 — FERRAILLAGE POTEAUX (A4 portrait)
# ══════════════════════════════════════════════════════════
def planche_ferraillage_poteaux(c, r, p):
    """Ferraillage poteaux — coupe transversale + tableau par niveau."""
    w, h = A4P
    c.setPageSize(A4P)
    draw_border(c, w, h)

    c.setFillColor(NOIR)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(12 * mm, h - 16 * mm, "FERRAILLAGE POTEAUX — COUPES ET ÉLÉVATIONS")
    c.setFont("Helvetica", 7)
    c.setFillColor(GRIS_FONCE)
    c.drawString(12 * mm, h - 22 * mm, "Armatures longitudinales et transversales par niveau")

    # Coupe transversale du poteau RDC
    poteaux = r.poteaux if hasattr(r, "poteaux") else []
    if poteaux:
        pot_rdc = poteaux[0]
        section = pot_rdc.section_mm
        nb_b = pot_rdc.nb_barres
        diam = pot_rdc.diametre_mm
        cadre = pot_rdc.cadre_diam_mm
        esp = pot_rdc.espacement_cadres_mm
    else:
        section, nb_b, diam, cadre, esp = 300, 4, 12, 10, 200

    c.setFillColor(VERT)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(15 * mm, h - 38 * mm, "COUPES TRANSVERSALES")

    # Dessin section
    scale_s = 0.45 * mm
    sec_cx = 55 * mm
    sec_cy = h - 75 * mm
    draw_rebar_section(c, sec_cx, sec_cy, section, section, nb_b, diam,
                       cadre, esp, scale=scale_s)

    # Annotations section
    c.setFillColor(NOIR)
    c.setFont("Helvetica", 6.5)
    c.drawCentredString(sec_cx, sec_cy - section * scale_s / 2 - 16,
                        f"{section}x{section}")
    c.drawCentredString(sec_cx, sec_cy - section * scale_s / 2 - 24,
                        f"{nb_b}HA{diam}")
    c.drawCentredString(sec_cx, sec_cy - section * scale_s / 2 - 32,
                        f"Cadres HA{cadre}/{esp}")

    # Tableau des sections par niveau
    c.setFillColor(VERT)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(15 * mm, h - 120 * mm, "TABLEAU DES SECTIONS PAR NIVEAU")

    tab_y = h - 132 * mm
    tab_x = 15 * mm
    col_widths = [28 * mm, 28 * mm, 30 * mm, 28 * mm, 28 * mm, 25 * mm]
    headers_t = ["Niveau", "NEd (kN)", "Section (mm)", "Long.", "Cadres", "Taux (%)"]

    # Header
    hx = tab_x
    c.setFillColor(VERT_PALE)
    for cw_t in col_widths:
        c.rect(hx, tab_y, cw_t, 12, fill=1, stroke=1)
        hx += cw_t
    hx = tab_x
    c.setFillColor(NOIR)
    c.setFont("Helvetica-Bold", 6)
    for i, header in enumerate(headers_t):
        c.drawCentredString(hx + col_widths[i] / 2, tab_y + 3.5, header)
        hx += col_widths[i]

    # Rows
    for k, pot in enumerate(poteaux):
        ry = tab_y - (k + 1) * 12
        hx = tab_x
        c.setFillColor(BLANC)
        for cw_t in col_widths:
            c.rect(hx, ry, cw_t, 12, fill=1, stroke=1)
            hx += cw_t

        c.setFillColor(NOIR)
        c.setFont("Helvetica", 6)
        hx = tab_x
        niveau = pot.niveau if hasattr(pot, "niveau") else f"N{k}"
        vals = [
            niveau,
            f"{pot.NEd_kN:.0f}",
            f"{pot.section_mm}x{pot.section_mm}",
            f"{pot.nb_barres}HA{pot.diametre_mm}",
            f"HA{pot.cadre_diam_mm}/{pot.espacement_cadres_mm}",
            f"{pot.taux_armature_pct:.2f}",
        ]
        for i, val in enumerate(vals):
            c.drawCentredString(hx + col_widths[i] / 2, ry + 3.5, val)
            hx += col_widths[i]

    draw_cartouche(c, w, h, p, "FERRAILLAGE POTEAUX", 2, 8, lot="STR")
    c.showPage()


# ══════════════════════════════════════════════════════════
# PLANCHE 3 — FERRAILLAGE POUTRE PRINCIPALE (A4 portrait)
# ══════════════════════════════════════════════════════════
def planche_ferraillage_poutre(c, r, p, poutre_type="principale", page_num=3):
    """Ferraillage poutre — élévation + coupe A-A + tableau armatures."""
    w, h = A4P
    c.setPageSize(A4P)
    draw_border(c, w, h)

    if poutre_type == "principale" and hasattr(r, "poutre_principale"):
        pt = r.poutre_principale
        titre = "FERRAILLAGE POUTRES PRINCIPALES"
    elif poutre_type == "secondaire" and hasattr(r, "poutre_secondaire") and r.poutre_secondaire:
        pt = r.poutre_secondaire
        titre = "FERRAILLAGE POUTRES SECONDAIRES"
    else:
        pt = None
        titre = f"FERRAILLAGE POUTRES {poutre_type.upper()}"

    c.setFillColor(NOIR)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(12 * mm, h - 16 * mm, titre)
    c.setFont("Helvetica", 7)
    c.setFillColor(GRIS_FONCE)
    c.drawString(12 * mm, h - 22 * mm, "Armatures inférieures, supérieures et étriers")

    if pt is None:
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(30 * mm, h / 2, "Données non disponibles")
        draw_cartouche(c, w, h, p, titre, page_num, 8, lot="STR")
        c.showPage()
        return

    portee_mm = pt.portee_m * 1000
    b_mm = pt.b_mm
    h_mm = pt.h_mm
    as_inf = pt.As_inf_cm2
    as_sup = pt.As_sup_cm2
    etr_diam = pt.etrier_diam_mm
    etr_esp = pt.etrier_esp_mm

    # Élévation
    c.setFillColor(VERT)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(15 * mm, h - 36 * mm, "ÉLÉVATION — COUPE LONGITUDINALE")

    elev_x = 25 * mm
    elev_y = h - 85 * mm
    avail_w = w - 50 * mm
    scale_e = min(avail_w / portee_mm, 0.035)
    # Ensure beam height is visible (at least 15mm on page)
    if h_mm * scale_e < 15:
        scale_e = 15 / h_mm
    armatures_info = {
        "nb_cadres": int(portee_mm / etr_esp),
        "esp_cadres_mm": etr_esp,
    }
    draw_beam_elevation(c, elev_x, elev_y, portee_mm, h_mm, armatures_info, scale=scale_e)

    # Flèche coupe A-A
    mid_x = elev_x + portee_mm * scale_e / 2
    c.setStrokeColor(NOIR)
    c.setLineWidth(0.5)
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(NOIR)
    c.drawCentredString(mid_x, elev_y + h_mm * scale_e + 10, "A")
    c.line(mid_x, elev_y + h_mm * scale_e + 6, mid_x, elev_y + h_mm * scale_e + 2)

    # Coupe A-A
    c.setFillColor(VERT)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(15 * mm, h - 105 * mm, "COUPE A-A")

    sec_cx = 50 * mm
    sec_cy = h - 140 * mm
    nb_barres_inf = max(int(as_inf / (math.pi * (12 / 10) ** 2 / 4)), 2)
    nb_barres_sup = max(int(as_sup / (math.pi * (12 / 10) ** 2 / 4)), 2)
    nb_total = nb_barres_inf + nb_barres_sup
    # Scale section to ~25mm max dimension on page
    max_dim = max(b_mm, h_mm)
    sec_scale = min(25 * mm / max_dim, 0.25 * mm)
    draw_rebar_section(c, sec_cx, sec_cy, b_mm, h_mm, nb_total, 12,
                       etr_diam, etr_esp, scale=sec_scale)

    # Tableau caractéristiques — à droite de la coupe A-A
    c.setFillColor(VERT)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(100 * mm, h - 105 * mm, "CARACTÉRISTIQUES POUTRE TYPE")

    tab_x = 100 * mm
    tab_y = h - 115 * mm
    beton_class = p.get("classe_beton", "C30/37")

    specs = [
        ("Section", f"{b_mm} × {h_mm} mm"),
        ("As inférieur (travée)", f"{as_inf:.1f} cm² — {nb_barres_inf} barres"),
        ("As supérieur (appuis)", f"{as_sup:.1f} cm² — {nb_barres_sup} barres"),
        ("Étriers", f"HA{etr_diam} / {etr_esp} mm"),
        ("Portée de calcul", f"{pt.portee_m:.1f} m"),
        ("Béton", beton_class),
    ]

    for i, (label, val) in enumerate(specs):
        ry = tab_y - i * 12
        c.setFillColor(VERT_PALE if i == 0 else BLANC)
        c.rect(tab_x, ry, 55 * mm, 12, fill=1, stroke=1)
        c.rect(tab_x + 55 * mm, ry, 75 * mm, 12, fill=1, stroke=1)
        c.setFillColor(NOIR)
        c.setFont("Helvetica-Bold" if i == 0 else "Helvetica", 6.5)
        c.drawString(tab_x + 3, ry + 3.5, label)
        c.setFont("Helvetica", 6.5)
        c.drawString(tab_x + 55 * mm + 3, ry + 3.5, val)

    draw_cartouche(c, w, h, p, titre, page_num, 8, lot="STR")
    c.showPage()


# ══════════════════════════════════════════════════════════
# PLANCHE 5 — PLAN DE FONDATIONS (A3 paysage)
# ══════════════════════════════════════════════════════════
def planche_fondations(c, r, p):
    """Plan de fondations avec pieux et longrines."""
    w, h = A3L
    c.setPageSize(A3L)
    draw_border(c, w, h)

    c.setFillColor(NOIR)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(15 * mm, h - 18 * mm, "PLAN DE FONDATIONS — PIEUX ET LONGRINES")
    c.setFont("Helvetica", 8)
    c.setFillColor(GRIS_FONCE)
    c.drawString(15 * mm, h - 24 * mm, "Implantation des pieux et longrines de liaison")

    fd = r.fondation if hasattr(r, "fondation") else None
    nx = min(p.get("nb_travees_x", 4), 8)
    ny = max(min(p.get("nb_travees_y", 3), 6), 2)
    portee_x = p.get("portee_max_m", 5.0)
    portee_y = p.get("portee_min_m", 4.0)
    if portee_y < 2.5:
        portee_y = portee_x * 0.7

    margin_l = 45 * mm
    margin_b = 55 * mm
    draw_w = w - margin_l - 70 * mm
    draw_h = h - margin_b - 35 * mm
    total_x = portee_x * nx
    total_y = portee_y * ny
    scale = min(draw_w / (total_x * 1000), draw_h / (total_y * 1000))
    grid_w = total_x * 1000 * scale
    grid_h = total_y * 1000 * scale
    ox = margin_l + (draw_w - grid_w) / 2
    oy = margin_b + (draw_h - grid_h) / 2

    # Axes
    c.setStrokeColor(GRIS_CLAIR)
    c.setLineWidth(0.3)
    c.setDash(6, 3)
    for i in range(nx + 1):
        x_pos = ox + i * portee_x * 1000 * scale
        c.line(x_pos, oy - 10 * mm, x_pos, oy + total_y * 1000 * scale + 10 * mm)
        draw_axis_label(c, x_pos, oy - 18 * mm, str(i + 1))
    for j in range(ny + 1):
        y_pos = oy + j * portee_y * 1000 * scale
        c.line(ox - 10 * mm, y_pos, ox + total_x * 1000 * scale + 10 * mm, y_pos)
        draw_axis_label(c, ox - 18 * mm, y_pos, chr(65 + j))
    c.setDash()

    # Pieux à chaque intersection
    nb_pieux = fd.nb_pieux if fd and hasattr(fd, "nb_pieux") else 4
    diam_pieu = fd.diam_pieu_mm if fd and hasattr(fd, "diam_pieu_mm") else 600
    pieu_r = max(diam_pieu * scale / 2, 4)

    for i in range(nx + 1):
        for j in range(ny + 1):
            px = ox + i * portee_x * 1000 * scale
            py = oy + j * portee_y * 1000 * scale

            if nb_pieux > 0 and diam_pieu > 0:
                # Dessiner groupe de pieux
                c.setFillColor(VERT_PALE)
                c.setStrokeColor(VERT)
                c.setLineWidth(0.5)
                if nb_pieux <= 1:
                    c.circle(px, py, pieu_r, fill=1, stroke=1)
                elif nb_pieux <= 4:
                    offsets = [(-1, -1), (1, -1), (-1, 1), (1, 1)]
                    for dx, dy in offsets[:nb_pieux]:
                        c.circle(px + dx * pieu_r * 0.8, py + dy * pieu_r * 0.8,
                                pieu_r * 0.6, fill=1, stroke=1)
                else:
                    c.circle(px, py, pieu_r * 1.2, fill=1, stroke=1)
                    c.setFillColor(NOIR)
                    c.setFont("Helvetica", 5)
                    c.drawCentredString(px, py - 2, f"{nb_pieux}p")
            else:
                # Semelle
                sem_size = max(1500 * scale, 8)
                c.setFillColor(GRIS_TRES_CLAIR)
                c.setStrokeColor(NOIR)
                c.setLineWidth(0.4)
                c.rect(px - sem_size / 2, py - sem_size / 2, sem_size, sem_size,
                       fill=1, stroke=1)

    # Longrines entre pieux (direction X)
    c.setStrokeColor(NOIR)
    c.setLineWidth(1.0)
    for j in range(ny + 1):
        for i in range(nx):
            x1 = ox + i * portee_x * 1000 * scale
            x2 = ox + (i + 1) * portee_x * 1000 * scale
            yp = oy + j * portee_y * 1000 * scale
            c.line(x1 + pieu_r, yp, x2 - pieu_r, yp)

    # Longrines direction Y
    for i in range(nx + 1):
        for j in range(ny):
            xp = ox + i * portee_x * 1000 * scale
            y1 = oy + j * portee_y * 1000 * scale
            y2 = oy + (j + 1) * portee_y * 1000 * scale
            c.line(xp, y1 + pieu_r, xp, y2 - pieu_r)

    # Info fondations
    lx = w - 60 * mm
    ly = h - 35 * mm
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(VERT)
    c.drawString(lx, ly, "FONDATIONS")
    ly -= 12
    c.setFont("Helvetica", 6.5)
    c.setFillColor(NOIR)

    type_fond = "Pieux forés" if (fd and hasattr(fd, "nb_pieux") and fd.nb_pieux > 0) else "Semelles"
    infos = [
        ("Type", type_fond),
        ("Diamètre", f"ø{diam_pieu} mm" if nb_pieux > 0 else "—"),
        ("Longueur", f"{fd.longueur_pieu_m:.1f} m" if fd and hasattr(fd, "longueur_pieu_m") else "—"),
        ("Nb/poteau", str(nb_pieux) if nb_pieux > 0 else "1"),
        ("Armatures", f"{fd.As_cm2:.1f} cm²" if fd and hasattr(fd, "As_cm2") else "—"),
        ("Béton", p.get("classe_beton", "C30/37")),
    ]
    for label, val in infos:
        c.drawString(lx, ly, f"{label} :")
        c.drawString(lx + 28 * mm, ly, val)
        ly -= 10

    draw_cartouche(c, w, h, p, "PLAN DE FONDATIONS", 5, 8, lot="STR")
    c.showPage()


# ══════════════════════════════════════════════════════════
# PLANCHE 6 — FERRAILLAGE LONGRINE TYPE (A4 portrait)
# ══════════════════════════════════════════════════════════
def planche_ferraillage_longrine(c, r, p):
    """Ferraillage longrine type — format Innov' Structures."""
    w, h = A4P
    c.setPageSize(A4P)
    draw_border(c, w, h)

    c.setFillColor(NOIR)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(12 * mm, h - 16 * mm, "FERRAILLAGE LONGRINES TYPE")
    c.setFont("Helvetica", 7)
    c.setFillColor(GRIS_FONCE)
    c.drawString(12 * mm, h - 22 * mm, "Élévation + coupe transversale + tableau armatures")

    # Longrine type = poutre de fondation
    portee = p.get("portee_max_m", 5.0)
    portee_mm = portee * 1000
    long_b = 200  # largeur longrine mm
    long_h = max(int(portee * 100), 300)  # h = portée/10 minimum
    long_h = min(long_h, 600)

    nb_barres = 4
    diam = 10
    cadre_diam = 6
    esp_cadres = int(portee_mm / 15)  # ~15 cadres
    esp_cadres = max(min(esp_cadres, 300), 150)

    # Élévation
    c.setFillColor(VERT)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(15 * mm, h - 36 * mm, f"LONGRINE L1 — Section {long_b}x{long_h}")

    elev_x = 25 * mm
    elev_y = h - 90 * mm
    scale_e = min((w - 50 * mm) / portee_mm, 0.025)
    armatures_info = {"nb_cadres": int(portee_mm / esp_cadres), "esp_cadres_mm": esp_cadres}
    draw_beam_elevation(c, elev_x, elev_y, portee_mm, long_h, armatures_info, scale=scale_e)

    # Coupe A-A
    c.setFillColor(VERT)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(15 * mm, h - 110 * mm, "COUPE A-A")

    sec_cx = 45 * mm
    sec_cy = h - 150 * mm
    draw_rebar_section(c, sec_cx, sec_cy, long_b, long_h, nb_barres, diam,
                       cadre_diam, esp_cadres, scale=0.35 * mm)

    # Tableau armatures
    c.setFillColor(VERT)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(15 * mm, h - 185 * mm, "NOMENCLATURE ARMATURES")

    armatures_list = [
        {"pos": 1, "desc": f"{nb_barres}HA {diam}", "longueur": portee + 0.2, "code": "00"},
        {"pos": 2, "desc": f"2HA {diam}", "longueur": portee + 0.4, "code": "00"},
        {"pos": 3, "desc": f"2HA 8", "longueur": portee + 0.1, "code": "00"},
        {"pos": 4, "desc": f"{int(portee_mm / esp_cadres)}HA {cadre_diam}",
         "longueur": (long_b + long_h) * 2 / 1000 + 0.2, "code": "31"},
    ]
    draw_armatures_table(c, 15 * mm, h - 197 * mm, armatures_list)

    # Infos bas de page
    c.setFont("Helvetica", 6)
    c.setFillColor(GRIS_FONCE)
    beton_vol = portee * long_b / 1000 * long_h / 1000
    c.drawString(15 * mm, 50 * mm, f"Béton : {p.get('classe_beton', 'C30/37')} = {beton_vol:.3f} m³")
    c.drawString(15 * mm, 44 * mm, f"Acier HA 500")
    c.drawString(15 * mm, 38 * mm, f"Enrobage : 3 cm")

    draw_cartouche(c, w, h, p, "FERRAILLAGE LONGRINES", 6, 8, lot="STR")
    c.showPage()


# ══════════════════════════════════════════════════════════
# PLANCHE 7 — TABLEAU DE FAÇONNAGE (A4 portrait)
# ══════════════════════════════════════════════════════════
def planche_tableau_faconnage(c, r, p):
    """Tableau de façonnage — nomenclature complète des aciers."""
    w, h = A4P
    c.setPageSize(A4P)
    draw_border(c, w, h)

    c.setFillColor(NOIR)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(12 * mm, h - 16 * mm, "TABLEAU DE FAÇONNAGE — ARMATURES")
    c.setFont("Helvetica", 7)
    c.setFillColor(GRIS_FONCE)
    c.drawString(12 * mm, h - 22 * mm, "Nomenclature des barres — longueurs développées")

    # Headers
    tab_x = 12 * mm
    tab_y = h - 38 * mm
    cols = [15 * mm, 30 * mm, 20 * mm, 18 * mm, 25 * mm, 25 * mm, 22 * mm, 30 * mm]
    headers = ["Repère", "Type", "Diam.", "Nb total", "Long. unitaire", "Long. dév.", "Masse (kg)", "Usage"]
    row_h = 12

    # Header row
    hx = tab_x
    c.setFillColor(VERT_PALE)
    for cw_f in cols:
        c.rect(hx, tab_y, cw_f, row_h + 2, fill=1, stroke=1)
        hx += cw_f
    hx = tab_x
    c.setFillColor(NOIR)
    c.setFont("Helvetica-Bold", 5.5)
    for i, header in enumerate(headers):
        c.drawCentredString(hx + cols[i] / 2, tab_y + 4, header)
        hx += cols[i]

    # Generate rows from structural results
    poteaux = r.poteaux if hasattr(r, "poteaux") else []
    pt_p = r.poutre_principale if hasattr(r, "poutre_principale") else None
    rows = []
    repere = 1

    # Poteaux
    for pot in poteaux:
        niveau = pot.niveau if hasattr(pot, "niveau") else "?"
        he = p.get("hauteur_etage_m", 3.0)
        long_unit = he + 0.6  # longueur développée avec recouvrement
        nb_total = pot.nb_barres * (p.get("nb_travees_x", 4) + 1) * (p.get("nb_travees_y", 3) + 1)
        masse_lin = 0.00617 * pot.diametre_mm ** 2  # kg/m
        masse = masse_lin * long_unit * pot.nb_barres
        rows.append([str(repere), f"Long. poteaux {niveau}", f"HA{pot.diametre_mm}",
                     str(pot.nb_barres), f"{long_unit:.2f}", f"{long_unit:.2f}",
                     f"{masse:.1f}", f"Poteaux {niveau}"])
        repere += 1

        nb_cadres = int(he * 1000 / pot.espacement_cadres_mm)
        perim = 4 * (pot.section_mm - 60) / 1000
        masse_c = 0.00617 * pot.cadre_diam_mm ** 2 * perim * nb_cadres
        rows.append([str(repere), f"Cadre poteaux {niveau}", f"HA{pot.cadre_diam_mm}",
                     str(nb_cadres), f"{perim:.2f}", f"{perim:.2f}",
                     f"{masse_c:.1f}", f"Cadres {niveau}"])
        repere += 1

    # Poutre principale
    if pt_p:
        nb_inf = max(int(pt_p.As_inf_cm2 / 1.13), 2)  # HA12
        long_p = pt_p.portee_m + 0.4
        masse_p = 0.888 * long_p * nb_inf  # HA12 = 0.888 kg/m
        rows.append([str(repere), "Long. poutre inf.", "HA12",
                     str(nb_inf), f"{long_p:.2f}", f"{long_p:.2f}",
                     f"{masse_p:.1f}", "Armatures inf. poutr."])
        repere += 1

    # Draw rows
    for k, row in enumerate(rows[:20]):  # Max 20 rows per page
        ry = tab_y - (k + 1) * row_h
        hx = tab_x
        c.setFillColor(BLANC)
        for cw_f in cols:
            c.rect(hx, ry, cw_f, row_h, fill=1, stroke=1)
            hx += cw_f

        c.setFillColor(NOIR)
        c.setFont("Helvetica", 5.5)
        hx = tab_x
        for i, val in enumerate(row):
            c.drawCentredString(hx + cols[i] / 2, ry + 3.5, val)
            hx += cols[i]

    draw_cartouche(c, w, h, p, "TABLEAU DE FAÇONNAGE", 7, 8, lot="STR")
    c.showPage()


# ══════════════════════════════════════════════════════════
# PLANCHE 8 — COUPE GÉNÉRALE BÂTIMENT (A3 paysage)
# ══════════════════════════════════════════════════════════
def planche_coupe_generale(c, r, p):
    """Coupe générale du bâtiment — élévation avec niveaux."""
    w, h = A3L
    c.setPageSize(A3L)
    draw_border(c, w, h)

    c.setFillColor(NOIR)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(15 * mm, h - 18 * mm, "COUPE GÉNÉRALE — ÉLÉVATION")
    c.setFont("Helvetica", 8)
    c.setFillColor(GRIS_FONCE)
    c.drawString(15 * mm, h - 24 * mm, "Sections poteaux variables par niveau")

    nb_niveaux = p.get("nb_niveaux", 5)
    he = p.get("hauteur_etage_m", 3.0)
    portee_x = p.get("portee_max_m", 5.0)
    nx = min(p.get("nb_travees_x", 4), 6)  # max 6 travées affichées

    # Zone de dessin
    total_h_m = nb_niveaux * he
    total_w_m = portee_x * nx

    margin_l = 50 * mm
    margin_b = 55 * mm
    draw_w = w - margin_l - 80 * mm
    draw_h = h - margin_b - 35 * mm

    scale_x = draw_w / (total_w_m * 1000)
    scale_y = draw_h / (total_h_m * 1000)
    scale = min(scale_x, scale_y)

    ox = margin_l
    oy = margin_b

    poteaux = r.poteaux if hasattr(r, "poteaux") else []

    for niv in range(nb_niveaux):
        y_base = oy + niv * he * 1000 * scale
        y_top = oy + (niv + 1) * he * 1000 * scale

        # Dalle
        c.setFillColor(GRIS_TRES_CLAIR)
        c.setStrokeColor(NOIR)
        c.setLineWidth(0.4)
        dalle_h = max(200 * scale, 2)
        c.rect(ox, y_top - dalle_h, total_w_m * 1000 * scale, dalle_h, fill=1, stroke=1)

        # Poteaux
        pot = poteaux[niv] if niv < len(poteaux) else None
        section = pot.section_mm if pot else 300
        pot_w = max(section * scale, 3)

        for i in range(nx + 1):
            px = ox + i * portee_x * 1000 * scale
            c.setFillColor(colors.Color(0.85, 0.85, 0.85))
            c.setStrokeColor(NOIR)
            c.setLineWidth(0.3)
            c.rect(px - pot_w / 2, y_base, pot_w, y_top - y_base - dalle_h, fill=1, stroke=1)

        # Niveau label
        c.setFillColor(NOIR)
        c.setFont("Helvetica", 6.5)
        label = pot.niveau if pot and hasattr(pot, "niveau") else f"N{niv}"
        c.drawString(ox - 20 * mm, y_base + (y_top - y_base) / 2, label)

        # Section poteau
        c.setFont("Helvetica", 5.5)
        c.setFillColor(GRIS_FONCE)
        c.drawString(ox + total_w_m * 1000 * scale + 5, y_base + (y_top - y_base) / 2,
                     f"{section}x{section}")

        # Hauteur étage cotation
        cot_x = ox - 8 * mm
        c.setStrokeColor(GRIS)
        c.setLineWidth(0.3)
        c.line(cot_x, y_base, cot_x, y_top)
        c.line(cot_x - 2, y_base, cot_x + 2, y_base)
        c.line(cot_x - 2, y_top, cot_x + 2, y_top)
        c.setFillColor(GRIS_FONCE)
        c.setFont("Helvetica", 5)
        c.drawCentredString(cot_x - 5, y_base + (y_top - y_base) / 2, f"{he*1000:.0f}")

    # Fondation en bas
    fd_h = max(500 * scale, 3)
    c.setFillColor(GRIS_CLAIR)
    c.setStrokeColor(NOIR)
    c.setLineWidth(0.5)
    c.rect(ox - 10, oy - fd_h, total_w_m * 1000 * scale + 20, fd_h, fill=1, stroke=1)
    c.setFillColor(NOIR)
    c.setFont("Helvetica", 6)
    c.drawString(ox, oy - fd_h + 3, "FONDATIONS")

    # Axes en bas
    for i in range(nx + 1):
        px = ox + i * portee_x * 1000 * scale
        draw_axis_label(c, px, oy - fd_h - 12 * mm, str(i + 1))

    # Titre hauteur totale
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(NOIR)
    c.drawString(ox + total_w_m * 1000 * scale + 15, oy + total_h_m * 1000 * scale / 2,
                 f"H totale = {total_h_m:.1f} m")

    draw_cartouche(c, w, h, p, "COUPE GÉNÉRALE", 8, 8, lot="STR", echelle="1/200")
    c.showPage()


# ══════════════════════════════════════════════════════════
# ASSEMBLAGE DOSSIER COMPLET
# ══════════════════════════════════════════════════════════
def generer_dossier_ba(output_path: str, resultats=None, params: dict = None):
    """Génère le dossier BA complet — 8 planches."""
    if params is None:
        params = {}
    if hasattr(params, "__dict__"):
        params = {k: v for k, v in vars(params).items() if not k.startswith("_")}

    r = resultats

    # Adapter moteur v2 → attributs attendus
    if r is not None:
        if not hasattr(r, "poteaux_par_niveau") and hasattr(r, "poteaux"):
            for pot in r.poteaux:
                if not hasattr(pot, "label") and hasattr(pot, "niveau"):
                    pot.label = pot.niveau
            r.poteaux_par_niveau = r.poteaux
        if not hasattr(r, "poutre_type") and hasattr(r, "poutre_principale"):
            r.poutre_type = r.poutre_principale
        if hasattr(r, "fondation"):
            fd = r.fondation
            if not hasattr(fd, "type_fond") and hasattr(fd, "type"):
                fd.type_fond = str(fd.type.value) if hasattr(fd.type, "value") else str(fd.type)
            if not hasattr(fd, "section_semelle_m") and hasattr(fd, "largeur_semelle_m"):
                fd.section_semelle_m = fd.largeur_semelle_m

    c = pdfcanvas.Canvas(output_path, pagesize=A3L)
    c.setTitle(f"Dossier BA — {params.get('nom', 'Projet Tijan')}")
    c.setAuthor("Tijan AI — Engineering Intelligence for Africa")

    # 8 planches
    planche_coffrage(c, r, params)                                    # 1
    planche_ferraillage_poteaux(c, r, params)                         # 2
    planche_ferraillage_poutre(c, r, params, "principale", 3)         # 3
    planche_ferraillage_poutre(c, r, params, "secondaire", 4)         # 4
    planche_fondations(c, r, params)                                  # 5
    planche_ferraillage_longrine(c, r, params)                        # 6
    planche_tableau_faconnage(c, r, params)                           # 7
    planche_coupe_generale(c, r, params)                              # 8

    c.save()
    return output_path


# Alias pour main.py
def generer_planches(resultats, output_path: str, params: dict = None):
    return generer_dossier_ba(output_path, resultats, params)
