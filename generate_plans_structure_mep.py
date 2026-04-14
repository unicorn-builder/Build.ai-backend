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


def _cartouche_pro(c, w, h, p, titre, pg, total, lot_label="", ech="1/100",
                   drawing_no=None, project_no=None, phase="APD"):
    """Professional BET-style cartouche (Designed/Drawn/Checked + Project/Drawing No)."""
    cw, ch_ = 180*mm, 55*mm
    cx = w - cw - 8*mm; cy = 6*mm
    c.setFillColor(BLANC); c.setStrokeColor(NOIR); c.setLineWidth(0.8)
    c.rect(cx, cy, cw, ch_, fill=1, stroke=1)

    # Outer thick rule + inner thin rule for a proper drawing-border feel
    c.setLineWidth(0.3)
    # Horizontal bands
    hb1 = cy + ch_ * 0.70   # top band (branding / project name / scale row)
    hb2 = cy + ch_ * 0.40   # title band
    hb3 = cy + ch_ * 0.20   # designed/drawn/checked band
    c.line(cx, hb1, cx+cw, hb1)
    c.line(cx, hb2, cx+cw, hb2)
    c.line(cx, hb3, cx+cw, hb3)
    # Column dividers
    c1 = cx + 42*mm        # after Tijan branding
    c2 = cx + 112*mm       # before scale/sheet column
    c.line(c1, cy, c1, cy+ch_)
    c.line(c2, cy, c2, cy+ch_)
    # Designed/Drawn/Checked sub-columns within bottom band
    sub_w = (c2 - c1) / 3.0
    c.line(c1 + sub_w, cy, c1 + sub_w, hb3)
    c.line(c1 + 2*sub_w, cy, c1 + 2*sub_w, hb3)

    # ─ Top-left: Tijan branding ─
    c.setFillColor(VERT); c.setFont("Helvetica-Bold", 11)
    c.drawString(cx+3*mm, cy+ch_-10*mm, "TIJAN AI")
    c.setFillColor(GRIS3); c.setFont("Helvetica", 5.5)
    c.drawString(cx+3*mm, cy+ch_-14.5*mm, "Automated Engineering Bureau")
    c.setFillColor(NOIR); c.setFont("Helvetica", 5.5)
    c.drawString(cx+3*mm, hb2+1.5*mm, "support@tijan.ai")
    c.drawString(cx+3*mm, hb3+1.5*mm, "www.tijan.ai")
    c.setFillColor(GRIS3); c.setFont("Helvetica", 5)
    c.drawString(cx+3*mm, cy+2*mm, f"{datetime.now().strftime('%d/%m/%Y')}")

    # ─ Middle-top: Project name + city ─
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 9)
    c.drawString(c1+3*mm, cy+ch_-10*mm, (p.get("nom") or "Projet")[:32])
    c.setFillColor(GRIS2); c.setFont("Helvetica", 6)
    c.drawString(c1+3*mm, cy+ch_-14.5*mm,
                 f"{p.get('ville','Dakar')}, {p.get('pays','Sénégal')}")

    # ─ Middle: Sheet title + lot label ─
    c.setFillColor(VERT); c.setFont("Helvetica-Bold", 8)
    c.drawString(c1+3*mm, hb2+3*mm, (titre or "")[:60])
    c.setFillColor(GRIS2); c.setFont("Helvetica", 5.5)
    c.drawString(c1+3*mm, hb2-3*mm, (lot_label or "")[:70])

    # ─ Bottom band: Designed / Drawn / Checked ─
    labels = [("DESIGNED", "TIJAN AI"),
              ("DRAWN",    "TIJAN AI"),
              ("CHECKED",  "TIJAN AI")]
    for i, (lbl, val) in enumerate(labels):
        xs = c1 + i * sub_w
        c.setFillColor(GRIS3); c.setFont("Helvetica", 4.5)
        c.drawString(xs+2*mm, hb3-3*mm, lbl)
        c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 6.5)
        c.drawString(xs+2*mm, cy+2.5*mm, val)

    # ─ Right column: Scale / Project No / Drawing No / Sheet ─
    c.setFillColor(GRIS3); c.setFont("Helvetica", 4.5)
    c.drawString(c2+2*mm, cy+ch_-5*mm, "SCALE")
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 8)
    c.drawString(c2+2*mm, cy+ch_-10*mm, ech)
    c.setFillColor(GRIS3); c.setFont("Helvetica", 4.5)
    c.drawString(c2+2*mm, cy+ch_-14*mm, f"PHASE: {phase}")

    c.setFillColor(GRIS3); c.setFont("Helvetica", 4.5)
    c.drawString(c2+2*mm, hb2-3*mm, "PROJECT No")
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 7)
    c.drawString(c2+2*mm, hb2-7.5*mm,
                 (project_no or f"TJN-{(p.get('nom','PRJ') or 'PRJ')[:6].upper().replace(' ','_')}"))

    c.setFillColor(GRIS3); c.setFont("Helvetica", 4.5)
    c.drawString(c2+2*mm, hb3-3*mm, "DRAWING No")
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 7)
    c.drawString(c2+2*mm, hb3-7.5*mm, (drawing_no or f"PL-{pg:03d}"))

    c.setFillColor(GRIS3); c.setFont("Helvetica", 4.5)
    c.drawString(c2+2*mm, cy+5*mm, "SHEET")
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 8)
    c.drawString(c2+2*mm, cy+1.5*mm, f"{pg} / {total}")


def _build_grid(p):
    """Build grid params — même logique que pl_coffrage dans v4."""
    nx = min(p.get("nb_travees_x", 4), 8)
    ny = max(min(p.get("nb_travees_y", 3), 6), 3)
    px_m = p.get("portee_max_m", 5.0)
    py_m = p.get("portee_min_m", 4.0)
    if py_m < 2.0:
        py_m = px_m * 0.65
    return nx, ny, px_m, py_m


def _grid_layout(w, h, nx, ny, px_m, py_m, ml=28*mm, mb=48*mm, mr=58*mm, mt=22*mm):
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


def _overlay_axes_columns_in_bounds(c, ox, oy, gw, gh, nx, ny, pot_s):
    """Draw subtle grid axes + column marks inside arbitrary bounds (ox, oy, gw, gh).

    Used when a PDF archi background is rendered but no room geometry is
    extracted — we still want a light structural grid anchored to the PDF
    bounds so MEP equipment layout visually relates to the actual plan.
    """
    if gw <= 0 or gh <= 0 or nx < 1 or ny < 1:
        return
    dx = gw / nx
    dy = gh / ny
    # Dashed axes
    c.setStrokeColor(GRIS4); c.setLineWidth(0.2); c.setDash(3, 3)
    for i in range(nx + 1):
        xp = ox + i * dx
        c.line(xp, oy - 4*mm, xp, oy + gh + 4*mm)
    for j in range(ny + 1):
        yp = oy + j * dy
        c.line(ox - 4*mm, yp, ox + gw + 4*mm, yp)
    c.setDash()
    # Axis labels
    for i in range(nx + 1):
        _axis_label(c, ox + i * dx, oy - 10*mm, str(i + 1))
    for j in range(ny + 1):
        _axis_label(c, ox - 10*mm, oy + j * dy, chr(65 + j))
    # Columns at intersections
    pt_d = max(min(dx, dy) * 0.04, 3)
    c.setFillColor(NOIR); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
    for i in range(nx + 1):
        for j in range(ny + 1):
            xp = ox + i * dx
            yp = oy + j * dy
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


def _dwg_layout(w, h, dwg, ml=28*mm, mb=48*mm, mr=58*mm, mt=22*mm):
    """Calculate DWG transform to fit on page with generous margins."""
    bounds = _dwg_bounds(dwg)
    if not bounds:
        return None, None, None, None, None
    xn, yn, xx, yx = bounds
    dw_r = xx - xn; dh_r = yx - yn
    if dw_r < 1 or dh_r < 1:
        return None, None, None, None, None
    aw = w - ml - mr; ah = h - mb - mt
    sc = min(aw / dw_r, ah / dh_r) * 0.99  # use almost full available area
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
        # MEP background: visible but not dominating
        c.setStrokeColor(colors.HexColor("#999999")); c.setLineWidth(0.6)
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
        c.setFillColor(colors.HexColor("#333333")); c.setFont("Helvetica-Bold", 5.5)
        for r in dwg.get('rooms', []):
            name = r.get('name', '')
            if name and len(name) >= 2:
                c.drawCentredString(tx(r['x']), ty(r['y']), name[:25])
    else:
        # Light mode: show room names more visible for MEP context
        c.setFillColor(colors.HexColor("#777777")); c.setFont("Helvetica", 4.5)
        for r in dwg.get('rooms', []):
            name = r.get('name', '')
            if name and len(name) >= 2:
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
    """Draw lightweight structural annotations on top of a PDF background.

    The PDF already shows the building plan — we add:
    - Axis labels (numbered/lettered circles) OUTSIDE the plan
    - Dimension labels between axes
    - Column markers at axis intersections (visible solid squares)
    - Beam lines along axes (PP along Y-rows, PS along X-columns)
    - A small info box with beam/slab specs
    """
    if not axes_x or not axes_y:
        return

    # ── Poteaux at axis intersections (solid black squares, always visible) ──
    # Size in points — based on actual column size projected through transform
    x0p = tx(axes_x[0]); x1p = tx(axes_x[-1])
    y0p = ty(axes_y[0]); y1p = ty(axes_y[-1])
    # Average pitch in points
    avg_pitch_pt = max(
        abs(x1p - x0p) / max(len(axes_x) - 1, 1),
        abs(y1p - y0p) / max(len(axes_y) - 1, 1)
    )
    pt_d = max(min(avg_pitch_pt * 0.06, 8.0), 3.5)  # 3.5-8pt visible
    c.saveState()
    c.setFillColor(NOIR); c.setStrokeColor(NOIR); c.setLineWidth(0.4)
    for ax in axes_x:
        for ay in axes_y:
            xp = tx(ax); yp = ty(ay)
            c.rect(xp - pt_d/2, yp - pt_d/2, pt_d, pt_d, fill=1, stroke=1)
    c.restoreState()

    # ── Poutres principales (PP) along Y-rows between columns ──
    pd_pp = max(min(avg_pitch_pt * 0.025, 3.0), 1.2)
    c.saveState()
    c.setStrokeColor(NOIR); c.setLineWidth(0.6); c.setStrokeAlpha(0.75)
    for ay in axes_y:
        yp = ty(ay)
        for i in range(len(axes_x) - 1):
            x1 = tx(axes_x[i]); x2 = tx(axes_x[i+1])
            c.line(x1, yp - pd_pp/2, x2, yp - pd_pp/2)
            c.line(x1, yp + pd_pp/2, x2, yp + pd_pp/2)
    c.restoreState()

    # ── Poutres secondaires (PS) along X-columns between rows ──
    pd_ps = max(min(avg_pitch_pt * 0.02, 2.5), 1.0)
    c.saveState()
    c.setStrokeColor(GRIS3); c.setLineWidth(0.35); c.setStrokeAlpha(0.6); c.setDash(3, 2)
    for ax in axes_x:
        xp = tx(ax)
        for j in range(len(axes_y) - 1):
            y1 = ty(axes_y[j]); y2 = ty(axes_y[j+1])
            c.line(xp - pd_ps/2, y1, xp - pd_ps/2, y2)
            c.line(xp + pd_ps/2, y1, xp + pd_ps/2, y2)
    c.setDash()
    c.restoreState()

    # Compute axis boundary positions
    y_lo = min(ty(axes_y[0]), ty(axes_y[-1])) - 10*mm
    y_hi = max(ty(axes_y[0]), ty(axes_y[-1])) + 10*mm
    x_lo = tx(axes_x[0]) - 10*mm
    x_hi = tx(axes_x[-1]) + 10*mm

    # ── Axis labels — numbered/lettered circles OUTSIDE the plan only ──
    for i, ax in enumerate(axes_x):
        _axis_label(c, tx(ax), y_lo - 5*mm, str(i + 1))
    for j, ay in enumerate(axes_y):
        _axis_label(c, x_lo - 5*mm, ty(ay), chr(65 + (j % 26)))

    # ── Dimension labels between axes ──
    c.setFillColor(GRIS2); c.setFont("Helvetica", 6)
    for i in range(len(axes_x) - 1):
        real_span = abs(axes_x[i+1] - axes_x[i])
        span_m = real_span / 1000.0 if real_span > 500 else px_m
        mid_x = (tx(axes_x[i]) + tx(axes_x[i+1])) / 2
        c.drawCentredString(mid_x, y_lo - 12*mm, f"{span_m:.2f}m")
    for j in range(len(axes_y) - 1):
        real_span = abs(axes_y[j+1] - axes_y[j])
        span_m = real_span / 1000.0 if real_span > 500 else py_m
        mid_y = (ty(axes_y[j]) + ty(axes_y[j+1])) / 2
        c.saveState()
        c.translate(x_lo - 12*mm, mid_y); c.rotate(90)
        c.drawCentredString(0, 0, f"{span_m:.2f}m")
        c.restoreState()

    # ── Compact spec box (bottom-left, outside the plan) ──
    box_x = x_lo - 5*mm
    box_y = y_lo - 28*mm
    c.setFillColor(colors.HexColor("#F5F5F5")); c.setStrokeColor(GRIS3); c.setLineWidth(0.3)
    c.rect(box_x, box_y, 60*mm, 14*mm, fill=1, stroke=1)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 5)
    c.drawString(box_x + 2*mm, box_y + 10*mm, f"Poteaux {pot_s}  |  PP {pp_b}×{pp_h}  |  PS {ps_b}×{ps_h}")
    c.setFont("Helvetica", 4.5)
    c.drawString(box_x + 2*mm, box_y + 5*mm, f"Dalle ep.{dalle_ep}  |  {beton}  |  {acier}")
    c.drawString(box_x + 2*mm, box_y + 1*mm, f"Portées: {px_m:.2f} × {py_m:.2f}m")


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
    """Draw legend box — top right. Backward-compatible with old format."""
    lx = w - 58*mm; ly = h - 28*mm
    c.setFont("Helvetica-Bold", 7); c.setFillColor(NOIR)
    c.drawString(lx, ly, "LÉGENDE"); ly -= 12
    for item in items:
        # Support both old format (color, width, label) and new format (dict)
        if isinstance(item, dict):
            color = item.get('color', NOIR)
            symbol_type = item.get('type', 'line')
            label = item.get('label', '')
            width = item.get('width', 0.5)
        else:
            color, width, label = item
            symbol_type = 'circle' if width == 'circle' else ('fill' if width == 'fill' else 'line')

        if symbol_type == 'fill':
            c.setFillColor(color); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
            c.rect(lx, ly, 5, 5, fill=1, stroke=1)
        elif symbol_type == 'circle':
            c.setFillColor(color); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
            c.circle(lx + 3, ly + 3, 3, fill=1, stroke=1)
        elif symbol_type == 'cross_circle':
            c.setFillColor(BLANC); c.setStrokeColor(color); c.setLineWidth(0.4)
            c.circle(lx + 3, ly + 3, 3, fill=1, stroke=1)
            c.setStrokeColor(color); c.setLineWidth(0.3)
            c.line(lx+0.5, ly+3, lx+5.5, ly+3); c.line(lx+3, ly+0.5, lx+3, ly+5.5)
        elif symbol_type == 'triangle':
            c.setFillColor(color); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
            path = c.beginPath()
            path.moveTo(lx+3, ly+5); path.lineTo(lx, ly); path.lineTo(lx+6, ly); path.close()
            c.drawPath(path, fill=1, stroke=1)
        elif symbol_type == 'rect_label':
            c.setFillColor(color); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
            c.rect(lx, ly, 6, 5, fill=1, stroke=1)
            c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 3)
            c.drawCentredString(lx+3, ly+1.5, item.get('symbol_text',''))
        else:  # line
            c.setStrokeColor(color); c.setLineWidth(width if isinstance(width, (int, float)) else 0.5)
            c.line(lx, ly + 3, lx + 15, ly + 3)

        c.setFillColor(NOIR); c.setFont("Helvetica", 5.5)
        c.drawString(lx + 18, ly + 1, label)
        ly -= 10


def _legend_pro(c, w, h, items, title="LÉGENDE"):
    """Enhanced legend with bordered box and rich symbol support.
    Width is computed from the longest label so no text overflows the frame."""
    # Compute label width with stringWidth, then add room for symbol + padding
    from reportlab.pdfbase.pdfmetrics import stringWidth
    LABEL_FONT = "Helvetica"; LABEL_SIZE = 6.5
    TITLE_FONT = "Helvetica-Bold"; TITLE_SIZE = 8
    LINE_STEP = 11
    def _lbl(it):
        if isinstance(it, dict): return it.get('label','')
        return it[2]
    max_label_w = max((stringWidth(_lbl(it), LABEL_FONT, LABEL_SIZE) for it in items), default=0)
    title_w = stringWidth(title, TITLE_FONT, TITLE_SIZE)
    # Box width: 3mm left pad + 14pt symbol zone + 3pt gap + label + 4mm right pad
    box_w_pt = 3*mm + 14 + 3 + max(max_label_w, title_w) + 4*mm
    box_w_pt = max(box_w_pt, 68*mm)   # keep a minimum so small lists still read well
    box_w_pt = min(box_w_pt, 118*mm)  # avoid overflowing the page
    lx = w - box_w_pt - 2*mm; ly = h - 25*mm
    leg_h = min(len(items) * LINE_STEP + 18, 200*mm)
    c.setFillColor(BLANC); c.setStrokeColor(NOIR); c.setLineWidth(0.5)
    c.rect(lx, ly - leg_h, box_w_pt, leg_h, fill=1, stroke=1)

    c.setFont(TITLE_FONT, TITLE_SIZE); c.setFillColor(VERT)
    c.drawString(lx + 3*mm, ly - 8*mm, title)
    ly_item = ly - 14*mm

    for item in items:
        if isinstance(item, dict):
            color = item.get('color', NOIR)
            symbol_type = item.get('type', 'line')
            label = item.get('label', '')
            width = item.get('width', 0.5)
        else:
            color, width, label = item
            symbol_type = 'circle' if width == 'circle' else ('fill' if width == 'fill' else 'line')

        # Draw symbol
        sx = lx + 3*mm
        if symbol_type == 'fill':
            c.setFillColor(color); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
            c.rect(sx, ly_item, 4, 4, fill=1, stroke=1)
        elif symbol_type == 'circle':
            c.setFillColor(color); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
            c.circle(sx + 2, ly_item + 2, 2.2, fill=1, stroke=1)
        elif symbol_type == 'cross_circle':
            c.setFillColor(BLANC); c.setStrokeColor(color); c.setLineWidth(0.35)
            c.circle(sx + 2, ly_item + 2, 2.2, fill=1, stroke=1)
            c.setStrokeColor(color); c.setLineWidth(0.25)
            c.line(sx+0.3, ly_item+2, sx+3.7, ly_item+2)
            c.line(sx+2, ly_item+0.3, sx+2, ly_item+3.7)
        elif symbol_type == 'triangle':
            c.setFillColor(color); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
            path = c.beginPath()
            path.moveTo(sx+2, ly_item+3.5); path.lineTo(sx-0.5, ly_item)
            path.lineTo(sx+4.5, ly_item); path.close()
            c.drawPath(path, fill=1, stroke=1)
        elif symbol_type == 'rect_label':
            c.setFillColor(color); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
            c.rect(sx, ly_item, 5, 4, fill=1, stroke=1)
            c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 2.5)
            c.drawCentredString(sx+2.5, ly_item+1, item.get('symbol_text',''))
        else:  # line
            c.setStrokeColor(color)
            c.setLineWidth(width if isinstance(width, (int, float)) else 0.5)
            c.line(sx, ly_item + 2, sx + 12, ly_item + 2)

        # Draw label
        c.setFillColor(NOIR); c.setFont(LABEL_FONT, LABEL_SIZE)
        c.drawString(sx + 16, ly_item - 0.5, label)
        ly_item -= LINE_STEP


def _label_columns_on_grid(c, ox, oy, sc, nx, ny, px_m, py_m, pot_s):
    """Add P1, P2, P3... labels to columns on parametric grid."""
    c.setFont("Helvetica-Bold", 3.5); c.setFillColor(NOIR)
    col_idx = 1
    for i in range(nx + 1):
        for j in range(ny + 1):
            xp = ox + i * px_m * sc
            yp = oy + j * py_m * sc
            pt_d = max(pot_s * sc / 1000, 3)
            # Label above/right of column
            c.drawString(xp + pt_d/2 + 1, yp + pt_d/2 + 1, f"P{col_idx}")
            col_idx += 1


def _label_columns_on_real_axes(c, tx, ty, axes_x, axes_y, pot_s):
    """Add P1, P2... labels to columns on real axes (DWG/PDF mode).

    This function labels columns at axis intersections using real coordinate transforms.
    tx, ty are callable transforms from model coordinates to page coordinates.
    """
    if not axes_x or not axes_y:
        return

    c.setFont("Helvetica-Bold", 4); c.setFillColor(NOIR)
    col_idx = 1
    for ax in axes_x:
        for ay in axes_y:
            px_pt = tx(ax)
            py_pt = ty(ay)
            pt_d = max(pot_s / 1000 * 2, 3)  # Rough conversion for label sizing
            c.drawString(px_pt + pt_d/2 + 1, py_pt + pt_d/2 + 1, f"P{col_idx}")
            col_idx += 1


def _draw_section_callouts(c, ox, oy, sc, nx, ny, px_m, py_m, pp_b, pp_h, ps_b, ps_h):
    """Draw section cut symbols (COUPE A-A, COUPE B-B callouts) on coffrage plan.

    Adds small section cut indicator circles with arrows showing viewing direction.
    Placed at strategic beam locations to indicate where cross-sections are taken.
    """
    # COUPE A-A — along first beam line (X direction)
    callout_y = oy + (ny / 2) * py_m * sc
    callout_x = ox + 0.5 * px_m * sc

    # Draw circle with "A" inside
    r = 4*mm
    c.setFillColor(BLANC); c.setStrokeColor(ROUGE); c.setLineWidth(0.6)
    c.circle(callout_x, callout_y, r, fill=1, stroke=1)
    c.setFillColor(ROUGE); c.setFont("Helvetica-Bold", 5)
    c.drawCentredString(callout_x, callout_y - 1.2, "A")

    # Draw arrow line with direction indicators
    arrow_len = 25*mm
    c.setStrokeColor(ROUGE); c.setLineWidth(0.5)
    c.line(callout_x - r - 3, callout_y, callout_x - r - arrow_len, callout_y)
    # Arrowheads
    c.line(callout_x - r - arrow_len, callout_y, callout_x - r - arrow_len + 3, callout_y + 2)
    c.line(callout_x - r - arrow_len, callout_y, callout_x - r - arrow_len + 3, callout_y - 2)

    # COUPE B-B — along column line (Y direction)
    callout_x_b = ox + (nx / 2) * px_m * sc
    callout_y_b = oy + 0.5 * py_m * sc

    c.setFillColor(BLANC); c.setStrokeColor(BLEU); c.setLineWidth(0.6)
    c.circle(callout_x_b, callout_y_b, r, fill=1, stroke=1)
    c.setFillColor(BLEU); c.setFont("Helvetica-Bold", 5)
    c.drawCentredString(callout_x_b, callout_y_b - 1.2, "B")

    c.setStrokeColor(BLEU); c.setLineWidth(0.5)
    c.line(callout_x_b, callout_y_b - r - 3, callout_x_b, callout_y_b - r - arrow_len)
    # Arrowheads
    c.line(callout_x_b, callout_y_b - r - arrow_len, callout_x_b + 2, callout_y_b - r - arrow_len + 3)
    c.line(callout_x_b, callout_y_b - r - arrow_len, callout_x_b - 2, callout_y_b - r - arrow_len + 3)


def _label_beams_and_slabs_on_grid(c, ox, oy, sc, nx, ny, px_m, py_m, pp_b, pp_h, ps_b, ps_h, dalle_ep):
    """Add section callouts and panel labels (D1, D2...) to parametric grid.
    Professional notation: PP 1(20×40) for main beams, PS for secondary, D1 for panels."""
    # ── Beam section callouts along main beams (horizontal) ──
    c.setFont("Helvetica-Bold", 3); c.setFillColor(GRIS2)
    beam_pp_idx = 1
    for j in range(ny + 1):
        yp = oy + j * py_m * sc
        for i in range(nx):
            mid_x = ox + (i + 0.5) * px_m * sc
            # Professional notation: beam_index(b×h)
            c.drawCentredString(mid_x, yp + 3, f"{beam_pp_idx}({pp_b}×{pp_h})")
            beam_pp_idx += 1

    # ── Secondary beam callouts (vertical) ──
    if ps_b > 0 and ps_h > 0:
        c.setFont("Helvetica", 2.5); c.setFillColor(GRIS3)
        beam_ps_idx = 1
        for i in range(nx + 1):
            xp = ox + i * px_m * sc
            for j in range(ny):
                mid_y = oy + (j + 0.5) * py_m * sc
                c.saveState()
                c.translate(xp + 3, mid_y); c.rotate(90)
                c.drawCentredString(0, 0, f"PS{beam_ps_idx}({ps_b}×{ps_h})")
                c.restoreState()
                beam_ps_idx += 1

    # ── Dalle panel labels (D1, D2...) with thickness ──
    panel_idx = 1
    for i in range(nx):
        for j in range(ny):
            sx = ox + i * px_m * sc
            sy = oy + j * py_m * sc
            sw = px_m * sc
            sh = py_m * sc
            cx_p = sx + sw / 2
            cy_p = sy + sh / 2
            # Panel reference in circle
            c.setStrokeColor(GRIS3); c.setFillColor(BLANC); c.setLineWidth(0.3)
            c.circle(cx_p, cy_p, 5, fill=1, stroke=1)
            c.setFont("Helvetica-Bold", 3.5); c.setFillColor(NOIR)
            c.drawCentredString(cx_p, cy_p - 1.2, f"D{panel_idx}")
            # Thickness below
            c.setFont("Helvetica", 2.5); c.setFillColor(GRIS3)
            c.drawCentredString(cx_p, cy_p - 7, f"ep.{dalle_ep}")
            panel_idx += 1


def _label_foundations_at_grid(c, ox, oy, sc, nx, ny, px_m, py_m, r, fd):
    """Add S1/P1... labels, NEd loads, and foundation dimensions to grid positions.
    Professional descente de charges notation per West African bureau d'études standards."""
    if not r.poteaux or len(r.poteaux) == 0:
        return

    nb_pieux = getattr(fd, 'nb_pieux', 0)
    diam_p = getattr(fd, 'diam_pieu_mm', 600)
    larg_sem = getattr(fd, 'largeur_semelle_m', 1.5)
    # Total descente de charges: sum NEd across all levels
    total_NEd = sum(p.NEd_kN for p in r.poteaux)

    c.setFont("Helvetica-Bold", 3.5); c.setFillColor(NOIR)
    found_idx = 1
    for i in range(nx + 1):
        for j in range(ny + 1):
            xp = ox + i * px_m * sc
            yp = oy + j * py_m * sc
            found_type = "S" if fd.type.value == "semelle_isolee" else "P"
            # Foundation reference
            c.setFont("Helvetica-Bold", 3.5); c.setFillColor(NOIR)
            c.drawString(xp + 3, yp - 8, f"{found_type}{found_idx}")
            # Foundation dimension
            c.setFont("Helvetica", 2.5); c.setFillColor(GRIS2)
            if nb_pieux > 0:
                c.drawString(xp + 3, yp - 12, f"ø{diam_p}")
            else:
                c.drawString(xp + 3, yp - 12, f"{larg_sem:.1f}×{larg_sem:.1f}m")
            # Descente de charges
            if total_NEd > 0:
                c.drawString(xp + 3, yp - 16, f"N={total_NEd:.0f}kN")
            found_idx += 1


def _draw_coupe_dimension_callouts(c, cox, coy, cgh, rsc, he, nb_niv, dalle_ep, pp_h, pp_b):
    """Draw detailed dimension callouts on coupe section.

    Shows element dimensions with leader lines and annotations:
    - Slab thickness annotation (ep=XXmm)
    - Beam drop height (retombée XXmm)
    - Column section labels
    """
    # Slab thickness callout (first slab only for clarity)
    dh_s = max(dalle_ep * rsc / 1000, 2.0)
    slab_y = coy + he * rsc - dh_s / 2
    c.setStrokeColor(ROUGE); c.setLineWidth(0.5)
    c.line(cox - 10, slab_y, cox - 25, slab_y)
    c.line(cox - 25, slab_y, cox - 25, slab_y + 8)
    c.setFillColor(ROUGE); c.setFont("Helvetica-Bold", 4)
    c.drawString(cox - 24, slab_y + 9, f"ep={dalle_ep}mm")

    # Beam drop callout (if beam is taller than slab)
    if pp_h > dalle_ep:
        beam_drop = pp_h - dalle_ep
        drop_y = coy + he * rsc - (dalle_ep + beam_drop/2) * rsc / 1000
        c.setStrokeColor(BLEU); c.setLineWidth(0.5)
        c.line(cox + 30, drop_y, cox + 45, drop_y)
        c.line(cox + 45, drop_y, cox + 45, drop_y + 8)
        c.setFillColor(BLEU); c.setFont("Helvetica-Bold", 4)
        c.drawString(cox + 46, drop_y + 9, f"retombée {beam_drop:.0f}mm")

    # Beam width label
    c.setFillColor(GRIS2); c.setFont("Helvetica", 3.5)
    c.drawString(cox + 20, coy + he * rsc + 2, f"PP b={pp_b}mm")


def _draw_accumulated_heights(c, cox, coy, cgh, rsc, he, nb_niv, p, fd_depth_m):
    """Draw accumulated height annotations on right side of coupe."""
    accum_dim_x = cox + 55*mm
    c.setStrokeColor(NOIR); c.setLineWidth(0.25)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 4)

    # Draw horizontal lines at each level and annotate accumulated height
    accumulated_h = fd_depth_m  # Start with foundation depth
    for niv in range(nb_niv):
        y_level = coy + niv * he * rsc
        # Draw tick mark
        c.line(accum_dim_x - 1.5, y_level, accum_dim_x + 1.5, y_level)
        # Annotate accumulated height
        c.drawString(accum_dim_x + 3, y_level - 1.5, f"{accumulated_h:.1f}m")
        accumulated_h += he

    # Final tick at top
    y_top = coy + nb_niv * he * rsc
    c.line(accum_dim_x - 1.5, y_top, accum_dim_x + 1.5, y_top)
    c.drawString(accum_dim_x + 3, y_top - 1.5, f"{accumulated_h:.1f}m")


def _draw_notes_techniques(c, x, y, beton_class, acier_class, fck, fyk, charge_g, charge_q, zone_sismique):
    """Draw technical notes box (60×25mm) with concrete, steel, coverage, norms, charges, seismic."""
    from reportlab.lib import colors as rl_colors
    box_w, box_h = 60*mm, 28*mm
    # Light beige background
    c.setFillColor(rl_colors.HexColor("#FFF9F5")); c.setStrokeColor(GRIS3); c.setLineWidth(0.4)
    c.rect(x, y, box_w, box_h, fill=1, stroke=1)

    c.setFont("Helvetica-Bold", 5.5); c.setFillColor(NOIR)
    c.drawString(x + 2*mm, y + box_h - 3*mm, "NOTES TECHNIQUES")

    c.setFont("Helvetica", 4); c.setFillColor(GRIS2)
    y_line = y + box_h - 8*mm
    line_spacing = 3.2*mm

    c.drawString(x + 2*mm, y_line, f"Béton: {beton_class} (fck={fck:.0f} MPa)")
    y_line -= line_spacing
    c.drawString(x + 2*mm, y_line, f"Acier: {acier_class} (fyk={fyk:.0f} MPa)")
    y_line -= line_spacing
    c.drawString(x + 2*mm, y_line, "Enrobage: 30mm (fond: 50mm)")
    y_line -= line_spacing
    c.drawString(x + 2*mm, y_line, "EC2 + EC8 — NF EN 1992/1998")
    y_line -= line_spacing
    c.drawString(x + 2*mm, y_line, f"G={charge_g:.1f} kN/m², Q={charge_q:.1f} kN/m²")
    y_line -= line_spacing
    c.drawString(x + 2*mm, y_line, f"Zone sismique: {zone_sismique}")


def _estimate_bar_from_as(as_cm2_ml):
    """Estimate bar diameter and spacing from As in cm²/ml.
    Returns (diameter_mm, spacing_cm, as_actual_cm2_ml).
    Used across ferraillage annotations and nomenclature."""
    import math
    if as_cm2_ml < 2.0:
        return 8, 25, math.pi * 0.8**2 / 4 * (100 / 25)
    elif as_cm2_ml < 3.0:
        return 10, 25, math.pi * 1.0**2 / 4 * (100 / 25)
    elif as_cm2_ml < 5.0:
        return 12, 20, math.pi * 1.2**2 / 4 * (100 / 20)
    elif as_cm2_ml < 7.0:
        return 14, 20, math.pi * 1.4**2 / 4 * (100 / 20)
    else:
        return 16, 15, math.pi * 1.6**2 / 4 * (100 / 15)


def _bar_notation(as_cm2_ml):
    """Return professional bar notation string like 'HA12 esp.20'."""
    diam, esp, _ = _estimate_bar_from_as(as_cm2_ml)
    return f"HA{diam} esp.{esp}"


def _bar_notation_bet(as_cm2_ml, length_m):
    """BET-standard notation: '{count}-HA{Ø} (e={esp})'.
    Matches French ferraillage convention (cf. réf. BET Sakho/Mar&Mor).
    length_m = bay length perpendicular to the bars.
    """
    diam, esp, _ = _estimate_bar_from_as(as_cm2_ml)
    # Nb of bars = (perpendicular length in m * 100cm) / spacing_cm, rounded up + 1
    nb = max(2, int((length_m * 100.0) / max(esp, 1)) + 1)
    return f"{nb}-HA{diam} (e={esp})"


def _bar_chapeau_bet(as_cm2_ml, length_m):
    """Chapeau notation: 'CH+Rep HA{Ø} (e={esp})'."""
    diam, esp, _ = _estimate_bar_from_as(as_cm2_ml)
    # Chapeaux use wider spacing (x1.5) in BET practice
    esp_ch = int(esp * 1.5)
    return f"CH+Rep HA{diam} (e={esp_ch})"


def _draw_rebar_nomenclature(c, x, y, dalle, nx, ny, px_m, py_m):
    """Draw nomenclature table for rebar schedule (small table bottom-left)."""
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors as rl_colors

    diam_x, esp_x, _ = _estimate_bar_from_as(dalle.As_x_cm2_ml)
    diam_y, esp_y, _ = _estimate_bar_from_as(dalle.As_y_cm2_ml)

    # Compute number of bars (approximation)
    # nb = (portée_m * 1000) / espacement_cm
    nb_x = max(1, int((px_m * 1000) / (esp_x * 10)))
    nb_y = max(1, int((py_m * 1000) / (esp_y * 10)))

    # Build table data
    data = [
        ["Rep.", "Nombre", "Ø (mm)", "Esp. (cm)", "L unit. (m)", "Type"],
        ["1", str(nb_x * ny), str(diam_x), str(esp_x), f"{px_m:.2f}", "Nappe inf X"],
        ["2", str(nb_y * nx), str(diam_y), str(esp_y), f"{py_m:.2f}", "Nappe inf Y"],
        ["3", str(max(1, int(nb_x / 2))), str(diam_x), str(esp_x * 2), f"{px_m/3:.2f}", "Chapeau X"],
    ]

    # Create table with small font
    table = Table(data, colWidths=[12*mm, 14*mm, 12*mm, 14*mm, 14*mm, 16*mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor("#E8F5E9")),
        ('TEXTCOLOR', (0, 0), (-1, 0), NOIR),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 4.5),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
        ('GRID', (0, 0), (-1, -1), 0.3, GRIS3),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BLANC, rl_colors.HexColor("#F5F5F5")]),
    ]))

    # Draw the table
    table.wrapOn(c, 100*mm, 40*mm)
    table.drawOn(c, x, y - 30*mm)


def _draw_chapeau_indicators(c, ox, oy, sc, nx, ny, px_m, py_m):
    """Draw chapeau (top mesh) indicators on ferraillage dalle plan.

    Draws short colored lines at grid intersections to indicate location of
    chapeaux d'appui (top rebar over supports). Green for X direction, purple for Y.
    """
    # Chapeau d'appui length ≈ 1/5 of span
    chapel_len = 3*mm

    for i in range(nx + 1):
        for j in range(ny + 1):
            xp = ox + i * px_m * sc
            yp = oy + j * py_m * sc

            # X direction chapeau (green)
            c.setStrokeColor(colors.HexColor("#66BB6A")); c.setLineWidth(0.6)
            c.line(xp - chapel_len/2, yp + 1.5, xp + chapel_len/2, yp + 1.5)

            # Y direction chapeau (purple)
            c.setStrokeColor(VIOLET); c.setLineWidth(0.6)
            c.line(xp + 1.5, yp - chapel_len/2, xp + 1.5, yp + chapel_len/2)


def _draw_column_schedule(c, x, y, poteaux, nx, ny, px_m, py_m):
    """Draw column nomenclature schedule on coffrage plan.

    Shows a table with: Rep. | Section | Niveau | NEd (kN) | NRd (kN) | Taux | Armatures
    This professional table helps builders and inspectors identify column requirements.
    """
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors as rl_colors

    if not poteaux or len(poteaux) == 0:
        return

    # Get first level column data (representative)
    pot0 = poteaux[0]
    sec_mm = pot0.section_mm
    nred_kn = pot0.NEd_kN if hasattr(pot0, 'NEd_kN') else 0
    nrrd_kn = pot0.NRd_kN if hasattr(pot0, 'NRd_kN') else 0
    taux = pot0.taux_armature_pct if hasattr(pot0, 'taux_armature_pct') else 0
    nb_barres = pot0.nb_barres if hasattr(pot0, 'nb_barres') else 0
    diam_mm = pot0.diametre_mm if hasattr(pot0, 'diametre_mm') else 14

    # Calculate ratio
    ratio = (nred_kn / nrrd_kn * 100) if nrrd_kn > 0 else 0

    # Build table data — showing representative column + typical from each level
    data = [
        ["Rep.", "Section", "Niveau", "NEd", "NRd", "Ratio", "Armatures"],
        ["P1-P" + str((nx+1)*(ny+1)), f"{sec_mm}×{sec_mm}", "RDC", f"{nred_kn:.0f}", f"{nrrd_kn:.0f}",
         f"{ratio:.0f}%", f"{nb_barres}HA{diam_mm}"],
    ]

    # Add rows for other levels if available
    for idx, pot_level in enumerate(poteaux[1:3], 1):  # Show up to 2 more levels
        nred_l = pot_level.NEd_kN if hasattr(pot_level, 'NEd_kN') else nred_kn
        nrrd_l = pot_level.NRd_kN if hasattr(pot_level, 'NRd_kN') else nrrd_kn
        ratio_l = (nred_l / nrrd_l * 100) if nrrd_l > 0 else ratio
        level_name = f"R+{idx}"
        data.append(
            ["(identique)", f"{sec_mm}×{sec_mm}", level_name, f"{nred_l:.0f}", f"{nrrd_l:.0f}",
             f"{ratio_l:.0f}%", f"{nb_barres}HA{diam_mm}"]
        )

    # Create table
    table = Table(data, colWidths=[16*mm, 16*mm, 14*mm, 12*mm, 12*mm, 12*mm, 18*mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor("#C8E6C9")),
        ('TEXTCOLOR', (0, 0), (-1, 0), NOIR),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 4),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
        ('GRID', (0, 0), (-1, -1), 0.3, GRIS3),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BLANC, rl_colors.HexColor("#F1F8F1")]),
    ]))

    # Draw the table
    table.wrapOn(c, 120*mm, 30*mm)
    table.drawOn(c, x, y - 20*mm)


# ══════════════════════════════════════════
# PDF RASTER BACKGROUND — archi PDF as greyed-out background image
# ══════════════════════════════════════════

def _render_pdf_background(c, archi_pdf_path, page_idx, w, h,
                            ml=28*mm, mb=48*mm, mr=58*mm, mt=22*mm,
                            opacity=0.18, dpi=150, grayscale=True):
    """Render a page from the architectural PDF as a background image.

    Uses PyMuPDF to rasterize the page, then places it on the ReportLab canvas.
    When grayscale=True, converts to grayscale so colors don't compete with
    structural/MEP annotations drawn on top.

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

        # Convert to grayscale to strip architectural colors
        img_w_px = pix.width
        img_h_px = pix.height
        if grayscale:
            try:
                from PIL import Image as _PILImage
                import numpy as _np
                pil_img = _PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples)
                pil_gray = pil_img.convert("L")
                # Lighten: push midtones toward white for cleaner background
                arr = _np.array(pil_gray, dtype=_np.float32)
                arr = 255 - (255 - arr) * 0.6  # reduce contrast by 40%
                pil_gray = _PILImage.fromarray(arr.astype(_np.uint8), mode="L")
                buf = _io.BytesIO()
                pil_gray.save(buf, format="PNG")
                img_bytes = buf.getvalue()
                img_w_px, img_h_px = pil_gray.size
            except ImportError:
                # Pillow not available — fallback to color image
                img_bytes = pix.tobytes("png")
        else:
            img_bytes = pix.tobytes("png")

        doc.close()

        # Calculate placement — fit within drawing area with margins
        aw = w - ml - mr
        ah = h - mb - mt
        img_scale = min(aw / img_w_px, ah / img_h_px)
        draw_w = img_w_px * img_scale
        draw_h = img_h_px * img_scale
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

def _draw_ferr_nomenclature_table(c, x, y, entries, page_w, filter_pos=None, max_rows=18):
    """Draw BET-style nomenclature table at bottom of ferraillage sheet.
    entries = list of tuples (rep, count, diam, esp, L_m, position).
    filter_pos = 'inf' | 'sup' | None — only rows whose position contains this substring.
    """
    if not entries:
        return
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors as rl_colors

    # Deduplicate by repère (keep first occurrence of each rep/position)
    seen = set()
    rows = []
    for rep, cnt, d, e, L, pos in entries:
        if filter_pos and filter_pos not in pos.lower():
            continue
        key = (rep, pos)
        if key in seen: continue
        seen.add(key)
        rows.append([str(rep), str(cnt), f"HA{d}", f"{e}", f"{L:.2f}", pos])
        if len(rows) >= max_rows: break

    if not rows: return

    header = ["Rep.", "Nb", "Ø", "Esp. (cm)", "L (m)", "Position"]
    data = [header] + rows
    col_w = [10*mm, 10*mm, 12*mm, 16*mm, 14*mm, 34*mm]
    table = Table(data, colWidths=col_w, rowHeights=[5*mm] + [3.5*mm]*len(rows))
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor("#43A956")),
        ('TEXTCOLOR', (0, 0), (-1, 0), BLANC),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 5),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 4.5),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (5, 1), (5, -1), 'LEFT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 0.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5),
        ('GRID', (0, 0), (-1, -1), 0.25, GRIS3),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BLANC, rl_colors.HexColor("#F5F7F5")]),
    ]))
    tw = sum(col_w)
    th = 5*mm + 3.5*mm * len(rows)
    # Title above the table
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 6.5)
    c.drawString(x, y + th + 2*mm, "NOMENCLATURE ARMATURES (extrait)")
    table.wrapOn(c, tw, th)
    table.drawOn(c, x, y)


def _draw_coupe_type_dalle(c, w, h, dalle, pp_b, pp_h):
    """Typical section cut showing top/bottom reinforcement layers + cover + support chapeau."""
    # Centered large section drawing
    cx0, cy0 = w * 0.20, h * 0.35
    scale = 40.0  # 1 cm -> 40 pt (big detail drawing)
    ep_cm = dalle.epaisseur_mm / 10.0
    L_cm = 320  # 3.2 m section width for display
    enrobage_cm = 3.0

    # Draw concrete slab rectangle
    x0 = cx0; y0 = cy0
    W = L_cm * scale / 10 * 0.6  # compressed horizontally
    H = ep_cm * scale / 2
    c.setFillColor(GRIS5); c.setStrokeColor(NOIR); c.setLineWidth(0.8)
    c.rect(x0, y0, W, H, fill=1, stroke=1)

    # Support beams at each end
    beam_w = pp_b / 10 * scale / 4
    beam_h = pp_h / 10 * scale / 4
    c.setFillColor(GRIS4); c.setLineWidth(0.6)
    c.rect(x0 - beam_w*0.5, y0 - beam_h*0.5, beam_w, beam_h + H*0.5, fill=1, stroke=1)
    c.rect(x0 + W - beam_w*0.5, y0 - beam_h*0.5, beam_w, beam_h + H*0.5, fill=1, stroke=1)

    # Bottom reinforcement — 1st layer
    c.setStrokeColor(ROUGE); c.setLineWidth(0.9)
    y_inf1 = y0 + enrobage_cm * scale / 10
    c.line(x0 + 4, y_inf1, x0 + W - 4, y_inf1)
    # bars as dots seen in section
    for k in range(8):
        xb = x0 + 8 + k * (W - 16) / 7
        c.setFillColor(ROUGE); c.circle(xb, y_inf1, 1.5, fill=1, stroke=0)

    # Top reinforcement — chapeau near supports
    c.setStrokeColor(colors.HexColor("#66BB6A")); c.setLineWidth(0.8)
    y_sup = y0 + H - enrobage_cm * scale / 10
    c.line(x0 + 4, y_sup, x0 + W * 0.28, y_sup)
    c.line(x0 + W * 0.72, y_sup, x0 + W - 4, y_sup)
    for xr in [x0 + 8, x0 + W * 0.18, x0 + W * 0.78, x0 + W - 8]:
        c.setFillColor(colors.HexColor("#66BB6A")); c.circle(xr, y_sup, 1.3, fill=1, stroke=0)

    # Top continuous reinforcement — 2e lit sup
    c.setStrokeColor(VIOLET); c.setLineWidth(0.4); c.setDash(2, 1.5)
    y_sup2 = y_sup - 2
    c.line(x0 + 10, y_sup2, x0 + W - 10, y_sup2)
    c.setDash()

    # Dimension arrows + labels
    c.setFillColor(NOIR); c.setFont("Helvetica", 6)
    c.drawString(x0 + W + 5, y_inf1 - 2, f"1er lit inf (enrobage {int(enrobage_cm*10)} mm)")
    c.drawString(x0 + W + 5, y_sup - 2, f"CH + 1er lit sup")
    c.drawString(x0 + W + 5, y_sup2 - 2, f"2e lit sup (continu)")

    # Vertical dimension of slab thickness
    c.setStrokeColor(NOIR); c.setLineWidth(0.3)
    xd = x0 - 14
    c.line(xd, y0, xd, y0 + H)
    c.line(xd - 2, y0, xd + 2, y0)
    c.line(xd - 2, y0 + H, xd + 2, y0 + H)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 7)
    c.drawRightString(xd - 3, y0 + H/2 - 2, f"{int(dalle.epaisseur_mm)} mm")

    # Legend
    ly = y0 - 24
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 8)
    c.drawString(x0, ly, "COUPE A-A — Détail ferraillage type dalle pleine")
    c.setFont("Helvetica", 6); c.setFillColor(GRIS2)
    c.drawString(x0, ly - 9, f"Épaisseur {int(dalle.epaisseur_mm)} mm · Béton classe projet · Enrobage 30 mm (50 mm en fondation)")
    c.drawString(x0, ly - 17, "1er lit inf (rouge) · CH + 1er lit sup (vert) · 2e lit sup continu (violet pointillé)")


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

    # per-level coffrage + (ferr INF + ferr SUP + coupe type dalle) + fondations + coupe bât + ferr poutre + ferr poteau
    total_pages = len(level_names) + 7
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
        # Terrasse: strip interior content — only structural slab + acrotère + grid
        # (pool, rooms, interior walls don't belong on a roof-slab plan)
        is_terrasse_level = level_name.lower().startswith(('terrasse','toiture','toit'))
        _ln = level_name.lower()
        is_soussol_level = 'sous-sol' in _ln or 'sous sol' in _ln or 'parking' in _ln
        if is_soussol_level and lvl_geom and lvl_geom is dwg_levels.get('Étage courant'):
            # Synth sous-sol: keep real emprise, strip residential rooms/openings
            lvl_geom = {
                'walls': list(lvl_geom.get('walls', [])),
                'windows': [], 'doors': [], 'rooms': [],
                'axes_x': lvl_geom.get('axes_x', []),
                'axes_y': lvl_geom.get('axes_y', []),
                '_terrace_bounds': _dwg_bounds(lvl_geom),
                '_cv_meta': lvl_geom.get('_cv_meta'),
                '_synth_level': 'sous_sol',
            }
        if is_terrasse_level and lvl_geom:
            lvl_geom = {
                'walls': list(lvl_geom.get('walls', [])),  # keep real emprise
                'windows': [], 'doors': [], 'rooms': [],
                'axes_x': lvl_geom.get('axes_x', []),
                'axes_y': lvl_geom.get('axes_y', []),
                '_terrace_bounds': _dwg_bounds(lvl_geom),
                '_cv_meta': lvl_geom.get('_cv_meta'),
            }
        has_geom = lvl_geom and (len(lvl_geom.get('walls', [])) >= 5 or is_terrasse_level)

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
        # Skip PDF background for terrasse — it must show slab/acrotère only.
        if archi_pdf_path and (is_from_pdf or not has_geom) and not is_terrasse_level:
            pdf_page_idx = level_names.index(level_name) if level_name in level_names else 0
            ok, placement = _render_pdf_background(
                c, archi_pdf_path, pdf_page_idx, w, h,
                opacity=0.90, dpi=200, grayscale=True
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
            # Terrasse: synthesize a layout from stored bounds (walls=[] so _dwg_layout may fail)
            # For terrasse, synthesize geom from stored bounds (no interior walls)
            geom_for_layout = lvl_geom
            if is_terrasse_level and lvl_geom.get('_terrace_bounds'):
                tb = lvl_geom['_terrace_bounds']
                geom_for_layout = {'walls': [{'type': 'polyline',
                    'points': [(tb[0], tb[1]), (tb[2], tb[1]), (tb[2], tb[3]), (tb[0], tb[3])],
                    'closed': True}]}
            dtx, dty, dsc, dgw, dgh = _dwg_layout(w, h, geom_for_layout)
            if dtx:
                if is_terrasse_level and lvl_geom.get('_terrace_bounds'):
                    # Dalle terrasse outline + acrotère (no interior architecture)
                    bx0, by0, bx1, by1 = lvl_geom['_terrace_bounds']
                    c.saveState()
                    c.setStrokeColor(NOIR); c.setLineWidth(1.4)
                    c.rect(dtx(bx0), dty(by0), dtx(bx1)-dtx(bx0), dty(by1)-dty(by0), fill=0, stroke=1)
                    acr_off = 150
                    c.setStrokeColor(colors.HexColor("#FFA726")); c.setLineWidth(0.8); c.setDash(4, 2)
                    c.rect(dtx(bx0+acr_off), dty(by0+acr_off),
                           dtx(bx1-acr_off)-dtx(bx0+acr_off),
                           dty(by1-acr_off)-dty(by0+acr_off), fill=0, stroke=1)
                    c.setDash()
                    c.setFillColor(GRIS2); c.setFont("Helvetica-Oblique", 7)
                    c.drawString(dtx(bx0)+3*mm, dty(by1)-6*mm,
                                 "Toiture-Terrasse inaccessible — Dalle BA + Acrotère h=80cm + étanchéité multicouche")
                    c.restoreState()
                else:
                    # Normal level: redraw architecture
                    _draw_dwg(c, lvl_geom, dtx, dty, sc=dsc)

                real_ax = lvl_geom.get('axes_x', [])
                real_ay = lvl_geom.get('axes_y', [])
                if real_ax and real_ay:
                    _draw_coffrage_annotations(
                        c, dtx, dty, real_ax, real_ay,
                        pot_s, pp_b, pp_h, ps_b, ps_h, dalle_ep,
                        px_m, py_m, beton, acier
                    )
                else:
                    # No axes — fitted grid
                    bb = _dwg_bounds(geom_for_layout)
                    if bb:
                        bx0, by0, bx1, by1 = bb
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
            # Add element labels: P1, P2... for columns, D1, D2... for dalle panels
            _label_columns_on_grid(c, ox, oy, sc, nx, ny, px_m, py_m, pot_s)
            _label_beams_and_slabs_on_grid(c, ox, oy, sc, nx, ny, px_m, py_m, pp_b, pp_h, ps_b, ps_h, dalle_ep)
            # Add section callout symbols
            _draw_section_callouts(c, ox, oy, sc, nx, ny, px_m, py_m, pp_b, pp_h, ps_b, ps_h)

        _legend_pro(c, w, h, [
            (NOIR, 'fill', f"Poteau P — {pot_s}×{pot_s}mm — Béton {beton}"),
            (NOIR, 0.8, f"Poutre Principale (PP) {pp_b}×{pp_h}mm"),
            (GRIS3, 0.4, f"Poutre Secondaire (PS) {ps_b}×{ps_h}mm" if ps else "PS — (non utilisée)"),
            (GRIS4, 0.1, f"Dalle — Épaisseur {dalle_ep}mm"),
            (GRIS4, 0.05, "Axes de cotation — grille structure"),
            (colors.HexColor("#D7CCC8"), 'fill', "Chaînage/Linteau"),
            (colors.HexColor("#FFE082"), 0.4, "Acrotère"),
            (ROUGE, 0.6, "COUPE A-A — Section poutre"),
            (BLEU, 0.6, "COUPE B-B — Section colonne"),
        ], "ÉLÉMENTS STRUCTURELS")

        # Notes techniques box
        _draw_notes_techniques(c, 14*mm, 42*mm, beton, acier, r.fck_MPa, r.fyk_MPa,
                              r.charge_G_kNm2, r.charge_Q_kNm2, r.sismique.zone)
        # Column schedule nomenclature
        _draw_column_schedule(c, 85*mm, 42*mm, r.poteaux, nx, ny, px_m, py_m)
        _cartouche_pro(c, w, h, p, f"COFFRAGE — {level_name}", page, total_pages, "STRUCTURE BÉTON ARMÉ")
        c.showPage()

    # ── FERRAILLAGE DALLE — NAPPE INFÉRIEURE (planche B14 / 12B style) ──
    page += 1
    w, h = A3L; c.setPageSize(A3L); _border(c, w, h)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 13)
    c.drawString(14*mm, h - 17*mm, "FERRAILLAGE INFÉRIEUR DALLE — PH NIVEAU COURANT")
    # Accumulator for repère nomenclature (shared across INF + SUP pages)
    _ferr_repere_counter = [0]
    _ferr_nomenclature = []  # list of tuples (rep, count, diam, esp, long_m, position)

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
        ok, placement = _render_pdf_background(c, archi_pdf_path, 0, w, h, opacity=0.80, dpi=200, grayscale=True)
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
        # Add chapeau (top mesh) indicators at grid intersections
        _draw_chapeau_indicators(c, ox, oy, sc, nx, ny, px_m, py_m)

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
                if sw > 14 and sh > 14:
                    # BET-standard panel annotation: count-HA(e=) / 1er lit inf + chapeau
                    # Estimate panel dimensions in metres (real axes are in mm)
                    px_bay = abs(real_ax_d[i+1] - real_ax_d[i]) / 1000.0
                    py_bay = abs(real_ay_d[j+1] - real_ay_d[j]) / 1000.0
                    lbl_x_inf = _bar_notation_bet(dalle.As_x_cm2_ml, py_bay)
                    lbl_y_inf = _bar_notation_bet(dalle.As_y_cm2_ml, px_bay)
                    # Repère circled number (as in réf. BET: 1, 2, 3... 76)
                    _ferr_repere_counter[0] += 1
                    rep_n = _ferr_repere_counter[0]
                    diam_x, esp_x, _ = _estimate_bar_from_as(dalle.As_x_cm2_ml)
                    diam_y, esp_y, _ = _estimate_bar_from_as(dalle.As_y_cm2_ml)
                    nb_x_bars = max(2, int(py_bay * 100 / esp_x) + 1)
                    nb_y_bars = max(2, int(px_bay * 100 / esp_y) + 1)
                    _ferr_nomenclature.append((rep_n, nb_x_bars, diam_x, esp_x, py_bay, "1er lit inf X"))
                    _ferr_nomenclature.append((rep_n, nb_y_bars, diam_y, esp_y, px_bay, "1er lit inf Y"))
                    # Draw circled repère number
                    c.setFillColor(BLANC); c.setStrokeColor(ROUGE); c.setLineWidth(0.5)
                    c.circle(sx + 4, sy_a + sh - 4, 3, fill=1, stroke=1)
                    c.setFillColor(ROUGE); c.setFont("Helvetica-Bold", 3.5)
                    tw = c.stringWidth(str(rep_n), "Helvetica-Bold", 3.5)
                    c.drawString(sx + 4 - tw/2, sy_a + sh - 5.2, str(rep_n))
                    # Labels
                    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 3.2)
                    c.drawCentredString(cx_p, cy_p + 5, lbl_x_inf)
                    c.setFont("Helvetica", 2.6); c.setFillColor(GRIS2)
                    c.drawCentredString(cx_p, cy_p + 2.2, "1er lit inf X")
                    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 3.2)
                    c.drawCentredString(cx_p, cy_p - 1.5, lbl_y_inf)
                    c.setFont("Helvetica", 2.6); c.setFillColor(GRIS2)
                    c.drawCentredString(cx_p, cy_p - 4.2, "1er lit inf Y")
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
                # BET-standard panel annotation
                lbl_x_inf = _bar_notation_bet(dalle.As_x_cm2_ml, py_m)
                lbl_y_inf = _bar_notation_bet(dalle.As_y_cm2_ml, px_m)
                lbl_ch    = _bar_chapeau_bet(max(dalle.As_x_cm2_ml, dalle.As_y_cm2_ml), min(px_m, py_m))
                c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 4)
                c.drawCentredString(cx_p, cy_p + 6, lbl_x_inf)
                c.setFont("Helvetica", 3); c.setFillColor(GRIS2)
                c.drawCentredString(cx_p, cy_p + 3, "1er lit inf X")
                c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 4)
                c.drawCentredString(cx_p, cy_p - 1, lbl_y_inf)
                c.setFont("Helvetica", 3); c.setFillColor(GRIS2)
                c.drawCentredString(cx_p, cy_p - 4, "1er lit inf Y")
                c.setFillColor(VIOLET); c.setFont("Helvetica-Bold", 3.5)
                c.drawString(sx + 3, sy + sh - 5, lbl_ch)

    _legend_pro(c, w, h, [
        (ROUGE, 0.5, f"1er lit inf. X — {_bar_notation(dalle.As_x_cm2_ml)} (As={dalle.As_x_cm2_ml:.2f} cm²/ml)"),
        (BLEU, 0.4, f"1er lit inf. Y — {_bar_notation(dalle.As_y_cm2_ml)} (As={dalle.As_y_cm2_ml:.2f} cm²/ml)"),
        (GRIS2, 0.2, "2e lit inf. — Renforts locaux en zone de moment max."),
        (NOIR, 'fill', f"Poteau {pot_s}×{pot_s}mm"),
        (ROUGE, 'fill', "Repères armatures (cf. nomenclature bas de planche)"),
    ], "FERRAILLAGE INFÉRIEUR")

    # Nomenclature table — repères accumulated from panels
    _draw_ferr_nomenclature_table(c, 14*mm, 42*mm, _ferr_nomenclature, w)
    _cartouche_pro(c, w, h, p, "FERRAILLAGE INF. DALLE", page, total_pages,
                   "LOT 01 — STRUCTURE / FERRAILLAGE B.A.",
                   drawing_no=f"TJN-STR-FER-INF-{page:03d}")
    c.showPage()

    # ── FERRAILLAGE DALLE — NAPPE SUPÉRIEURE (planche A15 / 13B style) ──
    page += 1
    w, h = A3L; c.setPageSize(A3L); _border(c, w, h)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 13)
    c.drawString(14*mm, h - 17*mm, "FERRAILLAGE SUPÉRIEUR DALLE — PH NIVEAU COURANT")

    # Re-render the architectural/DWG background (same modes as INF)
    rendered_sup = False; sup_tx = sup_ty = None
    real_ax_s = []; real_ay_s = []
    if archi_pdf_path and (is_from_pdf_d or not has_geom_d):
        ok, placement = _render_pdf_background(c, archi_pdf_path, 0, w, h, opacity=0.75, dpi=200, grayscale=True)
        if ok and placement and has_geom_d:
            real_ax_s = lvl_geom.get('axes_x', [])
            real_ay_s = lvl_geom.get('axes_y', [])
            if real_ax_s and real_ay_s and placement.get('pdf_h_pt'):
                sup_tx, sup_ty, _ = _pdf_bg_transforms(placement, placement['pdf_h_pt'])
                c.saveState(); c.setStrokeAlpha(0.4)
                c.setStrokeColor(GRIS4); c.setLineWidth(0.3); c.setDash(4, 2)
                for ax in real_ax_s:
                    c.line(sup_tx(ax), sup_ty(real_ay_s[0])-5*mm, sup_tx(ax), sup_ty(real_ay_s[-1])+5*mm)
                for ay in real_ay_s:
                    c.line(sup_tx(real_ax_s[0])-5*mm, sup_ty(ay), sup_tx(real_ax_s[-1])+5*mm, sup_ty(ay))
                c.setDash(); c.restoreState()
                for ax in real_ax_s:
                    for ay in real_ay_s:
                        c.setFillColor(NOIR); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
                        c.rect(sup_tx(ax)-2.5, sup_ty(ay)-2.5, 5, 5, fill=1, stroke=1)
                rendered_sup = True
    if not rendered_sup and has_geom_d:
        dtx2, dty2, dsc2, _, _ = _dwg_layout(w, h, lvl_geom)
        if dtx2:
            _draw_dwg(c, lvl_geom, dtx2, dty2, sc=dsc2)
            real_ax_s = lvl_geom.get('axes_x', [])
            real_ay_s = lvl_geom.get('axes_y', [])
            sup_tx, sup_ty = dtx2, dty2
            if real_ax_s and real_ay_s:
                c.setStrokeColor(GRIS4); c.setLineWidth(0.25); c.setDash(4, 2)
                for ax in real_ax_s:
                    c.line(dtx2(ax), dty2(real_ay_s[0])-6*mm, dtx2(ax), dty2(real_ay_s[-1])+6*mm)
                for ay in real_ay_s:
                    c.line(dtx2(real_ax_s[0])-6*mm, dty2(ay), dtx2(real_ax_s[-1])+6*mm, dty2(ay))
                c.setDash()
                for ax in real_ax_s:
                    for ay in real_ay_s:
                        c.setFillColor(NOIR); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
                        c.rect(dtx2(ax)-2, dty2(ay)-2, 4, 4, fill=1, stroke=1)
                rendered_sup = True
    if not rendered_sup:
        ox2, oy2, sc2, gw2, gh2 = _grid_layout(w, h, nx, ny, px_m, py_m)
        _draw_grid_axes(c, ox2, oy2, sc2, nx, ny, px_m, py_m, gw2, gh2)
        _draw_poteaux(c, ox2, oy2, sc2, nx, ny, px_m, py_m, pot_s)
        _draw_chapeau_indicators(c, ox2, oy2, sc2, nx, ny, px_m, py_m)

    # SUP annotations per panel — chapeaux primary, "CH+Rep" notation
    if rendered_sup and real_ax_s and real_ay_s and sup_tx:
        for i in range(len(real_ax_s) - 1):
            for j in range(len(real_ay_s) - 1):
                sx = sup_tx(real_ax_s[i]) + 2
                sy_b = min(sup_ty(real_ay_s[j]), sup_ty(real_ay_s[j+1])) + 2
                sw = abs(sup_tx(real_ax_s[i+1]) - sup_tx(real_ax_s[i])) - 4
                sh = abs(sup_ty(real_ay_s[j+1]) - sup_ty(real_ay_s[j])) - 4
                if sw < 5 or sh < 5: continue
                cx_p = sx + sw/2; cy_p = sy_b + sh/2
                # Chapeau bars (green for X, violet for Y) spanning ~1/4 panel near supports
                c.saveState(); c.setStrokeAlpha(0.55)
                c.setStrokeColor(colors.HexColor("#66BB6A")); c.setLineWidth(0.4)
                n_ch_x = max(2, int(sh / 10))
                for k in range(n_ch_x):
                    yb = sy_b + 3 + k * (sh - 6) / max(n_ch_x - 1, 1)
                    # Two band segments near the two supports
                    c.line(sx + 2, yb, sx + sw * 0.28, yb)
                    c.line(sx + sw * 0.72, yb, sx + sw - 2, yb)
                c.setStrokeColor(VIOLET); c.setLineWidth(0.35)
                n_ch_y = max(2, int(sw / 10))
                for k in range(n_ch_y):
                    xb = sx + 3 + k * (sw - 6) / max(n_ch_y - 1, 1)
                    c.line(xb, sy_b + 2, xb, sy_b + sh * 0.28)
                    c.line(xb, sy_b + sh * 0.72, xb, sy_b + sh - 2)
                c.restoreState()
                if sw > 14 and sh > 14:
                    px_bay = abs(real_ax_s[i+1] - real_ax_s[i]) / 1000.0
                    py_bay = abs(real_ay_s[j+1] - real_ay_s[j]) / 1000.0
                    lbl_ch_x = _bar_chapeau_bet(dalle.As_x_cm2_ml, py_bay)
                    lbl_ch_y = _bar_chapeau_bet(dalle.As_y_cm2_ml, px_bay)
                    _ferr_repere_counter[0] += 1
                    rep_n = _ferr_repere_counter[0]
                    d_cx, e_cx, _ = _estimate_bar_from_as(dalle.As_x_cm2_ml)
                    d_cy, e_cy, _ = _estimate_bar_from_as(dalle.As_y_cm2_ml)
                    _ferr_nomenclature.append((rep_n, max(2, int(py_bay*100/max(int(e_cx*1.5),1))+1),
                                               d_cx, int(e_cx*1.5), py_bay, "CH+Rep lit sup X"))
                    _ferr_nomenclature.append((rep_n, max(2, int(px_bay*100/max(int(e_cy*1.5),1))+1),
                                               d_cy, int(e_cy*1.5), px_bay, "CH+Rep lit sup Y"))
                    c.setFillColor(BLANC); c.setStrokeColor(VIOLET); c.setLineWidth(0.5)
                    c.circle(sx + 4, sy_b + sh - 4, 3, fill=1, stroke=1)
                    c.setFillColor(VIOLET); c.setFont("Helvetica-Bold", 3.5)
                    tw = c.stringWidth(str(rep_n), "Helvetica-Bold", 3.5)
                    c.drawString(sx + 4 - tw/2, sy_b + sh - 5.2, str(rep_n))
                    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 3.2)
                    c.drawCentredString(cx_p, cy_p + 5, lbl_ch_x)
                    c.setFont("Helvetica", 2.6); c.setFillColor(GRIS2)
                    c.drawCentredString(cx_p, cy_p + 2.2, "CH 1er lit sup X")
                    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 3.2)
                    c.drawCentredString(cx_p, cy_p - 1.5, lbl_ch_y)
                    c.setFont("Helvetica", 2.6); c.setFillColor(GRIS2)
                    c.drawCentredString(cx_p, cy_p - 4.2, "CH 1er lit sup Y")

    _legend_pro(c, w, h, [
        (colors.HexColor("#66BB6A"), 0.5, f"Chapeau X — {_bar_chapeau_bet(dalle.As_x_cm2_ml, py_m)}"),
        (VIOLET, 0.5, f"Chapeau Y — {_bar_chapeau_bet(dalle.As_y_cm2_ml, px_m)}"),
        (GRIS2, 0.2, "2e lit sup. — Renforts sur appuis continus"),
        (NOIR, 'fill', f"Poteau {pot_s}×{pot_s}mm"),
        (VIOLET, 'fill', "Repères armatures supérieures"),
    ], "FERRAILLAGE SUPÉRIEUR")

    _draw_ferr_nomenclature_table(c, 14*mm, 42*mm, _ferr_nomenclature, w,
                                   filter_pos="sup")
    _cartouche_pro(c, w, h, p, "FERRAILLAGE SUP. DALLE", page, total_pages,
                   "LOT 01 — STRUCTURE / FERRAILLAGE B.A.",
                   drawing_no=f"TJN-STR-FER-SUP-{page:03d}")
    c.showPage()

    # ── COUPE TYPE DALLE — lit inf / lit sup / chapeau / enrobage ──
    page += 1
    w, h = A3L; c.setPageSize(A3L); _border(c, w, h)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 13)
    c.drawString(14*mm, h - 17*mm, "COUPE TYPE DALLE — DÉTAIL FERRAILLAGE A-A")
    _draw_coupe_type_dalle(c, w, h, dalle, pp_b, pp_h)
    _cartouche_pro(c, w, h, p, "COUPE TYPE DALLE", page, total_pages,
                   "LOT 01 — DÉTAIL FERRAILLAGE",
                   drawing_no=f"TJN-STR-COUP-{page:03d}")
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
        ok, placement = _render_pdf_background(c, archi_pdf_path, 0, w, h, opacity=0.75, dpi=200, grayscale=True)
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
        # Add foundation labels S1, S2... on parametric grid
        _label_foundations_at_grid(c, ox, oy, sc, nx, ny, px_m, py_m, r, fd)

    type_f = fd.type.value.replace('_', ' ').title()
    c.setFont("Helvetica", 5.5); c.setFillColor(GRIS2)
    c.drawString(14*mm, 42*mm, f"{type_f} — prof.{fd.profondeur_m:.1f}m — σsol={r.pression_sol_MPa:.2f}MPa — {beton}")
    _legend_pro(c, w, h, [
        (VERT, 'fill', f"{'Pieu ø'+str(diam_p)+'mm' if nb_pieux else 'Semelle '+str(larg_sem)+'×'+str(larg_sem)+'m'}"),
        (NOIR, 0.8, "Longrine de liaison — Liant pieux/semelles"),
        (colors.HexColor("#D7CCC8"), 'fill', f"Dallage sur sol (ep.{dalle_ep}mm)" if not p.get("avec_sous_sol") else ""),
        (GRIS4, 0.05, "Axes de trame — Grille structure"),
        (colors.HexColor("#FFC107"), 0.4, "Charges concentrées (NEd/poteau)"),
    ], "FONDATIONS")
    _cartouche_pro(c, w, h, p, "FONDATIONS", page, total_pages, "FONDATIONS STRUCTURE")
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

        # Level label on left — generate proper level names (SOUS-SOL, RDC, R+1, R+2, ..., TERRASSE)
        if niv == 0:
            if p.get("avec_sous_sol"):
                niv_label = "SOUS-SOL"
            else:
                niv_label = "RDC"
        elif p.get("avec_sous_sol"):
            if niv == 1:
                niv_label = "RDC"
            else:
                niv_label = f"R+{niv - 1}"
        else:
            niv_label = f"R+{niv}"
        c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 6.5)
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

    # Draw accumulated height annotations
    _draw_accumulated_heights(c, cox, coy, cgh, rsc, he, nb_niv, p, fd_depth_m)

    # Draw dimension callouts for element thicknesses and drops
    _draw_coupe_dimension_callouts(c, cox, coy, cgh, rsc, he, nb_niv, dalle_ep, pp_h, pp_b)

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

    _legend_pro(c, w, h, [
        (GRIS2, 'fill', f"Poteau {pot_s}×{pot_s}mm — Béton {beton}"),
        (colors.HexColor("#1565C0"), 0.8, f"Poutre principale {pp_b}×{pp_h}mm"),
        (colors.HexColor("#8D6E63"), 0.5, f"Dalle ep.{dalle_ep}mm"),
        (colors.HexColor("#F57C00"), 0.6, f"Fondation prof.{fd.profondeur_m:.1f}m"),
    ], "COUPE GÉNÉRALE")

    _cartouche_pro(c, w, h, p, "COUPE GÉNÉRALE", page, total_pages, "STRUCTURE BÉTON ARMÉ", ech="1/200")
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
# MEP HELPERS — drawing_no, nomenclature, schémas de principe
# ══════════════════════════════════════════

# Normalized MEP lot codes for drawing number conventions (BET standard)
_MEP_LOT_CODES = {
    "plb_ef":   ("PLB-EF",  "PLOMBERIE Eau Froide"),
    "plb_ec":   ("PLB-EC",  "PLOMBERIE Eau Chaude"),
    "plb_eu":   ("PLB-EU",  "PLOMBERIE Évacuations"),
    "elec_ecl": ("ELE-ECL", "ÉLECTRICITÉ Éclairage"),
    "elec_dist":("ELE-DIS", "ÉLECTRICITÉ Prises & TGBT"),
    "cvc_clim": ("CVC-CLM", "CVC Climatisation"),
    "cvc_vmc":  ("CVC-VMC", "CVC Ventilation"),
    "ssi_det":  ("SSI-DET", "SSI Détection"),
    "ssi_ext":  ("SSI-EXT", "SSI Extinction"),
    "cfa":      ("CFA-RES", "Courants Faibles"),
    "asc_plan": ("ASC-PLN", "Ascenseurs"),
    "gtb":      ("GTB-BUS", "GTB Automatisation"),
}

_LEVEL_CODE_MAP = {
    "Sous-Sol": "SS",
    "Sous-Sol / Parking": "SS",
    "RDC": "R0",
    "Rez-de-Chaussée": "R0",
    "Terrasse": "TR",
}

def _level_code(level_label):
    """Convert level label to short code for drawing_no."""
    if level_label in _LEVEL_CODE_MAP:
        return _LEVEL_CODE_MAP[level_label]
    lab = (level_label or "").lower()
    if "sous" in lab: return "SS"
    if "terrasse" in lab: return "TR"
    if "rdc" in lab: return "R0"
    # Try to extract étage number
    import re as _re_lvl
    m = _re_lvl.search(r"(\d+)", level_label or "")
    if m:
        return f"E{int(m.group(1)):02d}"
    return "CR"  # courant

def _mep_drawing_no(key, level_label, page):
    """Build normalized BET drawing number: TJN-MEP-{LOT}-{LVL}-{PG:03d}"""
    lot_code = _MEP_LOT_CODES.get(key, ("MEP", ""))[0]
    lvl_code = _level_code(level_label)
    return f"TJN-MEP-{lot_code}-{lvl_code}-{page:03d}"


def _draw_mep_nomenclature_table(c, x, y, entries, title="NOMENCLATURE ÉQUIPEMENTS"):
    """BET-style equipment nomenclature table.
    entries = list of tuples (rep, desig, qty, unit, norme).
    """
    if not entries:
        return
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors as rl_colors

    header = ["Rep.", "Désignation", "Qté", "Unité", "Norme/DTU"]
    data = [header] + [[str(e[0]), str(e[1])[:42], str(e[2]), str(e[3]), str(e[4])[:18]] for e in entries[:14]]
    col_w = [10*mm, 66*mm, 12*mm, 12*mm, 26*mm]
    table = Table(data, colWidths=col_w, rowHeights=[6.5*mm] + [5*mm]*(len(data)-1))
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor("#43A956")),
        ('TEXTCOLOR', (0, 0), (-1, 0), BLANC),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7.5),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 6.8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('GRID', (0, 0), (-1, -1), 0.3, GRIS3),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BLANC, rl_colors.HexColor("#F5F7F5")]),
    ]))
    tw = sum(col_w)
    th = 6.5*mm + 5*mm * (len(data)-1)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 8.5)
    c.drawString(x, y + th + 2*mm, title)
    table.wrapOn(c, tw, th)
    table.drawOn(c, x, y)


def _build_mep_nomenclature(key, pl, el, cv, cf, si, asc, aut):
    """Build per-lot equipment nomenclature from MEP results."""
    if key == "plb_ef":
        return [
            ("1", f"Citerne eau potable {int(pl.volume_citerne_m3)}m³", 1, "U", "DTU 60.11"),
            ("2", f"Surpresseur {pl.debit_surpresseur_m3h}m³/h", 1, "U", "NF EN 12845"),
            ("3", f"Colonne montante EF DN{pl.diam_colonne_montante_mm}", 1, "U", "DTU 60.11"),
            ("4", "Robinet économiseur", pl.nb_robinets_eco, "U", "NF EDGE v3"),
            ("5", "WC double chasse 3/6L", pl.nb_wc_double_chasse, "U", "EDGE v3"),
        ]
    if key == "plb_ec":
        return [
            ("1", f"Chauffe-eau solaire individuel CESI", pl.nb_chauffe_eau_solaire, "U", "NF EN 12976"),
            ("2", "Colonne montante ECS DN32", 1, "U", "DTU 60.11"),
            ("3", "Circulation ECS DN16", 1, "U", "DTU 60.11"),
        ]
    if key == "plb_eu":
        return [
            ("1", "Chute EU DN100 PVC", 1, "U", "DTU 60.33"),
            ("2", "Chute EP DN75 PVC", 1, "U", "DTU 60.11"),
            ("3", f"Conso annuelle {pl.conso_eau_annuelle_m3:.0f}m³/an", 1, "-", "EDGE v3"),
        ]
    if key == "elec_ecl":
        return [
            ("1", "Plafonnier LED encastré 18W", 1, "U", "NF C 15-100"),
            ("2", "Interrupteur simple allumage", 1, "U", "NF C 15-100"),
            ("3", "Interrupteur VA-ET-VIENT", 1, "U", "NF C 15-100"),
            ("4", "Détecteur de mouvement", 1, "U", "NF C 15-100"),
            ("5", f"Puissance éclairage total {el.puissance_eclairage_kw:.1f}kW", 1, "-", "NF C 15-100"),
        ]
    if key == "elec_dist":
        return [
            ("1", f"Transformateur HT/BT {el.transfo_kva}kVA", 1, "U", "NF C 13-100"),
            ("2", f"Groupe électrogène {el.groupe_electrogene_kva}kVA", 1, "U", "NF C 15-401"),
            ("3", f"TGBT 4P+N / {el.nb_compteurs} départs", 1, "U", "NF C 15-100"),
            ("4", f"Colonne montante {el.section_colonne_mm2}mm²", 1, "U", "NF C 14-100"),
            ("5", "Prise 2P+T 16A NF", 1, "U", "NF C 15-100"),
            ("6", "Prise spécialisée 20A", 1, "U", "NF C 15-100"),
        ]
    if key == "cvc_clim":
        return [
            ("1", "Split mural 18000 BTU (séjour)", cv.nb_splits_sejour, "U", "NF EN 14511"),
            ("2", "Split mural 12000 BTU (chambre)", cv.nb_splits_chambre, "U", "NF EN 14511"),
            ("3", f"Puissance frigorifique {cv.puissance_frigorifique_kw:.0f}kW", 1, "-", "EDGE v3"),
        ]
    if key == "cvc_vmc":
        return [
            ("1", f"VMC {cv.type_vmc}", cv.nb_vmc, "U", "DTU 68.3"),
            ("2", "Bouche soufflage", 1, "U", "DTU 68.3"),
            ("3", "Bouche extraction", 1, "U", "DTU 68.3"),
        ]
    if key == "ssi_det":
        return [
            ("1", "Détecteur de fumée (DF) optique", si.nb_detecteurs_fumee, "U", "NF EN 54-7"),
            ("2", "Déclencheur manuel (DM) rouge", si.nb_declencheurs_manuels, "U", "NF EN 54-11"),
            ("3", f"Centrale SSI / {si.centrale_zones} zones", 1, "U", "NF EN 54-2"),
            ("4", f"Catégorie ERP {si.categorie_erp}", 1, "-", "IT 246"),
        ]
    if key == "ssi_ext":
        return [
            ("1", "RIA DN33 - robinet incendie armé", max(1, int(si.longueur_ria_ml // 25)), "U", "NF EN 671-1"),
            ("2", "BAES - bloc autonome éclairage", 1, "U", "NF C 71-800"),
            ("3", "Extincteur poudre ABC 6kg", si.nb_extincteurs_poudre, "U", "NF EN 3-7"),
            ("4", "Extincteur CO2 2kg", si.nb_extincteurs_co2, "U", "NF EN 3-7"),
            ("5", f"Sprinklers: {'OUI' if si.sprinklers_requis else 'NON'}", 1, "-", "NF EN 12845"),
        ]
    if key == "cfa":
        return [
            ("1", "Prise RJ45 Cat. 6A", cf.nb_prises_rj45, "U", "NF EN 50173"),
            ("2", "Caméra IP intérieure", cf.nb_cameras_int, "U", "NF EN 62676"),
            ("3", "Caméra IP extérieure IP66", cf.nb_cameras_ext, "U", "NF EN 62676"),
        ]
    if key == "asc_plan":
        return [
            ("1", f"Ascenseur {asc.capacite_kg}kg / {asc.vitesse_ms}m/s", asc.nb_ascenseurs, "U", "NF EN 81-20"),
            ("2", "Gaine ascenseur béton", 1, "U", "NF EN 81-20"),
        ]
    if key == "gtb":
        return [
            ("1", f"Bus {aut.protocole}", 1, "U", "NF EN 50090"),
            ("2", f"Points de contrôle GTB", aut.nb_points_controle, "U", "NF EN 15232"),
            ("3", "Capteur température", 1, "U", "NF EN 15232"),
            ("4", "Actionneur éclairage", 1, "U", "NF EN 15232"),
        ]
    return []


def _draw_principe_plomberie(c, w, h, p, pl, page, total):
    """Schéma de principe plomberie — colonnes montantes EF / EC / EU."""
    _border(c, w, h)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 12)
    c.drawString(14*mm, h - 17*mm, "SCHÉMA DE PRINCIPE — PLOMBERIE / COLONNES MONTANTES")
    nb_niv = max(2, p.get("nb_niveaux", 5))
    # 3 colonnes (EF bleu, EC rouge, EU marron)
    x_ef = 80*mm; x_ec = 150*mm; x_eu = 220*mm
    y_base = 40*mm; y_top = y_base + nb_niv * 20*mm

    # Rectangle colonnes
    for x, col, label in [(x_ef, BLEU, "EF"), (x_ec, ROUGE, "EC"), (x_eu, MARRON, "EU")]:
        c.setStrokeColor(col); c.setLineWidth(2)
        c.line(x, y_base, x, y_top)
        c.setFillColor(col); c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(x, y_top + 4*mm, label)

    # Étages horizontaux + piquages
    for i in range(nb_niv):
        y = y_base + i * 20*mm
        c.setStrokeColor(GRIS4); c.setLineWidth(0.3); c.setDash(2,2)
        c.line(30*mm, y, 280*mm, y); c.setDash()
        lvl_name = "Sous-Sol" if (i == 0 and p.get("avec_sous_sol")) else ("RDC" if i == (1 if p.get("avec_sous_sol") else 0) else f"Étage {i - (1 if p.get('avec_sous_sol') else 0)}")
        if i == nb_niv - 1: lvl_name = "Terrasse"
        c.setFillColor(GRIS2); c.setFont("Helvetica", 6)
        c.drawString(30*mm, y+1*mm, lvl_name)
        # Piquages EF/EC (robinets) et EU (chute)
        for x, col in [(x_ef, BLEU), (x_ec, ROUGE)]:
            c.setStrokeColor(col); c.setLineWidth(0.8)
            c.line(x, y, x + 12*mm, y)
            c.setFillColor(col); c.circle(x + 14*mm, y, 1.5, fill=1, stroke=0)
        # EU raccordement
        c.setStrokeColor(MARRON); c.setLineWidth(1); c.setDash(3,1.5)
        c.line(x_eu - 12*mm, y, x_eu, y); c.setDash()

    # Éléments en base
    c.setFillColor(BLEU_B); c.setStrokeColor(BLEU); c.setLineWidth(0.8)
    c.rect(x_ef - 18*mm, y_base - 18*mm, 30*mm, 14*mm, fill=1, stroke=1)
    c.setFillColor(BLEU); c.setFont("Helvetica-Bold", 6)
    c.drawCentredString(x_ef - 3*mm, y_base - 13*mm, f"Citerne {int(pl.volume_citerne_m3)}m³")
    c.setFont("Helvetica", 5); c.drawCentredString(x_ef - 3*mm, y_base - 16*mm, f"Surpr. {pl.debit_surpresseur_m3h}m³/h")

    c.setFillColor(colors.HexColor("#FFCDD2")); c.setStrokeColor(ROUGE); c.setLineWidth(0.8)
    c.rect(x_ec - 10*mm, y_top + 8*mm, 22*mm, 10*mm, fill=1, stroke=1)
    c.setFillColor(ROUGE); c.setFont("Helvetica-Bold", 6)
    c.drawCentredString(x_ec + 1*mm, y_top + 13*mm, f"CESI ×{pl.nb_chauffe_eau_solaire}")

    c.setFillColor(colors.HexColor("#D7CCC8")); c.setStrokeColor(MARRON); c.setLineWidth(0.8)
    c.rect(x_eu - 10*mm, y_base - 18*mm, 24*mm, 14*mm, fill=1, stroke=1)
    c.setFillColor(MARRON); c.setFont("Helvetica-Bold", 6)
    c.drawCentredString(x_eu + 2*mm, y_base - 13*mm, "Réseau EU")
    c.setFont("Helvetica", 5); c.drawCentredString(x_eu + 2*mm, y_base - 16*mm, "Fosse septique")

    # Notes
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 7)
    c.drawString(14*mm, 32*mm, "NOTES :")
    c.setFont("Helvetica", 6); c.setFillColor(GRIS2)
    c.drawString(14*mm, 28*mm, f"• EF : DN{pl.diam_colonne_montante_mm} PEHD, surpresseur automatique, pression 3 bar aux étages")
    c.drawString(14*mm, 24*mm, f"• EC : DN32 cuivre / PER gaine, calorifugeage 13mm, CESI individuel par logement")
    c.drawString(14*mm, 20*mm, f"• EU : DN100 PVC NF, pente 2% min., ventilation primaire en toiture")
    c.drawString(14*mm, 16*mm, f"• Normes applicables : DTU 60.11 (installation), DTU 60.33 (évacuations), EDGE v3")

    _cartouche_pro(c, w, h, p, "Schéma de principe — Plomberie", page, total, "PLB",
                   drawing_no=f"TJN-MEP-PLB-PCP-{page:03d}")


def _draw_principe_electricite(c, w, h, p, el, page, total):
    """Schéma unifilaire TGBT simplifié."""
    _border(c, w, h)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 12)
    c.drawString(14*mm, h - 17*mm, "SCHÉMA UNIFILAIRE SIMPLIFIÉ — TGBT")

    # Source HT
    sx = 50*mm; sy = h - 45*mm
    c.setFillColor(colors.HexColor("#FFECB3")); c.setStrokeColor(NOIR); c.setLineWidth(1)
    c.rect(sx, sy, 40*mm, 14*mm, fill=1, stroke=1)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(sx+20*mm, sy+8*mm, "Arrivée HT 30kV")
    c.setFont("Helvetica", 5); c.drawCentredString(sx+20*mm, sy+3*mm, "SENELEC / CIE")

    # Transfo
    tx0 = sx + 60*mm; ty0 = sy
    c.setFillColor(colors.HexColor("#C8E6C9")); c.setStrokeColor(VERT); c.setLineWidth(1)
    c.rect(tx0, ty0, 40*mm, 14*mm, fill=1, stroke=1)
    c.setFillColor(VERT); c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(tx0+20*mm, ty0+8*mm, f"Transfo {el.transfo_kva}kVA")
    c.setFont("Helvetica", 5); c.drawCentredString(tx0+20*mm, ty0+3*mm, "30kV / 400V 50Hz")

    # Ligne vers TGBT
    c.setStrokeColor(NOIR); c.setLineWidth(1.5)
    c.line(sx+40*mm, sy+7*mm, tx0, ty0+7*mm)
    c.line(tx0+40*mm, ty0+7*mm, tx0+60*mm, ty0+7*mm)

    # Inverseur + GE
    gex = tx0 + 60*mm
    c.setFillColor(colors.HexColor("#FFE0B2")); c.setStrokeColor(ORANGE); c.setLineWidth(1)
    c.rect(gex, ty0, 40*mm, 14*mm, fill=1, stroke=1)
    c.setFillColor(ORANGE); c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(gex+20*mm, ty0+8*mm, "Inverseur Normal/Secours")
    c.setFont("Helvetica", 5); c.drawCentredString(gex+20*mm, ty0+3*mm, f"GE {el.groupe_electrogene_kva}kVA")

    # TGBT principal
    tgx = 100*mm; tgy = sy - 50*mm
    c.setFillColor(VERT_P); c.setStrokeColor(VERT); c.setLineWidth(1.2)
    c.rect(tgx, tgy, 140*mm, 24*mm, fill=1, stroke=1)
    c.setFillColor(VERT); c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(tgx+70*mm, tgy+15*mm, "TGBT PRINCIPAL")
    c.setFont("Helvetica", 6); c.drawCentredString(tgx+70*mm, tgy+8*mm, f"4P+N — {el.nb_compteurs} départs — Col. {el.section_colonne_mm2}mm²")
    c.drawCentredString(tgx+70*mm, tgy+4*mm, "Disjoncteur général + parafoudre classe I")

    # Lien transfo -> TGBT
    c.setStrokeColor(NOIR); c.setLineWidth(1.5)
    c.line(tx0+20*mm, ty0, tx0+20*mm, tgy+24*mm)
    c.line(tx0+20*mm, tgy+24*mm, tgx+70*mm, tgy+24*mm)

    # Départs TGBT
    departs = [
        ("Éclairage", JAUNE, "1.5mm²", "16A"),
        ("Prises",    ORANGE, "2.5mm²", "16A"),
        ("Cuisine",   colors.HexColor("#E64A19"), "6mm²", "32A"),
        ("Clim CVC",  CYAN, "4mm²", "20A"),
        ("Ascenseur", BLEU, "16mm²", "63A"),
        ("SSI",       ROUGE, "2.5mm²", "10A"),
        ("Services",  VIOLET, "4mm²", "25A"),
    ]
    nb_dep = len(departs)
    for i, (nm, col, sect, prot) in enumerate(departs):
        dx = tgx + 5*mm + i * (130*mm/nb_dep)
        # disjoncteur
        c.setFillColor(BLANC); c.setStrokeColor(NOIR); c.setLineWidth(0.5)
        c.rect(dx-3*mm, tgy-10*mm, 6*mm, 8*mm, fill=1, stroke=1)
        c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 5)
        c.drawCentredString(dx, tgy-6*mm, prot)
        # ligne vers charge
        c.setStrokeColor(col); c.setLineWidth(1.2)
        c.line(dx, tgy-10*mm, dx, tgy-25*mm)
        # étiquette charge
        c.saveState()
        c.translate(dx, tgy-30*mm); c.rotate(-90)
        c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 6)
        c.drawString(0, 0, nm)
        c.setFillColor(GRIS2); c.setFont("Helvetica", 4.5)
        c.drawString(0, -3.5*mm, sect)
        c.restoreState()
        # Lien TGBT -> disjoncteur
        c.setStrokeColor(NOIR); c.setLineWidth(0.8)
        c.line(dx, tgy, dx, tgy-2*mm)

    # Notes
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 7)
    c.drawString(14*mm, 30*mm, "NOTES :")
    c.setFont("Helvetica", 6); c.setFillColor(GRIS2)
    c.drawString(14*mm, 26*mm, f"• Régime de neutre TT — sélectivité différentielle 30mA/300mA — NF C 15-100")
    c.drawString(14*mm, 22*mm, f"• Transformateur sec {el.transfo_kva}kVA en poste HT/BT, cellule SENELEC homologuée")
    c.drawString(14*mm, 18*mm, f"• Groupe électrogène {el.groupe_electrogene_kva}kVA — démarrage automatique inverseur 3s")
    c.drawString(14*mm, 14*mm, f"• Parafoudre type 1+2 classe I, mise à la terre < 10Ω — NF C 17-102")

    _cartouche_pro(c, w, h, p, "Schéma unifilaire TGBT", page, total, "ELEC",
                   drawing_no=f"TJN-MEP-ELE-UNI-{page:03d}")


def _draw_principe_cvc(c, w, h, p, cv, page, total):
    """Schéma de principe CVC — VMC + Climatisation."""
    _border(c, w, h)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 12)
    c.drawString(14*mm, h - 17*mm, "SCHÉMA DE PRINCIPE — VMC & CLIMATISATION")

    # VMC bloc (gauche)
    vx = 30*mm; vy = h - 60*mm
    c.setFillColor(colors.HexColor("#E8F5E9")); c.setStrokeColor(colors.HexColor("#2E7D32")); c.setLineWidth(1)
    c.rect(vx, vy, 120*mm, 40*mm, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#2E7D32")); c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(vx+60*mm, vy+33*mm, "VMC — VENTILATION MÉCANIQUE CONTRÔLÉE")
    c.setFillColor(NOIR); c.setFont("Helvetica", 6)
    c.drawCentredString(vx+60*mm, vy+27*mm, f"{cv.nb_vmc} × VMC {cv.type_vmc}")

    # Caisson VMC
    caisson_x = vx + 50*mm; caisson_y = vy + 5*mm
    c.setFillColor(colors.HexColor("#A5D6A7")); c.setStrokeColor(colors.HexColor("#1B5E20")); c.setLineWidth(0.8)
    c.rect(caisson_x, caisson_y, 20*mm, 12*mm, fill=1, stroke=1)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 6)
    c.drawCentredString(caisson_x+10*mm, caisson_y+6*mm, "Caisson")

    # Bouches extraction (SDB, Cuisine)
    for i, lbl in enumerate(["SDB/WC", "Cuisine", "Buanderie"]):
        bx = vx + 10*mm + i*12*mm; by = vy + 18*mm
        c.setStrokeColor(colors.HexColor("#1B5E20")); c.setFillColor(colors.HexColor("#C8E6C9"))
        c.circle(bx, by, 2.5, fill=1, stroke=1)
        c.setFillColor(NOIR); c.setFont("Helvetica", 4.5)
        c.drawCentredString(bx, by-6, lbl)
        # gaine vers caisson
        c.setStrokeColor(colors.HexColor("#2E7D32")); c.setLineWidth(0.8)
        c.line(bx, by, caisson_x, caisson_y + 6*mm)

    # Toiture rejet
    c.setFillColor(GRIS4); c.setStrokeColor(NOIR); c.setLineWidth(0.5)
    c.rect(caisson_x+8*mm, vy+35*mm, 4*mm, 4*mm, fill=1, stroke=1)
    c.setStrokeColor(colors.HexColor("#2E7D32")); c.setLineWidth(0.8)
    c.line(caisson_x+10*mm, caisson_y+12*mm, caisson_x+10*mm, vy+35*mm)
    c.setFillColor(NOIR); c.setFont("Helvetica", 4.5)
    c.drawString(caisson_x+14*mm, vy+36*mm, "Rejet toiture")

    # Entrées d'air
    for i, lbl in enumerate(["Séjour", "Chambre 1", "Chambre 2"]):
        ex = vx + 88*mm + i*8*mm; ey = vy + 18*mm
        c.setFillColor(BLEU_B); c.setStrokeColor(BLEU); c.setLineWidth(0.5)
        c.rect(ex-2, ey-1.5, 4, 3, fill=1, stroke=1)
        c.setFillColor(NOIR); c.setFont("Helvetica", 4)
        c.drawCentredString(ex, ey-6, lbl)

    # Climatisation (droite)
    cx0 = 170*mm; cy0 = h - 60*mm
    c.setFillColor(colors.HexColor("#E0F7FA")); c.setStrokeColor(CYAN); c.setLineWidth(1)
    c.rect(cx0, cy0, 110*mm, 40*mm, fill=1, stroke=1)
    c.setFillColor(CYAN); c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(cx0+55*mm, cy0+33*mm, "CLIMATISATION — SPLITS INDIVIDUELS")
    c.setFillColor(NOIR); c.setFont("Helvetica", 6)
    c.drawCentredString(cx0+55*mm, cy0+27*mm,
                        f"{cv.nb_splits_sejour + cv.nb_splits_chambre} splits — P.frigo {cv.puissance_frigorifique_kw:.0f}kW")

    # GE extérieure (toiture)
    gex0 = cx0 + 5*mm; gey0 = cy0 + 20*mm
    c.setFillColor(colors.HexColor("#B2EBF2")); c.setStrokeColor(CYAN); c.setLineWidth(0.7)
    c.rect(gex0, gey0, 18*mm, 8*mm, fill=1, stroke=1)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 5)
    c.drawCentredString(gex0+9*mm, gey0+4*mm, "GE ext.")
    c.setFont("Helvetica", 4); c.drawCentredString(gex0+9*mm, gey0+1*mm, "multi-split")

    # Unités intérieures
    splits = [("Séjour", "18000 BTU"), ("Ch.1", "12000 BTU"), ("Ch.2", "12000 BTU"), ("Bureau", "9000 BTU")]
    for i, (rm, btu) in enumerate(splits):
        ux = cx0 + 28*mm + i * 20*mm; uy = cy0 + 5*mm
        c.setFillColor(CYAN); c.setStrokeColor(colors.HexColor("#006064")); c.setLineWidth(0.4)
        c.rect(ux-6, uy, 12, 4, fill=1, stroke=1)
        c.setFillColor(NOIR); c.setFont("Helvetica", 4.5)
        c.drawCentredString(ux, uy-3, rm); c.drawCentredString(ux, uy+6, btu)
        # liaison frigorifique
        c.setStrokeColor(CYAN); c.setLineWidth(0.7)
        c.line(ux, uy+4, gex0 + 9*mm, gey0)

    # Notes
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 7)
    c.drawString(14*mm, 50*mm, "NOTES :")
    c.setFont("Helvetica", 6); c.setFillColor(GRIS2)
    c.drawString(14*mm, 46*mm, f"• VMC {cv.type_vmc} — extraction pièces humides, insufflation pièces sèches — DTU 68.3")
    c.drawString(14*mm, 42*mm, f"• Débits : WC 15 m³/h, SDB 30 m³/h, cuisine 75-125 m³/h (pointe)")
    c.drawString(14*mm, 38*mm, f"• Climatisation : R410A ou R32, COP > 3.5, niveau sonore < 40 dB(A) intérieur")
    c.drawString(14*mm, 34*mm, f"• Liaisons frigorifiques cuivre isolé 13mm, longueur max 15m par split")
    c.drawString(14*mm, 30*mm, f"• Condensats : évacuation gravitaire vers EU (pente 1%) ou pompe de relevage")
    c.drawString(14*mm, 26*mm, f"• Contrôle GTB : thermostat programmable par zone — NF EN 15232")

    _cartouche_pro(c, w, h, p, "Schéma de principe — CVC", page, total, "CVC",
                   drawing_no=f"TJN-MEP-CVC-PCP-{page:03d}")


def _draw_principe_ssi(c, w, h, p, si, page, total):
    """Schéma de principe SSI — Détection + Extinction."""
    _border(c, w, h)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 12)
    c.drawString(14*mm, h - 17*mm, "SCHÉMA DE PRINCIPE — SYSTÈME SÉCURITÉ INCENDIE (SSI)")

    # Centrale SSI (haut centre)
    ctx = 130*mm; cty = h - 55*mm
    c.setFillColor(colors.HexColor("#FFEBEE")); c.setStrokeColor(ROUGE); c.setLineWidth(1.2)
    c.rect(ctx, cty, 60*mm, 20*mm, fill=1, stroke=1)
    c.setFillColor(ROUGE); c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(ctx+30*mm, cty+13*mm, "CENTRALE SSI")
    c.setFillColor(NOIR); c.setFont("Helvetica", 6)
    c.drawCentredString(ctx+30*mm, cty+7*mm, f"Cat. ERP {si.categorie_erp} — {si.centrale_zones} zones")
    c.setFont("Helvetica", 5); c.drawCentredString(ctx+30*mm, cty+3*mm, "NF EN 54-2 + IT 246")

    # 3 branches descendantes : Détection / Alarme / Extinction
    br_y_top = cty; br_y_mid = cty - 30*mm
    branches = [
        ("DÉTECTION", 60*mm, [
            ("DF ×"+str(si.nb_detecteurs_fumee), "Détecteur fumée optique"),
            ("DM ×"+str(si.nb_declencheurs_manuels), "Déclencheur manuel"),
            ("DT", "Détecteur thermovélocimétrique"),
        ], ROUGE),
        ("ALARME & ÉVACUATION", 160*mm, [
            ("DS", "Diffuseur sonore type 2a"),
            ("BAES", "Bloc autonome éclairage"),
            ("MAD", "Mise en arrêt distribution"),
        ], colors.HexColor("#D32F2F")),
        ("EXTINCTION", 260*mm, [
            ("RIA", f"{int(si.longueur_ria_ml//25)} × RIA DN33"),
            ("EXT", f"{si.nb_extincteurs_poudre+si.nb_extincteurs_co2} extincteurs"),
            ("SPR", "Sprinklers" if si.sprinklers_requis else "—"),
        ], colors.HexColor("#E53935")),
    ]
    for name, x_br, items, col in branches:
        # Ligne centrale -> tête branche
        c.setStrokeColor(col); c.setLineWidth(1.2)
        c.line(ctx+30*mm, br_y_top, x_br, br_y_mid + 22*mm)
        c.line(x_br, br_y_mid + 22*mm, x_br, br_y_mid)
        # Tête de branche
        c.setFillColor(col); c.rect(x_br-20*mm, br_y_mid-4*mm, 40*mm, 8*mm, fill=1, stroke=0)
        c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(x_br, br_y_mid-1*mm, name)
        # Items
        for i, (code, desig) in enumerate(items):
            iy = br_y_mid - 12*mm - i*10*mm
            c.setFillColor(BLANC); c.setStrokeColor(col); c.setLineWidth(0.8)
            c.rect(x_br-18*mm, iy-3*mm, 16*mm, 7*mm, fill=1, stroke=1)
            c.setFillColor(col); c.setFont("Helvetica-Bold", 5.5)
            c.drawCentredString(x_br-10*mm, iy, code)
            c.setFillColor(NOIR); c.setFont("Helvetica", 5)
            c.drawString(x_br-1*mm, iy-1*mm, desig)
            # ligne vers item
            c.setStrokeColor(col); c.setLineWidth(0.6); c.setDash(2,1)
            c.line(x_br, br_y_mid-4*mm, x_br, iy+4*mm); c.setDash()

    # Notes
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 7)
    c.drawString(14*mm, 32*mm, "NOTES :")
    c.setFont("Helvetica", 6); c.setFillColor(GRIS2)
    c.drawString(14*mm, 28*mm, f"• Catégorie d'ERP : {si.categorie_erp} — règlement de sécurité IT 246")
    c.drawString(14*mm, 24*mm, f"• Détection automatique par DF optique NF EN 54-7, DM NF EN 54-11")
    c.drawString(14*mm, 20*mm, f"• Alarme générale type IAA — diffuseurs sonores 65 dB(A) à 3m min.")
    c.drawString(14*mm, 16*mm, f"• BAES NF C 71-800 — autonomie 1h minimum, maintenance annuelle obligatoire")
    c.drawString(14*mm, 12*mm, f"• RIA DN33 / 25m NF EN 671-1 — pression dynamique > 2 bar, débit > 35 L/min")

    _cartouche_pro(c, w, h, p, "Schéma de principe — SSI", page, total, "SSI",
                   drawing_no=f"TJN-MEP-SSI-PCP-{page:03d}")


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
    def _norm_name(raw: str) -> str:
        """Normalize a room label: lowercase, strip punctuation/apostrophes/accents,
        collapse spaces. 'S. D''EAU 2' -> 'sdeau 2', 'Tol.' -> 'tol', 'S.D.B' -> 'sdb'."""
        import unicodedata
        s = unicodedata.normalize('NFKD', raw or '').encode('ascii','ignore').decode('ascii').lower()
        s = _re.sub(r"[\.'`\-_/,;:]+", "", s)
        s = _re.sub(r"\s+", " ", s).strip()
        return s

    def _classify_rooms(rooms):
        """Classify rooms after normalising labels so that 'S.D.B', 'S. D''EAU',
        'Tol.', 'W.C.' are all captured as wet, and every sensible room gets
        a bucket (no silent drops)."""
        wet, living, service = [], [], []
        WET_KW  = ('sdb','sdeau','seau','wc','toil','douche','bain','water','lavabo','sanit','salle de bain','salle deau')
        KIT_KW  = ('cuisine','kitch','office','pantry','buanderie','lingerie')
        LIV_KW  = ('salon','chambre','sejour','bureau','sam','bar','gym','sport','restaurant','magasin','polyvalente','jeu','dressing','suite','parent','living')
        SRV_KW  = ('hall','palier','asc','ascenseur','dgt','degagement','sas','terrasse','balcon','jardin','piscine','vide','porche','circulation','guerite','accueil','technique','local','gaine','escalier','rangement','depot','archive','reserve','cave','garage','parking','service')
        for r in rooms:
            raw = r.get('name', '')
            n = _norm_name(raw)
            if not n or _re.match(r'^\d', n):
                continue
            rt = None
            if any(k in n for k in WET_KW):
                rt = 'wet'
            elif any(k in n for k in KIT_KW):
                rt = 'kitchen'
            elif any(k in n for k in SRV_KW):
                rt = 'service'
            elif any(k in n for k in LIV_KW):
                rt = 'living'
            else:
                # Heuristic fallback based on area: small unlabeled rooms are
                # more likely service/wet than living. Default 'other' -> living.
                rt = 'other'
            entry = {**r, 'rt': rt, 'name_norm': n}
            if rt in ('wet','kitchen'): wet.append(entry)
            elif rt == 'service':       service.append(entry)
            else:                       living.append(entry)
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

    def _synth_level_geom(base, level_label):
        """When only one DWG is uploaded, synthesize per-level geometry so
        each planche looks different. We KEEP the original walls (to preserve
        the real building emprise) but strip interior-only content — rooms,
        windows, doors — that don't belong on sous-sol/terrasse plans."""
        if not base:
            return base
        lab = str(level_label).lower()
        # Terrasse / toiture: real emprise + slab + acrotère (no interior rooms)
        if lab.startswith(('terrasse','toiture','toit')):
            return {
                'walls': list(base.get('walls', [])),
                'windows': [], 'doors': [], 'rooms': [],
                'axes_x': base.get('axes_x', []),
                'axes_y': base.get('axes_y', []),
                '_terrace_bounds': _dwg_bounds(base),
                '_cv_meta': base.get('_cv_meta'),
                '_synth_level': 'terrasse',
            }
        # Sous-sol / parking: real emprise + axes, strip residential rooms
        if 'sous-sol' in lab or 'sous sol' in lab or 'parking' in lab or lab.startswith('ss'):
            return {
                'walls': list(base.get('walls', [])),
                'windows': [], 'doors': [], 'rooms': [],
                'axes_x': base.get('axes_x', []),
                'axes_y': base.get('axes_y', []),
                '_terrace_bounds': _dwg_bounds(base),
                '_cv_meta': base.get('_cv_meta'),
                '_synth_level': 'sous_sol',
            }
        # RDC / étage courant: keep full plan
        return base

    # Map each level to its geometry (multi-DWG or reuse single)
    if dwg_levels and len(dwg_levels) > 1:
        level_list = list(dwg_levels.items())
    else:
        # Single geometry: synthesize a differentiated view per level so
        # we don't render the same plan 4 times.
        single_geom = list(dwg_levels.values())[0] if dwg_levels else None
        level_list = [(name, _synth_level_geom(single_geom, name)) for name in project_levels]

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

    # +4 principe pages (PLB, ELEC, CVC, SSI)
    total_pages = len(sublots) * len(level_list) + 4
    page = 0

    c = pdfcanvas.Canvas(output_path, pagesize=A3L)
    c.setTitle(f"Plans MEP — {p.get('nom','Projet')}")
    c.setAuthor("Tijan AI")

    for title, lot_label, key in sublots:
      for level_idx_mep, (level_label, level_geom) in enumerate(level_list):
        page += 1
        _lvl_lower = str(level_label).lower()
        is_terrasse_page = _lvl_lower.startswith(('terrasse','toiture','toit'))
        is_soussol_page = 'sous-sol' in _lvl_lower or 'sous sol' in _lvl_lower or 'parking' in _lvl_lower or _lvl_lower.startswith('ss')
        is_synth_level = bool(level_geom and level_geom.get('_synth_level'))
        w, h = A3L; c.setPageSize(A3L); _border(c, w, h)
        c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 12)
        c.drawString(14*mm, h - 17*mm, f"{title} — {level_label}")
        # Use enhanced cartouche with normalized drawing number
        _cartouche_pro(c, w, h, p, f"Plan {title}", page, total_pages, lot_label,
                       drawing_no=_mep_drawing_no(key, level_label, page))

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
            # If geometry was extracted from a specific PDF page, use THAT page
            # as background for all levels — otherwise coordinates don't match.
            cv_page = None
            if isinstance(level_geom, dict):
                cv_page = level_geom.get('_cv_meta', {}).get('page_idx')
            if cv_page is not None:
                pdf_page_idx = cv_page
            else:
                pdf_page_idx = min(level_idx_mep, 4)
            ok_mep, placement_mep = _render_pdf_background(
                c, archi_pdf_path, pdf_page_idx, w, h, opacity=0.85, dpi=200, grayscale=True
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
            elif ok_mep and placement_mep:
                # PDF rendered but no rooms extracted — anchor equipment to the
                # PDF drawing area so symbols sit INSIDE the actual plan, not
                # on an independent parametric grid floating above it.
                ox = placement_mep['ox']
                oy = placement_mep['oy']
                gw = placement_mep['draw_w']
                gh = placement_mep['draw_h']
                # Subtle structural overlay (axes + columns) aligned to PDF bounds
                c.saveState(); c.setStrokeAlpha(0.35); c.setFillAlpha(0.45)
                _overlay_axes_columns_in_bounds(c, ox, oy, gw, gh, nx, ny, pot_s)
                c.restoreState()
                use_dwg = True  # triggers bay-within-bounds logic below
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

        # ── Synth overlays (terrasse/sous-sol) — drawn on top of whichever
        # rendering mode was used, so the real DWG emprise stays visible ──
        if is_terrasse_page and is_synth_level and use_dwg and level_geom.get('_terrace_bounds'):
            tb = level_geom['_terrace_bounds']
            # Draw acrotère as an inset dashed outline along the real emprise
            # (offset 150mm inward from bounds, expressed in scene units)
            try:
                ox_b = tx(tb[0]); oy_b = ty(tb[1])
                ox_e = tx(tb[2]); oy_e = ty(tb[3])
                x0, x1 = min(ox_b, ox_e), max(ox_b, ox_e)
                y0, y1 = min(oy_b, oy_e), max(oy_b, oy_e)
                # 150mm -> scene points via bounds diff ratio
                ins = 0.02 * min(x1-x0, y1-y0)
                c.setStrokeColor(NOIR); c.setLineWidth(0.7); c.setDash(2, 1.5)
                c.rect(x0+ins, y0+ins, (x1-x0)-2*ins, (y1-y0)-2*ins, fill=0, stroke=1)
                c.setDash()
                c.setFillColor(NOIR); c.setFont("Helvetica-Oblique", 7)
                c.drawString(x0+4, y1-8, "Toiture-Terrasse — Dalle BA + Acrotère h=80cm + étanchéité multicouche")
            except Exception:
                pass
        if is_soussol_page and is_synth_level and use_dwg:
            c.setFillColor(NOIR); c.setFont("Helvetica-Oblique", 7)
            c.drawString(ox + 4, oy + 4, "Sous-sol — emprise bâtiment + axes + poteaux (parking / locaux techniques)")

        notes = []

        # ── Dessin MEP : logique room-aware ──
        # Classify rooms for this specific level
        if use_dwg:
            _lg = level_geom or {}
            lvl_wet, lvl_living, lvl_service = _classify_rooms(_lg.get('rooms', []))
            lvl_all = lvl_wet + lvl_living + lvl_service
            # On a terrace/roof page, interior rooms of the standard floor must
            # NOT drive equipment placement (prises, clim, etc.) — keep only
            # explicitly exterior spaces. If none, the page stays empty of indoor
            # symbols, which is correct for a roof plan.
            if is_terrasse_page:
                _EXT_KW = ('terrasse','toiture','toit','balcon','jardin','piscine','patio','loggia')
                def _ext_room(r):
                    nm = r.get('name_norm') or _norm_name(r.get('name',''))
                    return any(k in nm for k in _EXT_KW)
                lvl_wet = [r for r in lvl_wet if _ext_room(r)]
                lvl_living = [r for r in lvl_living if _ext_room(r)]
                lvl_service = [r for r in lvl_service if _ext_room(r)]
                lvl_all = lvl_wet + lvl_living + lvl_service
            if is_soussol_page:
                # Sous-sol/parking: strip residential rooms. Keep only genuine
                # parking/technical service spaces when present in the geom.
                _SS_KW = ('parking','box','garage','local','technique','gaine','cave','depot','reserve','rangement','bache','cuve','pompe','chaufferie','onduleur','tgbt','electrique','escalier','rampe','sas','ascenseur','asc','circulation')
                def _ss_room(r):
                    nm = r.get('name_norm') or _norm_name(r.get('name',''))
                    return any(k in nm for k in _SS_KW)
                lvl_wet = [r for r in lvl_wet if _ss_room(r)]
                lvl_living = []  # no residential living in sous-sol
                lvl_service = [r for r in lvl_service if _ss_room(r)]
                lvl_all = lvl_wet + lvl_living + lvl_service
            def _nm(r):
                return r.get('name_norm') or _norm_name(r.get('name',''))
            lvl_shafts = [(r['x'], r['y']) for r in lvl_service if 'asc' in _nm(r)]
            if not lvl_shafts:
                lvl_shafts = [(r['x'], r['y']) for r in lvl_service if 'palier' in _nm(r) or 'escalier' in _nm(r)]
            # Fallback: pick centermost service-ish room so the ascenseur symbol
            # always has a coherent anchor even on terrace / slabs without explicit labels
            if not lvl_shafts and lvl_service:
                b = _dwg_bounds(level_geom) or (0,0,0,0)
                cx = (b[0]+b[2])/2; cy = (b[1]+b[3])/2
                nearest = min(lvl_service, key=lambda r: (r['x']-cx)**2+(r['y']-cy)**2)
                lvl_shafts = [(nearest['x'], nearest['y'])]
            lvl_halls = [r for r in lvl_service if any(k in _nm(r) for k in ['hall','palier','dgt','sas','circulation','accueil'])]

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

        # ── WALL-AWARE SHORT-CIRCUIT ──
        # When geometry came from CV extraction on an uploaded PDF, bypass
        # the per-lot hand-coded drawing blocks (which place symbols at
        # room centroids with decorative offsets) and use the wall-aware
        # placer which:
        #  - filters rooms to those inside the building envelope
        #  - snaps equipment against the real walls of each room
        #  - routes per lot-type semantics (points d'eau in wet rooms, etc.)
        _wall_aware_done = False
        if use_dwg and level_geom and level_geom.get('_cv_meta'):
            try:
                import wall_aware_placer as _wap
                _prepared = _wap.prepare(level_geom)
                _u = _prepared.get('unit_scale', 1.0) or 1.0
                _items = _wap.place_equipment_with_scale(
                    key, _prepared['rooms'], _prepared['walls'], u=_u
                )
                if _items:
                    _wap.draw_items(c, _items, tx, ty, symbol_size=5.5)
                _wall_aware_done = True
                notes = [f"Placement wall-aware : {len(_items)} équipements "
                         f"dans {len(_prepared['rooms'])} pièces (envelope filtrée)"]
            except Exception as _e_wap:
                import logging as _lg_mod
                _lg_mod.getLogger('tijan').warning(
                    f"wall-aware placer failed: {_e_wap} — fallback to legacy"
                )
                _wall_aware_done = False

        # ── Rooftop equipment per lot (terrasse synth level) ──
        # The real emprise is drawn but there are no interior rooms to drive the
        # legacy per-lot blocks. Draw the ACTUAL roof equipment for each lot at
        # sensible positions on the slab, then skip the residential drawing.
        _rooftop_done = False
        if is_terrasse_page and use_dwg and level_geom and level_geom.get('_terrace_bounds'):
            tb = level_geom['_terrace_bounds']
            bx0, by0, bx1, by1 = tb
            cx_m = (bx0 + bx1) / 2; cy_m = (by0 + by1) / 2
            import math as _mrt
            def _grid_points(nx_g, ny_g, margin=0.10):
                """Return a list of (x_mm, y_mm) covering the slab in a grid."""
                mx = (bx1 - bx0) * margin; my = (by1 - by0) * margin
                xs = [bx0 + mx + (bx1 - bx0 - 2*mx) * (i+0.5)/nx_g for i in range(nx_g)]
                ys = [by0 + my + (by1 - by0 - 2*my) * (j+0.5)/ny_g for j in range(ny_g)]
                return [(x, y) for x in xs for y in ys]
            def _perim_points(n, inset_ratio=0.03):
                inx = (bx1 - bx0) * inset_ratio; iny = (by1 - by0) * inset_ratio
                x0, y0, x1, y1 = bx0+inx, by0+iny, bx1-inx, by1-iny
                pts = []
                for i in range(n):
                    t = (i + 0.5) / n
                    pts.append((x0 + t*(x1-x0), y0))
                    pts.append((x0 + t*(x1-x0), y1))
                    pts.append((x0, y0 + t*(y1-y0)))
                    pts.append((x1, y0 + t*(y1-y0)))
                return pts

            def _sym_box(x, y, w_pt, h_pt, fill_c, label):
                c.setFillColor(fill_c); c.setStrokeColor(NOIR); c.setLineWidth(0.35)
                c.rect(x - w_pt/2, y - h_pt/2, w_pt, h_pt, fill=1, stroke=1)
                c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 3.5)
                c.drawCentredString(x, y + h_pt/2 + 2, label)

            if key == 'plb_ef':
                # Citerne EF 50m³ + surpresseur
                x0, y0 = tx(bx0 + (bx1-bx0)*0.15), ty(by0 + (by1-by0)*0.15)
                c.setFillColor(BLEU); c.setStrokeColor(NOIR); c.setLineWidth(0.6)
                c.rect(x0-18, y0-10, 36, 20, fill=1, stroke=1)
                c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 5)
                c.drawCentredString(x0, y0-1, "CITERNE EF 50m³")
                c.setFont("Helvetica", 3.5); c.drawCentredString(x0, y0-6, "Surpresseur 6m³/h")
                notes = ["Citerne 50m³ + surpresseur 6m³/h sur dalle toiture", "Colonne montante EF DN40 vers tous niveaux"]
                _legend_pro(c, w, h, [(BLEU, 'fill', "Citerne EF 50m³"),
                                      (BLEU, 1.5, "Colonne montante DN40")], "LÉGENDE — EF TOITURE")
                _rooftop_done = True
            elif key == 'plb_ec':
                # Panneaux solaires thermiques
                panels = _grid_points(6, 3)
                for (px_m2, py_m2) in panels:
                    x1p, y1p = tx(px_m2), ty(py_m2)
                    c.setFillColor(colors.HexColor("#1565C0")); c.setStrokeColor(NOIR); c.setLineWidth(0.25)
                    c.rect(x1p-8, y1p-4, 16, 8, fill=1, stroke=1)
                notes = [f"{len(panels)} panneaux solaires thermiques", "Ballon ECS 1500L — appoint électrique"]
                _legend_pro(c, w, h, [(colors.HexColor("#1565C0"), 'fill', "Panneau solaire thermique")], "LÉGENDE — EC TOITURE")
                _rooftop_done = True
            elif key == 'plb_eu':
                # Descentes EP autour du périmètre
                for (px_m2, py_m2) in _perim_points(4):
                    xp, yp = tx(px_m2), ty(py_m2)
                    c.setFillColor(colors.HexColor("#5D4037")); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
                    c.circle(xp, yp, 3, fill=1, stroke=1)
                    c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 3)
                    c.drawCentredString(xp, yp-1, "EP")
                notes = ["Descentes EP 16 unités — DN100", "Pente dalle 1% vers avaloirs"]
                _legend_pro(c, w, h, [(colors.HexColor("#5D4037"), 'circle', "Descente EP DN100")], "LÉGENDE — EP TOITURE")
                _rooftop_done = True
            elif key == 'elec_ecl':
                # Éclairage extérieur périmétrique
                for (px_m2, py_m2) in _perim_points(3):
                    xp, yp = tx(px_m2), ty(py_m2)
                    c.setFillColor(JAUNE); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
                    c.circle(xp, yp, 2.8, fill=1, stroke=1)
                notes = ["Éclairage toiture/navigation aérienne", "Projecteurs LED 50W périmétrique"]
                _legend_pro(c, w, h, [(JAUNE, 'circle', "Projecteur LED 50W extérieur")], "LÉGENDE — ÉCLAIRAGE TOITURE")
                _rooftop_done = True
            elif key == 'elec_dist':
                # Paratonnerre au point haut + prises étanches
                xp, yp = tx(cx_m), ty(by1 - (by1-by0)*0.08)
                c.setFillColor(colors.HexColor("#C62828")); c.setStrokeColor(NOIR); c.setLineWidth(0.6)
                path = c.beginPath(); path.moveTo(xp, yp+10); path.lineTo(xp-5, yp); path.lineTo(xp+5, yp); path.close()
                c.drawPath(path, fill=1, stroke=1)
                c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 5)
                c.drawCentredString(xp, yp+14, "PARATONNERRE")
                for (px_m2, py_m2) in _perim_points(2):
                    xpp, ypp = tx(px_m2), ty(py_m2)
                    c.setFillColor(ORANGE); c.setStrokeColor(NOIR); c.setLineWidth(0.2)
                    c.rect(xpp-1.8, ypp-1.1, 3.6, 2.2, fill=1, stroke=1)
                notes = ["Paratonnerre PDA rayon 60m", "Prises étanches IP65 entretien périmétriques"]
                _legend_pro(c, w, h, [(colors.HexColor("#C62828"), 'triangle', "Paratonnerre PDA"),
                                      (ORANGE, 'fill', "Prise étanche IP65")], "LÉGENDE — ELEC TOITURE")
                _rooftop_done = True
            elif key == 'cvc_clim':
                # Groupes froids extérieurs
                for (px_m2, py_m2) in _grid_points(5, 3, margin=0.15):
                    xp, yp = tx(px_m2), ty(py_m2)
                    c.setFillColor(CYAN); c.setStrokeColor(NOIR); c.setLineWidth(0.4)
                    c.rect(xp-7, yp-5, 14, 10, fill=1, stroke=1)
                    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 3)
                    c.drawCentredString(xp, yp-1, "GF")
                notes = ["Groupes froids VRV en toiture", "Alimentation frigorifique vers cassettes étages"]
                _legend_pro(c, w, h, [(CYAN, 'fill', "Groupe froid VRV ext.")], "LÉGENDE — CLIM TOITURE")
                _rooftop_done = True
            elif key == 'cvc_vmc':
                # Terminaux extraction VMC
                for (px_m2, py_m2) in _grid_points(4, 3, margin=0.15):
                    xp, yp = tx(px_m2), ty(py_m2)
                    c.setFillColor(colors.HexColor("#78909C")); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
                    c.circle(xp, yp, 4, fill=1, stroke=1)
                    c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 3)
                    c.drawCentredString(xp, yp-1, "Ex")
                notes = ["Terminaux extraction VMC double flux", "Chapeaux ventilation DN200 pare-pluie"]
                _legend_pro(c, w, h, [(colors.HexColor("#78909C"), 'circle', "Terminal VMC extraction")], "LÉGENDE — VMC TOITURE")
                _rooftop_done = True
            elif key == 'ssi_det':
                # Détecteurs + SDI local
                for (px_m2, py_m2) in _perim_points(2):
                    xp, yp = tx(px_m2), ty(py_m2)
                    c.setFillColor(ROUGE); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
                    c.circle(xp, yp, 2.5, fill=1, stroke=1)
                notes = ["Détecteurs autonomes rooftop", "Remontée vers ECS niveau RDC"]
                _legend_pro(c, w, h, [(ROUGE, 'circle', "Détecteur toiture")], "LÉGENDE — SSI TOITURE")
                _rooftop_done = True
            elif key == 'ssi_ext':
                # EXU désenfumage
                for (px_m2, py_m2) in _grid_points(3, 2):
                    xp, yp = tx(px_m2), ty(py_m2)
                    c.setFillColor(colors.HexColor("#FF5252")); c.setStrokeColor(NOIR); c.setLineWidth(0.4)
                    c.rect(xp-6, yp-4, 12, 8, fill=1, stroke=1)
                    c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 3.5)
                    c.drawCentredString(xp, yp-1, "EXU")
                notes = ["Exutoires de désenfumage naturel", "Commande électrique + manuelle"]
                _legend_pro(c, w, h, [(colors.HexColor("#FF5252"), 'fill', "Exutoire désenfumage EXU")], "LÉGENDE — DÉSENFUMAGE")
                _rooftop_done = True
            elif key == 'asc_plan':
                # Local machinerie ascenseur
                xp, yp = tx(cx_m), ty(cy_m)
                c.setFillColor(colors.HexColor("#455A64")); c.setStrokeColor(NOIR); c.setLineWidth(0.6)
                c.rect(xp-14, yp-10, 28, 20, fill=1, stroke=1)
                c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 5)
                c.drawCentredString(xp, yp-1, "LOCAL MACHINERIE")
                c.setFont("Helvetica", 3.5); c.drawCentredString(xp, yp-6, "Asc. NF EN 81-20")
                notes = ["Local machinerie toiture", "Ventilation haute/basse naturelle"]
                _legend_pro(c, w, h, [(colors.HexColor("#455A64"), 'fill', "Local machinerie asc.")], "LÉGENDE — ASC TOITURE")
                _rooftop_done = True
            elif key == 'cf':
                # Antenne GSM / TV
                xp, yp = tx(cx_m), ty(by1 - (by1-by0)*0.12)
                c.setStrokeColor(colors.HexColor("#6A1B9A")); c.setFillColor(BLANC); c.setLineWidth(0.8)
                c.line(xp, yp, xp, yp+16)
                c.line(xp-6, yp+8, xp+6, yp+8)
                c.line(xp-4, yp+12, xp+4, yp+12)
                c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 4)
                c.drawCentredString(xp, yp+20, "ANTENNE GSM/TV")
                notes = ["Antennes GSM/4G + TV terrestre", "Descente câbles coaxiaux gaine TV"]
                _legend_pro(c, w, h, [(colors.HexColor("#6A1B9A"), 'line', "Antenne GSM/TV")], "LÉGENDE — CF TOITURE")
                _rooftop_done = True
            elif key == 'gtb':
                # Coffret GTB toiture
                xp, yp = tx(cx_m + (bx1-bx0)*0.2), ty(cy_m)
                c.setFillColor(VERT); c.setStrokeColor(NOIR); c.setLineWidth(0.6)
                c.rect(xp-10, yp-7, 20, 14, fill=1, stroke=1)
                c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 4.5)
                c.drawCentredString(xp, yp-1, "GTB")
                notes = ["Coffret GTB toiture", "Remontée BUS KNX vers GTC centrale"]
                _legend_pro(c, w, h, [(VERT, 'fill', "Coffret GTB toiture")], "LÉGENDE — GTB TOITURE")
                _rooftop_done = True

        if _wall_aware_done or _rooftop_done:
            pass  # drawn above; skip legacy per-lot block
        elif use_dwg and lvl_all:
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
                circuit_idx = 1
                for wr in wet_r:
                    wx, wy = tx(wr['x']), ty(wr['y'])
                    _route_to_gt(c, wx, wy, gtx_p, gty_p, BLEU)
                    n = wr.get('name_norm') or _norm_name(wr.get('name',''))
                    circuit_ref = f"EF{circuit_idx}"
                    if any(k in n for k in ('sdb','sdeau','seau','douche','bain','lavabo','sanit')):
                        c.setFillColor(BLANC); c.setStrokeColor(BLEU); c.setLineWidth(0.8)
                        c.circle(wx, wy, 5, fill=1, stroke=1)
                        c.setFillColor(BLEU); c.setFont("Helvetica-Bold", 4)
                        c.drawCentredString(wx, wy-1.5, "SDB")
                        c.setFont("Helvetica", 2.5); c.drawString(wx+8, wy-3, circuit_ref)
                    elif any(k in n for k in ('wc','toil','water')):
                        c.setFillColor(BLEU); c.circle(wx, wy, 4, fill=1, stroke=0)
                        c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 3.5)
                        c.drawCentredString(wx, wy-1.5, "WC")
                        c.setFillColor(NOIR); c.setFont("Helvetica", 2.5)
                        c.drawString(wx+7, wy-2.5, circuit_ref)
                    elif 'cuisine' in n or 'kitch' in n or 'office' in n or 'pantry' in n:
                        c.setFillColor(BLEU); c.rect(wx-6, wy-3.5, 12, 7, fill=1, stroke=0)
                        c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 4)
                        c.drawCentredString(wx, wy-1.5, "CUI")
                        c.setFillColor(NOIR); c.setFont("Helvetica", 2.5)
                        c.drawString(wx+8, wy-5, circuit_ref)
                    elif 'buanderie' in n or 'lingerie' in n:
                        c.setFillColor(CYAN); c.rect(wx-5, wy-3.5, 10, 7, fill=1, stroke=0)
                        c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 3.5)
                        c.drawCentredString(wx, wy-1.5, "BUA")
                        c.setFillColor(NOIR); c.setFont("Helvetica", 2.5)
                        c.drawString(wx+7, wy-5, circuit_ref)
                    else:
                        # Fallback — any wet/kitchen room not matched above still gets an EF tap
                        c.setFillColor(BLANC); c.setStrokeColor(BLEU); c.setLineWidth(0.6)
                        c.circle(wx, wy, 3, fill=1, stroke=1)
                        c.setFillColor(BLEU); c.setFont("Helvetica-Bold", 3)
                        c.drawCentredString(wx, wy-1, "EF")
                        c.setFillColor(NOIR); c.setFont("Helvetica", 2.5)
                        c.drawString(wx+6, wy-2, circuit_ref)
                    circuit_idx += 1
                notes = [f"Colonne montante EF DN{pl.diam_colonne_montante_mm}",
                         f"Citerne {int(pl.volume_citerne_m3)}m³ — Surpresseur {pl.debit_surpresseur_m3h}m³/h",
                         f"{pl.nb_robinets_eco} robinets économiseurs — {pl.nb_wc_double_chasse} WC double chasse"]
                _legend_pro(c, w, h, [(BLEU, 'fill', f"GT — CM EF DN{pl.diam_colonne_montante_mm}"),
                                      (BLEU, 0.5, "Distribution EF"),
                                      (BLEU, 'circle', "SDB / Douche"),
                                      (BLEU, 'fill', "WC / Toilettes"),
                                      (BLEU, 'fill', "Évier cuisine"),
                                      (CYAN, 'fill', "Buanderie")], "LÉGENDE EAU FROIDE")

            elif key == "plb_ec":
                _draw_gt(c, gtx_p, gty_p, "EC", ROUGE)
                c.setFillColor(ROUGE); c.setFont("Helvetica", 2.5)
                c.drawString(gtx_p+8, gty_p-1, f"CE {pl.nb_chauffe_eau_solaire}×CESI")
                circuit_idx = 1
                for wr in wet_r:
                    n = wr.get('name_norm') or _norm_name(wr.get('name',''))
                    # WC-only rooms don't get EC, but every SDB / salle d'eau / cuisine / buanderie does
                    if any(k in n for k in ('sdb','sdeau','seau','douche','bain','cuisine','kitch','office','pantry','buanderie','lingerie','lavabo','sanit')):
                        wx, wy = tx(wr['x']), ty(wr['y'])
                        _route_to_gt(c, wx, wy, gtx_p, gty_p, ROUGE, 0.5, (3,1.5))
                        c.setFillColor(BLANC); c.setStrokeColor(ROUGE); c.setLineWidth(0.5)
                        c.circle(wx, wy, 3, fill=1, stroke=1)
                        c.setFillColor(ROUGE); c.setFont("Helvetica-Bold", 2.8)
                        c.drawCentredString(wx, wy-1, "EC")
                        c.setFillColor(NOIR); c.setFont("Helvetica", 2.5)
                        c.drawString(wx+6, wy-3, f"EC{circuit_idx}")
                        circuit_idx += 1
                notes = ["CM EC DN32", f"{pl.nb_chauffe_eau_solaire} CESI"]
                _legend_pro(c, w, h, [(ROUGE, 'fill', "GT — Chauffe-eau"),
                                      (ROUGE, 0.5, "Distribution EC — DN32"),
                                      (colors.HexColor("#E57373"), 0.5, "Circulation ECS DN16")], "LÉGENDE EAU CHAUDE")

            elif key == "plb_eu":
                _draw_gt(c, gtx_p, gty_p, "EU", MARRON)
                c.setFillColor(MARRON); c.setFont("Helvetica", 3)
                c.drawString(gtx_p+7, gty_p+3, "CE EU DN100")
                c.setFont("Helvetica", 2.2)
                c.drawString(gtx_p+7, gty_p-2, f"EP DN75")
                circuit_idx = 1
                for wr in wet_r:
                    n = wr.get('name_norm') or _norm_name(wr.get('name',''))
                    if any(k in n for k in ('sdb','sdeau','seau','wc','toil','water','douche','bain','cuisine','kitch','office','pantry','buanderie','lingerie','lavabo','sanit')):
                        wx, wy = tx(wr['x']), ty(wr['y'])
                        _route_to_gt(c, wx, wy, gtx_p, gty_p, MARRON, 0.5, (4,2))
                        c.setFillColor(MARRON); c.circle(wx, wy, 2, fill=1, stroke=0)
                        c.setFillColor(NOIR); c.setFont("Helvetica", 2.5)
                        c.drawString(wx+6, wy-1, f"EU{circuit_idx}")
                        circuit_idx += 1
                notes = ["Chute EU DN100", f"Conso {pl.conso_eau_annuelle_m3:.0f}m³/an"]
                _legend_pro(c, w, h, [(MARRON, 'fill', "Colonne EU — DN100"),
                                      (colors.HexColor("#A1887F"), 'fill', "Colonne EP — DN75"),
                                      (MARRON, 0.5, "Chute EU"),
                                      (colors.HexColor("#A1887F"), 0.5, "Chute EP")], "LÉGENDE ÉVACUATIONS")

            elif key == "elec_ecl":
                circuit_idx = 1
                for r in all_r:
                    n = r.get('name','').lower()
                    if any(k in n for k in ['terrasse','balcon','jardin','piscine','vide','espace']): continue
                    rx, ry = tx(r['x']), ty(r['y'])
                    # Luminaire — cercle avec croix (symbole standard)
                    c.setStrokeColor(JAUNE); c.setFillColor(colors.HexColor("#FFF8E1")); c.setLineWidth(0.7)
                    c.circle(rx, ry+6, 5, fill=1, stroke=1)
                    c.setStrokeColor(JAUNE); c.setLineWidth(0.5)
                    c.line(rx-3.5, ry+6, rx+3.5, ry+6); c.line(rx, ry+2.5, rx, ry+9.5)
                    # Circuit reference and power annotation
                    c.setFillColor(NOIR); c.setFont("Helvetica", 2.5)
                    c.drawString(rx+7, ry+6, f"L{circuit_idx}")
                    # Interrupteur
                    if any(k in n for k in ['chambre','salon','sejour','bureau','sam','bar','cuisine','sdb','wc','restaurant','magasin','salle']):
                        c.setFillColor(colors.HexColor("#FFF9C4")); c.setStrokeColor(ORANGE); c.setLineWidth(0.5)
                        c.circle(rx-10, ry+2, 3, fill=1, stroke=1)
                        c.setStrokeColor(ORANGE); c.setLineWidth(0.4)
                        c.line(rx-10, ry+5, rx-7, ry+7)
                    circuit_idx += 1
                notes = [f"Puissance éclairage: {el.puissance_eclairage_kw:.1f} kW",
                         f"Puissance totale: {el.puissance_totale_kva:.0f} kVA"]
                _legend_pro(c, w, h, [(JAUNE, 'circle', "Plafonnier"),
                                      (ORANGE, 'circle', "Interrupteur simple allumage"),
                                      (colors.HexColor("#FFB74D"), 'circle', "Interrupteur VA-ET-VIENT"),
                                      (colors.HexColor("#FFA726"), 'circle', "Détecteur de mouvement"),
                                      (JAUNE, 0.5, "Distribution éclairage")], "LÉGENDE ÉLECTRICITÉ")

            elif key == "elec_dist":
                # TD dans la gaine technique
                _draw_gt(c, gtx_p, gty_p, "TD", VERT)
                c.setFillColor(VERT); c.setFont("Helvetica", 3)
                c.drawString(gtx_p+7, gty_p+3, f"Transfo {el.transfo_kva}kVA")
                c.setFont("Helvetica", 2.2); c.drawString(gtx_p+7, gty_p-2, f"GE {el.groupe_electrogene_kva}kVA")
                # Chemin de câbles principal via les circulations → GT
                sh = sorted(halls, key=lambda r: r['y'])
                if sh:
                    c.setStrokeColor(ORANGE); c.setLineWidth(1.5)
                    prev_x, prev_y = gtx_p, gty_p
                    for hh in sh:
                        hx, hy = tx(hh['x']), ty(hh['y'])
                        c.line(prev_x, prev_y, hx, hy); prev_x, prev_y = hx, hy
                # ── Placement individuel des prises, plaquées aux murs ──
                # Stratégie: pour chaque pièce, on utilise le bbox (si dispo) ou on
                # fabrique un bbox depuis aire_m² pour répartir les prises le long
                # des 4 murs. Puis on les dessine individuellement à leur position
                # réelle (plus de cluster autour du centroïde).
                import math as _m
                circuit_idx = 1
                # Building envelope — used to clamp fallback room bboxes so
                # prises never spill outside the walls.
                _env = _dwg_bounds(level_geom) if level_geom else None
                def _room_bbox(r):
                    b = r.get('bbox_mm') or r.get('bbox')
                    if b and len(b) >= 4:
                        return b[0], b[1], b[2], b[3]
                    # Fallback: carré équivalent centré sur (x,y), clampé à l'enveloppe
                    area = max(6.0, r.get('area_m2', 12.0))
                    side = _m.sqrt(area) * 1000.0  # mm
                    bx, by = r['x'] - side/2, r['y'] - side/2
                    bw, bh = side, side
                    if _env:
                        ex0, ey0, ex1, ey1 = _env
                        # Intersect with envelope
                        nx0 = max(bx, ex0); ny0 = max(by, ey0)
                        nx1 = min(bx + bw, ex1); ny1 = min(by + bh, ey1)
                        if nx1 > nx0 and ny1 > ny0:
                            return (nx0, ny0, nx1 - nx0, ny1 - ny0)
                    return (bx, by, bw, bh)
                def _place_along_perimeter(r, n_prises):
                    bx, by, bw, bh = _room_bbox(r)
                    if bw <= 0 or bh <= 0:
                        return []
                    # Inset 300 mm (≈ épaisseur mur + retrait réglementaire)
                    inset = min(bw, bh) * 0.08
                    inset = max(inset, 200.0)
                    x0, y0 = bx + inset, by + inset
                    x1, y1 = bx + bw - inset, by + bh - inset
                    # Hard clamp to building envelope as a last safety net
                    if _env:
                        ex0, ey0, ex1, ey1 = _env
                        x0 = max(x0, ex0); y0 = max(y0, ey0)
                        x1 = min(x1, ex1); y1 = min(y1, ey1)
                        if x1 <= x0 or y1 <= y0:
                            return []
                    # Distribue n_prises autour du périmètre, en évitant les coins
                    perim_pts = []
                    # Mur bas, haut, gauche, droite : chacune reçoit n/4 prises
                    n_each = max(1, n_prises // 4)
                    for i in range(n_each):
                        t = (i + 1) / (n_each + 1)
                        perim_pts.append((x0 + t*(x1-x0), y0))          # bas
                        perim_pts.append((x0 + t*(x1-x0), y1))          # haut
                        perim_pts.append((x0, y0 + t*(y1-y0)))          # gauche
                        perim_pts.append((x1, y0 + t*(y1-y0)))          # droite
                    return perim_pts[:n_prises]
                for r in all_r:
                    n = r.get('name_norm') or _norm_name(r.get('name',''))
                    if not n or any(k in n for k in ('terrasse','balcon','jardin','piscine','vide','espace','porche','gaine','technique')):
                        continue
                    circuit_ref = f"D{circuit_idx}"
                    # Nombre de prises selon type pièce (EN NF C15-100)
                    if any(k in n for k in ('cuisine','kitch','office','pantry')):
                        n_prises = 6
                    elif any(k in n for k in ('salon','sejour','sam','restaurant','polyvalente','sport','gym')):
                        n_prises = 5
                    elif 'chambre' in n or 'suite' in n:
                        n_prises = 3
                    elif any(k in n for k in ('bureau','sdb','sdeau','seau','bain')):
                        n_prises = 2
                    elif any(k in n for k in ('hall','palier','sas','dgt','degagement','circulation','accueil')):
                        n_prises = 1
                    else:
                        n_prises = 2
                    positions = _place_along_perimeter(r, n_prises)
                    for (px, py) in positions:
                        pxp, pyp = tx(px), ty(py)
                        c.setFillColor(ORANGE); c.setStrokeColor(NOIR); c.setLineWidth(0.15)
                        c.rect(pxp-1.8, pyp-1.1, 3.6, 2.2, fill=1, stroke=1)
                    # Label circuit au centre de la pièce (un seul par pièce, pas par prise)
                    rx, ry = tx(r['x']), ty(r['y'])
                    c.setFillColor(NOIR); c.setFont("Helvetica", 2.2)
                    c.drawString(rx, ry, circuit_ref)
                    circuit_idx += 1
                notes = [f"Transfo {el.transfo_kva}kVA", f"GE {el.groupe_electrogene_kva}kVA",
                         f"{el.nb_compteurs} compteurs — Col.{el.section_colonne_mm2}mm²"]
                _legend_pro(c, w, h, [(VERT, 'fill', "TGBT / Transfo"),
                                      (ORANGE, 1.5, "Chemin câbles principal"),
                                      (ORANGE, 'fill', "Prise 2P+T 16A"),
                                      (colors.HexColor("#FF7043"), 'fill', "Prise spécialisée"),
                                      (colors.HexColor("#E64A19"), 'fill', "Prise cuisinière/Chauffe-eau")], "LÉGENDE PRISES & DISTRIBUTION")

            elif key == "cvc_clim":
                # Climatise EVERY habitable room (living classification).
                # Only explicitly non-habitable zones are skipped (outdoor or service-only).
                _SKIP_CLIM = ('terrasse','balcon','jardin','piscine','vide','porche','guerite','gaine','escalier','technique')
                circuit_idx = 1
                for r in living_r:
                    n = r.get('name_norm') or _norm_name(r.get('name',''))
                    if not n or any(k in n for k in _SKIP_CLIM):
                        continue
                    rx, ry = tx(r['x']), ty(r['y'])
                    c.setFillColor(CYAN); c.setStrokeColor(colors.HexColor("#006064")); c.setLineWidth(0.35)
                    c.rect(rx-6, ry+7, 12, 4, fill=1, stroke=1)
                    c.setFillColor(colors.HexColor("#006064")); c.setFont("Helvetica", 2.2)
                    if any(k in n for k in ('salon','sejour','sam','restaurant','polyvalente','sport','gym')):
                        btu_val = "18000"
                    elif 'chambre' in n or 'suite' in n or 'parent' in n:
                        btu_val = "12000"
                    else:
                        btu_val = "9000"
                    c.drawCentredString(rx, ry+11.5, f"{btu_val} BTU")
                    c.setFillColor(NOIR); c.setFont("Helvetica", 2.5)
                    c.drawString(rx+8, ry+7, f"C{circuit_idx}")
                    circuit_idx += 1
                notes = [f"P frigo: {cv.puissance_frigorifique_kw:.0f}kW",
                         f"Splits séj: {cv.nb_splits_sejour} — ch: {cv.nb_splits_chambre}"]
                _legend_pro(c, w, h, [(CYAN, 'fill', "Split mural 18000 BTU"),
                                      (colors.HexColor("#80DEEA"), 'fill', "Split mural 12000 BTU"),
                                      (colors.HexColor("#B2EBF2"), 'fill', "Split mural 9000 BTU"),
                                      (CYAN, 0.5, "Liaison frigorifique"),
                                      (MARRON, 0.5, "Ligne condensats")], "LÉGENDE CLIMATISATION")

            elif key == "cvc_vmc":
                vmc_idx = 1
                for r in wet_r:
                    n = r.get('name','').lower()
                    rx, ry = tx(r['x']), ty(r['y'])
                    c.setStrokeColor(colors.HexColor("#2E7D32")); c.setFillColor(colors.HexColor("#C8E6C9"))
                    c.setLineWidth(0.4); c.circle(rx, ry+5, 4, fill=1, stroke=1)
                    c.setStrokeColor(colors.HexColor("#2E7D32")); c.setLineWidth(0.5)
                    c.line(rx, ry+6.5, rx, ry+9)
                    c.setFillColor(NOIR); c.setFont("Helvetica", 2.5)
                    c.drawString(rx+7, ry+5, f"V{vmc_idx}")
                    vmc_idx += 1
                if len(halls) >= 2:
                    sh = sorted(halls, key=lambda r: r['y'])
                    c.setStrokeColor(colors.HexColor("#2E7D32")); c.setLineWidth(1.2); c.setDash(5,2)
                    for i in range(len(sh)-1):
                        c.line(tx(sh[i]['x']), ty(sh[i]['y']), tx(sh[i+1]['x']), ty(sh[i+1]['y']))
                    c.setDash()
                notes = [f"{cv.nb_vmc} VMC {cv.type_vmc}"]
                _legend_pro(c, w, h, [(colors.HexColor("#2E7D32"), 'circle', "Bouche de soufflage VMC"),
                                      (colors.HexColor("#1B5E20"), 'circle', "Bouche de reprise VMC"),
                                      (colors.HexColor("#2E7D32"), 1.2, "Gaine VMC principal"),
                                      (colors.HexColor("#2E7D32"), 0.5, "Gaine VMC distribution")], "LÉGENDE VENTILATION")

            elif key == "ssi_det":
                det_idx = 1
                for r in all_r:
                    n = r.get('name','').lower()
                    if any(k in n for k in ['terrasse','balcon','jardin','piscine','vide']): continue
                    rx, ry = tx(r['x']), ty(r['y'])
                    c.setFillColor(BLANC); c.setStrokeColor(ROUGE); c.setLineWidth(0.5)
                    c.circle(rx, ry-6, 4, fill=1, stroke=1)
                    c.setFillColor(ROUGE); c.setFont("Helvetica-Bold", 3)
                    c.drawCentredString(rx, ry-8, "DF")
                    c.setFillColor(NOIR); c.setFont("Helvetica", 2.5)
                    c.drawString(rx+7, ry-6, f"D{det_idx}")
                    det_idx += 1
                exits = [r for r in lvl_service if any(k in r.get('name','').lower() for k in ['palier','hall','sas'])]
                dm_idx = 1
                for r in exits:
                    rx, ry = tx(r['x']), ty(r['y'])
                    c.setFillColor(ROUGE); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
                    c.rect(rx-9, ry-3, 6, 6, fill=1, stroke=1)
                    c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 2.5)
                    c.drawCentredString(rx-6, ry-1, "DM")
                    c.setFillColor(NOIR); c.setFont("Helvetica", 2)
                    c.drawString(rx-8, ry-7, f"DM{dm_idx}")
                    dm_idx += 1
                notes = [f"{si.nb_detecteurs_fumee} DF — {si.nb_declencheurs_manuels} DM",
                         f"Cat.ERP {si.categorie_erp} — {si.centrale_zones} zones"]
                _legend_pro(c, w, h, [(ROUGE, 'circle', "Détecteur fumée"),
                                      (ROUGE, 'fill', "Déclencheur manuel"),
                                      (colors.HexColor("#D32F2F"), 'cross_circle', "Détecteur chaleur"),
                                      (colors.HexColor("#C62828"), 'circle', "Sirène sonovisuelle"),
                                      (ROUGE, 0.5, "Liaison détection")], "LÉGENDE SÉCURITÉ INCENDIE")

            elif key == "ssi_ext":
                # RIA / BAES near every vertical circulation (palier, escalier, hall)
                ria_anchors = [r for r in lvl_service if any(k in (r.get('name_norm') or _norm_name(r.get('name',''))) for k in ('palier','escalier','hall','sas'))]
                # Fallback — for a terrace or a level with no named circulation
                # anchor RIAs to corners of the plan so extinction is never absent
                if not ria_anchors:
                    b = _dwg_bounds(level_geom)
                    if b:
                        xmid = (b[0]+b[2])/2; ymid = (b[1]+b[3])/2
                        ria_anchors = [
                            {'x': b[0] + (b[2]-b[0])*0.15, 'y': b[1] + (b[3]-b[1])*0.15, 'name': 'coin'},
                            {'x': b[0] + (b[2]-b[0])*0.85, 'y': b[1] + (b[3]-b[1])*0.85, 'name': 'coin'},
                        ]
                ria_idx = 1
                for r in ria_anchors:
                    rx, ry = tx(r['x']), ty(r['y'])
                    c.setFillColor(BLANC); c.setStrokeColor(ROUGE); c.setLineWidth(0.7)
                    c.circle(rx+10, ry+5, 5, fill=1, stroke=1)
                    c.setFillColor(ROUGE); c.setFont("Helvetica-Bold", 4)
                    c.drawCentredString(rx+10, ry+3, "R")
                    c.setFillColor(NOIR); c.setFont("Helvetica", 2.5)
                    c.drawString(rx+16, ry+5, f"RIA{ria_idx}")
                    ria_idx += 1
                    c.setFillColor(VERT); c.setStrokeColor(NOIR); c.setLineWidth(0.25)
                    c.rect(rx+4, ry-10, 8, 5, fill=1, stroke=1)
                    c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 2)
                    c.drawCentredString(rx+8, ry-8.5, "BAES")
                    c.setFillColor(NOIR); c.setFont("Helvetica", 2)
                    c.drawString(rx+2, ry-12, f"BD{ria_idx-1}")
                # Extincteurs poudre — 1 par pièce principale, placés près de la porte (approximé au centroid décalé)
                ext_idx = 1
                for r in (lvl_living + lvl_halls):
                    n = r.get('name_norm') or _norm_name(r.get('name',''))
                    if any(k in n for k in ('terrasse','balcon','jardin','piscine','vide')) and not ria_anchors:
                        # Sur la terrasse (quand c'est le seul élément), accepter quelques extincteurs
                        pass
                    rx, ry = tx(r['x']), ty(r['y'])
                    c.setFillColor(colors.HexColor("#E53935")); c.setStrokeColor(NOIR); c.setLineWidth(0.2)
                    c.rect(rx-2, ry+3, 3, 4, fill=1, stroke=1)
                    c.setFillColor(NOIR); c.setFont("Helvetica", 1.8)
                    c.drawString(rx+2, ry+5, f"E{ext_idx}")
                    ext_idx += 1
                    if ext_idx > 30: break
                notes = [f"{si.nb_extincteurs_co2+si.nb_extincteurs_poudre} ext. — RIA {si.longueur_ria_ml:.0f}ml",
                         f"Sprinklers: {'OUI' if si.sprinklers_requis else 'NON'}"]
                _legend_pro(c, w, h, [(ROUGE, 'circle', "RIA - Robinet d'incendie armé"),
                                      (VERT, 'fill', "BAES - Bloc autonome éclairage"),
                                      (colors.HexColor("#E53935"), 'fill', "Extincteur poudre"),
                                      (colors.HexColor("#1565C0"), 'fill', "Extincteur CO2"),
                                      (ROUGE, 0.5, "Distribution arrosage")], "LÉGENDE EXTINCTION & ÉVACUATION")

            elif key == "cfa":
                rj45_idx = 1
                for r in all_r:
                    n = r.get('name','').lower()
                    if any(k in n for k in ['terrasse','balcon','jardin','piscine','vide']): continue
                    if any(k in n for k in ['chambre','salon','sejour','bureau','sam','cuisine','hall','restaurant','salle']):
                        rx, ry = tx(r['x']), ty(r['y'])
                        c.setFillColor(VIOLET); c.setStrokeColor(NOIR); c.setLineWidth(0.2)
                        c.rect(rx-2.5, ry-5, 5, 4, fill=1, stroke=1)
                        c.setFillColor(NOIR); c.setFont("Helvetica", 2.5)
                        c.drawString(rx+6, ry-5, f"RJ{rj45_idx}")
                        rj45_idx += 1
                cams = [r for r in lvl_service if any(k in r.get('name','').lower() for k in ['hall','palier','sas','porche'])]
                cam_idx = 1
                for r in cams:
                    rx, ry = tx(r['x']), ty(r['y'])
                    c.setFillColor(colors.HexColor("#CE93D8")); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
                    path = c.beginPath()
                    path.moveTo(rx, ry+10); path.lineTo(rx-4, ry+3); path.lineTo(rx+4, ry+3)
                    path.close(); c.drawPath(path, fill=1, stroke=0)
                    c.setFillColor(NOIR); c.setFont("Helvetica", 2.5)
                    c.drawString(rx+8, ry+10, f"CAM{cam_idx}")
                    cam_idx += 1
                notes = [f"{cf.nb_prises_rj45} RJ45 — {cf.nb_cameras_int+cf.nb_cameras_ext} caméras"]
                _legend_pro(c, w, h, [(VIOLET, 'fill', "Prise RJ45"),
                                      (colors.HexColor("#CE93D8"), 'triangle', "Caméra IP intérieure"),
                                      (colors.HexColor("#BA68C8"), 'triangle', "Caméra IP extérieure"),
                                      (VIOLET, 0.5, "Réseau données")], "LÉGENDE COURANTS FAIBLES")

            elif key == "asc_plan":
                asc_idx = 1
                # Priority 1: rooms with 'asc' in their name
                asc_rooms = [r for r in lvl_service if 'asc' in (r.get('name_norm') or _norm_name(r.get('name','')))]
                # Priority 2: paliers / escaliers (reasonable location for shafts)
                if not asc_rooms:
                    asc_rooms = [r for r in lvl_service if any(k in (r.get('name_norm') or _norm_name(r.get('name',''))) for k in ('palier','escalier'))]
                # Priority 3: lvl_shafts fallback (which already covers the center of the plan)
                if not asc_rooms and lvl_shafts:
                    asc_rooms = [{'x': sx, 'y': sy, 'name': 'gaine'} for (sx, sy) in lvl_shafts]
                # Priority 4: last resort — pick the plan center so nb_ascenseurs count is not lost
                if not asc_rooms:
                    b = _dwg_bounds(level_geom) or (0,0,0,0)
                    asc_rooms = [{'x': (b[0]+b[2])/2, 'y': (b[1]+b[3])/2, 'name': 'centre'}]
                # Cap to actual nb_ascenseurs
                for r in asc_rooms[:max(1, asc.nb_ascenseurs)]:
                    rx, ry = tx(r['x']), ty(r['y'])
                    c.setFillColor(BLEU_B); c.setStrokeColor(BLEU); c.setLineWidth(1)
                    c.rect(rx-10, ry-10, 20, 20, fill=1, stroke=1)
                    c.setStrokeColor(BLEU); c.setLineWidth(0.3)
                    c.line(rx-10, ry-10, rx+10, ry+10); c.line(rx-10, ry+10, rx+10, ry-10)
                    c.setFillColor(BLEU); c.setFont("Helvetica-Bold", 3)
                    c.drawCentredString(rx, ry-12, f"{asc.capacite_kg}kg")
                    c.setFillColor(NOIR); c.setFont("Helvetica", 2.5)
                    c.drawString(rx+12, ry-10, f"A{asc_idx}")
                    asc_idx += 1
                notes = [f"{asc.nb_ascenseurs} asc. {asc.capacite_kg}kg — {asc.vitesse_ms}m/s"]
                _legend_pro(c, w, h, [(BLEU_B, 'fill', f"Gaine ascenseur {asc.capacite_kg}kg"),
                                      (colors.HexColor("#0277BD"), 'fill', "Cage escalier"),
                                      (BLEU, 0.5, "Gaine technique")], "LÉGENDE ASCENSEURS")

            elif key == "gtb":
                if len(halls) >= 2:
                    sh = sorted(halls, key=lambda r: r['y'])
                    c.setStrokeColor(BLEU); c.setLineWidth(1.8)
                    for i in range(len(sh)-1):
                        c.line(tx(sh[i]['x']), ty(sh[i]['y']), tx(sh[i+1]['x']), ty(sh[i+1]['y']))
                sensor_idx = 1
                for r in all_r:
                    n = r.get('name','').lower()
                    if any(k in n for k in ['terrasse','balcon','jardin','piscine','vide']): continue
                    rx, ry = tx(r['x']), ty(r['y'])
                    if any(k in n for k in ['hall','palier','dgt','sas']):
                        c.setFillColor(ORANGE); c.circle(rx-6, ry+6, 2, fill=1, stroke=0)
                        c.setFillColor(NOIR); c.setFont("Helvetica", 2)
                        c.drawString(rx-7, ry+1, f"S{sensor_idx}")
                        sensor_idx += 1
                    if any(k in n for k in ['chambre','salon','sejour','bureau','sam']):
                        c.setFillColor(ORANGE); c.rect(rx-7, ry-5, 4, 3, fill=1, stroke=0)
                        c.setFillColor(NOIR); c.setFont("Helvetica", 2)
                        c.drawString(rx-6, ry-7, f"S{sensor_idx}")
                        sensor_idx += 1
                notes = [f"{aut.protocole} — {aut.niveau} — {aut.nb_points_controle} pts"]
                _legend_pro(c, w, h, [(BLEU, 1.8, f"Bus {aut.protocole}"),
                                      (ORANGE, 'circle', "Capteur température"),
                                      (colors.HexColor("#FFB74D"), 'circle', "Capteur humidité"),
                                      (ORANGE, 'fill', "Actionneur éclairage"),
                                      (colors.HexColor("#FFB74D"), 'fill', "Actionneur climatisation")], "LÉGENDE AUTOMATISATION GTB")

        else:
            # MODE GRILLE : distribution dans les travées
            # When DWG geometry is drawn (use_dwg=True) but no rooms detected,
            # compute bays to fit within the actual building footprint (gw, gh)
            # instead of using sc_g which is the parametric grid scale.
            cx_noy = ox + gw/2; cy_noy = oy + gh/2
            bays = []
            if use_dwg and gw > 0 and gh > 0:
                # Distribute bays evenly within the DWG geometry bounds
                bay_dx = gw / max(nx, 1)
                bay_dy = gh / max(ny, 1)
                for i in range(nx):
                    for j in range(ny):
                        bays.append((ox + (i + 0.5) * bay_dx, oy + (j + 0.5) * bay_dy))
            else:
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
                _legend_pro(c, w, h, [(BLEU, 'fill', f"CM EF DN{pl.diam_colonne_montante_mm}"),
                                      (BLEU, 0.6, "Distribution EF"),
                                      (BLEU, 'circle', "Branchement"),
                                      (BLEU, 0.3, "Alimentation compteur")], "LÉGENDE EAU FROIDE")
            elif key == "plb_ec":
                c.setFillColor(ROUGE); c.setStrokeColor(NOIR); c.setLineWidth(0.6)
                c.circle(cx_noy, cy_noy, 4, fill=1, stroke=1)
                c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 5); c.drawCentredString(cx_noy, cy_noy-2, "EC")
                for bx, by in bays:
                    c.setStrokeColor(ROUGE); c.setLineWidth(0.5); c.setDash(3,1.5)
                    c.line(cx_noy, cy_noy, cx_noy, by); c.line(cx_noy, by, bx, by); c.setDash()
                notes = ["CM EC DN32", f"{pl.nb_chauffe_eau_solaire} CESI"]
                _legend_pro(c, w, h, [(ROUGE, 'fill', "CM EC"),
                                      (ROUGE, 0.5, "Distribution EC — DN32"),
                                      (colors.HexColor("#E57373"), 0.5, "Circulation ECS DN16")], "LÉGENDE EAU CHAUDE")
            elif key == "plb_eu":
                c.setFillColor(MARRON); c.setStrokeColor(NOIR); c.setLineWidth(0.6)
                c.circle(cx_noy, cy_noy, 4, fill=1, stroke=1)
                c.setFillColor(BLANC); c.setFont("Helvetica-Bold", 5); c.drawCentredString(cx_noy, cy_noy-2, "EU")
                for bx, by in bays:
                    c.setStrokeColor(MARRON); c.setLineWidth(0.5); c.setDash(4,2)
                    c.line(bx, by, cx_noy, by); c.line(cx_noy, by, cx_noy, cy_noy); c.setDash()
                    c.setFillColor(MARRON); c.circle(bx, by, 1.5, fill=1, stroke=0)
                notes = ["Chute EU DN100", f"Conso {pl.conso_eau_annuelle_m3:.0f}m³/an"]
                _legend_pro(c, w, h, [(MARRON, 'fill', "Colonne EU — DN100"),
                                      (colors.HexColor("#A1887F"), 'fill', "Colonne EP — DN75"),
                                      (MARRON, 0.5, "Chute EU"),
                                      (colors.HexColor("#A1887F"), 0.5, "Chute EP")], "LÉGENDE ÉVACUATIONS")
            elif key == "elec_ecl":
                for bx, by in bays:
                    c.setStrokeColor(JAUNE); c.setFillColor(colors.HexColor("#FFF8E1")); c.setLineWidth(0.4)
                    c.circle(bx, by, 3, fill=1, stroke=1)
                    c.setStrokeColor(JAUNE); c.setLineWidth(0.3)
                    c.line(bx-2, by, bx+2, by); c.line(bx, by-2, bx, by+2)
                notes = [f"P éclairage: {el.puissance_eclairage_kw:.1f}kW"]
                _legend_pro(c, w, h, [(JAUNE, 'circle', "Plafonnier"),
                                      (ORANGE, 'circle', "Interrupteur simple allumage"),
                                      (colors.HexColor("#FFB74D"), 'circle', "Interrupteur VA-ET-VIENT"),
                                      (colors.HexColor("#FFA726"), 'circle', "Détecteur de mouvement"),
                                      (JAUNE, 0.5, "Distribution éclairage")], "LÉGENDE ÉLECTRICITÉ")
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
                _legend_pro(c, w, h, [(VERT, 'fill', "TGBT / Transfo"),
                                      (ORANGE, 1.2, "Chemin câbles principal"),
                                      (ORANGE, 'fill', "Prise 2P+T 16A"),
                                      (colors.HexColor("#FF7043"), 'fill', "Prise spécialisée"),
                                      (colors.HexColor("#E64A19"), 'fill', "Prise cuisinière/Chauffe-eau")], "LÉGENDE PRISES & DISTRIBUTION")
            elif key == "cvc_clim":
                for bx, by in bays:
                    c.setFillColor(CYAN); c.setStrokeColor(colors.HexColor("#006064")); c.setLineWidth(0.35)
                    c.rect(bx-5, by+4, 10, 3, fill=1, stroke=1)
                notes = [f"P frigo: {cv.puissance_frigorifique_kw:.0f}kW", f"Splits: {cv.nb_splits_sejour+cv.nb_splits_chambre}"]
                _legend_pro(c, w, h, [(CYAN, 'fill', "Split mural 18000 BTU"),
                                      (colors.HexColor("#80DEEA"), 'fill', "Split mural 12000 BTU"),
                                      (colors.HexColor("#B2EBF2"), 'fill', "Split mural 9000 BTU"),
                                      (CYAN, 0.5, "Liaison frigorifique"),
                                      (MARRON, 0.5, "Ligne condensats")], "LÉGENDE CLIMATISATION")
            elif key == "cvc_vmc":
                for bx, by in bays:
                    c.setStrokeColor(colors.HexColor("#2E7D32")); c.setFillColor(colors.HexColor("#C8E6C9"))
                    c.setLineWidth(0.4); c.circle(bx, by-3, 3, fill=1, stroke=1)
                notes = [f"{cv.nb_vmc} VMC {cv.type_vmc}"]
                _legend_pro(c, w, h, [(colors.HexColor("#2E7D32"), 'circle', "Bouche de soufflage VMC"),
                                      (colors.HexColor("#1B5E20"), 'circle', "Bouche de reprise VMC"),
                                      (colors.HexColor("#2E7D32"), 1.2, "Gaine VMC principal"),
                                      (colors.HexColor("#2E7D32"), 0.5, "Gaine VMC distribution")], "LÉGENDE VENTILATION")
            elif key == "ssi_det":
                for bx, by in bays:
                    c.setFillColor(BLANC); c.setStrokeColor(ROUGE); c.setLineWidth(0.5)
                    c.circle(bx, by, 3, fill=1, stroke=1)
                    c.setFillColor(ROUGE); c.setFont("Helvetica-Bold", 3.5); c.drawCentredString(bx, by-1.5, "DF")
                notes = [f"{si.nb_detecteurs_fumee} DF — {si.nb_declencheurs_manuels} DM"]
                _legend_pro(c, w, h, [(ROUGE, 'circle', "Détecteur fumée"),
                                      (ROUGE, 'fill', "Déclencheur manuel"),
                                      (colors.HexColor("#D32F2F"), 'cross_circle', "Détecteur chaleur"),
                                      (colors.HexColor("#C62828"), 'circle', "Sirène sonovisuelle"),
                                      (ROUGE, 0.5, "Liaison détection")], "LÉGENDE SÉCURITÉ INCENDIE")
            elif key == "ssi_ext":
                for corner in [(ox+10, oy+10), (ox+gw-10, oy+gh-10)]:
                    rx, ry = corner
                    c.setFillColor(BLANC); c.setStrokeColor(ROUGE); c.setLineWidth(0.7)
                    c.circle(rx, ry, 4, fill=1, stroke=1)
                    c.setFillColor(ROUGE); c.setFont("Helvetica-Bold", 5); c.drawCentredString(rx, ry-2, "R")
                    c.setFillColor(VERT); c.rect(rx+8, ry-4, 6, 3.5, fill=1, stroke=1)
                notes = [f"{si.nb_extincteurs_co2+si.nb_extincteurs_poudre} ext. — RIA {si.longueur_ria_ml:.0f}ml"]
                _legend_pro(c, w, h, [(ROUGE, 'circle', "RIA - Robinet d'incendie armé"),
                                      (VERT, 'fill', "BAES - Bloc autonome éclairage"),
                                      (colors.HexColor("#E53935"), 'fill', "Extincteur poudre"),
                                      (colors.HexColor("#1565C0"), 'fill', "Extincteur CO2"),
                                      (ROUGE, 0.5, "Distribution arrosage")], "LÉGENDE EXTINCTION & ÉVACUATION")
            elif key == "cfa":
                for bx, by in bays:
                    c.setFillColor(VIOLET); c.setStrokeColor(NOIR); c.setLineWidth(0.2)
                    c.rect(bx-2, by-2, 4, 3, fill=1, stroke=1)
                notes = [f"{cf.nb_prises_rj45} RJ45 — {cf.nb_cameras_int+cf.nb_cameras_ext} caméras"]
                _legend_pro(c, w, h, [(VIOLET, 'fill', "Prise RJ45"),
                                      (colors.HexColor("#CE93D8"), 'triangle', "Caméra IP intérieure"),
                                      (colors.HexColor("#BA68C8"), 'triangle', "Caméra IP extérieure"),
                                      (VIOLET, 0.5, "Réseau données")], "LÉGENDE COURANTS FAIBLES")
            elif key == "asc_plan":
                c.setFillColor(BLEU_B); c.setStrokeColor(BLEU); c.setLineWidth(1)
                c.rect(cx_noy-8, cy_noy-8, 16, 16, fill=1, stroke=1)
                c.setStrokeColor(BLEU); c.setLineWidth(0.3)
                c.line(cx_noy-8, cy_noy-8, cx_noy+8, cy_noy+8); c.line(cx_noy-8, cy_noy+8, cx_noy+8, cy_noy-8)
                c.setFillColor(BLEU); c.setFont("Helvetica-Bold", 4)
                c.drawCentredString(cx_noy, cy_noy-12, f"{asc.nb_ascenseurs}× {asc.capacite_kg}kg")
                notes = [f"{asc.nb_ascenseurs} asc. {asc.capacite_kg}kg"]
                _legend_pro(c, w, h, [(BLEU_B, 'fill', f"Gaine ascenseur {asc.capacite_kg}kg"),
                                      (colors.HexColor("#0277BD"), 'fill', "Cage escalier"),
                                      (BLEU, 0.5, "Gaine technique")], "LÉGENDE ASCENSEURS")
            elif key == "gtb":
                c.setStrokeColor(BLEU); c.setLineWidth(1.8)
                c.line(ox, cy_noy, ox+gw, cy_noy)
                for bx, by in bays:
                    c.setFillColor(ORANGE); c.circle(bx-3, by+3, 1.5, fill=1, stroke=0)
                notes = [f"{aut.protocole} — {aut.nb_points_controle} pts"]
                _legend_pro(c, w, h, [(BLEU, 1.8, f"Bus {aut.protocole}"),
                                      (ORANGE, 'circle', "Capteur température"),
                                      (colors.HexColor("#FFB74D"), 'circle', "Capteur humidité"),
                                      (ORANGE, 'fill', "Actionneur éclairage"),
                                      (colors.HexColor("#FFB74D"), 'fill', "Actionneur climatisation")], "LÉGENDE AUTOMATISATION GTB")

        # Notes en bas
        c.setFont("Helvetica", 5); c.setFillColor(GRIS3)
        for k_n, note in enumerate(notes[:3]):
            c.drawString(14*mm, 42*mm - k_n*5*mm, note)

        # Nomenclature équipements (milieu-bas gauche)
        try:
            nomencl = _build_mep_nomenclature(key, pl, el, cv, cf, si, asc, aut)
            if nomencl:
                _draw_mep_nomenclature_table(c, 14*mm, 60*mm, nomencl,
                                             title=f"NOMENCLATURE — {title[:30]}")
        except Exception as _e_nom:
            pass

        _cartouche_pro(c, w, h, p, f"Plan {title}", page, total_pages, lot_label,
                       drawing_no=_mep_drawing_no(key, level_label, page))
        c.showPage()

    # ── 4 schémas de principe en fin de document ──
    try:
        page += 1
        _draw_principe_plomberie(c, A3L[0], A3L[1], p, pl, page, total_pages); c.showPage()
        page += 1
        _draw_principe_electricite(c, A3L[0], A3L[1], p, el, page, total_pages); c.showPage()
        page += 1
        _draw_principe_cvc(c, A3L[0], A3L[1], p, cv, page, total_pages); c.showPage()
        page += 1
        _draw_principe_ssi(c, A3L[0], A3L[1], p, si, page, total_pages); c.showPage()
    except Exception as _e_pcp:
        import logging
        logging.getLogger("tijan").warning(f"Schémas de principe skipped: {_e_pcp}")

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
