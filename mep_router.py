"""
mep_router.py — Topology-aware MEP network routing for TijanBIM

Phase 2 of the BIM Revolution. This module takes a Building with rooms
and placed equipment (from room_rules.py) and routes physical networks:

1. Plumbing: colonnes montantes → distribution → each fixture
2. HVAC: outdoor unit → refrigerant → indoor splits + VMC extraction
3. Electrical: tableau → circuits per room → each outlet/light
4. Fire Safety: sprinkler riser → branch lines → each head

All network segments have 3D coordinates, real diameters from engine_mep_v2,
and explicit connections to equipment instances.

Pipe sizing per DTU 60.11 / NF EN 806-3.
HVAC duct sizing per DTU 68.3.
Electrical per NF C 15-100.
Fire per IT 246 + NF EN 12845.
"""
from __future__ import annotations
import math
import logging
from typing import List, Optional, Dict, Tuple

from bim_model import (
    Building, Level, Room, Wall, Point, Point3D, BBox,
    EquipmentInstance, NetworkSegment,
    RoomType, EquipmentType, NetworkType, PlacementType
)

logger = logging.getLogger("tijan.mep_router")


# ══════════════════════════════════════════════════════════════
# PIPE / DUCT SIZING CONSTANTS
# ══════════════════════════════════════════════════════════════

# Plumbing diameters per fixture type (mm) — DTU 60.11
PIPE_DIAMETER = {
    # Cold water supply
    (EquipmentType.LAVABO, NetworkType.PLU_EF): 16,
    (EquipmentType.DOUCHE, NetworkType.PLU_EF): 16,
    (EquipmentType.WC_UNIT, NetworkType.PLU_EF): 12,
    (EquipmentType.EVIER, NetworkType.PLU_EF): 16,
    (EquipmentType.LAVE_LINGE, NetworkType.PLU_EF): 16,
    (EquipmentType.LAVE_VAISSELLE, NetworkType.PLU_EF): 16,
    (EquipmentType.CHAUFFE_EAU, NetworkType.PLU_EF): 25,
    # Hot water supply
    (EquipmentType.LAVABO, NetworkType.PLU_EC): 16,
    (EquipmentType.DOUCHE, NetworkType.PLU_EC): 16,
    (EquipmentType.EVIER, NetworkType.PLU_EC): 16,
    # Waste water
    (EquipmentType.LAVABO, NetworkType.PLU_EU): 40,
    (EquipmentType.DOUCHE, NetworkType.PLU_EU): 50,
    (EquipmentType.WC_UNIT, NetworkType.PLU_EU): 100,
    (EquipmentType.EVIER, NetworkType.PLU_EU): 50,
    (EquipmentType.LAVE_LINGE, NetworkType.PLU_EU): 40,
    (EquipmentType.LAVE_VAISSELLE, NetworkType.PLU_EU): 40,
}

# Distribution pipe diameters by number of fixtures served
DISTRIBUTION_DIAMETER = {
    1: 16, 2: 20, 3: 25, 4: 25, 5: 32, 8: 32, 12: 40, 20: 50,
}

# Waste collector diameters by number of fixtures
COLLECTOR_DIAMETER = {
    1: 50, 2: 63, 3: 75, 5: 100, 10: 125, 20: 150,
}

# VMC duct diameters (mm) by room type
VMC_DUCT_DIAMETER = {
    RoomType.SDB: 100,
    RoomType.WC: 80,
    RoomType.CUISINE: 125,
    RoomType.BUANDERIE: 100,
    RoomType.LOCAL_TECHNIQUE: 100,
}

# Refrigerant pipe sizes (mm)
REF_LIQUID = 10    # Liquid line
REF_GAS = 13       # Gas/suction line

# Condensate drain
CONDENSAT_DIAMETER = 32

# Sprinkler pipe diameters (mm) by zone
SPK_BRANCH = 25     # Branch line to individual head
SPK_MAIN = 40       # Main distribution
SPK_RISER = 65      # Riser

# Standard heights (meters above floor level)
H_FLOOR = 0.0
H_FIXTURE = 0.85    # Lavabo, évier height
H_CEILING = 2.70    # False ceiling
H_ABOVE_CEILING = 2.90  # Pipes/ducts above false ceiling
H_SLAB = 3.05       # Slab level (next floor)
H_SPLIT = 2.20      # Split AC unit
H_SPRINKLER = 2.85  # Sprinkler head below ceiling


# ══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════

def route_mep(building: Building, mep_results=None) -> Building:
    """Route all MEP networks through the building.

    Args:
        building: Building with rooms and placed equipment
        mep_results: Optional ResultatsMEP from engine_mep_v2

    Returns:
        Same building with network_segments populated
    """
    for level in building.levels:
        # Extract engine sizing if available
        col_diam = 50  # Default colonne montante
        if mep_results and hasattr(mep_results, 'plomberie'):
            col_diam = mep_results.plomberie.diam_colonne_montante_mm

        # Route each network
        _route_plumbing(level, col_diam)
        _route_hvac(level)
        _route_electrical(level)
        _route_fire_safety(level)

    return building


# ══════════════════════════════════════════════════════════════
# PLUMBING ROUTER
# ══════════════════════════════════════════════════════════════

def _route_plumbing(level: Level, col_diam_mm: int = 50):
    """Route plumbing networks: risers → distribution → fixtures.

    Strategy:
    1. Place a vertical riser (colonne montante) at a central wet zone
    2. From riser, run horizontal distribution along corridors
    3. Branch into each wet room (SDB, WC, cuisine, buanderie)
    4. Connect each fixture with correct diameter pipe
    5. Waste water follows gravity — slopes away from fixtures
    """
    elevation = level.elevation_m
    wet_rooms = [r for r in level.rooms if r.is_wet]

    if not wet_rooms:
        return

    # Find best riser position (centroid of wet rooms)
    riser_pos = _find_riser_position(wet_rooms)

    # Create vertical riser segments
    for net_type, label_prefix, diam in [
        (NetworkType.PLU_EF, "EF", col_diam_mm),
        (NetworkType.PLU_EC, "EC", max(25, col_diam_mm - 10)),
        (NetworkType.PLU_EU, "EU", 100),
    ]:
        riser = NetworkSegment(
            type=net_type,
            start=Point3D(riser_pos.x, riser_pos.y, elevation),
            end=Point3D(riser_pos.x, riser_pos.y, elevation + level.height_m),
            diameter_mm=diam,
            is_vertical=True,
            label=f"{label_prefix} {diam}mm colonne",
        )
        level.network_segments.append(riser)

    # Route to each wet room
    for room in wet_rooms:
        plumbing_equip = [e for e in room.equipment
                          if e.type in (EquipmentType.WC_UNIT, EquipmentType.LAVABO,
                                       EquipmentType.DOUCHE, EquipmentType.BAIGNOIRE,
                                       EquipmentType.EVIER, EquipmentType.LAVE_LINGE,
                                       EquipmentType.LAVE_VAISSELLE, EquipmentType.CHAUFFE_EAU)]

        if not plumbing_equip:
            continue

        # Distribution from riser to room entry point
        room_entry = room.center
        dist_z = elevation + H_ABOVE_CEILING

        # Count fixtures for distribution sizing
        n_fixtures = len(plumbing_equip)
        dist_diam_ef = _lookup_diameter(DISTRIBUTION_DIAMETER, n_fixtures)
        dist_diam_eu = _lookup_diameter(COLLECTOR_DIAMETER, n_fixtures)

        # Cold water distribution to room
        room.network_segments.append(NetworkSegment(
            type=NetworkType.PLU_EF,
            start=Point3D(riser_pos.x, riser_pos.y, dist_z),
            end=Point3D(room_entry.x, room_entry.y, dist_z),
            diameter_mm=dist_diam_ef,
            label=f"EF {dist_diam_ef}mm +{dist_z:.0f}",
        ))

        # Hot water distribution (skip WC-only rooms)
        has_hot = any(e.type in (EquipmentType.LAVABO, EquipmentType.DOUCHE,
                                  EquipmentType.EVIER, EquipmentType.BAIGNOIRE)
                      for e in plumbing_equip)
        if has_hot:
            room.network_segments.append(NetworkSegment(
                type=NetworkType.PLU_EC,
                start=Point3D(riser_pos.x, riser_pos.y, dist_z),
                end=Point3D(room_entry.x, room_entry.y, dist_z),
                diameter_mm=dist_diam_ef,
                label=f"EC {dist_diam_ef}mm +{dist_z:.0f}",
            ))

        # Waste water collector
        waste_z = elevation + 0.05  # Just above floor (gravity)
        room.network_segments.append(NetworkSegment(
            type=NetworkType.PLU_EU,
            start=Point3D(room_entry.x, room_entry.y, waste_z),
            end=Point3D(riser_pos.x, riser_pos.y, waste_z),
            diameter_mm=dist_diam_eu,
            label=f"EU {dist_diam_eu}mm +{waste_z:.2f}",
        ))

        # Connect each fixture
        for equip in plumbing_equip:
            _connect_fixture_plumbing(equip, room_entry, room, elevation)


def _connect_fixture_plumbing(equip: EquipmentInstance, room_entry: Point,
                                room: Room, elevation: float):
    """Connect a plumbing fixture to the room distribution."""
    eq_pos = equip.position
    eq_z_supply = elevation + (equip.height_m or H_FIXTURE)
    eq_z_waste = elevation + 0.05  # Floor level drain

    # Cold water supply drop from ceiling to fixture
    diam_ef = PIPE_DIAMETER.get((equip.type, NetworkType.PLU_EF), 16)
    if diam_ef:
        # Vertical drop
        room.network_segments.append(NetworkSegment(
            type=NetworkType.PLU_EF,
            start=Point3D(eq_pos.x, eq_pos.y, elevation + H_ABOVE_CEILING),
            end=Point3D(eq_pos.x, eq_pos.y, eq_z_supply),
            diameter_mm=diam_ef,
            is_vertical=True,
            connects_to=equip.id,
            label=f"EF {diam_ef}mm",
        ))

    # Hot water supply (not for WC)
    diam_ec = PIPE_DIAMETER.get((equip.type, NetworkType.PLU_EC))
    if diam_ec:
        room.network_segments.append(NetworkSegment(
            type=NetworkType.PLU_EC,
            start=Point3D(eq_pos.x, eq_pos.y, elevation + H_ABOVE_CEILING),
            end=Point3D(eq_pos.x, eq_pos.y, eq_z_supply),
            diameter_mm=diam_ec,
            is_vertical=True,
            connects_to=equip.id,
            label=f"EC {diam_ec}mm",
        ))

    # Waste water drain
    diam_eu = PIPE_DIAMETER.get((equip.type, NetworkType.PLU_EU))
    if diam_eu:
        room.network_segments.append(NetworkSegment(
            type=NetworkType.PLU_EU,
            start=Point3D(eq_pos.x, eq_pos.y, eq_z_waste),
            end=Point3D(room_entry.x, room_entry.y, eq_z_waste),
            diameter_mm=diam_eu,
            connects_to=equip.id,
            label=f"EU {diam_eu}mm",
        ))


def _find_riser_position(wet_rooms: List[Room]) -> Point:
    """Find optimal riser position (centroid of wet rooms)."""
    if not wet_rooms:
        return Point(0, 0)
    cx = sum(r.center.x for r in wet_rooms) / len(wet_rooms)
    cy = sum(r.center.y for r in wet_rooms) / len(wet_rooms)
    return Point(cx, cy)


def _lookup_diameter(table: dict, n: int) -> int:
    """Look up diameter from a threshold table."""
    for threshold, diam in sorted(table.items()):
        if n <= threshold:
            return diam
    return max(table.values())


# ══════════════════════════════════════════════════════════════
# HVAC ROUTER
# ══════════════════════════════════════════════════════════════

def _route_hvac(level: Level):
    """Route HVAC networks: splits, VMC extraction, supply air.

    Strategy:
    1. Outdoor unit on exterior (balcony or roof) → refrigerant to each split
    2. VMC: central extraction unit → ducts to each wet room
    3. Supply: diffusers in habitable rooms connected to supply duct
    """
    elevation = level.elevation_m

    # ── Refrigerant routing (splits) ──
    rooms_with_splits = [r for r in level.rooms
                         if any(e.type == EquipmentType.CLIMATISEUR
                                for e in r.equipment)]

    if rooms_with_splits:
        # Outdoor unit position: exterior of building
        bbox = level.bbox
        outdoor_pos = Point(bbox.max_pt.x + 0.5, bbox.center.y)

        for room in rooms_with_splits:
            split = next((e for e in room.equipment
                         if e.type == EquipmentType.CLIMATISEUR), None)
            if not split:
                continue

            split_pos = split.position
            split_z = elevation + H_SPLIT

            # Refrigerant liquid line (outdoor → indoor)
            room.network_segments.append(NetworkSegment(
                type=NetworkType.HVC_REF,
                start=Point3D(outdoor_pos.x, outdoor_pos.y, split_z),
                end=Point3D(split_pos.x, split_pos.y, split_z),
                diameter_mm=REF_LIQUID,
                connects_to=split.id,
                label=f"REF liquid {REF_LIQUID}mm",
            ))

            # Refrigerant gas line (indoor → outdoor)
            room.network_segments.append(NetworkSegment(
                type=NetworkType.HVC_REF,
                start=Point3D(split_pos.x, split_pos.y, split_z),
                end=Point3D(outdoor_pos.x, outdoor_pos.y, split_z),
                diameter_mm=REF_GAS,
                connects_to=split.id,
                label=f"REF gas {REF_GAS}mm",
            ))

            # Condensate drain
            room.network_segments.append(NetworkSegment(
                type=NetworkType.HVC_CONDENSAT,
                start=Point3D(split_pos.x, split_pos.y, split_z - 0.1),
                end=Point3D(split_pos.x, split_pos.y, elevation + 0.1),
                diameter_mm=CONDENSAT_DIAMETER,
                is_vertical=True,
                connects_to=split.id,
                label=f"Condensat {CONDENSAT_DIAMETER}mm",
            ))

    # ── VMC extraction ──
    rooms_with_vmc = [r for r in level.rooms
                      if any(e.type == EquipmentType.BOUCHE_VMC
                             for e in r.equipment)]

    if rooms_with_vmc:
        # VMC unit in local technique or at building exterior
        tech_rooms = level.rooms_by_type(RoomType.LOCAL_TECHNIQUE)
        if tech_rooms:
            vmc_unit_pos = tech_rooms[0].center
        else:
            bbox = level.bbox
            vmc_unit_pos = Point(bbox.min_pt.x, bbox.min_pt.y)

        vmc_z = elevation + H_ABOVE_CEILING

        # Main trunk duct
        trunk_diam = 200 if len(rooms_with_vmc) > 3 else 150

        for room in rooms_with_vmc:
            bouche = next((e for e in room.equipment
                          if e.type == EquipmentType.BOUCHE_VMC), None)
            if not bouche:
                continue

            # Duct diameter based on room type
            duct_diam = VMC_DUCT_DIAMETER.get(room.type, 100)

            # Main duct from VMC unit to room
            room.network_segments.append(NetworkSegment(
                type=NetworkType.HVC_VMC,
                start=Point3D(vmc_unit_pos.x, vmc_unit_pos.y, vmc_z),
                end=Point3D(room.center.x, room.center.y, vmc_z),
                diameter_mm=trunk_diam,
                label=f"VMC trunk {trunk_diam}mm +{vmc_z:.0f}",
            ))

            # Branch to grille
            room.network_segments.append(NetworkSegment(
                type=NetworkType.HVC_VMC,
                start=Point3D(room.center.x, room.center.y, vmc_z),
                end=Point3D(bouche.position.x, bouche.position.y, elevation + H_CEILING),
                diameter_mm=duct_diam,
                connects_to=bouche.id,
                label=f"VMC {duct_diam}mm +{H_CEILING:.0f}",
            ))

    # ── Supply air (diffusers) ──
    rooms_with_supply = [r for r in level.rooms
                         if any(e.type == EquipmentType.BOUCHE_SOUFFLAGE
                                for e in r.equipment)]

    if rooms_with_supply:
        supply_z = elevation + H_ABOVE_CEILING
        bbox = level.bbox

        for room in rooms_with_supply:
            diffuser = next((e for e in room.equipment
                            if e.type == EquipmentType.BOUCHE_SOUFFLAGE), None)
            if not diffuser:
                continue

            # Rectangular supply duct (850×125mm for séjour, 648×150mm for chambre)
            if room.type == RoomType.SEJOUR:
                duct_label = "Supply 850x125mm"
            else:
                duct_label = "Supply 648x150mm"

            room.network_segments.append(NetworkSegment(
                type=NetworkType.HVC_SOUFFLAGE,
                start=Point3D(bbox.center.x, supply_z, supply_z),
                end=Point3D(diffuser.position.x, diffuser.position.y, supply_z),
                diameter_mm=200,  # Equivalent diameter
                connects_to=diffuser.id,
                label=duct_label,
            ))


# ══════════════════════════════════════════════════════════════
# ELECTRICAL ROUTER
# ══════════════════════════════════════════════════════════════

def _route_electrical(level: Level):
    """Route electrical circuits per room.

    Strategy:
    1. Tableau électrique in foyer → main trunk
    2. One circuit per room (simplified — real design has dedicated circuits)
    3. Each outlet/switch/light connected to its room circuit
    """
    elevation = level.elevation_m

    # Find electrical panel
    panel_room = None
    panel_pos = None
    for room in level.rooms:
        panel = next((e for e in room.equipment
                     if e.type == EquipmentType.TABLEAU_ELEC), None)
        if panel:
            panel_room = room
            panel_pos = panel.position
            break

    if panel_pos is None:
        # Default: foyer or first room
        foyers = level.rooms_by_type(RoomType.FOYER)
        panel_room = foyers[0] if foyers else (level.rooms[0] if level.rooms else None)
        if panel_room:
            panel_pos = panel_room.center
        else:
            return

    panel_z = elevation + H_ABOVE_CEILING

    for room in level.rooms:
        elec_equip = [e for e in room.equipment
                      if e.type in (EquipmentType.PRISE, EquipmentType.PRISE_PLAN_TRAVAIL,
                                    EquipmentType.PRISE_ETANCHE, EquipmentType.INTERRUPTEUR,
                                    EquipmentType.LUMINAIRE, EquipmentType.APPLIQUE)]

        if not elec_equip:
            continue

        # Main circuit from panel to room
        room.network_segments.append(NetworkSegment(
            type=NetworkType.ELEC_FORT,
            start=Point3D(panel_pos.x, panel_pos.y, panel_z),
            end=Point3D(room.center.x, room.center.y, panel_z),
            diameter_mm=2.5,  # 2.5mm² cable section
            label=f"Circuit {room.name[:15]}",
        ))

        # Low current circuit (RJ45, TV, detectors)
        lc_equip = [e for e in room.equipment
                    if e.type in (EquipmentType.PRISE_RJ45, EquipmentType.PRISE_TV,
                                  EquipmentType.INTERPHONE, EquipmentType.WIFI_AP,
                                  EquipmentType.DETECTEUR_FUMEE,
                                  EquipmentType.DETECTEUR_CHALEUR)]
        if lc_equip:
            room.network_segments.append(NetworkSegment(
                type=NetworkType.ELEC_FAIBLE,
                start=Point3D(panel_pos.x, panel_pos.y, panel_z),
                end=Point3D(room.center.x, room.center.y, panel_z),
                diameter_mm=1.0,  # Cat6 cable
                label=f"LCU {room.name[:15]}",
            ))


# ══════════════════════════════════════════════════════════════
# FIRE SAFETY ROUTER
# ══════════════════════════════════════════════════════════════

def _route_fire_safety(level: Level):
    """Route fire safety networks: sprinkler + detection.

    Strategy:
    1. Sprinkler riser (vertical) at building core
    2. Main distribution along corridors
    3. Branch lines to each sprinkler head
    4. Detection loop connecting all detectors
    """
    elevation = level.elevation_m

    # Collect all sprinklers
    sprinkler_rooms = [r for r in level.rooms
                       if any(e.type == EquipmentType.SPRINKLER for e in r.equipment)]

    if not sprinkler_rooms:
        return

    # Sprinkler riser position (building center)
    bbox = level.bbox
    riser_pos = bbox.center

    # Riser
    level.network_segments.append(NetworkSegment(
        type=NetworkType.FIRE_SPK,
        start=Point3D(riser_pos.x, riser_pos.y, elevation),
        end=Point3D(riser_pos.x, riser_pos.y, elevation + level.height_m),
        diameter_mm=SPK_RISER,
        is_vertical=True,
        label=f"SPK riser {SPK_RISER}mm",
    ))

    spk_z = elevation + H_SPRINKLER

    # Main distribution
    level.network_segments.append(NetworkSegment(
        type=NetworkType.FIRE_SPK,
        start=Point3D(riser_pos.x, riser_pos.y, spk_z),
        end=Point3D(bbox.max_pt.x, riser_pos.y, spk_z),
        diameter_mm=SPK_MAIN,
        label=f"SPK main {SPK_MAIN}mm +{spk_z:.0f}",
    ))
    level.network_segments.append(NetworkSegment(
        type=NetworkType.FIRE_SPK,
        start=Point3D(riser_pos.x, riser_pos.y, spk_z),
        end=Point3D(bbox.min_pt.x, riser_pos.y, spk_z),
        diameter_mm=SPK_MAIN,
        label=f"SPK main {SPK_MAIN}mm +{spk_z:.0f}",
    ))

    # Branch to each room
    for room in sprinkler_rooms:
        sprinklers = [e for e in room.equipment if e.type == EquipmentType.SPRINKLER]

        # Branch from main to room
        room.network_segments.append(NetworkSegment(
            type=NetworkType.FIRE_SPK,
            start=Point3D(riser_pos.x, riser_pos.y, spk_z),
            end=Point3D(room.center.x, room.center.y, spk_z),
            diameter_mm=SPK_BRANCH,
            label=f"SPK branch {SPK_BRANCH}mm +{spk_z:.0f}",
        ))

        # Connect each head
        for spk in sprinklers:
            room.network_segments.append(NetworkSegment(
                type=NetworkType.FIRE_SPK,
                start=Point3D(room.center.x, room.center.y, spk_z),
                end=Point3D(spk.position.x, spk.position.y, spk_z),
                diameter_mm=SPK_BRANCH,
                connects_to=spk.id,
                label=f"SPK {SPK_BRANCH}mm +{spk_z:.2f}",
            ))

    # ── Detection loop ──
    detector_rooms = [r for r in level.rooms
                      if any(e.type in (EquipmentType.DETECTEUR_FUMEE,
                                        EquipmentType.DETECTEUR_CHALEUR)
                             for e in r.equipment)]

    if detector_rooms:
        det_z = elevation + H_CEILING
        # Daisy-chain detectors
        prev_pos = riser_pos
        for room in detector_rooms:
            detector = next((e for e in room.equipment
                            if e.type in (EquipmentType.DETECTEUR_FUMEE,
                                         EquipmentType.DETECTEUR_CHALEUR)), None)
            if detector:
                room.network_segments.append(NetworkSegment(
                    type=NetworkType.FIRE_DETECT,
                    start=Point3D(prev_pos.x, prev_pos.y, det_z),
                    end=Point3D(detector.position.x, detector.position.y, det_z),
                    diameter_mm=1.5,  # Fire detection cable
                    connects_to=detector.id,
                    label="Detection loop",
                ))
                prev_pos = detector.position


# ══════════════════════════════════════════════════════════════
# STATISTICS
# ══════════════════════════════════════════════════════════════

def mep_stats(building: Building) -> Dict:
    """Compute MEP network statistics for the building."""
    stats = {
        "plumbing": {"segments": 0, "total_length_m": 0.0, "fixtures_connected": 0},
        "hvac": {"segments": 0, "total_length_m": 0.0, "splits": 0, "vmc_grilles": 0},
        "electrical": {"segments": 0, "circuits": 0},
        "fire_safety": {"segments": 0, "sprinklers": 0, "detectors": 0},
    }

    for level in building.levels:
        all_segments = list(level.network_segments)
        for room in level.rooms:
            all_segments.extend(room.network_segments)

        for seg in all_segments:
            length = math.sqrt(
                (seg.end.x - seg.start.x) ** 2 +
                (seg.end.y - seg.start.y) ** 2 +
                (seg.end.z - seg.start.z) ** 2
            )

            if seg.type in (NetworkType.PLU_EF, NetworkType.PLU_EC, NetworkType.PLU_EU):
                stats["plumbing"]["segments"] += 1
                stats["plumbing"]["total_length_m"] += length
                if seg.connects_to:
                    stats["plumbing"]["fixtures_connected"] += 1
            elif seg.type in (NetworkType.HVC_REF, NetworkType.HVC_VMC,
                             NetworkType.HVC_SOUFFLAGE, NetworkType.HVC_REPRISE,
                             NetworkType.HVC_CONDENSAT):
                stats["hvac"]["segments"] += 1
                stats["hvac"]["total_length_m"] += length
            elif seg.type in (NetworkType.ELEC_FORT, NetworkType.ELEC_FAIBLE):
                stats["electrical"]["segments"] += 1
                stats["electrical"]["circuits"] += 1
            elif seg.type in (NetworkType.FIRE_SPK, NetworkType.FIRE_DETECT):
                stats["fire_safety"]["segments"] += 1

        # Count specific equipment
        for room in level.rooms:
            stats["hvac"]["splits"] += sum(1 for e in room.equipment
                                           if e.type == EquipmentType.CLIMATISEUR)
            stats["hvac"]["vmc_grilles"] += sum(1 for e in room.equipment
                                                 if e.type == EquipmentType.BOUCHE_VMC)
            stats["fire_safety"]["sprinklers"] += sum(1 for e in room.equipment
                                                       if e.type == EquipmentType.SPRINKLER)
            stats["fire_safety"]["detectors"] += sum(1 for e in room.equipment
                                                      if e.type in (EquipmentType.DETECTEUR_FUMEE,
                                                                    EquipmentType.DETECTEUR_CHALEUR))

    # Round lengths
    for cat in stats.values():
        if "total_length_m" in cat:
            cat["total_length_m"] = round(cat["total_length_m"], 1)

    return stats
