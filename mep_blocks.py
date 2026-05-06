"""
mep_blocks.py — Professional MEP block library for ezdxf

Each block is a standardized CAD symbol matching NF/EN conventions.
Blocks are drawn at 1:1 scale in meters, inserted with scale factor.

Usage:
    from mep_blocks import register_all_blocks
    register_all_blocks(doc)
    msp.add_blockref("TJ_WC", insert=(x, y), dxfattribs={"layer": "P-FIXT"})

Block naming: TJ_{EQUIPMENT_TYPE} (e.g. TJ_WC, TJ_LAVABO, TJ_SPLIT)
Layer conventions:
    A-WALL      Architectural walls
    A-WALL-INT  Interior partitions
    A-DOOR      Doors
    A-GLAZ      Windows/glazing
    A-TEXT      Room labels, annotations
    P-FIXT      Plumbing fixtures (WC, lavabo, douche, évier)
    P-PIPE-EF   Cold water pipes
    P-PIPE-EC   Hot water pipes
    P-PIPE-EU   Waste water pipes
    M-EQUIP     HVAC equipment (splits, VMC)
    M-DUCT      HVAC ducts
    E-POWR      Electrical power (prises, interrupteurs)
    E-LITE      Lighting (luminaires)
    E-LCCR      Low current (RJ45, TV, détecteurs)
    F-SPKL      Fire sprinklers
    F-DETECT    Fire detection
    S-GRID      Structural grid/axes
    S-DIM       Dimensions
    G-CART      Cartouche/title block
"""
from __future__ import annotations
import math
import logging
from typing import Optional

logger = logging.getLogger("tijan.mep_blocks")

try:
    import ezdxf
    from ezdxf import colors as dxf_colors
    from ezdxf.math import Vec2
except ImportError:
    ezdxf = None
    logger.warning("ezdxf not installed — mep_blocks unavailable")


# ══════════════════════════════════════════════════════════════
# LAYER DEFINITIONS
# ══════════════════════════════════════════════════════════════

LAYERS = {
    # (layer_name, color_index, lineweight_mm, linetype)
    # NOTE: Avoid color 7 (white) — invisible on white-background PDF.
    # Use 250 (near-black) for elements that need to be dark.
    "A-WALL":     (250, 50, "CONTINUOUS"),    # Near-black, 0.50mm
    "A-WALL-INT": (8, 25, "CONTINUOUS"),      # Grey, 0.25mm
    "A-DOOR":     (30, 18, "CONTINUOUS"),     # Orange
    "A-GLAZ":     (4, 18, "CONTINUOUS"),      # Cyan
    "A-TEXT":     (250, 0, "CONTINUOUS"),      # Near-black, default
    "A-HATCH":   (252, 0, "CONTINUOUS"),      # Light grey fill
    "P-FIXT":    (5, 25, "CONTINUOUS"),       # Blue
    "P-PIPE-EF": (5, 18, "CONTINUOUS"),       # Blue
    "P-PIPE-EC": (1, 18, "CONTINUOUS"),       # Red
    "P-PIPE-EU": (3, 18, "CONTINUOUS"),       # Green
    "M-EQUIP":   (2, 25, "CONTINUOUS"),       # Yellow
    "M-DUCT":    (2, 18, "DASHED"),           # Yellow dashed
    "E-POWR":    (6, 18, "CONTINUOUS"),       # Magenta
    "E-LITE":    (6, 13, "CONTINUOUS"),       # Magenta thin
    "E-LCCR":    (4, 13, "CONTINUOUS"),       # Cyan thin
    "F-SPKL":    (1, 25, "CONTINUOUS"),       # Red
    "F-DETECT":  (1, 13, "CONTINUOUS"),       # Red thin
    "S-GRID":    (8, 9, "CENTER"),            # Grey, center line
    "S-DIM":     (250, 13, "CONTINUOUS"),     # Near-black thin
    "G-CART":    (250, 35, "CONTINUOUS"),      # Near-black, 0.35mm
}


def setup_layers(doc):
    """Create all MEP layers in the DXF document."""
    for name, (color, lw, lt) in LAYERS.items():
        if name not in doc.layers:
            layer = doc.layers.add(name)
            layer.color = color
            layer.dxf.lineweight = lw
            if lt != "CONTINUOUS" and lt in doc.linetypes:
                layer.dxf.linetype = lt


# ══════════════════════════════════════════════════════════════
# BLOCK DEFINITIONS — Plumbing Fixtures
# ══════════════════════════════════════════════════════════════

def _block_wc(doc):
    """WC unit — plan view: bowl (ellipse) + tank (rectangle).
    Real dimensions: ~0.38m wide × 0.70m deep."""
    blk = doc.blocks.new(name="TJ_WC")

    # Tank (cistern) — rectangle at back
    blk.add_lwpolyline(
        [(-0.19, 0.55), (0.19, 0.55), (0.19, 0.70), (-0.19, 0.70)],
        close=True, dxfattribs={"layer": "P-FIXT"})

    # Bowl — ellipse shape approximated with polyline arc
    # Outer bowl contour
    pts = []
    for i in range(21):
        angle = math.pi * i / 20  # 0 to pi (semicircle front)
        x = 0.18 * math.sin(angle)
        y = 0.25 * math.cos(angle) + 0.15
        pts.append((x, y))
    # Close back
    pts.append((-0.18, 0.15))
    pts.append((-0.19, 0.55))
    pts.append((0.19, 0.55))
    pts.append((0.18, 0.15))
    blk.add_lwpolyline(pts, close=True, dxfattribs={"layer": "P-FIXT"})

    # Seat opening — inner ellipse
    inner = []
    for i in range(17):
        angle = math.pi * i / 16
        x = 0.12 * math.sin(angle)
        y = 0.18 * math.cos(angle) + 0.18
        inner.append((x, y))
    inner.append((-0.12, 0.18))
    blk.add_lwpolyline(inner, close=True, dxfattribs={"layer": "P-FIXT"})

    return blk


def _block_lavabo(doc):
    """Lavabo (washbasin) — plan view: D-shape ~0.50m × 0.40m."""
    blk = doc.blocks.new(name="TJ_LAVABO")

    # Outer contour — D shape (flat back, curved front)
    pts = [(-0.25, 0.40)]  # top-left (wall side)
    # Curved front
    for i in range(21):
        angle = math.pi * i / 20
        x = 0.25 * math.sin(angle)
        y = 0.35 * math.cos(angle)
        pts.append((x, y))
    pts.append((-0.25, 0.0))  # complete the curve
    pts.append((-0.25, 0.40))  # back to wall
    blk.add_lwpolyline(pts, close=True, dxfattribs={"layer": "P-FIXT"})

    # Basin (inner) — smaller D
    inner = [(-0.18, 0.35)]
    for i in range(17):
        angle = math.pi * i / 16
        x = 0.18 * math.sin(angle)
        y = 0.25 * math.cos(angle) + 0.05
        inner.append((x, y))
    inner.append((-0.18, 0.05))
    inner.append((-0.18, 0.35))
    blk.add_lwpolyline(inner, close=True, dxfattribs={"layer": "P-FIXT"})

    # Drain — small circle at center
    blk.add_circle((0, 0.18), 0.02, dxfattribs={"layer": "P-FIXT"})

    # Faucet — small rectangle at back center
    blk.add_lwpolyline(
        [(-0.03, 0.37), (0.03, 0.37), (0.03, 0.40), (-0.03, 0.40)],
        close=True, dxfattribs={"layer": "P-FIXT"})

    return blk


def _block_douche(doc):
    """Douche (shower tray) — plan view: square 0.90m × 0.90m with drain."""
    blk = doc.blocks.new(name="TJ_DOUCHE")

    # Tray outline
    blk.add_lwpolyline(
        [(0, 0), (0.90, 0), (0.90, 0.90), (0, 0.90)],
        close=True, dxfattribs={"layer": "P-FIXT"})

    # Inner edge (lip)
    blk.add_lwpolyline(
        [(0.05, 0.05), (0.85, 0.05), (0.85, 0.85), (0.05, 0.85)],
        close=True, dxfattribs={"layer": "P-FIXT"})

    # Drain — circle
    blk.add_circle((0.45, 0.45), 0.04, dxfattribs={"layer": "P-FIXT"})

    # Diagonal lines (standard shower symbol)
    blk.add_line((0, 0), (0.90, 0.90), dxfattribs={"layer": "P-FIXT"})
    blk.add_line((0.90, 0), (0, 0.90), dxfattribs={"layer": "P-FIXT"})

    return blk


def _block_evier(doc):
    """Évier (kitchen sink) — plan view: rectangle with 1 or 2 basins.
    ~0.80m × 0.50m."""
    blk = doc.blocks.new(name="TJ_EVIER")

    # Outer counter
    blk.add_lwpolyline(
        [(0, 0), (0.80, 0), (0.80, 0.50), (0, 0.50)],
        close=True, dxfattribs={"layer": "P-FIXT"})

    # Left basin
    blk.add_lwpolyline(
        [(0.05, 0.05), (0.37, 0.05), (0.37, 0.42), (0.05, 0.42)],
        close=True, dxfattribs={"layer": "P-FIXT"})

    # Right basin
    blk.add_lwpolyline(
        [(0.43, 0.05), (0.75, 0.05), (0.75, 0.42), (0.43, 0.42)],
        close=True, dxfattribs={"layer": "P-FIXT"})

    # Drains
    blk.add_circle((0.21, 0.23), 0.02, dxfattribs={"layer": "P-FIXT"})
    blk.add_circle((0.59, 0.23), 0.02, dxfattribs={"layer": "P-FIXT"})

    # Faucet
    blk.add_circle((0.40, 0.45), 0.03, dxfattribs={"layer": "P-FIXT"})

    return blk


def _block_baignoire(doc):
    """Baignoire (bathtub) — plan view: 1.70m × 0.70m rounded rectangle."""
    blk = doc.blocks.new(name="TJ_BAIGNOIRE")

    # Outer tub (rounded corners via bulge)
    pts = [
        (0, 0.10, 0),
        (0, 0.60, 0.4),
        (0.10, 0.70, 0),
        (1.60, 0.70, 0.4),
        (1.70, 0.60, 0),
        (1.70, 0.10, 0.4),
        (1.60, 0, 0),
        (0.10, 0, 0.4),
    ]
    blk.add_lwpolyline(pts, close=True, dxfattribs={"layer": "P-FIXT"})

    # Inner tub
    blk.add_lwpolyline(
        [(0.08, 0.08), (1.62, 0.08), (1.62, 0.62), (0.08, 0.62)],
        close=True, dxfattribs={"layer": "P-FIXT"})

    # Drain
    blk.add_circle((1.45, 0.35), 0.03, dxfattribs={"layer": "P-FIXT"})

    # Faucet end
    blk.add_lwpolyline(
        [(0.12, 0.28), (0.12, 0.42), (0.05, 0.42), (0.05, 0.28)],
        close=True, dxfattribs={"layer": "P-FIXT"})

    return blk


def _block_chauffe_eau(doc):
    """Chauffe-eau (water heater) — plan view: circle Ø0.50m."""
    blk = doc.blocks.new(name="TJ_CHAUFFE_EAU")
    blk.add_circle((0, 0), 0.25, dxfattribs={"layer": "P-FIXT"})
    # Inner circle
    blk.add_circle((0, 0), 0.20, dxfattribs={"layer": "P-FIXT"})
    # CE label
    blk.add_text("CE", height=0.10, dxfattribs={
        "layer": "P-FIXT", "insert": (-0.08, -0.05)})
    return blk


def _block_lave_linge(doc):
    """Lave-linge (washing machine) — plan view: 0.60m × 0.60m square + circle."""
    blk = doc.blocks.new(name="TJ_LAVE_LINGE")
    blk.add_lwpolyline(
        [(0, 0), (0.60, 0), (0.60, 0.60), (0, 0.60)],
        close=True, dxfattribs={"layer": "P-FIXT"})
    blk.add_circle((0.30, 0.30), 0.20, dxfattribs={"layer": "P-FIXT"})
    blk.add_circle((0.30, 0.30), 0.05, dxfattribs={"layer": "P-FIXT"})
    return blk


# ══════════════════════════════════════════════════════════════
# BLOCK DEFINITIONS — HVAC
# ══════════════════════════════════════════════════════════════

def _block_split(doc):
    """Climatiseur split (indoor unit) — plan view: 0.90m × 0.22m rectangle
    with airflow arrows."""
    blk = doc.blocks.new(name="TJ_SPLIT")

    # Unit body
    blk.add_lwpolyline(
        [(0, 0), (0.90, 0), (0.90, 0.22), (0, 0.22)],
        close=True, dxfattribs={"layer": "M-EQUIP"})

    # Airflow arrows (3 arrows pointing down from unit)
    for ax in [0.22, 0.45, 0.68]:
        blk.add_line((ax, 0), (ax, -0.15), dxfattribs={"layer": "M-EQUIP"})
        blk.add_line((ax, -0.15), (ax - 0.04, -0.10),
                     dxfattribs={"layer": "M-EQUIP"})
        blk.add_line((ax, -0.15), (ax + 0.04, -0.10),
                     dxfattribs={"layer": "M-EQUIP"})

    # Refrigerant connections (two circles at side)
    blk.add_circle((-0.04, 0.07), 0.02, dxfattribs={"layer": "M-EQUIP"})
    blk.add_circle((-0.04, 0.15), 0.02, dxfattribs={"layer": "M-EQUIP"})

    return blk


def _block_vmc(doc):
    """Bouche VMC (extraction grille) — plan view: circle Ø0.15m with V."""
    blk = doc.blocks.new(name="TJ_VMC")
    blk.add_circle((0, 0), 0.075, dxfattribs={"layer": "M-EQUIP"})
    # Crossed lines inside (ventilation symbol)
    blk.add_line((-0.05, -0.05), (0.05, 0.05),
                 dxfattribs={"layer": "M-EQUIP"})
    blk.add_line((-0.05, 0.05), (0.05, -0.05),
                 dxfattribs={"layer": "M-EQUIP"})
    return blk


def _block_hotte(doc):
    """Hotte (kitchen hood) — plan view: trapezoid ~0.60m × 0.50m."""
    blk = doc.blocks.new(name="TJ_HOTTE")
    blk.add_lwpolyline(
        [(0.05, 0), (0.55, 0), (0.60, 0.50), (0, 0.50)],
        close=True, dxfattribs={"layer": "M-EQUIP"})
    # Extraction circle
    blk.add_circle((0.30, 0.25), 0.08, dxfattribs={"layer": "M-EQUIP"})
    return blk


# ══════════════════════════════════════════════════════════════
# BLOCK DEFINITIONS — Electrical
# ══════════════════════════════════════════════════════════════

def _block_prise(doc):
    """Prise 2P+T (power socket) — NF symbol: semicircle + line.
    Scale: ~0.08m symbol size."""
    blk = doc.blocks.new(name="TJ_PRISE")

    # Semicircle
    pts = []
    for i in range(13):
        angle = math.pi * i / 12
        x = 0.04 * math.cos(angle)
        y = 0.04 * math.sin(angle)
        pts.append((x, y))
    blk.add_lwpolyline(pts, dxfattribs={"layer": "E-POWR"})
    # Base line
    blk.add_line((-0.04, 0), (0.04, 0), dxfattribs={"layer": "E-POWR"})
    # Earth pin (vertical line)
    blk.add_line((0, 0), (0, -0.03), dxfattribs={"layer": "E-POWR"})

    return blk


def _block_interrupteur(doc):
    """Interrupteur (light switch) — NF symbol: circle + diagonal line."""
    blk = doc.blocks.new(name="TJ_INTER")
    blk.add_circle((0, 0), 0.03, dxfattribs={"layer": "E-POWR"})
    blk.add_line((0.03, 0), (0.08, 0.05), dxfattribs={"layer": "E-POWR"})
    return blk


def _block_luminaire(doc):
    """Luminaire (ceiling light) — NF symbol: circle with X."""
    blk = doc.blocks.new(name="TJ_LUMINAIRE")
    blk.add_circle((0, 0), 0.05, dxfattribs={"layer": "E-LITE"})
    blk.add_line((-0.035, -0.035), (0.035, 0.035),
                 dxfattribs={"layer": "E-LITE"})
    blk.add_line((-0.035, 0.035), (0.035, -0.035),
                 dxfattribs={"layer": "E-LITE"})
    return blk


def _block_applique(doc):
    """Applique (wall light) — NF symbol: semicircle on wall."""
    blk = doc.blocks.new(name="TJ_APPLIQUE")
    pts = []
    for i in range(13):
        angle = math.pi * i / 12
        x = 0.04 * math.cos(angle)
        y = 0.04 * math.sin(angle)
        pts.append((x, y))
    blk.add_lwpolyline(pts, dxfattribs={"layer": "E-LITE"})
    blk.add_line((-0.04, 0), (0.04, 0), dxfattribs={"layer": "E-LITE"})
    return blk


def _block_tableau_elec(doc):
    """Tableau électrique (electrical panel) — rectangle with TE label."""
    blk = doc.blocks.new(name="TJ_TABLEAU")
    blk.add_lwpolyline(
        [(0, 0), (0.40, 0), (0.40, 0.60), (0, 0.60)],
        close=True, dxfattribs={"layer": "E-POWR"})
    # TE label
    blk.add_text("TE", height=0.12, dxfattribs={
        "layer": "E-POWR", "insert": (0.08, 0.24)})
    # Lightning bolt symbol (simplified zigzag)
    blk.add_lwpolyline(
        [(0.20, 0.50), (0.15, 0.38), (0.25, 0.38), (0.20, 0.26)],
        dxfattribs={"layer": "E-POWR"})
    return blk


def _block_rj45(doc):
    """Prise RJ45 (data outlet) — NF symbol: triangle."""
    blk = doc.blocks.new(name="TJ_RJ45")
    blk.add_lwpolyline(
        [(0, 0.06), (-0.04, -0.02), (0.04, -0.02)],
        close=True, dxfattribs={"layer": "E-LCCR"})
    blk.add_text("D", height=0.03, dxfattribs={
        "layer": "E-LCCR", "insert": (-0.01, -0.01)})
    return blk


def _block_prise_tv(doc):
    """Prise TV — NF symbol: triangle with TV."""
    blk = doc.blocks.new(name="TJ_TV")
    blk.add_lwpolyline(
        [(0, 0.06), (-0.04, -0.02), (0.04, -0.02)],
        close=True, dxfattribs={"layer": "E-LCCR"})
    blk.add_text("TV", height=0.025, dxfattribs={
        "layer": "E-LCCR", "insert": (-0.015, -0.01)})
    return blk


# ══════════════════════════════════════════════════════════════
# BLOCK DEFINITIONS — Fire Safety
# ══════════════════════════════════════════════════════════════

def _block_sprinkler(doc):
    """Sprinkler head — NF symbol: circle with cross + S."""
    blk = doc.blocks.new(name="TJ_SPK")
    blk.add_circle((0, 0), 0.05, dxfattribs={"layer": "F-SPKL"})
    blk.add_line((-0.05, 0), (0.05, 0), dxfattribs={"layer": "F-SPKL"})
    blk.add_line((0, -0.05), (0, 0.05), dxfattribs={"layer": "F-SPKL"})
    return blk


def _block_detecteur_fumee(doc):
    """Détecteur de fumée — NF symbol: circle with DF."""
    blk = doc.blocks.new(name="TJ_DF")
    blk.add_circle((0, 0), 0.04, dxfattribs={"layer": "F-DETECT"})
    blk.add_text("DF", height=0.03, dxfattribs={
        "layer": "F-DETECT", "insert": (-0.02, -0.015)})
    return blk


def _block_detecteur_chaleur(doc):
    """Détecteur de chaleur — NF symbol: circle with DC."""
    blk = doc.blocks.new(name="TJ_DC")
    blk.add_circle((0, 0), 0.04, dxfattribs={"layer": "F-DETECT"})
    blk.add_text("DC", height=0.03, dxfattribs={
        "layer": "F-DETECT", "insert": (-0.02, -0.015)})
    return blk


def _block_ria(doc):
    """RIA (Robinet d'incendie armé) — circle with RIA text."""
    blk = doc.blocks.new(name="TJ_RIA")
    blk.add_circle((0, 0), 0.08, dxfattribs={"layer": "F-SPKL"})
    blk.add_circle((0, 0), 0.06, dxfattribs={"layer": "F-SPKL"})
    blk.add_text("RIA", height=0.04, dxfattribs={
        "layer": "F-SPKL", "insert": (-0.05, -0.02)})
    return blk


# ══════════════════════════════════════════════════════════════
# BLOCK DEFINITIONS — Doors & Windows
# ══════════════════════════════════════════════════════════════

def _block_door(doc, width: float = 0.83, name: str = "TJ_DOOR"):
    """Standard door — plan view: line + 90° arc (swing)."""
    blk = doc.blocks.new(name=name)

    # Door leaf (closed position along wall)
    blk.add_line((0, 0), (width, 0), dxfattribs={"layer": "A-DOOR"})

    # Swing arc (90 degrees)
    blk.add_arc((0, 0), width, 0, 90, dxfattribs={"layer": "A-DOOR"})

    # Hinge point
    blk.add_circle((0, 0), 0.02, dxfattribs={"layer": "A-DOOR"})

    return blk


def _block_window(doc, width: float = 1.20, name: str = "TJ_WINDOW"):
    """Standard window — plan view: double line in wall."""
    blk = doc.blocks.new(name=name)

    # Window in wall — two parallel lines
    blk.add_line((0, -0.03), (width, -0.03), dxfattribs={"layer": "A-GLAZ"})
    blk.add_line((0, 0.03), (width, 0.03), dxfattribs={"layer": "A-GLAZ"})
    # Glass line (center)
    blk.add_line((0, 0), (width, 0), dxfattribs={"layer": "A-GLAZ"})

    return blk


# ══════════════════════════════════════════════════════════════
# EQUIPMENT TYPE → BLOCK NAME MAPPING
# ══════════════════════════════════════════════════════════════

from bim_model import EquipmentType

EQUIP_BLOCK_MAP = {
    EquipmentType.WC_UNIT: "TJ_WC",
    EquipmentType.LAVABO: "TJ_LAVABO",
    EquipmentType.DOUCHE: "TJ_DOUCHE",
    EquipmentType.EVIER: "TJ_EVIER",
    EquipmentType.BAIGNOIRE: "TJ_BAIGNOIRE",
    EquipmentType.CHAUFFE_EAU: "TJ_CHAUFFE_EAU",
    EquipmentType.LAVE_LINGE: "TJ_LAVE_LINGE",
    EquipmentType.CLIMATISEUR: "TJ_SPLIT",
    EquipmentType.BOUCHE_VMC: "TJ_VMC",
    EquipmentType.HOTTE: "TJ_HOTTE",
    EquipmentType.PRISE: "TJ_PRISE",
    EquipmentType.PRISE_PLAN_TRAVAIL: "TJ_PRISE",
    EquipmentType.PRISE_ETANCHE: "TJ_PRISE",
    EquipmentType.INTERRUPTEUR: "TJ_INTER",
    EquipmentType.LUMINAIRE: "TJ_LUMINAIRE",
    EquipmentType.APPLIQUE: "TJ_APPLIQUE",
    EquipmentType.TABLEAU_ELEC: "TJ_TABLEAU",
    EquipmentType.PRISE_RJ45: "TJ_RJ45",
    EquipmentType.PRISE_TV: "TJ_TV",
    EquipmentType.DETECTEUR_FUMEE: "TJ_DF",
    EquipmentType.DETECTEUR_CHALEUR: "TJ_DC",
    EquipmentType.SPRINKLER: "TJ_SPK",
    EquipmentType.RIA: "TJ_RIA",
}

# Equipment type → layer
EQUIP_LAYER_MAP = {
    EquipmentType.WC_UNIT: "P-FIXT",
    EquipmentType.LAVABO: "P-FIXT",
    EquipmentType.DOUCHE: "P-FIXT",
    EquipmentType.EVIER: "P-FIXT",
    EquipmentType.BAIGNOIRE: "P-FIXT",
    EquipmentType.CHAUFFE_EAU: "P-FIXT",
    EquipmentType.LAVE_LINGE: "P-FIXT",
    EquipmentType.CLIMATISEUR: "M-EQUIP",
    EquipmentType.BOUCHE_VMC: "M-EQUIP",
    EquipmentType.HOTTE: "M-EQUIP",
    EquipmentType.PRISE: "E-POWR",
    EquipmentType.PRISE_PLAN_TRAVAIL: "E-POWR",
    EquipmentType.PRISE_ETANCHE: "E-POWR",
    EquipmentType.INTERRUPTEUR: "E-POWR",
    EquipmentType.LUMINAIRE: "E-LITE",
    EquipmentType.APPLIQUE: "E-LITE",
    EquipmentType.TABLEAU_ELEC: "E-POWR",
    EquipmentType.PRISE_RJ45: "E-LCCR",
    EquipmentType.PRISE_TV: "E-LCCR",
    EquipmentType.DETECTEUR_FUMEE: "F-DETECT",
    EquipmentType.DETECTEUR_CHALEUR: "F-DETECT",
    EquipmentType.SPRINKLER: "F-SPKL",
    EquipmentType.RIA: "F-SPKL",
}

# Network type → layer
from bim_model import NetworkType

NETWORK_LAYER_MAP = {
    NetworkType.PLU_EF: "P-PIPE-EF",
    NetworkType.PLU_EC: "P-PIPE-EC",
    NetworkType.PLU_EU: "P-PIPE-EU",
    NetworkType.PLU_EP: "P-PIPE-EU",
    NetworkType.HVC_SOUFFLAGE: "M-DUCT",
    NetworkType.HVC_REPRISE: "M-DUCT",
    NetworkType.HVC_VMC: "M-DUCT",
    NetworkType.HVC_REF: "M-EQUIP",
    NetworkType.HVC_CONDENSAT: "M-EQUIP",
    NetworkType.ELEC_FORT: "E-POWR",
    NetworkType.ELEC_FAIBLE: "E-LCCR",
    NetworkType.FIRE_SPK: "F-SPKL",
    NetworkType.FIRE_DETECT: "F-DETECT",
}


# ══════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════

_BLOCK_BUILDERS = [
    _block_wc,
    _block_lavabo,
    _block_douche,
    _block_evier,
    _block_baignoire,
    _block_chauffe_eau,
    _block_lave_linge,
    _block_split,
    _block_vmc,
    _block_hotte,
    _block_prise,
    _block_interrupteur,
    _block_luminaire,
    _block_applique,
    _block_tableau_elec,
    _block_rj45,
    _block_prise_tv,
    _block_sprinkler,
    _block_detecteur_fumee,
    _block_detecteur_chaleur,
    _block_ria,
    _block_door,
    _block_window,
]


def register_all_blocks(doc) -> int:
    """Register all MEP blocks and layers in a DXF document.

    Call this once after creating the document, before inserting any blocks.
    Returns number of blocks registered.
    """
    setup_layers(doc)

    count = 0
    for builder in _BLOCK_BUILDERS:
        try:
            builder(doc)
            count += 1
        except Exception as e:
            logger.warning("Failed to create block: %s", e)

    logger.info("Registered %d MEP blocks + %d layers", count, len(LAYERS))
    return count
