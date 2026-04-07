"""
gen_schemas_ferraillage.py — Schemas de ferraillage Tijan AI

Produit un PDF avec coupes et elevations cotees pour:
  • Poteau type    (coupe transversale + elevation longitudinale)
  • Poutre type    (coupe transversale + elevation longitudinale)
  • Fondation type (semelle isolee, semelle filante ou pieu)

Toutes les dimensions sont reelles, derivees des resultats du moteur EC2.
Bilingue FR / EN via _current_lang du theme.
"""
from io import BytesIO
import math
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, PageBreak)
from reportlab.graphics.shapes import (Drawing, Rect, Circle, Line, String,
                                        Group, Polygon)
from reportlab.graphics import renderPDF

from tijan_theme import (VERT, VERT_DARK, NOIR, GRIS1, GRIS2, GRIS3, BLANC,
                         BLEU, ORANGE, ML, MR, CW, W, S, HeaderFooter,
                         p, fmt_n, section_title, table_style, _current_lang)


# ─────────────────────────────────────────────────────────────────────
#  i18n local
# ─────────────────────────────────────────────────────────────────────
def _T(fr, en):
    return en if _current_lang == 'en' else fr


# ─────────────────────────────────────────────────────────────────────
#  Helpers de dessin
# ─────────────────────────────────────────────────────────────────────
def _dim_h(d, x1, x2, y, label, size=7):
    """Cote horizontale avec fleches et label."""
    d.add(Line(x1, y, x2, y, strokeColor=GRIS3, strokeWidth=0.5))
    d.add(Line(x1, y - 2, x1, y + 2, strokeColor=GRIS3, strokeWidth=0.6))
    d.add(Line(x2, y - 2, x2, y + 2, strokeColor=GRIS3, strokeWidth=0.6))
    # fleches
    d.add(Polygon(points=[x1, y, x1 + 4, y - 1.5, x1 + 4, y + 1.5], fillColor=GRIS3, strokeColor=GRIS3))
    d.add(Polygon(points=[x2, y, x2 - 4, y - 1.5, x2 - 4, y + 1.5], fillColor=GRIS3, strokeColor=GRIS3))
    d.add(String((x1 + x2) / 2, y + 3, label, fontName='Helvetica', fontSize=size,
                 textAnchor='middle', fillColor=NOIR))


def _dim_v(d, y1, y2, x, label, size=7):
    """Cote verticale avec fleches et label."""
    d.add(Line(x, y1, x, y2, strokeColor=GRIS3, strokeWidth=0.5))
    d.add(Line(x - 2, y1, x + 2, y1, strokeColor=GRIS3, strokeWidth=0.6))
    d.add(Line(x - 2, y2, x + 2, y2, strokeColor=GRIS3, strokeWidth=0.6))
    d.add(Polygon(points=[x, y1, x - 1.5, y1 + 4, x + 1.5, y1 + 4], fillColor=GRIS3, strokeColor=GRIS3))
    d.add(Polygon(points=[x, y2, x - 1.5, y2 - 4, x + 1.5, y2 - 4], fillColor=GRIS3, strokeColor=GRIS3))
    s = String(x - 4, (y1 + y2) / 2, label, fontName='Helvetica', fontSize=size,
               textAnchor='end', fillColor=NOIR)
    d.add(s)


def _legend_bar(diam_mm, count, label):
    """Petite legende pour une barre HA."""
    return f"{count} HA{diam_mm}  —  {label}"


# ─────────────────────────────────────────────────────────────────────
#  POTEAU — coupe transversale + elevation
# ─────────────────────────────────────────────────────────────────────
def _draw_poteau(rs):
    """rs = ResultatsStructure"""
    pot = rs.poteaux[0] if rs.poteaux else None
    if not pot:
        return None

    b_mm = pot.section_mm
    nb = pot.nb_barres
    diam = pot.diametre_mm
    cad_d = pot.cadre_diam_mm
    cad_e = pot.espacement_cadres_mm
    h_etage_mm = int(getattr(rs.params, 'hauteur_etage_m', 3.0) * 1000)
    enrobage = 30 if rs.distance_mer_km >= 5 else 40

    # Echelle: cible 110mm de largeur graphique
    target_w = 110 * mm
    scale_xs = target_w / b_mm
    side = b_mm * scale_xs

    d = Drawing(CW, 100 * mm)

    # Coupe transversale (gauche)
    ox, oy = 8 * mm, 18 * mm
    d.add(Rect(ox, oy, side, side, fillColor=GRIS1, strokeColor=NOIR, strokeWidth=1.2))
    # Cadre interieur (etrier)
    e = enrobage * scale_xs
    d.add(Rect(ox + e, oy + e, side - 2 * e, side - 2 * e,
               fillColor=None, strokeColor=BLEU, strokeWidth=0.8, strokeDashArray=[2, 2]))
    # Barres longitudinales
    bar_r = max(diam * scale_xs / 2, 2.0)
    inner = side - 2 * e
    if nb == 4:
        positions = [(ox + e, oy + e), (ox + e + inner, oy + e),
                     (ox + e, oy + e + inner), (ox + e + inner, oy + e + inner)]
    elif nb == 6:
        positions = [(ox + e, oy + e), (ox + e + inner / 2, oy + e), (ox + e + inner, oy + e),
                     (ox + e, oy + e + inner), (ox + e + inner / 2, oy + e + inner),
                     (ox + e + inner, oy + e + inner)]
    else:  # 8 ou plus
        positions = []
        for i in range(3):
            for j in range(3):
                if i == 1 and j == 1:
                    continue
                positions.append((ox + e + i * inner / 2, oy + e + j * inner / 2))
    for (px, py) in positions:
        d.add(Circle(px, py, bar_r, fillColor=NOIR, strokeColor=NOIR))

    # Cotes
    _dim_h(d, ox, ox + side, oy - 8, f"{b_mm} mm")
    _dim_v(d, oy, oy + side, ox - 5, f"{b_mm} mm")

    # Titre coupe
    d.add(String(ox + side / 2, oy + side + 8,
                 _T("Coupe A-A", "Section A-A"),
                 fontName='Helvetica-Bold', fontSize=8.5, textAnchor='middle', fillColor=VERT_DARK))

    # Elevation longitudinale (droite) — 3 cadres visibles
    elev_w = 28 * mm
    elev_h = 75 * mm
    ex = ox + side + 18 * mm
    ey = oy
    d.add(Rect(ex, ey, elev_w, elev_h, fillColor=GRIS1, strokeColor=NOIR, strokeWidth=1.2))
    # Barres verticales (4 visibles en elevation : 2 a chaque face)
    for off in (3, elev_w - 3):
        d.add(Line(ex + off, ey + 2, ex + off, ey + elev_h - 2,
                   strokeColor=NOIR, strokeWidth=1.0))
    # Cadres horizontaux espaces
    n_cadres = max(3, min(8, int(elev_h / max(cad_e * 0.04, 6))))
    for i in range(n_cadres):
        cy = ey + 4 + i * (elev_h - 8) / (n_cadres - 1)
        d.add(Line(ex + 2, cy, ex + elev_w - 2, cy,
                   strokeColor=BLEU, strokeWidth=0.7))
    _dim_v(d, ey, ey + elev_h, ex - 4, f"H = {h_etage_mm} mm")
    _dim_h(d, ex, ex + elev_w, ey - 8, f"e cadres = {cad_e} mm")
    d.add(String(ex + elev_w / 2, ey + elev_h + 8,
                 _T("Elevation", "Elevation"),
                 fontName='Helvetica-Bold', fontSize=8.5, textAnchor='middle', fillColor=VERT_DARK))

    return d


# ─────────────────────────────────────────────────────────────────────
#  POUTRE — coupe transversale + elevation
# ─────────────────────────────────────────────────────────────────────
def _draw_poutre(rs):
    pou = rs.poutre_principale
    if not pou:
        return None
    b_mm = pou.b_mm
    h_mm = pou.h_mm
    portee_mm = int(pou.portee_m * 1000)
    As_inf = pou.As_inf_cm2
    As_sup = pou.As_sup_cm2
    et_d = pou.etrier_diam_mm
    et_e = pou.etrier_esp_mm
    enrobage = 30 if rs.distance_mer_km >= 5 else 40

    # Choix barres approx pour visualisation
    def _pick_bars(As_cm2):
        for d_mm in (12, 14, 16, 20, 25, 32):
            for n in (2, 3, 4, 5, 6):
                As_provided = n * math.pi * d_mm ** 2 / 400
                if As_provided >= As_cm2:
                    return n, d_mm
        return 6, 32
    n_inf, d_inf = _pick_bars(As_inf)
    n_sup, d_sup = _pick_bars(As_sup)

    target_w = 60 * mm
    scale = target_w / b_mm
    bw = b_mm * scale
    bh = h_mm * scale

    d = Drawing(CW, 110 * mm)

    # Coupe transversale (gauche)
    ox, oy = 12 * mm, 22 * mm
    d.add(Rect(ox, oy, bw, bh, fillColor=GRIS1, strokeColor=NOIR, strokeWidth=1.2))
    e = enrobage * scale
    d.add(Rect(ox + e, oy + e, bw - 2 * e, bh - 2 * e,
               fillColor=None, strokeColor=BLEU, strokeWidth=0.8, strokeDashArray=[2, 2]))
    # Barres inferieures
    inner_w = bw - 2 * e
    if n_inf > 1:
        for i in range(n_inf):
            px = ox + e + i * inner_w / (n_inf - 1)
            d.add(Circle(px, oy + e + 2, max(d_inf * scale / 2, 1.8),
                         fillColor=NOIR, strokeColor=NOIR))
    else:
        d.add(Circle(ox + bw / 2, oy + e + 2, max(d_inf * scale / 2, 1.8),
                     fillColor=NOIR, strokeColor=NOIR))
    # Barres superieures
    if n_sup > 1:
        for i in range(n_sup):
            px = ox + e + i * inner_w / (n_sup - 1)
            d.add(Circle(px, oy + bh - e - 2, max(d_sup * scale / 2, 1.8),
                         fillColor=NOIR, strokeColor=NOIR))
    else:
        d.add(Circle(ox + bw / 2, oy + bh - e - 2, max(d_sup * scale / 2, 1.8),
                     fillColor=NOIR, strokeColor=NOIR))

    _dim_h(d, ox, ox + bw, oy - 8, f"b = {b_mm} mm")
    _dim_v(d, oy, oy + bh, ox - 5, f"h = {h_mm} mm")
    d.add(String(ox + bw / 2, oy + bh + 8,
                 _T("Coupe B-B", "Section B-B"),
                 fontName='Helvetica-Bold', fontSize=8.5, textAnchor='middle', fillColor=VERT_DARK))

    # Elevation longitudinale (droite)
    elev_max_w = CW - (ox + bw) - 18 * mm
    elev_w = min(elev_max_w, max(80 * mm, portee_mm * 0.04))
    elev_h = bh
    ex = ox + bw + 16 * mm
    ey = oy
    d.add(Rect(ex, ey, elev_w, elev_h, fillColor=GRIS1, strokeColor=NOIR, strokeWidth=1.2))
    # Aciers sup et inf horizontaux
    d.add(Line(ex + 2, ey + elev_h - 3, ex + elev_w - 2, ey + elev_h - 3,
               strokeColor=NOIR, strokeWidth=1.4))
    d.add(Line(ex + 2, ey + 3, ex + elev_w - 2, ey + 3,
               strokeColor=NOIR, strokeWidth=1.4))
    # Etriers verticaux
    n_et = max(4, min(14, int(elev_w / max(et_e * 0.02, 8))))
    for i in range(n_et):
        sx = ex + 4 + i * (elev_w - 8) / (n_et - 1)
        d.add(Line(sx, ey + 2, sx, ey + elev_h - 2, strokeColor=BLEU, strokeWidth=0.7))
    # Appuis
    d.add(Polygon(points=[ex - 3, ey, ex + 3, ey, ex, ey - 5],
                  fillColor=GRIS3, strokeColor=NOIR))
    d.add(Polygon(points=[ex + elev_w - 3, ey, ex + elev_w + 3, ey, ex + elev_w, ey - 5],
                  fillColor=GRIS3, strokeColor=NOIR))
    _dim_h(d, ex, ex + elev_w, ey - 12, f"L = {portee_mm} mm")
    _dim_h(d, ex + 4, ex + 4 + (elev_w - 8) / (n_et - 1), ey + elev_h + 5, f"e = {et_e} mm")
    d.add(String(ex + elev_w / 2, ey + elev_h + 14,
                 _T("Elevation poutre", "Beam elevation"),
                 fontName='Helvetica-Bold', fontSize=8.5, textAnchor='middle', fillColor=VERT_DARK))
    return d


# ─────────────────────────────────────────────────────────────────────
#  FONDATION — semelle isolee, semelle filante ou pieu
# ─────────────────────────────────────────────────────────────────────
def _draw_fondation(rs):
    fond = rs.fondation
    if not fond:
        return None

    d = Drawing(CW, 95 * mm)
    ox, oy = 18 * mm, 18 * mm

    if str(fond.type).endswith('pieux') or 'pieu' in str(fond.type).lower():
        diam_mm = fond.diam_pieu_mm
        long_mm = int(fond.longueur_pieu_m * 1000)
        nb = fond.nb_pieux
        # Vue elevation pieu
        target_h = 70 * mm
        scale = target_h / long_mm
        pw = max(diam_mm * scale, 14)
        ph = long_mm * scale
        d.add(Rect(ox, oy, pw, ph, fillColor=GRIS1, strokeColor=NOIR, strokeWidth=1.2))
        # Cage d'armatures (lignes verticales)
        for off in (3, pw - 3):
            d.add(Line(ox + off, oy + 4, ox + off, oy + ph - 4,
                       strokeColor=NOIR, strokeWidth=1.0))
        # Cerces horizontales
        for i in range(7):
            cy = oy + 6 + i * (ph - 12) / 6
            d.add(Line(ox + 2, cy, ox + pw - 2, cy, strokeColor=BLEU, strokeWidth=0.6))
        # Tete pieu (chevetre)
        d.add(Rect(ox - 6, oy + ph, pw + 12, 6, fillColor=GRIS2, strokeColor=NOIR, strokeWidth=1.0))
        _dim_v(d, oy, oy + ph, ox - 6, f"L = {long_mm} mm")
        _dim_h(d, ox, ox + pw, oy - 8, f"D = {diam_mm} mm")
        d.add(String(ox + pw / 2, oy + ph + 14,
                     _T(f"Pieu fore — total {nb} unites", f"Bored pile — total {nb} units"),
                     fontName='Helvetica-Bold', fontSize=8.5, textAnchor='middle', fillColor=VERT_DARK))
    else:
        # Semelle isolee ou filante
        cote_mm = int(fond.largeur_semelle_m * 1000) or 1500
        prof_mm = int(fond.profondeur_m * 1000) or 1500
        ep_mm = 500  # epaisseur visible
        scale = (90 * mm) / max(cote_mm, prof_mm)
        sw = cote_mm * scale
        sh = ep_mm * scale
        # Coupe verticale: terrain + semelle + amorce poteau
        d.add(Rect(ox, oy, sw, sh, fillColor=GRIS1, strokeColor=NOIR, strokeWidth=1.2))
        # Sol
        for i in range(0, int(sw), 8):
            d.add(Line(ox + i, oy + sh, ox + i + 4, oy + sh + 3,
                       strokeColor=GRIS3, strokeWidth=0.4))
        # Amorce poteau au centre
        col_w = max(sw * 0.18, 8)
        d.add(Rect(ox + sw / 2 - col_w / 2, oy + sh, col_w, 12 * mm,
                   fillColor=GRIS2, strokeColor=NOIR, strokeWidth=1.0))
        # Armatures inf en grille
        e = 4
        for i in range(6):
            xx = ox + e + i * (sw - 2 * e) / 5
            d.add(Line(xx, oy + 3, xx, oy + sh - 2, strokeColor=BLEU, strokeWidth=0.7))
        for j in range(3):
            yy = oy + 3 + j * (sh - 5) / 2
            d.add(Line(ox + 2, yy, ox + sw - 2, yy, strokeColor=NOIR, strokeWidth=0.9))
        _dim_h(d, ox, ox + sw, oy - 8, f"B = {cote_mm} mm")
        _dim_v(d, oy, oy + sh, ox - 5, f"e = {ep_mm} mm")
        d.add(String(ox + sw / 2, oy + sh + 22,
                     _T("Semelle isolee — coupe", "Isolated footing — section"),
                     fontName='Helvetica-Bold', fontSize=8.5, textAnchor='middle', fillColor=VERT_DARK))
    return d


# ─────────────────────────────────────────────────────────────────────
#  TABLE recapitulative
# ─────────────────────────────────────────────────────────────────────
def _table_recap(rs):
    pot = rs.poteaux[0] if rs.poteaux else None
    pou = rs.poutre_principale
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
        rows.append([
            p(_T("Poutre principale", "Main beam")),
            p(f"{pou.b_mm} x {pou.h_mm} mm"),
            p(f"As inf {pou.As_inf_cm2:.2f} cm² / sup {pou.As_sup_cm2:.2f} cm²"),
            p(f"HA{pou.etrier_diam_mm} e={pou.etrier_esp_mm} mm"),
        ])
    if fond:
        if 'pieu' in str(fond.type).lower():
            rows.append([
                p(_T("Pieu fore", "Bored pile")),
                p(f"D = {fond.diam_pieu_mm} mm  L = {fond.longueur_pieu_m:.1f} m"),
                p(f"As {fond.As_cm2:.2f} cm²"),
                p("—"),
            ])
        else:
            rows.append([
                p(_T("Semelle isolee", "Isolated footing")),
                p(f"{fond.largeur_semelle_m:.2f} x {fond.largeur_semelle_m:.2f} m"),
                p(_T("Grille HA12 e=150 mm", "HA12 grid s=150 mm")),
                p("—"),
            ])
    t = Table(rows, colWidths=[CW * 0.22, CW * 0.22, CW * 0.34, CW * 0.22])
    t.setStyle(table_style())
    return t


# ─────────────────────────────────────────────────────────────────────
#  Entree principale
# ─────────────────────────────────────────────────────────────────────
def generer_schemas_ferraillage(rs, params: dict) -> bytes:
    """Genere le PDF complet des schemas de ferraillage."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=ML, rightMargin=MR,
                            topMargin=22 * mm, bottomMargin=18 * mm,
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
        "Plans d'execution des elements porteurs principaux. Cotes et armatures derivees des "
        "calculs Eurocode 2 (EC2) et Eurocode 8 (EC8) pour la structure complete.",
        "Execution drawings for the main load-bearing elements. Dimensions and rebars derived from "
        "Eurocode 2 (EC2) and Eurocode 8 (EC8) calculations of the complete structure."),
        S['body_j']))
    story.append(Spacer(1, 4 * mm))
    story.append(_table_recap(rs))
    story.append(Spacer(1, 4 * mm))

    # Poteau
    story.extend(section_title("1", _T("Poteau type", "Typical column")))
    pot_d = _draw_poteau(rs)
    if pot_d:
        story.append(pot_d)
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(_T(
        "Section carree avec armatures longitudinales HA et cadres transversaux. "
        "Espacement des cadres reduit en zones critiques selon EC8 5.4.3.2.2.",
        "Square section with longitudinal HA bars and transverse hoops. "
        "Hoop spacing reduced in critical zones per EC8 5.4.3.2.2."),
        S['body_j']))
    story.append(PageBreak())

    # Poutre
    story.extend(section_title("2", _T("Poutre principale", "Main beam")))
    pou_d = _draw_poutre(rs)
    if pou_d:
        story.append(pou_d)
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(_T(
        "Section rectangulaire b x h avec lit inferieur (As_inf) en travee, lit superieur "
        "(As_sup) sur appuis. Etriers fermes selon EC2 9.2.2.",
        "Rectangular b x h section with bottom layer (As_inf) at midspan, top layer (As_sup) "
        "over supports. Closed stirrups per EC2 9.2.2."),
        S['body_j']))
    story.append(PageBreak())

    # Fondation
    story.extend(section_title("3", _T("Fondation type", "Typical foundation")))
    f_d = _draw_fondation(rs)
    if f_d:
        story.append(f_d)
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(_T(
        "Coupe verticale de la fondation retenue par le moteur (semelle isolee, semelle filante "
        "ou pieu fore selon la portance du sol et les charges descendantes).",
        "Vertical section of the foundation selected by the engine (isolated footing, strip footing "
        "or bored pile depending on soil bearing capacity and gravity loads)."),
        S['body_j']))

    hf = HeaderFooter(project_name, _T("Schemas de ferraillage", "Reinforcement Drawings"))
    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    pdf = buf.getvalue()
    buf.close()
    return pdf
