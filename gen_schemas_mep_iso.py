"""
gen_schemas_mep_iso.py — Schemas de principe MEP Tijan AI

Produit un PDF avec 10 schemas blocs (un par lot), montrant les composants
principaux et leurs interactions :
  1. Electricite                 (TR + Genset + ATS + TGBT + Colonne + TD)
  2. Plomberie                   (Citerne + Surpresseur + Colonne + Nourrices + ECS)
  3. Climatisation               (UE + UI + Liaisons frigo + Condensats)
  4. Ventilation                 (VMC + Reseau + Bouches + Extracteurs)
  5. CCTV                        (NVR + Switch PoE + Cameras int/ext)
  6. Sonorisation                (Console + Ampli + Zones HP)
  7. Detection incendie          (ECS + Detecteurs + DM + Sirenes/UGA)
  8. Extinction incendie         (Bache + Pompe + Colonne seche + RIA + Sprinklers)
  9. Controle d'acces / Interphone (Controleur + Lecteurs + Ventouses + Interphone)
 10. GTB / BMS                   (Superviseur + Bus + Automates + Liens vers tous lots)

Chaque diagramme est dessine en blocs (rectangles + connecteurs) sur sa propre
page, avec une mini table des parametres-cles a cote ou au-dessus. Toutes les
valeurs proviennent du moteur MEP. Bilingue FR / EN.
"""
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, PageBreak)
from reportlab.graphics.shapes import (Drawing, Rect, Circle, Line, String,
                                        Group, Polygon, PolyLine)

from tijan_theme import (VERT, VERT_DARK, VERT_LIGHT, NOIR, GRIS1, GRIS2, GRIS3,
                         BLANC, BLEU, BLEU_LT, ORANGE, ORANGE_LT, ROUGE,
                         ML, MR, CW, W, S, HeaderFooter,
                         p, fmt_n, section_title, table_style, _current_lang)


def _T(fr, en):
    return en if _current_lang == 'en' else fr


# ─────────────────────────────────────────────────────────────────────
#  Diagramme generique a blocs
# ─────────────────────────────────────────────────────────────────────
#
# Un schema = (nodes, edges, title)
#   node  = dict(id, x, y, w, h, title, sub, color)   coords en mm internes
#   edge  = dict(src, dst, label='', style='solid|dashed', color=None,
#                src_side='r', dst_side='l')
#
# Le rendu se fait dans un Drawing dont la taille est calculee a partir
# de la bounding box des nodes + une marge configurable, evitant tout
# debordement et donc tout chevauchement avec d'autres flowables.

PAD = 8 * mm
H_TITLE = 9 * mm

NODE_COLORS = {
    'power':   (ORANGE_LT, ORANGE),
    'water':   (BLEU_LT,   BLEU),
    'hvac':    (BLEU_LT,   VERT_DARK),
    'fire':    (ORANGE_LT, ROUGE),
    'low':     (VERT_LIGHT, VERT),
    'gtb':     (VERT_LIGHT, VERT_DARK),
    'neutral': (GRIS1,     NOIR),
}


def _node_rect(d, n):
    fill, stroke = NODE_COLORS.get(n.get('color', 'neutral'), NODE_COLORS['neutral'])
    x = PAD + n['x'] * mm
    y = PAD + n['y'] * mm
    w = n['w'] * mm
    h = n['h'] * mm
    d.add(Rect(x, y, w, h, rx=2, ry=2,
               fillColor=fill, strokeColor=stroke, strokeWidth=1.2))
    title = n.get('title', '')
    sub = n.get('sub', '')
    cy = y + h / 2
    if sub:
        d.add(String(x + w / 2, cy + 2, title,
                     fontName='Helvetica-Bold', fontSize=8, textAnchor='middle', fillColor=NOIR))
        d.add(String(x + w / 2, cy - 7, sub,
                     fontName='Helvetica', fontSize=7, textAnchor='middle', fillColor=NOIR))
    else:
        d.add(String(x + w / 2, cy - 2, title,
                     fontName='Helvetica-Bold', fontSize=8, textAnchor='middle', fillColor=NOIR))
    return x, y, w, h


def _anchor(node, side):
    x = PAD + node['x'] * mm
    y = PAD + node['y'] * mm
    w = node['w'] * mm
    h = node['h'] * mm
    if side == 'r':
        return x + w, y + h / 2
    if side == 'l':
        return x, y + h / 2
    if side == 't':
        return x + w / 2, y + h
    if side == 'b':
        return x + w / 2, y
    return x + w / 2, y + h / 2


def _arrow_head(d, x, y, dx, dy, color):
    # Petite tete de fleche dans la direction (dx, dy)
    import math
    L = math.hypot(dx, dy) or 1
    ux, uy = dx / L, dy / L
    # rotation 150°
    a = math.radians(150)
    sz = 2.2 * mm
    p1 = (x + (ux * math.cos(a) - uy * math.sin(a)) * sz,
          y + (ux * math.sin(a) + uy * math.cos(a)) * sz)
    a = math.radians(-150)
    p2 = (x + (ux * math.cos(a) - uy * math.sin(a)) * sz,
          y + (ux * math.sin(a) + uy * math.cos(a)) * sz)
    d.add(Polygon(points=[x, y, p1[0], p1[1], p2[0], p2[1]],
                  fillColor=color, strokeColor=color, strokeWidth=0.5))


def _draw_edge(d, nodes_by_id, e):
    src = nodes_by_id[e['src']]
    dst = nodes_by_id[e['dst']]
    color = e.get('color') or NOIR
    style = e.get('style', 'solid')
    sx, sy = _anchor(src, e.get('src_side', 'r'))
    dx, dy = _anchor(dst, e.get('dst_side', 'l'))
    # Routage en L (sx,sy) → coude → (dx,dy) horizontal d'abord
    midx = (sx + dx) / 2
    pts = [sx, sy, midx, sy, midx, dy, dx, dy]
    if style == 'dashed':
        d.add(PolyLine(points=pts, strokeColor=color, strokeWidth=1.2,
                       strokeDashArray=[3, 2]))
    else:
        d.add(PolyLine(points=pts, strokeColor=color, strokeWidth=1.4))
    # Tete de fleche en direction de dst
    last_dx = dx - midx
    last_dy = 0 if dy == sy else 0
    _arrow_head(d, dx, dy, dx - midx if dx != midx else 1, 0, color)
    # Label central
    lab = e.get('label', '')
    if lab:
        d.add(String(midx + 1, (sy + dy) / 2 + 2, lab,
                     fontName='Helvetica', fontSize=6.5, fillColor=color))


def _make_diagram(title, nodes, edges, content_w_mm=170, content_h_mm=110):
    """Cree un Drawing dimensionne avec marges; titre interne en haut."""
    W_pts = content_w_mm * mm + 2 * PAD
    H_pts = content_h_mm * mm + 2 * PAD + H_TITLE
    d = Drawing(W_pts, H_pts)
    # Bordure douce
    d.add(Rect(PAD * 0.5, PAD * 0.5,
               W_pts - PAD, H_pts - PAD,
               rx=3, ry=3, fillColor=None,
               strokeColor=GRIS2, strokeWidth=0.6))
    # Titre interne
    d.add(String(W_pts / 2, H_pts - PAD,
                 title,
                 fontName='Helvetica-Bold', fontSize=10,
                 textAnchor='middle', fillColor=VERT_DARK))
    # Nodes
    nodes_by_id = {n['id']: n for n in nodes}
    for n in nodes:
        _node_rect(d, n)
    # Edges
    for e in edges:
        _draw_edge(d, nodes_by_id, e)
    return d


# ─────────────────────────────────────────────────────────────────────
#  Helpers — table recap a 2 colonnes
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
    nb_niveaux = int(getattr(rm.params, 'nb_niveaux', 4))
    n_show = min(max(nb_niveaux, 1), 6)
    nodes = [
        {'id': 'tr',   'x': 5,  'y': 80, 'w': 30, 'h': 14,
         'title': 'TR',  'sub': f"{e.transfo_kva} kVA", 'color': 'power'},
        {'id': 'gen',  'x': 5,  'y': 55, 'w': 30, 'h': 14,
         'title': _T('Groupe', 'Genset'), 'sub': f"{e.groupe_electrogene_kva} kVA", 'color': 'neutral'},
        {'id': 'ats',  'x': 50, 'y': 67, 'w': 22, 'h': 14,
         'title': 'ATS', 'sub': _T('Inverseur', 'Transfer sw.'), 'color': 'neutral'},
        {'id': 'tgbt', 'x': 85, 'y': 60, 'w': 30, 'h': 22,
         'title': 'TGBT', 'sub': f"{e.puissance_totale_kva:.0f} kVA", 'color': 'low'},
        {'id': 'col',  'x': 130, 'y': 60, 'w': 22, 'h': 22,
         'title': _T('Colonne', 'Riser'), 'sub': f"{e.section_colonne_mm2} mm²", 'color': 'low'},
    ]
    edges = [
        {'src': 'tr',   'dst': 'ats',  'color': ORANGE, 'label': 'HTA/BT'},
        {'src': 'gen',  'dst': 'ats',  'color': NOIR,   'label': _T('Secours', 'Backup')},
        {'src': 'ats',  'dst': 'tgbt', 'color': ORANGE},
        {'src': 'tgbt', 'dst': 'col',  'color': NOIR},
    ]
    # TD par niveau
    for i in range(n_show):
        y = 95 - i * 16
        nid = f'td{i}'
        nodes.append({'id': nid, 'x': 158, 'y': y, 'w': 14, 'h': 10,
                      'title': f"TD N{i+1}", 'color': 'low'})
        edges.append({'src': 'col', 'dst': nid, 'color': NOIR})
    return _make_diagram(_T("1. Electricite — Distribution principale",
                            "1. Electrical — Main distribution"),
                         nodes, edges)


# ─────────────────────────────────────────────────────────────────────
#  2. PLOMBERIE
# ─────────────────────────────────────────────────────────────────────
def _diag_plomberie(rm):
    pl = rm.plomberie
    nb_niveaux = int(getattr(rm.params, 'nb_niveaux', 4))
    n_show = min(max(nb_niveaux, 1), 6)
    nodes = [
        {'id': 'cit',  'x': 5,  'y': 75, 'w': 30, 'h': 22,
         'title': _T('Citerne', 'Tank'), 'sub': f"{pl.volume_citerne_m3:.0f} m³", 'color': 'water'},
        {'id': 'pmp',  'x': 50, 'y': 80, 'w': 24, 'h': 14,
         'title': _T('Surpresseur', 'Booster'), 'sub': f"{pl.debit_surpresseur_m3h:.0f} m³/h", 'color': 'water'},
        {'id': 'col',  'x': 90, 'y': 60, 'w': 22, 'h': 38,
         'title': _T('Colonne', 'Riser'), 'sub': f"DN{pl.diam_colonne_montante_mm}", 'color': 'water'},
        {'id': 'ces',  'x': 5,  'y': 25, 'w': 30, 'h': 14,
         'title': 'CESI', 'sub': f"{pl.nb_chauffe_eau_solaire} {_T('unites','units')}", 'color': 'fire'},
        {'id': 'ev',   'x': 130, 'y': 20, 'w': 30, 'h': 14,
         'title': _T('Evac. EU/EV', 'Drain stack'), 'sub': 'PVC DN100', 'color': 'neutral'},
    ]
    edges = [
        {'src': 'cit', 'dst': 'pmp', 'color': BLEU, 'label': _T('Aspiration', 'Suction')},
        {'src': 'pmp', 'dst': 'col', 'color': BLEU, 'label': _T('Refoulement', 'Discharge')},
        {'src': 'ces', 'dst': 'col', 'color': ORANGE, 'label': 'ECS', 'src_side': 'r', 'dst_side': 'l'},
    ]
    # Nourrices par niveau
    for i in range(n_show):
        y = 92 - i * 12
        nid = f'nv{i}'
        nodes.append({'id': nid, 'x': 130, 'y': y, 'w': 24, 'h': 9,
                      'title': f"N{i+1}", 'sub': _T('Nourrice', 'Manifold'), 'color': 'water'})
        edges.append({'src': 'col', 'dst': nid, 'color': BLEU})
    edges.append({'src': 'col', 'dst': 'ev', 'color': GRIS3, 'style': 'dashed', 'src_side': 'b'})
    return _make_diagram(_T("2. Plomberie — Eau froide / ECS / Evacuation",
                            "2. Plumbing — Cold water / DHW / Drainage"),
                         nodes, edges)


# ─────────────────────────────────────────────────────────────────────
#  3. CLIMATISATION
# ─────────────────────────────────────────────────────────────────────
def _diag_clim(rm):
    c = rm.cvc
    nodes = [
        {'id': 'ue',  'x': 5,  'y': 80, 'w': 32, 'h': 18,
         'title': _T('Unites Ext.', 'Outdoor units'), 'sub': f"{c.puissance_frigorifique_kw:.0f} kW", 'color': 'hvac'},
        {'id': 'lf',  'x': 55, 'y': 82, 'w': 28, 'h': 14,
         'title': _T('Liaisons frigo', 'Refrigerant lines'), 'sub': 'Cuivre', 'color': 'neutral'},
        {'id': 'sj',  'x': 100, 'y': 92, 'w': 32, 'h': 12,
         'title': _T('Splits sejour', 'Living units'), 'sub': f"{c.nb_splits_sejour}", 'color': 'hvac'},
        {'id': 'ch',  'x': 100, 'y': 76, 'w': 32, 'h': 12,
         'title': _T('Splits chambre', 'Bedroom units'), 'sub': f"{c.nb_splits_chambre}", 'color': 'hvac'},
        {'id': 'cas', 'x': 100, 'y': 60, 'w': 32, 'h': 12,
         'title': _T('Cassettes', 'Cassettes'), 'sub': f"{c.nb_cassettes}", 'color': 'hvac'},
        {'id': 'cnd', 'x': 145, 'y': 30, 'w': 28, 'h': 12,
         'title': _T('Condensats', 'Condensate'), 'sub': 'PVC DN32', 'color': 'water'},
    ]
    edges = [
        {'src': 'ue', 'dst': 'lf', 'color': BLEU},
        {'src': 'lf', 'dst': 'sj', 'color': BLEU},
        {'src': 'lf', 'dst': 'ch', 'color': BLEU},
        {'src': 'lf', 'dst': 'cas','color': BLEU},
        {'src': 'sj', 'dst': 'cnd','color': GRIS3, 'style': 'dashed'},
        {'src': 'ch', 'dst': 'cnd','color': GRIS3, 'style': 'dashed'},
        {'src': 'cas','dst': 'cnd','color': GRIS3, 'style': 'dashed'},
    ]
    return _make_diagram(_T("3. Climatisation — Detente directe DRV",
                            "3. HVAC — VRF direct expansion"),
                         nodes, edges)


# ─────────────────────────────────────────────────────────────────────
#  4. VENTILATION
# ─────────────────────────────────────────────────────────────────────
def _diag_vent(rm):
    c = rm.cvc
    nodes = [
        {'id': 'vmc', 'x': 5,  'y': 80, 'w': 32, 'h': 16,
         'title': f"VMC {c.type_vmc}", 'sub': f"{c.nb_vmc} {_T('caissons','units')}", 'color': 'hvac'},
        {'id': 'gp',  'x': 55, 'y': 82, 'w': 28, 'h': 12,
         'title': _T('Gaines princ.', 'Main ducts'), 'sub': 'Galva', 'color': 'neutral'},
        {'id': 'cuis','x': 100, 'y': 92, 'w': 32, 'h': 12,
         'title': _T('Bouches cuisine', 'Kitchen vents'), 'color': 'hvac'},
        {'id': 'sdb', 'x': 100, 'y': 76, 'w': 32, 'h': 12,
         'title': _T('Bouches SdB / WC', 'Bath / WC vents'), 'color': 'hvac'},
        {'id': 'amen','x': 100, 'y': 60, 'w': 32, 'h': 12,
         'title': _T('Entree air neuf', 'Fresh air inlets'), 'color': 'hvac'},
        {'id': 'rej', 'x': 145, 'y': 30, 'w': 28, 'h': 12,
         'title': _T('Rejet toiture', 'Roof exhaust'), 'color': 'neutral'},
    ]
    edges = [
        {'src': 'vmc', 'dst': 'gp', 'color': BLEU},
        {'src': 'gp',  'dst': 'cuis','color': BLEU},
        {'src': 'gp',  'dst': 'sdb', 'color': BLEU},
        {'src': 'amen','dst': 'gp',  'color': VERT, 'label': _T("Air neuf","Fresh")},
        {'src': 'gp',  'dst': 'rej', 'color': GRIS3, 'style': 'dashed'},
    ]
    return _make_diagram(_T("4. Ventilation — Schema aeraulique",
                            "4. Ventilation — Air-flow schematic"),
                         nodes, edges)


# ─────────────────────────────────────────────────────────────────────
#  5. CCTV
# ─────────────────────────────────────────────────────────────────────
def _diag_cctv(rm):
    cf = rm.courants_faibles
    nodes = [
        {'id': 'nvr', 'x': 5,   'y': 75, 'w': 32, 'h': 18,
         'title': 'NVR', 'sub': _T('Enregistreur', 'Recorder'), 'color': 'low'},
        {'id': 'sw',  'x': 55,  'y': 75, 'w': 28, 'h': 18,
         'title': 'Switch PoE', 'color': 'low'},
        {'id': 'cint','x': 100, 'y': 90, 'w': 36, 'h': 14,
         'title': _T('Cameras int.', 'Indoor cams'), 'sub': f"{cf.nb_cameras_int}", 'color': 'low'},
        {'id': 'cext','x': 100, 'y': 65, 'w': 36, 'h': 14,
         'title': _T('Cameras ext.', 'Outdoor cams'), 'sub': f"{cf.nb_cameras_ext}", 'color': 'low'},
        {'id': 'ecran','x': 5,  'y': 35, 'w': 32, 'h': 14,
         'title': _T('Ecran PC', 'Monitor PC'), 'color': 'neutral'},
    ]
    edges = [
        {'src': 'nvr', 'dst': 'sw', 'color': VERT_DARK, 'label': 'LAN'},
        {'src': 'sw',  'dst': 'cint', 'color': VERT_DARK, 'label': 'PoE'},
        {'src': 'sw',  'dst': 'cext', 'color': VERT_DARK, 'label': 'PoE'},
        {'src': 'nvr', 'dst': 'ecran', 'color': NOIR, 'src_side': 'b', 'dst_side': 't', 'label': 'HDMI'},
    ]
    return _make_diagram(_T("5. CCTV — Videosurveillance IP",
                            "5. CCTV — IP video surveillance"),
                         nodes, edges)


# ─────────────────────────────────────────────────────────────────────
#  6. SONORISATION
# ─────────────────────────────────────────────────────────────────────
def _diag_sono(rm):
    nodes = [
        {'id': 'src', 'x': 5,   'y': 80, 'w': 32, 'h': 14,
         'title': _T('Sources', 'Sources'), 'sub': 'Mic / BGM', 'color': 'low'},
        {'id': 'cons','x': 50,  'y': 80, 'w': 28, 'h': 14,
         'title': _T('Console', 'Mixer'), 'color': 'low'},
        {'id': 'amp', 'x': 90,  'y': 80, 'w': 28, 'h': 14,
         'title': _T('Ampli matrice', 'Matrix amp'), 'color': 'low'},
        {'id': 'z1',  'x': 130, 'y': 96, 'w': 32, 'h': 10,
         'title': _T('Zone hall', 'Lobby'), 'color': 'low'},
        {'id': 'z2',  'x': 130, 'y': 82, 'w': 32, 'h': 10,
         'title': _T('Zone couloirs', 'Corridors'), 'color': 'low'},
        {'id': 'z3',  'x': 130, 'y': 68, 'w': 32, 'h': 10,
         'title': _T('Zone parking', 'Parking'), 'color': 'low'},
    ]
    edges = [
        {'src': 'src', 'dst': 'cons', 'color': VERT_DARK},
        {'src': 'cons','dst': 'amp', 'color': VERT_DARK},
        {'src': 'amp', 'dst': 'z1',  'color': VERT_DARK, 'label': '100V'},
        {'src': 'amp', 'dst': 'z2',  'color': VERT_DARK, 'label': '100V'},
        {'src': 'amp', 'dst': 'z3',  'color': VERT_DARK, 'label': '100V'},
    ]
    return _make_diagram(_T("6. Sonorisation — Diffusion 100V multi-zones",
                            "6. PA system — 100V multi-zone"),
                         nodes, edges)


# ─────────────────────────────────────────────────────────────────────
#  7. DETECTION INCENDIE
# ─────────────────────────────────────────────────────────────────────
def _diag_di(rm):
    si = rm.securite_incendie
    nodes = [
        {'id': 'ecs', 'x': 5,   'y': 75, 'w': 32, 'h': 22,
         'title': 'ECS', 'sub': f"{si.centrale_zones} {_T('zones','zones')}", 'color': 'fire'},
        {'id': 'det', 'x': 55,  'y': 92, 'w': 36, 'h': 12,
         'title': _T('Detecteurs fumee', 'Smoke detectors'), 'sub': f"{si.nb_detecteurs_fumee}", 'color': 'fire'},
        {'id': 'dm',  'x': 55,  'y': 76, 'w': 36, 'h': 12,
         'title': _T('Decl. manuels', 'Manual call points'), 'sub': f"{si.nb_declencheurs_manuels}", 'color': 'fire'},
        {'id': 'sir', 'x': 55,  'y': 60, 'w': 36, 'h': 12,
         'title': _T('Sirenes UGA', 'Sounders UGA'), 'sub': f"{si.nb_sirenes}", 'color': 'fire'},
        {'id': 'des', 'x': 110, 'y': 76, 'w': 36, 'h': 12,
         'title': _T('Desenfumage', 'Smoke extraction'),
         'sub': _T('Requis','Required') if si.desenfumage_requis else _T('Non requis','Not req.'),
         'color': 'fire'},
        {'id': 'gtb', 'x': 110, 'y': 40, 'w': 36, 'h': 12,
         'title': _T('Report GTB', 'BMS report'), 'color': 'gtb'},
    ]
    edges = [
        {'src': 'det', 'dst': 'ecs', 'color': ROUGE, 'src_side': 'l', 'dst_side': 'r'},
        {'src': 'dm',  'dst': 'ecs', 'color': ROUGE, 'src_side': 'l', 'dst_side': 'r'},
        {'src': 'ecs', 'dst': 'sir', 'color': ROUGE, 'label': 'UGA'},
        {'src': 'ecs', 'dst': 'des', 'color': ROUGE, 'label': _T('Comm. cmd.', 'Cmd')},
        {'src': 'ecs', 'dst': 'gtb', 'color': VERT_DARK, 'style': 'dashed', 'label': 'TCP/IP'},
    ]
    return _make_diagram(_T("7. Detection incendie — SSI categorie A",
                            "7. Fire detection — SSI Cat. A"),
                         nodes, edges)


# ─────────────────────────────────────────────────────────────────────
#  8. EXTINCTION INCENDIE
# ─────────────────────────────────────────────────────────────────────
def _diag_ext(rm):
    si = rm.securite_incendie
    nodes = [
        {'id': 'bac', 'x': 5,   'y': 75, 'w': 30, 'h': 22,
         'title': _T('Bache feu', 'Fire tank'), 'sub': '120 m³', 'color': 'water'},
        {'id': 'pmp', 'x': 50,  'y': 80, 'w': 28, 'h': 14,
         'title': _T('Pompe incendie', 'Fire pump'), 'sub': 'Diesel + Elec', 'color': 'fire'},
        {'id': 'cs',  'x': 90,  'y': 60, 'w': 22, 'h': 38,
         'title': _T('Colonne seche', 'Dry riser'), 'color': 'fire'},
        {'id': 'ria', 'x': 130, 'y': 92, 'w': 36, 'h': 10,
         'title': 'RIA', 'sub': f"{si.longueur_ria_ml:.0f} ml", 'color': 'fire'},
        {'id': 'spr', 'x': 130, 'y': 76, 'w': 36, 'h': 10,
         'title': _T('Sprinklers', 'Sprinklers'), 'sub': f"{si.nb_tetes_sprinkler}", 'color': 'fire'},
        {'id': 'ext', 'x': 130, 'y': 60, 'w': 36, 'h': 10,
         'title': _T('Extincteurs', 'Extinguishers'),
         'sub': f"CO2 {si.nb_extincteurs_co2} / P {si.nb_extincteurs_poudre}",
         'color': 'fire'},
    ]
    edges = [
        {'src': 'bac', 'dst': 'pmp', 'color': BLEU},
        {'src': 'pmp', 'dst': 'cs',  'color': BLEU, 'label': _T('Refoul.', 'Disch.')},
        {'src': 'cs',  'dst': 'ria', 'color': BLEU},
        {'src': 'cs',  'dst': 'spr', 'color': BLEU},
    ]
    return _make_diagram(_T("8. Extinction incendie — RIA + Colonne seche + Sprinklers",
                            "8. Fire suppression — Hose reels + Dry riser + Sprinklers"),
                         nodes, edges)


# ─────────────────────────────────────────────────────────────────────
#  9. CONTROLE D'ACCES + INTERPHONE
# ─────────────────────────────────────────────────────────────────────
def _diag_acc(rm):
    cf = rm.courants_faibles
    nodes = [
        {'id': 'ctrl','x': 5,   'y': 75, 'w': 32, 'h': 18,
         'title': _T('Controleur', 'Controller'), 'sub': 'IP', 'color': 'low'},
        {'id': 'lec', 'x': 55,  'y': 90, 'w': 36, 'h': 12,
         'title': _T('Lecteurs badge', 'Card readers'), 'sub': f"{cf.nb_portes_controle_acces}", 'color': 'low'},
        {'id': 'ven', 'x': 55,  'y': 74, 'w': 36, 'h': 12,
         'title': _T('Ventouses / gaches', 'Mag locks / strikes'), 'color': 'low'},
        {'id': 'bds', 'x': 55,  'y': 58, 'w': 36, 'h': 12,
         'title': _T('Boutons sortie', 'Exit buttons'), 'color': 'low'},
        {'id': 'int', 'x': 110, 'y': 90, 'w': 36, 'h': 12,
         'title': _T('Interphones', 'Intercoms'), 'sub': f"{cf.nb_interphones}", 'color': 'low'},
        {'id': 'gtb', 'x': 110, 'y': 50, 'w': 36, 'h': 12,
         'title': 'GTB', 'sub': _T('Supervision','Supervision'), 'color': 'gtb'},
    ]
    edges = [
        {'src': 'ctrl','dst': 'lec', 'color': VERT_DARK, 'label': 'OSDP'},
        {'src': 'ctrl','dst': 'ven', 'color': NOIR, 'label': '24V'},
        {'src': 'ctrl','dst': 'bds', 'color': NOIR},
        {'src': 'ctrl','dst': 'int', 'color': VERT_DARK, 'label': 'SIP'},
        {'src': 'ctrl','dst': 'gtb', 'color': VERT_DARK, 'style': 'dashed', 'label': 'BACnet'},
    ]
    return _make_diagram(_T("9. Controle d'acces / Interphone",
                            "9. Access control / Intercom"),
                         nodes, edges)


# ─────────────────────────────────────────────────────────────────────
#  10. GTB / BMS
# ─────────────────────────────────────────────────────────────────────
def _diag_gtb(rm):
    a = rm.automatisation
    nodes = [
        {'id': 'sup', 'x': 70,  'y': 95, 'w': 36, 'h': 14,
         'title': _T('Superviseur', 'Supervisor'), 'sub': f"{a.protocole}", 'color': 'gtb'},
        {'id': 'bus', 'x': 70,  'y': 70, 'w': 36, 'h': 12,
         'title': _T('Bus terrain', 'Field bus'), 'sub': f"{a.nb_points_controle} pts", 'color': 'gtb'},
        {'id': 'ele', 'x': 5,   'y': 88, 'w': 32, 'h': 10,
         'title': _T('Eclairage','Lighting'), 'color': 'low'},
        {'id': 'cvc', 'x': 5,   'y': 74, 'w': 32, 'h': 10,
         'title': 'CVC', 'color': 'hvac'},
        {'id': 'ene', 'x': 5,   'y': 60, 'w': 32, 'h': 10,
         'title': _T('Compteurs','Energy meters'), 'color': 'power'},
        {'id': 'inc', 'x': 138, 'y': 88, 'w': 34, 'h': 10,
         'title': _T('SSI','Fire'), 'color': 'fire'},
        {'id': 'acc', 'x': 138, 'y': 74, 'w': 34, 'h': 10,
         'title': _T('Acces','Access'), 'color': 'low'},
        {'id': 'asc', 'x': 138, 'y': 60, 'w': 34, 'h': 10,
         'title': _T('Ascenseurs','Lifts'), 'color': 'neutral'},
    ]
    edges = [
        {'src': 'sup', 'dst': 'bus', 'color': VERT_DARK, 'src_side': 'b', 'dst_side': 't'},
        {'src': 'bus', 'dst': 'ele', 'color': VERT_DARK},
        {'src': 'bus', 'dst': 'cvc', 'color': VERT_DARK},
        {'src': 'bus', 'dst': 'ene', 'color': VERT_DARK},
        {'src': 'bus', 'dst': 'inc', 'color': VERT_DARK, 'style': 'dashed'},
        {'src': 'bus', 'dst': 'acc', 'color': VERT_DARK, 'style': 'dashed'},
        {'src': 'bus', 'dst': 'asc', 'color': VERT_DARK, 'style': 'dashed'},
    ]
    return _make_diagram(_T("10. GTB / BMS — Supervision centrale",
                            "10. BMS — Central supervision"),
                         nodes, edges)


# ─────────────────────────────────────────────────────────────────────
#  Tables recap par lot
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
def _section(story, num, title, table, drawing, caption_fr, caption_en):
    story.extend(section_title(num, _T(title['fr'], title['en'])))
    story.append(table)
    story.append(Spacer(1, 3 * mm))
    story.append(drawing)
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(_T(caption_fr, caption_en), S['body_j']))
    story.append(PageBreak())


def generer_schemas_mep_iso(rm, params: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=ML, rightMargin=MR,
                            topMargin=22 * mm, bottomMargin=18 * mm,
                            title=_T("Schemas de principe MEP", "MEP Schematic Diagrams"),
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
        "presente les composants principaux et leurs interactions, avec les valeurs "
        "issues du moteur MEP Tijan AI.",
        "Detailed block diagrams for the 10 technical packages. Each diagram shows "
        "the main components and their interactions, with values produced by the "
        "Tijan AI MEP engine."),
        S['body_j']))
    story.append(Spacer(1, 4 * mm))

    sections = [
        ('1', {'fr': 'Electricite', 'en': 'Electrical'},
         _t_elec(rm), _diag_electricite(rm),
         "Distribution principale TR + Genset via inverseur de source vers TGBT, "
         "puis colonne montante BT alimentant les tableaux divisionnaires d'etage.",
         "Main distribution TR + Genset via ATS to MSB, then LV riser feeding "
         "floor distribution boards."),
        ('2', {'fr': 'Plomberie', 'en': 'Plumbing'},
         _t_plomb(rm), _diag_plomberie(rm),
         "Aspiration depuis citerne, surpresseur, colonne montante DN dimensionnee, "
         "nourrices d'etage et evacuation EU/EV en colonne separee.",
         "Suction from tank, booster pump, sized DN riser, floor manifolds and "
         "separate WW/SW drainage stack."),
        ('3', {'fr': 'Climatisation', 'en': 'HVAC'},
         _t_clim(rm), _diag_clim(rm),
         "Systeme detente directe DRV : unites exterieures en toiture, liaisons "
         "frigorifiques cuivre, unites interieures par espace, evacuation condensats.",
         "VRF direct expansion system: rooftop outdoor units, copper refrigerant "
         "lines, indoor units per space, condensate drainage."),
        ('4', {'fr': 'Ventilation', 'en': 'Ventilation'},
         _t_vent(rm), _diag_vent(rm),
         "Caissons VMC, gaines galva isolees, bouches d'extraction cuisine et SdB, "
         "entrees d'air neuf et rejet en toiture.",
         "MVHR units, insulated galvanized ducts, kitchen and bath exhaust grilles, "
         "fresh air inlets and roof exhaust."),
        ('5', {'fr': 'CCTV', 'en': 'CCTV'},
         _t_cf(rm), _diag_cctv(rm),
         "Architecture IP : NVR central, switch PoE alimentant les cameras int. et ext., "
         "ecran de supervision PC.",
         "IP architecture: central NVR, PoE switch feeding indoor and outdoor cams, "
         "PC supervision monitor."),
        ('6', {'fr': 'Sonorisation', 'en': 'PA system'},
         _kv_table([(_T("Architecture","Architecture"),"100V multi-zones"),
                    (_T("Source","Source"),"BGM + Mic")]),
         _diag_sono(rm),
         "Architecture 100V multi-zones : sources audio, console, ampli matrice, "
         "zones HP independantes (hall, couloirs, parking).",
         "100V multi-zone architecture: audio sources, mixer, matrix amplifier, "
         "independent speaker zones (lobby, corridors, parking)."),
        ('7', {'fr': 'Detection incendie', 'en': 'Fire detection'},
         _t_si(rm), _diag_di(rm),
         "Centrale ECS, detecteurs fumee adressables, declencheurs manuels, sirenes UGA, "
         "commande desenfumage et report d'alarmes vers GTB.",
         "Addressable FACP, smoke detectors, manual call points, UGA sounders, "
         "smoke extraction command and BMS alarm reporting."),
        ('8', {'fr': 'Extinction incendie', 'en': 'Fire suppression'},
         _t_si(rm), _diag_ext(rm),
         "Bache feu, pompe incendie diesel + electrique, colonne seche, RIA, sprinklers "
         "et extincteurs portatifs CO2 / poudre.",
         "Fire tank, diesel + electric fire pump, dry riser, hose reels, sprinklers "
         "and portable CO2 / powder extinguishers."),
        ('9', {'fr': "Controle d'acces / Interphone", 'en': 'Access / Intercom'},
         _t_acc(rm), _diag_acc(rm),
         "Controleur IP, lecteurs badge OSDP, ventouses 24V, boutons de sortie, "
         "interphones SIP et report GTB en BACnet.",
         "IP controller, OSDP card readers, 24V mag locks, exit buttons, SIP "
         "intercoms and BMS reporting over BACnet."),
        ('10', {'fr': 'GTB / BMS', 'en': 'BMS'},
         _t_gtb(rm), _diag_gtb(rm),
         "Superviseur central, bus terrain, automates par lot. Interconnexion avec "
         "tous les autres lots (eclairage, CVC, energie, SSI, acces, ascenseurs).",
         "Central supervisor, field bus, package controllers. Interconnection with "
         "all other packages (lighting, HVAC, energy, fire, access, lifts)."),
    ]

    for num, t, tab, drw, cfr, cen in sections:
        _section(story, num, t, tab, drw, cfr, cen)

    # Pas de page break apres la derniere section
    if story and isinstance(story[-1], PageBreak):
        story.pop()

    hf = HeaderFooter(project_name, _T("Schemas de principe MEP", "MEP Schematic Diagrams"))
    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    pdf = buf.getvalue()
    buf.close()
    return pdf
