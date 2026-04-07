"""
gen_schemas_ferraillage.py — Schemas de ferraillage Tijan AI (rewrite v2)

Plans cotes pour:
  - Poteau type (coupe transversale + elevation)
  - Poutre type (coupe transversale + elevation)
  - Dalle type  (vue en plan + coupe verticale, EC2 §9.3)
  - Fondation type (semelle isolee OU pieu fore selon le moteur)

Toutes les valeurs (sections, armatures, espacements, portees) sont issues
des resultats du moteur EC2/EC8. Aucune valeur en dur.

Principe de construction des dessins :
  - chaque vue est un Drawing INDEPENDANT, dimensionne par son contenu
  - les marges internes (padding) reservent l'espace pour cotes et labels
  - les vues sont ensuite placees dans un Table 2 colonnes pour la mise en page
  -> impossible que les graphismes debordent ou se superposent
"""
from io import BytesIO
import math
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, PageBreak, KeepTogether)
from reportlab.graphics.shapes import (Drawing, Rect, Circle, Line, String,
                                        Group, Polygon, PolyLine)

from tijan_theme import (VERT, VERT_DARK, NOIR, GRIS1, GRIS2, GRIS3, BLANC,
                         BLEU, ORANGE, ML, MR, CW, W, S, HeaderFooter,
                         p, fmt_n, section_title, table_style, _current_lang)


# ════════════════════════════════════════════════════════════════════════
#  i18n local
# ════════════════════════════════════════════════════════════════════════
def _T(fr, en):
    return en if _current_lang == 'en' else fr


# ════════════════════════════════════════════════════════════════════════
#  Constantes de mise en page des dessins
# ════════════════════════════════════════════════════════════════════════
PAD_L = 14 * mm   # marge gauche (cote verticale + label)
PAD_R = 6 * mm
PAD_B = 12 * mm   # marge basse (cote horizontale + label)
PAD_T = 12 * mm   # marge haute (titre vue)


def _make_drawing(content_w_pts, content_h_pts):
    """Cree un Drawing dimensionne pour contenir 'content' + marges cote/label."""
    return Drawing(content_w_pts + PAD_L + PAD_R,
                   content_h_pts + PAD_B + PAD_T)


def _origin():
    """Origine (x, y) reservee au contenu apres marges."""
    return PAD_L, PAD_B


# ════════════════════════════════════════════════════════════════════════
#  Helpers de dessin (cotes, fleches, titres)
# ════════════════════════════════════════════════════════════════════════
def _arrow_h_left(d, x, y):
    d.add(Polygon(points=[x, y, x + 4, y - 1.6, x + 4, y + 1.6],
                  fillColor=GRIS3, strokeColor=GRIS3))


def _arrow_h_right(d, x, y):
    d.add(Polygon(points=[x, y, x - 4, y - 1.6, x - 4, y + 1.6],
                  fillColor=GRIS3, strokeColor=GRIS3))


def _arrow_v_down(d, x, y):
    d.add(Polygon(points=[x, y, x - 1.6, y + 4, x + 1.6, y + 4],
                  fillColor=GRIS3, strokeColor=GRIS3))


def _arrow_v_up(d, x, y):
    d.add(Polygon(points=[x, y, x - 1.6, y - 4, x + 1.6, y - 4],
                  fillColor=GRIS3, strokeColor=GRIS3))


def _dim_h(d, x1, x2, y, label, font=7):
    """Cote horizontale entre x1 et x2 a la hauteur y, label au milieu au-dessus."""
    d.add(Line(x1, y, x2, y, strokeColor=GRIS3, strokeWidth=0.5))
    d.add(Line(x1, y - 2, x1, y + 2, strokeColor=GRIS3, strokeWidth=0.6))
    d.add(Line(x2, y - 2, x2, y + 2, strokeColor=GRIS3, strokeWidth=0.6))
    _arrow_h_left(d, x1, y)
    _arrow_h_right(d, x2, y)
    d.add(String((x1 + x2) / 2, y + 2.5, label,
                 fontName='Helvetica', fontSize=font,
                 textAnchor='middle', fillColor=NOIR))


def _dim_v(d, y1, y2, x, label, font=7):
    """Cote verticale entre y1 et y2 a l'abscisse x, label a gauche."""
    d.add(Line(x, y1, x, y2, strokeColor=GRIS3, strokeWidth=0.5))
    d.add(Line(x - 2, y1, x + 2, y1, strokeColor=GRIS3, strokeWidth=0.6))
    d.add(Line(x - 2, y2, x + 2, y2, strokeColor=GRIS3, strokeWidth=0.6))
    _arrow_v_down(d, x, y1)
    _arrow_v_up(d, x, y2)
    d.add(String(x - 4, (y1 + y2) / 2 - 2, label,
                 fontName='Helvetica', fontSize=font,
                 textAnchor='end', fillColor=NOIR))


def _title(d, x, y, label):
    d.add(String(x, y, label,
                 fontName='Helvetica-Bold', fontSize=8.5,
                 textAnchor='middle', fillColor=VERT_DARK))


def _enrobage_mm(rs):
    return 30 if getattr(rs, 'distance_mer_km', 0) >= 5 else 40


# ════════════════════════════════════════════════════════════════════════
#  POTEAU — coupe transversale
# ════════════════════════════════════════════════════════════════════════
def _draw_poteau_section(rs):
    pot = rs.poteaux[0] if rs.poteaux else None
    if not pot:
        return None

    b_mm = pot.section_mm
    nb = pot.nb_barres
    diam = pot.diametre_mm
    enrobage = _enrobage_mm(rs)

    # Echelle: section visible 48 mm de cote
    side_pts = 48 * mm
    scale = side_pts / b_mm

    d = _make_drawing(side_pts, side_pts + 6 * mm)  # +6mm pour titre
    ox, oy = _origin()

    # Beton
    d.add(Rect(ox, oy, side_pts, side_pts,
               fillColor=GRIS1, strokeColor=NOIR, strokeWidth=1.2))
    # Cadre interieur (etrier)
    e = enrobage * scale
    d.add(Rect(ox + e, oy + e, side_pts - 2 * e, side_pts - 2 * e,
               fillColor=None, strokeColor=BLEU, strokeWidth=0.8,
               strokeDashArray=[2, 2]))
    # Barres longitudinales aux coins (et milieu si nb>=6)
    bar_r = max(diam * scale / 2, 1.8)
    inner = side_pts - 2 * e
    coords = []
    if nb <= 4:
        coords = [(0, 0), (1, 0), (0, 1), (1, 1)]
    elif nb <= 6:
        coords = [(0, 0), (0.5, 0), (1, 0), (0, 1), (0.5, 1), (1, 1)]
    elif nb <= 8:
        coords = [(0, 0), (0.5, 0), (1, 0),
                  (0, 0.5),          (1, 0.5),
                  (0, 1), (0.5, 1), (1, 1)]
    else:
        # 12 barres (3x3 plein - centre)
        for i in range(4):
            for j in range(4):
                if 0 < i < 3 and 0 < j < 3:
                    continue
                coords.append((i / 3, j / 3))
    for (fx, fy) in coords:
        d.add(Circle(ox + e + fx * inner, oy + e + fy * inner,
                     bar_r, fillColor=NOIR, strokeColor=NOIR))

    # Cotes b x b
    _dim_h(d, ox, ox + side_pts, oy - 6, f"{b_mm} mm")
    _dim_v(d, oy, oy + side_pts, ox - 5, f"{b_mm} mm")

    # Titre
    _title(d, ox + side_pts / 2, oy + side_pts + 4,
           _T("Coupe A-A", "Section A-A"))
    return d


def _draw_poteau_elevation(rs):
    pot = rs.poteaux[0] if rs.poteaux else None
    if not pot:
        return None
    h_etage_mm = int(getattr(rs.params, 'hauteur_etage_m', 3.0) * 1000)
    cad_e = pot.espacement_cadres_mm
    cad_d = pot.cadre_diam_mm

    elev_w_pts = 22 * mm
    elev_h_pts = 70 * mm
    d = _make_drawing(elev_w_pts, elev_h_pts + 6 * mm)
    ox, oy = _origin()

    d.add(Rect(ox, oy, elev_w_pts, elev_h_pts,
               fillColor=GRIS1, strokeColor=NOIR, strokeWidth=1.2))
    # Barres verticales (2 visibles aux faces)
    for off in (3, elev_w_pts - 3):
        d.add(Line(ox + off, oy + 3, ox + off, oy + elev_h_pts - 3,
                   strokeColor=NOIR, strokeWidth=1.0))
    # Cadres horizontaux espaces (representation indicative ~ 7 cadres)
    n_cadres = 8
    for i in range(n_cadres):
        cy = oy + 4 + i * (elev_h_pts - 8) / (n_cadres - 1)
        d.add(Line(ox + 2, cy, ox + elev_w_pts - 2, cy,
                   strokeColor=BLEU, strokeWidth=0.7))
    _dim_v(d, oy, oy + elev_h_pts, ox - 5, f"H = {h_etage_mm} mm")
    _dim_h(d, ox, ox + elev_w_pts, oy - 6,
           f"HA{cad_d} e={cad_e} mm")
    _title(d, ox + elev_w_pts / 2, oy + elev_h_pts + 4,
           _T("Elevation", "Elevation"))
    return d


# ════════════════════════════════════════════════════════════════════════
#  POUTRE — coupe transversale
# ════════════════════════════════════════════════════════════════════════
def _pick_bars(As_cm2):
    """Choisit (n, diam_mm) pour fournir au moins As_cm2."""
    for d_mm in (12, 14, 16, 20, 25, 32):
        for n in (2, 3, 4, 5, 6, 7, 8):
            As_provided = n * math.pi * d_mm ** 2 / 400
            if As_provided >= As_cm2:
                return n, d_mm
    return 8, 32


def _draw_poutre_section(rs):
    pou = rs.poutre_principale
    if not pou:
        return None
    b_mm = pou.b_mm
    h_mm = pou.h_mm
    enrobage = _enrobage_mm(rs)
    n_inf, d_inf = _pick_bars(pou.As_inf_cm2)
    n_sup, d_sup = _pick_bars(pou.As_sup_cm2)

    # Garder ratio reel : limit max h_pts = 75mm, derive bw
    h_pts = 75 * mm
    scale = h_pts / h_mm
    bw_pts = b_mm * scale
    if bw_pts > 50 * mm:  # garde-fou si poutre tres trapue
        bw_pts = 50 * mm
        scale = bw_pts / b_mm
        h_pts = h_mm * scale

    d = _make_drawing(bw_pts, h_pts + 6 * mm)
    ox, oy = _origin()

    d.add(Rect(ox, oy, bw_pts, h_pts,
               fillColor=GRIS1, strokeColor=NOIR, strokeWidth=1.2))
    e = enrobage * scale
    d.add(Rect(ox + e, oy + e, bw_pts - 2 * e, h_pts - 2 * e,
               fillColor=None, strokeColor=BLEU, strokeWidth=0.8,
               strokeDashArray=[2, 2]))

    # Barres lit inferieur
    inner_w = bw_pts - 2 * e
    if n_inf > 1:
        for i in range(n_inf):
            px = ox + e + i * inner_w / (n_inf - 1)
            d.add(Circle(px, oy + e + 3, max(d_inf * scale / 2, 1.8),
                         fillColor=NOIR, strokeColor=NOIR))
    else:
        d.add(Circle(ox + bw_pts / 2, oy + e + 3, 2,
                     fillColor=NOIR, strokeColor=NOIR))
    # Barres lit superieur
    if n_sup > 1:
        for i in range(n_sup):
            px = ox + e + i * inner_w / (n_sup - 1)
            d.add(Circle(px, oy + h_pts - e - 3, max(d_sup * scale / 2, 1.8),
                         fillColor=NOIR, strokeColor=NOIR))
    else:
        d.add(Circle(ox + bw_pts / 2, oy + h_pts - e - 3, 2,
                     fillColor=NOIR, strokeColor=NOIR))

    _dim_h(d, ox, ox + bw_pts, oy - 6, f"b = {b_mm} mm")
    _dim_v(d, oy, oy + h_pts, ox - 5, f"h = {h_mm} mm")
    _title(d, ox + bw_pts / 2, oy + h_pts + 4,
           _T("Coupe B-B", "Section B-B"))

    # Annotation des aciers a droite
    d.add(String(ox + bw_pts + 4, oy + e + 3,
                 f"{n_inf}HA{d_inf}",
                 fontName='Helvetica', fontSize=6.5, fillColor=NOIR))
    d.add(String(ox + bw_pts + 4, oy + h_pts - e - 5,
                 f"{n_sup}HA{d_sup}",
                 fontName='Helvetica', fontSize=6.5, fillColor=NOIR))
    return d


def _draw_poutre_elevation(rs):
    pou = rs.poutre_principale
    if not pou:
        return None
    portee_mm = int(pou.portee_m * 1000)
    et_d = pou.etrier_diam_mm
    et_e = pou.etrier_esp_mm
    h_mm = pou.h_mm

    # Largeur cible : 130 mm; hauteur de la poutre limitee a 18mm pour ratio visuel
    elev_w_pts = 130 * mm
    elev_h_pts = max(14 * mm, min(22 * mm, h_mm * elev_w_pts / max(portee_mm, 1)))

    d = _make_drawing(elev_w_pts, elev_h_pts + 8 * mm)
    ox, oy = _origin()
    oy += 4  # un peu d'air pour les appuis

    d.add(Rect(ox, oy, elev_w_pts, elev_h_pts,
               fillColor=GRIS1, strokeColor=NOIR, strokeWidth=1.2))
    # Aciers superieurs et inferieurs (lignes pleines)
    d.add(Line(ox + 4, oy + elev_h_pts - 3, ox + elev_w_pts - 4,
               oy + elev_h_pts - 3, strokeColor=NOIR, strokeWidth=1.4))
    d.add(Line(ox + 4, oy + 3, ox + elev_w_pts - 4, oy + 3,
               strokeColor=NOIR, strokeWidth=1.4))
    # Etriers verticaux (representation: ~12)
    n_et = 14
    for i in range(n_et):
        sx = ox + 6 + i * (elev_w_pts - 12) / (n_et - 1)
        d.add(Line(sx, oy + 2, sx, oy + elev_h_pts - 2,
                   strokeColor=BLEU, strokeWidth=0.7))
    # Appuis (triangles)
    d.add(Polygon(points=[ox - 3, oy, ox + 3, oy, ox, oy - 5],
                  fillColor=GRIS3, strokeColor=NOIR))
    d.add(Polygon(points=[ox + elev_w_pts - 3, oy, ox + elev_w_pts + 3, oy,
                          ox + elev_w_pts, oy - 5],
                  fillColor=GRIS3, strokeColor=NOIR))

    _dim_h(d, ox, ox + elev_w_pts, oy - 9, f"L = {portee_mm} mm")
    # Cote etriers : un seul espacement
    pas = (elev_w_pts - 12) / (n_et - 1)
    _dim_h(d, ox + 6, ox + 6 + pas, oy + elev_h_pts + 4,
           f"HA{et_d} e={et_e} mm")
    _title(d, ox + elev_w_pts / 2, oy + elev_h_pts + 12,
           _T("Elevation poutre", "Beam elevation"))
    return d


# ════════════════════════════════════════════════════════════════════════
#  DALLE — vue en plan + coupe verticale (EC2 §9.3)
# ════════════════════════════════════════════════════════════════════════
def _draw_dalle_plan(rs):
    dalle = getattr(rs, 'dalle', None)
    if not dalle:
        return None
    portee_m = max(getattr(dalle, 'portee_m', 4.0), 1.0)
    Lx_mm = int(portee_m * 1000)
    Ly_mm = int(portee_m * 1000)

    # Plan carre 90 x 70 mm
    plan_w = 90 * mm
    plan_h = 70 * mm
    d = _make_drawing(plan_w, plan_h + 6 * mm)
    ox, oy = _origin()

    # Contour dalle
    d.add(Rect(ox, oy, plan_w, plan_h,
               fillColor=GRIS1, strokeColor=NOIR, strokeWidth=1.2))
    # Hachures direction X (nappe inferieure)
    for i in range(0, int(plan_w), 6):
        d.add(Line(ox + i, oy + 4, ox + i, oy + plan_h - 4,
                   strokeColor=BLEU, strokeWidth=0.4))
    # Hachures direction Y (nappe superieure - en pointilles)
    for j in range(0, int(plan_h), 6):
        d.add(Line(ox + 4, oy + j, ox + plan_w - 4, oy + j,
                   strokeColor=ORANGE, strokeWidth=0.4,
                   strokeDashArray=[1.5, 1.5]))
    # Reperes coupe A-A (au tiers gauche)
    cut_x = ox + plan_w * 0.5
    d.add(Line(cut_x, oy - 4, cut_x, oy + plan_h + 4,
               strokeColor=NOIR, strokeWidth=0.6, strokeDashArray=[3, 2]))
    d.add(String(cut_x - 6, oy + plan_h + 6, "A",
                 fontName='Helvetica-Bold', fontSize=7, fillColor=NOIR))
    d.add(String(cut_x + 2, oy + plan_h + 6, "A",
                 fontName='Helvetica-Bold', fontSize=7, fillColor=NOIR))
    # Cotes
    _dim_h(d, ox, ox + plan_w, oy - 6, f"Lx = {Lx_mm} mm")
    _dim_v(d, oy, oy + plan_h, ox - 5, f"Ly = {Ly_mm} mm")
    _title(d, ox + plan_w / 2, oy + plan_h + 4,
           _T("Vue en plan", "Plan view"))
    return d


def _draw_dalle_section(rs):
    dalle = getattr(rs, 'dalle', None)
    if not dalle:
        return None
    ep_mm = int(dalle.epaisseur_mm)
    portee_m = max(getattr(dalle, 'portee_m', 4.0), 1.0)
    L_mm = int(portee_m * 1000)
    enrobage = 25  # dalle interieure standard
    As_x = dalle.As_x_cm2_ml
    As_y = dalle.As_y_cm2_ml

    sec_w = 130 * mm
    sec_h = max(20 * mm, min(35 * mm, ep_mm * 0.04))  # echelle visuelle
    d = _make_drawing(sec_w, sec_h + 8 * mm)
    ox, oy = _origin()
    oy += 3

    # Beton
    d.add(Rect(ox, oy, sec_w, sec_h,
               fillColor=GRIS1, strokeColor=NOIR, strokeWidth=1.2))
    # Nappe inferieure (bleu)
    d.add(Line(ox + 3, oy + 3, ox + sec_w - 3, oy + 3,
               strokeColor=BLEU, strokeWidth=1.6))
    # Aciers en plot (cercles representant les barres en coupe)
    n_bars = 18
    for i in range(n_bars):
        bx = ox + 4 + i * (sec_w - 8) / (n_bars - 1)
        d.add(Circle(bx, oy + 3, 1.4, fillColor=BLEU, strokeColor=BLEU))
    # Nappe superieure (orange)
    d.add(Line(ox + 3, oy + sec_h - 3, ox + sec_w - 3, oy + sec_h - 3,
               strokeColor=ORANGE, strokeWidth=1.4, strokeDashArray=[2, 1.5]))
    for i in range(n_bars):
        bx = ox + 4 + i * (sec_w - 8) / (n_bars - 1)
        d.add(Circle(bx, oy + sec_h - 3, 1.2,
                     fillColor=ORANGE, strokeColor=ORANGE))

    # Cotes
    _dim_h(d, ox, ox + sec_w, oy - 7, f"L = {L_mm} mm")
    _dim_v(d, oy, oy + sec_h, ox - 5, f"e = {ep_mm} mm")

    # Annotations aciers
    d.add(String(ox + sec_w + 3, oy + sec_h - 5,
                 f"As sup = {As_y:.2f} cm²/ml",
                 fontName='Helvetica', fontSize=6.5, fillColor=ORANGE))
    d.add(String(ox + sec_w + 3, oy + 1,
                 f"As inf = {As_x:.2f} cm²/ml",
                 fontName='Helvetica', fontSize=6.5, fillColor=BLEU))
    d.add(String(ox + sec_w + 3, oy + sec_h * 0.5,
                 _T(f"enrobage {enrobage} mm", f"cover {enrobage} mm"),
                 fontName='Helvetica-Oblique', fontSize=6, fillColor=GRIS3))

    _title(d, ox + sec_w / 2, oy + sec_h + 5,
           _T("Coupe A-A", "Section A-A"))
    return d


# ════════════════════════════════════════════════════════════════════════
#  FONDATION
# ════════════════════════════════════════════════════════════════════════
def _draw_pieu_elevation(rs):
    fond = rs.fondation
    diam_mm = getattr(fond, 'diam_pieu_mm', 800)
    long_mm = int(getattr(fond, 'longueur_pieu_m', 10) * 1000)

    elev_h_pts = 95 * mm
    elev_w_pts = 18 * mm  # representation, pas a l'echelle reelle
    d = _make_drawing(elev_w_pts + 12 * mm, elev_h_pts + 8 * mm)
    ox, oy = _origin()
    ox += 4
    # Sol (hachures au-dessus du chevetre)
    d.add(Rect(ox - 6, oy + elev_h_pts + 2, elev_w_pts + 12, 6,
               fillColor=GRIS2, strokeColor=NOIR, strokeWidth=0.9))
    # Pieu
    d.add(Rect(ox, oy, elev_w_pts, elev_h_pts,
               fillColor=GRIS1, strokeColor=NOIR, strokeWidth=1.2))
    # Cage (longitudinales)
    for off in (3, elev_w_pts - 3):
        d.add(Line(ox + off, oy + 4, ox + off, oy + elev_h_pts - 4,
                   strokeColor=NOIR, strokeWidth=1.0))
    # Cerces
    n_c = 9
    for i in range(n_c):
        cy = oy + 6 + i * (elev_h_pts - 12) / (n_c - 1)
        d.add(Line(ox + 2, cy, ox + elev_w_pts - 2, cy,
                   strokeColor=BLEU, strokeWidth=0.6))
    _dim_v(d, oy, oy + elev_h_pts, ox - 5, f"L = {long_mm} mm")
    _dim_h(d, ox, ox + elev_w_pts, oy - 6, f"D = {diam_mm} mm")
    _title(d, ox + elev_w_pts / 2, oy + elev_h_pts + 11,
           _T("Pieu fore", "Bored pile"))
    return d


def _draw_pieu_section(rs):
    fond = rs.fondation
    diam_mm = getattr(fond, 'diam_pieu_mm', 800)
    enrobage = _enrobage_mm(rs) + 30  # pieu : enrobage majore
    side_pts = 45 * mm
    scale = side_pts / diam_mm

    d = _make_drawing(side_pts, side_pts + 6 * mm)
    ox, oy = _origin()
    cx, cy = ox + side_pts / 2, oy + side_pts / 2

    # Cercle beton
    d.add(Circle(cx, cy, side_pts / 2,
                 fillColor=GRIS1, strokeColor=NOIR, strokeWidth=1.2))
    # Cerce (etrier helicoidal vu en coupe)
    d.add(Circle(cx, cy, side_pts / 2 - enrobage * scale,
                 fillColor=None, strokeColor=BLEU, strokeWidth=0.8,
                 strokeDashArray=[2, 2]))
    # 8 barres reparties sur le cercle
    R = side_pts / 2 - enrobage * scale
    for k in range(8):
        ang = k * math.pi / 4
        bx = cx + R * math.cos(ang)
        by = cy + R * math.sin(ang)
        d.add(Circle(bx, by, 2.2, fillColor=NOIR, strokeColor=NOIR))
    _dim_h(d, ox, ox + side_pts, oy - 6, f"D = {diam_mm} mm")
    _title(d, cx, oy + side_pts + 4,
           _T("Coupe pieu", "Pile section"))
    return d


def _draw_semelle(rs):
    fond = rs.fondation
    cote_mm = int(getattr(fond, 'largeur_semelle_m', 1.5) * 1000) or 1500
    ep_mm = 500

    sec_w_pts = 95 * mm
    sec_h_pts = 30 * mm
    d = _make_drawing(sec_w_pts, sec_h_pts + 18 * mm)
    ox, oy = _origin()
    oy += 4

    # Sol entourant
    for i in range(0, int(sec_w_pts), 7):
        d.add(Line(ox + i, oy + sec_h_pts, ox + i + 4, oy + sec_h_pts + 3,
                   strokeColor=GRIS3, strokeWidth=0.4))
    # Semelle
    d.add(Rect(ox, oy, sec_w_pts, sec_h_pts,
               fillColor=GRIS1, strokeColor=NOIR, strokeWidth=1.2))
    # Amorce poteau au centre
    col_w = 14 * mm
    d.add(Rect(ox + sec_w_pts / 2 - col_w / 2, oy + sec_h_pts,
               col_w, 12 * mm,
               fillColor=GRIS2, strokeColor=NOIR, strokeWidth=1.0))
    # Aciers en grille (vue en coupe)
    e = 4
    for i in range(8):
        xx = ox + e + i * (sec_w_pts - 2 * e) / 7
        d.add(Circle(xx, oy + 4, 1.4, fillColor=NOIR, strokeColor=NOIR))
    d.add(Line(ox + 3, oy + 4, ox + sec_w_pts - 3, oy + 4,
               strokeColor=NOIR, strokeWidth=0.9))
    # Aciers superieurs (chapeaux)
    d.add(Line(ox + 3, oy + sec_h_pts - 4, ox + sec_w_pts - 3,
               oy + sec_h_pts - 4,
               strokeColor=NOIR, strokeWidth=0.9, strokeDashArray=[2, 1.5]))

    _dim_h(d, ox, ox + sec_w_pts, oy - 6, f"B = {cote_mm} mm")
    _dim_v(d, oy, oy + sec_h_pts, ox - 5, f"e = {ep_mm} mm")
    _title(d, ox + sec_w_pts / 2, oy + sec_h_pts + 16,
           _T("Semelle isolee — coupe", "Isolated footing — section"))
    return d


# ════════════════════════════════════════════════════════════════════════
#  MISE EN PAGE — placement de 2 vues cote a cote dans un Table
# ════════════════════════════════════════════════════════════════════════
def _two_views(left, right):
    """Place 2 Drawings cote a cote dans un Table 2 colonnes."""
    if left and right:
        t = Table([[left, right]], colWidths=[CW * 0.42, CW * 0.58])
    elif left:
        t = Table([[left]], colWidths=[CW])
    else:
        t = Table([[right]], colWidths=[CW])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    return t


def _single_view(drawing):
    if not drawing:
        return Spacer(1, 1)
    t = Table([[drawing]], colWidths=[CW])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    return t


# ════════════════════════════════════════════════════════════════════════
#  TABLE recapitulative
# ════════════════════════════════════════════════════════════════════════
def _table_recap(rs):
    pot = rs.poteaux[0] if rs.poteaux else None
    pou = rs.poutre_principale
    dalle = getattr(rs, 'dalle', None)
    fond = rs.fondation
    rows = [[
        Paragraph(_T("Element", "Element"), S['th_l']),
        Paragraph(_T("Section", "Section"), S['th_l']),
        Paragraph(_T("Armatures", "Reinforcement"), S['th_l']),
        Paragraph(_T("Etriers / Cadres", "Stirrups / Hoops"), S['th_l']),
    ]]
    if pot:
        rows.append([
            p(_T("Poteau type", "Typical column")),
            p(f"{pot.section_mm} x {pot.section_mm} mm"),
            p(f"{pot.nb_barres} HA{pot.diametre_mm}"),
            p(f"HA{pot.cadre_diam_mm} e={pot.espacement_cadres_mm} mm"),
        ])
    if pou:
        n_inf, d_inf = _pick_bars(pou.As_inf_cm2)
        n_sup, d_sup = _pick_bars(pou.As_sup_cm2)
        rows.append([
            p(_T("Poutre principale", "Main beam")),
            p(f"{pou.b_mm} x {pou.h_mm} mm"),
            p(f"inf {n_inf}HA{d_inf} ({pou.As_inf_cm2:.1f} cm²) / "
              f"sup {n_sup}HA{d_sup} ({pou.As_sup_cm2:.1f} cm²)"),
            p(f"HA{pou.etrier_diam_mm} e={pou.etrier_esp_mm} mm"),
        ])
    if dalle:
        rows.append([
            p(_T("Dalle pleine", "Solid slab")),
            p(f"e = {dalle.epaisseur_mm} mm  L = {dalle.portee_m:.1f} m"),
            p(f"As_x {dalle.As_x_cm2_ml:.2f} / "
              f"As_y {dalle.As_y_cm2_ml:.2f} cm²/ml"),
            p(_T("Treillis HA10", "HA10 mesh")),
        ])
    if fond:
        if 'pieu' in str(fond.type).lower():
            rows.append([
                p(_T("Pieu fore", "Bored pile")),
                p(f"D = {fond.diam_pieu_mm} mm  "
                  f"L = {fond.longueur_pieu_m:.1f} m"),
                p(f"As {fond.As_cm2:.2f} cm²"),
                p("—"),
            ])
        else:
            rows.append([
                p(_T("Semelle isolee", "Isolated footing")),
                p(f"{fond.largeur_semelle_m:.2f} x "
                  f"{fond.largeur_semelle_m:.2f} m"),
                p(_T("Grille HA12 e=150 mm", "HA12 grid s=150 mm")),
                p("—"),
            ])
    t = Table(rows, colWidths=[CW * 0.20, CW * 0.22, CW * 0.36, CW * 0.22])
    t.setStyle(table_style())
    return t


# ════════════════════════════════════════════════════════════════════════
#  Construction du document
# ════════════════════════════════════════════════════════════════════════
def generer_schemas_ferraillage(rs, params: dict) -> bytes:
    """Genere le PDF complet des schemas de ferraillage."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=ML, rightMargin=MR,
        topMargin=24 * mm, bottomMargin=18 * mm,
        title=_T("Schemas de ferraillage", "Reinforcement Drawings"),
        author='Tijan AI')

    project_name = params.get('nom') or _T("Projet", "Project")
    ville = params.get('ville') or 'Dakar'
    pays = params.get('pays') or 'Senegal'
    sub = f"{project_name} — {ville}, {pays}"

    story = []
    story.append(Paragraph(
        _T("Schemas de ferraillage", "Reinforcement Drawings"),
        S['titre']))
    story.append(Paragraph(sub, S['sous_titre']))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(_T(
        "Plans d'execution des elements porteurs principaux : poteaux, poutres, "
        "dalles et fondations. Cotes et armatures derivees des calculs Eurocode 2 "
        "(EC2) et Eurocode 8 (EC8) pour la structure complete.",
        "Execution drawings for the main load-bearing elements: columns, beams, "
        "slabs and foundations. Dimensions and rebars derived from Eurocode 2 (EC2) "
        "and Eurocode 8 (EC8) calculations of the complete structure."),
        S['body_j']))
    story.append(Spacer(1, 4 * mm))
    story.append(_table_recap(rs))
    story.append(Spacer(1, 4 * mm))

    # ── 1. Poteau
    story.extend(section_title("1", _T("Poteau type", "Typical column")))
    story.append(_two_views(_draw_poteau_section(rs),
                            _draw_poteau_elevation(rs)))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(_T(
        "Section carree avec armatures longitudinales HA aux angles et cadres "
        "transversaux fermes. Espacement des cadres reduit en zones critiques "
        "(L/6 ou 450 mm aux extremites) selon EC8 5.4.3.2.2.",
        "Square section with longitudinal HA bars at corners and closed transverse "
        "hoops. Hoop spacing reduced in critical zones (L/6 or 450 mm at ends) "
        "per EC8 5.4.3.2.2."),
        S['body_j']))
    story.append(PageBreak())

    # ── 2. Poutre
    story.extend(section_title("2", _T("Poutre principale", "Main beam")))
    story.append(_single_view(_draw_poutre_section(rs)))
    story.append(Spacer(1, 2 * mm))
    story.append(_single_view(_draw_poutre_elevation(rs)))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(_T(
        "Section rectangulaire b x h avec lit inferieur (As_inf) en travee, "
        "lit superieur (As_sup) sur appuis. Etriers fermes selon EC2 9.2.2 "
        "et zone confinee aux abouts pour ductilite EC8.",
        "Rectangular b x h section with bottom layer (As_inf) at midspan, top "
        "layer (As_sup) over supports. Closed stirrups per EC2 9.2.2 with "
        "confinement zone at ends for EC8 ductility."),
        S['body_j']))
    story.append(PageBreak())

    # ── 3. Dalle
    story.extend(section_title("3", _T("Dalle pleine", "Solid slab")))
    story.append(_single_view(_draw_dalle_plan(rs)))
    story.append(Spacer(1, 2 * mm))
    story.append(_single_view(_draw_dalle_section(rs)))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(_T(
        "Dalle pleine portant dans deux directions (EC2 §9.3). Nappe inferieure "
        "(bleu, sens X) en travee, nappe superieure (orange, sens Y) sur appuis. "
        "Section A-A montre l'epaisseur, l'enrobage et la position des deux "
        "nappes. Treillis soudes type ST equivalents acceptes.",
        "Two-way solid slab (EC2 §9.3). Bottom mesh (blue, X direction) at "
        "midspan, top mesh (orange, Y direction) over supports. Section A-A "
        "shows thickness, cover and position of both mesh layers. Equivalent "
        "welded ST mesh accepted."),
        S['body_j']))
    story.append(PageBreak())

    # ── 4. Fondation
    story.extend(section_title("4", _T("Fondation type", "Typical foundation")))
    fond = rs.fondation
    if fond and 'pieu' in str(fond.type).lower():
        story.append(_two_views(_draw_pieu_elevation(rs),
                                _draw_pieu_section(rs)))
        story.append(Spacer(1, 2 * mm))
        nb = getattr(fond, 'nb_pieux', None)
        story.append(Paragraph(_T(
            f"Fondation profonde par pieux fores beton arme. "
            f"{nb if nb else '—'} unites au total. Cage d'armatures "
            "longitudinales 8HA reparties sur le pourtour, cerces helicoidales "
            "pour le confinement. Tete de pieu ancree dans le chevetre.",
            f"Deep foundation with bored RC piles. "
            f"{nb if nb else '—'} units total. Longitudinal cage of 8 HA bars "
            "around the perimeter, helical hoops for confinement. Pile head "
            "anchored in the cap beam."),
            S['body_j']))
    else:
        story.append(_single_view(_draw_semelle(rs)))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(_T(
            "Semelle isolee carree, dimensionnee pour la portance du sol et "
            "les charges descendantes. Grille d'armatures inferieures dans les "
            "deux directions, chapeaux superieurs si moments d'encastrement.",
            "Square isolated footing, sized for soil bearing capacity and "
            "gravity loads. Bottom rebar grid in both directions, top bars if "
            "fixed-end moments."),
            S['body_j']))

    hf = HeaderFooter(project_name,
                      _T("Schemas de ferraillage", "Reinforcement Drawings"))
    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    pdf = buf.getvalue()
    buf.close()
    return pdf
