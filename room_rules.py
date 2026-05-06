"""
room_rules.py — Room type equipment rules for TijanBIM

Defines WHAT equipment each room type requires and HOW it should be placed.
This is the intelligence layer that prevents:
  - Climatiseur in WC/couloirs
  - Prises floating in space (not on walls)
  - Toilets without water supply
  - Missing VMC extraction in wet rooms

These rules are used by Phase 2 MEP routers to populate rooms with equipment.
All placement rules reference physical wall faces, not abstract grid positions.

Standards: NF C 15-100 (electrical), DTU 60.11 (plumbing), IT 246 (fire safety)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from bim_model import (
    RoomType, EquipmentType, PlacementType, NetworkType, WallType,
    Room, Wall, EquipmentInstance, Point
)


# ══════════════════════════════════════════════════════════════
# EQUIPMENT RULE DEFINITION
# ══════════════════════════════════════════════════════════════

@dataclass
class EquipmentRule:
    """Specifies one piece of equipment to place in a room."""
    equipment_type: EquipmentType
    placement: PlacementType
    quantity: int = 1                # How many instances
    height_m: float = 0.3           # Installation height above floor
    min_room_area_m2: float = 0.0   # Only place if room is large enough
    prefer_wall_type: Optional[str] = None  # "exterior" / "interior" / None
    label_fr: str = ""
    label_en: str = ""
    # Dimensions for floor-standing equipment
    width_m: float = 0.0
    depth_m: float = 0.0
    # Network connections this equipment requires
    networks_required: List[NetworkType] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════
# RULES BY ROOM TYPE
# ══════════════════════════════════════════════════════════════

ROOM_EQUIPMENT_RULES: Dict[RoomType, List[EquipmentRule]] = {

    # ── SÉJOUR / SALON ──
    RoomType.SEJOUR: [
        # Electrical — NF C 15-100: 1 prise par 4m² min, au moins 5
        EquipmentRule(EquipmentType.PRISE, PlacementType.ON_WALL,
                      quantity=6, height_m=0.30,
                      label_fr="Prise 2P+T 16A", label_en="Socket outlet 2P+T-16A"),
        EquipmentRule(EquipmentType.INTERRUPTEUR, PlacementType.ON_WALL,
                      quantity=2, height_m=1.10,
                      label_fr="Interrupteur va-et-vient", label_en="Two-way switch"),
        EquipmentRule(EquipmentType.LUMINAIRE, PlacementType.CEILING_CENTER,
                      quantity=2, label_fr="Plafonnier", label_en="Ceiling light"),
        # Low current
        EquipmentRule(EquipmentType.PRISE_RJ45, PlacementType.ON_WALL,
                      quantity=2, height_m=0.30,
                      label_fr="Prise RJ45", label_en="RJ45 data outlet"),
        EquipmentRule(EquipmentType.PRISE_TV, PlacementType.ON_WALL,
                      quantity=1, height_m=0.30,
                      label_fr="Prise TV", label_en="TV outlet"),
        EquipmentRule(EquipmentType.WIFI_AP, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Point d'accès WiFi", label_en="Wireless AP"),
        # HVAC
        EquipmentRule(EquipmentType.CLIMATISEUR, PlacementType.WALL_HIGH,
                      quantity=1, height_m=2.20, prefer_wall_type="interior",
                      label_fr="Split climatiseur", label_en="AC indoor unit",
                      networks_required=[NetworkType.HVC_REF, NetworkType.HVC_CONDENSAT]),
        EquipmentRule(EquipmentType.BOUCHE_SOUFFLAGE, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Grille soufflage", label_en="Supply grille",
                      width_m=0.85, depth_m=0.125),
        # Fire safety
        EquipmentRule(EquipmentType.DETECTEUR_FUMEE, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Détecteur de fumée", label_en="Smoke detector"),
        EquipmentRule(EquipmentType.SPRINKLER, PlacementType.CEILING_ZONE,
                      quantity=2, min_room_area_m2=15.0,
                      label_fr="Sprinkler", label_en="Sprinkler",
                      networks_required=[NetworkType.FIRE_SPK]),
    ],

    # ── CHAMBRE ──
    RoomType.CHAMBRE: [
        EquipmentRule(EquipmentType.PRISE, PlacementType.ON_WALL,
                      quantity=4, height_m=0.30,
                      label_fr="Prise 2P+T 16A", label_en="Socket outlet 2P+T-16A"),
        EquipmentRule(EquipmentType.INTERRUPTEUR, PlacementType.ON_WALL,
                      quantity=2, height_m=1.10,
                      label_fr="Interrupteur va-et-vient", label_en="Two-way switch"),
        EquipmentRule(EquipmentType.LUMINAIRE, PlacementType.CEILING_CENTER,
                      quantity=1, label_fr="Plafonnier", label_en="Ceiling light"),
        EquipmentRule(EquipmentType.APPLIQUE, PlacementType.ON_WALL,
                      quantity=2, height_m=1.60, label_fr="Applique tête de lit",
                      label_en="Bedside wall light"),
        EquipmentRule(EquipmentType.PRISE_RJ45, PlacementType.ON_WALL,
                      quantity=1, height_m=0.30,
                      label_fr="Prise RJ45", label_en="RJ45 data outlet"),
        EquipmentRule(EquipmentType.PRISE_TV, PlacementType.ON_WALL,
                      quantity=1, height_m=0.30,
                      label_fr="Prise TV", label_en="TV outlet"),
        EquipmentRule(EquipmentType.CLIMATISEUR, PlacementType.WALL_HIGH,
                      quantity=1, height_m=2.20, prefer_wall_type="interior",
                      label_fr="Split climatiseur", label_en="AC indoor unit",
                      networks_required=[NetworkType.HVC_REF, NetworkType.HVC_CONDENSAT]),
        EquipmentRule(EquipmentType.BOUCHE_SOUFFLAGE, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Grille soufflage", label_en="Supply grille",
                      width_m=0.648, depth_m=0.150),
        EquipmentRule(EquipmentType.DETECTEUR_FUMEE, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Détecteur de fumée", label_en="Smoke detector"),
        EquipmentRule(EquipmentType.SPRINKLER, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Sprinkler", label_en="Sprinkler",
                      networks_required=[NetworkType.FIRE_SPK]),
    ],

    # ── CUISINE ──
    RoomType.CUISINE: [
        # Electrical — NF C 15-100: min 6 prises dont 4 plan de travail
        EquipmentRule(EquipmentType.PRISE_PLAN_TRAVAIL, PlacementType.ON_WALL,
                      quantity=4, height_m=1.10,
                      label_fr="Prise plan de travail", label_en="Worktop socket"),
        EquipmentRule(EquipmentType.PRISE, PlacementType.ON_WALL,
                      quantity=2, height_m=0.30,
                      label_fr="Prise 2P+T 16A", label_en="Socket outlet 2P+T-16A"),
        EquipmentRule(EquipmentType.INTERRUPTEUR, PlacementType.ON_WALL,
                      quantity=1, height_m=1.10,
                      label_fr="Interrupteur", label_en="Switch"),
        EquipmentRule(EquipmentType.LUMINAIRE, PlacementType.CEILING_CENTER,
                      quantity=1, label_fr="Plafonnier", label_en="Ceiling light"),
        # Plumbing
        EquipmentRule(EquipmentType.EVIER, PlacementType.FLOOR_AGAINST_WALL,
                      quantity=1, height_m=0.85, width_m=0.80, depth_m=0.50,
                      label_fr="Évier cuisine", label_en="Kitchen sink",
                      networks_required=[NetworkType.PLU_EF, NetworkType.PLU_EC,
                                        NetworkType.PLU_EU]),
        EquipmentRule(EquipmentType.LAVE_VAISSELLE, PlacementType.FLOOR_AGAINST_WALL,
                      quantity=1, width_m=0.60, depth_m=0.60,
                      label_fr="Lave-vaisselle", label_en="Dishwasher",
                      networks_required=[NetworkType.PLU_EF, NetworkType.PLU_EU]),
        # HVAC
        EquipmentRule(EquipmentType.HOTTE, PlacementType.WALL_HIGH,
                      quantity=1, height_m=1.80, width_m=0.60,
                      label_fr="Hotte aspirante", label_en="Kitchen hood",
                      networks_required=[NetworkType.HVC_VMC]),
        EquipmentRule(EquipmentType.BOUCHE_VMC, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Bouche VMC extraction",
                      label_en="VMC extraction grille",
                      networks_required=[NetworkType.HVC_VMC]),
        EquipmentRule(EquipmentType.CLIMATISEUR, PlacementType.WALL_HIGH,
                      quantity=1, height_m=2.20, min_room_area_m2=8.0,
                      label_fr="Split climatiseur", label_en="AC indoor unit",
                      networks_required=[NetworkType.HVC_REF, NetworkType.HVC_CONDENSAT]),
        # Fire safety
        EquipmentRule(EquipmentType.DETECTEUR_CHALEUR, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Détecteur de chaleur",
                      label_en="Heat detector"),
        EquipmentRule(EquipmentType.SPRINKLER, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Sprinkler", label_en="Sprinkler",
                      networks_required=[NetworkType.FIRE_SPK]),
    ],

    # ── SALLE DE BAIN ──
    RoomType.SDB: [
        # Electrical — zone de sécurité NF C 15-100
        EquipmentRule(EquipmentType.PRISE_ETANCHE, PlacementType.ON_WALL,
                      quantity=1, height_m=1.10,
                      label_fr="Prise étanche 2P+T", label_en="Waterproof socket 2P+T-16A"),
        EquipmentRule(EquipmentType.INTERRUPTEUR, PlacementType.ON_WALL,
                      quantity=1, height_m=1.10,
                      label_fr="Interrupteur", label_en="Switch"),
        EquipmentRule(EquipmentType.LUMINAIRE, PlacementType.CEILING_CENTER,
                      quantity=1, label_fr="Plafonnier IP44", label_en="IP44 ceiling light"),
        EquipmentRule(EquipmentType.APPLIQUE, PlacementType.ON_WALL,
                      quantity=2, height_m=1.80,
                      label_fr="Applique miroir", label_en="Mirror light"),
        # Plumbing — CRITICAL: every fixture gets connected
        EquipmentRule(EquipmentType.LAVABO, PlacementType.FLOOR_AGAINST_WALL,
                      quantity=1, height_m=0.85, width_m=0.60, depth_m=0.45,
                      label_fr="Lavabo", label_en="Washbasin",
                      networks_required=[NetworkType.PLU_EF, NetworkType.PLU_EC,
                                        NetworkType.PLU_EU]),
        EquipmentRule(EquipmentType.DOUCHE, PlacementType.FLOOR_CENTER,
                      quantity=1, width_m=0.90, depth_m=0.90,
                      label_fr="Douche", label_en="Shower",
                      networks_required=[NetworkType.PLU_EF, NetworkType.PLU_EC,
                                        NetworkType.PLU_EU]),
        EquipmentRule(EquipmentType.WC_UNIT, PlacementType.FLOOR_AGAINST_WALL,
                      quantity=1, width_m=0.40, depth_m=0.65,
                      label_fr="WC suspendu", label_en="Wall-hung WC",
                      networks_required=[NetworkType.PLU_EF, NetworkType.PLU_EU]),
        # HVAC — VMC extraction only, NO climatiseur
        EquipmentRule(EquipmentType.BOUCHE_VMC, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Bouche VMC extraction",
                      label_en="VMC extraction grille",
                      networks_required=[NetworkType.HVC_VMC]),
        # Fire safety
        EquipmentRule(EquipmentType.DETECTEUR_FUMEE, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Détecteur de fumée", label_en="Smoke detector"),
        EquipmentRule(EquipmentType.SPRINKLER, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Sprinkler", label_en="Sprinkler",
                      networks_required=[NetworkType.FIRE_SPK]),
    ],

    # ── WC SÉPARÉ ──
    RoomType.WC: [
        EquipmentRule(EquipmentType.INTERRUPTEUR, PlacementType.ON_WALL,
                      quantity=1, height_m=1.10,
                      label_fr="Interrupteur", label_en="Switch"),
        EquipmentRule(EquipmentType.LUMINAIRE, PlacementType.CEILING_CENTER,
                      quantity=1, label_fr="Plafonnier", label_en="Ceiling light"),
        EquipmentRule(EquipmentType.WC_UNIT, PlacementType.FLOOR_AGAINST_WALL,
                      quantity=1, width_m=0.40, depth_m=0.65,
                      label_fr="WC suspendu", label_en="Wall-hung WC",
                      networks_required=[NetworkType.PLU_EF, NetworkType.PLU_EU]),
        EquipmentRule(EquipmentType.LAVABO, PlacementType.FLOOR_AGAINST_WALL,
                      quantity=1, height_m=0.85, width_m=0.45, depth_m=0.35,
                      label_fr="Lave-mains", label_en="Hand basin",
                      networks_required=[NetworkType.PLU_EF, NetworkType.PLU_EU]),
        EquipmentRule(EquipmentType.BOUCHE_VMC, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Bouche VMC extraction",
                      label_en="VMC extraction grille",
                      networks_required=[NetworkType.HVC_VMC]),
        EquipmentRule(EquipmentType.SPRINKLER, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Sprinkler", label_en="Sprinkler",
                      networks_required=[NetworkType.FIRE_SPK]),
    ],

    # ── COULOIR / CIRCULATION ──
    # NO climatiseur, NO prises data, minimal equipment
    RoomType.COULOIR: [
        EquipmentRule(EquipmentType.INTERRUPTEUR, PlacementType.ON_WALL,
                      quantity=2, height_m=1.10,
                      label_fr="Interrupteur va-et-vient", label_en="Two-way switch"),
        EquipmentRule(EquipmentType.LUMINAIRE, PlacementType.CEILING_CENTER,
                      quantity=1, label_fr="Plafonnier", label_en="Ceiling light"),
        EquipmentRule(EquipmentType.DETECTEUR_FUMEE, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Détecteur de fumée", label_en="Smoke detector"),
        EquipmentRule(EquipmentType.SPRINKLER, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Sprinkler", label_en="Sprinkler",
                      networks_required=[NetworkType.FIRE_SPK]),
    ],

    # ── FOYER / ENTRÉE ──
    RoomType.FOYER: [
        EquipmentRule(EquipmentType.PRISE, PlacementType.ON_WALL,
                      quantity=1, height_m=0.30,
                      label_fr="Prise 2P+T 16A", label_en="Socket outlet"),
        EquipmentRule(EquipmentType.INTERRUPTEUR, PlacementType.ON_WALL,
                      quantity=1, height_m=1.10,
                      label_fr="Interrupteur", label_en="Switch"),
        EquipmentRule(EquipmentType.LUMINAIRE, PlacementType.CEILING_CENTER,
                      quantity=1, label_fr="Plafonnier", label_en="Ceiling light"),
        EquipmentRule(EquipmentType.INTERPHONE, PlacementType.ON_WALL,
                      quantity=1, height_m=1.50,
                      label_fr="Interphone", label_en="Intercom unit"),
        EquipmentRule(EquipmentType.TABLEAU_ELEC, PlacementType.ON_WALL,
                      quantity=1, height_m=1.40,
                      label_fr="Tableau électrique", label_en="Electrical panel"),
        EquipmentRule(EquipmentType.DETECTEUR_FUMEE, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Détecteur de fumée", label_en="Smoke detector"),
        EquipmentRule(EquipmentType.SPRINKLER, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Sprinkler", label_en="Sprinkler",
                      networks_required=[NetworkType.FIRE_SPK]),
    ],

    # ── DRESSING ──
    RoomType.DRESSING: [
        EquipmentRule(EquipmentType.PRISE, PlacementType.ON_WALL,
                      quantity=1, height_m=0.30,
                      label_fr="Prise 2P+T 16A", label_en="Socket outlet"),
        EquipmentRule(EquipmentType.INTERRUPTEUR, PlacementType.ON_WALL,
                      quantity=1, height_m=1.10,
                      label_fr="Interrupteur", label_en="Switch"),
        EquipmentRule(EquipmentType.LUMINAIRE, PlacementType.CEILING_CENTER,
                      quantity=1, label_fr="Plafonnier", label_en="Ceiling light"),
        EquipmentRule(EquipmentType.DETECTEUR_FUMEE, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Détecteur de fumée", label_en="Smoke detector"),
    ],

    # ── BUREAU / WORKSPACE ──
    RoomType.BUREAU: [
        EquipmentRule(EquipmentType.PRISE, PlacementType.ON_WALL,
                      quantity=4, height_m=0.30,
                      label_fr="Prise 2P+T 16A", label_en="Socket outlet 2P+T-16A"),
        EquipmentRule(EquipmentType.INTERRUPTEUR, PlacementType.ON_WALL,
                      quantity=1, height_m=1.10,
                      label_fr="Interrupteur", label_en="Switch"),
        EquipmentRule(EquipmentType.LUMINAIRE, PlacementType.CEILING_CENTER,
                      quantity=1, label_fr="Plafonnier", label_en="Ceiling light"),
        EquipmentRule(EquipmentType.PRISE_RJ45, PlacementType.ON_WALL,
                      quantity=2, height_m=0.30,
                      label_fr="Prise RJ45", label_en="RJ45 data outlet"),
        EquipmentRule(EquipmentType.CLIMATISEUR, PlacementType.WALL_HIGH,
                      quantity=1, height_m=2.20,
                      label_fr="Split climatiseur", label_en="AC indoor unit",
                      networks_required=[NetworkType.HVC_REF, NetworkType.HVC_CONDENSAT]),
        EquipmentRule(EquipmentType.DETECTEUR_FUMEE, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Détecteur de fumée", label_en="Smoke detector"),
        EquipmentRule(EquipmentType.SPRINKLER, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Sprinkler", label_en="Sprinkler",
                      networks_required=[NetworkType.FIRE_SPK]),
    ],

    # ── BUANDERIE / LAUNDRY ──
    RoomType.BUANDERIE: [
        EquipmentRule(EquipmentType.PRISE_ETANCHE, PlacementType.ON_WALL,
                      quantity=2, height_m=1.10,
                      label_fr="Prise étanche", label_en="Waterproof socket"),
        EquipmentRule(EquipmentType.INTERRUPTEUR, PlacementType.ON_WALL,
                      quantity=1, height_m=1.10,
                      label_fr="Interrupteur", label_en="Switch"),
        EquipmentRule(EquipmentType.LUMINAIRE, PlacementType.CEILING_CENTER,
                      quantity=1, label_fr="Plafonnier", label_en="Ceiling light"),
        EquipmentRule(EquipmentType.LAVE_LINGE, PlacementType.FLOOR_AGAINST_WALL,
                      quantity=1, width_m=0.60, depth_m=0.60,
                      label_fr="Lave-linge", label_en="Washing machine",
                      networks_required=[NetworkType.PLU_EF, NetworkType.PLU_EU]),
        EquipmentRule(EquipmentType.BOUCHE_VMC, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Bouche VMC extraction",
                      label_en="VMC extraction grille",
                      networks_required=[NetworkType.HVC_VMC]),
        EquipmentRule(EquipmentType.DETECTEUR_FUMEE, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Détecteur de fumée", label_en="Smoke detector"),
    ],

    # ── RANGEMENT / STORAGE ──
    RoomType.RANGEMENT: [
        EquipmentRule(EquipmentType.PRISE, PlacementType.ON_WALL,
                      quantity=1, height_m=0.30,
                      label_fr="Prise 2P+T", label_en="Socket outlet"),
        EquipmentRule(EquipmentType.INTERRUPTEUR, PlacementType.ON_WALL,
                      quantity=1, height_m=1.10,
                      label_fr="Interrupteur", label_en="Switch"),
        EquipmentRule(EquipmentType.LUMINAIRE, PlacementType.CEILING_CENTER,
                      quantity=1, label_fr="Plafonnier", label_en="Ceiling light"),
    ],

    # ── LOCAL TECHNIQUE ──
    RoomType.LOCAL_TECHNIQUE: [
        EquipmentRule(EquipmentType.PRISE, PlacementType.ON_WALL,
                      quantity=2, height_m=0.30,
                      label_fr="Prise 2P+T 16A", label_en="Socket outlet"),
        EquipmentRule(EquipmentType.LUMINAIRE, PlacementType.CEILING_CENTER,
                      quantity=1, label_fr="Plafonnier", label_en="Ceiling light"),
        EquipmentRule(EquipmentType.CHAUFFE_EAU, PlacementType.FLOOR_AGAINST_WALL,
                      quantity=1, width_m=0.50, depth_m=0.50,
                      label_fr="Chauffe-eau", label_en="Water heater",
                      networks_required=[NetworkType.PLU_EF, NetworkType.PLU_EC]),
        EquipmentRule(EquipmentType.BOUCHE_VMC, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Bouche VMC",
                      label_en="VMC grille",
                      networks_required=[NetworkType.HVC_VMC]),
        EquipmentRule(EquipmentType.DETECTEUR_CHALEUR, PlacementType.CEILING_ZONE,
                      quantity=1, label_fr="Détecteur de chaleur",
                      label_en="Heat detector"),
    ],

    # ── BALCON ──
    RoomType.BALCON: [
        EquipmentRule(EquipmentType.PRISE_ETANCHE, PlacementType.ON_WALL,
                      quantity=1, height_m=0.30,
                      label_fr="Prise étanche extérieure", label_en="Outdoor waterproof socket"),
        EquipmentRule(EquipmentType.APPLIQUE, PlacementType.ON_WALL,
                      quantity=1, height_m=2.20,
                      label_fr="Applique extérieure IP65", label_en="Outdoor wall light IP65"),
    ],
}


# ══════════════════════════════════════════════════════════════
# EQUIPMENT PLACEMENT ENGINE
# ══════════════════════════════════════════════════════════════

def get_rules_for_room(room: Room) -> List[EquipmentRule]:
    """Get the equipment rules applicable to a room based on its type and area."""
    rules = ROOM_EQUIPMENT_RULES.get(room.type, [])
    return [r for r in rules if room.area_m2 >= r.min_room_area_m2]


def place_equipment_in_room(room: Room, walls: List[Wall], lang: str = "fr") -> List[EquipmentInstance]:
    """Place all required equipment in a room respecting topology.

    Returns list of EquipmentInstance with correct positions and wall references.
    Equipment is placed ON wall faces, not in abstract grid positions.
    """
    rules = get_rules_for_room(room)
    if not rules or not walls:
        return []

    # Classify walls
    interior_walls = [w for w in walls if w.type in (WallType.CLOISON, WallType.MITOYEN)]
    exterior_walls = [w for w in walls if w.type in (WallType.FACADE,)]
    all_usable = [w for w in walls if w.length_m > 0.5]  # Skip tiny walls

    if not all_usable:
        all_usable = walls

    placed = []
    wall_usage = {}  # wall_id -> list of used offsets (avoid stacking)

    for rule in rules:
        for _ in range(rule.quantity):
            equip = EquipmentInstance(
                type=rule.equipment_type,
                placement=rule.placement,
                height_m=rule.height_m,
                label=rule.label_fr if lang == "fr" else rule.label_en,
                width_m=rule.width_m,
                depth_m=rule.depth_m,
            )

            if rule.placement in (PlacementType.CEILING_CENTER, PlacementType.CEILING_ZONE):
                # Place at room center (ceiling)
                equip.position = room.center
                equip.height_m = 2.70  # Standard ceiling height

            elif rule.placement in (PlacementType.ON_WALL, PlacementType.WALL_HIGH,
                                     PlacementType.FLOOR_AGAINST_WALL):
                # Pick best wall
                if rule.prefer_wall_type == "exterior" and exterior_walls:
                    candidates = exterior_walls
                elif rule.prefer_wall_type == "interior" and interior_walls:
                    candidates = interior_walls
                else:
                    candidates = all_usable

                # Find wall with most free space
                wall = _pick_least_used_wall(candidates, wall_usage)
                if wall is None:
                    wall = all_usable[0]

                # Find position along wall avoiding overlap
                offset = _find_free_offset(wall, wall_usage, rule.width_m or 0.3)
                equip.wall_id = wall.id
                equip.wall_offset_m = offset
                equip.position = wall.interior_face_point(
                    offset, room.id, standoff_m=0.05 if rule.depth_m == 0 else rule.depth_m / 2
                )

                # Record usage
                wall_usage.setdefault(wall.id, []).append(offset)

            elif rule.placement == PlacementType.FLOOR_CENTER:
                equip.position = room.center

            placed.append(equip)

    return placed


def _pick_least_used_wall(candidates: List[Wall], usage: Dict[str, list]) -> Optional[Wall]:
    """Pick the wall with the most available space."""
    if not candidates:
        return None
    # Sort by (usage_count, -length) to prefer long empty walls
    return min(candidates, key=lambda w: (len(usage.get(w.id, [])), -w.length_m))


def _find_free_offset(wall: Wall, usage: Dict[str, list],
                       item_width: float = 0.3) -> float:
    """Find a free position along a wall, avoiding overlaps."""
    used = sorted(usage.get(wall.id, []))
    length = wall.length_m
    margin = 0.15  # Min distance from wall end
    min_gap = max(item_width, 0.4)  # Min gap between items

    if not used:
        return length / 2  # Center of wall

    # Try evenly spaced positions
    n_existing = len(used)
    n_slots = n_existing + 1
    slot_width = (length - 2 * margin) / max(n_slots, 1)

    # Find the largest gap
    points = [margin] + used + [length - margin]
    best_pos = length / 2
    best_gap = 0
    for i in range(len(points) - 1):
        gap = points[i + 1] - points[i]
        if gap > best_gap:
            best_gap = gap
            best_pos = (points[i] + points[i + 1]) / 2

    return max(margin, min(best_pos, length - margin))


# ══════════════════════════════════════════════════════════════
# TRADE DEFINITIONS (for plan generation)
# ══════════════════════════════════════════════════════════════

@dataclass
class TradeDef:
    """Defines a construction trade / lot technique."""
    code: str           # "ARC", "STR", "PLU", etc.
    number: str         # "001", "302", "410", etc.
    name_fr: str
    name_en: str
    color: str          # Hex color for coordination plans
    equipment_types: List[EquipmentType] = field(default_factory=list)
    network_types: List[NetworkType] = field(default_factory=list)


# Trade definitions matching Crystal Residence convention
TRADES = [
    TradeDef("ARC", "001", "Architecture", "Architecture", "#000000"),
    TradeDef("STR", "200", "Structure", "Structure", "#808080",
             network_types=[]),
    TradeDef("TDL", "102", "Doublage Thermique", "Thermal Dry Lining", "#FFD700"),
    TradeDef("MAS", "302", "Maçonnerie", "Masonry Works", "#0000FF"),
    TradeDef("FIF", "400", "Sécurité Incendie", "Fire Fighting", "#FF0000",
             equipment_types=[EquipmentType.SPRINKLER, EquipmentType.SIRENE,
                             EquipmentType.CDI, EquipmentType.RIA],
             network_types=[NetworkType.FIRE_SPK, NetworkType.FIRE_DETECT]),
    TradeDef("PLU", "410", "Plomberie", "Plumbing", "#008000",
             equipment_types=[EquipmentType.WC_UNIT, EquipmentType.LAVABO,
                             EquipmentType.DOUCHE, EquipmentType.BAIGNOIRE,
                             EquipmentType.EVIER, EquipmentType.LAVE_LINGE,
                             EquipmentType.LAVE_VAISSELLE, EquipmentType.CHAUFFE_EAU],
             network_types=[NetworkType.PLU_EF, NetworkType.PLU_EC,
                           NetworkType.PLU_EU, NetworkType.PLU_EP]),
    TradeDef("HVC", "413", "CVC / Ventilation", "HVAC", "#800080",
             equipment_types=[EquipmentType.CLIMATISEUR, EquipmentType.UNITE_EXT,
                             EquipmentType.BOUCHE_VMC, EquipmentType.BOUCHE_SOUFFLAGE,
                             EquipmentType.HOTTE],
             network_types=[NetworkType.HVC_SOUFFLAGE, NetworkType.HVC_REPRISE,
                           NetworkType.HVC_VMC, NetworkType.HVC_REF,
                           NetworkType.HVC_CONDENSAT]),
    TradeDef("HCU", "510", "Courants Forts", "High Current Unit", "#FF00FF",
             equipment_types=[EquipmentType.PRISE, EquipmentType.PRISE_PLAN_TRAVAIL,
                             EquipmentType.PRISE_ETANCHE, EquipmentType.INTERRUPTEUR,
                             EquipmentType.LUMINAIRE, EquipmentType.APPLIQUE,
                             EquipmentType.TABLEAU_ELEC]),
    TradeDef("LCU", "520", "Courants Faibles", "Low Current Unit", "#4169E1",
             equipment_types=[EquipmentType.PRISE_RJ45, EquipmentType.PRISE_TV,
                             EquipmentType.INTERPHONE, EquipmentType.DETECTEUR_FUMEE,
                             EquipmentType.DETECTEUR_CHALEUR, EquipmentType.BOUTON_PANIQUE,
                             EquipmentType.WIFI_AP],
             network_types=[NetworkType.FIRE_DETECT]),
    TradeDef("RC", "113", "Faux Plafond", "Reflected Ceiling", "#4682B4"),
    TradeDef("SYN", "001", "Synthèse / Coordination", "Network Coordination", "#FF8C00"),
]


def get_trade_by_code(code: str) -> Optional[TradeDef]:
    for t in TRADES:
        if t.code == code:
            return t
    return None


def get_relevant_trades(building) -> List[TradeDef]:
    """Determine which trades are relevant for a building based on its content."""
    relevant = []
    all_equip_types = set()
    all_network_types = set()

    for room in building.all_rooms:
        for eq in room.equipment:
            all_equip_types.add(eq.type)
        for seg in room.network_segments:
            all_network_types.add(seg.type)

    for trade in TRADES:
        # ARC and STR are always relevant
        if trade.code in ("ARC", "STR", "SYN"):
            relevant.append(trade)
            continue
        # Check if any equipment or network of this trade exists
        if any(et in all_equip_types for et in trade.equipment_types):
            relevant.append(trade)
        elif any(nt in all_network_types for nt in trade.network_types):
            relevant.append(trade)

    return relevant
