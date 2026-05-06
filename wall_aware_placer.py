"""Wall-aware MEP equipment placement.

Given a geometry dict {walls, rooms, doors, ...} extracted from an architectural
plan, this module:

1. Computes the building envelope (outer polygon) from the longest walls.
2. Filters false-positive rooms (cartouche, landscape, outside envelope).
3. For each valid room, identifies its local walls (bbox inflation).
4. Places MEP equipment against the walls (prises, luminaires,
   points d'eau, VMC, EU descents) following BET conventions.

Coordinates are in the same unit as the input geometry (typically mm
for CV-extracted plans, or raw PDF points after conversion). All
placement helpers return lists of dicts: {x, y, angle_deg, kind, label}.
"""
from __future__ import annotations
import math
from typing import List, Tuple, Dict, Optional


# ──────────────────────────────────────────────────────────────────
#  Footprint + filters
# ──────────────────────────────────────────────────────────────────

def _wall_bounds(walls: List[dict]) -> Tuple[float, float, float, float]:
    xs, ys = [], []
    for w in walls:
        s, e = w['start'], w['end']
        xs += [s[0], e[0]]; ys += [s[1], e[1]]
    if not xs:
        return 0.0, 0.0, 0.0, 0.0
    return min(xs), min(ys), max(xs), max(ys)


def _wall_length(w: dict) -> float:
    s, e = w['start'], w['end']
    return math.hypot(e[0] - s[0], e[1] - s[1])


def compute_building_envelope(walls: List[dict]) -> Tuple[float, float, float, float]:
    """Return (xmin, ymin, xmax, ymax) of the building footprint.

    Strategy: keep walls of **medium length** (typical interior and load-bearing
    partitions) and exclude the very long ones (property lines, landscape
    borders, page frames). Then use the p5–p95 percentile of endpoint
    coordinates to exclude outlier walls that still slipped through.

    This is unit-agnostic: we pick medium walls as those whose length is
    between 5 % and 40 % of the longest wall observed.
    """
    if not walls:
        return 0, 0, 0, 0
    lengths = [_wall_length(w) for w in walls]
    Lmax = max(lengths) or 1.0
    lo, hi = 0.05 * Lmax, 0.40 * Lmax
    mid = [w for w, L in zip(walls, lengths) if lo <= L <= hi]
    if len(mid) < 20:
        # Too few medium walls — fall back to top 40 % longest
        mid = sorted(walls, key=_wall_length, reverse=True)[:max(1, len(walls) // 3)]
    xs, ys = [], []
    for w in mid:
        s, e = w['start'], w['end']
        xs += [s[0], e[0]]; ys += [s[1], e[1]]
    xs.sort(); ys.sort()
    n_x, n_y = len(xs), len(ys)
    def pct(arr, p):
        return arr[max(0, min(len(arr) - 1, int(len(arr) * p)))]
    return (pct(xs, 0.05), pct(ys, 0.05),
            pct(xs, 0.95), pct(ys, 0.95))


def _room_enclosure_score(room: dict, walls: List[dict],
                          radius: float) -> int:
    """Count how many of the 4 cardinal directions (N/S/E/W) have a wall
    close to the room centroid. A real interior room has walls on ≥3 sides.
    This excludes open terraces and landscape patches."""
    cx, cy = room.get('x', 0), room.get('y', 0)
    found = [False, False, False, False]  # N, S, E, W
    for w in walls:
        s, e = w['start'], w['end']
        mx = (s[0] + e[0]) / 2
        my = (s[1] + e[1]) / 2
        dx, dy = mx - cx, my - cy
        if math.hypot(dx, dy) > radius:
            continue
        if abs(dy) > abs(dx):
            if dy < 0:
                found[0] = True  # North (smaller y == top)
            else:
                found[1] = True  # South
        else:
            if dx > 0:
                found[2] = True  # East
            else:
                found[3] = True  # West
    return sum(found)


def filter_rooms_inside_envelope(rooms: List[dict],
                                 envelope: Tuple[float, float, float, float],
                                 walls: Optional[List[dict]] = None,
                                 margin: float = 500.0,
                                 min_area_m2: float = 2.0,
                                 max_area_m2: float = 120.0,
                                 max_aspect: float = 4.0,
                                 min_enclosure: int = 3) -> List[dict]:
    """Keep only rooms whose centroid lies inside the envelope and whose
    geometry looks like a real habitable/service room enclosed by walls.

    A room is considered interior if it has walls on at least `min_enclosure`
    of the 4 cardinal directions within a reasonable radius. This rejects
    terraces, gardens, and landscape contours."""
    xmin, ymin, xmax, ymax = envelope
    # Enclosure radius: derive from room's own bbox if available, else
    # from envelope size.
    env_diag = math.hypot(xmax - xmin, ymax - ymin)
    default_r = env_diag * 0.08
    keep = []
    for r in rooms:
        x, y = r.get('x', 0), r.get('y', 0)
        if not (xmin - margin <= x <= xmax + margin and
                ymin - margin <= y <= ymax + margin):
            continue
        area = r.get('area_m2')
        if area is not None and not (min_area_m2 <= area <= max_area_m2):
            continue
        aspect = r.get('aspect')
        if aspect is not None and aspect > max_aspect:
            continue
        if walls is not None:
            bbox = r.get('bbox_mm')
            if bbox:
                _, _, bw, bh = bbox
                radius = max(bw, bh) * 1.5
            else:
                radius = default_r
            if _room_enclosure_score(r, walls, radius) < min_enclosure:
                continue
        keep.append(r)
    return keep


# ──────────────────────────────────────────────────────────────────
#  Room typing (wet / dry / service)
# ──────────────────────────────────────────────────────────────────

WET_KEYWORDS = ('sdb', 'wc', 'toil', 'douche', 'bain', 'bath', 'lav')
KITCHEN_KEYWORDS = ('cuisine', 'kitch', 'buand', 'office')
LIVING_KEYWORDS = ('salon', 'sejour', 'séjour', 'living', 'chambre', 'bedroom',
                   'bureau', 'sam', 'salle', 'sport', 'gym', 'jeu', 'dressing')
SERVICE_KEYWORDS = ('hall', 'palier', 'asc', 'dgt', 'sas', 'degagement',
                    'dégagement', 'circulation', 'escalier', 'gaine')


def classify_room(name: str, area_m2: float = 0.0) -> str:
    n = (name or '').lower().strip()
    if any(k in n for k in WET_KEYWORDS):
        return 'wet'
    if any(k in n for k in KITCHEN_KEYWORDS):
        return 'kitchen'
    if any(k in n for k in SERVICE_KEYWORDS):
        return 'service'
    if any(k in n for k in LIVING_KEYWORDS):
        return 'living'
    # Fallback by area
    if area_m2 and area_m2 < 4:
        return 'wet'
    if area_m2 and area_m2 > 25:
        return 'living'
    return 'living'


# ──────────────────────────────────────────────────────────────────
#  Wall geometry per room
# ──────────────────────────────────────────────────────────────────

def _wall_orientation(w: dict, tol: float = 3.0) -> str:
    """'h' (horizontal), 'v' (vertical), or 'd' (diagonal) — uses the
    angle from the X axis in degrees."""
    s, e = w['start'], w['end']
    dx, dy = e[0] - s[0], e[1] - s[1]
    ang = abs(math.degrees(math.atan2(dy, dx))) % 180
    if ang < tol or ang > 180 - tol:
        return 'h'
    if abs(ang - 90) < tol:
        return 'v'
    return 'd'


def walls_near_room(room: dict, walls: List[dict],
                    inflate_frac: float = 0.5) -> List[dict]:
    """Return walls whose midpoint lies within the room bbox (inflated).

    inflate_frac: the bbox is enlarged by this fraction of its own size on each
    side. This is unit-agnostic so the helper works whether coordinates are mm
    or PDF points. If bbox is missing or inconsistent with walls' unit,
    fall back to a centroid-radius match sized from the walls' own span.
    """
    bbox = room.get('bbox_mm')
    cx, cy = room.get('x', 0), room.get('y', 0)
    if bbox:
        bx, by, bw, bh = bbox
        ix = bw * inflate_frac
        iy = bh * inflate_frac
        near = []
        for w in walls:
            s, e = w['start'], w['end']
            mx = (s[0] + e[0]) / 2
            my = (s[1] + e[1]) / 2
            if (bx - ix <= mx <= bx + bw + ix and
                    by - iy <= my <= by + bh + iy):
                near.append(w)
        if near:
            return near
    # Fallback: radius match in same unit as walls. Derive a typical room
    # "radius" from the walls' bounding diagonal / sqrt(N rooms).
    if not walls:
        return []
    xs, ys = [], []
    for w in walls:
        xs += [w['start'][0], w['end'][0]]
        ys += [w['start'][1], w['end'][1]]
    diag = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
    r = diag * 0.12  # generous radius, ~1/8 of building diagonal
    near = []
    for w in walls:
        s, e = w['start'], w['end']
        mx = (s[0] + e[0]) / 2
        my = (s[1] + e[1]) / 2
        if math.hypot(mx - cx, my - cy) <= r:
            near.append(w)
    return near


# ──────────────────────────────────────────────────────────────────
#  Equipment placement along walls
# ──────────────────────────────────────────────────────────────────

def place_along_wall(wall: dict, spacing: float = 3000.0,
                     offset: float = 100.0,
                     skip_ends: float = 300.0,
                     clip_bbox: Optional[Tuple[float, float, float, float]] = None,
                     ) -> List[Tuple[float, float, float]]:
    """Sample points along a wall every `spacing` mm, offset `offset` mm
    perpendicular to the wall (into the room). Skips the `skip_ends` mm
    at each extremity.

    Returns list of (x, y, angle_deg) — angle is the wall's normal (for symbol
    orientation).
    """
    s, e = wall['start'], wall['end']
    dx, dy = e[0] - s[0], e[1] - s[1]
    L = math.hypot(dx, dy)
    if L <= 2 * skip_ends:
        return []
    ux, uy = dx / L, dy / L    # unit tangent
    nx, ny = -uy, ux          # unit normal
    n = max(1, int((L - 2 * skip_ends) // spacing))
    # Evenly space n points; if n=1, put it at midpoint
    pts = []
    if n == 1:
        ts = [L / 2]
    else:
        step = (L - 2 * skip_ends) / n
        ts = [skip_ends + (i + 0.5) * step for i in range(n)]
    ang = math.degrees(math.atan2(ny, nx))
    for t in ts:
        px = s[0] + ux * t + nx * offset
        py = s[1] + uy * t + nx * 0 + ny * offset
        if clip_bbox is not None:
            bx, by, bw, bh = clip_bbox
            # Allow a small tolerance equal to the offset itself (prises can
            # sit just outside the bbox due to the perpendicular offset).
            tol = abs(offset) * 1.5
            if not (bx - tol <= px <= bx + bw + tol and
                    by - tol <= py <= by + bh + tol):
                continue
        pts.append((px, py, ang))
    return pts


def pick_interior_direction(wall: dict, room: dict) -> int:
    """Return +1 or -1 to indicate which side of the wall is *inside* the room.

    Uses the wall midpoint and the vector to the room centroid projected
    onto the wall normal.
    """
    s, e = wall['start'], wall['end']
    dx, dy = e[0] - s[0], e[1] - s[1]
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    mx = (s[0] + e[0]) / 2
    my = (s[1] + e[1]) / 2
    cx, cy = room.get('x', mx), room.get('y', my)
    return 1 if ((cx - mx) * nx + (cy - my) * ny) > 0 else -1


def place_prises(room: dict, walls: List[dict],
                 spacing: float = 3000.0) -> List[dict]:
    """Place wall-mounted electrical sockets (prises) along each wall of
    the room, spaced every `spacing` mm, at 100 mm offset from the wall
    (inside the room)."""
    items = []
    for w in walls:
        if _wall_orientation(w) == 'd':
            continue
        sign = pick_interior_direction(w, room)
        pts = place_along_wall(w, spacing=spacing, offset=100.0, skip_ends=500.0)
        for px, py, ang in pts:
            # Flip offset sign if it pointed outside
            if sign < 0:
                s, e = w['start'], w['end']
                dx, dy = e[0] - s[0], e[1] - s[1]
                L = math.hypot(dx, dy) or 1.0
                nx, ny = -dy / L, dx / L
                px -= 2 * 100.0 * nx
                py -= 2 * 100.0 * ny
            items.append({'x': px, 'y': py, 'angle': ang,
                          'kind': 'prise', 'label': 'PC'})
    return items


def place_luminaire(room: dict) -> List[dict]:
    """Ceiling luminaire(s) at the centroid of the room.
    Adds 2–4 luminaires for large rooms."""
    area = room.get('area_m2', 12)
    cx, cy = room['x'], room['y']
    if area < 12:
        return [{'x': cx, 'y': cy, 'angle': 0, 'kind': 'plafonnier',
                 'label': 'Plaf'}]
    # Larger room: 2 luminaires on the long axis of the bbox
    bbox = room.get('bbox_mm', [cx - 1500, cy - 1500, 3000, 3000])
    bx, by, bw, bh = bbox
    if bw >= bh:
        return [
            {'x': bx + bw * 0.33, 'y': by + bh / 2, 'angle': 0,
             'kind': 'plafonnier', 'label': 'Plaf'},
            {'x': bx + bw * 0.67, 'y': by + bh / 2, 'angle': 0,
             'kind': 'plafonnier', 'label': 'Plaf'},
        ]
    else:
        return [
            {'x': bx + bw / 2, 'y': by + bh * 0.33, 'angle': 0,
             'kind': 'plafonnier', 'label': 'Plaf'},
            {'x': bx + bw / 2, 'y': by + bh * 0.67, 'angle': 0,
             'kind': 'plafonnier', 'label': 'Plaf'},
        ]


def place_interrupteur(room: dict, walls: List[dict],
                       doors: Optional[List[dict]] = None) -> List[dict]:
    """Light switch near the door opening (or at the nearest wall-corner
    of the longest wall)."""
    if not walls:
        return []
    # Pick the longest wall as the "main" wall for now (proper door-side
    # detection would require matching doors to walls — out of scope).
    w = max(walls, key=_wall_length)
    s, e = w['start'], w['end']
    L = math.hypot(e[0] - s[0], e[1] - s[1]) or 1
    ux = (e[0] - s[0]) / L
    uy = (e[1] - s[1]) / L
    sign = pick_interior_direction(w, room)
    nx, ny = -uy * sign, ux * sign
    t = min(800.0, L * 0.15)
    px = s[0] + ux * t + nx * 100.0
    py = s[1] + uy * t + ny * 100.0
    return [{'x': px, 'y': py, 'angle': math.degrees(math.atan2(ny, nx)),
             'kind': 'interrupteur', 'label': 'IS'}]


def place_point_deau(room: dict, walls: List[dict],
                     kind: str = 'ef') -> List[dict]:
    """Water point against the wall opposite the room entrance.

    kind: 'ef' (eau froide, blue), 'ec' (eau chaude, red), 'eu' (évacuation).
    """
    if not walls:
        return [{'x': room['x'], 'y': room['y'], 'angle': 0,
                 'kind': f'point_{kind}', 'label': kind.upper()}]
    # Pick wall with midpoint farthest from room center (= opposite to where
    # door likely opens). Deterministic proxy.
    cx, cy = room['x'], room['y']
    def dist(w):
        mx = (w['start'][0] + w['end'][0]) / 2
        my = (w['start'][1] + w['end'][1]) / 2
        return math.hypot(mx - cx, my - cy)
    w = max(walls, key=dist)
    s, e = w['start'], w['end']
    dx, dy = e[0] - s[0], e[1] - s[1]
    L = math.hypot(dx, dy) or 1
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    sign = pick_interior_direction(w, room)
    # Slightly off-center along the wall
    t = L * 0.5
    off = 150.0
    px = s[0] + ux * t + nx * off * sign
    py = s[1] + uy * t + ny * off * sign
    return [{'x': px, 'y': py, 'angle': math.degrees(math.atan2(ny * sign, nx * sign)),
             'kind': f'point_{kind}', 'label': kind.upper()}]


def place_vmc_bouche(room: dict) -> List[dict]:
    """VMC extraction grille: ceiling, wet-room only — at centroid."""
    return [{'x': room['x'], 'y': room['y'], 'angle': 0,
             'kind': 'vmc', 'label': 'VMC'}]


def place_detecteur_fumee(room: dict) -> List[dict]:
    """Smoke detector: ceiling, center of large rooms."""
    return [{'x': room['x'], 'y': room['y'], 'angle': 0,
             'kind': 'detect', 'label': 'DF'}]


# ──────────────────────────────────────────────────────────────────
#  Per-lot placement façade — called by generer_plans_mep
# ──────────────────────────────────────────────────────────────────

def place_equipment_for_lot(lot_key: str,
                            rooms: List[dict],
                            walls: List[dict]) -> List[dict]:
    """Return a list of equipment items for a given MEP sub-lot.

    lot_key ∈ {'plb_ef', 'plb_ec', 'plb_eu',
               'elec_ecl', 'elec_dist',
               'cvc_clim', 'cvc_vmc',
               'cf_rj45', 'cf_video',
               'si_det', 'si_alarm',
               'aut_bms'}
    """
    items = []
    for r in rooms:
        kind = classify_room(r.get('name', ''), r.get('area_m2', 0))
        near = walls_near_room(r, walls)

        if lot_key == 'elec_ecl':
            items += place_luminaire(r)
            items += place_interrupteur(r, near)
        elif lot_key == 'elec_dist':
            if kind != 'service':
                items += place_prises(r, near,
                                      spacing=2500.0 if kind == 'kitchen' else 3500.0)
        elif lot_key == 'plb_ef':
            if kind in ('wet', 'kitchen'):
                items += place_point_deau(r, near, kind='ef')
        elif lot_key == 'plb_ec':
            if kind in ('wet', 'kitchen'):
                items += place_point_deau(r, near, kind='ec')
        elif lot_key == 'plb_eu':
            if kind in ('wet', 'kitchen'):
                items += place_point_deau(r, near, kind='eu')
        elif lot_key == 'cvc_clim':
            if kind == 'living' and r.get('area_m2', 0) >= 10:
                items.append({'x': r['x'], 'y': r['y'], 'angle': 0,
                              'kind': 'split', 'label': 'Split'})
        elif lot_key == 'cvc_vmc':
            if kind in ('wet', 'kitchen'):
                items += place_vmc_bouche(r)
        elif lot_key == 'cf_rj45':
            if kind == 'living':
                items.append({'x': r['x'], 'y': r['y'], 'angle': 0,
                              'kind': 'rj45', 'label': 'RJ'})
        elif lot_key == 'cf_video':
            if kind in ('living', 'service'):
                items.append({'x': r['x'], 'y': r['y'], 'angle': 0,
                              'kind': 'tv', 'label': 'TV'})
        elif lot_key in ('si_det', 'ssi_det'):
            if r.get('area_m2', 0) >= 6:
                items += place_detecteur_fumee(r)
        elif lot_key in ('si_alarm', 'ssi_ext'):
            if r.get('area_m2', 0) >= 6:
                items.append({'x': r['x'], 'y': r['y'] + 200, 'angle': 0,
                              'kind': 'sirene', 'label': 'Si'})
        elif lot_key in ('aut_bms', 'gtb'):
            if r.get('area_m2', 0) >= 10:
                items.append({'x': r['x'], 'y': r['y'], 'angle': 0,
                              'kind': 'bms', 'label': 'BMS'})
        elif lot_key in ('cfa',):
            # courants faibles: RJ45 + TV in living rooms
            if kind == 'living':
                items.append({'x': r['x'] - 200, 'y': r['y'], 'angle': 0,
                              'kind': 'rj45', 'label': 'RJ'})
                items.append({'x': r['x'] + 200, 'y': r['y'], 'angle': 0,
                              'kind': 'tv', 'label': 'TV'})
        elif lot_key in ('asc_plan',):
            # Show shafts only (service rooms); placer has limited info so skip
            pass
    return items


# ──────────────────────────────────────────────────────────────────
#  Rendering helper — called by generer_plans_mep in MODE 1
# ──────────────────────────────────────────────────────────────────

def draw_items(c, items: List[dict], tx, ty, symbol_size: float = 4.0):
    """Draw the equipment items on a ReportLab canvas using tx/ty to map
    geometry-space coordinates to canvas points.

    Each `kind` gets a distinct symbol + color. Sizes are in canvas points.
    """
    from reportlab.lib import colors as rl_colors
    PALETTE = {
        'prise':        ('#1976d2', 'rect'),
        'plafonnier':   ('#f9a825', 'circle'),
        'interrupteur': ('#6a1b9a', 'tri'),
        'point_ef':     ('#1565c0', 'drop'),
        'point_ec':     ('#c62828', 'drop'),
        'point_eu':     ('#4e342e', 'drop'),
        'vmc':          ('#00838f', 'hex'),
        'split':        ('#2e7d32', 'diamond'),
        'rj45':         ('#5d4037', 'rect'),
        'tv':           ('#424242', 'rect'),
        'detect':       ('#d32f2f', 'circle'),
        'sirene':       ('#b71c1c', 'hex'),
        'bms':          ('#37474f', 'rect'),
    }
    s = symbol_size
    for it in items:
        color_hex, shape = PALETTE.get(it['kind'], ('#666666', 'rect'))
        cx = tx(it['x']); cy = ty(it['y'])
        c.saveState()
        c.setFillColor(rl_colors.HexColor(color_hex))
        c.setStrokeColor(rl_colors.HexColor(color_hex))
        c.setLineWidth(0.3)
        if shape == 'rect':
            c.rect(cx - s / 2, cy - s / 2, s, s, fill=1, stroke=1)
        elif shape == 'circle':
            c.circle(cx, cy, s / 2, fill=1, stroke=1)
        elif shape == 'tri':
            from reportlab.graphics.shapes import Polygon
            p = c.beginPath()
            p.moveTo(cx, cy + s / 2)
            p.lineTo(cx - s / 2, cy - s / 2)
            p.lineTo(cx + s / 2, cy - s / 2)
            p.close()
            c.drawPath(p, fill=1, stroke=1)
        elif shape == 'drop':
            c.circle(cx, cy, s / 2, fill=1, stroke=1)
            c.setFillColor(rl_colors.white)
            c.setFont("Helvetica-Bold", s * 0.9)
            c.drawCentredString(cx, cy - s * 0.3, it.get('label', '')[:1])
        elif shape == 'diamond':
            p = c.beginPath()
            p.moveTo(cx, cy + s / 2); p.lineTo(cx + s / 2, cy)
            p.lineTo(cx, cy - s / 2); p.lineTo(cx - s / 2, cy)
            p.close()
            c.drawPath(p, fill=1, stroke=1)
        elif shape == 'hex':
            p = c.beginPath()
            r = s / 2
            for i in range(6):
                a = math.radians(60 * i)
                x = cx + r * math.cos(a); y = cy + r * math.sin(a)
                if i == 0: p.moveTo(x, y)
                else: p.lineTo(x, y)
            p.close()
            c.drawPath(p, fill=1, stroke=1)
        c.restoreState()


# ──────────────────────────────────────────────────────────────────
#  Public convenience
# ──────────────────────────────────────────────────────────────────

def _detect_unit_scale(walls: List[dict]) -> float:
    """Return a multiplier for mm-valued constants so they make physical sense
    in the walls' coordinate unit. 1.0 if walls are in mm; < 1 if walls are in
    PDF points or other scaled unit.

    Heuristic: a residential building is 10–80 m across. If the walls' bbox
    diagonal is in that range in millimetres (10000–80000) we assume mm; if
    much smaller (say 300–3000) we assume PDF points and scale down.
    """
    if not walls:
        return 1.0
    xs, ys = [], []
    for w in walls:
        xs += [w['start'][0], w['end'][0]]
        ys += [w['start'][1], w['end'][1]]
    diag = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
    if diag <= 0:
        return 1.0
    # Target: assume 30 m = 30000 mm as canonical building scale
    target_mm = 30000.0
    return diag / target_mm


def place_equipment_with_scale(lot_key: str, rooms: List[dict],
                               walls: List[dict], u: float = 1.0) -> List[dict]:
    """Scale-aware variant of place_equipment_for_lot. `u` is the multiplier
    applied to every mm-valued constant (spacing, offset, skip_ends)."""
    items = []
    def _pr(r, sp_mm):
        near = walls_near_room(r, walls)
        its = []
        clip = r.get('bbox_mm')  # same-unit bbox after preview conversion
        for w in near:
            if _wall_orientation(w) == 'd':
                continue
            sign = pick_interior_direction(w, r)
            pts = place_along_wall(w, spacing=sp_mm * u,
                                   offset=100.0 * u, skip_ends=500.0 * u,
                                   clip_bbox=clip)
            for px, py, ang in pts:
                if sign < 0:
                    s, e = w['start'], w['end']
                    dx, dy = e[0] - s[0], e[1] - s[1]
                    L = math.hypot(dx, dy) or 1.0
                    nx, ny = -dy / L, dx / L
                    px -= 2 * 100.0 * u * nx
                    py -= 2 * 100.0 * u * ny
                its.append({'x': px, 'y': py, 'angle': ang,
                            'kind': 'prise', 'label': 'PC'})
        return its

    for r in rooms:
        kind = classify_room(r.get('name', ''), r.get('area_m2', 0))
        near = walls_near_room(r, walls)
        if lot_key == 'elec_ecl':
            items += place_luminaire(r)
            items += place_interrupteur(r, near)
        elif lot_key == 'elec_dist':
            if kind != 'service':
                items += _pr(r, 2500.0 if kind == 'kitchen' else 3500.0)
        elif lot_key in ('plb_ef', 'plb_ec', 'plb_eu'):
            if kind in ('wet', 'kitchen'):
                items += place_point_deau(r, near, kind=lot_key.split('_')[1])
        elif lot_key == 'cvc_clim':
            if kind == 'living' and r.get('area_m2', 0) >= 10:
                items.append({'x': r['x'], 'y': r['y'], 'angle': 0,
                              'kind': 'split', 'label': 'Split'})
        elif lot_key == 'cvc_vmc':
            if kind in ('wet', 'kitchen'):
                items += place_vmc_bouche(r)
        elif lot_key in ('si_det', 'ssi_det'):
            if r.get('area_m2', 0) >= 6:
                items += place_detecteur_fumee(r)
        elif lot_key in ('si_alarm', 'ssi_ext'):
            if r.get('area_m2', 0) >= 6:
                items.append({'x': r['x'], 'y': r['y'] + 200 * u, 'angle': 0,
                              'kind': 'sirene', 'label': 'Si'})
        elif lot_key in ('aut_bms', 'gtb'):
            if r.get('area_m2', 0) >= 10:
                items.append({'x': r['x'], 'y': r['y'], 'angle': 0,
                              'kind': 'bms', 'label': 'BMS'})
        elif lot_key == 'cfa':
            if kind == 'living':
                items.append({'x': r['x'] - 200 * u, 'y': r['y'], 'angle': 0,
                              'kind': 'rj45', 'label': 'RJ'})
                items.append({'x': r['x'] + 200 * u, 'y': r['y'], 'angle': 0,
                              'kind': 'tv', 'label': 'TV'})
    return items


def prepare(geometry: dict) -> dict:
    """Return a dict with filtered rooms + envelope + walls + unit scale,
    ready for the generator."""
    walls = geometry.get('walls', [])
    rooms = geometry.get('rooms', [])
    env = compute_building_envelope(walls)
    filt = filter_rooms_inside_envelope(rooms, env, walls=walls)
    return {
        'walls': walls,
        'rooms': filt,
        'envelope': env,
        'unit_scale': _detect_unit_scale(walls),
        '_cv_meta': geometry.get('_cv_meta', {}),
    }
