"""
generate_plans_dxf.py — Professional BIM plan renderer using ezdxf

Generates DXF files with proper CAD blocks, layers, hatching, dimensions,
and a title block. Each sublot × level produces one DXF drawing.
Can also compile all pages into a single multi-page PDF via ezdxf.addons.drawing.

Replaces ReportLab for BIM drawings with real CAD output.

Usage:
    from generate_plans_dxf import render_bim_dxf, compile_bim_pdf
    # Single DXF per level × sublot
    paths = render_bim_dxf(building, output_dir="out/")
    # All-in-one PDF
    pdf_path = compile_bim_pdf(building, "dossier_bim.pdf")
"""
from __future__ import annotations
import os
import math
import logging
import tempfile
from dataclasses import dataclass, field
from typing import Optional

import ezdxf
from ezdxf.math import Vec2
from ezdxf import units as dxf_units
from ezdxf.enums import TextEntityAlignment

from bim_model import (
    Building, Level, Room, Wall, Point,
    EquipmentInstance, NetworkSegment,
    RoomType, WallType, EquipmentType, NetworkType,
)
from mep_blocks import (
    register_all_blocks, setup_layers,
    EQUIP_BLOCK_MAP, EQUIP_LAYER_MAP,
    NETWORK_LAYER_MAP, LAYERS,
)

logger = logging.getLogger("tijan.dxf_renderer")

# ══════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════

# Paper layout — ISO A1 (841 × 594 mm) landscape
PAPER_W_MM = 841.0
PAPER_H_MM = 594.0

# Drawing area margins (mm from paper edge)
MARGIN_LEFT = 30.0
MARGIN_RIGHT = 30.0
MARGIN_TOP = 20.0
MARGIN_BOTTOM = 40.0  # Space for cartouche

# Cartouche dimensions (mm)
CART_W = PAPER_W_MM - MARGIN_LEFT - MARGIN_RIGHT
CART_H = 35.0

# Text heights (in model-space meters)
TEXT_ROOM_LABEL = 0.30
TEXT_ROOM_AREA = 0.20
TEXT_DIM = 0.15
TEXT_EQUIP = 0.10
TEXT_AXIS = 0.25
TEXT_CARTOUCHE = 2.5   # mm in paperspace

# Axis overshoot (meters beyond building bbox)
AXIS_OVERSHOOT = 2.0
AXIS_CIRCLE_R = 0.5

# Network segment line widths by type (in DXF lineweight: hundredths of mm)
NETWORK_LINEWEIGHTS = {
    "P-PIPE-EF": 25, "P-PIPE-EC": 25, "P-PIPE-EU": 25,
    "M-DUCT": 35, "M-EQUIP": 25,
    "E-POWR": 18, "E-LITE": 13, "E-LCCR": 13,
    "F-SPKL": 25, "F-DETECT": 13,
}

# DXF color indices for network types (override layer default if needed)
NETWORK_COLORS = {
    NetworkType.PLU_EF: 5,    # Blue
    NetworkType.PLU_EC: 1,    # Red
    NetworkType.PLU_EU: 3,    # Green
    NetworkType.PLU_EP: 3,    # Green
    NetworkType.HVC_SOUFFLAGE: 30,  # Orange
    NetworkType.HVC_REPRISE: 140,   # Purple
    NetworkType.HVC_VMC: 140,
    NetworkType.HVC_REF: 2,   # Yellow
    NetworkType.HVC_CONDENSAT: 4,   # Cyan
    NetworkType.ELEC_FORT: 6, # Magenta
    NetworkType.ELEC_FAIBLE: 4,     # Cyan
    NetworkType.FIRE_SPK: 1,  # Red
    NetworkType.FIRE_DETECT: 1,
}


# ══════════════════════════════════════════════════════════════
# SUBLOT DEFINITIONS (same structure as generate_plans_bim.py)
# ══════════════════════════════════════════════════════════════

SUBLOTS = [
    {"code": "ARC", "title": "001 ARC — Architecture",
     "eq_types": set(), "net_types": set()},

    {"code": "STR", "title": "200 STR — Coffrage",
     "eq_types": set(), "net_types": set()},

    {"code": "PLU_EF", "title": "410 PLU — Eau Froide",
     "eq_types": {EquipmentType.WC_UNIT, EquipmentType.LAVABO,
                  EquipmentType.DOUCHE, EquipmentType.BAIGNOIRE,
                  EquipmentType.EVIER, EquipmentType.LAVE_LINGE},
     "net_types": {NetworkType.PLU_EF}},

    {"code": "PLU_EC", "title": "410 PLU — Eau Chaude",
     "eq_types": {EquipmentType.CHAUFFE_EAU, EquipmentType.LAVABO,
                  EquipmentType.DOUCHE, EquipmentType.BAIGNOIRE,
                  EquipmentType.EVIER},
     "net_types": {NetworkType.PLU_EC}},

    {"code": "PLU_EU", "title": "410 PLU — Eaux Usées",
     "eq_types": {EquipmentType.WC_UNIT, EquipmentType.LAVABO,
                  EquipmentType.DOUCHE, EquipmentType.BAIGNOIRE,
                  EquipmentType.EVIER, EquipmentType.LAVE_LINGE},
     "net_types": {NetworkType.PLU_EU, NetworkType.PLU_EP}},

    {"code": "HVC_CLIM", "title": "413 HVC — Climatisation",
     "eq_types": {EquipmentType.CLIMATISEUR},
     "net_types": {NetworkType.HVC_REF, NetworkType.HVC_CONDENSAT,
                   NetworkType.HVC_SOUFFLAGE, NetworkType.HVC_REPRISE}},

    {"code": "HVC_VMC", "title": "413 HVC — Ventilation",
     "eq_types": {EquipmentType.BOUCHE_VMC, EquipmentType.HOTTE},
     "net_types": {NetworkType.HVC_VMC}},

    {"code": "FIF_SPK", "title": "400 FIF — Extinction",
     "eq_types": {EquipmentType.SPRINKLER, EquipmentType.RIA},
     "net_types": {NetworkType.FIRE_SPK}},

    {"code": "FIF_DET", "title": "400 FIF — Détection",
     "eq_types": {EquipmentType.DETECTEUR_FUMEE, EquipmentType.DETECTEUR_CHALEUR},
     "net_types": {NetworkType.FIRE_DETECT}},

    {"code": "HCU_ECL", "title": "510 HCU — Éclairage",
     "eq_types": {EquipmentType.LUMINAIRE, EquipmentType.APPLIQUE,
                  EquipmentType.INTERRUPTEUR},
     "net_types": {NetworkType.ELEC_FORT}},

    {"code": "HCU_PC", "title": "510 HCU — Prises de Courant",
     "eq_types": {EquipmentType.PRISE, EquipmentType.PRISE_PLAN_TRAVAIL,
                  EquipmentType.PRISE_ETANCHE, EquipmentType.TABLEAU_ELEC},
     "net_types": {NetworkType.ELEC_FORT}},

    {"code": "LCU", "title": "520 LCU — Courants Faibles",
     "eq_types": {EquipmentType.PRISE_RJ45, EquipmentType.PRISE_TV},
     "net_types": {NetworkType.ELEC_FAIBLE}},

    {"code": "SYN", "title": "001 SYN — Synthèse",
     "eq_types": set(), "net_types": set()},
]


def _has_content(building: Building, sublot: dict) -> bool:
    """Check if this sublot has any equipment or networks in the building."""
    code = sublot["code"]
    if code in ("ARC", "STR", "SYN"):
        return True
    for lvl in building.levels:
        for room in lvl.rooms:
            for eq in room.equipment:
                if eq.type in sublot["eq_types"]:
                    return True
            for seg in room.network_segments:
                if seg.type in sublot["net_types"]:
                    return True
        for seg in lvl.network_segments:
            if seg.type in sublot["net_types"]:
                return True
    return False


# ══════════════════════════════════════════════════════════════
# DXF RENDERING ENGINE
# ══════════════════════════════════════════════════════════════

def _level_bbox(level: Level) -> tuple:
    """Get bounding box of level geometry. Returns (xmin, ymin, xmax, ymax)."""
    xs, ys = [], []
    for wall in level.walls:
        xs.extend([wall.start.x, wall.end.x])
        ys.extend([wall.start.y, wall.end.y])
    for room in level.rooms:
        if room.polygon:
            for pt in room.polygon:
                xs.append(pt.x)
                ys.append(pt.y)
    if not xs:
        return 0, 0, 28, 50  # fallback
    return min(xs), min(ys), max(xs), max(ys)


def _draw_walls(msp, level: Level, is_structure: bool = False):
    """Draw walls as polylines with thickness."""
    for wall in level.walls:
        layer = "A-WALL"
        if wall.type == WallType.FACADE:
            layer = "A-WALL"
        elif wall.type == WallType.PORTEUR:
            layer = "A-WALL" if not is_structure else "A-WALL"
        elif wall.type == WallType.CLOISON:
            layer = "A-WALL-INT"

        # Draw wall as a thick line (using lwpolyline with width)
        thickness = wall.thickness_m
        dx = wall.end.x - wall.start.x
        dy = wall.end.y - wall.start.y
        length = math.sqrt(dx*dx + dy*dy)
        if length < 0.01:
            continue

        # Perpendicular offset for wall thickness
        nx = -dy / length * thickness / 2
        ny = dx / length * thickness / 2

        # Wall as filled rectangle (4-point polyline)
        pts = [
            (wall.start.x + nx, wall.start.y + ny),
            (wall.end.x + nx, wall.end.y + ny),
            (wall.end.x - nx, wall.end.y - ny),
            (wall.start.x - nx, wall.start.y - ny),
        ]
        poly = msp.add_lwpolyline(pts, close=True,
                                   dxfattribs={"layer": layer})

        # For facade walls, add hatch fill
        if wall.type in (WallType.FACADE, WallType.PORTEUR):
            try:
                hatch = msp.add_hatch(color=8, dxfattribs={"layer": "A-HATCH"})
                hatch.paths.add_polyline_path(
                    [(p[0], p[1]) for p in pts] + [pts[0]], is_closed=True)
                hatch.set_pattern_fill("ANSI31", scale=0.05)
            except Exception:
                pass  # Hatch may fail for very small walls


def _draw_room_labels(msp, level: Level):
    """Add room labels with area at centroid."""
    for room in level.rooms:
        if not room.polygon or len(room.polygon) < 3:
            continue
        # Centroid
        cx = sum(p.x for p in room.polygon) / len(room.polygon)
        cy = sum(p.y for p in room.polygon) / len(room.polygon)

        # Room name
        label = room.label or room.name or str(room.type.value)
        # Truncate long labels
        if len(label) > 25:
            label = label[:22] + "..."

        txt = msp.add_text(label, height=TEXT_ROOM_LABEL,
                           dxfattribs={"layer": "A-TEXT"})
        txt.set_placement((cx, cy), align=TextEntityAlignment.MIDDLE_CENTER)

        # Area
        area = getattr(room, "_area_m2", 0)
        if area <= 0 and room.polygon and len(room.polygon) >= 3:
            # Shoelace formula
            pts = room.polygon
            n = len(pts)
            a = sum(pts[i].x * pts[(i+1)%n].y - pts[(i+1)%n].x * pts[i].y
                    for i in range(n))
            area = abs(a) / 2

        if area > 0:
            area_text = f"{area:.1f} m²"
            txt = msp.add_text(area_text, height=TEXT_ROOM_AREA,
                               dxfattribs={"layer": "A-TEXT"})
            txt.set_placement(
                (cx, cy - TEXT_ROOM_LABEL * 1.5),
                align=TextEntityAlignment.MIDDLE_CENTER)


def _draw_axes(msp, level: Level, bbox: tuple):
    """Draw structural grid axes."""
    xmin, ymin, xmax, ymax = bbox
    ovr = AXIS_OVERSHOOT

    # X axes (vertical lines)
    for i, x in enumerate(level.axes_x or []):
        label = (level.axis_labels_x or [])[i] if i < len(level.axis_labels_x or []) else str(i+1)
        # Line
        msp.add_line((x, ymin - ovr), (x, ymax + ovr),
                     dxfattribs={"layer": "S-GRID", "linetype": "CENTER"})
        # Circle + label at bottom
        msp.add_circle((x, ymin - ovr - AXIS_CIRCLE_R), AXIS_CIRCLE_R,
                       dxfattribs={"layer": "S-GRID"})
        txt = msp.add_text(label, height=TEXT_AXIS,
                           dxfattribs={"layer": "S-GRID"})
        txt.set_placement(
            (x, ymin - ovr - AXIS_CIRCLE_R),
            align=TextEntityAlignment.MIDDLE_CENTER)

    # Y axes (horizontal lines)
    for i, y in enumerate(level.axes_y or []):
        label = (level.axis_labels_y or [])[i] if i < len(level.axis_labels_y or []) else chr(65+i)
        msp.add_line((xmin - ovr, y), (xmax + ovr, y),
                     dxfattribs={"layer": "S-GRID", "linetype": "CENTER"})
        msp.add_circle((xmin - ovr - AXIS_CIRCLE_R, y), AXIS_CIRCLE_R,
                       dxfattribs={"layer": "S-GRID"})
        txt = msp.add_text(label, height=TEXT_AXIS,
                           dxfattribs={"layer": "S-GRID"})
        txt.set_placement(
            (xmin - ovr - AXIS_CIRCLE_R, y),
            align=TextEntityAlignment.MIDDLE_CENTER)


def _draw_dimensions(msp, level: Level, bbox: tuple):
    """Add dimension annotations along axes."""
    xmin, ymin, xmax, ymax = bbox
    dim_offset = AXIS_OVERSHOOT + AXIS_CIRCLE_R + 1.0

    # Horizontal dimensions (along bottom)
    axes_x = level.axes_x or []
    for i in range(len(axes_x) - 1):
        x1, x2 = axes_x[i], axes_x[i+1]
        try:
            dim = msp.add_linear_dim(
                base=(x1, ymin - dim_offset - 0.5),
                p1=(x1, ymin - dim_offset),
                p2=(x2, ymin - dim_offset),
                dimstyle="EZDXF",
                dxfattribs={"layer": "S-DIM"},
            )
            dim.render()
        except Exception:
            # Fallback: manual dimension text
            mid_x = (x1 + x2) / 2
            dist = x2 - x1
            txt = msp.add_text(f"{dist:.2f}", height=TEXT_DIM,
                               dxfattribs={"layer": "S-DIM"})
            txt.set_placement(
                (mid_x, ymin - dim_offset),
                align=TextEntityAlignment.MIDDLE_CENTER)

    # Vertical dimensions (along left side)
    axes_y = level.axes_y or []
    for i in range(len(axes_y) - 1):
        y1, y2 = axes_y[i], axes_y[i+1]
        try:
            dim = msp.add_linear_dim(
                base=(xmin - dim_offset - 0.5, y1),
                p1=(xmin - dim_offset, y1),
                p2=(xmin - dim_offset, y2),
                angle=90,
                dimstyle="EZDXF",
                dxfattribs={"layer": "S-DIM"},
            )
            dim.render()
        except Exception:
            mid_y = (y1 + y2) / 2
            dist = y2 - y1
            txt = msp.add_text(f"{dist:.2f}", height=TEXT_DIM,
                               dxfattribs={"layer": "S-DIM"})
            txt.set_placement(
                (xmin - dim_offset, mid_y),
                align=TextEntityAlignment.MIDDLE_CENTER)


def _draw_equipment(msp, level: Level, eq_filter: set):
    """Insert equipment block references at correct positions."""
    for room in level.rooms:
        for eq in room.equipment:
            if eq_filter and eq.type not in eq_filter:
                continue

            block_name = EQUIP_BLOCK_MAP.get(eq.type)
            layer = EQUIP_LAYER_MAP.get(eq.type, "A-TEXT")

            if not eq.position:
                continue

            x, y = eq.position.x, eq.position.y

            if block_name:
                # Insert as block reference
                try:
                    msp.add_blockref(
                        block_name,
                        insert=(x, y),
                        dxfattribs={"layer": layer},
                    )
                except Exception as exc:
                    logger.debug("Block %s insert failed: %s", block_name, exc)
                    # Fallback: circle marker
                    msp.add_circle((x, y), 0.15,
                                   dxfattribs={"layer": layer})
            else:
                # No block defined — circle + label
                msp.add_circle((x, y), 0.12,
                               dxfattribs={"layer": layer})
                if eq.label:
                    msp.add_text(eq.label, height=TEXT_EQUIP,
                                 dxfattribs={"layer": layer,
                                             "insert": (x + 0.15, y)})


def _draw_networks(msp, level: Level, net_filter: set, rooms_too: bool = True):
    """Draw network segments as lines on trade-specific layers."""
    segments = list(level.network_segments)
    if rooms_too:
        for room in level.rooms:
            segments.extend(room.network_segments)

    for seg in segments:
        if net_filter and seg.type not in net_filter:
            continue

        layer = NETWORK_LAYER_MAP.get(seg.type, "A-TEXT")
        color = NETWORK_COLORS.get(seg.type, 256)  # 256 = bylayer
        lw = NETWORK_LINEWEIGHTS.get(layer, 18)

        if not seg.start or not seg.end:
            continue

        attribs = {"layer": layer, "lineweight": lw}
        if color != 256:
            attribs["color"] = color

        msp.add_line(
            (seg.start.x, seg.start.y),
            (seg.end.x, seg.end.y),
            dxfattribs=attribs,
        )

        # Diameter label at midpoint for pipes > 20mm
        if seg.diameter_mm and seg.diameter_mm > 20:
            mx = (seg.start.x + seg.end.x) / 2
            my = (seg.start.y + seg.end.y) / 2
            msp.add_text(
                f"Ø{seg.diameter_mm:.0f}",
                height=TEXT_EQUIP,
                dxfattribs={"layer": layer, "insert": (mx, my + 0.08)},
            )


def _draw_cartouche(msp, bbox: tuple, building: Building,
                    level: Level, sublot: dict, page_num: int = 0):
    """Draw a professional title block (cartouche) below the plan."""
    xmin, ymin, xmax, ymax = bbox
    # Place cartouche below the axes
    cart_y = ymin - AXIS_OVERSHOOT - AXIS_CIRCLE_R - 3.0
    cart_x = xmin - AXIS_OVERSHOOT
    cart_w = (xmax - xmin) + 2 * AXIS_OVERSHOOT
    cart_h = 2.5  # meters in model space

    # Outer border
    msp.add_lwpolyline(
        [(cart_x, cart_y), (cart_x + cart_w, cart_y),
         (cart_x + cart_w, cart_y - cart_h),
         (cart_x, cart_y - cart_h)],
        close=True,
        dxfattribs={"layer": "G-CART", "lineweight": 50},
    )

    # Vertical dividers
    col1 = cart_x + cart_w * 0.35
    col2 = cart_x + cart_w * 0.65
    msp.add_line((col1, cart_y), (col1, cart_y - cart_h),
                 dxfattribs={"layer": "G-CART"})
    msp.add_line((col2, cart_y), (col2, cart_y - cart_h),
                 dxfattribs={"layer": "G-CART"})

    # Project info (left column)
    text_h = 0.20
    small_h = 0.15
    pad = 0.15

    msp.add_text(building.name or "Projet",
                 height=text_h,
                 dxfattribs={"layer": "G-CART",
                             "insert": (cart_x + pad, cart_y - pad - text_h)})
    msp.add_text(f"{building.city or ''}, {building.country or ''}",
                 height=small_h,
                 dxfattribs={"layer": "G-CART",
                             "insert": (cart_x + pad, cart_y - pad - text_h - 0.4)})
    if building.reference:
        msp.add_text(f"Réf: {building.reference}",
                     height=small_h,
                     dxfattribs={"layer": "G-CART",
                                 "insert": (cart_x + pad, cart_y - pad - text_h - 0.8)})

    # Sublot info (center column)
    msp.add_text(sublot["title"],
                 height=text_h,
                 dxfattribs={"layer": "G-CART",
                             "insert": (col1 + pad, cart_y - pad - text_h)})
    msp.add_text(f"Niveau: {level.name}",
                 height=text_h,
                 dxfattribs={"layer": "G-CART",
                             "insert": (col1 + pad, cart_y - pad - text_h - 0.5)})
    elev_text = f"Élévation: {level.elevation_m:+.2f} m" if level.elevation_m else ""
    msp.add_text(elev_text,
                 height=small_h,
                 dxfattribs={"layer": "G-CART",
                             "insert": (col1 + pad, cart_y - pad - text_h - 1.0)})

    # Scale + page (right column)
    msp.add_text("TIJAN AI",
                 height=text_h * 1.2,
                 dxfattribs={"layer": "G-CART",
                             "insert": (col2 + pad, cart_y - pad - text_h)})
    msp.add_text("Bureau d'Études Automatisé",
                 height=small_h,
                 dxfattribs={"layer": "G-CART",
                             "insert": (col2 + pad, cart_y - pad - text_h - 0.5)})
    msp.add_text(f"Échelle: 1/100",
                 height=small_h,
                 dxfattribs={"layer": "G-CART",
                             "insert": (col2 + pad, cart_y - pad - text_h - 1.0)})
    if page_num:
        msp.add_text(f"Page {page_num}",
                     height=small_h,
                     dxfattribs={"layer": "G-CART",
                                 "insert": (col2 + pad, cart_y - pad - text_h - 1.5)})


# ══════════════════════════════════════════════════════════════
# RENDERING FUNCTIONS
# ══════════════════════════════════════════════════════════════

def _render_level_sublot(building: Building, level: Level,
                         sublot: dict, page_num: int = 0) -> ezdxf.document.Drawing:
    """Render a single level × sublot combination into a DXF document."""
    doc = ezdxf.new("R2018", setup=True)
    doc.units = dxf_units.M  # Model space in meters

    # Register blocks and layers
    register_all_blocks(doc)

    msp = doc.modelspace()
    bbox = _level_bbox(level)
    code = sublot["code"]

    # ── Always draw: walls + axes + room labels ──
    _draw_walls(msp, level, is_structure=(code == "STR"))
    _draw_room_labels(msp, level)
    _draw_axes(msp, level, bbox)

    # ── Dimensions (only on ARC and STR) ──
    if code in ("ARC", "STR"):
        _draw_dimensions(msp, level, bbox)

    # ── Trade-specific content ──
    if code == "ARC":
        # Architecture only: walls + labels + axes + dimensions (already drawn)
        pass
    elif code == "STR":
        # Structure: highlight structural walls (already drawn with thicker lines)
        pass
    elif code == "SYN":
        # Synthesis: all equipment + all networks
        _draw_equipment(msp, level, eq_filter=set())
        _draw_networks(msp, level, net_filter=set())
    else:
        # Trade-specific sublot
        _draw_equipment(msp, level, eq_filter=sublot["eq_types"])
        _draw_networks(msp, level, net_filter=sublot["net_types"])

    # ── Cartouche ──
    _draw_cartouche(msp, bbox, building, level, sublot, page_num)

    return doc


def render_bim_dxf(building: Building, output_dir: str,
                   sublots_filter: list = None) -> list:
    """Render all level × sublot combinations as individual DXF files.

    Args:
        building: The BIM Building model
        output_dir: Directory to save DXF files
        sublots_filter: Optional list of sublot codes to generate (default: all)

    Returns:
        List of (filepath, sublot_title, level_name) tuples
    """
    os.makedirs(output_dir, exist_ok=True)
    results = []
    page = 0

    active_sublots = [s for s in SUBLOTS if _has_content(building, s)]
    if sublots_filter:
        active_sublots = [s for s in active_sublots if s["code"] in sublots_filter]

    for sublot in active_sublots:
        for level in building.levels:
            page += 1
            doc = _render_level_sublot(building, level, sublot, page)

            fname = f"{sublot['code']}_{level.name.replace('+', 'p').replace(' ', '_')}.dxf"
            fpath = os.path.join(output_dir, fname)
            doc.saveas(fpath)

            results.append((fpath, sublot["title"], level.name))
            logger.info("Rendered %s — %s → %s", sublot["title"], level.name, fpath)

    logger.info("Generated %d DXF files in %s", len(results), output_dir)
    return results


# ══════════════════════════════════════════════════════════════
# PDF COMPILATION (via ezdxf.addons.drawing)
# ══════════════════════════════════════════════════════════════

def _dxf_to_png(doc, png_path: str, dpi: int = 200):
    """Render a DXF document to a PNG image using matplotlib backend."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from ezdxf.addons.drawing import Frontend, RenderContext
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

    fig = plt.figure(dpi=dpi, facecolor="white")
    ax = fig.add_axes([0.02, 0.02, 0.96, 0.96])
    ax.set_facecolor("white")

    ctx = RenderContext(doc)
    ctx.current_layout_properties.set_colors("#FFFFFF")
    backend = MatplotlibBackend(ax)
    Frontend(ctx, backend).draw_layout(doc.modelspace())

    ax.set_aspect("equal")
    ax.autoscale(tight=True)
    fig.savefig(png_path, dpi=dpi, bbox_inches="tight", pad_inches=0.1,
                facecolor="white")
    plt.close(fig)
    return png_path


def compile_bim_pdf(building: Building, output_path: str,
                    lang: str = "fr",
                    sublots_filter: list = None,
                    dpi: int = 200) -> dict:
    """Generate a multi-page PDF dossier from BIM model.

    Each page is one level × sublot rendered via ezdxf → matplotlib → PDF.

    Args:
        building: The BIM Building model
        output_path: Path for the output PDF file
        lang: Language code (fr/en)
        sublots_filter: Optional list of sublot codes
        dpi: Resolution for rendering (default 200)

    Returns:
        Dict with stats: pages, sublots, levels, file_path
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from ezdxf.addons.drawing import Frontend, RenderContext
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

    active_sublots = [s for s in SUBLOTS if _has_content(building, s)]
    if sublots_filter:
        active_sublots = [s for s in active_sublots if s["code"] in sublots_filter]

    # A1 landscape aspect ratio
    fig_w = 16.0  # inches
    fig_h = fig_w * (PAPER_H_MM / PAPER_W_MM)

    page_count = 0
    sublot_names = set()

    with PdfPages(output_path) as pdf:
        # ── Cover page ──
        fig_cover = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
        ax_cover = fig_cover.add_subplot(111)
        ax_cover.set_xlim(0, 100)
        ax_cover.set_ylim(0, 70)
        ax_cover.set_facecolor("white")
        ax_cover.axis("off")

        # Title
        ax_cover.text(50, 55, "TIJAN AI", fontsize=32, ha="center",
                      fontweight="bold", color="#1a1a2e")
        ax_cover.text(50, 48, "Bureau d'Études Automatisé",
                      fontsize=14, ha="center", color="#555")
        ax_cover.text(50, 38, building.name or "Projet BIM",
                      fontsize=22, ha="center", fontweight="bold")
        ax_cover.text(50, 32, f"{building.city or ''}, {building.country or ''}",
                      fontsize=14, ha="center", color="#555")

        info_lines = [
            f"Référence: {building.reference or '—'}",
            f"Niveaux: {len(building.levels)}",
            f"Pièces: {sum(len(l.rooms) for l in building.levels)}",
            f"Sublots: {len(active_sublots)}",
            f"Béton: {building.classe_beton or '—'}",
        ]
        for i, line in enumerate(info_lines):
            ax_cover.text(50, 22 - i * 4, line, fontsize=11,
                          ha="center", color="#333")

        ax_cover.text(50, 3, "Dossier BIM — Plans d'exécution tous corps d'état",
                      fontsize=10, ha="center", color="#888")

        pdf.savefig(fig_cover, dpi=dpi, facecolor="white")
        plt.close(fig_cover)
        page_count += 1

        # ── Plan pages ──
        for sublot in active_sublots:
            sublot_names.add(sublot["title"])
            for level in building.levels:
                page_count += 1
                doc = _render_level_sublot(building, level, sublot, page_count)

                # Use landscape aspect ratio matching the drawing content
                bbox = _level_bbox(level)
                bw = bbox[2] - bbox[0] + 2 * AXIS_OVERSHOOT + 2 * AXIS_CIRCLE_R + 4
                bh = bbox[3] - bbox[1] + 2 * AXIS_OVERSHOOT + 2 * AXIS_CIRCLE_R + 8
                # Fit into landscape page, maintaining aspect ratio
                aspect = bw / max(bh, 0.1)
                if aspect > fig_w / fig_h:
                    pw, ph = fig_w, fig_w / aspect
                else:
                    pw, ph = fig_h * aspect, fig_h

                fig = plt.figure(figsize=(max(pw, 10), max(ph, 7)),
                                 dpi=dpi, facecolor="white")
                ax = fig.add_axes([0.02, 0.02, 0.96, 0.96])
                ax.set_facecolor("white")

                ctx = RenderContext(doc)
                # Override background to white
                ctx.current_layout_properties.set_colors("#FFFFFF")
                backend = MatplotlibBackend(ax)
                Frontend(ctx, backend).draw_layout(doc.modelspace())

                ax.set_aspect("equal")
                ax.autoscale(tight=True)

                pdf.savefig(fig, dpi=dpi, facecolor="white")
                plt.close(fig)

    result = {
        "pages": page_count,
        "sublots": sorted(sublot_names),
        "levels": [l.name for l in building.levels],
        "file_path": output_path,
        "file_size_kb": os.path.getsize(output_path) / 1024,
    }
    logger.info("Compiled PDF: %d pages, %.0f KB → %s",
                result["pages"], result["file_size_kb"], output_path)
    return result


# ══════════════════════════════════════════════════════════════
# STANDALONE TEST
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    # Quick test: generate a minimal building and render
    from bim_model import Building, Level, Room, Wall, Point
    b = Building(name="Test", city="Dakar", country="Senegal")
    lvl = b.add_level("RDC", 0, 3.0)
    lvl.walls = [
        Wall(start=Point(0, 0), end=Point(10, 0), thickness_m=0.25, type=WallType.FACADE),
        Wall(start=Point(10, 0), end=Point(10, 8), thickness_m=0.25, type=WallType.FACADE),
        Wall(start=Point(10, 8), end=Point(0, 8), thickness_m=0.25, type=WallType.FACADE),
        Wall(start=Point(0, 8), end=Point(0, 0), thickness_m=0.25, type=WallType.FACADE),
    ]
    lvl.rooms = [Room(type=RoomType.SEJOUR, name="Séjour", label="Séjour",
                      polygon=[Point(0,0), Point(10,0), Point(10,8), Point(0,8)])]
    lvl.rooms[0]._area_m2 = 80.0
    lvl.axes_x = [0.0, 5.0, 10.0]
    lvl.axes_y = [0.0, 4.0, 8.0]
    lvl.axis_labels_x = ["1", "2", "3"]
    lvl.axis_labels_y = ["A", "B", "C"]

    out = "tests/output"
    os.makedirs(out, exist_ok=True)

    if "--dxf" in sys.argv:
        paths = render_bim_dxf(b, out, sublots_filter=["ARC"])
        print(f"Generated {len(paths)} DXF files")
        for p, t, l in paths:
            print(f"  {p}")

    if "--pdf" in sys.argv or "--dxf" not in sys.argv:
        result = compile_bim_pdf(b, f"{out}/test_dxf_renderer.pdf",
                                 sublots_filter=["ARC", "STR"])
        print(f"Generated PDF: {result['pages']} pages, {result['file_size_kb']:.0f} KB")
        print(f"  → {result['file_path']}")
