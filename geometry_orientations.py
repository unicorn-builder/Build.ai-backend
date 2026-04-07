"""
geometry_orientations.py — Calcule les longueurs et expositions façade
par 8 orientations (N, NE, E, SE, S, SW, W, NW) à partir d'une géométrie
DXF/PDF (walls list avec start/end en mm).

Utilisé par /generate-edge-assessment pour remplir la section
'Building Dimensions' du rapport EDGE v3.0.0.

Convention :
- Y croissant = Nord (convention CAO)
- Angle 0° = Est, 90° = Nord, 180° = Ouest, 270° = Sud
- L'orientation d'un mur = direction de sa normale extérieure
"""
import math
from typing import Dict, List, Optional


# Octants centrés sur N (90°), NE (45°), E (0°), SE (-45°/315°), S (-90°/270°), etc.
# Chaque secteur fait 45° de large.
OCTANTS = [
    ('E',  0),
    ('NE', 45),
    ('N',  90),
    ('NW', 135),
    ('W',  180),
    ('SW', 225),
    ('S',  270),
    ('SE', 315),
]


def _wall_endpoints(wall: dict) -> Optional[tuple]:
    """Extract (x1,y1,x2,y2) from various wall dict formats."""
    if 'start' in wall and 'end' in wall:
        s, e = wall['start'], wall['end']
        if len(s) >= 2 and len(e) >= 2:
            return (float(s[0]), float(s[1]), float(e[0]), float(e[1]))
    if all(k in wall for k in ('x1', 'y1', 'x2', 'y2')):
        return (float(wall['x1']), float(wall['y1']),
                float(wall['x2']), float(wall['y2']))
    return None


def _all_walls(geometry: dict) -> List[dict]:
    """Flatten walls from a geometry dict that may be either:
       {'walls': [...]} or {'level1': {'walls': [...]}, 'level2': {...}}.
       Returns walls from the level with most walls (typical floor)."""
    if not isinstance(geometry, dict):
        return []
    if 'walls' in geometry and isinstance(geometry['walls'], list):
        return geometry['walls']
    # Multi-level: pick richest level
    best = []
    for v in geometry.values():
        if isinstance(v, dict) and isinstance(v.get('walls'), list):
            if len(v['walls']) > len(best):
                best = v['walls']
    return best


def _bbox(walls: List[dict]) -> Optional[tuple]:
    xs, ys = [], []
    for w in walls:
        ep = _wall_endpoints(w)
        if not ep:
            continue
        xs.extend([ep[0], ep[2]])
        ys.extend([ep[1], ep[3]])
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def _classify_octant(angle_deg: float) -> str:
    """Map an angle (0-360°) to the closest octant label."""
    angle_deg = angle_deg % 360
    best, best_diff = 'N', 360
    for label, center in OCTANTS:
        diff = min(abs(angle_deg - center), 360 - abs(angle_deg - center))
        if diff < best_diff:
            best_diff, best = diff, label
    return best


def compute_facade_orientations(geometry: dict,
                                 perimeter_tolerance_pct: float = 8.0) -> Dict[str, dict]:
    """
    Calcule longueur (m) et % exposition par orientation pour les murs périmétriques.

    Args:
        geometry: dict de géométrie DXF/PDF avec 'walls'
        perimeter_tolerance_pct: tolérance (% bbox) pour considérer un mur comme périmétrique

    Returns:
        dict {orientation: {'len': m, 'exposed_pct': %}} pour les 8 orientations.
        Retourne None si la géométrie est insuffisante.
    """
    walls = _all_walls(geometry)
    if len(walls) < 4:
        return None

    bb = _bbox(walls)
    if not bb:
        return None
    xmin, ymin, xmax, ymax = bb
    w_bb = xmax - xmin
    h_bb = ymax - ymin
    if w_bb <= 0 or h_bb <= 0:
        return None

    tol_x = w_bb * perimeter_tolerance_pct / 100
    tol_y = h_bb * perimeter_tolerance_pct / 100

    octant_lengths = {label: 0.0 for label, _ in OCTANTS}
    total_len = 0.0

    for wall in walls:
        ep = _wall_endpoints(wall)
        if not ep:
            continue
        x1, y1, x2, y2 = ep
        length_mm = math.hypot(x2 - x1, y2 - y1)
        if length_mm < 100:  # ignore < 10 cm
            continue
        # Mid-point
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        # Identify which side of bbox this wall is closest to (perimeter check)
        d_left = abs(mx - xmin)
        d_right = abs(xmax - mx)
        d_bot = abs(my - ymin)
        d_top = abs(ymax - my)

        # Outward normal direction (degrees, 0=East, 90=North)
        normal_deg = None
        if d_top < tol_y and d_top <= min(d_left, d_right, d_bot):
            normal_deg = 90  # North-facing
        elif d_bot < tol_y and d_bot <= min(d_left, d_right, d_top):
            normal_deg = 270  # South-facing
        elif d_left < tol_x and d_left <= min(d_top, d_bot, d_right):
            normal_deg = 180  # West-facing
        elif d_right < tol_x and d_right <= min(d_top, d_bot, d_left):
            normal_deg = 0    # East-facing
        else:
            # Not on perimeter — skip (interior wall)
            continue

        # Refine using wall angle: if wall is tilted, blend orientation
        wall_angle = math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180
        # Wall normal is perpendicular to wall line (90° off)
        # but we already locked side; use wall angle to detect diagonals
        if abs(wall_angle - 45) < 15 or abs(wall_angle - 135) < 15:
            # Diagonal wall — shift normal by ±45°
            if normal_deg in (90, 270):
                normal_deg += 45 if wall_angle < 90 else -45
            else:
                normal_deg += 45 if wall_angle > 90 else -45
            normal_deg %= 360

        octant = _classify_octant(normal_deg)
        length_m = length_mm / 1000.0
        octant_lengths[octant] += length_m
        total_len += length_m

    if total_len <= 0:
        return None

    # Build result : len (m) + exposed_pct = part de cette orientation dans le total
    result = {}
    for label, _ in OCTANTS:
        L = octant_lengths[label]
        result[label] = {
            'len': round(L, 1),
            'exposed_pct': round(100 * L / total_len, 1) if total_len > 0 else 0.0,
        }
    return result
