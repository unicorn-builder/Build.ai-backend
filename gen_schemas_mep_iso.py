"""
gen_schemas_mep_iso.py — Schemas de principe MEP Tijan AI

10 diagrammes blocs (un par lot technique). Mise en page rigoureusement
contrainte dans une grille 4 colonnes x 6 rangees, avec routage orthogonal,
trunk fan-out et libelles d'arete sur fond blanc.
"""
import math
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, PageBreak, KeepTogether)
from reportlab.graphics.shapes import (Drawing, Rect, Circle, Line, String,
                                        Group, Polygon, PolyLine)

from tijan_theme import (VERT, VERT_DARK, VERT_LIGHT, NOIR, GRIS1, GRIS2, GRIS3,
                         BLANC, BLEU, BLEU_LT, ORANGE, ORANGE_LT, ROUGE,
                         ML, MR, CW, W, S, HeaderFooter,
                         p, fmt_n, section_title, table_style, _current_lang)


def _T(fr, en):
    return en if _current_lang == 'en' else fr


# ─────────────────────────────────────────────────────────────────────
#  Constantes visuelles
# ─────────────────────────────────────────────────────────────────────
PAD       = 10 * mm
H_TITLE   = 12 * mm
CONTENT_W = 178   # mm — largeur utile interne
CONTENT_H = 118   # mm — hauteur utile interne (laisse de la marge pour caption)

# 4 colonnes parfaitement alignees, largeur node = 38 mm
#   col x  +  w(38) reste <= CONTENT_W (178)
#   A: 4 → 42   B: 50 → 88   C: 96 → 134   D: 140 → 178
COL = {'A': 4, 'B': 50, 'C': 96, 'D': 140}
NODE_W = 38

# 6 rangees, hauteur node 18 mm + ecart 5 mm = pitch 23 mm
#   R1 top à y=104, R6 bottom à y=4
ROW = {'1': 104, '2': 81, '3': 58, '4': 35, '5': 12, '6': -11}  # R6 reserve / non utilise
NODE_H = 18

# Couleurs (pastels)
NODE_COLORS = {
    'power':   (colors.HexColor('#FFEFD5'), ORANGE),
    'water':   (colors.HexColor('#E1EFFB'), BLEU),
    'hvac':    (colors.HexColor('#E1EFFB'), VERT_DARK),
    'fire':    (colors.HexColor('#FDE5E0'), ROUGE),
    'low':     (colors.HexColor('#E6F3E8'), VERT),
    'gtb':     (colors.HexColor('#E6F3E8'), VERT_DARK),
    'neutral': (colors.HexColor('#F2F2F2'), colors.HexColor('#666666')),
}

SHADOW_COLOR = colors.HexColor('#D9D9D9')


# ─────────────────────────────────────────────────────────────────────
#  Construction des nodes
# ─────────────────────────────────────────────────────────────────────
def _node(id, title, sub='', color='neutral',
          col=None, row=None, x=None, y=None, w=NODE_W, h=NODE_H):
    if col is not None:
        x = COL[col]
    if row is not None:
        y = ROW[row]
    return {'id': id, 'x': x, 'y': y, 'w': w, 'h': h,
            'title': title, 'sub': sub, 'color': color}


def _node_rect(d, n):
    fill, stroke = NODE_COLORS.get(n.get('color', 'neutral'), NODE_COLORS['neutral'])
    x = PAD + n['x'] * mm
    y = PAD + n['y'] * mm
    w = n['w'] * mm
    h = n['h'] * mm
    # Drop shadow (offset gris massif)
    d.add(Rect(x + 0.7 * mm, y - 0.7 * mm, w, h, rx=2.5, ry=2.5,
               fillColor=SHADOW_COLOR, strokeColor=None))
    # Body
    d.add(Rect(x, y, w, h, rx=2.5, ry=2.5,
               fillColor=fill, strokeColor=stroke, strokeWidth=1.3))
    title = n.get('title', '')
    sub = n.get('sub', '')
    cx = x + w / 2
    if sub:
        # Titre dans le tiers haut, sub dans le tiers bas (top-down)
        d.add(String(cx, y + h - 7, title,
                     fontName='Helvetica-Bold', fontSize=8.4,
                     textAnchor='middle', fillColor=NOIR))
        d.add(String(cx, y + 4, sub,
                     fontName='Helvetica', fontSize=6.8,
                     textAnchor='middle', fillColor=colors.HexColor('#444444')))
    else:
        d.add(String(cx, y + h / 2 - 2.6, title,
                     fontName='Helvetica-Bold', fontSize=8.6,
                     textAnchor='middle', fillColor=NOIR))


def _anchor(node, side):
    x = PAD + node['x'] * mm
    y = PAD + node['y'] * mm
    w = node['w'] * mm
    h = node['h'] * mm
    if side == 'r': return x + w, y + h / 2
    if side == 'l': return x, y + h / 2
    if side == 't': return x + w / 2, y + h
    if side == 'b': return x + w / 2, y
    return x + w / 2, y + h / 2


# ─────────────────────────────────────────────────────────────────────
#  Edges : routage orthogonal + fleche + label fond blanc
# ─────────────────────────────────────────────────────────────────────
def _arrow_head(d, x, y, dx, dy, color):
    L = math.hypot(dx, dy) or 1
    ux, uy = dx / L, dy / L
    size = 2.4 * mm
    bx, by = x - ux * size, y - uy * size
    px, py = -uy * size * 0.5, ux * size * 0.5
    d.add(Polygon(points=[x, y, bx + px, by + py, bx - px, by - py],
                  fillColor=color, strokeColor=color, strokeWidth=0.4))


def _edge_label(d, lx, ly, text, color):
    if not text:
        return
    tw = len(text) * 3.3 + 5
    d.add(Rect(lx - tw / 2, ly - 4, tw, 8,
               fillColor=BLANC, strokeColor=None))
    d.add(String(lx, ly - 2.2, text,
                 fontName='Helvetica', fontSize=6.6,
                 textAnchor='middle', fillColor=color))


def _draw_edge(d, nodes_by_id, e):
    src = nodes_by_id[e['src']]
    dst = nodes_by_id[e['dst']]
    color = e.get('color') or colors.HexColor('#555555')
    style = e.get('style', 'solid')
    src_side = e.get('src_side', 'r')
    dst_side = e.get('dst_side', 'l')
    sx, sy = _anchor(src, src_side)
    dx, dy = _anchor(dst, dst_side)

    midx_mm = e.get('midx_mm')
    midy_mm = e.get('midy_mm')

    if src_side in ('r', 'l') and dst_side in ('r', 'l'):
        if midx_mm is not None:
            mx = PAD + midx_mm * mm
        else:
            mx = (sx + dx) / 2
        pts = [sx, sy, mx, sy, mx, dy, dx, dy]
        last = (1 if dx >= mx else -1, 0)
        lab_x, lab_y = mx, (sy + dy) / 2
    elif src_side in ('t', 'b') and dst_side in ('t', 'b'):
        if midy_mm is not None:
            my = PAD + midy_mm * mm
        else:
            my = (sy + dy) / 2
        pts = [sx, sy, sx, my, dx, my, dx, dy]
        last = (0, 1 if dy >= my else -1)
        lab_x, lab_y = (sx + dx) / 2, my
    else:
        # b → l ou t → l : dog-leg en L
        pts = [sx, sy, dx, sy, dx, dy]
        last = (0, 1 if dy >= sy else -1)
        lab_x, lab_y = dx, (sy + dy) / 2

    if style == 'dashed':
        d.add(PolyLine(points=pts, strokeColor=color, strokeWidth=1.2,
                       strokeDashArray=[3, 2], strokeLineCap=1))
    else:
        d.add(PolyLine(points=pts, strokeColor=color, strokeWidth=1.5,
                       strokeLineCap=1))

    _arrow_head(d, dx, dy, last[0], last[1], color)
    _edge_label(d, lab_x, lab_y, e.get('label', ''), color)


# ─────────────────────────────────────────────────────────────────────
#  Diagramme
# ─────────────────────────────────────────────────────────────────────
def _make_diagram(title, nodes, edges, legend=None):
    W_pts = CONTENT_W * mm + 2 * PAD
    H_pts = CONTENT_H * mm + 2 * PAD + H_TITLE
    d = Drawing(W_pts, H_pts)
    # Fond carte
    d.add(Rect(PAD * 0.35, PAD * 0.35,
               W_pts - PAD * 0.7, H_pts - PAD * 0.7,
               rx=4, ry=4,
               fillColor=colors.HexColor('#FAFBFC'),
               strokeColor=GRIS2, strokeWidth=0.6))
    # Bandeau titre
    d.add(Rect(PAD * 0.35, H_pts - PAD * 0.35 - H_TITLE,
               W_pts - PAD * 0.7, H_TITLE,
               fillColor=colors.HexColor('#EFF5F0'),
               strokeColor=None))
    d.add(String(W_pts / 2, H_pts - PAD * 0.35 - H_TITLE + 4, title,
                 fontName='Helvetica-Bold', fontSize=11,
                 textAnchor='middle', fillColor=VERT_DARK))
    # Nodes
    nodes_by_id = {n['id']: n for n in nodes}
    for n in nodes:
        _node_rect(d, n)
    # Edges
    for e in edges:
        _draw_edge(d, nodes_by_id, e)
    # Legende
    if legend:
        ly = PAD * 0.35 + 4
        lx = PAD + 6
        for label, col in legend:
            d.add(Line(lx, ly + 2, lx + 12, ly + 2,
                       strokeColor=col, strokeWidth=1.8))
            d.add(String(lx + 15, ly, label,
                         fontName='Helvetica', fontSize=7, fillColor=NOIR))
            lx += 15 + len(label) * 3.5 + 12
    return d


# ─────────────────────────────────────────────────────────────────────
#  Helpers tables
# ─────────────────────────────────────────────────────────────────────
def _kv_table(rows):
    data = [[Paragraph(_T("Parametre", "Parameter"), S['th_l']),
             Paragraph(_T("Valeur", "Value"), S['th_l'])]] + [
        [p(k), p(v)] for k, v in rows
    ]
    t = Table(data, colWidths=[CW * 0.55, CW * 0.45])
    t.setStyle(table_style())
    return t


# ─────────────────────────────────────────────────────────────────────
#  1. ELECTRICITE
# ─────────────────────────────────────────────────────────────────────
def _diag_electricite(rm):
    e = rm.electrique
    nb = min(max(int(getattr(rm.params, 'nb_niveaux', 4)), 1), 5)
    # 5 niveaux max, repartis sur les 5 rangees R1..R5
    rows_for_td = ['1', '2', '3', '4', '5'][:nb]
    nodes = [
        _node('tr',  'TR', f"{e.transfo_kva} kVA", 'power', col='A', row='2'),
        _node('gen', _T('Groupe','Genset'), f"{e.groupe_electrogene_kva} kVA",
              'neutral', col='A', row='4'),
        _node('ats', 'ATS', _T('Inverseur','Transfer sw.'), 'neutral',
              col='B', row='3'),
        _node('tgbt','TGBT', f"{e.puissance_totale_kva:.0f} kVA", 'low',
              col='C', row='3'),
    ]
    # Colonne montante = noeud vertical etroit
    col_x = 122  # juste a droite de col C (96+38=134), garde marge
    col_w = 14
    nodes.append({'id': 'col', 'x': col_x, 'y': ROW['5'],
                  'w': col_w, 'h': ROW['1'] + NODE_H - ROW['5'],
                  'title': _T('Colonne','Riser'),
                  'sub': f"{e.section_colonne_mm2} mm²",
                  'color': 'low'})
    # TDs sur la 4eme colonne (D), un par rangee
    for i, r in enumerate(rows_for_td):
        nodes.append(_node(f'td{i}', f"TD N{i+1}",
                           color='low', col='D', row=r, h=14))
    edges = [
        {'src': 'tr',   'dst': 'ats',  'color': ORANGE, 'label': 'HTA/BT'},
        {'src': 'gen',  'dst': 'ats',  'color': NOIR,   'label': _T('Secours','Backup')},
        {'src': 'ats',  'dst': 'tgbt', 'color': ORANGE},
        # TGBT → colonne : trunk a x=118 (juste avant col)
        {'src': 'tgbt', 'dst': 'col',  'color': NOIR,   'label': 'BT'},
    ]
    # Trunk vers TDs : tous via midx fixe a la droite de la colonne
    trunk_x = col_x + col_w + 1
    for i in range(nb):
        edges.append({'src': 'col', 'dst': f'td{i}',
                      'color': NOIR, 'midx_mm': trunk_x})
    return _make_diagram(
        _T("1. Electricite — Distribution principale",
           "1. Electrical — Main distribution"),
        nodes, edges,
        legend=[(_T('Energie HTA/BT','HV/LV power'), ORANGE),
                (_T('Liaison BT','LV link'), NOIR)])


# ─────────────────────────────────────────────────────────────────────
#  2. PLOMBERIE
# ─────────────────────────────────────────────────────────────────────
def _diag_plomberie(rm):
    pl = rm.plomberie
    nb = min(max(int(getattr(rm.params, 'nb_niveaux', 4)), 1), 5)
    rows_for_n = ['1', '2', '3', '4', '5'][:nb]
    nodes = [
        _node('cit', _T('Citerne','Tank'), f"{pl.volume_citerne_m3:.0f} m³",
              'water', col='A', row='2'),
        _node('pmp', _T('Surpresseur','Booster'), f"{pl.debit_surpresseur_m3h:.0f} m³/h",
              'water', col='B', row='2'),
        _node('ces', 'CESI', f"{pl.nb_chauffe_eau_solaire} {_T('unites','units')}",
              'fire', col='A', row='4'),
        _node('ev',  _T('Evac. EU/EV','Drain stack'), 'PVC DN100',
              'neutral', col='A', row='5'),
    ]
    # Colonne montante verticale
    col_x = 102
    col_w = 14
    nodes.append({'id': 'col', 'x': col_x, 'y': ROW['5'],
                  'w': col_w, 'h': ROW['1'] + NODE_H - ROW['5'],
                  'title': _T('Colonne','Riser'),
                  'sub': f"DN{pl.diam_colonne_montante_mm}",
                  'color': 'water'})
    for i, r in enumerate(rows_for_n):
        nodes.append(_node(f'nv{i}', f"N{i+1}",
                           _T('Nourrice','Manifold'),
                           color='water', col='D', row=r))
    trunk_x = col_x + col_w + 1
    edges = [
        {'src': 'cit', 'dst': 'pmp', 'color': BLEU, 'label': _T('Aspir.','Suct.')},
        {'src': 'pmp', 'dst': 'col', 'color': BLEU, 'label': _T('Refoul.','Disch.')},
        {'src': 'ces', 'dst': 'col', 'color': ORANGE, 'label': 'ECS'},
        {'src': 'ev',  'dst': 'col', 'color': GRIS3, 'style': 'dashed',
         'label': _T('Evac.','Drain')},
    ]
    for i in range(nb):
        edges.append({'src': 'col', 'dst': f'nv{i}',
                      'color': BLEU, 'midx_mm': trunk_x})
    return _make_diagram(
        _T("2. Plomberie — Eau froide / ECS / Evacuation",
           "2. Plumbing — Cold water / DHW / Drainage"),
        nodes, edges,
        legend=[(_T('Eau froide','Cold water'), BLEU),
                ('ECS', ORANGE),
                (_T('Evacuation','Drainage'), GRIS3)])


# ─────────────────────────────────────────────────────────────────────
#  3. CLIMATISATION
# ─────────────────────────────────────────────────────────────────────
def _diag_clim(rm):
    c = rm.cvc
    nodes = [
        _node('ue',  _T('Unites Ext.','Outdoor'),
              f"{c.puissance_frigorifique_kw:.0f} kW", 'hvac', col='A', row='2'),
        _node('lf',  _T('Liaisons frigo','Refrig. lines'),
              _T('Cuivre isole','Insul. copper'), 'neutral', col='B', row='2'),
        _node('sj',  _T('Splits sejour','Living splits'),
              f"× {c.nb_splits_sejour}", 'hvac', col='C', row='1'),
        _node('ch',  _T('Splits chambre','Bedroom splits'),
              f"× {c.nb_splits_chambre}", 'hvac', col='C', row='2'),
        _node('cas', _T('Cassettes','Cassettes'),
              f"× {c.nb_cassettes}", 'hvac', col='C', row='3'),
        _node('cnd', _T('Condensats','Condensate'),
              'PVC DN32', 'water', col='D', row='2'),
    ]
    edges = [
        {'src': 'ue', 'dst': 'lf', 'color': BLEU},
        {'src': 'lf', 'dst': 'sj', 'color': BLEU, 'label': 'R410A', 'midx_mm': 92},
        {'src': 'lf', 'dst': 'ch', 'color': BLEU, 'label': 'R410A', 'midx_mm': 92},
        {'src': 'lf', 'dst': 'cas','color': BLEU, 'label': 'R410A', 'midx_mm': 92},
        {'src': 'sj', 'dst': 'cnd','color': GRIS3, 'style': 'dashed'},
        {'src': 'ch', 'dst': 'cnd','color': GRIS3, 'style': 'dashed'},
        {'src': 'cas','dst': 'cnd','color': GRIS3, 'style': 'dashed'},
    ]
    return _make_diagram(
        _T("3. Climatisation — Detente directe DRV",
           "3. HVAC — VRF direct expansion"),
        nodes, edges,
        legend=[(_T('Frigo R410A','Refrigerant'), BLEU),
                (_T('Condensats','Condensate'), GRIS3)])


# ─────────────────────────────────────────────────────────────────────
#  4. VENTILATION
# ─────────────────────────────────────────────────────────────────────
def _diag_vent(rm):
    c = rm.cvc
    nodes = [
        _node('vmc', f"VMC {c.type_vmc}",
              f"× {c.nb_vmc} {_T('caissons','units')}", 'hvac', col='A', row='2'),
        _node('gp',  _T('Gaines princ.','Main ducts'),
              _T('Galva isolee','Insul. galv.'), 'neutral', col='B', row='2'),
        _node('cuis', _T('Bouches cuisine','Kitchen vents'),
              '', 'hvac', col='C', row='1'),
        _node('sdb',  _T('Bouches SdB/WC','Bath/WC vents'),
              '', 'hvac', col='C', row='2'),
        _node('amen', _T('Entree air neuf','Fresh air'),
              '', 'hvac', col='C', row='3'),
        _node('rej',  _T('Rejet toiture','Roof exhaust'),
              '', 'neutral', col='D', row='2'),
    ]
    edges = [
        {'src': 'vmc', 'dst': 'gp',  'color': BLEU},
        {'src': 'gp',  'dst': 'cuis','color': BLEU, 'label': _T('Extr.','Exh.'), 'midx_mm': 92},
        {'src': 'gp',  'dst': 'sdb', 'color': BLEU, 'label': _T('Extr.','Exh.'), 'midx_mm': 92},
        {'src': 'amen','dst': 'gp',  'color': VERT, 'label': _T('Air neuf','Fresh')},
        {'src': 'gp',  'dst': 'rej', 'color': GRIS3, 'style': 'dashed',
         'label': _T('Rejet','Exhaust')},
    ]
    return _make_diagram(
        _T("4. Ventilation — Schema aeraulique",
           "4. Ventilation — Air-flow schematic"),
        nodes, edges,
        legend=[(_T('Extraction','Exhaust'), BLEU),
                (_T('Air neuf','Fresh air'), VERT),
                (_T('Rejet','Discharge'), GRIS3)])


# ─────────────────────────────────────────────────────────────────────
#  5. CCTV
# ─────────────────────────────────────────────────────────────────────
def _diag_cctv(rm):
    cf = rm.courants_faibles
    nodes = [
        _node('nvr', 'NVR', _T('Enregistreur','Recorder'),
              'low', col='A', row='2'),
        _node('sw',  'Switch PoE',
              f"{cf.nb_cameras_int + cf.nb_cameras_ext} ports",
              'low', col='B', row='2'),
        _node('cint', _T('Cameras int.','Indoor cams'),
              f"× {cf.nb_cameras_int}", 'low', col='C', row='1'),
        _node('cext', _T('Cameras ext.','Outdoor cams'),
              f"× {cf.nb_cameras_ext}", 'low', col='C', row='3'),
        _node('mon',  _T('Poste super.','Workstation'),
              'HDMI', 'neutral', col='D', row='2'),
    ]
    edges = [
        {'src': 'nvr', 'dst': 'sw',  'color': VERT_DARK, 'label': 'LAN'},
        {'src': 'sw',  'dst': 'cint','color': VERT_DARK, 'label': 'PoE', 'midx_mm': 92},
        {'src': 'sw',  'dst': 'cext','color': VERT_DARK, 'label': 'PoE', 'midx_mm': 92},
        {'src': 'nvr', 'dst': 'mon', 'color': NOIR,       'label': 'HDMI', 'midx_mm': 138},
    ]
    return _make_diagram(
        _T("5. CCTV — Videosurveillance IP",
           "5. CCTV — IP video surveillance"),
        nodes, edges,
        legend=[('LAN/PoE', VERT_DARK), ('HDMI', NOIR)])


# ─────────────────────────────────────────────────────────────────────
#  6. SONORISATION
# ─────────────────────────────────────────────────────────────────────
def _diag_sono(rm):
    nodes = [
        _node('src', _T('Sources','Sources'), 'Mic / BGM',
              'low', col='A', row='2'),
        _node('cons',_T('Console','Mixer'), '', 'low', col='B', row='2'),
        _node('amp', _T('Ampli matrice','Matrix amp'), '100V',
              'low', col='C', row='2'),
        _node('z1', _T('Zone hall','Lobby'), '',         'low', col='D', row='1'),
        _node('z2', _T('Zone couloirs','Corridors'), '', 'low', col='D', row='2'),
        _node('z3', _T('Zone parking','Parking'), '',    'low', col='D', row='3'),
    ]
    edges = [
        {'src': 'src', 'dst': 'cons','color': VERT_DARK, 'label': 'XLR'},
        {'src': 'cons','dst': 'amp', 'color': VERT_DARK},
        {'src': 'amp', 'dst': 'z1',  'color': VERT_DARK, 'label': '100V', 'midx_mm': 136},
        {'src': 'amp', 'dst': 'z2',  'color': VERT_DARK, 'label': '100V', 'midx_mm': 136},
        {'src': 'amp', 'dst': 'z3',  'color': VERT_DARK, 'label': '100V', 'midx_mm': 136},
    ]
    return _make_diagram(
        _T("6. Sonorisation — Diffusion 100V multi-zones",
           "6. PA system — 100V multi-zone"),
        nodes, edges,
        legend=[(_T('Signal audio','Audio'), VERT_DARK)])


# ─────────────────────────────────────────────────────────────────────
#  7. DETECTION INCENDIE
# ─────────────────────────────────────────────────────────────────────
def _diag_di(rm):
    si = rm.securite_incendie
    nodes = [
        _node('det', _T('Detecteurs fumee','Smoke det.'),
              f"× {si.nb_detecteurs_fumee}", 'fire', col='A', row='1'),
        _node('dm',  _T('Decl. manuels','Manual CP'),
              f"× {si.nb_declencheurs_manuels}", 'fire', col='A', row='2'),
        _node('ecs', 'ECS', f"{si.centrale_zones} {_T('zones','zones')}",
              'fire', col='B', row='2'),
        _node('sir', _T('Sirenes UGA','Sounders UGA'),
              f"× {si.nb_sirenes}", 'fire', col='C', row='1'),
        _node('des', _T('Desenfumage','Smoke extr.'),
              _T('Requis','Required') if si.desenfumage_requis
                  else _T('Non requis','Not req.'),
              'fire', col='C', row='2'),
        _node('gtb', _T('Report GTB','BMS report'), 'TCP/IP',
              'gtb', col='D', row='2'),
    ]
    edges = [
        {'src': 'det', 'dst': 'ecs', 'color': ROUGE},
        {'src': 'dm',  'dst': 'ecs', 'color': ROUGE},
        {'src': 'ecs', 'dst': 'sir', 'color': ROUGE, 'label': 'UGA', 'midx_mm': 92},
        {'src': 'ecs', 'dst': 'des', 'color': ROUGE, 'label': 'Cmd', 'midx_mm': 92},
        {'src': 'ecs', 'dst': 'gtb', 'color': VERT_DARK, 'style': 'dashed',
         'midx_mm': 138},
    ]
    return _make_diagram(
        _T("7. Detection incendie — SSI categorie A",
           "7. Fire detection — SSI Cat. A"),
        nodes, edges,
        legend=[(_T('Boucle SSI','Fire loop'), ROUGE),
                (_T('Report GTB','BMS report'), VERT_DARK)])


# ─────────────────────────────────────────────────────────────────────
#  8. EXTINCTION INCENDIE
# ─────────────────────────────────────────────────────────────────────
def _diag_ext(rm):
    si = rm.securite_incendie
    nodes = [
        _node('bac', _T('Bache feu','Fire tank'), '120 m³',
              'water', col='A', row='2'),
        _node('pmp', _T('Pompe incendie','Fire pump'),
              _T('Diesel + Elec','Diesel + Elec'),
              'fire', col='B', row='2'),
    ]
    col_x = 102
    col_w = 14
    nodes.append({'id': 'cs', 'x': col_x, 'y': ROW['5'],
                  'w': col_w, 'h': ROW['1'] + NODE_H - ROW['5'],
                  'title': _T('Colonne','Riser'),
                  'sub': _T('seche','dry'), 'color': 'fire'})
    nodes += [
        _node('ria', 'RIA', f"{si.longueur_ria_ml:.0f} ml",
              'fire', col='D', row='1'),
        _node('spr', _T('Sprinklers','Sprinklers'),
              f"× {si.nb_tetes_sprinkler}", 'fire', col='D', row='2'),
        _node('ext', _T('Extincteurs','Extinguishers'),
              f"CO2 {si.nb_extincteurs_co2} / P {si.nb_extincteurs_poudre}",
              'fire', col='D', row='3'),
    ]
    trunk_x = col_x + col_w + 1
    edges = [
        {'src': 'bac', 'dst': 'pmp', 'color': BLEU, 'label': _T('Aspir.','Suct.')},
        {'src': 'pmp', 'dst': 'cs',  'color': BLEU, 'label': _T('Refoul.','Disch.')},
        {'src': 'cs',  'dst': 'ria', 'color': BLEU, 'midx_mm': trunk_x},
        {'src': 'cs',  'dst': 'spr', 'color': BLEU, 'midx_mm': trunk_x},
        {'src': 'cs',  'dst': 'ext', 'color': BLEU, 'midx_mm': trunk_x},
    ]
    return _make_diagram(
        _T("8. Extinction incendie — RIA + Colonne seche + Sprinklers",
           "8. Fire suppression — Hose reels + Dry riser + Sprinklers"),
        nodes, edges,
        legend=[(_T('Eau sous pression','Pressurized water'), BLEU)])


# ─────────────────────────────────────────────────────────────────────
#  9. CONTROLE D'ACCES + INTERPHONE
# ─────────────────────────────────────────────────────────────────────
def _diag_acc(rm):
    cf = rm.courants_faibles
    nodes = [
        _node('ctrl', _T('Controleur','Controller'), 'IP',
              'low', col='A', row='2'),
        _node('lec', _T('Lecteurs badge','Card readers'),
              f"× {cf.nb_portes_controle_acces}", 'low', col='C', row='1'),
        _node('ven', _T('Ventouses/gaches','Locks/strikes'),
              '24V', 'low', col='C', row='2'),
        _node('bds', _T('Boutons sortie','Exit buttons'),
              '', 'low', col='C', row='3'),
        _node('int', _T('Interphones','Intercoms'),
              f"× {cf.nb_interphones}", 'low', col='D', row='2'),
        _node('gtb', 'GTB', _T('Supervision','Supervision'),
              'gtb', col='A', row='4'),
    ]
    edges = [
        {'src': 'ctrl','dst': 'lec', 'color': VERT_DARK, 'label': 'OSDP', 'midx_mm': 80},
        {'src': 'ctrl','dst': 'ven', 'color': NOIR,       'label': '24V',  'midx_mm': 80},
        {'src': 'ctrl','dst': 'bds', 'color': NOIR,       'midx_mm': 80},
        {'src': 'ctrl','dst': 'int', 'color': VERT_DARK, 'label': 'SIP',
         'midx_mm': 138},
        {'src': 'ctrl','dst': 'gtb', 'color': VERT_DARK, 'style': 'dashed',
         'label': 'BACnet'},
    ]
    return _make_diagram(
        _T("9. Controle d'acces / Interphone",
           "9. Access control / Intercom"),
        nodes, edges,
        legend=[(_T('Bus IP','IP bus'), VERT_DARK),
                ('24V', NOIR)])


# ─────────────────────────────────────────────────────────────────────
#  10. GTB / BMS
# ─────────────────────────────────────────────────────────────────────
def _diag_gtb(rm):
    a = rm.automatisation
    # Layout vertical : superviseur en haut, bus horizontal au milieu,
    # 6 consommateurs alignes sur une seule rangee en bas
    nodes = [
        # Superviseur centre
        {'id': 'sup', 'x': 70, 'y': ROW['1'], 'w': 38, 'h': NODE_H,
         'title': _T('Superviseur','Supervisor'), 'sub': a.protocole,
         'color': 'gtb'},
        # Bus horizontal large
        {'id': 'bus', 'x': 8,  'y': ROW['3'], 'w': 162, 'h': 14,
         'title': _T('Bus terrain','Field bus'),
         'sub': f"{a.nb_points_controle} pts {a.protocole}",
         'color': 'gtb'},
    ]
    # 6 consommateurs en une rangee. Largeur 26 mm, x = 4..148
    cons = [
        ('ele', _T('Eclairage','Lighting'), 'low'),
        ('cvc', 'CVC',                       'hvac'),
        ('ene', _T('Energie','Energy'),     'power'),
        ('inc', 'SSI',                       'fire'),
        ('acc', _T('Acces','Access'),       'low'),
        ('asc', _T('Ascenseurs','Lifts'),   'neutral'),
    ]
    cw = 26
    gap = (CONTENT_W - 6 * cw) / 7  # marge egalisee
    for i, (cid, title, color) in enumerate(cons):
        cx = gap + i * (cw + gap)
        nodes.append({'id': cid, 'x': cx, 'y': ROW['5'],
                      'w': cw, 'h': 16,
                      'title': title, 'sub': '', 'color': color})
    edges = [
        {'src': 'sup', 'dst': 'bus',
         'src_side': 'b', 'dst_side': 't', 'color': VERT_DARK},
    ]
    for cid, _, _color in cons:
        edges.append({'src': 'bus', 'dst': cid,
                      'src_side': 'b', 'dst_side': 't',
                      'color': VERT_DARK})
    return _make_diagram(
        _T("10. GTB / BMS — Supervision centrale",
           "10. BMS — Central supervision"),
        nodes, edges,
        legend=[(_T('Bus GTB','BMS bus'), VERT_DARK)])


# ─────────────────────────────────────────────────────────────────────
#  Tables recap
# ─────────────────────────────────────────────────────────────────────
def _t_elec(rm):
    e = rm.electrique
    return _kv_table([
        (_T("Puissance totale", "Total power"), f"{e.puissance_totale_kva:.0f} kVA"),
        (_T("Transformateur", "Transformer"), f"{e.transfo_kva} kVA"),
        (_T("Groupe electrogene", "Backup genset"), f"{e.groupe_electrogene_kva} kVA"),
        (_T("Compteurs", "Meters"), f"{e.nb_compteurs}"),
        (_T("Section colonne", "Riser section"), f"{e.section_colonne_mm2} mm²"),
    ])

def _t_plomb(rm):
    pl = rm.plomberie
    return _kv_table([
        (_T("Logements", "Apartments"), f"{pl.nb_logements}"),
        (_T("Besoin", "Demand"), f"{pl.besoin_total_m3_j:.1f} m³/j"),
        (_T("Citerne", "Tank"), f"{pl.volume_citerne_m3:.0f} m³"),
        (_T("Surpresseur", "Booster"), f"{pl.debit_surpresseur_m3h:.0f} m³/h"),
        (_T("Colonne", "Riser"), f"DN{pl.diam_colonne_montante_mm}"),
        ("CESI", f"{pl.nb_chauffe_eau_solaire}"),
    ])

def _t_clim(rm):
    c = rm.cvc
    return _kv_table([
        (_T("Puissance frigo", "Cooling power"), f"{c.puissance_frigorifique_kw:.0f} kW"),
        (_T("Splits sejour", "Living units"), f"{c.nb_splits_sejour}"),
        (_T("Splits chambre", "Bedroom units"), f"{c.nb_splits_chambre}"),
        (_T("Cassettes", "Cassettes"), f"{c.nb_cassettes}"),
    ])

def _t_vent(rm):
    c = rm.cvc
    return _kv_table([
        (_T("Type VMC", "MVHR type"), c.type_vmc),
        (_T("Caissons VMC", "Units"), f"{c.nb_vmc}"),
    ])

def _t_cf(rm):
    cf = rm.courants_faibles
    return _kv_table([
        (_T("Cameras int.", "Indoor cams"), f"{cf.nb_cameras_int}"),
        (_T("Cameras ext.", "Outdoor cams"), f"{cf.nb_cameras_ext}"),
        (_T("Prises RJ45", "RJ45 ports"), f"{cf.nb_prises_rj45}"),
        (_T("Baies serveur", "Server racks"), f"{cf.baies_serveur}"),
    ])

def _t_si(rm):
    si = rm.securite_incendie
    return _kv_table([
        (_T("Categorie ERP", "ERP category"), si.categorie_erp),
        (_T("Detecteurs fumee", "Smoke detectors"), f"{si.nb_detecteurs_fumee}"),
        (_T("Decl. manuels", "Manual call pts"), f"{si.nb_declencheurs_manuels}"),
        (_T("Sirenes", "Sounders"), f"{si.nb_sirenes}"),
        (_T("RIA", "Hose reels"), f"{si.longueur_ria_ml:.0f} ml"),
        (_T("Sprinklers", "Sprinklers"), f"{si.nb_tetes_sprinkler}"),
    ])

def _t_acc(rm):
    cf = rm.courants_faibles
    return _kv_table([
        (_T("Portes contr. acces", "Access doors"), f"{cf.nb_portes_controle_acces}"),
        (_T("Interphones", "Intercoms"), f"{cf.nb_interphones}"),
    ])

def _t_gtb(rm):
    a = rm.automatisation
    return _kv_table([
        (_T("Niveau", "Level"), a.niveau),
        (_T("Protocole", "Protocol"), a.protocole),
        (_T("Points", "Points"), f"{a.nb_points_controle}"),
        ('BMS', _T("Requis","Required") if a.bms_requis else _T("Optionnel","Optional")),
    ])


# ─────────────────────────────────────────────────────────────────────
#  Entree principale
# ─────────────────────────────────────────────────────────────────────
def _section(story, num, title_fr, title_en, table, drawing,
             caption_fr, caption_en, last=False):
    block = []
    block.extend(section_title(num, _T(title_fr, title_en)))
    block.append(table)
    block.append(Spacer(1, 2 * mm))
    block.append(Paragraph(_T(caption_fr, caption_en), S['body_j']))
    block.append(Spacer(1, 2 * mm))
    block.append(drawing)
    story.append(KeepTogether(block))
    if not last:
        story.append(PageBreak())


def generer_schemas_mep_iso(rm, params: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=ML, rightMargin=MR,
                            topMargin=22 * mm, bottomMargin=18 * mm,
                            title=_T("Schemas de principe MEP",
                                     "MEP Schematic Diagrams"),
                            author='Tijan AI')

    project_name = params.get('nom') or _T("Projet", "Project")
    ville = params.get('ville') or 'Dakar'
    pays = params.get('pays') or 'Senegal'
    sub = f"{project_name} — {ville}, {pays}"

    story = []
    story.append(Paragraph(
        _T("Schemas de principe MEP", "MEP Schematic Diagrams"),
        S['titre']))
    story.append(Paragraph(sub, S['sous_titre']))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(_T(
        "Schemas blocs detailles pour les 10 lots techniques. Chaque diagramme "
        "presente les composants principaux et leurs interactions, avec les "
        "valeurs issues du moteur MEP Tijan AI.",
        "Detailed block diagrams for the 10 technical packages. Each diagram "
        "shows the main components and their interactions, with values produced "
        "by the Tijan AI MEP engine."),
        S['body_j']))
    story.append(Spacer(1, 4 * mm))

    sections = [
        ('1', 'Electricite', 'Electrical', _t_elec(rm), _diag_electricite(rm),
         "Distribution principale TR + Genset via inverseur de source vers TGBT, "
         "puis colonne montante BT alimentant les tableaux divisionnaires d'etage.",
         "Main distribution TR + Genset via ATS to MSB, then LV riser feeding "
         "floor distribution boards."),
        ('2', 'Plomberie', 'Plumbing', _t_plomb(rm), _diag_plomberie(rm),
         "Aspiration depuis citerne, surpresseur, colonne montante DN dimensionnee, "
         "nourrices d'etage et evacuation EU/EV en colonne separee.",
         "Suction from tank, booster pump, sized DN riser, floor manifolds and "
         "separate WW/SW drainage stack."),
        ('3', 'Climatisation', 'HVAC', _t_clim(rm), _diag_clim(rm),
         "Systeme detente directe DRV : unites exterieures en toiture, liaisons "
         "frigorifiques cuivre, unites interieures par espace, evacuation condensats.",
         "VRF direct expansion system: rooftop outdoor units, copper refrigerant "
         "lines, indoor units per space, condensate drainage."),
        ('4', 'Ventilation', 'Ventilation', _t_vent(rm), _diag_vent(rm),
         "Caissons VMC, gaines galva isolees, bouches d'extraction cuisine et SdB, "
         "entrees d'air neuf et rejet en toiture.",
         "MVHR units, insulated galvanized ducts, kitchen and bath exhaust grilles, "
         "fresh air inlets and roof exhaust."),
        ('5', 'CCTV', 'CCTV', _t_cf(rm), _diag_cctv(rm),
         "Architecture IP : NVR central, switch PoE alimentant les cameras int. et "
         "ext., poste de supervision.",
         "IP architecture: central NVR, PoE switch feeding indoor and outdoor cams, "
         "supervision workstation."),
        ('6', 'Sonorisation', 'PA system',
         _kv_table([(_T("Architecture","Architecture"),"100V multi-zones"),
                    (_T("Source","Source"),"BGM + Mic")]),
         _diag_sono(rm),
         "Architecture 100V multi-zones : sources audio, console, ampli matrice, "
         "zones HP independantes (hall, couloirs, parking).",
         "100V multi-zone architecture: audio sources, mixer, matrix amplifier, "
         "independent speaker zones (lobby, corridors, parking)."),
        ('7', 'Detection incendie', 'Fire detection', _t_si(rm), _diag_di(rm),
         "Centrale ECS, detecteurs fumee adressables, declencheurs manuels, "
         "sirenes UGA, commande desenfumage et report d'alarmes vers GTB.",
         "Addressable FACP, smoke detectors, manual call points, UGA sounders, "
         "smoke extraction command and BMS alarm reporting."),
        ('8', 'Extinction incendie', 'Fire suppression', _t_si(rm), _diag_ext(rm),
         "Bache feu, pompe incendie diesel + electrique, colonne seche, RIA, "
         "sprinklers et extincteurs portatifs CO2 / poudre.",
         "Fire tank, diesel + electric fire pump, dry riser, hose reels, sprinklers "
         "and portable CO2 / powder extinguishers."),
        ('9', "Controle d'acces / Interphone", 'Access / Intercom',
         _t_acc(rm), _diag_acc(rm),
         "Controleur IP, lecteurs badge OSDP, ventouses 24V, boutons de sortie, "
         "interphones SIP et report GTB en BACnet.",
         "IP controller, OSDP card readers, 24V mag locks, exit buttons, SIP "
         "intercoms and BMS reporting over BACnet."),
        ('10', 'GTB / BMS', 'BMS', _t_gtb(rm), _diag_gtb(rm),
         "Superviseur central, bus terrain, automates par lot. Interconnexion avec "
         "tous les autres lots (eclairage, CVC, energie, SSI, acces, ascenseurs).",
         "Central supervisor, field bus, package controllers. Interconnection with "
         "all other packages (lighting, HVAC, energy, fire, access, lifts)."),
    ]

    for i, (num, tfr, ten, tab, drw, cfr, cen) in enumerate(sections):
        _section(story, num, tfr, ten, tab, drw, cfr, cen,
                 last=(i == len(sections) - 1))

    hf = HeaderFooter(project_name,
                      _T("Schemas de principe MEP", "MEP Schematic Diagrams"))
    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    pdf = buf.getvalue()
    buf.close()
    return pdf
