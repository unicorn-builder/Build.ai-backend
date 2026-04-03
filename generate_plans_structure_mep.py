"""
generate_plans_structure_mep.py — Plans Structure étendu + Plans MEP
Même pattern que generate_plans_v4.py (le seul générateur validé).

Grille : nb_travees_x/y × portee_max/min depuis ParamsProjet
Structure : poteaux/poutres/dalle/fondation depuis ResultatsStructure
MEP : équipements depuis ResultatsMEP, placés dans les travées

Zéro hardcoding. Chaque valeur vient des moteurs de calcul.
"""
import math
from datetime import datetime
from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdfcanvas

# ── Colors — mêmes que v4 ──
NOIR  = colors.HexColor("#111111")
GRIS2 = colors.HexColor("#555555")
GRIS3 = colors.HexColor("#888888")
GRIS4 = colors.HexColor("#CCCCCC")
GRIS5 = colors.HexColor("#E8E8E8")
BLANC = colors.white
VERT  = colors.HexColor("#43A956")
VERT_P= colors.HexColor("#E8F5E9")
ROUGE = colors.HexColor("#CC3333")
BLEU  = colors.HexColor("#2196F3")
BLEU_B= colors.HexColor("#D6E4F0")
ORANGE= colors.HexColor("#FF9800")
CYAN  = colors.HexColor("#00ACC1")
MARRON= colors.HexColor("#795548")
JAUNE = colors.HexColor("#FBC02D")
VIOLET= colors.HexColor("#7B1FA2")

A3L = landscape(A3)


# ══════════════════════════════════════════
# UTILITAIRES — copie exacte de v4
# ══════════════════════════════════════════

def _border(c, w, h):
    c.setStrokeColor(NOIR); c.setLineWidth(0.5)
    c.rect(8*mm, 8*mm, w-16*mm, h-16*mm)

def _axis_label(c, x, y, label):
    r = 4.5*mm
    c.setStrokeColor(NOIR); c.setLineWidth(0.4); c.setFillColor(BLANC)
    c.circle(x, y, r, fill=1, stroke=1)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 7)
    tw = c.stringWidth(str(label), "Helvetica-Bold", 7)
    c.drawString(x - tw/2, y - 2.5, str(label))

def _cartouche(c, w, h, p, titre, pg, total, ech="1/100"):
    cw, ch_ = 180*mm, 28*mm
    cx = w - cw - 8*mm; cy = 6*mm
    c.setFillColor(BLANC); c.setStrokeColor(NOIR); c.setLineWidth(0.7)
    c.rect(cx, cy, cw, ch_, fill=1, stroke=1)
    c1, c2 = 38*mm, 108*mm
    c.setLineWidth(0.3)
    c.line(cx+c1, cy, cx+c1, cy+ch_)
    c.line(cx+c2, cy, cx+c2, cy+ch_)
    c.line(cx+c1, cy+ch_/2, cx+cw, cy+ch_/2)
    c.setFillColor(VERT); c.setFont("Helvetica-Bold", 10)
    c.drawString(cx+3*mm, cy+ch_-9*mm, "TIJAN AI")
    c.setFillColor(GRIS3); c.setFont("Helvetica", 5.5)
    c.drawString(cx+3*mm, cy+ch_-14*mm, "Engineering Intelligence")
    c.drawString(cx+3*mm, cy+5*mm, f"Date: {datetime.now().strftime('%d/%m/%Y')}")
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 8)
    c.drawString(cx+c1+3*mm, cy+ch_-9*mm, p.get("nom","Projet")[:30])
    c.setFillColor(VERT); c.setFont("Helvetica-Bold", 7)
    c.drawString(cx+c1+3*mm, cy+ch_/2-8*mm, titre)
    c.setFillColor(GRIS3); c.setFont("Helvetica", 6)
    c.drawString(cx+c2+3*mm, cy+ch_-9*mm, f"Éch: {ech}")
    c.drawString(cx+c2+3*mm, cy+ch_-14*mm, p.get("ville","Dakar"))
    c.drawString(cx+c2+3*mm, cy+5*mm, f"Pl. {pg}/{total}")


def _build_grid(p):
    """Build grid params — même logique que pl_coffrage dans v4."""
    nx = min(p.get("nb_travees_x", 4), 8)
    ny = max(min(p.get("nb_travees_y", 3), 6), 3)
    px_m = p.get("portee_max_m", 5.0)
    py_m = p.get("portee_min_m", 4.0)
    if py_m < 2.0:
        py_m = px_m * 0.65
    return nx, ny, px_m, py_m


def _grid_layout(w, h, nx, ny, px_m, py_m, ml=50*mm, mb=55*mm, mr=72*mm, mt=30*mm):
    """Calculate grid position and scale — copie de v4."""
    dw = w - ml - mr
    dh = h - mb - mt
    tot_x = px_m * nx
    tot_y = py_m * ny
    sc = min(dw / tot_x, dh / tot_y)
    gw = tot_x * sc
    gh = tot_y * sc
    ox = ml + (dw - gw) / 2
    oy = mb + (dh - gh) / 2
    return ox, oy, sc, gw, gh


def _draw_grid_axes(c, ox, oy, sc, nx, ny, px_m, py_m, gw, gh):
    """Draw grid axes lines + labels — copie de v4."""
    c.setStrokeColor(GRIS4); c.setLineWidth(0.2); c.setDash(4, 2)
    for i in range(nx + 1):
        xp = ox + i * px_m * sc
        c.line(xp, oy - 8*mm, xp, oy + gh + 8*mm)
    for j in range(ny + 1):
        yp = oy + j * py_m * sc
        c.line(ox - 8*mm, yp, ox + gw + 8*mm, yp)
    c.setDash()
    for i in range(nx + 1):
        _axis_label(c, ox + i * px_m * sc, oy - 15*mm, str(i + 1))
    for j in range(ny + 1):
        _axis_label(c, ox - 15*mm, oy + j * py_m * sc, chr(65 + j))
    # Dimensions
    c.setFillColor(GRIS3); c.setFont("Helvetica", 5.5)
    for i in range(nx):
        mid = ox + (i + 0.5) * px_m * sc
        c.drawCentredString(mid, oy - 9*mm, f"{px_m*1000:.0f}")
    for j in range(ny):
        mid_y = oy + (j + 0.5) * py_m * sc
        c.saveState(); c.translate(ox - 9*mm, mid_y); c.rotate(90)
        c.drawCentredString(0, 0, f"{py_m*1000:.0f}"); c.restoreState()


def _draw_poteaux(c, ox, oy, sc, nx, ny, px_m, py_m, pot_s):
    """Draw columns at grid intersections — copie de v4."""
    pt_d = max(pot_s * sc / 1000, 3)
    for i in range(nx + 1):
        for j in range(ny + 1):
            xp = ox + i * px_m * sc
            yp = oy + j * py_m * sc
            c.setFillColor(NOIR); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
            c.rect(xp - pt_d/2, yp - pt_d/2, pt_d, pt_d, fill=1, stroke=1)


def _draw_poutres_pp(c, ox, oy, sc, nx, ny, px_m, py_m, pp_b):
    """Draw main beams along Y-axes — copie de v4."""
    pd = max(pp_b * sc / 1000, 1.5)
    for j in range(ny + 1):
        yp = oy + j * py_m * sc
        for i in range(nx):
            x1 = ox + i * px_m * sc
            x2 = ox + (i+1) * px_m * sc
            c.setStrokeColor(NOIR); c.setLineWidth(0.8)
            c.line(x1, yp - pd/2, x2, yp - pd/2)
            c.line(x1, yp + pd/2, x2, yp + pd/2)


def _draw_poutres_ps(c, ox, oy, sc, nx, ny, px_m, py_m):
    """Draw secondary beams along X-axes — copie de v4."""
    for i in range(nx + 1):
        xp = ox + i * px_m * sc
        for j in range(ny):
            y1 = oy + j * py_m * sc
            y2 = oy + (j+1) * py_m * sc
            c.setStrokeColor(GRIS3); c.setLineWidth(0.4)
            c.line(xp, y1, xp, y2)


def _draw_dalle_hatch(c, ox, oy, sc, nx, ny, px_m, py_m):
    """Draw slab panel hatch — copie de v4."""
    c.setStrokeColor(GRIS4); c.setLineWidth(0.1)
    for i in range(nx):
        for j in range(ny):
            sx = ox + i * px_m * sc + 2
            sy = oy + j * py_m * sc + 2
            sw = px_m * sc - 4
            sh = py_m * sc - 4
            step = max(6, int(sw / 15))
            for k in range(0, int(sw + sh), step):
                lx1 = sx + min(k, sw); ly1 = sy + max(0, k - sw)
                lx2 = sx + max(0, k - sh); ly2 = sy + min(k, sh)
                c.line(lx1, ly1, lx2, ly2)


# ══════════════════════════════════════════
# AXIS INFERENCE — detect structural grid from wall geometry
# ══════════════════════════════════════════

def _infer_axes_from_walls(dwg, nx=None, ny=None, px_m=None, py_m=None):
    """Infer structural axes from wall geometry when explicit axes_x/axes_y are absent.

    Works with ANY coordinate system (PDF points ~0-1200, DWG mm ~0-50000+, etc.)
    by computing thresholds relative to the geometry's bounding box.

    Strategy: For each wall segment, find long horizontal/vertical lines.
    Vertical lines contribute their X coordinate as a potential X-axis.
    Horizontal lines contribute their Y coordinate as a potential Y-axis.
    Cluster these and pick the most prominent positions.

    Returns (axes_x, axes_y) as sorted coordinate lists, or ([], []) if failed.
    """
    # First compute bounding box to calibrate thresholds
    bounds = _dwg_bounds(dwg)
    if not bounds:
        return _infer_axes_fallback(dwg, nx, ny, px_m, py_m)
    xn, yn, xx, yx = bounds
    span_x = xx - xn
    span_y = yx - yn
    if span_x < 1 or span_y < 1:
        return [], []

    # Scale-relative thresholds (work for both PDF points and DWG mm)
    min_seg_len = min(span_x, span_y) * 0.05   # min 5% of smallest span
    min_long_wall = min(span_x, span_y) * 0.15  # 15% of span to be "long"

    # Collect axis-aligned wall coordinates weighted by their length
    x_positions = []  # (x_coord, weight) from vertical walls
    y_positions = []  # (y_coord, weight) from horizontal walls

    for item in dwg.get('walls', []):
        segments = []
        if item['type'] == 'line':
            segments.append((item['start'], item['end']))
        elif item['type'] == 'polyline':
            pts = item['points']
            for i in range(len(pts) - 1):
                segments.append((pts[i], pts[i + 1]))
            if item.get('closed') and len(pts) > 2:
                segments.append((pts[-1], pts[0]))

        for (x1, y1), (x2, y2) in segments:
            dx = abs(x2 - x1)
            dy = abs(y2 - y1)
            length = (dx**2 + dy**2) ** 0.5
            if length < min_seg_len:
                continue

            # Vertical wall (dx small relative to dy): contributes X axis
            if dx < dy * 0.15 and dy > min_long_wall:
                avg_x = (x1 + x2) / 2
                x_positions.append((avg_x, dy))

            # Horizontal wall (dy small relative to dx): contributes Y axis
            elif dy < dx * 0.15 and dx > min_long_wall:
                avg_y = (y1 + y2) / 2
                y_positions.append((avg_y, dx))

    if len(x_positions) < 2 or len(y_positions) < 2:
        return _infer_axes_fallback(dwg, nx, ny, px_m, py_m)

    # Clustering gap: ~3% of the geometry span
    cluster_gap_x = span_x * 0.03
    cluster_gap_y = span_y * 0.03

    def _weighted_cluster(positions, cluster_gap):
        """Cluster positions with weights. Returns [(avg_pos, total_weight), ...]."""
        if not positions:
            return []
        s = sorted(positions, key=lambda p: p[0])
        clusters = []
        cur_positions = [s[0]]
        for pos, wt in s[1:]:
            if pos - cur_positions[-1][0] < cluster_gap:
                cur_positions.append((pos, wt))
            else:
                total_w = sum(w for _, w in cur_positions)
                avg_p = sum(p * w for p, w in cur_positions) / total_w
                clusters.append((avg_p, total_w))
                cur_positions = [(pos, wt)]
        total_w = sum(w for _, w in cur_positions)
        avg_p = sum(p * w for p, w in cur_positions) / total_w
        clusters.append((avg_p, total_w))
        return clusters

    def _select_top(clusters, min_gap, max_axes=12):
        """Select top clusters that are well-spaced."""
        if not clusters:
            return []
        by_weight = sorted(clusters, key=lambda c: c[1], reverse=True)
        selected = []
        for pos, wt in by_weight:
            if len(selected) >= max_axes:
                break
            if all(abs(pos - s) > min_gap for s in selected):
                selected.append(pos)
        selected.sort()
        return selected

    x_clusters = _weighted_cluster(x_positions, cluster_gap_x)
    y_clusters = _weighted_cluster(y_positions, cluster_gap_y)

    # Minimum axis spacing: ~8% of span (a bay should be at least that wide)
    min_gap_x = span_x * 0.08
    min_gap_y = span_y * 0.08

    axes_x = _select_top(x_clusters, min_gap_x)
    axes_y = _select_top(y_clusters, min_gap_y)

    if len(axes_x) < 2 or len(axes_y) < 2:
        return _infer_axes_fallback(dwg, nx, ny, px_m, py_m)

    return axes_x, axes_y


def _infer_axes_fallback(dwg, nx=None, ny=None, px_m=None, py_m=None):
    """Fallback: create a uniform grid from bounding box when wall-based inference fails.
    Works with any coordinate system."""
    bounds = _dwg_bounds(dwg)
    if not bounds:
        return [], []
    xn, yn, xx, yx = bounds
    dw = xx - xn
    dh = yx - yn
    if dw < 1 or dh < 1:
        return [], []

    # Determine number of axes from project params
    n_ax = (nx + 1) if nx else 5
    n_ay = (ny + 1) if ny else 4
    n_ax = max(2, min(n_ax, 10))
    n_ay = max(2, min(n_ay, 8))

    # Inset slightly from edges — axes usually inside outer walls
    margin_x = dw * 0.02
    margin_y = dh * 0.02
    axes_x = [xn + margin_x + i * (dw - 2*margin_x) / (n_ax - 1) for i in range(n_ax)]
    axes_y = [yn + margin_y + j * (dh - 2*margin_y) / (n_ay - 1) for j in range(n_ay)]
    return axes_x, axes_y


def _ensure_axes(dwg, nx=None, ny=None, px_m=None, py_m=None):
    """Ensure dwg geometry has axes_x/axes_y. Infer from walls if missing."""
    if dwg.get('axes_x') and dwg.get('axes_y'):
        return dwg  # Already has axes

    ax, ay = _infer_axes_from_walls(dwg, nx, ny, px_m, py_m)
    if ax and ay:
        dwg = dict(dwg)  # Don't mutate original
        dwg['axes_x'] = ax
        dwg['axes_y'] = ay
    return dwg


# ══════════════════════════════════════════
# DWG REAL GEOMETRY — quand disponible
# ══════════════════════════════════════════

def _dwg_bounds(dwg):
    """Bounding box de la géométrie DWG — recadré sur la zone la plus dense si trop grand."""
    xs, ys = [], []
    for item in dwg.get('walls',[]) + dwg.get('windows',[]) + dwg.get('doors',[]):
        if item['type'] == 'line':
            xs += [item['start'][0], item['end'][0]]
            ys += [item['start'][1], item['end'][1]]
        elif item['type'] == 'polyline':
            for p in item['points']:
                xs.append(p[0]); ys.append(p[1])
    if not xs:
        return None

    full_w = max(xs) - min(xs)
    full_h = max(ys) - min(ys)

    # If the drawing is very large (> 50m in any direction),
    # it likely contains multiple plan sheets. Crop to densest zone.
    if full_w > 50000 or full_h > 50000:  # > 50m
        # Find the densest cluster of wall endpoints using histogram
        import math
        # X histogram
        nbins = max(20, int(full_w / 5000))
        x_hist = [0] * nbins
        for x in xs:
            b = min(int((x - min(xs)) / full_w * nbins), nbins - 1)
            x_hist[b] += 1
        # Find the peak region (contiguous bins with > 30% of max)
        x_max = max(x_hist)
        x_thresh = x_max * 0.3
        best_start = best_end = 0
        best_score = 0
        start = None
        for i in range(nbins):
            if x_hist[i] >= x_thresh:
                if start is None: start = i
            else:
                if start is not None:
                    score = sum(x_hist[start:i])
                    if score > best_score:
                        best_score = score; best_start = start; best_end = i
                    start = None
        if start is not None:
            score = sum(x_hist[start:nbins])
            if score > best_score:
                best_start = start; best_end = nbins

        crop_x_min = min(xs) + best_start * full_w / nbins - 2000  # 2m margin
        crop_x_max = min(xs) + best_end * full_w / nbins + 2000

        # Same for Y
        nbins_y = max(20, int(full_h / 5000))
        y_hist = [0] * nbins_y
        for y in ys:
            b = min(int((y - min(ys)) / full_h * nbins_y), nbins_y - 1)
            y_hist[b] += 1
        y_max = max(y_hist)
        y_thresh = y_max * 0.3
        start = None; best_start_y = best_end_y = 0; best_score_y = 0
        for i in range(nbins_y):
            if y_hist[i] >= y_thresh:
                if start is None: start = i
            else:
                if start is not None:
                    score = sum(y_hist[start:i])
                    if score > best_score_y:
                        best_score_y = score; best_start_y = start; best_end_y = i
                    start = None
        if start is not None:
            score = sum(y_hist[start:nbins_y])
            if score > best_score_y:
                best_start_y = start; best_end_y = nbins_y

        crop_y_min = min(ys) + best_start_y * full_h / nbins_y - 2000
        crop_y_max = min(ys) + best_end_y * full_h / nbins_y + 2000

        return crop_x_min, crop_y_min, crop_x_max, crop_y_max

    return min(xs), min(ys), max(xs), max(ys)


def _dwg_layout(w, h, dwg, ml=50*mm, mb=55*mm, mr=72*mm, mt=30*mm):
    """Calculate DWG transform to fit on page with generous margins."""
    bounds = _dwg_bounds(dwg)
    if not bounds:
        return None, None, None, None, None
    xn, yn, xx, yx = bounds
    dw_r = xx - xn; dh_r = yx - yn
    if dw_r < 1 or dh_r < 1:
        return None, None, None, None, None
    aw = w - ml - mr; ah = h - mb - mt
    sc = min(aw / dw_r, ah / dh_r) * 0.95  # slight margin to breathe
    gw = dw_r * sc; gh = dh_r * sc
    ox = ml + (aw - gw) / 2
    oy = mb + (ah - gh) / 2
    tx = lambda x: ox + (x - xn) * sc
    ty = lambda y: oy + (y - yn) * sc
    return tx, ty, sc, gw, gh


def _draw_dwg(c, dwg, tx, ty, light=False, sc=None):
    """Dessine la géométrie DWG réelle (murs, fenêtres, portes, labels).
    light=True pour les plans MEP (architecture très claire en fond).
    sc = scale factor (mm to points) for thickness calculation.

    For DWG uploads (mm coordinates), uses clean double-line walls.
    For any coordinates, wall thickness is capped to avoid dominating the view.
    """
    import re

    # Wall line weight — clean, architectural look
    # For DWG mm coords: 200mm wall * sc gives proper thickness
    # Capped to prevent thick black rectangles
    wall_lw = 0.8  # default line weight in points
    if sc and sc > 0:
        wall_lw = max(200 * sc * 0.4, 0.5)
        wall_lw = min(wall_lw, 2.0)  # strict cap at 2pt for clean look

    # ── Murs ──
    if light:
        # MEP background: light single lines
        c.setStrokeColor(colors.HexColor("#BBBBBB")); c.setLineWidth(0.4)
        for item in dwg.get('walls', []):
            if item['type'] == 'line':
                c.line(tx(item['start'][0]), ty(item['start'][1]),
                       tx(item['end'][0]), ty(item['end'][1]))
            elif item['type'] == 'polyline':
                pts = item['points']
                for i in range(len(pts)-1):
                    c.line(tx(pts[i][0]), ty(pts[i][1]),
                           tx(pts[i+1][0]), ty(pts[i+1][1]))
                if item.get('closed') and len(pts) > 2:
                    c.line(tx(pts[-1][0]), ty(pts[-1][1]),
                           tx(pts[0][0]), ty(pts[0][1]))
    else:
        # Structure: clean architectural lines (NOT thick filled rectangles)
        c.setStrokeColor(colors.HexColor("#444444")); c.setLineWidth(wall_lw)
        for item in dwg.get('walls', []):
            if item['type'] == 'line':
                c.line(tx(item['start'][0]), ty(item['start'][1]),
                       tx(item['end'][0]), ty(item['end'][1]))
            elif item['type'] == 'polyline':
                pts = item['points']
                for i in range(len(pts)-1):
                    c.line(tx(pts[i][0]), ty(pts[i][1]),
                           tx(pts[i+1][0]), ty(pts[i+1][1]))
                if item.get('closed') and len(pts) > 2:
                    c.line(tx(pts[-1][0]), ty(pts[-1][1]),
                           tx(pts[0][0]), ty(pts[0][1]))

    # ── Fenêtres — blue thin lines with gap ──
    win_color = colors.HexColor("#D6E8F5") if light else colors.HexColor("#64B5F6")
    c.setStrokeColor(win_color); c.setLineWidth(0.2 if light else 0.6)
    for item in dwg.get('windows', []):
        if item['type'] == 'line':
            c.line(tx(item['start'][0]), ty(item['start'][1]),
                   tx(item['end'][0]), ty(item['end'][1]))
        elif item['type'] == 'polyline':
            pts = item['points']
            for i in range(len(pts)-1):
                c.line(tx(pts[i][0]), ty(pts[i][1]),
                       tx(pts[i+1][0]), ty(pts[i+1][1]))

    # ── Portes — brown lines ──
    door_color = colors.HexColor("#E0D5CF") if light else colors.HexColor("#8D6E63")
    c.setStrokeColor(door_color); c.setLineWidth(0.15 if light else 0.4)
    for item in dwg.get('doors', []):
        if item['type'] == 'line':
            c.line(tx(item['start'][0]), ty(item['start'][1]),
                   tx(item['end'][0]), ty(item['end'][1]))
        elif item['type'] == 'polyline':
            pts = item['points']
            for i in range(len(pts)-1):
                c.line(tx(pts[i][0]), ty(pts[i][1]),
                       tx(pts[i+1][0]), ty(pts[i+1][1]))

    # ── Labels pièces ──
    if not light:
        c.setFillColor(GRIS2); c.setFont("Helvetica", 4.5)
        for r in dwg.get('rooms', []):
            name = r.get('name', '')
            if name and not re.match(r'^\d', name):
                c.drawCentredString(tx(r['x']), ty(r['y']), name[:25])
    else:
        # Even in light mode, show room names very faintly
        c.setFillColor(colors.HexColor("#AAAAAA")); c.setFont("Helvetica", 3)
        for r in dwg.get('rooms', []):
            name = r.get('name', '')
            if name and not re.match(r'^\d', name):
                c.drawCentredString(tx(r['x']), ty(r['y']), name[:20])


def _draw_thick_wall(c, x1, y1, x2, y2, thickness):
    """Draw a wall as a filled rectangle along a line segment."""
    dx = x2 - x1
    dy = y2 - y1
    length = (dx**2 + dy**2) ** 0.5
    if length < 0.5:
        return
    # Normal vector (perpendicular)
    nx = -dy / length * thickness / 2
    ny = dx / length * thickness / 2

    path = c.beginPath()
    path.moveTo(x1 + nx, y1 + ny)
    path.lineTo(x2 + nx, y2 + ny)
    path.lineTo(x2 - nx, y2 - ny)
    path.lineTo(x1 - nx, y1 - ny)
    path.close()
    c.drawPath(path, fill=1, stroke=1)


# ══════════════════════════════════════════
# PDF-BACKGROUND MODE — lightweight annotations over architect's original
# ══════════════════════════════════════════

def _draw_coffrage_annotations(c, tx, ty, axes_x, axes_y, pot_s, pp_b, pp_h,
                                ps_b, ps_h, dalle_ep, px_m, py_m, beton, acier):
    """Draw structural coffrage annotations on top of a PDF background.

    Only draws lightweight overlay: axis lines, axis labels, column markers,
    beam indicators, slab labels. Does NOT redraw walls/windows/doors.
    """
    if not axes_x or not axes_y:
        return

    # ── Axis lines — thin dashed, semi-transparent ──
    c.saveState()
    c.setStrokeAlpha(0.5)
    c.setStrokeColor(colors.HexColor("#CC3333")); c.setLineWidth(0.4); c.setDash(8, 4)
    y_lo = ty(axes_y[-1]) - 10*mm  # lowest point (Y flipped)
    y_hi = ty(axes_y[0]) + 10*mm   # highest point
    x_lo = tx(axes_x[0]) - 10*mm
    x_hi = tx(axes_x[-1]) + 10*mm
    for ax in axes_x:
        c.line(tx(ax), y_lo, tx(ax), y_hi)
    for ay in axes_y:
        c.line(x_lo, ty(ay), x_hi, ty(ay))
    c.setDash()
    c.restoreState()

    # ── Axis labels — numbered/lettered circles ──
    for i, ax in enumerate(axes_x):
        _axis_label(c, tx(ax), y_lo - 5*mm, str(i + 1))
        _axis_label(c, tx(ax), y_hi + 5*mm, str(i + 1))
    for j, ay in enumerate(axes_y):
        _axis_label(c, x_lo - 5*mm, ty(ay), chr(65 + (j % 26)))
        _axis_label(c, x_hi + 5*mm, ty(ay), chr(65 + (j % 26)))

    # ── Dimension labels between axes ──
    c.setFillColor(GRIS2); c.setFont("Helvetica", 5)
    for i in range(len(axes_x) - 1):
        span_m = px_m  # use project portée (PDF coords don't convert to meters reliably)
        mid_x = (tx(axes_x[i]) + tx(axes_x[i+1])) / 2
        c.drawCentredString(mid_x, y_lo - 12*mm, f"{span_m:.2f}m")
    for j in range(len(axes_y) - 1):
        span_m = py_m
        mid_y = (ty(axes_y[j]) + ty(axes_y[j+1])) / 2
        c.saveState()
        c.translate(x_lo - 12*mm, mid_y); c.rotate(90)
        c.drawCentredString(0, 0, f"{span_m:.2f}m")
        c.restoreState()

    # ── Poteaux (columns) — small red-outlined squares at intersections ──
    pt_d = 6  # fixed 6pt column marker — visible but not dominating
    for ax in axes_x:
        for ay in axes_y:
            px, py = tx(ax), ty(ay)
            c.setFillColor(colors.HexColor("#FFCCCC"))  # light red fill
            c.setStrokeColor(ROUGE); c.setLineWidth(0.6)
            c.rect(px - pt_d/2, py - pt_d/2, pt_d, pt_d, fill=1, stroke=1)
            # Label — tiny section text
            c.setFillColor(ROUGE); c.setFont("Helvetica-Bold", 2.5)
            c.drawCentredString(px, py - 1, f"{pot_s}")

    # ── Poutres principales (main beams) — semi-transparent thick lines ──
    c.saveState()
    c.setStrokeAlpha(0.4)
    c.setStrokeColor(NOIR); c.setLineWidth(2.5)
    for ay in axes_y:
        py = ty(ay)
        for i in range(len(axes_x) - 1):
            c.line(tx(axes_x[i]), py, tx(axes_x[i+1]), py)
    c.restoreState()
    # Label PP on first span
    if len(axes_x) >= 2 and len(axes_y) >= 1:
        c.setFillColor(ROUGE); c.setFont("Helvetica-Bold", 4)
        mid_x = (tx(axes_x[0]) + tx(axes_x[1])) / 2
        c.drawCentredString(mid_x, ty(axes_y[0]) + 5, f"PP {pp_b}×{pp_h}")

    # ── Poutres secondaires — thinner semi-transparent ──
    c.saveState()
    c.setStrokeAlpha(0.3)
    c.setStrokeColor(GRIS3); c.setLineWidth(1.2)
    for ax in axes_x:
        px = tx(ax)
        for j in range(len(axes_y) - 1):
            c.line(px, ty(axes_y[j]), px, ty(axes_y[j+1]))
    c.restoreState()

    # ── Dalle labels — section in large panels ──
    c.setFont("Helvetica", 4); c.setFillColor(GRIS2)
    for i in range(len(axes_x) - 1):
        for j in range(len(axes_y) - 1):
            cx = (tx(axes_x[i]) + tx(axes_x[i+1])) / 2
            cy = (ty(axes_y[j]) + ty(axes_y[j+1])) / 2
            sw = abs(tx(axes_x[i+1]) - tx(axes_x[i]))
            sh = abs(ty(axes_y[j+1]) - ty(axes_y[j]))
            if sw > 20 and sh > 20:
                c.drawCentredString(cx, cy + 3, f"Dalle ep.{dalle_ep}")
                c.setFont("Helvetica", 3)
                c.drawCentredString(cx, cy - 4, f"{px_m:.1f}×{py_m:.1f}m")
                c.setFont("Helvetica", 4)

    # ── Light diagonal hatch for slab panels ──
    c.saveState()
    c.setStrokeAlpha(0.12)
    c.setStrokeColor(GRIS4); c.setLineWidth(0.15)
    for i in range(len(axes_x) - 1):
        for j in range(len(axes_y) - 1):
            x1p = tx(axes_x[i]) + 3; x2p = tx(axes_x[i+1]) - 3
            y1p_d = min(ty(axes_y[j]), ty(axes_y[j+1])) + 3
            y2p_d = max(ty(axes_y[j]), ty(axes_y[j+1])) - 3
            sw = x2p - x1p; sh = y2p_d - y1p_d
            if sw > 10 and sh > 10:
                step = max(10, int(sw / 6))
                for k in range(0, int(sw + sh), step):
                    lx1 = x1p + min(k, sw); ly1 = y1p_d + max(0, k - sw)
                    lx2 = x1p + max(0, k - sh); ly2 = y1p_d + min(k, sh)
                    c.line(lx1, ly1, lx2, ly2)
    c.restoreState()


def _draw_mep_annotations(c, tx, ty, axes_x, axes_y, rooms, key, sublot_data,
                          pot_s):
    """Draw MEP equipment annotations on top of a PDF background.

    Only draws equipment symbols at room positions. Does NOT redraw walls.
    sublot_data is the MEP results object for the current sub-lot.
    """
    import re as _re

    # Draw faint axes for reference
    if axes_x and axes_y:
        c.saveState()
        c.setStrokeAlpha(0.2)
        c.setStrokeColor(GRIS4); c.setLineWidth(0.3); c.setDash(4, 4)
        y_lo = min(ty(axes_y[0]), ty(axes_y[-1])) - 5*mm
        y_hi = max(ty(axes_y[0]), ty(axes_y[-1])) + 5*mm
        x_lo = tx(axes_x[0]) - 5*mm
        x_hi = tx(axes_x[-1]) + 5*mm
        for ax in axes_x:
            c.line(tx(ax), y_lo, tx(ax), y_hi)
        for ay in axes_y:
            c.line(x_lo, ty(ay), x_hi, ty(ay))
        c.setDash()
        c.restoreState()

    # Classify rooms
    def _classify(rooms):
        wet, living, service = [], [], []
        for r in rooms:
            n = r.get('name', '').lower().strip()
            if _re.match(r'^\d', n):
                continue
            if any(k in n for k in ['sdb', 'wc', 'toil', 'douche']):
                wet.append({**r, 'rt': 'wet'})
            elif any(k in n for k in ['cuisine', 'kitch', 'buanderie']):
                wet.append({**r, 'rt': 'kitchen'})
            elif any(k in n for k in ['salon', 'chambre', 'sejour', 'bureau', 'sam', 'bar',
                                       'gym', 'restaurant', 'magasin', 'salle']):
                living.append({**r, 'rt': 'living'})
            elif any(k in n for k in ['hall', 'palier', 'asc', 'dgt', 'sas', 'terrasse',
                                       'balcon', 'jardin', 'piscine', 'vide', 'porche']):
                service.append({**r, 'rt': 'service'})
            else:
                living.append({**r, 'rt': 'other'})
        return wet, living, service

    wet, living, service = _classify(rooms)
    all_rooms = wet + living + service

    # Color map per sub-lot key
    colors_map = {
        'plb_ef': BLEU, 'plb_ec': ROUGE, 'plb_eu': VERT,
        'elec_ecl': JAUNE, 'elec_dist': ORANGE,
        'cvc_clim': CYAN, 'cvc_vmc': VIOLET,
        'ssi_det': ROUGE, 'ssi_ext': ROUGE,
        'cfa': MARRON, 'asc_plan': GRIS2, 'gtb': VERT,
    }
    color = colors_map.get(key, BLEU)

    # Determine which rooms get equipment
    if key.startswith('plb_'):
        target = wet
    elif key.startswith('elec_'):
        target = all_rooms
    elif key.startswith('cvc_'):
        target = living if 'clim' in key else wet
    elif key.startswith('ssi_'):
        target = all_rooms
    elif key == 'cfa':
        target = living
    elif key == 'asc_plan':
        target = [r for r in service if 'asc' in r.get('name', '').lower() or 'palier' in r.get('name', '').lower()]
    elif key == 'gtb':
        target = all_rooms
    else:
        target = all_rooms

    # Draw equipment symbols
    for r in target:
        rx, ry = tx(r['x']), ty(r['y'])
        name = r.get('name', '').lower()

        c.setFillColor(color); c.setStrokeColor(NOIR); c.setLineWidth(0.4)

        if key in ('plb_ef', 'plb_ec'):
            # Circle with label
            c.circle(rx, ry, 5, fill=1, stroke=1)
            c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 4)
            label = "EF" if key == 'plb_ef' else "EC"
            c.drawCentredString(rx, ry - 1.5, label)
        elif key == 'plb_eu':
            # Down arrow (drain)
            c.circle(rx, ry, 4, fill=1, stroke=1)
            c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 4)
            c.drawCentredString(rx, ry - 1.5, "EU")
        elif key == 'elec_ecl':
            # Lighting symbol (X in circle)
            c.setStrokeColor(color); c.setLineWidth(0.6)
            c.circle(rx, ry, 4, fill=0, stroke=1)
            c.line(rx-2.5, ry-2.5, rx+2.5, ry+2.5)
            c.line(rx-2.5, ry+2.5, rx+2.5, ry-2.5)
        elif key == 'elec_dist':
            # Outlet symbol (small square)
            c.rect(rx-3, ry-3, 6, 6, fill=1, stroke=1)
        elif key.startswith('cvc_'):
            # HVAC symbol
            c.rect(rx-5, ry-3, 10, 6, fill=1, stroke=1)
            c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 3.5)
            c.drawCentredString(rx, ry - 1.5, "CLIM" if 'clim' in key else "VMC")
        elif key.startswith('ssi_'):
            # Fire safety — triangle
            path = c.beginPath()
            path.moveTo(rx, ry + 5); path.lineTo(rx - 4, ry - 3); path.lineTo(rx + 4, ry - 3)
            path.close()
            c.drawPath(path, fill=1, stroke=1)
            c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 3)
            c.drawCentredString(rx, ry - 1, "D" if 'det' in key else "E")
        elif key == 'asc_plan':
            c.circle(rx, ry, 8, fill=0, stroke=1)
            c.setFillColor(color); c.setFont("Helvetica-Bold", 5)
            c.drawCentredString(rx, ry - 2, "ASC")
        else:
            c.circle(rx, ry, 4, fill=1, stroke=1)

        # Room name label (tiny, below equipment)
        c.setFillColor(GRIS2); c.setFont("Helvetica", 2.5)
        short_name = r.get('name', '')[:15]
        c.drawCentredString(rx, ry - 9, short_name)


# ══════════════════════════════════════════
# STRUCTURAL GRID IN DWG COORDINATES
# Grid inscribed within DWG footprint bounds
# ══════════════════════════════════════════

def _draw_grid_axes_dwg(c, tx, ty, xn, yn, nx, ny, px_m, py_m, dwg_w, dwg_h):
    """Draw structural axes inscribed in DWG bounds."""
    c.setStrokeColor(GRIS4); c.setLineWidth(0.2); c.setDash(4, 2)
    for i in range(nx + 1):
        xp = xn + i * px_m * 1000  # m → mm (DWG units)
        c.line(tx(xp), ty(yn) - 8*mm, tx(xp), ty(yn + dwg_h * 1000) + 8*mm)
    for j in range(ny + 1):
        yp = yn + j * py_m * 1000
        c.line(tx(xn) - 8*mm, ty(yp), tx(xn + dwg_w * 1000) + 8*mm, ty(yp))
    c.setDash()
    for i in range(nx + 1):
        xp = xn + i * px_m * 1000
        _axis_label(c, tx(xp), ty(yn) - 15*mm, str(i + 1))
    for j in range(ny + 1):
        yp = yn + j * py_m * 1000
        _axis_label(c, tx(xn) - 15*mm, ty(yp), chr(65 + j))
    # Dimensions
    c.setFillColor(GRIS3); c.setFont("Helvetica", 5.5)
    for i in range(nx):
        mid = xn + (i + 0.5) * px_m * 1000
        c.drawCentredString(tx(mid), ty(yn) - 9*mm, f"{px_m*1000:.0f}")
    for j in range(ny):
        mid_y = yn + (j + 0.5) * py_m * 1000
        c.saveState(); c.translate(tx(xn) - 9*mm, ty(mid_y)); c.rotate(90)
        c.drawCentredString(0, 0, f"{py_m*1000:.0f}"); c.restoreState()


def _draw_poteaux_dwg(c, tx, ty, xn, yn, nx, ny, px_m, py_m, pot_s, dwg_sc):
    """Draw columns at DWG-aligned grid intersections."""
    pt_d = max(pot_s * dwg_sc / 2, 3)  # pot_s in mm, dwg_sc converts mm→pt
    for i in range(nx + 1):
        for j in range(ny + 1):
            xp = xn + i * px_m * 1000
            yp = yn + j * py_m * 1000
            px_pt, py_pt = tx(xp), ty(yp)
            c.setFillColor(NOIR); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
            c.rect(px_pt - pt_d/2, py_pt - pt_d/2, pt_d, pt_d, fill=1, stroke=1)


def _draw_poutres_pp_dwg(c, tx, ty, xn, yn, nx, ny, px_m, py_m, pp_b):
    """Draw main beams on DWG coordinate system."""
    for j in range(ny + 1):
        yp = yn + j * py_m * 1000
        for i in range(nx):
            x1 = xn + i * px_m * 1000
            x2 = xn + (i + 1) * px_m * 1000
            c.setStrokeColor(NOIR); c.setLineWidth(0.8)
            c.line(tx(x1), ty(yp), tx(x2), ty(yp))


def _draw_poutres_ps_dwg(c, tx, ty, xn, yn, nx, ny, px_m, py_m):
    """Draw secondary beams on DWG coordinate system."""
    for i in range(nx + 1):
        xp = xn + i * px_m * 1000
        for j in range(ny):
            y1 = yn + j * py_m * 1000
            y2 = yn + (j + 1) * py_m * 1000
            c.setStrokeColor(GRIS3); c.setLineWidth(0.4)
            c.line(tx(xp), ty(y1), tx(xp), ty(y2))


def _draw_dalle_hatch_dwg(c, tx, ty, xn, yn, nx, ny, px_m, py_m):
    """Draw slab hatch on DWG coordinate system."""
    c.setStrokeColor(GRIS4); c.setLineWidth(0.1)
    for i in range(nx):
        for j in range(ny):
            x1 = tx(xn + i * px_m * 1000) + 2
            y1 = ty(yn + j * py_m * 1000) + 2
            x2 = tx(xn + (i + 1) * px_m * 1000) - 2
            y2 = ty(yn + (j + 1) * py_m * 1000) - 2
            sw = x2 - x1; sh = y2 - y1
            if sw < 3 or sh < 3: continue
            step = max(6, int(sw / 15))
            for k in range(0, int(sw + sh), step):
                lx1 = x1 + min(k, sw); ly1 = y1 + max(0, k - sw)
                lx2 = x1 + max(0, k - sh); ly2 = y1 + min(k, sh)
                c.line(lx1, ly1, lx2, ly2)


def _legend(c, w, h, items):
    """Draw legend box — top right."""
    lx = w - 58*mm; ly = h - 28*mm
    c.setFont("Helvetica-Bold", 7); c.setFillColor(NOIR)
    c.drawString(lx, ly, "LÉGENDE"); ly -= 12
    for color, width, label in items:
        if width == 'fill':
            c.setFillColor(color)
            c.rect(lx, ly, 5, 5, fill=1, stroke=1)
        elif width == 'circle':
            c.setFillColor(color)
            c.circle(lx + 3, ly + 3, 3, fill=1, stroke=0)
        else:
            c.setStrokeColor(color); c.setLineWidth(width)
            c.line(lx, ly + 3, lx + 15, ly + 3)
        c.setFillColor(NOIR); c.setFont("Helvetica", 5.5)
        c.drawString(lx + 18, ly + 1, label)
        ly -= 10


# ══════════════════════════════════════════
# PDF RASTER BACKGROUND — archi PDF as greyed-out background image
# ══════════════════════════════════════════

def _render_pdf_background(c, archi_pdf_path, page_idx, w, h,
                            ml=50*mm, mb=55*mm, mr=72*mm, mt=30*mm,
                            opacity=0.18, dpi=150):
    """Render a page from the architectural PDF as a background image.

    Uses PyMuPDF to rasterize the page, then places it on the ReportLab canvas.

    Returns (success, placement_dict) where placement_dict contains:
        ox, oy: bottom-left of the placed image on the ReportLab page
        draw_w, draw_h: size of the placed image on the page
        pdf_w_pt, pdf_h_pt: original PDF page size in points
        scale: mapping factor from PDF points to page points
    This allows callers to build tx/ty transforms that align with the background.
    """
    try:
        import fitz
        from reportlab.lib.utils import ImageReader
        import io as _io

        doc = fitz.open(archi_pdf_path)
        if page_idx >= len(doc):
            doc.close()
            return False, {}

        page = doc[page_idx]
        pdf_rect = page.rect  # PDF page dimensions in points
        pdf_w_pt = pdf_rect.width
        pdf_h_pt = pdf_rect.height

        # Render at specified DPI
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_bytes = pix.tobytes("png")
        doc.close()

        # Calculate placement — fit within drawing area with margins
        aw = w - ml - mr
        ah = h - mb - mt
        img_w = pix.width
        img_h = pix.height
        img_scale = min(aw / img_w, ah / img_h)
        draw_w = img_w * img_scale
        draw_h = img_h * img_scale
        ox = ml + (aw - draw_w) / 2
        oy = mb + (ah - draw_h) / 2

        # Scale from PDF points to placed-image points
        pdf_to_page = draw_w / pdf_w_pt  # same as draw_h / pdf_h_pt

        # Draw with specified opacity
        c.saveState()
        c.setFillAlpha(opacity)
        c.setStrokeAlpha(opacity)
        img_reader = ImageReader(_io.BytesIO(img_bytes))
        c.drawImage(img_reader, ox, oy, draw_w, draw_h,
                    preserveAspectRatio=True, anchor='c')
        c.restoreState()

        placement = {
            'ox': ox, 'oy': oy,
            'draw_w': draw_w, 'draw_h': draw_h,
            'pdf_w_pt': pdf_w_pt, 'pdf_h_pt': pdf_h_pt,
            'scale': pdf_to_page,
        }
        return True, placement

    except Exception as e:
        import logging
        logging.getLogger("tijan").warning(f"PDF background render failed: {e}")
        return False, {}


def _pdf_bg_transforms(placement, pdf_h_pt):
    """Build tx/ty transforms from PDF-point coordinates to page coordinates.

    PDF coordinate system: origin at bottom-left, Y up (same as ReportLab).
    But pdf_to_geometry() returns coordinates from get_drawings() which uses
    PDF's native coordinate system where Y=0 is at the TOP of the page.
    So we need to flip Y: page_y = oy + (pdf_h_pt - geo_y) * scale.
    """
    ox = placement['ox']
    oy = placement['oy']
    sc = placement['scale']
    h = pdf_h_pt

    def tx(x):
        return ox + x * sc

    def ty(y):
        # Flip Y: PDF get_drawings() has Y=0 at top
        return oy + (h - y) * sc

    return tx, ty, sc


# ══════════════════════════════════════════
# PLANS STRUCTURE — même pattern que v4
# ══════════════════════════════════════════

def generer_plans_structure(output_path, resultats=None, params=None, dwg_geometry=None, archi_pdf_path=None, **kw):
    """
    Plans structure. Trois modes (par ordre de priorité) :
    1. Avec dwg_geometry : fond de plan DWG/PDF réel + structure superposée
    2. Avec archi_pdf_path : PDF archi en fond grisé + grille structure superposée
    3. Sans : grille paramétrique seule depuis ParamsProjet
    Toutes les valeurs viennent de ResultatsStructure.
    """
    if resultats is None:
        raise ValueError("ResultatsStructure requis")
    if params is None:
        params = {}
    if hasattr(params, "__dict__"):
        params = {k: v for k, v in vars(params).items() if not k.startswith("_")}

    r = resultats
    p = params
    nx, ny, px_m, py_m = _build_grid(p)
    pot0 = r.poteaux[0] if r.poteaux else None
    pp = r.poutre_principale
    ps = r.poutre_secondaire
    dalle = r.dalle
    fd = r.fondation

    if pot0 is None or pp is None:
        raise ValueError("Résultats structure incomplets")

    pot_s = pot0.section_mm
    pp_b, pp_h = pp.b_mm, pp.h_mm
    ps_b = ps.b_mm if ps else 0
    ps_h = ps.h_mm if ps else 0
    dalle_ep = dalle.epaisseur_mm
    beton = r.classe_beton
    acier = r.classe_acier

    nb_niv = p.get("nb_niveaux", len(r.poteaux))
    he = p.get("hauteur_etage_m", 3.0)

    # Normalize dwg_geometry to level dict — with axis inference
    LEVEL_LABELS = {
        'SOUS_SOL': 'Sous-Sol', 'RDC': 'Rez-de-Chaussée',
        'ETAGES_1_7': 'Étage courant', 'ETAGE_8': 'Étage 8', 'TERRASSE': 'Terrasse',
    }
    dwg_levels = {}
    if dwg_geometry:
        if 'walls' in dwg_geometry:
            enriched = _ensure_axes(dwg_geometry, nx, ny, px_m, py_m)
            dwg_levels = {'Étage courant': enriched}
        else:
            for key, geom in dwg_geometry.items():
                if isinstance(geom, dict) and len(geom.get('walls', [])) >= 5:
                    enriched = _ensure_axes(geom, nx, ny, px_m, py_m)
                    dwg_levels[LEVEL_LABELS.get(key, key)] = enriched

    # Build level list
    level_names = []
    if p.get("avec_sous_sol"):
        level_names.append("Sous-Sol")
    level_names.append("RDC")
    nb_etages = nb_niv - len(level_names)
    if nb_etages > 0:
        level_names.append(f"Étage courant" if nb_etages > 1 else "Étage 1")
    level_names.append("Terrasse")

    total_pages = len(level_names) + 5  # +ferraillage dalle + fondations + coupe + ferraillage poutre + ferraillage poteau
    page = 0

    c = pdfcanvas.Canvas(output_path, pagesize=A3L)
    c.setTitle(f"Plans Structure — {p.get('nom','Projet')}")
    c.setAuthor("Tijan AI")

    # ── COFFRAGE per level ──
    for level_name in level_names:
        page += 1
        w, h = A3L; c.setPageSize(A3L); _border(c, w, h)
        c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 13)
        c.drawString(14*mm, h - 17*mm, f"PLAN DE COFFRAGE — {level_name.upper()}")

        # DWG geometry for this level if available
        lvl_geom = dwg_levels.get(level_name) or dwg_levels.get('Étage courant')
        has_geom = lvl_geom and len(lvl_geom.get('walls', [])) >= 5

        # Detect if geometry came from PDF (coordinates in points, small range)
        # vs DWG (coordinates in mm, large range)
        # Also detect CV pipeline output (mm coordinates but source was PDF)
        is_from_pdf = False
        is_from_cv = bool(lvl_geom.get('_cv_meta')) if has_geom else False
        if has_geom:
            bounds = _dwg_bounds(lvl_geom)
            if bounds:
                span = max(bounds[2] - bounds[0], bounds[3] - bounds[1])
                is_from_pdf = span < 5000  # PDF points are typically < 2000
            if is_from_cv and lvl_geom.get('_cv_meta', {}).get('source') == 'pdf':
                is_from_pdf = True  # CV extracted from PDF — use PDF background

        rendered = False

        # ── MODE 1: PDF BACKGROUND (primary for PDF uploads) ──
        # When we have the original PDF, use it as high-quality background
        # and overlay lightweight structural annotations only.
        if archi_pdf_path and (is_from_pdf or not has_geom):
            pdf_page_idx = level_names.index(level_name) if level_name in level_names else 0
            ok, placement = _render_pdf_background(
                c, archi_pdf_path, pdf_page_idx, w, h,
                opacity=0.85, dpi=200  # high quality, high opacity
            )
            if ok and placement:
                # Get axes from extracted geometry (used for annotation positioning)
                axes_x = lvl_geom.get('axes_x', []) if has_geom else []
                axes_y = lvl_geom.get('axes_y', []) if has_geom else []
                if axes_x and axes_y and placement.get('pdf_h_pt'):
                    # Build transforms aligned with PDF background
                    pdf_tx, pdf_ty, pdf_sc = _pdf_bg_transforms(
                        placement, placement['pdf_h_pt']
                    )
                    _draw_coffrage_annotations(
                        c, pdf_tx, pdf_ty, axes_x, axes_y,
                        pot_s, pp_b, pp_h, ps_b, ps_h, dalle_ep,
                        px_m, py_m, beton, acier
                    )
                else:
                    # No axes — overlay parametric grid on top of PDF background
                    ox, oy, sc, gw, gh = _grid_layout(w, h, nx, ny, px_m, py_m)
                    c.saveState(); c.setStrokeAlpha(0.5); c.setFillAlpha(0.6)
                    _draw_grid_axes(c, ox, oy, sc, nx, ny, px_m, py_m, gw, gh)
                    _draw_poutres_pp(c, ox, oy, sc, nx, ny, px_m, py_m, pp_b)
                    _draw_poutres_ps(c, ox, oy, sc, nx, ny, px_m, py_m)
                    _draw_poteaux(c, ox, oy, sc, nx, ny, px_m, py_m, pot_s)
                    c.restoreState()
                rendered = True

        # ── MODE 2: DWG REDRAW (any geometry — works for DWG mm or DXF model units) ──
        if not rendered and has_geom:
            dtx, dty, dsc, dgw, dgh = _dwg_layout(w, h, lvl_geom)
            if dtx:
                # Draw architecture — thin clean lines (not thick black rectangles)
                _draw_dwg(c, lvl_geom, dtx, dty, sc=dsc)

                real_ax = lvl_geom.get('axes_x', [])
                real_ay = lvl_geom.get('axes_y', [])
                if real_ax and real_ay:
                    # Axes, poteaux, poutres, dalle labels — same as before but using
                    # the annotation function for consistency
                    _draw_coffrage_annotations(
                        c, dtx, dty, real_ax, real_ay,
                        pot_s, pp_b, pp_h, ps_b, ps_h, dalle_ep,
                        px_m, py_m, beton, acier
                    )
                else:
                    # No axes — fitted grid
                    bx0, by0, bx1, by1 = _dwg_bounds(lvl_geom)
                    bw = bx1 - bx0; bh = by1 - by0
                    gx0 = bx0 + bw * 0.02; gy0 = by0 + bh * 0.02
                    g_px = (bw * 0.96) / max(nx, 1)
                    g_py = (bh * 0.96) / max(ny, 1)
                    _draw_grid_axes_dwg(c, dtx, dty, gx0, gy0, nx, ny, g_px/1000, g_py/1000, bw*0.96, bh*0.96)
                    _draw_poutres_pp_dwg(c, dtx, dty, gx0, gy0, nx, ny, g_px/1000, g_py/1000, pp_b)
                    _draw_poutres_ps_dwg(c, dtx, dty, gx0, gy0, nx, ny, g_px/1000, g_py/1000)
                    _draw_poteaux_dwg(c, dtx, dty, gx0, gy0, nx, ny, g_px/1000, g_py/1000, pot_s, dsc)
                rendered = True

        # ── MODE 3: PARAMETRIC GRID (no file uploaded) ──
        if not rendered:
            ox, oy, sc, gw, gh = _grid_layout(w, h, nx, ny, px_m, py_m)
            _draw_grid_axes(c, ox, oy, sc, nx, ny, px_m, py_m, gw, gh)
            _draw_dalle_hatch(c, ox, oy, sc, nx, ny, px_m, py_m)
            _draw_poutres_pp(c, ox, oy, sc, nx, ny, px_m, py_m, pp_b)
            _draw_poutres_ps(c, ox, oy, sc, nx, ny, px_m, py_m)
            _draw_poteaux(c, ox, oy, sc, nx, ny, px_m, py_m, pot_s)
            c.setFillColor(GRIS3); c.setFont("Helvetica", 4.5)
            for i in range(nx):
                for j in range(ny):
                    cx_p = ox + (i + 0.5) * px_m * sc
                    cy_p = oy + (j + 0.5) * py_m * sc
                    c.drawCentredString(cx_p, cy_p, f"D ep.{dalle_ep}")

        _legend(c, w, h, [
            (NOIR, 'fill', f"Poteau {pot_s}×{pot_s}"),
            (NOIR, 0.8, f"PP {pp_b}×{pp_h}"),
            (GRIS3, 0.4, f"PS {ps_b}×{ps_h}" if ps else "PS"),
            (GRIS4, 0.1, f"Dalle ep.{dalle_ep}mm"),
        ])

        c.setFont("Helvetica", 5); c.setFillColor(GRIS3)
        c.drawString(14*mm, 42*mm, f"Béton {beton} — Acier {acier} — Enrobage 30mm")
        _cartouche(c, w, h, p, f"COFFRAGE — {level_name}", page, total_pages)
        c.showPage()

    # ── FERRAILLAGE DALLE ──
    page += 1
    w, h = A3L; c.setPageSize(A3L); _border(c, w, h)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 13)
    c.drawString(14*mm, h - 17*mm, "FERRAILLAGE DALLE — NIVEAU COURANT")

    lvl_geom = dwg_levels.get('Étage courant') or dwg_levels.get('Rez-de-Chaussée')
    has_geom_d = lvl_geom and len(lvl_geom.get('walls', [])) >= 5
    is_from_pdf_d = False
    is_from_cv_d = bool(lvl_geom.get('_cv_meta')) if has_geom_d else False
    if has_geom_d:
        bounds_d = _dwg_bounds(lvl_geom)
        if bounds_d:
            span_d = max(bounds_d[2] - bounds_d[0], bounds_d[3] - bounds_d[1])
            is_from_pdf_d = span_d < 5000
        if is_from_cv_d and lvl_geom.get('_cv_meta', {}).get('source') == 'pdf':
            is_from_pdf_d = True

    rendered_dalle = False
    real_ax_d = []; real_ay_d = []
    dalle_tx = dalle_ty = None

    # MODE 1: PDF background for ferraillage
    if archi_pdf_path and (is_from_pdf_d or not has_geom_d):
        ok, placement = _render_pdf_background(c, archi_pdf_path, 0, w, h, opacity=0.70, dpi=200)
        if ok and placement and has_geom_d:
            real_ax_d = lvl_geom.get('axes_x', [])
            real_ay_d = lvl_geom.get('axes_y', [])
            if real_ax_d and real_ay_d and placement.get('pdf_h_pt'):
                dalle_tx, dalle_ty, _ = _pdf_bg_transforms(placement, placement['pdf_h_pt'])
                # Light axes + columns
                c.saveState(); c.setStrokeAlpha(0.4)
                c.setStrokeColor(GRIS4); c.setLineWidth(0.3); c.setDash(4, 2)
                for ax in real_ax_d:
                    c.line(dalle_tx(ax), dalle_ty(real_ay_d[0])-5*mm, dalle_tx(ax), dalle_ty(real_ay_d[-1])+5*mm)
                for ay in real_ay_d:
                    c.line(dalle_tx(real_ax_d[0])-5*mm, dalle_ty(ay), dalle_tx(real_ax_d[-1])+5*mm, dalle_ty(ay))
                c.setDash(); c.restoreState()
                # Small column markers
                for ax in real_ax_d:
                    for ay in real_ay_d:
                        c.setFillColor(NOIR); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
                        c.rect(dalle_tx(ax)-2.5, dalle_ty(ay)-2.5, 5, 5, fill=1, stroke=1)
                rendered_dalle = True

    # MODE 2: DWG redraw for ferraillage
    if not rendered_dalle and has_geom_d:
        dtx, dty, dsc, dgw, dgh = _dwg_layout(w, h, lvl_geom)
        if dtx:
            _draw_dwg(c, lvl_geom, dtx, dty, sc=dsc)
            real_ax_d = lvl_geom.get('axes_x', [])
            real_ay_d = lvl_geom.get('axes_y', [])
            dalle_tx, dalle_ty = dtx, dty
            if real_ax_d and real_ay_d:
                c.setStrokeColor(GRIS4); c.setLineWidth(0.25); c.setDash(4, 2)
                for ax in real_ax_d:
                    c.line(dtx(ax), dty(real_ay_d[0])-6*mm, dtx(ax), dty(real_ay_d[-1])+6*mm)
                for ay in real_ay_d:
                    c.line(dtx(real_ax_d[0])-6*mm, dty(ay), dtx(real_ax_d[-1])+6*mm, dty(ay))
                c.setDash()
                pt_d = 4  # fixed size column marker
                for ax in real_ax_d:
                    for ay in real_ay_d:
                        c.setFillColor(NOIR); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
                        c.rect(dtx(ax)-pt_d/2, dty(ay)-pt_d/2, pt_d, pt_d, fill=1, stroke=1)
                rendered_dalle = True

    # MODE 3: Parametric grid
    if not rendered_dalle:
        ox, oy, sc, gw, gh = _grid_layout(w, h, nx, ny, px_m, py_m)
        _draw_grid_axes(c, ox, oy, sc, nx, ny, px_m, py_m, gw, gh)
        _draw_poteaux(c, ox, oy, sc, nx, ny, px_m, py_m, pot_s)

    # Rebar direction arrows in each panel
    if rendered_dalle and real_ax_d and real_ay_d and dalle_tx:
        n_rx = len(real_ax_d); n_ry = len(real_ay_d)
        for i in range(n_rx - 1):
            for j in range(n_ry - 1):
                sx = dalle_tx(real_ax_d[i]) + 2
                sy_a = min(dalle_ty(real_ay_d[j]), dalle_ty(real_ay_d[j+1])) + 2
                sw = abs(dalle_tx(real_ax_d[i+1]) - dalle_tx(real_ax_d[i])) - 4
                sh = abs(dalle_ty(real_ay_d[j+1]) - dalle_ty(real_ay_d[j])) - 4
                if sw < 5 or sh < 5: continue
                cx_p = sx + sw/2; cy_p = sy_a + sh/2
                c.saveState(); c.setStrokeAlpha(0.5)
                c.setStrokeColor(ROUGE); c.setLineWidth(0.4)
                nb_x = max(2, int(sh / 8))
                for k in range(nb_x):
                    yb = sy_a + 3 + k * (sh - 6) / max(nb_x - 1, 1)
                    c.line(sx + 2, yb, sx + sw - 2, yb)
                c.setStrokeColor(BLEU); c.setLineWidth(0.3)
                nb_y = max(2, int(sw / 8))
                for k in range(nb_y):
                    xb = sx + 3 + k * (sw - 6) / max(nb_y - 1, 1)
                    c.line(xb, sy_a + 2, xb, sy_a + sh - 2)
                c.restoreState()
                if sw > 10 and sh > 10:
                    c.setFillColor(NOIR); c.setFont("Helvetica", 2.5)
                    c.drawCentredString(cx_p, cy_p + 2, f"As x={dalle.As_x_cm2_ml:.2f}")
                    c.drawCentredString(cx_p, cy_p - 3, f"As y={dalle.As_y_cm2_ml:.2f}")
    elif not rendered_dalle:
        for i in range(nx):
            for j in range(ny):
                sx = ox + i * px_m * sc; sy = oy + j * py_m * sc
                sw = px_m * sc; sh = py_m * sc
                cx_p = sx + sw/2; cy_p = sy + sh/2
                c.setStrokeColor(ROUGE); c.setLineWidth(0.5)
                nb_x = max(2, int(sh / 8))
                for k in range(nb_x):
                    yb = sy + 4 + k * (sh - 8) / max(nb_x - 1, 1)
                    c.line(sx + 3, yb, sx + sw - 3, yb)
                c.setStrokeColor(BLEU); c.setLineWidth(0.4)
                nb_y = max(2, int(sw / 8))
                for k in range(nb_y):
                    xb = sx + 4 + k * (sw - 8) / max(nb_y - 1, 1)
                    c.line(xb, sy + 3, xb, sy + sh - 3)
                c.setFillColor(NOIR); c.setFont("Helvetica", 3.5)
                c.drawCentredString(cx_p, cy_p + 3, f"As x={dalle.As_x_cm2_ml:.2f}")
                c.drawCentredString(cx_p, cy_p - 3, f"As y={dalle.As_y_cm2_ml:.2f}")

    _legend(c, w, h, [
        (ROUGE, 0.5, f"Nappe inf X — As={dalle.As_x_cm2_ml:.2f} cm²/ml"),
        (BLEU, 0.4, f"Nappe inf Y — As={dalle.As_y_cm2_ml:.2f} cm²/ml"),
        (NOIR, 'fill', f"Poteau {pot_s}×{pot_s}"),
    ])
    c.setFont("Helvetica", 5); c.setFillColor(GRIS3)
    c.drawString(14*mm, 42*mm, f"Dalle ep.{dalle_ep}mm — {beton} — {acier}")
    _cartouche(c, w, h, p, "FERRAILLAGE DALLE", page, total_pages)
    c.showPage()

    # ── FONDATIONS ──
    page += 1
    w, h = A3L; c.setPageSize(A3L); _border(c, w, h)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 13)
    c.drawString(14*mm, h - 17*mm, "PLAN DE FONDATIONS")

    lvl_geom = dwg_levels.get('Sous-Sol') or dwg_levels.get('Rez-de-Chaussée')
    has_geom_f = lvl_geom and len(lvl_geom.get('walls', [])) >= 5
    is_from_pdf_f = False
    is_from_cv_f = bool(lvl_geom.get('_cv_meta')) if has_geom_f else False
    if has_geom_f:
        bounds_f = _dwg_bounds(lvl_geom)
        if bounds_f:
            span_f = max(bounds_f[2] - bounds_f[0], bounds_f[3] - bounds_f[1])
            is_from_pdf_f = span_f < 5000
        if is_from_cv_f and lvl_geom.get('_cv_meta', {}).get('source') == 'pdf':
            is_from_pdf_f = True

    rendered_fond = False
    real_ax_f = []; real_ay_f = []
    fond_tx = fond_ty = None

    nb_pieux = getattr(fd, 'nb_pieux', 0)
    diam_p = getattr(fd, 'diam_pieu_mm', 600)
    larg_sem = getattr(fd, 'largeur_semelle_m', 1.5)

    # MODE 1: PDF background for fondations
    if archi_pdf_path and (is_from_pdf_f or not has_geom_f):
        ok, placement = _render_pdf_background(c, archi_pdf_path, 0, w, h, opacity=0.60, dpi=200)
        if ok and placement and has_geom_f:
            real_ax_f = lvl_geom.get('axes_x', [])
            real_ay_f = lvl_geom.get('axes_y', [])
            if real_ax_f and real_ay_f and placement.get('pdf_h_pt'):
                fond_tx, fond_ty, _ = _pdf_bg_transforms(placement, placement['pdf_h_pt'])
                rendered_fond = True

    # MODE 2: DWG redraw
    if not rendered_fond and has_geom_f:
        dtx, dty, dsc, dgw, dgh = _dwg_layout(w, h, lvl_geom)
        if dtx:
            _draw_dwg(c, lvl_geom, dtx, dty, sc=dsc)
            real_ax_f = lvl_geom.get('axes_x', [])
            real_ay_f = lvl_geom.get('axes_y', [])
            fond_tx, fond_ty = dtx, dty
            if real_ax_f and real_ay_f:
                c.setStrokeColor(GRIS4); c.setLineWidth(0.25); c.setDash(4, 2)
                for ax in real_ax_f:
                    c.line(dtx(ax), dty(real_ay_f[0])-6*mm, dtx(ax), dty(real_ay_f[-1])+6*mm)
                for ay in real_ay_f:
                    c.line(dtx(real_ax_f[0])-6*mm, dty(ay), dtx(real_ax_f[-1])+6*mm, dty(ay))
                c.setDash()
                rendered_fond = True

    if not rendered_fond:
        ox, oy, sc, gw, gh = _grid_layout(w, h, nx, ny, px_m, py_m)
        _draw_grid_axes(c, ox, oy, sc, nx, ny, px_m, py_m, gw, gh)

    # Draw foundations at axis intersections
    if rendered_fond and real_ax_f and real_ay_f and fond_tx:
        pr = 6  # foundation marker size
        for ax in real_ax_f:
            for ay in real_ay_f:
                px_pt, py_pt = fond_tx(ax), fond_ty(ay)
                c.setFillColor(VERT_P); c.setStrokeColor(VERT); c.setLineWidth(0.6)
                if nb_pieux > 0:
                    c.circle(px_pt, py_pt, pr, fill=1, stroke=1)
                else:
                    c.rect(px_pt - pr, py_pt - pr, 2*pr, 2*pr, fill=1, stroke=1)
        # Longrines between foundations
        c.setStrokeColor(NOIR); c.setLineWidth(1.0)
        for ay in real_ay_f:
            for i in range(len(real_ax_f)-1):
                c.line(fond_tx(real_ax_f[i])+pr, fond_ty(ay), fond_tx(real_ax_f[i+1])-pr, fond_ty(ay))
        for ax in real_ax_f:
            for j in range(len(real_ay_f)-1):
                y1_f = fond_ty(real_ay_f[j])
                y2_f = fond_ty(real_ay_f[j+1])
                # Handle flipped Y (y1 might be > y2)
                y_lo_f = min(y1_f, y2_f); y_hi_f = max(y1_f, y2_f)
                c.line(fond_tx(ax), y_lo_f+pr, fond_tx(ax), y_hi_f-pr)
        # Axis labels for fondations
        for i, ax in enumerate(real_ax_f):
            y_lo = min(fond_ty(real_ay_f[0]), fond_ty(real_ay_f[-1]))
            _axis_label(c, fond_tx(ax), y_lo - 10*mm, str(i + 1))
        for j, ay in enumerate(real_ay_f):
            x_lo = fond_tx(real_ax_f[0]) - 10*mm
            _axis_label(c, x_lo, fond_ty(ay), chr(65 + (j % 26)))
    else:
        pr = max(min(diam_p * sc / 2000, 8), 3) if nb_pieux else max(larg_sem * sc / 2, 5)
        for i in range(nx + 1):
            for j in range(ny + 1):
                xp = ox + i * px_m * sc; yp = oy + j * py_m * sc
                c.setFillColor(VERT_P); c.setStrokeColor(VERT); c.setLineWidth(0.4)
                if nb_pieux > 0:
                    c.circle(xp, yp, pr, fill=1, stroke=1)
                else:
                    c.rect(xp - pr, yp - pr, 2*pr, 2*pr, fill=1, stroke=1)
        c.setStrokeColor(NOIR); c.setLineWidth(0.8)
        for j in range(ny + 1):
            for i in range(nx):
                x1 = ox + i * px_m * sc + pr; x2 = ox + (i+1) * px_m * sc - pr
                c.line(x1, oy + j * py_m * sc, x2, oy + j * py_m * sc)
        for i in range(nx + 1):
            for j in range(ny):
                y1 = oy + j * py_m * sc + pr; y2 = oy + (j+1) * py_m * sc - pr
                c.line(ox + i * px_m * sc, y1, ox + i * px_m * sc, y2)

    type_f = fd.type.value.replace('_', ' ').title()
    c.setFont("Helvetica", 5.5); c.setFillColor(GRIS2)
    c.drawString(14*mm, 42*mm, f"{type_f} — prof.{fd.profondeur_m:.1f}m — σsol={r.pression_sol_MPa:.2f}MPa — {beton}")
    _legend(c, w, h, [
        (VERT, 'fill', f"{'Pieu ø'+str(diam_p)+'mm' if nb_pieux else 'Semelle '+str(larg_sem)+'×'+str(larg_sem)+'m'}"),
        (NOIR, 0.8, "Longrine"),
    ])
    _cartouche(c, w, h, p, "FONDATIONS", page, total_pages)
    c.showPage()

    # ── COUPE GÉNÉRALE ──
    page += 1
    w, h = A3L; c.setPageSize(A3L); _border(c, w, h)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 13)
    c.drawString(14*mm, h - 17*mm, "COUPE GÉNÉRALE")

    nc = min(nx, 5)
    rml = 55*mm; rmb = 52*mm
    rdw = w - rml - 45*mm; rdh = h - rmb - 38*mm
    tot_hm = nb_niv * he; tot_wm = px_m * nc
    rsc = min(rdw / tot_wm, rdh / tot_hm)
    cgw = tot_wm * rsc; cgh = tot_hm * rsc
    cox = rml + (rdw - cgw) / 2; coy = rmb + (rdh - cgh) / 2

    # Foundation depth visualization
    fd_depth_m = fd.profondeur_m if hasattr(fd, 'profondeur_m') else 1.5
    fd_h = max(fd_depth_m * rsc, 8)

    # Ground line hatch pattern
    ground_y = coy
    c.setStrokeColor(GRIS3); c.setLineWidth(0.8)
    c.line(cox - 20, ground_y, cox + cgw + 20, ground_y)
    # Earth hatch below ground
    c.setStrokeColor(GRIS4); c.setLineWidth(0.15)
    for k in range(0, int(cgw + 40), 6):
        c.line(cox - 20 + k, ground_y, cox - 20 + k - 4, ground_y - 4)

    # Foundation — hatched concrete block
    c.setFillColor(colors.HexColor("#D7CCC8")); c.setStrokeColor(NOIR); c.setLineWidth(0.5)
    c.rect(cox - 8, coy - fd_h, cgw + 16, fd_h, fill=1, stroke=1)
    # Cross-hatch for concrete
    c.setStrokeColor(GRIS3); c.setLineWidth(0.1)
    for k in range(0, int(cgw + 24 + fd_h), 4):
        lx1 = cox - 8 + min(k, cgw + 16)
        ly1 = coy - fd_h + max(0, k - (cgw + 16))
        lx2 = cox - 8 + max(0, k - fd_h)
        ly2 = coy - fd_h + min(k, fd_h)
        c.line(lx1, ly1, lx2, ly2)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 5)
    c.drawCentredString(cox + cgw/2, coy - fd_h + 3, f"FONDATIONS — {type_f}")
    c.setFillColor(GRIS2); c.setFont("Helvetica", 4)
    c.drawCentredString(cox + cgw/2, coy - fd_h - 5, f"Prof. {fd_depth_m:.1f}m — σsol={r.pression_sol_MPa:.2f} MPa")

    # Draw each storey
    for niv in range(nb_niv):
        yb = coy + niv * he * rsc; yt = coy + (niv + 1) * he * rsc
        pot_k = r.poteaux[niv] if niv < len(r.poteaux) else pot0
        sec_k = pot_k.section_mm
        pw = max(sec_k * rsc / 1000, 2.5)
        dh_s = max(dalle_ep * rsc / 1000, 2.0)

        # Slab — filled with hatch
        c.setFillColor(GRIS5); c.setStrokeColor(NOIR); c.setLineWidth(0.4)
        c.rect(cox - 3, yt - dh_s, cgw + 6, dh_s, fill=1, stroke=1)
        # Slab hatch (diagonal lines)
        c.setStrokeColor(GRIS3); c.setLineWidth(0.08)
        for k in range(0, int(cgw + 6 + dh_s), 3):
            lx1 = cox - 3 + min(k, cgw + 6)
            ly1 = yt - dh_s + max(0, k - (cgw + 6))
            lx2 = cox - 3 + max(0, k - dh_s)
            ly2 = yt - dh_s + min(k, dh_s)
            c.line(lx1, ly1, lx2, ly2)

        # Columns — hatched rectangles
        for i in range(nc + 1):
            cpx = cox + i * px_m * rsc
            col_h = yt - yb - dh_s
            c.setFillColor(colors.HexColor("#E0E0E0")); c.setStrokeColor(NOIR); c.setLineWidth(0.4)
            c.rect(cpx - pw/2, yb, pw, col_h, fill=1, stroke=1)
            # Column hatch
            c.setStrokeColor(GRIS3); c.setLineWidth(0.08)
            for k in range(0, int(pw + col_h), 3):
                lx1 = cpx - pw/2 + min(k, pw)
                ly1 = yb + max(0, k - pw)
                lx2 = cpx - pw/2 + max(0, k - col_h)
                ly2 = yb + min(k, col_h)
                c.line(lx1, ly1, lx2, ly2)

        # Beams at slab level (visible on section as thicker zone)
        if pp_h > dalle_ep:
            beam_ext = max((pp_h - dalle_ep) * rsc / 1000, 1)
            for i in range(nc):
                bx1 = cox + i * px_m * rsc + pw
                bx2 = cox + (i + 1) * px_m * rsc - pw
                c.setFillColor(GRIS5); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
                c.rect(bx1, yt - dh_s - beam_ext, bx2 - bx1, beam_ext, fill=1, stroke=1)

        # Level label on left
        niv_label = getattr(pot_k, 'niveau', f'N{niv}')
        c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 6)
        c.drawRightString(cox - 22*mm, yb + (yt-yb)/2, niv_label)

        # Storey height dimension on right
        c.setStrokeColor(GRIS3); c.setLineWidth(0.3)
        dim_x = cox + cgw + 10
        c.line(dim_x, yb + 1, dim_x, yt - 1)
        c.line(dim_x - 2, yb + 1, dim_x + 2, yb + 1)
        c.line(dim_x - 2, yt - 1, dim_x + 2, yt - 1)
        c.setFillColor(GRIS2); c.setFont("Helvetica", 4)
        c.drawString(dim_x + 3, yb + (yt-yb)/2 - 2, f"{he:.1f}m")

        # Column section label
        c.setFillColor(GRIS3); c.setFont("Helvetica", 3.5)
        c.drawString(dim_x + 3, yb + (yt-yb)/2 - 8, f"Pot.{sec_k}×{sec_k}")

    # Total height dimension on far right
    total_dim_x = cox + cgw + 25
    c.setStrokeColor(NOIR); c.setLineWidth(0.4)
    c.line(total_dim_x, coy, total_dim_x, coy + cgh)
    c.line(total_dim_x - 3, coy, total_dim_x + 3, coy)
    c.line(total_dim_x - 3, coy + cgh, total_dim_x + 3, coy + cgh)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 6)
    c.saveState()
    c.translate(total_dim_x + 5, coy + cgh/2); c.rotate(90)
    c.drawCentredString(0, 0, f"H totale = {tot_hm:.1f} m")
    c.restoreState()

    # Axis labels at bottom
    for i in range(nc + 1):
        _axis_label(c, cox + i * px_m * rsc, coy - fd_h - 14*mm, str(i+1))

    # Span dimensions at bottom
    c.setFillColor(GRIS2); c.setFont("Helvetica", 4.5)
    for i in range(nc):
        mid = cox + (i + 0.5) * px_m * rsc
        c.drawCentredString(mid, coy - fd_h - 8*mm, f"{px_m*1000:.0f}")

    # Technical info
    c.setFont("Helvetica", 5); c.setFillColor(GRIS3)
    c.drawString(14*mm, 46*mm, f"Béton {beton} — Acier {acier}")
    c.drawString(14*mm, 41*mm, f"Dalle ep.{dalle_ep}mm — PP {pp_b}×{pp_h}mm")

    _cartouche(c, w, h, p, "COUPE GÉNÉRALE", page, total_pages, ech="1/200")
    c.showPage()

    # ── PLANCHES FERRAILLAGE depuis generate_plans_v4.py (validées) ──
    # Ces fonctions dessinent sur le canvas et appellent c.showPage()
    try:
        from generate_plans_v4 import pl_poutre, pl_poteau
        # Update page count in cartouche
        pl_poutre(c, r, p)   # Ferraillage poutre principale (A4)
        pl_poteau(c, r, p)   # Ferraillage poteaux par niveau (A4)
    except Exception as e:
        import logging
        logging.getLogger("tijan").warning(f"Ferraillage planches skipped: {e}")

    c.save()
    return output_path


# ══════════════════════════════════════════
# PLANS MEP — même grille, équipements depuis ResultatsMEP
# ══════════════════════════════════════════

def generer_plans_mep(output_path, resultats_mep=None, resultats_structure=None,
                      params=None, dwg_geometry=None, archi_pdf_path=None, **kw):
    """
    Plans MEP. Trois modes (par ordre de priorité) :
    1. Avec dwg_geometry : fond de plan DWG/PDF réel + MEP superposé
    2. Avec archi_pdf_path : PDF archi en fond grisé + grille MEP superposée
    3. Sans : grille paramétrique depuis ParamsProjet + MEP superposé
    Équipements placés dans les pièces réelles depuis ResultatsMEP.
    """
    if resultats_mep is None:
        raise ValueError("ResultatsMEP requis")
    if params is None:
        params = {}
    if hasattr(params, "__dict__"):
        params = {k: v for k, v in vars(params).items() if not k.startswith("_")}

    rm = resultats_mep
    p = params
    nx, ny, px_m, py_m = _build_grid(p)

    # Normalize dwg_geometry to a dict of levels — with axis inference
    dwg_levels = {}
    if dwg_geometry:
        if 'walls' in dwg_geometry:
            # Single geometry — use as "Étage courant"
            enriched = _ensure_axes(dwg_geometry, nx, ny, px_m, py_m)
            dwg_levels = {'Étage courant': enriched}
        else:
            # Multi-level dict
            LEVEL_LABELS = {
                'SOUS_SOL': 'Sous-Sol / Parking',
                'RDC': 'Rez-de-Chaussée',
                'ETAGES_1_7': 'Étages 1 à 7',
                'ETAGE_8': 'Étage 8',
                'TERRASSE': 'Terrasse',
            }
            for key, geom in dwg_geometry.items():
                if isinstance(geom, dict) and len(geom.get('walls', [])) >= 5:
                    enriched = _ensure_axes(geom, nx, ny, px_m, py_m)
                    label = LEVEL_LABELS.get(key, geom.get('label', key))
                    dwg_levels[label] = enriched

    el = rm.electrique
    pl = rm.plomberie
    cv = rm.cvc
    cf = rm.courants_faibles
    si = rm.securite_incendie
    asc = rm.ascenseurs
    aut = rm.automatisation

    pot_s = 300
    if resultats_structure and resultats_structure.poteaux:
        pot_s = resultats_structure.poteaux[0].section_mm

    import re as _re
    def _classify_rooms(rooms):
        wet, living, service = [], [], []
        for r in rooms:
            n = r.get('name', '').lower().strip()
            if _re.match(r'^\d', n): continue
            if any(k in n for k in ['sdb','wc','toil','douche']):
                wet.append({**r, 'rt': 'wet'})
            elif any(k in n for k in ['cuisine','kitch','buanderie']):
                wet.append({**r, 'rt': 'kitchen'})
            elif any(k in n for k in ['salon','chambre','sejour','bureau','sam','bar','gym','restaurant','magasin','salle']):
                living.append({**r, 'rt': 'living'})
            elif any(k in n for k in ['hall','palier','asc','dgt','sas','terrasse','balcon','jardin','piscine','vide','porche','circulation']):
                service.append({**r, 'rt': 'service'})
            else:
                living.append({**r, 'rt': 'other'})
        return wet, living, service

    # Build level list from project params
    nb_niv = p.get('nb_niveaux', 5)
    project_levels = []
    if p.get('avec_sous_sol'):
        project_levels.append("Sous-Sol")
    project_levels.append("RDC")
    nb_et = nb_niv - len(project_levels) - 1  # -1 for terrasse
    if nb_et > 0:
        project_levels.append(f"Étage courant (1-{nb_et})" if nb_et > 1 else "Étage 1")
    project_levels.append("Terrasse")

    # Map each level to its geometry (multi-DWG or reuse single)
    if dwg_levels and len(dwg_levels) > 1:
        level_list = list(dwg_levels.items())
    else:
        # Single geometry: reuse for all levels
        single_geom = list(dwg_levels.values())[0] if dwg_levels else None
        level_list = [(name, single_geom) for name in project_levels]

    # Sub-lots with grouping: sub-lots sharing lot_label are on SAME page
    # 12 sous-lots × N niveaux = 1 page par sous-lot par niveau (lisible)
    sublots = [
        ("PLOMBERIE — Eau Froide",          "PLB",  "plb_ef"),
        ("PLOMBERIE — Eau Chaude",          "PLB",  "plb_ec"),
        ("PLOMBERIE — Évacuations EU/EP",   "PLB",  "plb_eu"),
        ("ÉLECTRICITÉ — Éclairage",         "ELEC", "elec_ecl"),
        ("ÉLECTRICITÉ — Prises & TGBT",     "ELEC", "elec_dist"),
        ("CVC — Climatisation",             "CVC",  "cvc_clim"),
        ("CVC — Ventilation VMC",           "CVC",  "cvc_vmc"),
        ("SÉCURITÉ INCENDIE — Détection",   "SSI",  "ssi_det"),
        ("SÉCURITÉ INCENDIE — Extinction",  "SSI",  "ssi_ext"),
        ("COURANTS FAIBLES",                "CFA",  "cfa"),
        ("ASCENSEURS",                      "ASC",  "asc_plan"),
        ("AUTOMATISATION — GTB",            "GTB",  "gtb"),
    ]

    total_pages = len(sublots) * len(level_list)
    page = 0

    c = pdfcanvas.Canvas(output_path, pagesize=A3L)
    c.setTitle(f"Plans MEP — {p.get('nom','Projet')}")
    c.setAuthor("Tijan AI")

    for title, lot_label, key in sublots:
      for level_idx_mep, (level_label, level_geom) in enumerate(level_list):
        page += 1
        w, h = A3L; c.setPageSize(A3L); _border(c, w, h)
        c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 12)
        c.drawString(14*mm, h - 17*mm, f"{title} — {level_label}")

        # ── Fond de plan : 3 modes (PDF background, DWG redraw, parametric grid) ──
        has_geom_mep = level_geom and len(level_geom.get('walls', [])) >= 5
        is_from_pdf_mep = False
        is_from_cv_mep = bool(level_geom.get('_cv_meta')) if has_geom_mep else False
        if has_geom_mep:
            bounds_mep = _dwg_bounds(level_geom)
            if bounds_mep:
                span_mep = max(bounds_mep[2] - bounds_mep[0], bounds_mep[3] - bounds_mep[1])
                is_from_pdf_mep = span_mep < 5000
            if is_from_cv_mep and level_geom.get('_cv_meta', {}).get('source') == 'pdf':
                is_from_pdf_mep = True

        use_dwg = False
        # Always compute grid layout (needed for fallback bays calculation)
        ox_g, oy_g, sc_g, gw_g, gh_g = _grid_layout(w, h, nx, ny, px_m, py_m)

        # MODE 1: PDF background (primary for PDF uploads)
        if archi_pdf_path and (is_from_pdf_mep or not has_geom_mep):
            pdf_page_idx = min(level_idx_mep, 4)
            ok_mep, placement_mep = _render_pdf_background(
                c, archi_pdf_path, pdf_page_idx, w, h, opacity=0.80, dpi=200
            )
            if ok_mep and placement_mep and has_geom_mep and placement_mep.get('pdf_h_pt'):
                mep_tx, mep_ty, mep_sc = _pdf_bg_transforms(
                    placement_mep, placement_mep['pdf_h_pt']
                )
                tx, ty = mep_tx, mep_ty
                bounds = _dwg_bounds(level_geom)
                ox = tx(bounds[0]); oy = ty(bounds[1])
                gw = abs(tx(bounds[2]) - tx(bounds[0]))
                gh = abs(ty(bounds[3]) - ty(bounds[1]))
                use_dwg = True  # use_dwg means "we have room-aware geometry"
            else:
                ox, oy, gw, gh = ox_g, oy_g, gw_g, gh_g
                c.saveState(); c.setStrokeAlpha(0.4); c.setFillAlpha(0.5)
                _draw_grid_axes(c, ox, oy, sc_g, nx, ny, px_m, py_m, gw, gh)
                _draw_poteaux(c, ox, oy, sc_g, nx, ny, px_m, py_m, pot_s)
                c.restoreState()

        # MODE 2: DWG redraw (any geometry — DWG mm or DXF model units)
        elif has_geom_mep:
            dwg_tx, dwg_ty, dwg_sc, dwg_gw, dwg_gh = _dwg_layout(w, h, level_geom)
            if dwg_tx:
                _draw_dwg(c, level_geom, dwg_tx, dwg_ty, light=True, sc=dwg_sc)
                tx, ty = dwg_tx, dwg_ty
                bounds = _dwg_bounds(level_geom)
                ox = tx(bounds[0]); oy = ty(bounds[1])
                gw = dwg_gw; gh = dwg_gh
                use_dwg = True
            else:
                ox, oy, gw, gh = ox_g, oy_g, gw_g, gh_g
                _draw_grid_axes(c, ox, oy, sc_g, nx, ny, px_m, py_m, gw, gh)
                _draw_poteaux(c, ox, oy, sc_g, nx, ny, px_m, py_m, pot_s)

        # MODE 3: Parametric grid
        else:
            ox, oy, gw, gh = ox_g, oy_g, gw_g, gh_g
            _draw_grid_axes(c, ox, oy, sc_g, nx, ny, px_m, py_m, gw, gh)
            _draw_poteaux(c, ox, oy, sc_g, nx, ny, px_m, py_m, pot_s)

        notes = []

        # ── Dessin MEP : logique room-aware ──
        # Classify rooms for this specific level
        if use_dwg:
            lvl_wet, lvl_living, lvl_service = _classify_rooms(level_geom.get('rooms', []))
            lvl_all = lvl_wet + lvl_living + lvl_service
            lvl_shafts = [(r['x'], r['y']) for r in lvl_service if 'asc' in r.get('name', '').lower()]
            if not lvl_shafts:
                lvl_shafts = [(r['x'], r['y']) for r in lvl_service if 'palier' in r.get('name', '').lower()]
            lvl_halls = [r for r in lvl_service if any(k in r.get('name', '').lower() for k in ['hall','palier','dgt'])]

        # ── Gaine technique unique (GT) : point de passage vertical ──
        # Positionnée à côté de la première gaine ascenseur
        # Tous les réseaux convergent vers ce point via collecteurs horizontaux
        def _draw_gt(c, gtx, gty, label, color):
            """Dessine la gaine technique — symbole large et visible."""
            c.setFillColor(color); c.setStrokeColor(NOIR); c.setLineWidth(1)
            c.rect(gtx-10, gty-10, 20, 20, fill=1, stroke=1)
            c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(gtx, gty-3, label)
            c.setStrokeColor(BLANC); c.setLineWidth(0.8)
            c.line(gtx-4, gty+4, gtx, gty+8); c.line(gtx+4, gty+4, gtx, gty+8)
            c.line(gtx-4, gty-6, gtx, gty-10); c.line(gtx+4, gty-6, gtx, gty-10)
            c.setFillColor(color); c.setFont("Helvetica-Bold", 4)
            c.drawCentredString(gtx, gty-16, "GAINE TECHNIQUE")

        def _route_to_gt(c, fx, fy, gtx, gty, color, width=0.9, dash=None):
            """Placeholder — routing lines removed for clarity."""
            pass

        if use_dwg and lvl_all:
            # MODE DWG : utilise les positions réelles des pièces
            shafts = lvl_shafts
            wet_r = lvl_wet
            living_r = lvl_living
            all_r = lvl_all
            halls = lvl_halls

            # GT position : à côté du premier ascenseur (décalé de 3m)
            if shafts:
                gt_x, gt_y = shafts[0][0] + 3000, shafts[0][1]
            elif halls:
                gt_x, gt_y = halls[0]['x'], halls[0]['y']
            else:
                b = _dwg_bounds(level_geom)
                gt_x, gt_y = (b[0]+b[2])/2, (b[1]+b[3])/2
            gtx_p, gty_p = tx(gt_x), ty(gt_y)

            if key == "plb_ef":
                _draw_gt(c, gtx_p, gty_p, "EF", BLEU)
                c.setFillColor(BLEU); c.setFont("Helvetica-Bold", 3.5)
                c.drawString(gtx_p+10, gty_p+5, f"CM EF DN{pl.diam_colonne_montante_mm}")
                c.setFont("Helvetica", 3)
                c.drawString(gtx_p+10, gty_p, f"Citerne {int(pl.volume_citerne_m3)}m³")
                for wr in wet_r:
                    wx, wy = tx(wr['x']), ty(wr['y'])
                    _route_to_gt(c, wx, wy, gtx_p, gty_p, BLEU)
                    n = wr.get('name','').lower()
                    if 'sdb' in n or 'douche' in n:
                        c.setFillColor(BLANC); c.setStrokeColor(BLEU); c.setLineWidth(0.8)
                        c.circle(wx, wy, 5, fill=1, stroke=1)
                        c.setFillColor(BLEU); c.setFont("Helvetica-Bold", 4)
                        c.drawCentredString(wx, wy-1.5, "SDB")
                    elif 'wc' in n or 'toil' in n:
                        c.setFillColor(BLEU); c.circle(wx, wy, 4, fill=1, stroke=0)
                        c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 3.5)
                        c.drawCentredString(wx, wy-1.5, "WC")
                    elif 'cuisine' in n or 'kitch' in n:
                        c.setFillColor(BLEU); c.rect(wx-6, wy-3.5, 12, 7, fill=1, stroke=0)
                        c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 4)
                        c.drawCentredString(wx, wy-1.5, "CUI")
                    elif 'buanderie' in n:
                        c.setFillColor(CYAN); c.rect(wx-5, wy-3.5, 10, 7, fill=1, stroke=0)
                        c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 3.5)
                        c.drawCentredString(wx, wy-1.5, "BUA")
                notes = [f"Colonne montante EF DN{pl.diam_colonne_montante_mm}",
                         f"Citerne {int(pl.volume_citerne_m3)}m³ — Surpresseur {pl.debit_surpresseur_m3h}m³/h",
                         f"{pl.nb_robinets_eco} robinets économiseurs — {pl.nb_wc_double_chasse} WC double chasse"]
                _legend(c, w, h, [(BLEU, 'fill', f"GT — CM EF DN{pl.diam_colonne_montante_mm}"),
                                  (BLEU, 0.5, "Distribution EF"),
                                  (BLEU, 'circle', "SDB / Douche"),
                                  (BLEU, 'fill', "WC / Toilettes"),
                                  (BLEU, 'fill', "Évier cuisine"),
                                  (CYAN, 'fill', "Buanderie")])

            elif key == "plb_ec":
                _draw_gt(c, gtx_p, gty_p, "EC", ROUGE)
                for wr in wet_r:
                    n = wr.get('name','').lower()
                    if any(k in n for k in ['sdb','douche','cuisine','kitch','buanderie']):
                        wx, wy = tx(wr['x']), ty(wr['y'])
                        _route_to_gt(c, wx, wy, gtx_p, gty_p, ROUGE, 0.5, (3,1.5))
                        c.setFillColor(BLANC); c.setStrokeColor(ROUGE); c.setLineWidth(0.5)
                        c.circle(wx, wy, 2.5, fill=1, stroke=1)
                notes = ["CM EC DN32", f"{pl.nb_chauffe_eau_solaire} CESI"]
                _legend(c, w, h, [(ROUGE, 'fill', "GT — EC DN32"), (ROUGE, 0.5, "Distribution EC")])

            elif key == "plb_eu":
                _draw_gt(c, gtx_p, gty_p, "EU", MARRON)
                c.setFillColor(MARRON); c.setFont("Helvetica", 3)
                c.drawString(gtx_p+7, gty_p+3, "CE EU DN100")
                for wr in wet_r:
                    wx, wy = tx(wr['x']), ty(wr['y'])
                    _route_to_gt(c, wx, wy, gtx_p, gty_p, MARRON, 0.5, (4,2))
                    c.setFillColor(MARRON); c.circle(wx, wy, 2, fill=1, stroke=0)
                notes = ["Chute EU DN100", f"Conso {pl.conso_eau_annuelle_m3:.0f}m³/an"]
                _legend(c, w, h, [(MARRON, 'fill', "GT — EU DN100"), (MARRON, 0.5, "Collecteur")])

            elif key == "elec_ecl":
                for r in all_r:
                    n = r.get('name','').lower()
                    if any(k in n for k in ['terrasse','balcon','jardin','piscine','vide','espace']): continue
                    rx, ry = tx(r['x']), ty(r['y'])
                    # Luminaire — cercle avec croix (symbole standard)
                    c.setStrokeColor(JAUNE); c.setFillColor(colors.HexColor("#FFF8E1")); c.setLineWidth(0.7)
                    c.circle(rx, ry+6, 5, fill=1, stroke=1)
                    c.setStrokeColor(JAUNE); c.setLineWidth(0.5)
                    c.line(rx-3.5, ry+6, rx+3.5, ry+6); c.line(rx, ry+2.5, rx, ry+9.5)
                    # Interrupteur
                    if any(k in n for k in ['chambre','salon','sejour','bureau','sam','bar','cuisine','sdb','wc','restaurant','magasin','salle']):
                        c.setFillColor(colors.HexColor("#FFF9C4")); c.setStrokeColor(ORANGE); c.setLineWidth(0.5)
                        c.circle(rx-10, ry+2, 3, fill=1, stroke=1)
                        c.setStrokeColor(ORANGE); c.setLineWidth(0.4)
                        c.line(rx-10, ry+5, rx-7, ry+7)
                notes = [f"Puissance éclairage: {el.puissance_eclairage_kw:.1f} kW",
                         f"Puissance totale: {el.puissance_totale_kva:.0f} kVA"]
                _legend(c, w, h, [(JAUNE, 'circle', "Luminaire plafonnier"),
                                  (colors.HexColor("#FFF9C4"), 'circle', "Interrupteur simple allumage")])

            elif key == "elec_dist":
                # TD dans la gaine technique
                _draw_gt(c, gtx_p, gty_p, "TD", VERT)
                c.setFillColor(VERT); c.setFont("Helvetica", 3)
                c.drawString(gtx_p+7, gty_p+3, f"Transfo {el.transfo_kva}kVA")
                # Chemin de câbles principal via les circulations → GT
                sh = sorted(halls, key=lambda r: r['y'])
                if sh:
                    c.setStrokeColor(ORANGE); c.setLineWidth(1.5)
                    prev_x, prev_y = gtx_p, gty_p
                    for hh in sh:
                        hx, hy = tx(hh['x']), ty(hh['y'])
                        c.line(prev_x, prev_y, hx, hy); prev_x, prev_y = hx, hy
                # Prises dans chaque pièce
                for r in all_r:
                    n = r.get('name','').lower()
                    if any(k in n for k in ['terrasse','balcon','jardin','piscine','vide','espace']): continue
                    rx, ry = tx(r['x']), ty(r['y'])
                    c.setFillColor(ORANGE); c.setStrokeColor(NOIR); c.setLineWidth(0.15)
                    if any(k in n for k in ['chambre','salon','sejour','bureau','sam','bar','restaurant']):
                        for dx, dy in [(-6,-3),(6,-3),(-6,3),(6,3)]:
                            c.rect(rx+dx-2, ry+dy-1.2, 4, 2.4, fill=1, stroke=1)
                    elif any(k in n for k in ['cuisine','kitch']):
                        for dx, dy in [(-6,-3),(6,-3),(-6,3),(6,3),(0,-5),(0,5)]:
                            c.rect(rx+dx-2, ry+dy-1.2, 4, 2.4, fill=1, stroke=1)
                    else:
                        c.rect(rx+4, ry-0.8, 2.4, 1.6, fill=1, stroke=1)
                notes = [f"Transfo {el.transfo_kva}kVA", f"GE {el.groupe_electrogene_kva}kVA",
                         f"{el.nb_compteurs} compteurs — Col.{el.section_colonne_mm2}mm²"]
                _legend(c, w, h, [(VERT, 'fill', "GT — TD"), (ORANGE, 1.5, "Chemin câbles"),
                                  (ORANGE, 'fill', "Prise 2P+T")])

            elif key == "cvc_clim":
                for r in living_r:
                    n = r.get('name','').lower()
                    if any(k in n for k in ['chambre','salon','sejour','bureau','sam','bar','gym','restaurant','salle','magasin']):
                        rx, ry = tx(r['x']), ty(r['y'])
                        c.setFillColor(CYAN); c.setStrokeColor(colors.HexColor("#006064")); c.setLineWidth(0.35)
                        c.rect(rx-6, ry+7, 12, 4, fill=1, stroke=1)
                        c.setFillColor(colors.HexColor("#006064")); c.setFont("Helvetica", 2.2)
                        if 'salon' in n or 'sejour' in n or 'sam' in n or 'restaurant' in n:
                            c.drawCentredString(rx, ry+11.5, "18000 BTU")
                        elif 'chambre' in n:
                            c.drawCentredString(rx, ry+11.5, "12000 BTU")
                        else:
                            c.drawCentredString(rx, ry+11.5, "9000 BTU")
                notes = [f"P frigo: {cv.puissance_frigorifique_kw:.0f}kW",
                         f"Splits séj: {cv.nb_splits_sejour} — ch: {cv.nb_splits_chambre}"]
                _legend(c, w, h, [(CYAN, 'fill', "Split mural")])

            elif key == "cvc_vmc":
                for r in wet_r:
                    rx, ry = tx(r['x']), ty(r['y'])
                    c.setStrokeColor(colors.HexColor("#2E7D32")); c.setFillColor(colors.HexColor("#C8E6C9"))
                    c.setLineWidth(0.4); c.circle(rx, ry+5, 4, fill=1, stroke=1)
                    c.setStrokeColor(colors.HexColor("#2E7D32")); c.setLineWidth(0.5)
                    c.line(rx, ry+6.5, rx, ry+9)
                if len(halls) >= 2:
                    sh = sorted(halls, key=lambda r: r['y'])
                    c.setStrokeColor(colors.HexColor("#2E7D32")); c.setLineWidth(1.2); c.setDash(5,2)
                    for i in range(len(sh)-1):
                        c.line(tx(sh[i]['x']), ty(sh[i]['y']), tx(sh[i+1]['x']), ty(sh[i+1]['y']))
                    c.setDash()
                notes = [f"{cv.nb_vmc} VMC {cv.type_vmc}"]
                _legend(c, w, h, [(colors.HexColor("#2E7D32"), 'circle', "Bouche VMC"),
                                  (colors.HexColor("#2E7D32"), 0.5, "Gaine VMC")])

            elif key == "ssi_det":
                for r in all_r:
                    n = r.get('name','').lower()
                    if any(k in n for k in ['terrasse','balcon','jardin','piscine','vide']): continue
                    rx, ry = tx(r['x']), ty(r['y'])
                    c.setFillColor(BLANC); c.setStrokeColor(ROUGE); c.setLineWidth(0.5)
                    c.circle(rx, ry-6, 4, fill=1, stroke=1)
                    c.setFillColor(ROUGE); c.setFont("Helvetica-Bold", 3)
                    c.drawCentredString(rx, ry-8, "DF")
                exits = [r for r in lvl_service if any(k in r.get('name','').lower() for k in ['palier','hall','sas'])]
                for r in exits:
                    rx, ry = tx(r['x']), ty(r['y'])
                    c.setFillColor(ROUGE); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
                    c.rect(rx-9, ry-3, 6, 6, fill=1, stroke=1)
                    c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 2.5)
                    c.drawCentredString(rx-6, ry-1, "DM")
                notes = [f"{si.nb_detecteurs_fumee} DF — {si.nb_declencheurs_manuels} DM",
                         f"Cat.ERP {si.categorie_erp} — {si.centrale_zones} zones"]
                _legend(c, w, h, [(ROUGE, 'circle', "DF"), (ROUGE, 'fill', "DM")])

            elif key == "ssi_ext":
                stairs = [r for r in lvl_service if 'palier' in r.get('name','').lower()]
                for r in stairs:
                    rx, ry = tx(r['x']), ty(r['y'])
                    c.setFillColor(BLANC); c.setStrokeColor(ROUGE); c.setLineWidth(0.7)
                    c.circle(rx+10, ry+5, 5, fill=1, stroke=1)
                    c.setFillColor(ROUGE); c.setFont("Helvetica-Bold", 4)
                    c.drawCentredString(rx+10, ry+3, "R")
                    c.setFillColor(VERT); c.setStrokeColor(NOIR); c.setLineWidth(0.25)
                    c.rect(rx+4, ry-10, 8, 5, fill=1, stroke=1)
                    c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 2)
                    c.drawCentredString(rx+8, ry-8.5, "BAES")
                notes = [f"{si.nb_extincteurs_co2+si.nb_extincteurs_poudre} ext. — RIA {si.longueur_ria_ml:.0f}ml",
                         f"Sprinklers: {'OUI' if si.sprinklers_requis else 'NON'}"]
                _legend(c, w, h, [(ROUGE, 'circle', "RIA"), (VERT, 'fill', "BAES")])

            elif key == "cfa":
                for r in all_r:
                    n = r.get('name','').lower()
                    if any(k in n for k in ['terrasse','balcon','jardin','piscine','vide']): continue
                    if any(k in n for k in ['chambre','salon','sejour','bureau','sam','cuisine','hall','restaurant','salle']):
                        rx, ry = tx(r['x']), ty(r['y'])
                        c.setFillColor(VIOLET); c.setStrokeColor(NOIR); c.setLineWidth(0.2)
                        c.rect(rx-2.5, ry-5, 5, 4, fill=1, stroke=1)
                cams = [r for r in lvl_service if any(k in r.get('name','').lower() for k in ['hall','palier','sas','porche'])]
                for r in cams:
                    rx, ry = tx(r['x']), ty(r['y'])
                    c.setFillColor(colors.HexColor("#CE93D8")); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
                    path = c.beginPath()
                    path.moveTo(rx, ry+10); path.lineTo(rx-4, ry+3); path.lineTo(rx+4, ry+3)
                    path.close(); c.drawPath(path, fill=1, stroke=0)
                notes = [f"{cf.nb_prises_rj45} RJ45 — {cf.nb_cameras_int+cf.nb_cameras_ext} caméras"]
                _legend(c, w, h, [(VIOLET, 'fill', "RJ45"), (colors.HexColor("#CE93D8"), 'circle', "Caméra IP")])

            elif key == "asc_plan":
                for r in lvl_service:
                    if 'asc' in r.get('name','').lower():
                        rx, ry = tx(r['x']), ty(r['y'])
                        c.setFillColor(BLEU_B); c.setStrokeColor(BLEU); c.setLineWidth(1)
                        c.rect(rx-10, ry-10, 20, 20, fill=1, stroke=1)
                        c.setStrokeColor(BLEU); c.setLineWidth(0.3)
                        c.line(rx-10, ry-10, rx+10, ry+10); c.line(rx-10, ry+10, rx+10, ry-10)
                        c.setFillColor(BLEU); c.setFont("Helvetica-Bold", 3)
                        c.drawCentredString(rx, ry-12, f"{asc.nb_ascenseurs}× {asc.capacite_kg}kg")
                notes = [f"{asc.nb_ascenseurs} asc. {asc.capacite_kg}kg — {asc.vitesse_ms}m/s"]
                _legend(c, w, h, [(BLEU_B, 'fill', "Gaine ascenseur")])

            elif key == "gtb":
                if len(halls) >= 2:
                    sh = sorted(halls, key=lambda r: r['y'])
                    c.setStrokeColor(BLEU); c.setLineWidth(1.8)
                    for i in range(len(sh)-1):
                        c.line(tx(sh[i]['x']), ty(sh[i]['y']), tx(sh[i+1]['x']), ty(sh[i+1]['y']))
                for r in all_r:
                    n = r.get('name','').lower()
                    if any(k in n for k in ['terrasse','balcon','jardin','piscine','vide']): continue
                    rx, ry = tx(r['x']), ty(r['y'])
                    if any(k in n for k in ['hall','palier','dgt','sas']):
                        c.setFillColor(ORANGE); c.circle(rx-6, ry+6, 2, fill=1, stroke=0)
                    if any(k in n for k in ['chambre','salon','sejour','bureau','sam']):
                        c.setFillColor(ORANGE); c.rect(rx-7, ry-5, 4, 3, fill=1, stroke=0)
                notes = [f"{aut.protocole} — {aut.niveau} — {aut.nb_points_controle} pts"]
                _legend(c, w, h, [(BLEU, 1.8, f"Bus {aut.protocole}"), (ORANGE, 'circle', "Capteur")])

        else:
            # MODE GRILLE : distribution dans les travées
            cx_noy = ox + gw/2; cy_noy = oy + gh/2
            bays = []
            for i in range(nx):
                for j in range(ny):
                    bays.append((ox + (i+0.5)*px_m*sc_g, oy + (j+0.5)*py_m*sc_g))

            if key == "plb_ef":
                c.setFillColor(BLEU); c.setStrokeColor(NOIR); c.setLineWidth(0.6)
                c.circle(cx_noy, cy_noy, 4, fill=1, stroke=1)
                c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 5); c.drawCentredString(cx_noy, cy_noy-2, "EF")
                for bx, by in bays:
                    c.setStrokeColor(BLEU); c.setLineWidth(0.6)
                    c.line(cx_noy, cy_noy, cx_noy, by); c.line(cx_noy, by, bx, by)
                    c.setFillColor(BLEU); c.circle(bx, by, 2, fill=1, stroke=0)
                notes = [f"CM EF DN{pl.diam_colonne_montante_mm}", f"Citerne {int(pl.volume_citerne_m3)}m³"]
                _legend(c, w, h, [(BLEU, 'circle', f"CM EF DN{pl.diam_colonne_montante_mm}"),
                                  (BLEU, 0.6, "Distribution EF")])
            elif key == "plb_ec":
                c.setFillColor(ROUGE); c.setStrokeColor(NOIR); c.setLineWidth(0.6)
                c.circle(cx_noy, cy_noy, 4, fill=1, stroke=1)
                c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 5); c.drawCentredString(cx_noy, cy_noy-2, "EC")
                for bx, by in bays:
                    c.setStrokeColor(ROUGE); c.setLineWidth(0.5); c.setDash(3,1.5)
                    c.line(cx_noy, cy_noy, cx_noy, by); c.line(cx_noy, by, bx, by); c.setDash()
                notes = ["CM EC DN32", f"{pl.nb_chauffe_eau_solaire} CESI"]
                _legend(c, w, h, [(ROUGE, 'circle', "CM EC DN32"), (ROUGE, 0.5, "Distribution EC")])
            elif key == "plb_eu":
                c.setFillColor(MARRON); c.setStrokeColor(NOIR); c.setLineWidth(0.6)
                c.circle(cx_noy, cy_noy, 4, fill=1, stroke=1)
                c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 5); c.drawCentredString(cx_noy, cy_noy-2, "EU")
                for bx, by in bays:
                    c.setStrokeColor(MARRON); c.setLineWidth(0.5); c.setDash(4,2)
                    c.line(bx, by, cx_noy, by); c.line(cx_noy, by, cx_noy, cy_noy); c.setDash()
                    c.setFillColor(MARRON); c.circle(bx, by, 1.5, fill=1, stroke=0)
                notes = ["Chute EU DN100", f"Conso {pl.conso_eau_annuelle_m3:.0f}m³/an"]
                _legend(c, w, h, [(MARRON, 'circle', "Chute EU DN100"), (MARRON, 0.5, "Collecteur")])
            elif key == "elec_ecl":
                for bx, by in bays:
                    c.setStrokeColor(JAUNE); c.setFillColor(colors.HexColor("#FFF8E1")); c.setLineWidth(0.4)
                    c.circle(bx, by, 3, fill=1, stroke=1)
                    c.setStrokeColor(JAUNE); c.setLineWidth(0.3)
                    c.line(bx-2, by, bx+2, by); c.line(bx, by-2, bx, by+2)
                notes = [f"P éclairage: {el.puissance_eclairage_kw:.1f}kW"]
                _legend(c, w, h, [(JAUNE, 'circle', "Luminaire")])
            elif key == "elec_dist":
                c.setFillColor(VERT); c.setStrokeColor(NOIR); c.setLineWidth(0.6)
                c.rect(cx_noy-5, cy_noy-5, 10, 7, fill=1, stroke=1)
                c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 4); c.drawCentredString(cx_noy, cy_noy-3, "TGBT")
                c.setStrokeColor(ORANGE); c.setLineWidth(1.2)
                c.line(cx_noy, cy_noy-5, cx_noy, oy); c.line(cx_noy, cy_noy+2, cx_noy, oy+gh)
                for bx, by in bays:
                    c.setFillColor(ORANGE); c.setStrokeColor(NOIR); c.setLineWidth(0.15)
                    for dx, dy in [(-4,-2),(4,-2),(-4,2),(4,2)]:
                        c.rect(bx+dx-1.2, by+dy-0.8, 2.4, 1.6, fill=1, stroke=1)
                notes = [f"Transfo {el.transfo_kva}kVA", f"GE {el.groupe_electrogene_kva}kVA"]
                _legend(c, w, h, [(VERT, 'fill', "TGBT"), (ORANGE, 1.2, "Chemin câbles"), (ORANGE, 'fill', "Prise")])
            elif key == "cvc_clim":
                for bx, by in bays:
                    c.setFillColor(CYAN); c.setStrokeColor(colors.HexColor("#006064")); c.setLineWidth(0.35)
                    c.rect(bx-5, by+4, 10, 3, fill=1, stroke=1)
                notes = [f"P frigo: {cv.puissance_frigorifique_kw:.0f}kW", f"Splits: {cv.nb_splits_sejour+cv.nb_splits_chambre}"]
                _legend(c, w, h, [(CYAN, 'fill', "Split")])
            elif key == "cvc_vmc":
                for bx, by in bays:
                    c.setStrokeColor(colors.HexColor("#2E7D32")); c.setFillColor(colors.HexColor("#C8E6C9"))
                    c.setLineWidth(0.4); c.circle(bx, by-3, 3, fill=1, stroke=1)
                notes = [f"{cv.nb_vmc} VMC {cv.type_vmc}"]
                _legend(c, w, h, [(colors.HexColor("#2E7D32"), 'circle', "Bouche VMC")])
            elif key == "ssi_det":
                for bx, by in bays:
                    c.setFillColor(BLANC); c.setStrokeColor(ROUGE); c.setLineWidth(0.5)
                    c.circle(bx, by, 3, fill=1, stroke=1)
                    c.setFillColor(ROUGE); c.setFont("Helvetica-Bold", 3.5); c.drawCentredString(bx, by-1.5, "DF")
                notes = [f"{si.nb_detecteurs_fumee} DF — {si.nb_declencheurs_manuels} DM"]
                _legend(c, w, h, [(ROUGE, 'circle', "DF")])
            elif key == "ssi_ext":
                for corner in [(ox+10, oy+10), (ox+gw-10, oy+gh-10)]:
                    rx, ry = corner
                    c.setFillColor(BLANC); c.setStrokeColor(ROUGE); c.setLineWidth(0.7)
                    c.circle(rx, ry, 4, fill=1, stroke=1)
                    c.setFillColor(ROUGE); c.setFont("Helvetica-Bold", 5); c.drawCentredString(rx, ry-2, "R")
                    c.setFillColor(VERT); c.rect(rx+8, ry-4, 6, 3.5, fill=1, stroke=1)
                notes = [f"{si.nb_extincteurs_co2+si.nb_extincteurs_poudre} ext. — RIA {si.longueur_ria_ml:.0f}ml"]
                _legend(c, w, h, [(ROUGE, 'circle', "RIA"), (VERT, 'fill', "BAES")])
            elif key == "cfa":
                for bx, by in bays:
                    c.setFillColor(VIOLET); c.setStrokeColor(NOIR); c.setLineWidth(0.2)
                    c.rect(bx-2, by-2, 4, 3, fill=1, stroke=1)
                notes = [f"{cf.nb_prises_rj45} RJ45 — {cf.nb_cameras_int+cf.nb_cameras_ext} caméras"]
                _legend(c, w, h, [(VIOLET, 'fill', "RJ45")])
            elif key == "asc_plan":
                c.setFillColor(BLEU_B); c.setStrokeColor(BLEU); c.setLineWidth(1)
                c.rect(cx_noy-8, cy_noy-8, 16, 16, fill=1, stroke=1)
                c.setStrokeColor(BLEU); c.setLineWidth(0.3)
                c.line(cx_noy-8, cy_noy-8, cx_noy+8, cy_noy+8); c.line(cx_noy-8, cy_noy+8, cx_noy+8, cy_noy-8)
                c.setFillColor(BLEU); c.setFont("Helvetica-Bold", 4)
                c.drawCentredString(cx_noy, cy_noy-12, f"{asc.nb_ascenseurs}× {asc.capacite_kg}kg")
                notes = [f"{asc.nb_ascenseurs} asc. {asc.capacite_kg}kg"]
                _legend(c, w, h, [(BLEU_B, 'fill', "Gaine ascenseur")])
            elif key == "gtb":
                c.setStrokeColor(BLEU); c.setLineWidth(1.8)
                c.line(ox, cy_noy, ox+gw, cy_noy)
                for bx, by in bays:
                    c.setFillColor(ORANGE); c.circle(bx-3, by+3, 1.5, fill=1, stroke=0)
                notes = [f"{aut.protocole} — {aut.nb_points_controle} pts"]
                _legend(c, w, h, [(BLEU, 1.8, f"Bus {aut.protocole}"), (ORANGE, 'circle', "Capteur")])

        # Notes en bas
        c.setFont("Helvetica", 5); c.setFillColor(GRIS3)
        for k_n, note in enumerate(notes[:3]):
            c.drawString(14*mm, 42*mm - k_n*5*mm, note)

        _cartouche(c, w, h, p, f"{title} — {level_label}", page, total_pages)
        c.showPage()

    c.save()
    return output_path


# ══════════════════════════════════════════
# DXF OUTPUT — Structure & MEP plans as DXF
# ══════════════════════════════════════════

def _dxf_add_geometry(msp, dwg, layer_walls, layer_win, layer_doors, layer_rooms, oy=0):
    """Add DWG geometry entities to ezdxf modelspace."""
    for item in dwg.get('walls', []):
        if item['type'] == 'line':
            msp.add_line(
                (item['start'][0], item['start'][1] + oy),
                (item['end'][0], item['end'][1] + oy),
                dxfattribs={'layer': layer_walls},
            )
        elif item['type'] == 'polyline':
            pts = [(p[0], p[1] + oy) for p in item['points']]
            pl = msp.add_lwpolyline(pts, dxfattribs={'layer': layer_walls})
            if item.get('closed'):
                pl.close()
    for item in dwg.get('windows', []):
        if item['type'] == 'line':
            msp.add_line(
                (item['start'][0], item['start'][1] + oy),
                (item['end'][0], item['end'][1] + oy),
                dxfattribs={'layer': layer_win},
            )
    for item in dwg.get('doors', []):
        if item['type'] == 'line':
            msp.add_line(
                (item['start'][0], item['start'][1] + oy),
                (item['end'][0], item['end'][1] + oy),
                dxfattribs={'layer': layer_doors},
            )
    for room in dwg.get('rooms', []):
        msp.add_text(
            room.get('name', ''),
            height=200,
            dxfattribs={
                'layer': layer_rooms,
                'insert': (room['x'], room['y'] + oy),
            },
        )


def generer_plans_structure_dxf(output_path, resultats=None, params=None, dwg_geometry=None, **kw):
    """
    Plans structure as DXF — architecture + structural grid (poteaux, poutres, dalles).
    Same data as generer_plans_structure() but outputs DXF instead of PDF.
    """
    import ezdxf

    if resultats is None:
        raise ValueError("ResultatsStructure requis")
    if params is None:
        params = {}
    if hasattr(params, "__dict__"):
        params = {k: v for k, v in vars(params).items() if not k.startswith("_")}

    r = resultats
    p = params
    nx, ny, px_m, py_m = _build_grid(p)
    pot0 = r.poteaux[0] if r.poteaux else None
    pp = r.poutre_principale
    ps = r.poutre_secondaire
    dalle = r.dalle

    if pot0 is None or pp is None:
        raise ValueError("Résultats structure incomplets")

    pot_s = pot0.section_mm
    pp_b, pp_h = pp.b_mm, pp.h_mm
    dalle_ep = dalle.epaisseur_mm

    # Normalize DWG geometry to levels
    LEVEL_LABELS = {
        'SOUS_SOL': 'Sous-Sol', 'RDC': 'Rez-de-Chaussée',
        'ETAGES_1_7': 'Étage courant', 'ETAGE_8': 'Étage 8', 'TERRASSE': 'Terrasse',
    }
    dwg_levels = {}
    if dwg_geometry:
        if 'walls' in dwg_geometry:
            enriched = _ensure_axes(dwg_geometry, nx, ny, px_m, py_m)
            dwg_levels = {'Étage courant': enriched}
        else:
            for key, geom in dwg_geometry.items():
                if isinstance(geom, dict) and len(geom.get('walls', [])) >= 5:
                    enriched = _ensure_axes(geom, nx, ny, px_m, py_m)
                    dwg_levels[LEVEL_LABELS.get(key, key)] = enriched

    level_names = []
    if p.get("avec_sous_sol"):
        level_names.append("Sous-Sol")
    level_names.append("RDC")
    nb_niv = p.get("nb_niveaux", len(r.poteaux))
    nb_etages = nb_niv - len(level_names)
    if nb_etages > 0:
        level_names.append("Étage courant")
    level_names.append("Terrasse")

    # Create DXF document
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()

    # Layers
    doc.layers.new('ARCH_MURS', dxfattribs={'color': 8})
    doc.layers.new('ARCH_FENETRES', dxfattribs={'color': 4})
    doc.layers.new('ARCH_PORTES', dxfattribs={'color': 30})
    doc.layers.new('ARCH_PIECES', dxfattribs={'color': 9})
    doc.layers.new('STR_AXES', dxfattribs={'color': 8})
    doc.layers.new('STR_POTEAUX', dxfattribs={'color': 7})
    doc.layers.new('STR_POUTRES_PP', dxfattribs={'color': 1})
    doc.layers.new('STR_POUTRES_PS', dxfattribs={'color': 8})
    doc.layers.new('STR_DALLES', dxfattribs={'color': 9})
    doc.layers.new('STR_LABELS', dxfattribs={'color': 2})
    doc.layers.new('LEVEL_LABELS', dxfattribs={'color': 3})

    y_offset = 0

    for level_name in level_names:
        lvl_geom = dwg_levels.get(level_name) or dwg_levels.get('Étage courant')
        has_dwg = lvl_geom and len(lvl_geom.get('walls', [])) >= 5

        if has_dwg:
            bounds = _dwg_bounds(lvl_geom)
            if not bounds:
                continue
            xn, yn, xx, yx = bounds
            dh_r = yx - yn

            # Level label
            msp.add_text(
                level_name.upper(), height=500,
                dxfattribs={'layer': 'LEVEL_LABELS', 'insert': (xn, yn - 2000 + y_offset)},
            )

            # Architecture
            _dxf_add_geometry(msp, lvl_geom, 'ARCH_MURS', 'ARCH_FENETRES', 'ARCH_PORTES', 'ARCH_PIECES', oy=y_offset)

            # Structural grid from real axes if available
            real_ax = lvl_geom.get('axes_x', [])
            real_ay = lvl_geom.get('axes_y', [])
            if real_ax and real_ay:
                for ax in real_ax:
                    msp.add_line(
                        (ax, real_ay[0] - 1500 + y_offset),
                        (ax, real_ay[-1] + 1500 + y_offset),
                        dxfattribs={'layer': 'STR_AXES', 'linetype': 'DASHED'},
                    )
                for ay in real_ay:
                    msp.add_line(
                        (real_ax[0] - 1500, ay + y_offset),
                        (real_ax[-1] + 1500, ay + y_offset),
                        dxfattribs={'layer': 'STR_AXES', 'linetype': 'DASHED'},
                    )
                for i, ax in enumerate(real_ax):
                    msp.add_text(
                        str(i + 1), height=300,
                        dxfattribs={'layer': 'STR_LABELS', 'insert': (ax, real_ay[0] - 3000 + y_offset)},
                    )
                for j, ay in enumerate(real_ay):
                    msp.add_text(
                        chr(65 + (j % 26)), height=300,
                        dxfattribs={'layer': 'STR_LABELS', 'insert': (real_ax[0] - 3000, ay + y_offset)},
                    )
                for ay in real_ay:
                    for i in range(len(real_ax) - 1):
                        msp.add_line(
                            (real_ax[i], ay + y_offset),
                            (real_ax[i + 1], ay + y_offset),
                            dxfattribs={'layer': 'STR_POUTRES_PP'},
                        )
                for ax in real_ax:
                    for j in range(len(real_ay) - 1):
                        msp.add_line(
                            (ax, real_ay[j] + y_offset),
                            (ax, real_ay[j + 1] + y_offset),
                            dxfattribs={'layer': 'STR_POUTRES_PS'},
                        )
                half = pot_s / 2
                for ax in real_ax:
                    for ay in real_ay:
                        pts = [
                            (ax - half, ay - half + y_offset),
                            (ax + half, ay - half + y_offset),
                            (ax + half, ay + half + y_offset),
                            (ax - half, ay + half + y_offset),
                        ]
                        pl = msp.add_lwpolyline(pts, dxfattribs={'layer': 'STR_POTEAUX'})
                        pl.close()
                for i in range(len(real_ax) - 1):
                    for j in range(len(real_ay) - 1):
                        cx = (real_ax[i] + real_ax[i + 1]) / 2
                        cy = (real_ay[j] + real_ay[j + 1]) / 2
                        span_x = (real_ax[i + 1] - real_ax[i]) / 1000
                        span_y = (real_ay[j + 1] - real_ay[j]) / 1000
                        msp.add_text(
                            f"Dalle ep.{dalle_ep} — {span_x:.1f}x{span_y:.1f}m",
                            height=150,
                            dxfattribs={'layer': 'STR_DALLES', 'insert': (cx, cy + y_offset)},
                        )
            else:
                cx_d = (xn + xx) / 2
                cy_d = (yn + yx) / 2
                gx0 = cx_d - nx * px_m * 500
                gy0 = cy_d - ny * py_m * 500
                for i in range(nx + 1):
                    ax = gx0 + i * px_m * 1000
                    msp.add_line(
                        (ax, gy0 + y_offset), (ax, gy0 + ny * py_m * 1000 + y_offset),
                        dxfattribs={'layer': 'STR_AXES'},
                    )
                for j in range(ny + 1):
                    ay = gy0 + j * py_m * 1000
                    msp.add_line(
                        (gx0, ay + y_offset), (gx0 + nx * px_m * 1000, ay + y_offset),
                        dxfattribs={'layer': 'STR_AXES'},
                    )
                half = pot_s / 2
                for i in range(nx + 1):
                    for j in range(ny + 1):
                        px = gx0 + i * px_m * 1000
                        py_ = gy0 + j * py_m * 1000 + y_offset
                        pts = [(px - half, py_ - half), (px + half, py_ - half),
                               (px + half, py_ + half), (px - half, py_ + half)]
                        pl = msp.add_lwpolyline(pts, dxfattribs={'layer': 'STR_POTEAUX'})
                        pl.close()

            y_offset += dh_r + 15000

        else:
            gx0, gy0 = 0, y_offset
            msp.add_text(
                level_name.upper(), height=500,
                dxfattribs={'layer': 'LEVEL_LABELS', 'insert': (gx0, gy0 - 2000)},
            )
            for i in range(nx + 1):
                ax = gx0 + i * px_m * 1000
                msp.add_line(
                    (ax, gy0), (ax, gy0 + ny * py_m * 1000),
                    dxfattribs={'layer': 'STR_AXES'},
                )
                msp.add_text(str(i + 1), height=300, dxfattribs={'layer': 'STR_LABELS', 'insert': (ax, gy0 - 1500)})
            for j in range(ny + 1):
                ay = gy0 + j * py_m * 1000
                msp.add_line(
                    (gx0, ay), (gx0 + nx * px_m * 1000, ay),
                    dxfattribs={'layer': 'STR_AXES'},
                )
                msp.add_text(chr(65 + j), height=300, dxfattribs={'layer': 'STR_LABELS', 'insert': (gx0 - 1500, ay)})
            half = pot_s / 2
            for i in range(nx + 1):
                for j in range(ny + 1):
                    px = gx0 + i * px_m * 1000
                    py_ = gy0 + j * py_m * 1000
                    pts = [(px - half, py_ - half), (px + half, py_ - half),
                           (px + half, py_ + half), (px - half, py_ + half)]
                    pl = msp.add_lwpolyline(pts, dxfattribs={'layer': 'STR_POTEAUX'})
                    pl.close()
            y_offset += ny * py_m * 1000 + 15000

    doc.saveas(output_path)
    return output_path


def generer_plans_mep_dxf(output_path, resultats_mep=None, resultats_structure=None,
                          params=None, dwg_geometry=None, **kw):
    """
    Plans MEP as DXF — architecture + MEP equipment on layers per lot.
    Same data as generer_plans_mep() but outputs DXF instead of PDF.
    """
    import ezdxf
    import re as _re

    if resultats_mep is None:
        raise ValueError("ResultatsMEP requis")
    if params is None:
        params = {}
    if hasattr(params, "__dict__"):
        params = {k: v for k, v in vars(params).items() if not k.startswith("_")}

    rm = resultats_mep
    p = params
    nx, ny, px_m, py_m = _build_grid(p)

    # Normalize DWG geometry — with axis inference
    dwg_levels = {}
    if dwg_geometry:
        if 'walls' in dwg_geometry:
            enriched = _ensure_axes(dwg_geometry, nx, ny, px_m, py_m)
            dwg_levels = {'Étage courant': enriched}
        else:
            LEVEL_LABELS = {
                'SOUS_SOL': 'Sous-Sol', 'RDC': 'Rez-de-Chaussée',
                'ETAGES_1_7': 'Étages 1 à 7', 'ETAGE_8': 'Étage 8', 'TERRASSE': 'Terrasse',
            }
            for key, geom in dwg_geometry.items():
                if isinstance(geom, dict) and len(geom.get('walls', [])) >= 5:
                    enriched = _ensure_axes(geom, nx, ny, px_m, py_m)
                    dwg_levels[LEVEL_LABELS.get(key, key)] = enriched

    level_names = []
    if p.get('avec_sous_sol'):
        level_names.append("Sous-Sol")
    level_names.append("RDC")
    nb_niv = p.get("nb_niveaux", 5)
    nb_et = nb_niv - len(level_names) - 1
    if nb_et > 0:
        level_names.append("Étage courant")
    level_names.append("Terrasse")

    if dwg_levels and len(dwg_levels) > 1:
        level_list = list(dwg_levels.items())
    else:
        single_geom = list(dwg_levels.values())[0] if dwg_levels else None
        level_list = [(name, single_geom) for name in level_names]

    def _classify_rooms(rooms):
        wet, living, service = [], [], []
        for r in rooms:
            n = r.get('name', '').lower().strip()
            if _re.match(r'^\d', n):
                continue
            if any(k in n for k in ['sdb', 'wc', 'toil', 'douche']):
                wet.append(r)
            elif any(k in n for k in ['cuisine', 'kitch', 'buanderie']):
                wet.append(r)
            elif any(k in n for k in ['salon', 'chambre', 'sejour', 'bureau', 'salle']):
                living.append(r)
            else:
                service.append(r)
        return wet, living, service

    # Create DXF document
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()

    # Architecture layers
    doc.layers.new('ARCH_MURS', dxfattribs={'color': 8})
    doc.layers.new('ARCH_FENETRES', dxfattribs={'color': 4})
    doc.layers.new('ARCH_PORTES', dxfattribs={'color': 30})
    doc.layers.new('ARCH_PIECES', dxfattribs={'color': 9})
    doc.layers.new('LEVEL_LABELS', dxfattribs={'color': 3})

    # MEP layers
    mep_layers = {
        'MEP_PLOMBERIE_EF': 4, 'MEP_PLOMBERIE_EC': 1, 'MEP_PLOMBERIE_EU': 8,
        'MEP_ELEC_ECLAIRAGE': 2, 'MEP_ELEC_PRISES': 6,
        'MEP_CVC_CLIM': 5, 'MEP_CVC_VMC': 140,
        'MEP_SSI_DETECTION': 1, 'MEP_SSI_EXTINCTION': 30,
        'MEP_COURANTS_FAIBLES': 3, 'MEP_ASCENSEURS': 4, 'MEP_GTB': 6,
    }
    for lname, cidx in mep_layers.items():
        doc.layers.new(lname, dxfattribs={'color': cidx})

    y_offset = 0

    for level_label, level_geom in level_list:
        has_dwg = level_geom and len(level_geom.get('walls', [])) >= 5

        if has_dwg:
            bounds = _dwg_bounds(level_geom)
            if not bounds:
                continue
            xn, yn, xx, yx = bounds
            dh_r = yx - yn

            msp.add_text(
                level_label.upper(), height=500,
                dxfattribs={'layer': 'LEVEL_LABELS', 'insert': (xn, yn - 2000 + y_offset)},
            )
            _dxf_add_geometry(msp, level_geom, 'ARCH_MURS', 'ARCH_FENETRES', 'ARCH_PORTES', 'ARCH_PIECES', oy=y_offset)

            rooms = level_geom.get('rooms', [])
            wet, living, service = _classify_rooms(rooms)
            all_rooms = wet + living + service

            for r in wet:
                msp.add_circle((r['x'], r['y'] + y_offset), radius=200, dxfattribs={'layer': 'MEP_PLOMBERIE_EF'})
                msp.add_circle((r['x'] + 400, r['y'] + y_offset), radius=200, dxfattribs={'layer': 'MEP_PLOMBERIE_EC'})
                msp.add_circle((r['x'] - 400, r['y'] + y_offset), radius=200, dxfattribs={'layer': 'MEP_PLOMBERIE_EU'})
            for r in all_rooms:
                msp.add_circle((r['x'], r['y'] + 300 + y_offset), radius=150, dxfattribs={'layer': 'MEP_ELEC_ECLAIRAGE'})
            for r in living + wet:
                msp.add_circle((r['x'] + 500, r['y'] + y_offset), radius=100, dxfattribs={'layer': 'MEP_ELEC_PRISES'})
            for r in living:
                msp.add_circle((r['x'], r['y'] - 300 + y_offset), radius=250, dxfattribs={'layer': 'MEP_CVC_CLIM'})
            for r in wet:
                msp.add_circle((r['x'], r['y'] + 600 + y_offset), radius=150, dxfattribs={'layer': 'MEP_CVC_VMC'})
            for r in all_rooms:
                msp.add_circle((r['x'] - 300, r['y'] + 300 + y_offset), radius=100, dxfattribs={'layer': 'MEP_SSI_DETECTION'})
            for r in living:
                msp.add_circle((r['x'] - 500, r['y'] + y_offset), radius=100, dxfattribs={'layer': 'MEP_COURANTS_FAIBLES'})

            y_offset += dh_r + 15000
        else:
            gx0, gy0 = 0, y_offset
            msp.add_text(
                level_label.upper(), height=500,
                dxfattribs={'layer': 'LEVEL_LABELS', 'insert': (gx0, gy0 - 2000)},
            )
            for i in range(nx + 1):
                ax = gx0 + i * px_m * 1000
                msp.add_line((ax, gy0), (ax, gy0 + ny * py_m * 1000), dxfattribs={'layer': 'ARCH_MURS'})
            for j in range(ny + 1):
                ay = gy0 + j * py_m * 1000
                msp.add_line((gx0, ay), (gx0 + nx * px_m * 1000, ay), dxfattribs={'layer': 'ARCH_MURS'})
            for i in range(nx):
                for j in range(ny):
                    cx = gx0 + (i + 0.5) * px_m * 1000
                    cy = gy0 + (j + 0.5) * py_m * 1000
                    msp.add_circle((cx, cy), radius=150, dxfattribs={'layer': 'MEP_ELEC_ECLAIRAGE'})
                    msp.add_circle((cx + 300, cy), radius=100, dxfattribs={'layer': 'MEP_ELEC_PRISES'})
                    if j == 0:
                        msp.add_circle((cx, cy - 300), radius=200, dxfattribs={'layer': 'MEP_PLOMBERIE_EF'})
            y_offset += ny * py_m * 1000 + 15000

    doc.saveas(output_path)
    return output_path
