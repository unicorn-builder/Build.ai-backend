"""
generate_plans_bim.py — Unified BIM-based plan generator

Single PDF dossier organized by trade then by level, reading ALL equipment
and networks from the Building graph (TijanBIM). One source of truth.

Replaces the dual Plan BA / Plan MEP system.

Output structure (Crystal Residence convention):
  001 ARC  — Architecture plan per level
  200 STR  — Coffrage + ferraillage per level
  410 PLU  — Plumbing (EF/EC/EU) per level + schéma de principe
  413 HVC  — HVAC (clim + VMC) per level + schéma de principe
  400 FIF  — Fire safety (SPK + detection) per level
  510 HCU  — Electrical high current per level
  520 LCU  — Low current per level
  113 RC   — False ceiling per level
  001 SYN  — Synthesis (all networks superimposed) per level

Page count = f(niveaux × trades relevant) — no a priori constraint.
"""
import math
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdfcanvas

from bim_model import (
    Building, Level, Room, Wall, Point,
    EquipmentInstance, NetworkSegment,
    RoomType, WallType, EquipmentType, NetworkType, PlacementType
)
from room_rules import TRADES, TradeDef, get_relevant_trades
from bim_boq import generate_bim_boq, BOQItem

import logging
logger = logging.getLogger("tijan.plans_bim")


# ══════════════════════════════════════════════════════════════
# COLORS
# ══════════════════════════════════════════════════════════════
NOIR   = colors.HexColor("#111111")
GRIS2  = colors.HexColor("#555555")
GRIS3  = colors.HexColor("#888888")
GRIS4  = colors.HexColor("#CCCCCC")
GRIS5  = colors.HexColor("#E8E8E8")
BLANC  = colors.white
VERT   = colors.HexColor("#43A956")
ROUGE  = colors.HexColor("#CC3333")
BLEU   = colors.HexColor("#2196F3")
ORANGE = colors.HexColor("#FF9800")
CYAN   = colors.HexColor("#00ACC1")
MARRON = colors.HexColor("#795548")
JAUNE  = colors.HexColor("#FBC02D")
VIOLET = colors.HexColor("#7B1FA2")

# Trade-specific colors
TRADE_COLORS = {
    "ARC": NOIR,
    "STR": GRIS3,
    "PLU": colors.HexColor("#008000"),
    "HVC": VIOLET,
    "FIF": ROUGE,
    "HCU": colors.HexColor("#FF00FF"),
    "LCU": colors.HexColor("#4169E1"),
    "RC":  colors.HexColor("#4682B4"),
    "SYN": ORANGE,
}

# Network type → display color
NETWORK_COLORS = {
    NetworkType.PLU_EF: BLEU,
    NetworkType.PLU_EC: ROUGE,
    NetworkType.PLU_EU: colors.HexColor("#008000"),
    NetworkType.PLU_EP: MARRON,
    NetworkType.HVC_SOUFFLAGE: BLEU,
    NetworkType.HVC_REPRISE: colors.HexColor("#008000"),
    NetworkType.HVC_VMC: VIOLET,
    NetworkType.HVC_REF: ORANGE,
    NetworkType.HVC_CONDENSAT: GRIS3,
    NetworkType.ELEC_FORT: ORANGE,
    NetworkType.ELEC_FAIBLE: colors.HexColor("#4169E1"),
    NetworkType.FIRE_SPK: ROUGE,
    NetworkType.FIRE_DETECT: JAUNE,
}

A3L = landscape(A3)


# ══════════════════════════════════════════════════════════════
# SUB-LOT DEFINITIONS (Crystal Residence convention)
# Each trade is split into focused sub-lots for readability.
# ══════════════════════════════════════════════════════════════

SUBLOTS = [
    # Architecture — one page per level
    {"title": "001 ARC — Architecture",
     "trade_code": "ARC", "eq_types": set(), "net_types": set(),
     "color": NOIR},

    # Structure — one page per level
    {"title": "200 STR — Coffrage",
     "trade_code": "STR", "eq_types": set(), "net_types": set(),
     "color": GRIS3},

    # Plumbing — split into 3 sub-lots
    {"title": "410 PLU — Eau Froide (EF)",
     "trade_code": "PLU",
     "eq_types": {EquipmentType.WC_UNIT, EquipmentType.LAVABO,
                  EquipmentType.DOUCHE, EquipmentType.BAIGNOIRE,
                  EquipmentType.EVIER, EquipmentType.LAVE_LINGE,
                  EquipmentType.LAVE_VAISSELLE},
     "net_types": {NetworkType.PLU_EF},
     "color": BLEU},

    {"title": "410 PLU — Eau Chaude (EC)",
     "trade_code": "PLU",
     "eq_types": {EquipmentType.CHAUFFE_EAU, EquipmentType.LAVABO,
                  EquipmentType.DOUCHE, EquipmentType.BAIGNOIRE,
                  EquipmentType.EVIER},
     "net_types": {NetworkType.PLU_EC},
     "color": ROUGE},

    {"title": "410 PLU — Eaux Usées (EU)",
     "trade_code": "PLU",
     "eq_types": {EquipmentType.WC_UNIT, EquipmentType.LAVABO,
                  EquipmentType.DOUCHE, EquipmentType.BAIGNOIRE,
                  EquipmentType.EVIER, EquipmentType.LAVE_LINGE,
                  EquipmentType.LAVE_VAISSELLE},
     "net_types": {NetworkType.PLU_EU, NetworkType.PLU_EP},
     "color": colors.HexColor("#008000")},

    # HVAC — split into 2 sub-lots
    {"title": "413 HVC — Climatisation (CLIM)",
     "trade_code": "HVC",
     "eq_types": {EquipmentType.CLIMATISEUR, EquipmentType.UNITE_EXT},
     "net_types": {NetworkType.HVC_REF, NetworkType.HVC_CONDENSAT,
                   NetworkType.HVC_SOUFFLAGE, NetworkType.HVC_REPRISE},
     "color": ORANGE},

    {"title": "413 HVC — Ventilation (VMC)",
     "trade_code": "HVC",
     "eq_types": {EquipmentType.BOUCHE_VMC, EquipmentType.BOUCHE_SOUFFLAGE,
                  EquipmentType.HOTTE},
     "net_types": {NetworkType.HVC_VMC},
     "color": VIOLET},

    # Fire safety — split into 2 sub-lots
    {"title": "400 FIF — Extinction (SPK)",
     "trade_code": "FIF",
     "eq_types": {EquipmentType.SPRINKLER, EquipmentType.RIA, EquipmentType.CDI},
     "net_types": {NetworkType.FIRE_SPK},
     "color": ROUGE},

    {"title": "400 FIF — Détection (DET)",
     "trade_code": "FIF",
     "eq_types": {EquipmentType.DETECTEUR_FUMEE, EquipmentType.DETECTEUR_CHALEUR,
                  EquipmentType.SIRENE, EquipmentType.BOUTON_PANIQUE},
     "net_types": {NetworkType.FIRE_DETECT},
     "color": JAUNE},

    # High current — split into 2 sub-lots
    {"title": "510 HCU — Éclairage (ECL)",
     "trade_code": "HCU",
     "eq_types": {EquipmentType.LUMINAIRE, EquipmentType.APPLIQUE,
                  EquipmentType.INTERRUPTEUR},
     "net_types": {NetworkType.ELEC_FORT},
     "color": ORANGE},

    {"title": "510 HCU — Prises de Courant (PC)",
     "trade_code": "HCU",
     "eq_types": {EquipmentType.PRISE, EquipmentType.PRISE_PLAN_TRAVAIL,
                  EquipmentType.PRISE_ETANCHE, EquipmentType.TABLEAU_ELEC},
     "net_types": {NetworkType.ELEC_FORT},
     "color": colors.HexColor("#FF00FF")},

    # Low current — single page (already light)
    {"title": "520 LCU — Courants Faibles",
     "trade_code": "LCU",
     "eq_types": {EquipmentType.PRISE_RJ45, EquipmentType.PRISE_TV,
                  EquipmentType.INTERPHONE, EquipmentType.WIFI_AP},
     "net_types": {NetworkType.ELEC_FAIBLE},
     "color": colors.HexColor("#4169E1")},

    # False ceiling — single page
    {"title": "113 RC — Faux Plafond",
     "trade_code": "RC", "eq_types": set(), "net_types": set(),
     "color": colors.HexColor("#4682B4")},

    # Synthesis — all networks superimposed
    {"title": "001 SYN — Synthèse",
     "trade_code": "SYN", "eq_types": set(), "net_types": set(),
     "color": ORANGE},
]


def _get_relevant_sublots(building: Building) -> list:
    """Filter SUBLOTS to only those that have equipment or networks in this building."""
    # Collect all equipment types and network types present
    all_eq_types = set()
    all_net_types = set()
    for room in building.all_rooms:
        for eq in room.equipment:
            all_eq_types.add(eq.type)
        for seg in room.network_segments:
            all_net_types.add(seg.type)
    for level in building.levels:
        for seg in level.network_segments:
            all_net_types.add(seg.type)

    relevant = []
    for sublot in SUBLOTS:
        code = sublot["trade_code"]
        # ARC, STR, SYN always included
        if code in ("ARC", "STR", "SYN"):
            relevant.append(sublot)
            continue
        # RC included if building has rooms (always useful)
        if code == "RC":
            relevant.append(sublot)
            continue
        # For MEP sublots: include if any eq_type or net_type is present
        if sublot["eq_types"] & all_eq_types:
            relevant.append(sublot)
        elif sublot["net_types"] & all_net_types:
            relevant.append(sublot)

    return relevant


def _sublot_has_content(sublot: dict, level: Level) -> bool:
    """Check if a sublot has any equipment or networks on this level."""
    code = sublot["trade_code"]
    if code in ("ARC", "STR", "SYN", "RC"):
        return True

    eq_types = sublot.get("eq_types", set())
    net_types = sublot.get("net_types", set())

    # Check equipment
    for room in level.rooms:
        for eq in room.equipment:
            if eq.type in eq_types:
                return True

    # Check networks
    for seg in level.network_segments:
        if seg.type in net_types:
            return True
    for room in level.rooms:
        for seg in room.network_segments:
            if seg.type in net_types:
                return True

    return False


# ══════════════════════════════════════════════════════════════
# EQUIPMENT SYMBOL DRAWING
# ══════════════════════════════════════════════════════════════

def _draw_equipment_symbol(c, x: float, y: float, eq_type: EquipmentType,
                           color, scale: float = 1.0):
    """Draw a standardized MEP symbol at (x, y) in page coordinates."""
    s = scale
    c.setStrokeColor(NOIR)
    c.setLineWidth(0.4)
    c.setFillColor(color)

    if eq_type in (EquipmentType.WC_UNIT,):
        # WC: rounded rectangle
        c.roundRect(x - 3*s, y - 2*s, 6*s, 4*s, 1*s, fill=1, stroke=1)
        c.setFillColor(BLANC); c.setFont("Helvetica-Bold", max(3, 3.5*s))
        c.drawCentredString(x, y - 1.2*s, "WC")

    elif eq_type in (EquipmentType.LAVABO, EquipmentType.EVIER):
        # Lavabo/évier: circle
        c.circle(x, y, 4*s, fill=1, stroke=1)
        c.setFillColor(BLANC); c.setFont("Helvetica-Bold", max(3, 3*s))
        label = "LV" if eq_type == EquipmentType.LAVABO else "EV"
        c.drawCentredString(x, y - 1*s, label)

    elif eq_type == EquipmentType.DOUCHE:
        # Douche: square with X
        c.rect(x - 4*s, y - 4*s, 8*s, 8*s, fill=0, stroke=1)
        c.setStrokeColor(color); c.setLineWidth(0.3)
        c.line(x - 3*s, y - 3*s, x + 3*s, y + 3*s)
        c.line(x - 3*s, y + 3*s, x + 3*s, y - 3*s)

    elif eq_type == EquipmentType.CLIMATISEUR:
        # Split: rectangle with "CLIM"
        c.rect(x - 6*s, y - 2*s, 12*s, 4*s, fill=1, stroke=1)
        c.setFillColor(BLANC); c.setFont("Helvetica-Bold", max(3, 3*s))
        c.drawCentredString(x, y - 1*s, "CLIM")

    elif eq_type == EquipmentType.BOUCHE_VMC:
        # VMC grille: circle with V
        c.circle(x, y, 3.5*s, fill=1, stroke=1)
        c.setFillColor(BLANC); c.setFont("Helvetica-Bold", max(3, 4*s))
        c.drawCentredString(x, y - 1.2*s, "V")

    elif eq_type == EquipmentType.PRISE:
        # Socket: small filled square
        c.rect(x - 2.5*s, y - 2.5*s, 5*s, 5*s, fill=1, stroke=1)

    elif eq_type == EquipmentType.PRISE_RJ45:
        # Data: small diamond
        path = c.beginPath()
        path.moveTo(x, y + 3*s); path.lineTo(x + 3*s, y)
        path.lineTo(x, y - 3*s); path.lineTo(x - 3*s, y)
        path.close()
        c.drawPath(path, fill=1, stroke=1)

    elif eq_type == EquipmentType.INTERRUPTEUR:
        # Switch: small circle with line
        c.circle(x, y, 2.5*s, fill=0, stroke=1)
        c.line(x, y + 2.5*s, x + 3*s, y + 5*s)

    elif eq_type == EquipmentType.LUMINAIRE:
        # Light: X in circle
        c.setStrokeColor(color); c.setLineWidth(0.5)
        c.circle(x, y, 3.5*s, fill=0, stroke=1)
        c.line(x - 2*s, y - 2*s, x + 2*s, y + 2*s)
        c.line(x - 2*s, y + 2*s, x + 2*s, y - 2*s)

    elif eq_type == EquipmentType.SPRINKLER:
        # Sprinkler: triangle pointing down
        path = c.beginPath()
        path.moveTo(x, y - 4*s); path.lineTo(x - 3*s, y + 2*s)
        path.lineTo(x + 3*s, y + 2*s)
        path.close()
        c.drawPath(path, fill=1, stroke=1)

    elif eq_type in (EquipmentType.DETECTEUR_FUMEE, EquipmentType.DETECTEUR_CHALEUR):
        # Detector: circle with D
        c.circle(x, y, 3*s, fill=1, stroke=1)
        c.setFillColor(BLANC); c.setFont("Helvetica-Bold", max(3, 3.5*s))
        label = "DF" if eq_type == EquipmentType.DETECTEUR_FUMEE else "DC"
        c.drawCentredString(x, y - 1*s, label)

    elif eq_type == EquipmentType.TABLEAU_ELEC:
        # Panel: large rectangle
        c.rect(x - 5*s, y - 3*s, 10*s, 6*s, fill=1, stroke=1)
        c.setFillColor(BLANC); c.setFont("Helvetica-Bold", max(3, 3*s))
        c.drawCentredString(x, y - 1*s, "TGBT")

    else:
        # Default: filled circle
        c.circle(x, y, 3*s, fill=1, stroke=1)


# ══════════════════════════════════════════════════════════════
# NETWORK SEGMENT DRAWING
# ══════════════════════════════════════════════════════════════

def _draw_network_segment(c, seg: NetworkSegment, tx, ty, color, scale: float = 1.0):
    """Draw a network segment (pipe/duct/cable) in page coordinates."""
    x1, y1 = tx(seg.start.x), ty(seg.start.y)
    x2, y2 = tx(seg.end.x), ty(seg.end.y)

    if seg.is_vertical:
        # Vertical segments shown as small circles (riser markers)
        c.setStrokeColor(color); c.setFillColor(color)
        c.setLineWidth(0.5)
        c.circle(x1, y1, 2.5 * scale, fill=1, stroke=1)
        return

    # Horizontal segments: line with appropriate weight
    width = max(0.3, min(seg.diameter_mm / 30.0, 2.5)) * scale
    c.setStrokeColor(color)
    c.setLineWidth(width)

    # Dashed for waste water, solid for supply
    if seg.type in (NetworkType.PLU_EU, NetworkType.PLU_EP):
        c.setDash(3, 2)
    elif seg.type in (NetworkType.ELEC_FAIBLE, NetworkType.FIRE_DETECT):
        c.setDash(2, 2)
    else:
        c.setDash()

    c.line(x1, y1, x2, y2)
    c.setDash()  # Reset

    # Diameter label on longer segments
    length_px = math.hypot(x2 - x1, y2 - y1)
    if length_px > 25 * scale and seg.diameter_mm >= 12:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        c.setFillColor(color)
        c.setFont("Helvetica", max(2.5, 3 * scale))
        c.drawCentredString(mx, my + 2, f"Ø{int(seg.diameter_mm)}")


# ══════════════════════════════════════════════════════════════
# LAYOUT ENGINE
# ══════════════════════════════════════════════════════════════

def _compute_layout(level: Level, w: float, h: float
                    ) -> Tuple[float, float, float, float, float]:
    """Compute transform parameters to fit a level into the page.

    Returns (ox, oy, scale, draw_w, draw_h) where:
      ox, oy = page origin (bottom-left of drawing area)
      scale = meters → points conversion
      draw_w, draw_h = available drawing area in points
    """
    margin_l = 20 * mm
    margin_r = 15 * mm
    margin_b = 55 * mm  # Space for cartouche
    margin_t = 22 * mm  # Space for title

    draw_w = w - margin_l - margin_r
    draw_h = h - margin_b - margin_t

    bbox = level.bbox
    bw = max(bbox.width, 1.0)
    bh = max(bbox.height, 1.0)

    # Scale to fit with 5% padding
    sx = draw_w / (bw * 1.05)
    sy = draw_h / (bh * 1.05)
    scale = min(sx, sy)

    # Center in drawing area
    ox = margin_l + (draw_w - bw * scale) / 2 - bbox.min_pt.x * scale
    oy = margin_b + (draw_h - bh * scale) / 2 - bbox.min_pt.y * scale

    return ox, oy, scale, draw_w, draw_h


def _tx(x: float, ox: float, scale: float) -> float:
    """Transform model X to page X."""
    return ox + x * scale

def _ty(y: float, oy: float, scale: float) -> float:
    """Transform model Y to page Y."""
    return oy + y * scale


# ══════════════════════════════════════════════════════════════
# PAGE ELEMENTS
# ══════════════════════════════════════════════════════════════

def _border(c, w, h):
    c.setStrokeColor(NOIR); c.setLineWidth(0.5)
    c.rect(8*mm, 8*mm, w - 16*mm, h - 16*mm)

def _cartouche_bim(c, w, h, building: Building, titre: str,
                   page: int, total: int, trade_code: str = "",
                   ech: str = "1/100"):
    """Professional BIM-style cartouche."""
    cw, ch_ = 180*mm, 42*mm
    cx = w - cw - 10*mm; cy = 8*mm

    c.setFillColor(BLANC); c.setStrokeColor(NOIR); c.setLineWidth(0.8)
    c.rect(cx, cy, cw, ch_, fill=1, stroke=1)

    # Horizontal dividers
    c.setLineWidth(0.3)
    hb1 = cy + ch_ * 0.60
    hb2 = cy + ch_ * 0.28
    c.line(cx, hb1, cx + cw, hb1)
    c.line(cx, hb2, cx + cw, hb2)

    # Vertical dividers
    c1 = 38*mm; c2 = 108*mm; c3 = 140*mm
    c.line(cx + c1, cy, cx + c1, cy + ch_)
    c.line(cx + c2, cy + hb1 - cy, cx + c2, cy + ch_)
    c.line(cx + c3, cy, cx + c3, hb2)

    # Branding
    c.setFillColor(VERT); c.setFont("Helvetica-Bold", 10)
    c.drawString(cx + 3*mm, cy + ch_ - 9*mm, "TIJAN AI")
    c.setFillColor(GRIS3); c.setFont("Helvetica", 5.5)
    c.drawString(cx + 3*mm, cy + ch_ - 14*mm, "Bureau d'Études Automatisé")
    c.drawString(cx + 3*mm, cy + 3*mm, f"Date: {datetime.now().strftime('%d/%m/%Y')}")

    # Project info
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 8)
    c.drawString(cx + c1 + 3*mm, cy + ch_ - 9*mm, building.name[:30])
    c.setFillColor(GRIS3); c.setFont("Helvetica", 6)
    c.drawString(cx + c1 + 3*mm, cy + ch_ - 14*mm, f"{building.city}, {building.country}")

    # Scale + page
    c.drawString(cx + c2 + 3*mm, cy + ch_ - 9*mm, f"Éch: {ech}")
    c.drawString(cx + c2 + 3*mm, cy + ch_ - 14*mm, f"Pl. {page}/{total}")

    # Title (trade)
    trade_color = TRADE_COLORS.get(trade_code, VERT)
    c.setFillColor(trade_color); c.setFont("Helvetica-Bold", 7)
    c.drawString(cx + c1 + 3*mm, hb2 + (hb1 - hb2 - 7) / 2,
                 titre[:50])

    # Phase + reference
    c.setFillColor(GRIS3); c.setFont("Helvetica", 5)
    c.drawString(cx + c1 + 3*mm, cy + 3*mm, f"Réf: {building.reference or trade_code}")
    c.drawString(cx + c3 + 3*mm, cy + 3*mm, "Phase: APD")
    c.drawString(cx + c3 + 3*mm, cy + 10*mm, f"BIM v{trade_code}-{page:03d}")


def _draw_walls(c, level: Level, ox: float, oy: float, scale: float,
                light: bool = False):
    """Draw all walls of a level."""
    alpha = 0.3 if light else 1.0
    c.saveState()
    if light:
        c.setStrokeAlpha(alpha)
        c.setFillAlpha(alpha)

    for wall in level.walls:
        x1 = _tx(wall.start.x, ox, scale)
        y1 = _ty(wall.start.y, oy, scale)
        x2 = _tx(wall.end.x, ox, scale)
        y2 = _ty(wall.end.y, oy, scale)

        # Wall thickness in page units
        thick_px = max(1.0, wall.thickness_m * scale)

        if wall.type == WallType.FACADE:
            c.setStrokeColor(NOIR)
            c.setLineWidth(thick_px)
        elif wall.type == WallType.PORTEUR:
            c.setStrokeColor(GRIS2)
            c.setLineWidth(thick_px)
        else:
            c.setStrokeColor(GRIS3)
            c.setLineWidth(max(0.5, thick_px * 0.6))

        c.line(x1, y1, x2, y2)

        # Draw openings
        for opening in wall.openings:
            _draw_opening(c, wall, opening, ox, oy, scale)

    c.restoreState()


def _draw_opening(c, wall: Wall, opening, ox: float, oy: float, scale: float):
    """Draw a door or window opening on a wall."""
    pt = wall.point_at_offset(opening.offset_along_wall_m)
    x = _tx(pt.x, ox, scale)
    y = _ty(pt.y, oy, scale)
    half_w = (opening.width_m * scale) / 2

    dx, dy = wall.direction
    c.saveState()

    if opening.type.value == "window":
        # Window: two parallel lines
        c.setStrokeColor(BLEU); c.setLineWidth(0.8)
        c.line(x - dx * half_w, y - dy * half_w,
               x + dx * half_w, y + dy * half_w)
    else:
        # Door: gap in wall + arc
        c.setStrokeColor(BLANC); c.setLineWidth(max(2, wall.thickness_m * scale * 1.2))
        c.line(x - dx * half_w, y - dy * half_w,
               x + dx * half_w, y + dy * half_w)
        # Door arc
        c.setStrokeColor(GRIS4); c.setLineWidth(0.3)
        nx, ny = wall.normal
        arc_x = x - dx * half_w
        arc_y = y - dy * half_w
        c.arc(arc_x - half_w, arc_y - half_w,
              arc_x + half_w * 2, arc_y + half_w * 2,
              0, 90)

    c.restoreState()


def _draw_room_labels(c, level: Level, ox: float, oy: float, scale: float):
    """Draw room names and areas."""
    c.setFont("Helvetica", max(4, 5))
    for room in level.rooms:
        cx = _tx(room.center.x, ox, scale)
        cy = _ty(room.center.y, oy, scale)
        c.setFillColor(GRIS2)
        label = room.name or room.type.value
        c.drawCentredString(cx, cy + 2, label[:18])
        c.setFont("Helvetica", max(3, 4))
        c.setFillColor(GRIS3)
        c.drawCentredString(cx, cy - 5, f"{room.area_m2:.1f} m²")
        c.setFont("Helvetica", max(4, 5))


def _draw_axes(c, level: Level, ox: float, oy: float, scale: float):
    """Draw structural grid axes."""
    if not level.axes_x or not level.axes_y:
        return

    c.saveState()
    c.setStrokeColor(GRIS4); c.setLineWidth(0.3); c.setDash(4, 4)

    bbox = level.bbox
    y_lo = _ty(bbox.min_pt.y, oy, scale) - 8*mm
    y_hi = _ty(bbox.max_pt.y, oy, scale) + 8*mm
    x_lo = _tx(bbox.min_pt.x, ox, scale) - 8*mm
    x_hi = _tx(bbox.max_pt.x, ox, scale) + 8*mm

    for i, ax in enumerate(level.axes_x):
        px = _tx(ax, ox, scale)
        c.line(px, y_lo, px, y_hi)
        # Label
        label = level.axis_labels_x[i] if i < len(level.axis_labels_x) else str(i + 1)
        _draw_axis_label(c, px, y_lo - 5*mm, label)
        _draw_axis_label(c, px, y_hi + 5*mm, label)

    for j, ay in enumerate(level.axes_y):
        py = _ty(ay, oy, scale)
        c.line(x_lo, py, x_hi, py)
        label = level.axis_labels_y[j] if j < len(level.axis_labels_y) else chr(65 + j)
        _draw_axis_label(c, x_lo - 5*mm, py, label)
        _draw_axis_label(c, x_hi + 5*mm, py, label)

    c.setDash()
    c.restoreState()


def _draw_axis_label(c, x, y, label):
    """Draw a circled axis label."""
    r = 4*mm
    c.setStrokeColor(NOIR); c.setLineWidth(0.4)
    c.setFillColor(BLANC)
    c.circle(x, y, r, fill=1, stroke=1)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 7)
    tw = c.stringWidth(str(label), "Helvetica-Bold", 7)
    c.drawString(x - tw / 2, y - 2.5, str(label))


# ══════════════════════════════════════════════════════════════
# TRADE-SPECIFIC RENDERERS
# ══════════════════════════════════════════════════════════════


def _render_sublot_page(c, level: Level, building: Building,
                        sublot: dict, ox: float, oy: float,
                        scale: float, w: float, h: float,
                        page: int, total: int):
    """Render one page: background walls + sublot-specific equipment + networks.

    sublot dict keys: title, trade_code, eq_types (set), net_types (set), color
    """
    _border(c, w, h)

    trade_code = sublot["trade_code"]
    title = sublot["title"]
    color = sublot["color"]

    # Title
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 11)
    c.drawString(14*mm, h - 17*mm, f"{title} — {level.name}")

    # Draw background walls (light for MEP, full for ARC/STR)
    light = trade_code not in ("ARC", "STR")
    _draw_walls(c, level, ox, oy, scale, light=light)
    _draw_axes(c, level, ox, oy, scale)

    if trade_code == "ARC":
        _draw_room_labels(c, level, ox, oy, scale)

    elif trade_code == "SYN":
        _draw_room_labels(c, level, ox, oy, scale)
        _draw_all_equipment(c, level, ox, oy, scale)
        _draw_all_networks(c, level, ox, oy, scale)
        _draw_legend_synthesis(c, w, h)

    else:
        eq_types = sublot.get("eq_types", set())
        net_types = sublot.get("net_types", set())

        # Draw ONLY network segments for this sublot
        all_segs = list(level.network_segments)
        for room in level.rooms:
            all_segs.extend(room.network_segments)

        for seg in all_segs:
            if seg.type in net_types:
                seg_color = NETWORK_COLORS.get(seg.type, color)
                _draw_network_segment(c, seg,
                                      lambda x: _tx(x, ox, scale),
                                      lambda y: _ty(y, oy, scale),
                                      seg_color, scale=1.0)

        # Draw ONLY equipment for this sublot
        for room in level.rooms:
            for eq in room.equipment:
                if eq.type in eq_types:
                    px = _tx(eq.position.x, ox, scale)
                    py = _ty(eq.position.y, oy, scale)
                    _draw_equipment_symbol(c, px, py, eq.type, color)

        # Nomenclature for this sublot only
        _draw_sublot_nomenclature(c, level, sublot, w, h)

    # Cartouche
    _cartouche_bim(c, w, h, building, f"{title} — {level.name}",
                   page, total, trade_code)


def _draw_sublot_nomenclature(c, level: Level, sublot: dict,
                               w: float, h: float):
    """Draw equipment count table for a sublot on this level."""
    eq_types = sublot.get("eq_types", set())
    counts = {}
    for room in level.rooms:
        for eq in room.equipment:
            if eq.type in eq_types:
                label = eq.label or eq.type.value
                counts[label] = counts.get(label, 0) + 1

    if not counts:
        return

    x = 14*mm; y = 52*mm
    c.setFont("Helvetica-Bold", 6)
    c.setFillColor(sublot["color"])
    c.drawString(x, y + 4*mm, f"NOMENCLATURE — {sublot['title']}")

    c.setFont("Helvetica", 5)
    c.setFillColor(NOIR)
    row_y = y
    for label, qty in sorted(counts.items(), key=lambda x: -x[1]):
        c.drawString(x, row_y, f"• {label}: {qty}")
        row_y -= 3.5*mm
        if row_y < 12*mm:
            break


def _draw_all_equipment(c, level: Level, ox: float, oy: float, scale: float):
    """Draw all equipment in all rooms (for synthesis page)."""
    for room in level.rooms:
        for eq in room.equipment:
            px = _tx(eq.position.x, ox, scale)
            py = _ty(eq.position.y, oy, scale)
            # Use network-appropriate color
            eq_color = _equipment_color(eq.type)
            _draw_equipment_symbol(c, px, py, eq.type, eq_color, scale=0.7)


def _draw_all_networks(c, level: Level, ox: float, oy: float, scale: float):
    """Draw all network segments (for synthesis page)."""
    all_segs = list(level.network_segments)
    for room in level.rooms:
        all_segs.extend(room.network_segments)

    for seg in all_segs:
        color = NETWORK_COLORS.get(seg.type, GRIS3)
        _draw_network_segment(c, seg,
                              lambda x: _tx(x, ox, scale),
                              lambda y: _ty(y, oy, scale),
                              color, scale=0.8)


def _equipment_color(eq_type: EquipmentType) -> colors.Color:
    """Get display color for equipment type."""
    plumbing = {EquipmentType.WC_UNIT, EquipmentType.LAVABO, EquipmentType.DOUCHE,
                EquipmentType.BAIGNOIRE, EquipmentType.EVIER, EquipmentType.LAVE_LINGE,
                EquipmentType.LAVE_VAISSELLE, EquipmentType.CHAUFFE_EAU}
    hvac = {EquipmentType.CLIMATISEUR, EquipmentType.UNITE_EXT, EquipmentType.BOUCHE_VMC,
            EquipmentType.BOUCHE_SOUFFLAGE, EquipmentType.HOTTE}
    fire = {EquipmentType.SPRINKLER, EquipmentType.SIRENE, EquipmentType.CDI,
            EquipmentType.RIA, EquipmentType.DETECTEUR_FUMEE, EquipmentType.DETECTEUR_CHALEUR}

    if eq_type in plumbing:
        return colors.HexColor("#008000")
    elif eq_type in hvac:
        return VIOLET
    elif eq_type in fire:
        return ROUGE
    elif eq_type in (EquipmentType.PRISE_RJ45, EquipmentType.PRISE_TV,
                     EquipmentType.INTERPHONE, EquipmentType.WIFI_AP):
        return colors.HexColor("#4169E1")
    else:
        return ORANGE  # Electrical



def _draw_legend_synthesis(c, w: float, h: float):
    """Draw a color legend for the synthesis page."""
    x = 14*mm; y = h - 25*mm
    c.setFont("Helvetica-Bold", 6)
    c.setFillColor(NOIR)
    c.drawString(x, y, "LÉGENDE RÉSEAUX")

    items = [
        ("EF — Eau Froide", BLEU),
        ("EC — Eau Chaude", ROUGE),
        ("EU — Eaux Usées", colors.HexColor("#008000")),
        ("CLIM — Réfrigérant", ORANGE),
        ("VMC — Extraction", VIOLET),
        ("HCU — Courants Forts", ORANGE),
        ("LCU — Courants Faibles", colors.HexColor("#4169E1")),
        ("SPK — Sprinkler", ROUGE),
    ]

    c.setFont("Helvetica", 4.5)
    for i, (label, color) in enumerate(items):
        ly = y - (i + 1) * 4*mm
        c.setFillColor(color)
        c.rect(x, ly - 1, 6, 3, fill=1, stroke=0)
        c.setFillColor(NOIR)
        c.drawString(x + 8, ly - 1, label)


# ══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════

def generer_dossier_bim(output_path: str, building: Building,
                        resultats_structure=None, resultats_mep=None,
                        lang: str = "fr") -> Dict[str, Any]:
    """Generate a unified BIM plan dossier as a single PDF.

    Uses sub-lot splitting for readability: each trade is broken into
    focused sub-pages (e.g., PLU → EF/EC/EU, HVC → CLIM/VMC).
    Empty sub-lots on a given level are skipped.

    Args:
        output_path: Where to write the PDF
        building: Building with rooms, equipment, and network_segments
        resultats_structure: Optional ResultatsStructure for structural pages
        resultats_mep: Optional ResultatsMEP for additional sizing info
        lang: "fr" or "en"

    Returns:
        Dict with metadata: {pages, trades, boq_summary}
    """
    # Get relevant sublots for this building
    sublots = _get_relevant_sublots(building)
    if not sublots:
        sublots = [s for s in SUBLOTS if s["trade_code"] in ("ARC", "STR", "SYN")]

    # Pre-count pages (skip empty sublot×level combos)
    page_plan = []
    for sublot in sublots:
        for level in building.levels:
            if _sublot_has_content(sublot, level):
                page_plan.append((sublot, level))

    total_pages = len(page_plan)
    page = 0

    c = pdfcanvas.Canvas(output_path, pagesize=A3L)
    c.setTitle(f"Dossier BIM — {building.name}")
    c.setAuthor("Tijan AI — Bureau d'Études Automatisé")

    for sublot, level in page_plan:
        page += 1
        w, h = A3L
        c.setPageSize(A3L)

        ox, oy, scale, draw_w, draw_h = _compute_layout(level, w, h)

        _render_sublot_page(c, level, building, sublot,
                            ox, oy, scale, w, h, page, total_pages)

        c.showPage()

    c.save()

    # Generate BOQ from same BIM model
    boq = generate_bim_boq(building, lang=lang)

    # Collect unique trade codes used
    trade_codes = list(dict.fromkeys(s["trade_code"] for s in sublots))

    logger.info("BIM dossier: %d pages, %d sublots, %d levels → %s",
                page, len(sublots), len(building.levels), output_path)

    return {
        "pages": page,
        "trades": trade_codes,
        "sublots": [s["title"] for s in sublots],
        "levels": [l.name for l in building.levels],
        "boq_summary": boq["summary"],
        "output_path": output_path,
    }


# ══════════════════════════════════════════════════════════════
# CONVENIENCE: Full pipeline in one call
# ══════════════════════════════════════════════════════════════

def full_bim_pipeline(params: Dict, output_path: str,
                      lang: str = "fr") -> Dict[str, Any]:
    """Run the complete BIM pipeline from params to PDF.

    1. Create Building from params
    2. Place equipment via room_rules
    3. Route MEP networks
    4. Generate unified PDF dossier
    5. Generate BIM-counted BOQ

    Returns metadata dict.
    """
    from room_rules import place_equipment_in_room
    from mep_router import route_mep

    # Step 1: Create building
    building = Building.from_params_dict(params)

    # Step 2: Place equipment
    for level in building.levels:
        for room in level.rooms:
            room_walls = [w for w in level.walls
                          if w.room_left_id == room.id or w.room_right_id == room.id]
            room.equipment = place_equipment_in_room(room, room_walls, lang=lang)

    # Step 3: Route MEP
    building = route_mep(building)

    # Step 4: Generate dossier
    result = generer_dossier_bim(output_path, building, lang=lang)

    # Step 5: BOQ
    boq = generate_bim_boq(building, lang=lang)
    result["boq"] = boq

    return result
