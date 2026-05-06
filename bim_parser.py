"""
bim_parser.py — Universal parser that produces a TijanBIM Building

All input formats (PDF, DWG, DXF) go through this module and produce
the same Building object with rooms, walls, openings, and axes.

Strategy:
  1. DXF (ezdxf) → extract walls, axes, texts, dimensions → Room Graph
  2. DWG → convert to DXF (LibreDWG/ODA/APS) → same as above
  3. PDF → Claude Vision extracts room layout → Room Graph
  4. Fallback → parametric grid from basic parameters

The output is always a Building object that can feed:
  - engine_structure_v2 (via to_params_dict())
  - engine_mep_v2 (via to_params_dict())
  - room_rules (equipment placement)
  - plan generators (2D/3D output)
"""
from __future__ import annotations
import os
import re
import json
import math
import base64
import logging
import pathlib
import unicodedata
from collections import deque
from typing import Dict, List, Optional, Tuple, Any

from bim_model import (
    Building, Level, Room, Wall, Opening, Point, BBox,
    RoomType, WallType, OpeningType
)

logger = logging.getLogger("tijan.bim_parser")

CLAUDE_MODEL = "claude-sonnet-4-20250514"

# Room type classification from text labels
ROOM_TYPE_MAP = {
    # French
    "sejour": RoomType.SEJOUR, "salon": RoomType.SEJOUR,
    "living": RoomType.SEJOUR, "living room": RoomType.SEJOUR,
    "salle a manger": RoomType.SEJOUR, "dining": RoomType.SEJOUR,
    "chambre": RoomType.CHAMBRE, "bedroom": RoomType.CHAMBRE,
    "master bedroom": RoomType.CHAMBRE, "family bedroom": RoomType.CHAMBRE,
    "guest bedroom": RoomType.CHAMBRE, "chambre amis": RoomType.CHAMBRE,
    "chambre parentale": RoomType.CHAMBRE, "ch.": RoomType.CHAMBRE,
    "cuisine": RoomType.CUISINE, "kitchen": RoomType.CUISINE,
    "sdb": RoomType.SDB, "salle de bain": RoomType.SDB,
    "bathroom": RoomType.SDB, "master bath": RoomType.SDB,
    "family bathroom": RoomType.SDB, "salle d'eau": RoomType.SDB,
    "wc": RoomType.WC, "toilette": RoomType.WC, "toilet": RoomType.WC,
    "guest toilet": RoomType.WC,
    "couloir": RoomType.COULOIR, "circulation": RoomType.COULOIR,
    "circ": RoomType.COULOIR, "corridor": RoomType.COULOIR,
    "hall": RoomType.HALL, "lobby": RoomType.HALL,
    "foyer": RoomType.FOYER, "entree": RoomType.FOYER, "entrance": RoomType.FOYER,
    "dressing": RoomType.DRESSING, "walk-in": RoomType.DRESSING,
    "bureau": RoomType.BUREAU, "workspace": RoomType.BUREAU,
    "office": RoomType.BUREAU,
    "buanderie": RoomType.BUANDERIE, "laundry": RoomType.BUANDERIE,
    "linge": RoomType.RANGEMENT, "linen": RoomType.RANGEMENT,
    "rangement": RoomType.RANGEMENT, "storage": RoomType.RANGEMENT,
    "s. - food": RoomType.RANGEMENT, "s. - consumables": RoomType.RANGEMENT,
    "mech": RoomType.LOCAL_TECHNIQUE, "mech.": RoomType.LOCAL_TECHNIQUE,
    "local technique": RoomType.LOCAL_TECHNIQUE, "mechanical": RoomType.LOCAL_TECHNIQUE,
    "balcon": RoomType.BALCON, "balcony": RoomType.BALCON,
    "terrasse": RoomType.TERRASSE, "terrace": RoomType.TERRASSE,
    "parking": RoomType.PARKING,
    "commerce": RoomType.COMMERCE, "boutique": RoomType.COMMERCE,
    "escalier": RoomType.ESCALIER, "stairwell": RoomType.ESCALIER,
    "ascenseur": RoomType.ASCENSEUR, "elevator": RoomType.ASCENSEUR,
}


def classify_room_type(label: str) -> RoomType:
    """Classify a room type from its text label."""
    clean = label.lower().strip()
    clean = re.sub(r'\s+', ' ', clean)
    clean = re.sub(r'[0-9\-_\.]+$', '', clean).strip()
    # Strip accents: Séjour → sejour, Entrée → entree
    clean = unicodedata.normalize('NFD', clean)
    clean = ''.join(c for c in clean if unicodedata.category(c) != 'Mn')

    # Direct match
    if clean in ROOM_TYPE_MAP:
        return ROOM_TYPE_MAP[clean]

    # Partial match
    for key, rt in ROOM_TYPE_MAP.items():
        if key in clean or clean in key:
            return rt

    # Pattern match
    if re.match(r'^ch\.?\s*\d', clean):
        return RoomType.CHAMBRE
    if "sdb" in clean or "bain" in clean or "bath" in clean:
        return RoomType.SDB

    return RoomType.INCONNU


# Regex patterns for level and apartment detection
_LEVEL_RE = re.compile(
    r'(?:SOUS.?SOL|SS|RDC|REZ|R\+\d+|ETAGE\s*\d+|NIVEAU\s*\d+|TERRASSE)',
    re.IGNORECASE,
)
_TYPICAL_FLOOR_RE = re.compile(
    r'(?:ETAGES?|R\+)\s*(\d+)\s*[àa]\s*(\d+)',
    re.IGNORECASE,
)
_APARTMENT_RE = re.compile(
    r'(?:APPART|APP|APPARTEMENT|STUDIO|TYPE|LOGEMENT|UNIT)[.\s]*([A-Z0-9]+)',
    re.IGNORECASE,
)


# ══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════

def parse_to_building(file_path: str, client=None,
                       fallback_params: Optional[Dict] = None) -> Building:
    """Parse any supported file into a Building object.

    Args:
        file_path: Path to PDF, DWG, or DXF file
        client: Anthropic client (for Claude Vision on PDF)
        fallback_params: Default params if parsing fails

    Returns:
        Building object with rooms, walls, openings
    """
    path = pathlib.Path(file_path)
    ext = path.suffix.lower()

    building = None

    if ext == ".dxf":
        building = _parse_dxf(str(path))
    elif ext == ".dwg":
        building = _parse_dwg(str(path))
    elif ext == ".pdf":
        building = _parse_pdf(str(path), client)

    if building is None or len(building.all_rooms) == 0:
        logger.info("Parsing produced no rooms — falling back to parametric grid")
        params = fallback_params or {}
        building = Building.from_params_dict(params)
        building.source_format = f"{ext}_fallback"
        building.parse_confidence = 0.2

    building.source_file = str(path)
    return building


# ══════════════════════════════════════════════════════════════
# DXF PARSER (ezdxf)
# ══════════════════════════════════════════════════════════════

# Layer sets for door and window detection
_DOOR_LAYERS = {"A-DOOR", "DOOR", "PORTE", "A-DOOR-FULL"}
_WINDOW_LAYERS = {"A-GLAZ", "A-WINDOW", "WINDOW", "FENETRE", "VITRAGE"}
_DOOR_LAYERS_LOWER = {l.lower() for l in _DOOR_LAYERS}
_WINDOW_LAYERS_LOWER = {l.lower() for l in _WINDOW_LAYERS}


def _parse_dxf(path: str) -> Optional[Building]:
    """Parse a DXF file into a Building using ezdxf."""
    try:
        import ezdxf
        from ezdxf.recover import readfile
    except ImportError:
        logger.warning("ezdxf not installed")
        return None

    try:
        doc, _ = readfile(path)
    except Exception as e:
        logger.warning(f"ezdxf cannot read {path}: {e}")
        return None

    msp = doc.modelspace()

    # Extract raw geometry
    walls_raw = []
    texts = []
    dimensions = []
    doors_raw = []    # [(Point, width_estimate, layer), ...]
    windows_raw = []  # [(Point, width_estimate, layer), ...]

    # Wall detection layers (priority order)
    WALL_LAYERS = [
        "A-WALL", "WALL", "MURS", "A-WALL-FULL",
        "I-WALL", "CLOISON", "PARTITION",
        "0",  # Default layer fallback
    ]
    WALL_LAYERS_LOWER = {l.lower() for l in WALL_LAYERS}

    for entity in msp:
        etype = entity.dxftype()
        layer = entity.dxf.layer.upper() if hasattr(entity.dxf, 'layer') else ""
        layer_lower = layer.lower()

        # -----------------------------------------------------------
        # Walls: lines and polylines on wall layers
        # -----------------------------------------------------------
        if etype in ("LINE", "LWPOLYLINE", "POLYLINE"):
            if layer_lower in WALL_LAYERS_LOWER or "wall" in layer_lower or "mur" in layer_lower:
                try:
                    if etype == "LINE":
                        p1 = Point(entity.dxf.start.x, entity.dxf.start.y)
                        p2 = Point(entity.dxf.end.x, entity.dxf.end.y)
                        walls_raw.append((p1, p2, layer))
                    elif etype == "LWPOLYLINE":
                        pts = list(entity.get_points())
                        for i in range(len(pts) - 1):
                            p1 = Point(pts[i][0], pts[i][1])
                            p2 = Point(pts[i + 1][0], pts[i + 1][1])
                            walls_raw.append((p1, p2, layer))
                        if entity.closed and len(pts) > 2:
                            p1 = Point(pts[-1][0], pts[-1][1])
                            p2 = Point(pts[0][0], pts[0][1])
                            walls_raw.append((p1, p2, layer))
                except Exception:
                    pass

            # Windows on glazing layers (LINE / POLYLINE)
            elif layer_lower in _WINDOW_LAYERS_LOWER or "glaz" in layer_lower or "fenetre" in layer_lower:
                try:
                    if etype == "LINE":
                        p1 = Point(entity.dxf.start.x, entity.dxf.start.y)
                        p2 = Point(entity.dxf.end.x, entity.dxf.end.y)
                        width = p1.distance_to(p2)
                        mid = p1.midpoint(p2)
                        if width > 0.1:
                            windows_raw.append((mid, width, layer))
                    elif etype == "LWPOLYLINE":
                        pts = list(entity.get_points())
                        if len(pts) >= 2:
                            p1 = Point(pts[0][0], pts[0][1])
                            p2 = Point(pts[-1][0], pts[-1][1])
                            width = p1.distance_to(p2)
                            mid = p1.midpoint(p2)
                            if width > 0.1:
                                windows_raw.append((mid, width, layer))
                except Exception:
                    pass

        # -----------------------------------------------------------
        # Doors: ARC entities (door swings) on door layers
        # -----------------------------------------------------------
        elif etype == "ARC":
            if layer_lower in _DOOR_LAYERS_LOWER or "door" in layer_lower or "porte" in layer_lower:
                try:
                    cx = entity.dxf.center.x
                    cy = entity.dxf.center.y
                    radius = entity.dxf.radius
                    pos = Point(cx, cy)
                    # Arc radius ~ door width
                    width = radius if 0.3 < radius < 2.5 else 0.9
                    doors_raw.append((pos, width, layer))
                except Exception:
                    pass

        # -----------------------------------------------------------
        # Doors/windows: INSERT (block references) on relevant layers
        # -----------------------------------------------------------
        elif etype == "INSERT":
            if layer_lower in _DOOR_LAYERS_LOWER or "door" in layer_lower or "porte" in layer_lower:
                try:
                    pos = Point(entity.dxf.insert.x, entity.dxf.insert.y)
                    # Use x-scale as width estimate, default 0.9m
                    sx = getattr(entity.dxf, 'xscale', 1.0) or 1.0
                    width = abs(sx) if 0.3 < abs(sx) < 2.5 else 0.9
                    doors_raw.append((pos, width, layer))
                except Exception:
                    pass
            elif layer_lower in _WINDOW_LAYERS_LOWER or "glaz" in layer_lower or "fenetre" in layer_lower:
                try:
                    pos = Point(entity.dxf.insert.x, entity.dxf.insert.y)
                    sx = getattr(entity.dxf, 'xscale', 1.0) or 1.0
                    width = abs(sx) if 0.3 < abs(sx) < 3.0 else 1.2
                    windows_raw.append((pos, width, layer))
                except Exception:
                    pass

        # -----------------------------------------------------------
        # Texts
        # -----------------------------------------------------------
        elif etype in ("TEXT", "MTEXT", "ATTDEF", "ATTRIB"):
            try:
                if etype == "MTEXT":
                    txt = entity.plain_mtext().strip()
                else:
                    txt = entity.dxf.text.strip()
                if txt and len(txt) < 300:
                    pos = entity.dxf.insert if hasattr(entity.dxf, 'insert') else None
                    if pos:
                        texts.append({
                            "text": txt,
                            "x": pos.x, "y": pos.y,
                            "layer": layer,
                        })
                    else:
                        texts.append({"text": txt, "x": 0, "y": 0, "layer": layer})
            except Exception:
                pass

        # -----------------------------------------------------------
        # Dimensions
        # -----------------------------------------------------------
        elif etype == "DIMENSION":
            try:
                val = entity.dxf.actual_measurement
                if val and 0.01 < abs(val) < 200000:
                    dimensions.append(round(abs(val), 2))
            except Exception:
                pass

    if len(walls_raw) < 4:
        logger.info(f"DXF has only {len(walls_raw)} wall segments — too few for room detection")
        return None

    # Detect unit scale
    scale = _detect_scale(walls_raw, dimensions)

    logger.info(f"DXF parsed: {len(walls_raw)} walls, {len(texts)} texts, "
                f"{len(doors_raw)} doors, {len(windows_raw)} windows, scale={scale}")

    # Build room graph from walls (with multi-level, apartments, openings)
    building = _walls_to_building(walls_raw, texts, dimensions, scale, "dxf",
                                  doors_raw=doors_raw, windows_raw=windows_raw)

    return building


# ══════════════════════════════════════════════════════════════
# DWG PARSER (converts to DXF then parses)
# ══════════════════════════════════════════════════════════════

def _parse_dwg(path: str) -> Optional[Building]:
    """Parse DWG by converting to DXF first."""
    try:
        from dwg_converter import convert_to_dxf
    except ImportError:
        logger.warning("dwg_converter not available")
        return None

    try:
        dxf_path = convert_to_dxf(path)
        if dxf_path and os.path.exists(dxf_path):
            building = _parse_dxf(dxf_path)
            if building:
                building.source_format = "dwg_converted"
                return building
    except Exception as e:
        logger.warning(f"DWG conversion failed: {e}")

    # Fallback: try APS Model Derivative
    try:
        from aps_parser_v2 import parser_dwg_aps
        aps_result = parser_dwg_aps(path)
        if aps_result.get("ok"):
            dm = aps_result.get("donnees_moteur", {})
            building = Building.from_params_dict(dm)
            building.source_format = "dwg_aps"
            building.parse_confidence = 0.5
            return building
    except Exception as e:
        logger.warning(f"APS parsing also failed: {e}")

    return None


# ══════════════════════════════════════════════════════════════
# PDF PARSER (Claude Vision)
# ══════════════════════════════════════════════════════════════

VISION_PROMPT = """Tu es un expert BIM. Analyse ce plan architectural et extrais la structure du bâtiment.

Réponds UNIQUEMENT avec un JSON valide (sans markdown) de cette forme:
{
  "nom": "nom du projet",
  "ville": "ville",
  "nb_niveaux": entier,
  "hauteur_etage_m": float,
  "rooms": [
    {
      "name": "Séjour",
      "type": "sejour",
      "x_min": float_m, "y_min": float_m,
      "x_max": float_m, "y_max": float_m
    }
  ],
  "axes_x": [0.0, 6.0, 12.0, 18.0],
  "axes_y": [0.0, 4.5, 9.0, 13.5],
  "axis_labels_x": ["7", "8", "9", "10"],
  "axis_labels_y": ["A", "B", "C", "D"]
}

Types de pièces valides: sejour, chambre, cuisine, sdb, wc, couloir, foyer, dressing, bureau, buanderie, rangement, balcon, terrasse, local_tech, hall, escalier, ascenseur

Dimensions en mètres. Si tu ne peux pas déterminer les dimensions exactes, estime à partir de l'échelle.
Si une valeur est inconnue, mets null."""


def _parse_pdf(path: str, client=None) -> Optional[Building]:
    """Parse PDF using Claude Vision to extract room layout."""
    if client is None:
        try:
            import anthropic
            key = os.getenv("ANTHROPIC_API_KEY")
            if not key:
                return None
            client = anthropic.Anthropic(api_key=key)
        except ImportError:
            return None

    try:
        import fitz
    except ImportError:
        logger.warning("pymupdf not installed")
        return None

    try:
        doc = fitz.open(path)
    except Exception as e:
        logger.warning(f"Cannot open PDF: {e}")
        return None

    try:
        if len(doc) == 0:
            return None

        # Process up to first 5 pages (architectural plans)
        results = []
        for page_idx in range(min(len(doc), 5)):
            page = doc[page_idx]

            # Try vector text first
            text = page.get_text().strip()

            # Always try vision for plan extraction
            try:
                mat = fitz.Matrix(150 / 72, 150 / 72)  # Higher res for room detection
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img_bytes = pix.tobytes("jpeg")
                if len(img_bytes) > 4_000_000:
                    mat = fitz.Matrix(100 / 72, 100 / 72)
                    pix = page.get_pixmap(matrix=mat, alpha=False)
                    img_bytes = pix.tobytes("jpeg")
                img_b64 = base64.standard_b64encode(img_bytes).decode()

                msg = client.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=2000,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {
                                "type": "base64", "media_type": "image/jpeg",
                                "data": img_b64}},
                            {"type": "text", "text": VISION_PROMPT},
                        ]
                    }]
                )
                raw = msg.content[0].text.strip()
                raw = re.sub(r'^```json\s*', '', raw)
                raw = re.sub(r'^```\s*', '', raw)
                raw = re.sub(r'\s*```$', '', raw)
                data = json.loads(raw)
                if data.get("rooms") and len(data["rooms"]) > 0:
                    results.append(data)
                    break  # Got good data from this page
            except Exception as e:
                logger.info(f"Vision extraction failed on page {page_idx}: {e}")
                continue

        if not results:
            # Fallback: extract basic params from text
            text_all = "\n".join(p.get_text() for p in doc)
            if len(text_all.strip()) > 80:
                return _parse_text_to_building(text_all, client)
            return None

        # Build Building from vision results
        data = results[0]  # Best result
        building = _vision_data_to_building(data)
        building.source_format = "pdf_vision"
        building.parse_confidence = 0.7
        return building

    finally:
        doc.close()


def _parse_text_to_building(text: str, client) -> Optional[Building]:
    """Fallback: extract basic parameters from text and create parametric building."""
    from parse_plans import PROMPT as BASIC_PROMPT, _clean, _defaults

    try:
        msg = client.messages.create(
            model=CLAUDE_MODEL, max_tokens=600,
            messages=[{"role": "user",
                       "content": f"{BASIC_PROMPT}\n\nCONTENU:\n{text[:8000]}"}]
        )
        params = _clean(msg.content[0].text)
        params = _defaults(params)
        building = Building.from_params_dict(params)
        building.source_format = "pdf_text"
        building.parse_confidence = 0.4
        return building
    except Exception as e:
        logger.warning(f"Text-based parsing failed: {e}")
        return None


def _vision_data_to_building(data: Dict) -> Building:
    """Convert Claude Vision output to a Building object."""
    b = Building(
        name=data.get("nom", "Projet"),
        city=data.get("ville", "Dakar"),
    )

    nb_niveaux = data.get("nb_niveaux") or 1
    he = data.get("hauteur_etage_m") or 3.0
    rooms_data = data.get("rooms", [])
    axes_x = data.get("axes_x") or []
    axes_y = data.get("axes_y") or []

    for idx in range(nb_niveaux):
        name = "RDC" if idx == 0 else f"Étage {idx}"
        lvl = b.add_level(name=name, index=idx, height_m=he)
        lvl.axes_x = [float(x) for x in axes_x] if axes_x else []
        lvl.axes_y = [float(y) for y in axes_y] if axes_y else []
        lvl.axis_labels_x = data.get("axis_labels_x", [])
        lvl.axis_labels_y = data.get("axis_labels_y", [])

        # Create rooms from vision data
        for rd in rooms_data:
            room_name = rd.get("name", "Pièce")
            room_type_str = rd.get("type", "inconnu")
            rt = classify_room_type(room_type_str)

            x0 = float(rd.get("x_min", 0))
            y0 = float(rd.get("y_min", 0))
            x1 = float(rd.get("x_max", x0 + 4))
            y1 = float(rd.get("y_max", y0 + 3))

            polygon = [Point(x0, y0), Point(x1, y0),
                       Point(x1, y1), Point(x0, y1)]

            room = Room(
                type=rt,
                name=room_name,
                label=rd.get("label", ""),
                level_id=lvl.id,
                polygon=polygon,
            )

            # Create walls
            _create_room_walls(room, x0, y0, x1, y1, lvl, rooms_data)
            lvl.rooms.append(room)

    return b


def _create_room_walls(room: Room, x0: float, y0: float, x1: float, y1: float,
                        level: Level, all_rooms_data: list):
    """Create walls for a room from its bounding box."""
    walls = []
    segments = [
        (Point(x0, y0), Point(x1, y0)),  # Bottom
        (Point(x1, y0), Point(x1, y1)),  # Right
        (Point(x1, y1), Point(x0, y1)),  # Top
        (Point(x0, y1), Point(x0, y0)),  # Left
    ]

    for start, end in segments:
        # Determine if this is a facade wall (at building boundary)
        is_exterior = _is_boundary_wall(start, end, all_rooms_data)
        wall = Wall(
            start=start, end=end,
            thickness_m=0.20 if is_exterior else 0.10,
            type=WallType.FACADE if is_exterior else WallType.CLOISON,
            room_left_id=room.id,
        )

        # Add door on non-exterior walls
        if not is_exterior and wall.length_m > 1.2:
            wall.openings.append(Opening(
                type=OpeningType.DOOR,
                width_m=0.9, height_m=2.1,
                offset_along_wall_m=wall.length_m / 2,
            ))

        # Add window on exterior walls for habitable rooms
        if is_exterior and wall.length_m > 1.5 and room.type in (
            RoomType.SEJOUR, RoomType.CHAMBRE, RoomType.BUREAU, RoomType.CUISINE):
            wall.openings.append(Opening(
                type=OpeningType.WINDOW,
                width_m=min(1.4, wall.length_m - 0.6),
                height_m=1.2, sill_height_m=1.0,
                offset_along_wall_m=wall.length_m / 2,
            ))

        walls.append(wall)
        level.walls.append(wall)

    room.wall_ids = [w.id for w in walls]


def _is_boundary_wall(start: Point, end: Point, all_rooms: list) -> bool:
    """Check if a wall segment is on the building boundary."""
    mid = start.midpoint(end)
    # A wall is exterior if no other room shares this edge
    tolerance = 0.1
    shared = 0
    for rd in all_rooms:
        x0 = float(rd.get("x_min", 0))
        y0 = float(rd.get("y_min", 0))
        x1 = float(rd.get("x_max", 0))
        y1 = float(rd.get("y_max", 0))
        edges = [(x0, y0, x1, y0), (x1, y0, x1, y1),
                 (x1, y1, x0, y1), (x0, y1, x0, y0)]
        for ex0, ey0, ex1, ey1 in edges:
            emid_x = (ex0 + ex1) / 2
            emid_y = (ey0 + ey1) / 2
            if abs(emid_x - mid.x) < tolerance and abs(emid_y - mid.y) < tolerance:
                shared += 1
    return shared <= 1  # Only this room touches this edge


# ══════════════════════════════════════════════════════════════
# FLOOD-FILL POLYGON ROOM DETECTION  (Improvement #1)
# ══════════════════════════════════════════════════════════════

def _rasterize_walls(walls_m: list, resolution: float = 0.05
                     ) -> Tuple[list, float, float, float]:
    """Rasterize wall segments onto a 2D boolean grid.

    Returns:
        (grid, x_min, y_min, resolution)
        grid[row][col] == True means the cell is blocked (wall).
    """
    if not walls_m:
        return [], 0.0, 0.0, resolution

    # Bounding box of all walls with 1m padding
    all_x = []
    all_y = []
    for p1, p2, _ in walls_m:
        all_x.extend([p1.x, p2.x])
        all_y.extend([p1.y, p2.y])

    x_min = min(all_x) - 1.0
    y_min = min(all_y) - 1.0
    x_max = max(all_x) + 1.0
    y_max = max(all_y) + 1.0

    span_x = x_max - x_min
    span_y = y_max - y_min

    # Auto-increase resolution for very large plans to keep grid manageable
    if max(span_x, span_y) > 100.0:
        resolution = 0.10
    elif max(span_x, span_y) > 200.0:
        resolution = 0.20

    cols = int(math.ceil(span_x / resolution)) + 1
    rows = int(math.ceil(span_y / resolution)) + 1

    # Safety cap: avoid absurdly large grids
    if rows * cols > 20_000_000:
        resolution = max(resolution, math.sqrt(span_x * span_y / 5_000_000))
        cols = int(math.ceil(span_x / resolution)) + 1
        rows = int(math.ceil(span_y / resolution)) + 1

    grid = [[False] * cols for _ in range(rows)]

    # Rasterize each wall segment using Bresenham-like stepping
    half_thick = max(1, int(0.15 / resolution))  # wall rendering thickness in cells

    for p1, p2, _ in walls_m:
        c1 = int((p1.x - x_min) / resolution)
        r1 = int((p1.y - y_min) / resolution)
        c2 = int((p2.x - x_min) / resolution)
        r2 = int((p2.y - y_min) / resolution)

        # Bresenham line rasterization
        dc = abs(c2 - c1)
        dr = abs(r2 - r1)
        sc = 1 if c1 < c2 else -1
        sr = 1 if r1 < r2 else -1
        err = dc - dr
        c, r = c1, r1
        steps = dc + dr + 1

        for _ in range(steps + 1):
            # Paint a small brush around the line to represent wall thickness
            for dr2 in range(-half_thick, half_thick + 1):
                for dc2 in range(-half_thick, half_thick + 1):
                    rr = r + dr2
                    cc = c + dc2
                    if 0 <= rr < rows and 0 <= cc < cols:
                        grid[rr][cc] = True

            if c == c2 and r == r2:
                break
            e2 = 2 * err
            if e2 > -dr:
                err -= dr
                c += sc
            if e2 < dc:
                err += dc
                r += sr

    return grid, x_min, y_min, resolution


def _flood_fill(grid: list, start_row: int, start_col: int,
                rows: int, cols: int) -> set:
    """BFS flood fill from a point. Returns set of (row, col) cells.

    Stops at blocked cells (walls) and grid boundaries.
    """
    if start_row < 0 or start_row >= rows or start_col < 0 or start_col >= cols:
        return set()
    if grid[start_row][start_col]:
        # Starting point is on a wall — nudge to nearest open cell
        for dr in range(-3, 4):
            for dc in range(-3, 4):
                nr, nc = start_row + dr, start_col + dc
                if 0 <= nr < rows and 0 <= nc < cols and not grid[nr][nc]:
                    start_row, start_col = nr, nc
                    break
            else:
                continue
            break
        else:
            return set()

    filled = set()
    queue = deque()
    queue.append((start_row, start_col))
    filled.add((start_row, start_col))

    # Safety limit to prevent unbounded fills (e.g. outside building)
    max_cells = rows * cols // 2

    while queue:
        if len(filled) > max_cells:
            # Probably leaked outside — return empty to skip this room
            return set()
        r, c = queue.popleft()
        for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in filled and not grid[nr][nc]:
                filled.add((nr, nc))
                queue.append((nr, nc))

    return filled


def _boundary_to_polygon(cells: set, x_min: float, y_min: float,
                          resolution: float, walls_m: list) -> List[Point]:
    """Extract boundary of a filled region and simplify to polygon.

    Strategy:
      1. Find boundary cells (cells with at least one non-filled neighbor).
      2. Compute bounding coordinates of boundary cells in world space.
      3. Simplify using Douglas-Peucker.
      4. Snap vertices to nearby wall endpoints.
    """
    if not cells:
        return []

    # Find boundary cells
    boundary_cells = set()
    for r, c in cells:
        for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            if (r + dr, c + dc) not in cells:
                boundary_cells.add((r, c))
                break

    if not boundary_cells:
        return []

    # Convert boundary cells to world-space points and sort them
    # into a contour by tracing the boundary
    boundary_pts = []
    for r, c in boundary_cells:
        wx = x_min + c * resolution
        wy = y_min + r * resolution
        boundary_pts.append((wx, wy))

    if len(boundary_pts) < 3:
        return []

    # Sort into a contour by angle from centroid
    cx = sum(p[0] for p in boundary_pts) / len(boundary_pts)
    cy = sum(p[1] for p in boundary_pts) / len(boundary_pts)
    boundary_pts.sort(key=lambda p: math.atan2(p[1] - cy, p[0] - cx))

    # Subsample to avoid huge polygon: take every Nth point
    max_pts = 200
    if len(boundary_pts) > max_pts:
        step = len(boundary_pts) // max_pts
        boundary_pts = boundary_pts[::step]

    # Douglas-Peucker simplification
    simplified = _douglas_peucker(boundary_pts, tolerance=0.10)

    if len(simplified) < 3:
        # Fall back to bounding box
        xs = [p[0] for p in boundary_pts]
        ys = [p[1] for p in boundary_pts]
        return [Point(min(xs), min(ys)), Point(max(xs), min(ys)),
                Point(max(xs), max(ys)), Point(min(xs), max(ys))]

    # Snap to wall endpoints within 0.15m
    wall_endpoints = []
    for p1, p2, _ in walls_m:
        wall_endpoints.append((p1.x, p1.y))
        wall_endpoints.append((p2.x, p2.y))

    result = []
    snap_dist = 0.15
    for sx, sy in simplified:
        best = (sx, sy)
        best_d = snap_dist
        for wx, wy in wall_endpoints:
            d = math.hypot(sx - wx, sy - wy)
            if d < best_d:
                best_d = d
                best = (wx, wy)
        result.append(Point(best[0], best[1]))

    return result


def _douglas_peucker(points: list, tolerance: float) -> list:
    """Douglas-Peucker polygon simplification on a list of (x, y) tuples."""
    if len(points) <= 2:
        return list(points)

    # Find point with max distance from line between first and last
    start = points[0]
    end = points[-1]
    max_dist = 0.0
    max_idx = 0

    dx = end[0] - start[0]
    dy = end[1] - start[1]
    line_len = math.hypot(dx, dy)

    for i in range(1, len(points) - 1):
        if line_len < 1e-9:
            dist = math.hypot(points[i][0] - start[0], points[i][1] - start[1])
        else:
            # Perpendicular distance
            dist = abs(dy * points[i][0] - dx * points[i][1]
                       + end[0] * start[1] - end[1] * start[0]) / line_len
        if dist > max_dist:
            max_dist = dist
            max_idx = i

    if max_dist > tolerance:
        left = _douglas_peucker(points[:max_idx + 1], tolerance)
        right = _douglas_peucker(points[max_idx:], tolerance)
        return left[:-1] + right
    else:
        return [start, end]


def _detect_room_polygons(walls_m: list, texts: list,
                           scale: float) -> List[Dict]:
    """Detect rooms as true polygons using flood-fill on rasterized wall grid.

    For each room text label, flood-fills from the label position to find the
    enclosed area, then extracts the boundary polygon.
    """
    # Find room-type text labels
    room_texts = []
    for t in texts:
        rt = classify_room_type(t["text"])
        if rt != RoomType.INCONNU:
            room_texts.append({
                "text": t["text"],
                "type": rt,
                "x": t["x"] * scale,
                "y": t["y"] * scale,
            })

    if not room_texts:
        return []

    # Determine grid resolution
    resolution = 0.05
    all_x = [p1.x for p1, _, _ in walls_m] + [p2.x for _, p2, _ in walls_m]
    all_y = [p1.y for p1, _, _ in walls_m] + [p2.y for _, p2, _ in walls_m]
    span = max(max(all_x) - min(all_x), max(all_y) - min(all_y)) if all_x else 0
    if span > 100.0:
        resolution = 0.10

    grid, x_min, y_min, resolution = _rasterize_walls(walls_m, resolution)
    if not grid:
        return []

    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0

    # Track which cells are already assigned to a room
    assigned = set()

    rooms = []
    for rt in room_texts:
        # Convert world coordinate to grid cell
        col = int((rt["x"] - x_min) / resolution)
        row = int((rt["y"] - y_min) / resolution)

        # Skip if already assigned
        if (row, col) in assigned:
            continue

        filled = _flood_fill(grid, row, col, rows, cols)
        if not filled:
            continue

        # Skip very small fills (< 2 m2 worth of cells)
        area_cells = len(filled)
        area_m2 = area_cells * resolution * resolution
        if area_m2 < 1.5:
            continue

        # Check overlap with already-assigned cells
        overlap = filled & assigned
        if len(overlap) > len(filled) * 0.5:
            continue  # >50% overlap — skip

        assigned |= filled

        # Extract polygon boundary
        polygon = _boundary_to_polygon(filled, x_min, y_min, resolution, walls_m)
        if len(polygon) < 3:
            # Fallback: compute bounding box from filled cells
            rs = [r for r, c in filled]
            cs = [c for r, c in filled]
            bx0 = x_min + min(cs) * resolution
            by0 = y_min + min(rs) * resolution
            bx1 = x_min + max(cs) * resolution
            by1 = y_min + max(rs) * resolution
            polygon = [Point(bx0, by0), Point(bx1, by0),
                       Point(bx1, by1), Point(bx0, by1)]

        rooms.append({
            "name": rt["text"],
            "type": rt["type"],
            "polygon": polygon,
            "area_m2": area_m2,
        })

    return rooms


# ══════════════════════════════════════════════════════════════
# MULTI-LEVEL DETECTION  (Improvement #2)
# ══════════════════════════════════════════════════════════════

def _detect_levels_from_texts(texts: list) -> List[Dict]:
    """Detect floor/level definitions from text labels.

    Returns a list of dicts:
        [{"name": "RDC", "index": 0, "region_y": (y_min, y_max)}, ...]

    If typical floors are found (e.g. "ETAGES 1 à 7"), they are expanded.
    """
    level_hits = []

    for t in texts:
        txt = t["text"].strip()

        # Check for typical floor range (e.g. "ETAGES 1 à 7")
        m_range = _TYPICAL_FLOOR_RE.search(txt)
        if m_range:
            lo = int(m_range.group(1))
            hi = int(m_range.group(2))
            for idx in range(lo, hi + 1):
                level_hits.append({
                    "name": f"Étage {idx}",
                    "index": idx,
                    "y": t["y"],
                    "is_typical": True,
                })
            continue

        m = _LEVEL_RE.search(txt)
        if m:
            matched = m.group(0).upper().strip()
            index = _level_name_to_index(matched)
            name = _normalize_level_name(matched, index)
            level_hits.append({
                "name": name,
                "index": index,
                "y": t["y"],
                "is_typical": False,
            })

    if not level_hits:
        return []

    # Deduplicate by index
    seen = {}
    for lh in level_hits:
        idx = lh["index"]
        if idx not in seen:
            seen[idx] = lh

    result = sorted(seen.values(), key=lambda l: l["index"])
    return result


def _level_name_to_index(name_upper: str) -> int:
    """Convert a level name to a numeric index (RDC=0, SS=-1, etc.)."""
    name_upper = name_upper.strip()
    if name_upper in ("RDC", "REZ"):
        return 0
    if "TERRASSE" in name_upper:
        return 99  # Will be renumbered later
    m = re.search(r'(\d+)', name_upper)
    num = int(m.group(1)) if m else 1
    if "SOUS" in name_upper or name_upper.startswith("SS"):
        return -num
    return num


def _normalize_level_name(matched: str, index: int) -> str:
    """Produce a clean display name for a level."""
    matched = matched.strip()
    if index == 0:
        return "RDC"
    if index < 0:
        return f"Sous-sol {abs(index)}"
    if "TERRASSE" in matched.upper():
        return "Terrasse"
    return f"Étage {index}"


# ══════════════════════════════════════════════════════════════
# APARTMENT GROUPING  (Improvement #3)
# ══════════════════════════════════════════════════════════════

def _group_rooms_into_apartments(rooms_data: List[Dict], texts: list,
                                  scale: float) -> List[Dict]:
    """Detect apartment labels and prefix room names with apartment ID.

    Looks for text labels matching apartment patterns (APPART A, TYPE F3, etc.),
    then assigns rooms to the nearest apartment label by spatial proximity.

    Modifies rooms_data in-place (adds 'apartment' key and prefixes name).
    Returns rooms_data for chaining.
    """
    # Find apartment labels
    apt_labels = []
    for t in texts:
        m = _APARTMENT_RE.search(t["text"])
        if m:
            apt_id = m.group(1).upper()
            apt_labels.append({
                "id": apt_id,
                "text": t["text"],
                "x": t["x"] * scale,
                "y": t["y"] * scale,
            })

    if not apt_labels:
        return rooms_data

    # Assign each room to the nearest apartment label
    for rd in rooms_data:
        # Compute room centroid from polygon
        poly = rd.get("polygon", [])
        if not poly:
            continue
        cx = sum(p.x for p in poly) / len(poly)
        cy = sum(p.y for p in poly) / len(poly)

        best_apt = None
        best_dist = float('inf')
        for apt in apt_labels:
            d = math.hypot(cx - apt["x"], cy - apt["y"])
            if d < best_dist:
                best_dist = d
                best_apt = apt

        if best_apt and best_dist < 30.0:  # Within 30m — reasonable for an apartment
            apt_id = best_apt["id"]
            rd["apartment"] = apt_id
            rd["name"] = f"{apt_id}-{rd['name']}"
            rd["label"] = apt_id

    return rooms_data


# ══════════════════════════════════════════════════════════════
# DOOR/WINDOW MATCHING TO WALLS  (Improvement #4)
# ══════════════════════════════════════════════════════════════

def _match_openings_to_walls(doors_raw: list, windows_raw: list,
                              wall_objects: List[Wall], scale: float):
    """Match detected doors/windows to nearest wall and add Opening objects.

    doors_raw:   [(Point_raw, width_estimate, layer), ...]
    windows_raw: [(Point_raw, width_estimate, layer), ...]
    wall_objects: list of Wall instances already created.

    Modifies wall_objects in-place by appending Opening to wall.openings.
    """
    if not wall_objects:
        return

    def _nearest_wall(pt: Point, walls: List[Wall], max_dist: float = 1.0
                      ) -> Optional[Tuple[Wall, float]]:
        """Find the wall closest to a point. Returns (wall, offset_along_wall)."""
        best_wall = None
        best_dist = max_dist
        best_offset = 0.0

        for w in walls:
            # Project point onto wall line segment
            wx = w.end.x - w.start.x
            wy = w.end.y - w.start.y
            wlen = w.length_m
            if wlen < 0.1:
                continue
            # Parameterize: t in [0, 1]
            t = ((pt.x - w.start.x) * wx + (pt.y - w.start.y) * wy) / (wlen * wlen)
            t = max(0.0, min(1.0, t))
            proj_x = w.start.x + t * wx
            proj_y = w.start.y + t * wy
            dist = math.hypot(pt.x - proj_x, pt.y - proj_y)
            if dist < best_dist:
                best_dist = dist
                best_wall = w
                best_offset = t * wlen

        if best_wall is not None:
            return best_wall, best_offset
        return None

    # Process doors
    for pos_raw, width, layer in doors_raw:
        pt = Point(pos_raw.x * scale, pos_raw.y * scale)
        w_scaled = width * scale if width * scale > 0.3 else 0.9
        # Clamp to reasonable door width
        w_scaled = min(w_scaled, 2.0)

        result = _nearest_wall(pt, wall_objects, max_dist=0.5)
        if result:
            wall, offset = result
            # Avoid duplicate openings at same offset
            duplicate = False
            for existing in wall.openings:
                if abs(existing.offset_along_wall_m - offset) < 0.3:
                    duplicate = True
                    break
            if not duplicate:
                wall.openings.append(Opening(
                    type=OpeningType.DOOR,
                    width_m=round(w_scaled, 2),
                    height_m=2.1,
                    offset_along_wall_m=round(offset, 2),
                ))

    # Process windows
    for pos_raw, width, layer in windows_raw:
        pt = Point(pos_raw.x * scale, pos_raw.y * scale)
        w_scaled = width * scale if width * scale > 0.3 else 1.2
        w_scaled = min(w_scaled, 3.0)

        result = _nearest_wall(pt, wall_objects, max_dist=0.5)
        if result:
            wall, offset = result
            duplicate = False
            for existing in wall.openings:
                if abs(existing.offset_along_wall_m - offset) < 0.3:
                    duplicate = True
                    break
            if not duplicate:
                wall.openings.append(Opening(
                    type=OpeningType.WINDOW,
                    width_m=round(w_scaled, 2),
                    height_m=1.2,
                    sill_height_m=1.0,
                    offset_along_wall_m=round(offset, 2),
                ))


# ══════════════════════════════════════════════════════════════
# WALL-TO-ROOM GRAPH CONSTRUCTION (updated for all 4 improvements)
# ══════════════════════════════════════════════════════════════

def _detect_scale(walls_raw: list, dimensions: list) -> float:
    """Detect if coordinates are in mm, cm, or m."""
    lengths = [p1.distance_to(p2) for p1, p2, _ in walls_raw if p1.distance_to(p2) > 0.01]
    if not lengths:
        return 1.0
    median = sorted(lengths)[len(lengths) // 2]

    if median > 500:
        return 0.001  # Coordinates in mm → convert to m
    elif median > 50:
        return 0.01   # Coordinates in cm → convert to m
    else:
        return 1.0    # Already in meters


def _walls_to_building(walls_raw: list, texts: list, dimensions: list,
                        scale: float, source: str,
                        doors_raw: Optional[list] = None,
                        windows_raw: Optional[list] = None) -> Optional[Building]:
    """Convert raw wall segments and texts into a Building with rooms.

    This is the core geometry → topology conversion. Supports:
      - Polygon room detection via flood-fill
      - Multi-level detection from text labels
      - Apartment grouping
      - Door/window matching from DXF entities
    """
    doors_raw = doors_raw or []
    windows_raw = windows_raw or []

    # Scale walls to meters
    walls_m = [(Point(p1.x * scale, p1.y * scale),
                Point(p2.x * scale, p2.y * scale), layer)
               for p1, p2, layer in walls_raw]

    # Filter too-short segments (noise)
    walls_m = [(p1, p2, l) for p1, p2, l in walls_m
               if p1.distance_to(p2) > 0.3]

    if len(walls_m) < 4:
        return None

    # Detect axes from wall endpoints
    axes_x, axes_y = _detect_axes(walls_m)

    # --- Improvement #1: polygon room detection via flood-fill ---
    rooms_data = _detect_room_polygons(walls_m, texts, scale)

    if not rooms_data:
        # Fallback: create rooms from axis grid
        rooms_data = _rooms_from_axes(axes_x, axes_y, texts, scale)

    # --- Improvement #3: apartment grouping ---
    if rooms_data:
        rooms_data = _group_rooms_into_apartments(rooms_data, texts, scale)

    # Extract project info from texts
    nom = _extract_project_name(texts)
    ville = _extract_city(texts)

    # --- Improvement #2: multi-level detection ---
    levels_def = _detect_levels_from_texts(texts)

    b = Building(
        name=nom or "Projet",
        city=ville or "Dakar",
        source_format=source,
        parse_confidence=0.6 if rooms_data else 0.3,
    )

    if not levels_def:
        # Single level (legacy behavior)
        levels_def = [{"name": "RDC", "index": 0, "is_typical": False}]

    # Create levels and populate with rooms
    for ldef in levels_def:
        lvl = b.add_level(name=ldef["name"], index=ldef["index"])
        lvl.axes_x = axes_x
        lvl.axes_y = axes_y

        for rd in rooms_data:
            room = Room(
                type=rd["type"],
                name=rd["name"],
                label=rd.get("label", ""),
                level_id=lvl.id,
                polygon=list(rd["polygon"]),  # Copy so each level gets its own
            )
            # Create walls from polygon
            wall_objects = []
            for i in range(len(room.polygon)):
                j = (i + 1) % len(room.polygon)
                wall = Wall(
                    start=room.polygon[i],
                    end=room.polygon[j],
                    thickness_m=0.20,
                    type=WallType.FACADE,
                    room_left_id=room.id,
                )
                lvl.walls.append(wall)
                room.wall_ids.append(wall.id)
                wall_objects.append(wall)

            # --- Improvement #4: match DXF openings to these walls ---
            if doors_raw or windows_raw:
                _match_openings_to_walls(doors_raw, windows_raw,
                                         wall_objects, scale)

            lvl.rooms.append(room)

    logger.info(f"Building created: {len(b.levels)} levels, "
                f"{len(b.all_rooms)} total rooms")

    return b


def _detect_axes(walls_m: list) -> Tuple[List[float], List[float]]:
    """Detect structural axes from wall alignment patterns."""
    # Collect X coordinates of vertical wall endpoints
    x_coords = []
    y_coords = []

    for p1, p2, _ in walls_m:
        if abs(p1.x - p2.x) < 0.1:  # Vertical wall
            x_coords.append(round(p1.x, 2))
        if abs(p1.y - p2.y) < 0.1:  # Horizontal wall
            y_coords.append(round(p1.y, 2))

    axes_x = _cluster_coordinates(x_coords, tolerance=0.3)
    axes_y = _cluster_coordinates(y_coords, tolerance=0.3)

    return sorted(axes_x), sorted(axes_y)


def _cluster_coordinates(coords: List[float], tolerance: float = 0.3) -> List[float]:
    """Cluster nearby coordinate values into axis positions."""
    if not coords:
        return []

    from collections import Counter
    rounded = [round(c / tolerance) * tolerance for c in coords]
    counter = Counter(rounded)

    # Keep coordinates that appear multiple times (axis lines)
    threshold = max(2, len(coords) * 0.02)
    axes = [c for c, count in counter.items() if count >= threshold]

    return sorted(set(round(a, 2) for a in axes))


def _rooms_from_axes(axes_x: List[float], axes_y: List[float],
                      texts: list, scale: float) -> List[Dict]:
    """Create rooms from axis grid intersections."""
    if len(axes_x) < 2 or len(axes_y) < 2:
        return []

    rooms = []
    for i in range(len(axes_x) - 1):
        for j in range(len(axes_y) - 1):
            x0, x1 = axes_x[i], axes_x[i + 1]
            y0, y1 = axes_y[j], axes_y[j + 1]
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

            # Find text label near this cell center
            name = f"Pièce {chr(65 + j)}{i + 1}"
            rt = RoomType.INCONNU
            for t in texts:
                tx, ty = t["x"] * scale, t["y"] * scale
                if x0 <= tx <= x1 and y0 <= ty <= y1:
                    candidate_rt = classify_room_type(t["text"])
                    if candidate_rt != RoomType.INCONNU:
                        name = t["text"]
                        rt = candidate_rt
                        break

            rooms.append({
                "name": name,
                "type": rt,
                "polygon": [
                    Point(x0, y0), Point(x1, y0),
                    Point(x1, y1), Point(x0, y1),
                ],
            })

    return rooms


# ══════════════════════════════════════════════════════════════
# TEXT EXTRACTION HELPERS
# ══════════════════════════════════════════════════════════════

def _extract_project_name(texts: list) -> Optional[str]:
    """Try to find project name in text labels."""
    keywords = ["residence", "résidence", "tower", "tour", "villa",
                "immeuble", "building", "projet", "project"]
    for t in texts:
        txt = t["text"].lower()
        if any(k in txt for k in keywords) and len(t["text"]) < 60:
            return t["text"].strip()
    return None


def _extract_city(texts: list) -> Optional[str]:
    """Try to find city name in text labels."""
    cities = ["dakar", "abidjan", "casablanca", "lagos", "accra",
              "ouagadougou", "bamako", "conakry", "niamey", "lome",
              "cotonou", "nouakchott", "freetown", "monrovia"]
    for t in texts:
        for city in cities:
            if city in t["text"].lower():
                return city.capitalize()
    return None
