"""
CV-based geometry extraction pipeline for architectural plans.

Three-stage pipeline:
  1. OpenCV  — structural geometry (walls, contours, openings) from rasterized image
  2. Claude Vision — semantic labels (room names, dimensions, annotations)
  3. Fusion  — merge geometry + labels into normalized dict matching ezdxf output

Accepts: PDF (vector or scanned), DWG (pre-converted to image), raw image (photo/scan).
Returns: geometry dict compatible with plan generators:
    {walls, windows, doors, rooms, axes_x, axes_y}

Author: Tijan AI — built by Malick with Claude
"""

import logging
import math
import os
import tempfile
from collections import defaultdict
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger("tijan.cv_geometry")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Minimum wall length in pixels at 200 DPI (~3mm real = noise threshold)
MIN_WALL_PX = 40
# Minimum wall length in output mm (skip very short segments)
MIN_WALL_MM = 200
# Tolerance for axis clustering (mm)
AXIS_CLUSTER_TOL = 100
# Hough line detection parameters
HOUGH_THRESHOLD = 80
HOUGH_MIN_LINE_LEN = 50
HOUGH_MAX_LINE_GAP = 15
# Contour area thresholds (in px² at 200 DPI) for room detection
MIN_ROOM_AREA_PX = 3000    # ~15cm × 20cm at 1:100
MAX_ROOM_AREA_PX = 500000  # ~7m × 7m at 1:100
# Door arc detection
MIN_ARC_RADIUS_PX = 15
MAX_ARC_RADIUS_PX = 80
# Window detection — short parallel double lines
WINDOW_MIN_LEN_PX = 20
WINDOW_MAX_LEN_PX = 100
WINDOW_PARALLEL_TOL = 8  # px gap between parallel lines


# ===========================================================================
# Stage 1: PDF / Image → Preprocessed binary image
# ===========================================================================

def _pdf_to_image(pdf_path: str, dpi: int = 200) -> Optional[np.ndarray]:
    """Rasterize the best plan page from a PDF to a numpy image (BGR)."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF not installed — cannot rasterize PDF")
        return None

    doc = fitz.open(pdf_path)
    if len(doc) == 0:
        doc.close()
        return None

    # Pick the page with the most drawing content (= floor plan)
    best_page = 0
    best_score = 0
    for pi in range(len(doc)):
        page = doc[pi]
        score = 0
        for d in page.get_drawings():
            for item in d.get("items", []):
                if item[0] == "l":
                    p1, p2 = item[1], item[2]
                    length = math.hypot(p2.x - p1.x, p2.y - p1.y)
                    if length >= 20:
                        score += 1
        # Also count text blocks as tiebreaker
        score += len(page.get_text("dict").get("blocks", [])) * 0.1
        if score > best_score:
            best_score = score
            best_page = pi

    page = doc[best_page]
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)

    # Convert to numpy BGR
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, 3)
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    # Store page dimensions in PDF points for coordinate mapping
    page_rect = page.rect
    doc.close()

    return img, page_rect.width, page_rect.height, best_page


def _load_image(path: str) -> Optional[np.ndarray]:
    """Load an image file (PNG, JPG, TIFF) as BGR numpy array."""
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        logger.warning(f"Cannot read image: {path}")
    return img


def _preprocess(img: np.ndarray) -> tuple:
    """
    Adaptive preprocessing for architectural plans.
    Returns: (binary_image, gray_image, edges)
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Adaptive thresholding — handles uneven lighting in scans
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, blockSize=21, C=10
    )

    # Morphological close to connect broken wall segments
    kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_close, iterations=1)

    # Remove small noise blobs
    kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_open, iterations=1)

    # Canny edges for line detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    return binary, gray, edges


# ===========================================================================
# Stage 2: OpenCV — Structural geometry extraction
# ===========================================================================

def _detect_lines(edges: np.ndarray, binary: np.ndarray) -> list:
    """
    Detect wall lines using probabilistic Hough transform.
    Returns list of (x1, y1, x2, y2) in pixel coordinates.
    """
    lines_raw = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=HOUGH_THRESHOLD,
        minLineLength=HOUGH_MIN_LINE_LEN,
        maxLineGap=HOUGH_MAX_LINE_GAP
    )

    if lines_raw is None:
        # Fallback: try on binary image directly
        lines_raw = cv2.HoughLinesP(
            binary,
            rho=1,
            theta=np.pi / 180,
            threshold=HOUGH_THRESHOLD // 2,
            minLineLength=HOUGH_MIN_LINE_LEN,
            maxLineGap=HOUGH_MAX_LINE_GAP * 2
        )

    if lines_raw is None:
        return []

    lines = []
    for line in lines_raw:
        x1, y1, x2, y2 = line[0]
        length = math.hypot(x2 - x1, y2 - y1)
        if length >= MIN_WALL_PX:
            lines.append((x1, y1, x2, y2))

    return lines


def _classify_lines(lines: list) -> dict:
    """
    Classify detected lines. In rasterized plans, axes are usually dashed
    and indistinguishable from walls, so we treat ALL lines as walls.
    Axes are inferred later from wall endpoint clustering.
    """
    if not lines:
        return {'walls': [], 'axes_h': [], 'axes_v': []}

    walls = []
    for x1, y1, x2, y2 in lines:
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        angle = math.atan2(min(dx, dy), max(dx, dy))

        # Filter out strongly diagonal lines (>20° from H/V) — noise/hatching
        if angle > 0.35:  # ~20 degrees
            continue

        walls.append((x1, y1, x2, y2))

    return {'walls': walls, 'axes_h': [], 'axes_v': []}


def _merge_collinear_walls(walls: list, tolerance: float = 8.0) -> list:
    """Merge nearly collinear wall segments that are close together."""
    if len(walls) < 2:
        return walls

    merged = list(walls)
    changed = True
    max_iters = 5

    while changed and max_iters > 0:
        max_iters -= 1
        changed = False
        new_merged = []
        used = set()

        for i in range(len(merged)):
            if i in used:
                continue
            x1, y1, x2, y2 = merged[i]
            dx_i = x2 - x1
            dy_i = y2 - y1
            len_i = math.hypot(dx_i, dy_i)
            if len_i < 1:
                continue

            for j in range(i + 1, len(merged)):
                if j in used:
                    continue
                ax1, ay1, ax2, ay2 = merged[j]
                dx_j = ax2 - ax1
                dy_j = ay2 - ay1
                len_j = math.hypot(dx_j, dy_j)
                if len_j < 1:
                    continue

                # Check if nearly parallel (cross product ~ 0)
                cross = abs(dx_i * dy_j - dy_i * dx_j) / (len_i * len_j)
                if cross > 0.1:
                    continue

                # Check if close (perpendicular distance < tolerance)
                # Midpoint of j to line i
                mx, my = (ax1 + ax2) / 2, (ay1 + ay2) / 2
                dist = abs(dy_i * mx - dx_i * my + x2 * y1 - y2 * x1) / len_i
                if dist > tolerance:
                    continue

                # Check if overlapping or close in projection
                # Project all 4 endpoints onto line i direction
                ux, uy = dx_i / len_i, dy_i / len_i
                projs = [
                    ux * (x1 - x1) + uy * (y1 - y1),
                    ux * (x2 - x1) + uy * (y2 - y1),
                    ux * (ax1 - x1) + uy * (ay1 - y1),
                    ux * (ax2 - x1) + uy * (ay2 - y1),
                ]
                min_p, max_p = min(projs), max(projs)
                gap = max(0, min(projs[2], projs[3]) - max(projs[0], projs[1]),
                          min(projs[0], projs[1]) - max(projs[2], projs[3]))
                # Allow small gap for merging
                if gap > tolerance * 3:
                    continue

                # Merge: take the two extreme projected points
                pts = [(x1 + ux * p, y1 + uy * p) for p in projs]
                idx_min = projs.index(min_p)
                idx_max = projs.index(max_p)
                x1, y1 = pts[idx_min][0], pts[idx_min][1]
                x2, y2 = pts[idx_max][0], pts[idx_max][1]
                dx_i, dy_i = x2 - x1, y2 - y1
                len_i = math.hypot(dx_i, dy_i)
                used.add(j)
                changed = True

            new_merged.append((round(x1), round(y1), round(x2), round(y2)))
            used.add(i)

        # Add any segments that weren't part of merging
        for i in range(len(merged)):
            if i not in used:
                new_merged.append(merged[i])

        merged = new_merged

    return merged


def _detect_rooms(binary: np.ndarray, img_h: int, img_w: int) -> list:
    """
    Detect room-like enclosed regions using contour detection.
    Returns list of {centroid_x, centroid_y, area_px, bbox}.
    """
    # Dilate to close wall gaps (room boundaries need to be closed)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(binary, cv2.MORPH_DILATE, kernel, iterations=2)

    # Invert to find enclosed spaces (rooms are white areas between black walls)
    inv = cv2.bitwise_not(closed)

    contours, _ = cv2.findContours(inv, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    rooms = []
    total_area = img_h * img_w

    for cnt in contours:
        area = cv2.contourArea(cnt)
        # Filter by area: skip tiny noise and the outer boundary
        if area < MIN_ROOM_AREA_PX or area > total_area * 0.5:
            continue

        # Compute centroid
        M = cv2.moments(cnt)
        if M["m00"] == 0:
            continue
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])

        # Bounding rect
        x, y, w, h = cv2.boundingRect(cnt)

        # Aspect ratio filter: rooms are roughly rectangular
        aspect = max(w, h) / max(min(w, h), 1)
        if aspect > 8:
            continue

        rooms.append({
            'centroid_x': cx,
            'centroid_y': cy,
            'area_px': area,
            'bbox': (x, y, w, h),
            'contour': cnt
        })

    return rooms


def _detect_doors_arcs(binary: np.ndarray) -> list:
    """Detect door swing arcs using Hough circle transform."""
    # Doors appear as quarter-circle arcs in floor plans
    circles = cv2.HoughCircles(
        binary, cv2.HOUGH_GRADIENT,
        dp=1.5, minDist=30,
        param1=100, param2=40,
        minRadius=MIN_ARC_RADIUS_PX,
        maxRadius=MAX_ARC_RADIUS_PX
    )

    doors = []
    if circles is not None:
        circles = np.round(circles[0, :]).astype(int)
        for (cx, cy, r) in circles:
            doors.append({
                'type': 'arc',
                'center_px': (cx, cy),
                'radius_px': r
            })

    return doors


def _extract_axes_from_lines(axes_h: list, axes_v: list,
                              px_to_mm_x, px_to_mm_y) -> tuple:
    """
    Convert detected axis lines to sorted coordinate lists (mm).
    Deduplicate close axes.
    """
    # Vertical axes → X coordinates
    x_coords = []
    for x1, y1, x2, y2 in axes_v:
        x_mm = px_to_mm_x((x1 + x2) / 2)
        x_coords.append(x_mm)

    # Horizontal axes → Y coordinates
    y_coords = []
    for x1, y1, x2, y2 in axes_h:
        y_mm = px_to_mm_y((y1 + y2) / 2)
        y_coords.append(y_mm)

    # Deduplicate
    def dedup(coords, tol=AXIS_CLUSTER_TOL):
        if not coords:
            return []
        coords = sorted(coords)
        result = [coords[0]]
        for c in coords[1:]:
            if c - result[-1] > tol:
                result.append(c)
        return result

    return dedup(x_coords), dedup(y_coords)


# ===========================================================================
# Stage 3: Claude Vision — Semantic label extraction
# ===========================================================================

def _extract_labels_with_vision(img_path: str, api_key: Optional[str] = None) -> dict:
    """
    Use Claude Vision to extract room labels, dimensions, and annotations
    from an architectural plan image.

    Returns: {
        'rooms': [{'name': str, 'x_pct': float, 'y_pct': float}],
        'dimensions': [{'text': str, 'x_pct': float, 'y_pct': float}],
        'scale': str or None  (e.g. "1:100")
    }
    Coordinates are in % of image width/height (0.0–1.0).
    """
    import base64
    import json

    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("No Anthropic API key — skipping Vision label extraction")
        return {'rooms': [], 'dimensions': [], 'scale': None}

    # Read and encode image
    with open(img_path, "rb") as f:
        img_data = base64.standard_b64encode(f.read()).decode("utf-8")

    # Determine media type
    ext = os.path.splitext(img_path)[1].lower()
    media_map = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                 '.tiff': 'image/tiff', '.tif': 'image/tiff', '.webp': 'image/webp'}
    media_type = media_map.get(ext, 'image/png')

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        prompt = """Analyze this architectural floor plan image. Extract ALL text labels and their approximate positions.

For each room label you find, provide:
- name: the room name exactly as written (e.g. "Chambre 1", "Salon", "Cuisine", "SDB", "WC", "Hall")
- x_pct: horizontal position as fraction of image width (0.0 = left, 1.0 = right)
- y_pct: vertical position as fraction of image height (0.0 = top, 1.0 = bottom)

For each dimension/measurement you find, provide:
- text: the dimension text (e.g. "4.50", "3.20 m", "2.80")
- x_pct, y_pct: position as fraction of image dimensions

Also detect the scale if visible (e.g. "1:100", "1:50").

Return ONLY valid JSON, no markdown:
{
  "rooms": [{"name": "...", "x_pct": 0.xx, "y_pct": 0.xx}],
  "dimensions": [{"text": "...", "x_pct": 0.xx, "y_pct": 0.xx}],
  "scale": "1:100" or null
}"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": img_data
                        }
                    },
                    {"type": "text", "text": prompt}
                ]
            }]
        )

        # Parse response
        text = response.content[0].text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        result = json.loads(text)
        rooms = result.get("rooms", [])
        dims = result.get("dimensions", [])
        scale = result.get("scale")

        logger.info(f"Vision: {len(rooms)} rooms, {len(dims)} dimensions, scale={scale}")
        return {'rooms': rooms, 'dimensions': dims, 'scale': scale}

    except Exception as e:
        logger.warning(f"Vision label extraction failed: {e}")
        return {'rooms': [], 'dimensions': [], 'scale': None}


# ===========================================================================
# Stage 4: Fusion — Combine geometry + labels → normalized output
# ===========================================================================

def _compute_scale(vision_dims: list, lines: list, img_w: int, img_h: int,
                   declared_scale: Optional[str] = None) -> float:
    """
    Compute px → mm conversion factor.

    Strategy:
    1. If declared scale (e.g. "1:100"), use it with standard A3 at 200 DPI
    2. If Vision found dimensions, cross-reference with line lengths
    3. Fallback: assume typical A3 plan at 1:100 scale
    """
    # Strategy 1: declared scale
    if declared_scale:
        try:
            parts = declared_scale.replace(" ", "").split(":")
            scale_factor = float(parts[1]) / float(parts[0])
            # At 200 DPI, 1 inch = 200 px. 1 inch = 25.4 mm.
            # At scale 1:S, 1mm on paper = S mm real
            px_per_mm_paper = 200 / 25.4  # ~7.87 px per mm on paper
            return scale_factor / px_per_mm_paper  # mm_real per px
        except Exception:
            pass

    # Strategy 2: cross-reference Vision dimensions with detected lines
    if vision_dims and lines:
        # Find dimensions that are near wall endpoints
        calibrations = []
        for dim in vision_dims:
            try:
                # Parse dimension value (e.g. "4.50" → 4500 mm)
                text = dim.get('text', '')
                val = float(text.replace('m', '').replace(',', '.').strip())
                if val < 0.5:
                    continue
                if val < 50:
                    val *= 1000  # meters → mm
                dim_mm = val

                # Find nearby wall line
                dx = dim['x_pct'] * img_w
                dy = dim['y_pct'] * img_h

                for x1, y1, x2, y2 in lines:
                    # Check if dimension label is near this line
                    mid_x = (x1 + x2) / 2
                    mid_y = (y1 + y2) / 2
                    dist = math.hypot(dx - mid_x, dy - mid_y)
                    line_len = math.hypot(x2 - x1, y2 - y1)

                    if dist < line_len * 0.8 and line_len > 30:
                        px_per_mm = line_len / dim_mm
                        if 0.01 < px_per_mm < 5.0:  # sanity check
                            calibrations.append(1.0 / px_per_mm)
            except (ValueError, KeyError):
                continue

        if calibrations:
            # Use median calibration
            calibrations.sort()
            median = calibrations[len(calibrations) // 2]
            logger.info(f"Scale calibrated from {len(calibrations)} dimension matches: {median:.4f} mm/px")
            return median

    # Strategy 3: fallback — assume A3 (420×297mm) at 1:100 = 200 DPI
    # At 200 DPI, A3 landscape = 3307 × 2339 px
    # Real building span ≈ 42m × 30m = 42000 × 30000 mm
    # So mm/px ≈ 42000 / 3307 ≈ 12.7
    if img_w > 0:
        assumed_building_width_mm = 30000  # 30m typical
        return float(assumed_building_width_mm / img_w)

    return 10.0  # absolute fallback


def _fuse_geometry(cv_lines: dict, cv_rooms: list, cv_doors: list,
                   vision_labels: dict,
                   mm_per_px: float, img_w: int, img_h: int) -> dict:
    """
    Merge OpenCV geometry + Vision labels into the normalized format.

    Output format matches _extract_dxf_geometry():
    {
        walls: [{type:'line', start:[x,y], end:[x,y]}],
        windows: [...],
        doors: [{type:'arc', center:[x,y], radius:float}],
        rooms: [{name:str, x:float, y:float}],
        axes_x: [sorted floats in mm],
        axes_y: [sorted floats in mm]
    }
    """
    # Coordinate transform functions: pixel → mm (native Python float)
    # Origin at top-left of image, Y increases downward
    # Convert to building coords: origin at bottom-left, Y increases upward
    def px_to_mm_x(px):
        return round(float(px) * mm_per_px, 1)

    def px_to_mm_y(py):
        return round(float(img_h - py) * mm_per_px, 1)

    geometry = {
        'walls': [],
        'windows': [],
        'doors': [],
        'sanitary': [],
        'rooms': [],
        'axes_x': [],
        'axes_y': []
    }

    # --- Walls ---
    wall_lines = cv_lines.get('walls', [])
    wall_lines = _merge_collinear_walls(wall_lines)

    for x1, y1, x2, y2 in wall_lines:
        mx1, my1 = px_to_mm_x(x1), px_to_mm_y(y1)
        mx2, my2 = px_to_mm_x(x2), px_to_mm_y(y2)
        length_mm = math.hypot(mx2 - mx1, my2 - my1)
        if length_mm < MIN_WALL_MM:
            continue
        geometry['walls'].append({
            'type': 'line',
            'start': [mx1, my1],
            'end': [mx2, my2]
        })

    # --- Axes ---
    axes_x, axes_y = _extract_axes_from_lines(
        cv_lines.get('axes_h', []),
        cv_lines.get('axes_v', []),
        px_to_mm_x, px_to_mm_y
    )
    geometry['axes_x'] = axes_x
    geometry['axes_y'] = axes_y

    # --- Doors ---
    for door in cv_doors:
        cx, cy = door['center_px']
        geometry['doors'].append({
            'type': 'arc',
            'center': [px_to_mm_x(cx), px_to_mm_y(cy)],
            'radius': round(door['radius_px'] * mm_per_px, 1),
            'start_angle': 0,
            'end_angle': 90
        })

    # --- Rooms (from Vision labels, positioned onto geometry) ---
    vision_rooms = vision_labels.get('rooms', [])
    for room in vision_rooms:
        name = room.get('name', '').strip()
        if not name:
            continue
        # Convert % position to mm
        rx = px_to_mm_x(room.get('x_pct', 0.5) * img_w)
        ry = px_to_mm_y(room.get('y_pct', 0.5) * img_h)
        geometry['rooms'].append({'name': name, 'x': rx, 'y': ry})

    # If Vision found no rooms, try to label from contour centroids
    if not geometry['rooms'] and cv_rooms:
        for i, room in enumerate(cv_rooms):
            cx, cy = room['centroid_x'], room['centroid_y']
            area_m2 = (room['area_px'] * mm_per_px * mm_per_px) / 1e6
            bx, by, bw, bh = room['bbox']
            # Auto-label based on area
            if area_m2 < 4:
                name = f"SDB/WC"
            elif area_m2 < 10:
                name = f"Pièce {i+1}"
            elif area_m2 < 20:
                name = f"Chambre {i+1}"
            else:
                name = f"Salon/Séjour"
            geometry['rooms'].append({
                'name': name,
                'x': px_to_mm_x(cx),
                'y': px_to_mm_y(cy),
                'area_m2': round(area_m2, 1),
                'bbox_mm': [
                    px_to_mm_x(bx), px_to_mm_y(by),
                    round(bw * mm_per_px, 1), round(bh * mm_per_px, 1),
                ],
                'aspect': round(max(bw, bh) / max(min(bw, bh), 1), 2),
            })

    # --- Infer axes from walls if none detected ---
    if len(geometry['axes_x']) < 2 or len(geometry['axes_y']) < 2:
        inferred_x, inferred_y = _infer_axes_from_walls(geometry['walls'])
        if len(inferred_x) >= 2:
            geometry['axes_x'] = inferred_x
        if len(inferred_y) >= 2:
            geometry['axes_y'] = inferred_y

    logger.info(
        f"Fusion result: {len(geometry['walls'])} walls, "
        f"{len(geometry['rooms'])} rooms, "
        f"{len(geometry['doors'])} doors, "
        f"axes {len(geometry['axes_x'])}x{len(geometry['axes_y'])}"
    )

    return geometry


def _infer_axes_from_walls(walls: list) -> tuple:
    """Infer structural axes from wall endpoint clustering."""
    if not walls:
        return [], []

    # Collect all X and Y coordinates from wall endpoints
    x_coords = []
    y_coords = []
    for w in walls:
        if w['type'] == 'line':
            x_coords.extend([w['start'][0], w['end'][0]])
            y_coords.extend([w['start'][1], w['end'][1]])

    def cluster(coords, tol=AXIS_CLUSTER_TOL, min_count=3):
        """Cluster coordinates and return centers of dense clusters."""
        if not coords:
            return []
        coords = sorted(coords)
        clusters = []
        current = [coords[0]]
        for c in coords[1:]:
            if c - current[-1] < tol:
                current.append(c)
            else:
                if len(current) >= min_count:
                    clusters.append(round(sum(current) / len(current), 1))
                current = [c]
        if len(current) >= min_count:
            clusters.append(round(sum(current) / len(current), 1))
        return clusters

    return cluster(x_coords), cluster(y_coords)


# ===========================================================================
# Main entry point
# ===========================================================================

def extract_geometry_cv(
    file_path: str,
    file_type: str = "auto",
    dpi: int = 200,
    use_vision: bool = True,
    api_key: Optional[str] = None
) -> Optional[dict]:
    """
    Main entry: extract geometry from any architectural plan file.

    Args:
        file_path: Path to PDF, DWG (pre-converted image), PNG, JPG, etc.
        file_type: "pdf", "image", or "auto" (detect from extension)
        dpi: Rasterization DPI for PDFs (default 200)
        use_vision: Whether to call Claude Vision for label extraction
        api_key: Anthropic API key (falls back to ANTHROPIC_API_KEY env var)

    Returns:
        Geometry dict compatible with plan generators, or None on failure.
    """
    logger.info(f"CV geometry extraction: {file_path} (type={file_type})")

    # Detect file type
    if file_type == "auto":
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            file_type = 'pdf'
        elif ext in ('.png', '.jpg', '.jpeg', '.tiff', '.tif', '.webp', '.bmp'):
            file_type = 'image'
        else:
            logger.warning(f"Unknown file type: {ext}")
            return None

    # --- Stage 1: Get image ---
    img = None
    pdf_w_pt = pdf_h_pt = 0
    page_idx = 0

    if file_type == 'pdf':
        result = _pdf_to_image(file_path, dpi=dpi)
        if result is None:
            logger.warning("Failed to rasterize PDF")
            return None
        img, pdf_w_pt, pdf_h_pt, page_idx = result
    elif file_type == 'image':
        img = _load_image(file_path)

    if img is None:
        return None

    img_h, img_w = img.shape[:2]
    logger.info(f"Image: {img_w}×{img_h} px (page {page_idx})")

    # --- Stage 2: OpenCV geometry ---
    binary, gray, edges = _preprocess(img)
    raw_lines = _detect_lines(edges, binary)
    classified = _classify_lines(raw_lines)
    cv_rooms = _detect_rooms(binary, img_h, img_w)
    cv_doors = _detect_doors_arcs(binary)

    logger.info(
        f"OpenCV: {len(classified['walls'])} walls, "
        f"{len(classified['axes_h'])}+{len(classified['axes_v'])} axes, "
        f"{len(cv_rooms)} rooms, {len(cv_doors)} doors"
    )

    # --- Stage 3: Vision labels ---
    vision_labels = {'rooms': [], 'dimensions': [], 'scale': None}
    if use_vision:
        # Save image to temp file for Vision API
        tmp_img = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                tmp_img = f.name
                cv2.imwrite(tmp_img, img)
            vision_labels = _extract_labels_with_vision(tmp_img, api_key=api_key)
        finally:
            if tmp_img and os.path.exists(tmp_img):
                try:
                    os.unlink(tmp_img)
                except OSError:
                    pass

    # --- Stage 4: Compute scale & fuse ---
    mm_per_px = _compute_scale(
        vision_labels.get('dimensions', []),
        classified['walls'],
        img_w, img_h,
        declared_scale=vision_labels.get('scale')
    )
    logger.info(f"Scale: {mm_per_px:.2f} mm/px")

    geometry = _fuse_geometry(
        classified, cv_rooms, cv_doors,
        vision_labels,
        mm_per_px, img_w, img_h
    )

    # Store metadata for coordinate mapping
    geometry['_cv_meta'] = {
        'source': file_type,
        'img_w': img_w,
        'img_h': img_h,
        'mm_per_px': mm_per_px,
        'dpi': dpi,
        'page_idx': page_idx,
    }
    if file_type == 'pdf':
        geometry['_cv_meta']['pdf_w_pt'] = pdf_w_pt
        geometry['_cv_meta']['pdf_h_pt'] = pdf_h_pt

    # Quality gate: need at least some walls
    if len(geometry['walls']) < 5:
        logger.warning(f"Too few walls ({len(geometry['walls'])}), CV extraction unreliable")
        # Still return — caller can decide whether to use it
        geometry['_cv_meta']['quality'] = 'low'
    else:
        geometry['_cv_meta']['quality'] = 'good' if len(geometry['walls']) > 20 else 'medium'

    return geometry


# ===========================================================================
# Convenience: extract from PDF with fallback chain
# ===========================================================================

def extract_geometry_from_pdf_cv(pdf_path: str, use_vision: bool = True) -> Optional[dict]:
    """
    Convenience wrapper for PDF files. Tries CV pipeline, then falls back
    to existing vector extraction if CV quality is low.
    """
    # Try CV pipeline first
    cv_geom = extract_geometry_cv(pdf_path, file_type='pdf', use_vision=use_vision)

    if cv_geom and cv_geom.get('_cv_meta', {}).get('quality') != 'low':
        return cv_geom

    # Fallback: try vector extraction (existing code)
    try:
        from dwg_converter import pdf_to_geometry
        vec_geom = pdf_to_geometry(pdf_path)
        if vec_geom and len(vec_geom.get('walls', [])) > len((cv_geom or {}).get('walls', [])):
            logger.info("Falling back to vector PDF extraction (more walls)")
            return vec_geom
    except Exception as e:
        logger.info(f"Vector fallback not available: {e}")

    return cv_geom
