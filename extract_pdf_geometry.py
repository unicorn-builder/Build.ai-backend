"""
extract_pdf_geometry.py — Extract wall geometry from architectural PDF plans.
Uses PyMuPDF (fitz) get_drawings() to extract vector paths from each page.
Outputs the same dict format as DWG geometry so the existing plan generators
can use it directly via _draw_dwg().

Returns:
  {
    "walls": [{"type":"line","start":[x,y],"end":[x,y]}, {"type":"polyline","points":[[x,y],...],"closed":bool}],
    "rooms": [{"name":"CHAMBRE","x":cx,"y":cy}],
    "windows": [...],
    "doors": [...],
  }
  Coordinates in mm (same convention as DWG geometry).
"""

import logging
from collections import defaultdict

logger = logging.getLogger("tijan")

# Minimum path length (mm) to keep — filters noise/dots
MIN_PATH_LEN_MM = 200
# Wall thickness range (mm) — filled rects in this range are likely walls
WALL_THICK_MIN = 50
WALL_THICK_MAX = 400
# Minimum line segment length (mm) to keep
MIN_SEG_LEN_MM = 80


def _pt_to_mm(val):
    """PDF points to mm (1pt = 0.3528mm, but we use the raw coordinate scale)."""
    # PDF coordinates are in points (72 dpi). We convert to mm-scale.
    return val * 25.4 / 72.0


def _distance(p1, p2):
    return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2) ** 0.5


def _path_length(points):
    total = 0
    for i in range(len(points)-1):
        total += _distance(points[i], points[i+1])
    return total


def _is_wall_rect(rect_w, rect_h):
    """Check if a filled rectangle looks like a wall (thin and long)."""
    short = min(rect_w, rect_h)
    long_ = max(rect_w, rect_h)
    if WALL_THICK_MIN <= short <= WALL_THICK_MAX and long_ > short * 2.5:
        return True
    return False


def extract_geometry_from_page(page, page_idx=0):
    """Extract wall geometry from a single PDF page.

    Args:
        page: fitz.Page object
        page_idx: page number (for logging)

    Returns:
        dict with 'walls', 'rooms', 'windows', 'doors' lists,
        or None if too few elements found.
    """
    walls = []
    rooms = []
    windows = []
    doors = []

    # ── 1. Extract vector paths (drawings) ──
    try:
        drawings = page.get_drawings()
    except Exception as e:
        logger.warning(f"Page {page_idx}: get_drawings failed: {e}")
        return None

    if not drawings:
        logger.info(f"Page {page_idx}: no vector drawings found")
        return None

    for d in drawings:
        items = d.get("items", [])
        if not items:
            continue

        # Build point list from path items
        points = []
        for item in items:
            kind = item[0]  # "l" (line), "c" (curve), "re" (rect), "qu" (quad)
            if kind == "l":  # line to
                p1 = (_pt_to_mm(item[1].x), _pt_to_mm(item[1].y))
                p2 = (_pt_to_mm(item[2].x), _pt_to_mm(item[2].y))
                if not points or _distance(points[-1], p1) > 0.5:
                    points.append(p1)
                points.append(p2)

            elif kind == "re":  # rectangle
                rect = item[1]
                x0 = _pt_to_mm(rect.x0)
                y0 = _pt_to_mm(rect.y0)
                x1 = _pt_to_mm(rect.x1)
                y1 = _pt_to_mm(rect.y1)
                rw = abs(x1 - x0)
                rh = abs(y1 - y0)

                if _is_wall_rect(rw, rh):
                    # Thin rectangle = wall, convert to center line
                    if rw < rh:  # vertical wall
                        cx = (x0 + x1) / 2
                        walls.append({
                            "type": "line",
                            "start": [cx, y0],
                            "end": [cx, y1],
                        })
                    else:  # horizontal wall
                        cy = (y0 + y1) / 2
                        walls.append({
                            "type": "line",
                            "start": [x0, cy],
                            "end": [x1, cy],
                        })
                elif rw > MIN_SEG_LEN_MM and rh > MIN_SEG_LEN_MM:
                    # Larger rectangle — could be a room outline
                    walls.append({
                        "type": "polyline",
                        "points": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
                        "closed": True,
                    })

            elif kind == "c":  # cubic bezier — approximate with line
                p1 = (_pt_to_mm(item[1].x), _pt_to_mm(item[1].y))
                p4 = (_pt_to_mm(item[4].x), _pt_to_mm(item[4].y))
                if _distance(p1, p4) > MIN_SEG_LEN_MM:
                    if not points or _distance(points[-1], p1) > 0.5:
                        points.append(p1)
                    points.append(p4)

            elif kind == "qu":  # quad
                quad = item[1]
                pts_q = [
                    (_pt_to_mm(quad.ul.x), _pt_to_mm(quad.ul.y)),
                    (_pt_to_mm(quad.ur.x), _pt_to_mm(quad.ur.y)),
                    (_pt_to_mm(quad.lr.x), _pt_to_mm(quad.lr.y)),
                    (_pt_to_mm(quad.ll.x), _pt_to_mm(quad.ll.y)),
                ]
                walls.append({
                    "type": "polyline",
                    "points": pts_q,
                    "closed": True,
                })

        # Convert accumulated points to wall segments
        if len(points) >= 2 and _path_length(points) >= MIN_PATH_LEN_MM:
            # Check if closed path
            closed = len(points) >= 3 and _distance(points[0], points[-1]) < 5.0

            if len(points) == 2:
                walls.append({
                    "type": "line",
                    "start": list(points[0]),
                    "end": list(points[1]),
                })
            else:
                walls.append({
                    "type": "polyline",
                    "points": [list(p) for p in points],
                    "closed": closed,
                })

    # ── 2. Extract text labels (room names) ──
    try:
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if b.get("type") != 0:  # not text
                continue
            for line in b.get("lines", []):
                text = ""
                for span in line.get("spans", []):
                    text += span.get("text", "")
                text = text.strip()
                if not text or len(text) > 40 or len(text) < 2:
                    continue

                # Room-like labels: words that look like room names
                bbox = line.get("bbox", b.get("bbox"))
                if bbox:
                    cx = _pt_to_mm((bbox[0] + bbox[2]) / 2)
                    cy = _pt_to_mm((bbox[1] + bbox[3]) / 2)

                    # Heuristic: room names are typically uppercase or common names
                    upper_words = ["CHAMBRE", "CUISINE", "SALON", "SEJOUR", "HALL",
                                   "SDB", "WC", "BUREAU", "DEPOT", "DRESSING",
                                   "TERRASSE", "BALCON", "GARAGE", "ENTREE",
                                   "RESERVE", "LOCAL", "PISCINE", "JARDIN",
                                   "VIDE", "COUR", "BAC", "ESCALIER"]
                    text_up = text.upper()
                    is_room = any(w in text_up for w in upper_words)
                    # Also catch "XX.XX m²" area labels
                    is_area = "m²" in text or "m2" in text.lower()

                    if is_room or is_area:
                        rooms.append({
                            "name": text,
                            "x": cx,
                            "y": cy,
                        })
    except Exception as e:
        logger.warning(f"Page {page_idx}: text extraction failed: {e}")

    if len(walls) < 10:
        logger.info(f"Page {page_idx}: only {len(walls)} walls found, skipping")
        return None

    logger.info(f"Page {page_idx}: extracted {len(walls)} walls, {len(rooms)} rooms")
    return {
        "walls": walls,
        "rooms": rooms,
        "windows": windows,
        "doors": doors,
    }


def extract_geometry_from_pdf(pdf_path, max_pages=5):
    """Extract geometry from a multi-page architectural PDF.

    Returns a dict keyed by level label:
      {
        "RDC": {walls, rooms, ...},
        "Étage courant": {walls, rooms, ...},
        "Terrasse": {walls, rooms, ...},
      }
    or a flat dict with "walls" key if only one usable page.
    """
    import fitz

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        logger.error(f"Cannot open PDF: {e}")
        return None

    try:
        n_pages = min(len(doc), max_pages)
        if n_pages == 0:
            return None

        results = {}
        # Common level keywords in French architectural plans
        level_keywords = {
            "RDC": ["RDC", "REZ-DE-CHAUSSEE", "REZ DE CHAUSSEE", "R.D.C", "GROUND"],
            "Étage 1": ["1ER ETAGE", "R+1", "ETAGE 1", "1ST FLOOR", "PREMIER"],
            "Étage 2": ["2EME ETAGE", "R+2", "ETAGE 2", "2ND FLOOR", "DEUXIEME"],
            "Étage 3": ["3EME ETAGE", "R+3", "ETAGE 3"],
            "Terrasse": ["TERRASSE", "TOITURE", "ROOF", "TERRACE"],
            "Sous-Sol": ["SOUS-SOL", "BASEMENT", "SS", "SOUS SOL"],
        }

        for i in range(n_pages):
            page = doc[i]
            geom = extract_geometry_from_page(page, i)
            if geom is None:
                continue

            # Try to identify the level from page text
            page_text = page.get_text().upper()
            level_name = f"Niveau {i}"  # fallback

            for name, keywords in level_keywords.items():
                if any(kw in page_text for kw in keywords):
                    level_name = name
                    break

            # Avoid duplicate level names
            if level_name in results:
                level_name = f"{level_name} ({i+1})"

            results[level_name] = geom

        if not results:
            return None

        # If only one page, return flat dict for compatibility
        if len(results) == 1:
            return list(results.values())[0]

        return results

    finally:
        doc.close()


def extract_geometry_from_pdf_bytes(pdf_bytes, max_pages=5):
    """Same as extract_geometry_from_pdf but from bytes."""
    import fitz
    import tempfile, os

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        return extract_geometry_from_pdf(tmp_path, max_pages)
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
