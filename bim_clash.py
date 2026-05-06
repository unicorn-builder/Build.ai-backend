"""
bim_clash.py — Clash detection between MEP trades

Detects spatial conflicts between network segments and equipment from
different trades in a TijanBIM Building model.

Clash types:
  - HARD: Physical intersection (two segments crossing in the same zone)
  - SOFT: Clearance violation (segments too close, no maintenance access)
  - CROSSING: Vertical pipes/ducts crossing horizontal runs at same height

Rules are based on French DTU norms and standard BET practice:
  - Min 50mm between parallel pipes of different trades
  - Min 100mm between electrical and plumbing
  - Min 200mm between HVAC ducts and other trades
  - Sprinkler heads must be 150mm min from walls/ducts
  - No electrical runs above plumbing without protection

Output: list of Clash objects that feed into coordination plans and reports.
"""
from __future__ import annotations
import math
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple, Set

from bim_model import (
    Building, Level, Room, NetworkSegment, EquipmentInstance,
    NetworkType, EquipmentType, Point, Point3D,
)

logger = logging.getLogger("tijan.clash")


# ══════════════════════════════════════════════════════════════
# ENUMS & TYPES
# ══════════════════════════════════════════════════════════════

class ClashSeverity(Enum):
    HARD = "hard"           # Physical intersection — must fix
    SOFT = "soft"           # Clearance violation — should fix
    CROSSING = "crossing"   # Crossing at same height — verify coordination


class ClashCategory(Enum):
    PLU_VS_ELEC = "plu_vs_elec"       # Plumbing vs electrical
    PLU_VS_HVC = "plu_vs_hvc"         # Plumbing vs HVAC
    HVC_VS_ELEC = "hvc_vs_elec"       # HVAC vs electrical
    FIRE_VS_PLU = "fire_vs_plu"       # Fire safety vs plumbing
    FIRE_VS_HVC = "fire_vs_hvc"       # Fire safety vs HVAC
    FIRE_VS_ELEC = "fire_vs_elec"     # Fire safety vs electrical
    PLU_VS_PLU = "plu_vs_plu"         # Intra-plumbing (EF vs EU proximity)
    HVC_VS_HVC = "hvc_vs_hvc"         # Intra-HVAC
    EQUIP_VS_NET = "equip_vs_net"     # Equipment vs network segment
    STR_VS_NET = "str_vs_net"         # Structural element vs network


# ══════════════════════════════════════════════════════════════
# CLEARANCE RULES (mm) — DTU norms
# ══════════════════════════════════════════════════════════════

# Minimum clearance in mm between network types
_CLEARANCE_RULES: Dict[Tuple[str, str], float] = {
    # Plumbing vs Electrical — 100mm minimum
    ("plu", "elec"): 100.0,
    # HVAC vs any other — 200mm minimum (duct maintenance)
    ("hvc", "plu"): 200.0,
    ("hvc", "elec"): 150.0,
    # Fire vs other — 150mm minimum (sprinkler clearance)
    ("fire", "plu"): 150.0,
    ("fire", "hvc"): 200.0,
    ("fire", "elec"): 150.0,
    # Same trade — 50mm minimum
    ("plu", "plu"): 50.0,
    ("hvc", "hvc"): 100.0,
    ("elec", "elec"): 30.0,
    ("fire", "fire"): 100.0,
}


def _get_trade(net_type: NetworkType) -> str:
    """Extract trade group from NetworkType."""
    name = net_type.value
    if name.startswith("plu"):
        return "plu"
    elif name.startswith("hvc"):
        return "hvc"
    elif name.startswith("elec"):
        return "elec"
    elif name.startswith("fire"):
        return "fire"
    return "other"


def _get_clearance(trade_a: str, trade_b: str) -> float:
    """Get minimum clearance in mm between two trades."""
    key = (min(trade_a, trade_b), max(trade_a, trade_b))
    if key in _CLEARANCE_RULES:
        return _CLEARANCE_RULES[key]
    # Reversed key
    key_rev = (key[1], key[0])
    if key_rev in _CLEARANCE_RULES:
        return _CLEARANCE_RULES[key_rev]
    return 50.0  # Default 50mm


def _category_from_trades(trade_a: str, trade_b: str) -> ClashCategory:
    """Determine clash category from two trade codes."""
    pair = frozenset([trade_a, trade_b])
    mapping = {
        frozenset(["plu", "elec"]): ClashCategory.PLU_VS_ELEC,
        frozenset(["plu", "hvc"]): ClashCategory.PLU_VS_HVC,
        frozenset(["hvc", "elec"]): ClashCategory.HVC_VS_ELEC,
        frozenset(["fire", "plu"]): ClashCategory.FIRE_VS_PLU,
        frozenset(["fire", "hvc"]): ClashCategory.FIRE_VS_HVC,
        frozenset(["fire", "elec"]): ClashCategory.FIRE_VS_ELEC,
        frozenset(["plu"]): ClashCategory.PLU_VS_PLU,
        frozenset(["hvc"]): ClashCategory.HVC_VS_HVC,
    }
    return mapping.get(pair, ClashCategory.PLU_VS_ELEC)


# ══════════════════════════════════════════════════════════════
# CLASH DATA
# ══════════════════════════════════════════════════════════════

@dataclass
class Clash:
    """A detected clash between two BIM elements."""
    severity: ClashSeverity
    category: ClashCategory
    level_name: str                     # Which floor
    room_name: str = ""                 # Which room (if identifiable)

    # Elements involved
    element_a_id: str = ""
    element_a_type: str = ""            # e.g. "PLU_EF pipe 25mm"
    element_b_id: str = ""
    element_b_type: str = ""            # e.g. "ELEC_FORT cable"

    # Clash location
    location: Optional[Point] = None    # 2D location on plan
    location_3d: Optional[Point3D] = None
    distance_mm: float = 0.0            # Actual distance between elements
    required_mm: float = 0.0            # Required minimum clearance

    # Resolution
    description: str = ""               # Human-readable description
    suggestion: str = ""                # Suggested fix

    def __repr__(self):
        return (f"Clash({self.severity.value}: {self.element_a_type} vs "
                f"{self.element_b_type} @ {self.level_name}/"
                f"{self.room_name} — {self.distance_mm:.0f}mm < "
                f"{self.required_mm:.0f}mm)")


@dataclass
class ClashReport:
    """Summary of all clashes in a building."""
    building_name: str
    total_clashes: int = 0
    hard_count: int = 0
    soft_count: int = 0
    crossing_count: int = 0
    clashes: List[Clash] = field(default_factory=list)
    by_level: Dict[str, List[Clash]] = field(default_factory=dict)
    by_category: Dict[str, List[Clash]] = field(default_factory=dict)
    by_severity: Dict[str, List[Clash]] = field(default_factory=dict)

    def summary_text(self, lang: str = "fr") -> str:
        """Generate a human-readable summary."""
        if lang == "en":
            lines = [
                f"CLASH REPORT — {self.building_name}",
                f"Total clashes: {self.total_clashes}",
                f"  Hard (must fix): {self.hard_count}",
                f"  Soft (clearance): {self.soft_count}",
                f"  Crossings (verify): {self.crossing_count}",
                "",
            ]
            for level_name, level_clashes in sorted(self.by_level.items()):
                lines.append(f"Level {level_name}: {len(level_clashes)} clash(es)")
                for c in level_clashes[:5]:
                    lines.append(f"  - [{c.severity.value.upper()}] "
                                 f"{c.element_a_type} vs {c.element_b_type}: "
                                 f"{c.description}")
                if len(level_clashes) > 5:
                    lines.append(f"  ... and {len(level_clashes) - 5} more")
        else:
            lines = [
                f"RAPPORT DE CLASHS — {self.building_name}",
                f"Total des conflits: {self.total_clashes}",
                f"  Critiques (à corriger): {self.hard_count}",
                f"  Dégagements insuffisants: {self.soft_count}",
                f"  Croisements (à vérifier): {self.crossing_count}",
                "",
            ]
            for level_name, level_clashes in sorted(self.by_level.items()):
                lines.append(f"Niveau {level_name}: "
                             f"{len(level_clashes)} conflit(s)")
                for c in level_clashes[:5]:
                    lines.append(f"  - [{c.severity.value.upper()}] "
                                 f"{c.element_a_type} vs {c.element_b_type}: "
                                 f"{c.description}")
                if len(level_clashes) > 5:
                    lines.append(f"  ... et {len(level_clashes) - 5} de plus")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# GEOMETRY HELPERS
# ══════════════════════════════════════════════════════════════

def _seg_to_2d(seg: NetworkSegment) -> Tuple[Point, Point]:
    """Project a 3D network segment to 2D plan view."""
    return Point(seg.start.x, seg.start.y), Point(seg.end.x, seg.end.y)


def _seg_midpoint_2d(seg: NetworkSegment) -> Point:
    """2D midpoint of a segment."""
    return Point((seg.start.x + seg.end.x) / 2,
                 (seg.start.y + seg.end.y) / 2)


def _seg_midpoint_3d(seg: NetworkSegment) -> Point3D:
    """3D midpoint of a segment."""
    return Point3D((seg.start.x + seg.end.x) / 2,
                   (seg.start.y + seg.end.y) / 2,
                   (seg.start.z + seg.end.z) / 2)


def _point_to_segment_dist_2d(px: float, py: float,
                               ax: float, ay: float,
                               bx: float, by: float) -> float:
    """Minimum distance from point (px,py) to segment (ax,ay)-(bx,by)."""
    dx, dy = bx - ax, by - ay
    len_sq = dx * dx + dy * dy
    if len_sq < 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / len_sq))
    proj_x = ax + t * dx
    proj_y = ay + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def _segment_to_segment_dist_2d(a_start: Point, a_end: Point,
                                  b_start: Point, b_end: Point) -> float:
    """Minimum distance between two 2D line segments."""
    # Check all 4 point-to-segment distances and take minimum
    d1 = _point_to_segment_dist_2d(a_start.x, a_start.y,
                                    b_start.x, b_start.y,
                                    b_end.x, b_end.y)
    d2 = _point_to_segment_dist_2d(a_end.x, a_end.y,
                                    b_start.x, b_start.y,
                                    b_end.x, b_end.y)
    d3 = _point_to_segment_dist_2d(b_start.x, b_start.y,
                                    a_start.x, a_start.y,
                                    a_end.x, a_end.y)
    d4 = _point_to_segment_dist_2d(b_end.x, b_end.y,
                                    a_start.x, a_start.y,
                                    a_end.x, a_end.y)
    min_d = min(d1, d2, d3, d4)

    # Also check if segments actually intersect (distance = 0)
    if _segments_intersect_2d(a_start, a_end, b_start, b_end):
        return 0.0

    return min_d


def _cross_2d(o: Point, a: Point, b: Point) -> float:
    """2D cross product of vectors OA and OB."""
    return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)


def _segments_intersect_2d(a1: Point, a2: Point,
                            b1: Point, b2: Point) -> bool:
    """Check if two 2D segments intersect (proper or improper)."""
    d1 = _cross_2d(b1, b2, a1)
    d2 = _cross_2d(b1, b2, a2)
    d3 = _cross_2d(a1, a2, b1)
    d4 = _cross_2d(a1, a2, b2)

    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
       ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
        return True

    # Collinear cases
    eps = 1e-9
    if abs(d1) < eps and _on_segment(b1, a1, b2):
        return True
    if abs(d2) < eps and _on_segment(b1, a2, b2):
        return True
    if abs(d3) < eps and _on_segment(a1, b1, a2):
        return True
    if abs(d4) < eps and _on_segment(a1, b2, a2):
        return True

    return False


def _on_segment(p: Point, q: Point, r: Point) -> bool:
    """Check if q lies on segment pr."""
    return (min(p.x, r.x) <= q.x + 1e-9 <= max(p.x, r.x) + 1e-9 and
            min(p.y, r.y) <= q.y + 1e-9 <= max(p.y, r.y) + 1e-9)


def _z_overlap(seg_a: NetworkSegment, seg_b: NetworkSegment,
               tolerance_m: float = 0.15) -> bool:
    """Check if two segments overlap in the Z axis (same height zone)."""
    a_z_min = min(seg_a.start.z, seg_a.end.z) - tolerance_m
    a_z_max = max(seg_a.start.z, seg_a.end.z) + tolerance_m
    b_z_min = min(seg_b.start.z, seg_b.end.z) - tolerance_m
    b_z_max = max(seg_b.start.z, seg_b.end.z) + tolerance_m
    return a_z_max >= b_z_min and b_z_max >= a_z_min


# ══════════════════════════════════════════════════════════════
# SEGMENT DESCRIPTION
# ══════════════════════════════════════════════════════════════

_NET_TYPE_LABELS_FR = {
    NetworkType.PLU_EF: "Eau Froide",
    NetworkType.PLU_EC: "Eau Chaude",
    NetworkType.PLU_EU: "Eaux Usées",
    NetworkType.PLU_EP: "Eaux Pluviales",
    NetworkType.HVC_SOUFFLAGE: "Soufflage HVAC",
    NetworkType.HVC_REPRISE: "Reprise HVAC",
    NetworkType.HVC_VMC: "VMC Extraction",
    NetworkType.HVC_REF: "Réfrigérant",
    NetworkType.HVC_CONDENSAT: "Condensat",
    NetworkType.ELEC_FORT: "Courant Fort",
    NetworkType.ELEC_FAIBLE: "Courant Faible",
    NetworkType.FIRE_SPK: "Sprinkler",
    NetworkType.FIRE_DETECT: "Détection Incendie",
}


def _describe_segment(seg: NetworkSegment, lang: str = "fr") -> str:
    """Human label for a network segment."""
    if lang == "fr":
        label = _NET_TYPE_LABELS_FR.get(seg.type, seg.type.value)
    else:
        label = seg.type.value.upper().replace("_", " ")
    return f"{label} Ø{seg.diameter_mm:.0f}mm"


# ══════════════════════════════════════════════════════════════
# CLASH DETECTION ENGINE
# ══════════════════════════════════════════════════════════════

def _collect_all_segments(level: Level) -> List[NetworkSegment]:
    """Gather all network segments on a level (rooms + level risers)."""
    segments = list(level.network_segments)  # Level risers
    for room in level.rooms:
        segments.extend(room.network_segments)
    return segments


def _detect_segment_clashes(segments: List[NetworkSegment],
                             level_name: str,
                             rooms: List[Room],
                             lang: str = "fr") -> List[Clash]:
    """Detect clashes between all pairs of segments on a level."""
    clashes = []
    n = len(segments)
    if n < 2:
        return clashes

    # Build room lookup for segment → room name
    seg_room: Dict[str, str] = {}
    for room in rooms:
        for seg in room.network_segments:
            seg_room[seg.id] = room.name or room.label or room.type.value

    for i in range(n):
        seg_a = segments[i]
        trade_a = _get_trade(seg_a.type)

        for j in range(i + 1, n):
            seg_b = segments[j]
            trade_b = _get_trade(seg_b.type)

            # Skip if both are vertical risers (they're stacked, not clashing)
            if seg_a.is_vertical and seg_b.is_vertical:
                continue

            # Check Z overlap — segments at different heights don't clash
            if not _z_overlap(seg_a, seg_b):
                continue

            # Compute 2D distance
            a_start_2d, a_end_2d = _seg_to_2d(seg_a)
            b_start_2d, b_end_2d = _seg_to_2d(seg_b)
            dist_m = _segment_to_segment_dist_2d(
                a_start_2d, a_end_2d, b_start_2d, b_end_2d)
            dist_mm = dist_m * 1000.0

            # Get required clearance
            required_mm = _get_clearance(trade_a, trade_b)

            # Account for pipe diameters (center-to-center distance includes radii)
            effective_gap_mm = dist_mm - (seg_a.diameter_mm + seg_b.diameter_mm) / 2

            if effective_gap_mm >= required_mm:
                continue  # No clash

            # Determine severity
            if dist_mm < 1.0:  # Essentially intersecting
                severity = ClashSeverity.HARD
            elif trade_a != trade_b and effective_gap_mm < 0:
                severity = ClashSeverity.HARD
            elif (seg_a.is_vertical != seg_b.is_vertical):
                severity = ClashSeverity.CROSSING
            else:
                severity = ClashSeverity.SOFT

            # Location: midpoint of the closer pair
            location = Point((a_start_2d.x + b_start_2d.x) / 2,
                              (a_start_2d.y + b_start_2d.y) / 2)

            # Room
            room_a = seg_room.get(seg_a.id, "")
            room_b = seg_room.get(seg_b.id, "")
            room_name = room_a or room_b

            # Description
            desc_a = _describe_segment(seg_a, lang)
            desc_b = _describe_segment(seg_b, lang)

            if lang == "fr":
                if severity == ClashSeverity.HARD:
                    desc = (f"Intersection physique entre {desc_a} et {desc_b} "
                            f"(distance {effective_gap_mm:.0f}mm)")
                    suggestion = ("Décaler un des réseaux ou modifier le "
                                  "tracé pour éviter le croisement")
                elif severity == ClashSeverity.CROSSING:
                    desc = (f"Croisement {desc_a} / {desc_b} à la même "
                            f"hauteur (dégagement {effective_gap_mm:.0f}mm "
                            f"< {required_mm:.0f}mm requis)")
                    suggestion = ("Vérifier la coordination des hauteurs "
                                  "de passage au droit du croisement")
                else:
                    desc = (f"Dégagement insuffisant entre {desc_a} et "
                            f"{desc_b}: {effective_gap_mm:.0f}mm "
                            f"< {required_mm:.0f}mm requis")
                    suggestion = ("Augmenter l'espacement entre les deux "
                                  "réseaux ou modifier le tracé")
            else:
                if severity == ClashSeverity.HARD:
                    desc = (f"Physical intersection between {desc_a} and "
                            f"{desc_b} (distance {effective_gap_mm:.0f}mm)")
                    suggestion = ("Offset one network or reroute to avoid "
                                  "the crossing")
                elif severity == ClashSeverity.CROSSING:
                    desc = (f"Crossing {desc_a} / {desc_b} at same height "
                            f"(gap {effective_gap_mm:.0f}mm < "
                            f"{required_mm:.0f}mm required)")
                    suggestion = ("Verify height coordination at the "
                                  "crossing point")
                else:
                    desc = (f"Insufficient clearance between {desc_a} and "
                            f"{desc_b}: {effective_gap_mm:.0f}mm "
                            f"< {required_mm:.0f}mm required")
                    suggestion = ("Increase spacing between networks or "
                                  "modify routing")

            clash = Clash(
                severity=severity,
                category=_category_from_trades(trade_a, trade_b),
                level_name=level_name,
                room_name=room_name,
                element_a_id=seg_a.id,
                element_a_type=desc_a,
                element_b_id=seg_b.id,
                element_b_type=desc_b,
                location=location,
                location_3d=_seg_midpoint_3d(seg_a),
                distance_mm=effective_gap_mm,
                required_mm=required_mm,
                description=desc,
                suggestion=suggestion,
            )
            clashes.append(clash)

    return clashes


def _detect_equipment_vs_network(segments: List[NetworkSegment],
                                  rooms: List[Room],
                                  level_name: str,
                                  lang: str = "fr") -> List[Clash]:
    """Detect clashes between equipment and network segments.

    Rules:
    - Sprinkler heads need 150mm clearance from ducts/pipes
    - Electrical panels need 600mm clear zone in front
    - Climatiseurs need 200mm clearance from plumbing
    """
    clashes = []

    # Equipment clearance rules (equipment_type → min distance from networks in mm)
    _EQUIP_CLEARANCE = {
        EquipmentType.SPRINKLER: 150.0,
        EquipmentType.TABLEAU_ELEC: 300.0,
        EquipmentType.CLIMATISEUR: 200.0,
        EquipmentType.CHAUFFE_EAU: 150.0,
        EquipmentType.CDI: 200.0,
    }

    for room in rooms:
        for equip in room.equipment:
            min_clear = _EQUIP_CLEARANCE.get(equip.type)
            if min_clear is None:
                continue

            eq_trade = "fire" if equip.type in (
                EquipmentType.SPRINKLER, EquipmentType.CDI,
                EquipmentType.SIRENE
            ) else "elec" if equip.type in (
                EquipmentType.TABLEAU_ELEC, EquipmentType.PRISE
            ) else "hvc" if equip.type == EquipmentType.CLIMATISEUR else "plu"

            for seg in segments:
                seg_trade = _get_trade(seg.type)
                # Skip same trade (e.g. sprinkler vs sprinkler pipe is OK)
                if seg_trade == eq_trade:
                    continue

                # Distance from equipment position to segment
                a_2d, b_2d = _seg_to_2d(seg)
                dist_m = _point_to_segment_dist_2d(
                    equip.position.x, equip.position.y,
                    a_2d.x, a_2d.y, b_2d.x, b_2d.y)
                dist_mm = dist_m * 1000.0

                if dist_mm >= min_clear:
                    continue

                desc_seg = _describe_segment(seg, lang)
                eq_label = equip.type.value.upper()

                if lang == "fr":
                    desc = (f"{eq_label} trop proche de {desc_seg}: "
                            f"{dist_mm:.0f}mm < {min_clear:.0f}mm requis")
                    suggestion = (f"Déplacer le {eq_label} ou modifier le "
                                  f"tracé de {desc_seg}")
                else:
                    desc = (f"{eq_label} too close to {desc_seg}: "
                            f"{dist_mm:.0f}mm < {min_clear:.0f}mm required")
                    suggestion = (f"Move {eq_label} or reroute {desc_seg}")

                clashes.append(Clash(
                    severity=ClashSeverity.SOFT,
                    category=ClashCategory.EQUIP_VS_NET,
                    level_name=level_name,
                    room_name=room.name or room.label,
                    element_a_id=equip.id,
                    element_a_type=eq_label,
                    element_b_id=seg.id,
                    element_b_type=desc_seg,
                    location=equip.position,
                    distance_mm=dist_mm,
                    required_mm=min_clear,
                    description=desc,
                    suggestion=suggestion,
                ))

    return clashes


def _detect_structural_clashes(segments: List[NetworkSegment],
                                level: Level,
                                lang: str = "fr") -> List[Clash]:
    """Detect network segments crossing structural walls.

    Load-bearing walls and facades cannot have unplanned penetrations.
    Pipes/ducts should cross through planned sleeves.
    """
    from bim_model import WallType
    clashes = []

    # Only check bearing walls and facades
    structural_walls = [w for w in level.walls
                        if w.type in (WallType.PORTEUR, WallType.FACADE)]

    for seg in segments:
        if seg.is_vertical:
            continue  # Vertical risers have planned penetrations

        a_2d, b_2d = _seg_to_2d(seg)

        for wall in structural_walls:
            if _segments_intersect_2d(a_2d, b_2d, wall.start, wall.end):
                desc_seg = _describe_segment(seg, lang)
                wall_label = (f"Mur {wall.type.value} ({wall.length_m:.1f}m)"
                              if lang == "fr" else
                              f"{wall.type.value} wall ({wall.length_m:.1f}m)")

                if lang == "fr":
                    desc = (f"{desc_seg} traverse un mur "
                            f"{wall.type.value} sans réservation")
                    suggestion = ("Prévoir une réservation (fourreau) dans "
                                  "le mur porteur ou modifier le tracé")
                else:
                    desc = (f"{desc_seg} crosses a {wall.type.value} wall "
                            f"without a planned sleeve")
                    suggestion = ("Plan a sleeve in the structural wall or "
                                  "modify the route")

                clashes.append(Clash(
                    severity=ClashSeverity.HARD,
                    category=ClashCategory.STR_VS_NET,
                    level_name=level.name,
                    room_name="",
                    element_a_id=seg.id,
                    element_a_type=desc_seg,
                    element_b_id=wall.id,
                    element_b_type=wall_label,
                    location=wall.midpoint,
                    distance_mm=0.0,
                    required_mm=0.0,
                    description=desc,
                    suggestion=suggestion,
                ))

    return clashes


# ══════════════════════════════════════════════════════════════
# SPECIAL RULES
# ══════════════════════════════════════════════════════════════

def _detect_elec_above_plumbing(segments: List[NetworkSegment],
                                 level_name: str,
                                 lang: str = "fr") -> List[Clash]:
    """Detect electrical runs above plumbing without protection.

    NF C 15-100: electrical cables must not pass above plumbing pipes
    without a protective device (goulotte, séparation physique).
    """
    clashes = []

    plu_segs = [s for s in segments
                if _get_trade(s.type) == "plu" and not s.is_vertical]
    elec_segs = [s for s in segments
                 if _get_trade(s.type) == "elec" and not s.is_vertical]

    for elec in elec_segs:
        elec_z = (elec.start.z + elec.end.z) / 2
        for plu in plu_segs:
            plu_z = (plu.start.z + plu.end.z) / 2
            # Electrical ABOVE plumbing
            if elec_z <= plu_z:
                continue

            # Check if they overlap in 2D plan
            e_start, e_end = _seg_to_2d(elec)
            p_start, p_end = _seg_to_2d(plu)
            dist_m = _segment_to_segment_dist_2d(
                e_start, e_end, p_start, p_end)

            if dist_m > 0.5:  # More than 50cm apart in plan = OK
                continue

            desc_e = _describe_segment(elec, lang)
            desc_p = _describe_segment(plu, lang)

            if lang == "fr":
                desc = (f"{desc_e} passe au-dessus de {desc_p} "
                        f"sans protection (NF C 15-100)")
                suggestion = ("Ajouter une goulotte de protection ou "
                              "inverser les positions verticales")
            else:
                desc = (f"{desc_e} runs above {desc_p} without "
                        f"protection (NF C 15-100)")
                suggestion = ("Add protective trunking or swap "
                              "vertical positions")

            clashes.append(Clash(
                severity=ClashSeverity.SOFT,
                category=ClashCategory.PLU_VS_ELEC,
                level_name=level_name,
                room_name="",
                element_a_id=elec.id,
                element_a_type=desc_e,
                element_b_id=plu.id,
                element_b_type=desc_p,
                location=_seg_midpoint_2d(elec),
                distance_mm=dist_m * 1000,
                required_mm=0.0,
                description=desc,
                suggestion=suggestion,
            ))

    return clashes


# ══════════════════════════════════════════════════════════════
# MAIN API
# ══════════════════════════════════════════════════════════════

def detect_clashes(building: Building,
                   lang: str = "fr") -> ClashReport:
    """Run full clash detection on a Building model.

    Checks:
    1. Segment-to-segment clearance violations (all trade pairs)
    2. Equipment-to-network proximity violations
    3. Network-through-structural-wall violations
    4. Electrical-above-plumbing (NF C 15-100)

    Returns a ClashReport with all findings organized by level,
    category, and severity.
    """
    all_clashes: List[Clash] = []

    for level in building.levels:
        segments = _collect_all_segments(level)
        if not segments:
            continue

        level_name = level.name

        # 1. Segment vs segment
        seg_clashes = _detect_segment_clashes(
            segments, level_name, level.rooms, lang)
        all_clashes.extend(seg_clashes)

        # 2. Equipment vs network
        eq_clashes = _detect_equipment_vs_network(
            segments, level.rooms, level_name, lang)
        all_clashes.extend(eq_clashes)

        # 3. Network vs structure
        str_clashes = _detect_structural_clashes(
            segments, level, lang)
        all_clashes.extend(str_clashes)

        # 4. Electrical above plumbing
        elec_plu = _detect_elec_above_plumbing(
            segments, level_name, lang)
        all_clashes.extend(elec_plu)

        logger.info("Level %s: %d segments → %d clashes",
                     level_name,
                     len(segments),
                     len(seg_clashes) + len(eq_clashes) +
                     len(str_clashes) + len(elec_plu))

    # Build report
    report = ClashReport(
        building_name=building.name,
        total_clashes=len(all_clashes),
        hard_count=sum(1 for c in all_clashes
                       if c.severity == ClashSeverity.HARD),
        soft_count=sum(1 for c in all_clashes
                       if c.severity == ClashSeverity.SOFT),
        crossing_count=sum(1 for c in all_clashes
                          if c.severity == ClashSeverity.CROSSING),
        clashes=all_clashes,
    )

    # Index by level
    for c in all_clashes:
        report.by_level.setdefault(c.level_name, []).append(c)
        report.by_category.setdefault(c.category.value, []).append(c)
        report.by_severity.setdefault(c.severity.value, []).append(c)

    logger.info("Clash detection complete: %d total (%d hard, %d soft, "
                "%d crossing)",
                report.total_clashes, report.hard_count,
                report.soft_count, report.crossing_count)

    return report
