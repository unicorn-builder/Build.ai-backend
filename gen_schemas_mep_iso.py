"""
gen_schemas_mep_iso.py — Schemas isometriques MEP Tijan AI

Produit un PDF avec deux schemas de principe iso simplifies:
  • Plomberie  : citerne -> surpresseur -> colonne montante -> piquages par niveau
  • Electricite: transfo -> TGBT -> colonne montante -> tableaux divisionnaires par niveau

Toutes les valeurs (debits, sections, nombre de niveaux, nb logements,
puissance, diametre colonne) viennent du moteur MEP. Bilingue FR / EN.
"""
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, PageBreak)
from reportlab.graphics.shapes import (Drawing, Rect, Circle, Line, String,
                                        Group, Polygon, Path)
from reportlab.graphics import renderPDF

from tijan_theme import (VERT, VERT_DARK, VERT_LIGHT, NOIR, GRIS1, GRIS2, GRIS3,
                         BLANC, BLEU, BLEU_LT, ORANGE, ORANGE_LT, ROUGE,
                         ML, MR, CW, W, S, HeaderFooter,
                         p, fmt_n, section_title, table_style, _current_lang)


def _T(fr, en):
    return en if _current_lang == 'en' else fr


# ─────────────────────────────────────────────────────────────────────
#  SCHEMA PLOMBERIE iso simplifie
# ─────────────────────────────────────────────────────────────────────
def _draw_plomberie(rm):
    """rm = ResultatsMEP"""
    plomb = rm.plomberie
    nb_niveaux = int(getattr(rm.params, 'nb_niveaux', 4))
    nb_log = plomb.nb_logements
    citerne = plomb.volume_citerne_m3
    surp = plomb.debit_surpresseur_m3h
    diam = plomb.diam_colonne_montante_mm

    H = 175 * mm
    d = Drawing(CW, H)

    # Titre interne
    d.add(String(CW / 2, H - 6,
                 _T("Schema isometrique plomberie — Principe", "Plumbing isometric schematic — Principle"),
                 fontName='Helvetica-Bold', fontSize=10, fillColor=VERT_DARK, textAnchor='middle'))

    # Citerne (en haut a gauche)
    cx, cy, cw, ch = 12 * mm, H - 60 * mm, 30 * mm, 35 * mm
    d.add(Rect(cx, cy, cw, ch, fillColor=BLEU_LT, strokeColor=BLEU, strokeWidth=1.4))
    d.add(Line(cx, cy + ch * 0.85, cx + cw, cy + ch * 0.85, strokeColor=BLEU, strokeWidth=0.8))
    d.add(String(cx + cw / 2, cy + ch + 4,
                 _T(f"Citerne {citerne:.0f} m³", f"Tank {citerne:.0f} m³"),
                 fontName='Helvetica-Bold', fontSize=8, textAnchor='middle', fillColor=NOIR))
    d.add(String(cx + cw / 2, cy + ch / 2,
                 _T("EAU", "WATER"),
                 fontName='Helvetica-Bold', fontSize=10, textAnchor='middle', fillColor=BLEU))

    # Surpresseur
    sx = cx + cw + 18 * mm
    sy = cy + ch * 0.4
    sr = 8 * mm
    d.add(Circle(sx + sr, sy + sr, sr, fillColor=ORANGE_LT, strokeColor=ORANGE, strokeWidth=1.4))
    d.add(String(sx + sr, sy + sr - 1, "P", fontName='Helvetica-Bold', fontSize=12,
                 textAnchor='middle', fillColor=ORANGE))
    d.add(String(sx + sr, sy - 6,
                 _T(f"Surpresseur {surp:.0f} m³/h", f"Booster pump {surp:.0f} m³/h"),
                 fontName='Helvetica', fontSize=7, textAnchor='middle', fillColor=NOIR))
    # Liaison citerne -> surpresseur
    d.add(Line(cx + cw, sy + sr, sx, sy + sr, strokeColor=BLEU, strokeWidth=2.2))

    # Colonne montante verticale
    col_x = sx + sr * 2 + 22 * mm
    col_top = H - 18 * mm
    col_bot = sy + sr
    d.add(Line(col_x, col_bot, col_x, col_top, strokeColor=BLEU, strokeWidth=2.6))
    d.add(Line(sx + sr * 2, sy + sr, col_x, sy + sr, strokeColor=BLEU, strokeWidth=2.2))
    d.add(String(col_x + 4, (col_top + col_bot) / 2,
                 _T(f"Colonne DN{diam}", f"Riser DN{diam}"),
                 fontName='Helvetica-Bold', fontSize=8, fillColor=BLEU))

    # Niveaux : piquages
    n_show = min(nb_niveaux, 8)
    log_per_niveau = max(1, nb_log // max(n_show, 1))
    for i in range(n_show):
        ny = col_bot + (i + 1) * (col_top - col_bot - 8) / (n_show + 1)
        # Branchement horizontal
        bx_end = col_x + 55 * mm
        d.add(Line(col_x, ny, bx_end, ny, strokeColor=BLEU, strokeWidth=1.4))
        # Vanne
        d.add(Polygon(points=[col_x + 8, ny - 2, col_x + 8, ny + 2,
                              col_x + 12, ny - 2, col_x + 12, ny + 2],
                      fillColor=ORANGE, strokeColor=NOIR, strokeWidth=0.5))
        # Piquage logement (boite)
        d.add(Rect(bx_end, ny - 4, 22 * mm, 8, fillColor=GRIS1, strokeColor=NOIR, strokeWidth=0.7))
        d.add(String(bx_end + 11 * mm, ny - 1,
                     _T(f"N{i+1} — {log_per_niveau} log.", f"L{i+1} — {log_per_niveau} apt."),
                     fontName='Helvetica', fontSize=7, textAnchor='middle', fillColor=NOIR))

    # Legende
    ly = 8 * mm
    d.add(Line(8 * mm, ly, 18 * mm, ly, strokeColor=BLEU, strokeWidth=2.4))
    d.add(String(20 * mm, ly - 2,
                 _T("Eau froide", "Cold water"),
                 fontName='Helvetica', fontSize=7.5, fillColor=NOIR))
    d.add(Polygon(points=[55 * mm, ly - 2, 55 * mm, ly + 2, 59 * mm, ly - 2, 59 * mm, ly + 2],
                  fillColor=ORANGE, strokeColor=NOIR, strokeWidth=0.5))
    d.add(String(62 * mm, ly - 2, _T("Vanne", "Valve"),
                 fontName='Helvetica', fontSize=7.5, fillColor=NOIR))
    d.add(Circle(90 * mm, ly, 3, fillColor=ORANGE_LT, strokeColor=ORANGE, strokeWidth=1))
    d.add(String(95 * mm, ly - 2, _T("Pompe", "Pump"),
                 fontName='Helvetica', fontSize=7.5, fillColor=NOIR))
    return d


# ─────────────────────────────────────────────────────────────────────
#  SCHEMA ELECTRIQUE iso simplifie
# ─────────────────────────────────────────────────────────────────────
def _draw_electrique(rm):
    elec = rm.electrique
    nb_niveaux = int(getattr(rm.params, 'nb_niveaux', 4))
    nb_log = rm.nb_logements
    transfo = elec.transfo_kva
    groupe = elec.groupe_electrogene_kva
    sect = elec.section_colonne_mm2
    p_tot = elec.puissance_totale_kva

    H = 180 * mm
    d = Drawing(CW, H)

    d.add(String(CW / 2, H - 6,
                 _T("Schema isometrique electrique — Principe", "Electrical isometric schematic — Principle"),
                 fontName='Helvetica-Bold', fontSize=10, fillColor=VERT_DARK, textAnchor='middle'))

    # Transfo (rectangle a gauche)
    tx, ty, tw, th = 12 * mm, H - 60 * mm, 28 * mm, 26 * mm
    d.add(Rect(tx, ty, tw, th, fillColor=ORANGE_LT, strokeColor=ORANGE, strokeWidth=1.4))
    d.add(String(tx + tw / 2, ty + th / 2 + 2, "TR",
                 fontName='Helvetica-Bold', fontSize=14, textAnchor='middle', fillColor=ORANGE))
    d.add(String(tx + tw / 2, ty - 6,
                 _T(f"Transfo {transfo} kVA", f"Transformer {transfo} kVA"),
                 fontName='Helvetica-Bold', fontSize=8, textAnchor='middle', fillColor=NOIR))

    # Groupe electrogene (sous transfo)
    gx, gy, gw, gh = tx, ty - 28 * mm, tw, 18 * mm
    d.add(Rect(gx, gy, gw, gh, fillColor=GRIS1, strokeColor=NOIR, strokeWidth=1.2))
    d.add(String(gx + gw / 2, gy + gh / 2 - 1, "G",
                 fontName='Helvetica-Bold', fontSize=12, textAnchor='middle', fillColor=NOIR))
    d.add(String(gx + gw / 2, gy - 6,
                 _T(f"Groupe {groupe} kVA", f"Genset {groupe} kVA"),
                 fontName='Helvetica', fontSize=7.5, textAnchor='middle', fillColor=NOIR))

    # TGBT
    bx, by, bw, bh = tx + tw + 22 * mm, ty - 4 * mm, 30 * mm, 36 * mm
    d.add(Rect(bx, by, bw, bh, fillColor=VERT_LIGHT, strokeColor=VERT, strokeWidth=1.4))
    d.add(String(bx + bw / 2, by + bh - 8, "TGBT",
                 fontName='Helvetica-Bold', fontSize=9, textAnchor='middle', fillColor=VERT_DARK))
    d.add(String(bx + bw / 2, by + bh / 2 - 2,
                 _T(f"{p_tot:.0f} kVA", f"{p_tot:.0f} kVA"),
                 fontName='Helvetica', fontSize=8, textAnchor='middle', fillColor=NOIR))
    # Inverseur de source dessine en symbole
    d.add(Line(bx + bw / 2 - 4, by + 6, bx + bw / 2 + 4, by + 6, strokeColor=NOIR, strokeWidth=0.8))
    d.add(Line(bx + bw / 2 - 4, by + 6, bx + bw / 2 + 4, by + 11, strokeColor=NOIR, strokeWidth=0.8))

    # Liaisons
    d.add(Line(tx + tw, ty + th / 2, bx, by + bh - 12, strokeColor=ORANGE, strokeWidth=1.8))
    d.add(Line(gx + gw, gy + gh / 2, bx, by + 12, strokeColor=NOIR, strokeWidth=1.4))

    # Colonne montante
    col_x = bx + bw + 22 * mm
    col_top = H - 18 * mm
    col_bot = by + bh / 2
    d.add(Line(col_x, col_bot, col_x, col_top, strokeColor=NOIR, strokeWidth=2.6))
    d.add(Line(bx + bw, col_bot, col_x, col_bot, strokeColor=NOIR, strokeWidth=2.2))
    d.add(String(col_x + 4, (col_top + col_bot) / 2,
                 _T(f"Colonne {sect} mm²", f"Riser {sect} mm²"),
                 fontName='Helvetica-Bold', fontSize=8, fillColor=NOIR))

    # Tableaux divisionnaires par niveau
    n_show = min(nb_niveaux, 8)
    log_per_niveau = max(1, nb_log // max(n_show, 1))
    for i in range(n_show):
        ny = col_bot + (i + 1) * (col_top - col_bot - 8) / (n_show + 1)
        bx_end = col_x + 55 * mm
        d.add(Line(col_x, ny, bx_end, ny, strokeColor=NOIR, strokeWidth=1.2))
        # Disjoncteur (petit rectangle)
        d.add(Rect(col_x + 8, ny - 3, 6, 6, fillColor=BLANC, strokeColor=NOIR, strokeWidth=0.7))
        d.add(Line(col_x + 8, ny + 3, col_x + 14, ny - 3, strokeColor=NOIR, strokeWidth=0.7))
        # Tableau divisionnaire
        d.add(Rect(bx_end, ny - 4, 22 * mm, 8, fillColor=VERT_LIGHT, strokeColor=VERT, strokeWidth=0.8))
        d.add(String(bx_end + 11 * mm, ny - 1,
                     _T(f"TD N{i+1} — {log_per_niveau} log.", f"DB L{i+1} — {log_per_niveau} apt."),
                     fontName='Helvetica', fontSize=7, textAnchor='middle', fillColor=NOIR))

    # Legende
    ly = 8 * mm
    d.add(Line(8 * mm, ly, 18 * mm, ly, strokeColor=NOIR, strokeWidth=2.2))
    d.add(String(20 * mm, ly - 2, _T("Cable BT", "LV cable"),
                 fontName='Helvetica', fontSize=7.5, fillColor=NOIR))
    d.add(Rect(50 * mm, ly - 3, 6, 6, fillColor=BLANC, strokeColor=NOIR, strokeWidth=0.7))
    d.add(String(60 * mm, ly - 2, _T("Disjoncteur", "Breaker"),
                 fontName='Helvetica', fontSize=7.5, fillColor=NOIR))
    d.add(Rect(85 * mm, ly - 3, 6, 6, fillColor=VERT_LIGHT, strokeColor=VERT, strokeWidth=0.7))
    d.add(String(95 * mm, ly - 2, _T("Tableau divisionnaire", "Distribution board"),
                 fontName='Helvetica', fontSize=7.5, fillColor=NOIR))
    return d


# ─────────────────────────────────────────────────────────────────────
#  Tables recap
# ─────────────────────────────────────────────────────────────────────
def _table_plomb(rm):
    plomb = rm.plomberie
    rows = [[Paragraph(_T("Parametre", "Parameter"), S['th_l']),
             Paragraph(_T("Valeur", "Value"), S['th_l'])]]
    rows += [
        [p(_T("Logements desservis", "Apartments served")), p(f"{plomb.nb_logements}")],
        [p(_T("Personnes", "Occupants")), p(f"{plomb.nb_personnes}")],
        [p(_T("Besoin total", "Total demand")), p(f"{plomb.besoin_total_m3_j:.1f} m³/j")],
        [p(_T("Citerne", "Tank")), p(f"{plomb.volume_citerne_m3:.0f} m³")],
        [p(_T("Surpresseur", "Booster pump")), p(f"{plomb.debit_surpresseur_m3h:.0f} m³/h")],
        [p(_T("Colonne montante", "Riser pipe")), p(f"DN{plomb.diam_colonne_montante_mm}")],
        [p(_T("Chauffe-eau solaires", "Solar water heaters")), p(f"{plomb.nb_chauffe_eau_solaire}")],
    ]
    t = Table(rows, colWidths=[CW * 0.55, CW * 0.45])
    t.setStyle(table_style())
    return t


def _table_elec(rm):
    elec = rm.electrique
    rows = [[Paragraph(_T("Parametre", "Parameter"), S['th_l']),
             Paragraph(_T("Valeur", "Value"), S['th_l'])]]
    rows += [
        [p(_T("Puissance totale", "Total power")), p(f"{elec.puissance_totale_kva:.0f} kVA")],
        [p(_T("Transformateur", "Transformer")), p(f"{elec.transfo_kva} kVA")],
        [p(_T("Groupe electrogene", "Backup genset")), p(f"{elec.groupe_electrogene_kva} kVA")],
        [p(_T("Compteurs", "Meters")), p(f"{elec.nb_compteurs}")],
        [p(_T("Section colonne montante", "Riser cable section")), p(f"{elec.section_colonne_mm2} mm²")],
        [p(_T("Eclairage", "Lighting")), p(f"{elec.puissance_eclairage_kw:.1f} kW")],
        [p(_T("Prises", "Sockets")), p(f"{elec.puissance_prises_kw:.1f} kW")],
        [p(_T("CVC", "HVAC")), p(f"{elec.puissance_cvc_kw:.1f} kW")],
    ]
    t = Table(rows, colWidths=[CW * 0.55, CW * 0.45])
    t.setStyle(table_style())
    return t


# ─────────────────────────────────────────────────────────────────────
#  Entree principale
# ─────────────────────────────────────────────────────────────────────
def generer_schemas_mep_iso(rm, params: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=ML, rightMargin=MR,
                            topMargin=22 * mm, bottomMargin=18 * mm,
                            title=_T("Schemas isometriques MEP", "MEP Isometric Drawings"),
                            author='Tijan AI')

    project_name = params.get('nom') or _T("Projet", "Project")
    ville = params.get('ville') or 'Dakar'
    pays = params.get('pays') or 'Senegal'
    sub = f"{project_name} — {ville}, {pays}"

    story = []
    story.append(Paragraph(
        _T("Schemas isometriques MEP", "MEP Isometric Drawings"),
        S['titre']))
    story.append(Paragraph(sub, S['sous_titre']))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(_T(
        "Schemas de principe en vue isometrique simplifiee pour les lots Plomberie et "
        "Electricite. Toutes les valeurs sont issues des bilans MEP du moteur Tijan AI.",
        "Simplified isometric principle diagrams for the Plumbing and Electrical packages. "
        "All values come from the Tijan AI MEP engine."),
        S['body_j']))
    story.append(Spacer(1, 4 * mm))

    # Plomberie
    story.extend(section_title("1", _T("Plomberie", "Plumbing")))
    story.append(_table_plomb(rm))
    story.append(Spacer(1, 2 * mm))
    story.append(_draw_plomberie(rm))
    story.append(Paragraph(_T(
        "Distribution gravitaire depuis citerne haute, surpresseur de mise en pression, colonne "
        "montante DN dimensionnee selon le debit de pointe et nombre de niveaux desservis.",
        "Gravity distribution from elevated tank, pressure booster pump, DN riser sized for peak "
        "demand and number of served floors."),
        S['body_j']))
    story.append(PageBreak())

    # Electrique
    story.extend(section_title("2", _T("Electricite", "Electrical")))
    story.append(_table_elec(rm))
    story.append(Spacer(1, 2 * mm))
    story.append(_draw_electrique(rm))
    story.append(Paragraph(_T(
        "Schema TGBT avec transformateur principal et groupe electrogene de secours via inverseur "
        "de source. Colonne montante BT dimensionnee selon la puissance foisonnee et les chutes de "
        "tension reglementaires.",
        "Main switchboard scheme with main transformer and backup genset via automatic transfer "
        "switch. LV riser sized for diversified power and regulatory voltage drops."),
        S['body_j']))

    hf = HeaderFooter(project_name, _T("Schemas isometriques MEP", "MEP Isometric Drawings"))
    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    pdf = buf.getvalue()
    buf.close()
    return pdf
