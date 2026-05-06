"""
bim_boq.py — BIM-based Bill of Quantities

Counts equipment and network segments directly from the Building graph,
ensuring the BOQ matches plans exactly. One source of truth.

Replaces the parametric formulas in engine_mep_v2 for quantity estimation.
The engine is still used for SIZING (diameters, capacities, etc.), but
QUANTITIES come from the actual BIM model.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import math

from bim_model import (
    Building, Level, Room,
    EquipmentType, NetworkType, RoomType
)


# ══════════════════════════════════════════════════════════════
# BOQ LINE ITEM
# ══════════════════════════════════════════════════════════════

@dataclass
class BOQItem:
    """A single line in the Bill of Quantities."""
    lot: str              # "PLU", "HVC", "HCU", "LCU", "FIF"
    code: str             # "PLU-001", "HCU-003"
    label_fr: str
    label_en: str
    unit: str             # "u", "ml", "m²", "lot"
    quantity: float
    # Optional breakdown by level
    by_level: Dict[str, float] = field(default_factory=dict)


# ══════════════════════════════════════════════════════════════
# EQUIPMENT TYPE → BOQ MAPPING
# ══════════════════════════════════════════════════════════════

_EQUIP_BOQ = {
    # Plumbing
    EquipmentType.WC_UNIT: ("PLU", "PLU-001", "WC double chasse", "Dual-flush WC", "u"),
    EquipmentType.LAVABO: ("PLU", "PLU-002", "Lavabo + robinet mitigeur", "Basin with mixer tap", "u"),
    EquipmentType.DOUCHE: ("PLU", "PLU-003", "Receveur douche + mitigeur", "Shower tray with mixer", "u"),
    EquipmentType.BAIGNOIRE: ("PLU", "PLU-004", "Baignoire + robinetterie", "Bathtub with fittings", "u"),
    EquipmentType.EVIER: ("PLU", "PLU-005", "Évier cuisine + mitigeur", "Kitchen sink with mixer", "u"),
    EquipmentType.LAVE_LINGE: ("PLU", "PLU-006", "Alimentation machine à laver", "Washing machine supply", "u"),
    EquipmentType.LAVE_VAISSELLE: ("PLU", "PLU-007", "Alimentation lave-vaisselle", "Dishwasher supply", "u"),
    EquipmentType.CHAUFFE_EAU: ("PLU", "PLU-008", "Chauffe-eau", "Water heater", "u"),
    # HVAC
    EquipmentType.CLIMATISEUR: ("HVC", "HVC-001", "Split climatiseur", "AC split unit", "u"),
    EquipmentType.UNITE_EXT: ("HVC", "HVC-002", "Groupe extérieur", "Outdoor unit", "u"),
    EquipmentType.BOUCHE_VMC: ("HVC", "HVC-003", "Bouche extraction VMC", "VMC extraction grille", "u"),
    EquipmentType.BOUCHE_SOUFFLAGE: ("HVC", "HVC-004", "Diffuseur soufflage", "Supply air diffuser", "u"),
    EquipmentType.HOTTE: ("HVC", "HVC-005", "Hotte aspirante", "Kitchen hood", "u"),
    # Electrical — high current
    EquipmentType.PRISE: ("HCU", "HCU-001", "Prise 2P+T 16A", "Socket outlet 2P+T 16A", "u"),
    EquipmentType.PRISE_PLAN_TRAVAIL: ("HCU", "HCU-002", "Prise plan de travail", "Worktop socket", "u"),
    EquipmentType.PRISE_ETANCHE: ("HCU", "HCU-003", "Prise étanche IP44", "Waterproof socket IP44", "u"),
    EquipmentType.INTERRUPTEUR: ("HCU", "HCU-004", "Interrupteur va-et-vient", "Two-way switch", "u"),
    EquipmentType.LUMINAIRE: ("HCU", "HCU-005", "Plafonnier LED", "LED ceiling light", "u"),
    EquipmentType.APPLIQUE: ("HCU", "HCU-006", "Applique murale", "Wall light", "u"),
    EquipmentType.TABLEAU_ELEC: ("HCU", "HCU-007", "Tableau électrique", "Distribution board", "u"),
    # Electrical — low current
    EquipmentType.PRISE_RJ45: ("LCU", "LCU-001", "Prise RJ45 Cat6", "RJ45 Cat6 data outlet", "u"),
    EquipmentType.PRISE_TV: ("LCU", "LCU-002", "Prise TV/SAT", "TV/SAT outlet", "u"),
    EquipmentType.INTERPHONE: ("LCU", "LCU-003", "Interphone vidéo", "Video intercom", "u"),
    EquipmentType.DETECTEUR_FUMEE: ("LCU", "LCU-004", "Détecteur de fumée", "Smoke detector", "u"),
    EquipmentType.DETECTEUR_CHALEUR: ("LCU", "LCU-005", "Détecteur de chaleur", "Heat detector", "u"),
    EquipmentType.BOUTON_PANIQUE: ("LCU", "LCU-006", "Bouton panique", "Panic button", "u"),
    EquipmentType.WIFI_AP: ("LCU", "LCU-007", "Point d'accès WiFi", "Wireless AP", "u"),
    # Fire safety
    EquipmentType.SPRINKLER: ("FIF", "FIF-001", "Tête sprinkler", "Sprinkler head", "u"),
    EquipmentType.SIRENE: ("FIF", "FIF-002", "Sirène incendie", "Fire sounder", "u"),
    EquipmentType.CDI: ("FIF", "FIF-003", "Centrale détection incendie", "Fire alarm panel", "u"),
    EquipmentType.RIA: ("FIF", "FIF-004", "RIA DN25/30m", "Fire hose reel DN25/30m", "u"),
}


# Network type → BOQ lot for pipe/duct/cable quantities
_NETWORK_BOQ_LOT = {
    NetworkType.PLU_EF: "PLU",
    NetworkType.PLU_EC: "PLU",
    NetworkType.PLU_EU: "PLU",
    NetworkType.PLU_EP: "PLU",
    NetworkType.HVC_SOUFFLAGE: "HVC",
    NetworkType.HVC_REPRISE: "HVC",
    NetworkType.HVC_VMC: "HVC",
    NetworkType.HVC_REF: "HVC",
    NetworkType.HVC_CONDENSAT: "HVC",
    NetworkType.ELEC_FORT: "HCU",
    NetworkType.ELEC_FAIBLE: "LCU",
    NetworkType.FIRE_SPK: "FIF",
    NetworkType.FIRE_DETECT: "FIF",
}


# ══════════════════════════════════════════════════════════════
# MAIN BOQ GENERATOR
# ══════════════════════════════════════════════════════════════

def generate_bim_boq(building: Building, lang: str = "fr") -> Dict[str, Any]:
    """Generate a complete BOQ from the BIM model.

    Returns a dict with:
      - lots: {lot_code: {label, items: [BOQItem]}}
      - summary: {total_items, total_pipe_m, total_duct_m, total_cable_m}
      - by_level: {level_name: {lot_code: item_count}}
    """
    # Count equipment by type, grouped by level
    equip_counts: Dict[EquipmentType, Dict[str, int]] = {}
    for level in building.levels:
        for room in level.rooms:
            for eq in room.equipment:
                if eq.type not in equip_counts:
                    equip_counts[eq.type] = {}
                equip_counts[eq.type][level.name] = \
                    equip_counts[eq.type].get(level.name, 0) + 1

    # Count network lengths by type and diameter, grouped by level
    network_lengths: Dict[str, Dict[str, float]] = {}  # "PLU_EF_25mm" → {level: meters}
    for level in building.levels:
        all_segs = list(level.network_segments)
        for room in level.rooms:
            all_segs.extend(room.network_segments)

        for seg in all_segs:
            length = math.sqrt(
                (seg.end.x - seg.start.x) ** 2 +
                (seg.end.y - seg.start.y) ** 2 +
                (seg.end.z - seg.start.z) ** 2
            )
            key = f"{seg.type.value}_{int(seg.diameter_mm)}mm"
            if key not in network_lengths:
                network_lengths[key] = {}
            network_lengths[key][level.name] = \
                network_lengths[key].get(level.name, 0.0) + length

    # Build BOQ items
    items: List[BOQItem] = []

    # Equipment items
    for eq_type, level_counts in sorted(equip_counts.items(), key=lambda x: x[0].value):
        mapping = _EQUIP_BOQ.get(eq_type)
        if not mapping:
            continue
        lot, code, label_fr, label_en, unit = mapping
        total = sum(level_counts.values())
        items.append(BOQItem(
            lot=lot, code=code,
            label_fr=label_fr, label_en=label_en,
            unit=unit, quantity=total,
            by_level=dict(level_counts),
        ))

    # Network items (pipes, ducts, cables)
    for net_key, level_lengths in sorted(network_lengths.items()):
        parts = net_key.rsplit("_", 1)
        net_type_val = parts[0]
        diam = parts[1] if len(parts) > 1 else ""

        # Find NetworkType
        net_type = None
        for nt in NetworkType:
            if nt.value == net_type_val:
                net_type = nt
                break
        if not net_type:
            continue

        lot = _NETWORK_BOQ_LOT.get(net_type, "")
        total_m = sum(level_lengths.values())
        if total_m < 0.1:
            continue

        label = _network_label(net_type, diam, lang)
        items.append(BOQItem(
            lot=lot,
            code=f"{lot}-NET-{net_type_val.upper()}",
            label_fr=label if lang == "fr" else label,
            label_en=label if lang == "en" else label,
            unit="ml",
            quantity=round(total_m, 1),
            by_level={k: round(v, 1) for k, v in level_lengths.items()},
        ))

    # Organize by lot
    lots = {}
    for item in items:
        if item.lot not in lots:
            lots[item.lot] = {
                "label": _lot_label(item.lot, lang),
                "items": [],
            }
        lots[item.lot]["items"].append(item)

    # Summary
    total_pipe_m = sum(
        item.quantity for item in items
        if item.unit == "ml" and item.lot == "PLU"
    )
    total_duct_m = sum(
        item.quantity for item in items
        if item.unit == "ml" and item.lot == "HVC"
    )
    total_cable_m = sum(
        item.quantity for item in items
        if item.unit == "ml" and item.lot in ("HCU", "LCU", "FIF")
    )

    # By level summary
    by_level = {}
    for level in building.levels:
        by_level[level.name] = {}
        for item in items:
            if level.name in item.by_level:
                by_level[level.name][item.lot] = \
                    by_level[level.name].get(item.lot, 0) + 1

    return {
        "lots": lots,
        "items": items,
        "summary": {
            "total_equipment": sum(1 for i in items if i.unit == "u"),
            "total_quantity": sum(i.quantity for i in items if i.unit == "u"),
            "total_pipe_m": round(total_pipe_m, 1),
            "total_duct_m": round(total_duct_m, 1),
            "total_cable_m": round(total_cable_m, 1),
        },
        "by_level": by_level,
    }


def _network_label(net_type: NetworkType, diam: str, lang: str) -> str:
    """Human-readable label for a network segment type."""
    labels = {
        NetworkType.PLU_EF: ("Tube cuivre EF", "Cold water copper pipe"),
        NetworkType.PLU_EC: ("Tube cuivre EC", "Hot water copper pipe"),
        NetworkType.PLU_EU: ("Tube PVC EU", "PVC waste pipe"),
        NetworkType.PLU_EP: ("Tube PVC EP", "PVC rainwater pipe"),
        NetworkType.HVC_SOUFFLAGE: ("Gaine soufflage", "Supply air duct"),
        NetworkType.HVC_REPRISE: ("Gaine reprise", "Return air duct"),
        NetworkType.HVC_VMC: ("Gaine VMC", "VMC extraction duct"),
        NetworkType.HVC_REF: ("Tube frigorifique", "Refrigerant pipe"),
        NetworkType.HVC_CONDENSAT: ("Tube condensat", "Condensate pipe"),
        NetworkType.ELEC_FORT: ("Câble U1000R2V", "Power cable U1000R2V"),
        NetworkType.ELEC_FAIBLE: ("Câble Cat6", "Cat6 data cable"),
        NetworkType.FIRE_SPK: ("Tube acier SPK", "Steel sprinkler pipe"),
        NetworkType.FIRE_DETECT: ("Câble détection incendie", "Fire detection cable"),
    }
    fr, en = labels.get(net_type, (net_type.value, net_type.value))
    label = fr if lang == "fr" else en
    if diam:
        label += f" Ø{diam}"
    return label


def _lot_label(lot_code: str, lang: str) -> str:
    """Human-readable lot label."""
    labels = {
        "PLU": ("LOT PLU — Plomberie Sanitaire", "LOT PLU — Plumbing"),
        "HVC": ("LOT HVC — CVC / Ventilation", "LOT HVC — HVAC"),
        "HCU": ("LOT HCU — Courants Forts", "LOT HCU — High Current"),
        "LCU": ("LOT LCU — Courants Faibles", "LOT LCU — Low Current"),
        "FIF": ("LOT FIF — Sécurité Incendie", "LOT FIF — Fire Safety"),
    }
    fr, en = labels.get(lot_code, (lot_code, lot_code))
    return fr if lang == "fr" else en


# ══════════════════════════════════════════════════════════════
# BOQ COMPARISON (BIM vs engine)
# ══════════════════════════════════════════════════════════════

def compare_bim_vs_engine(building: Building, resultats_mep) -> Dict[str, Any]:
    """Compare BIM-counted quantities vs engine-calculated quantities.
    Useful for debugging and validation."""
    bim_boq = generate_bim_boq(building)

    # Count BIM equipment by type
    bim_counts = {}
    for item in bim_boq["items"]:
        if item.unit == "u":
            bim_counts[item.code] = item.quantity

    # Engine counts (from ResultatsMEP)
    engine_counts = {}
    if resultats_mep:
        rm = resultats_mep
        if hasattr(rm, 'plomberie'):
            pl = rm.plomberie
            engine_counts["PLU-001"] = getattr(pl, 'nb_wc_double_chasse', 0)
            engine_counts["PLU-002"] = getattr(pl, 'nb_lavabos', 0)
            engine_counts["PLU-003"] = getattr(pl, 'nb_douches', 0)
            engine_counts["PLU-005"] = getattr(pl, 'nb_eviers', 0)
        if hasattr(rm, 'electrique'):
            el = rm.electrique
            engine_counts["HCU-001"] = getattr(el, 'nb_prises', 0)
            engine_counts["HCU-004"] = getattr(el, 'nb_interrupteurs', 0)
            engine_counts["HCU-005"] = getattr(el, 'nb_points_lumineux', 0)
        if hasattr(rm, 'cvc'):
            cv = rm.cvc
            engine_counts["HVC-001"] = getattr(cv, 'nb_splits', 0)
            engine_counts["HVC-003"] = getattr(cv, 'nb_bouches_vmc', 0)
        if hasattr(rm, 'securite_incendie'):
            si = rm.securite_incendie
            engine_counts["FIF-001"] = getattr(si, 'nb_sprinklers', 0)

    # Compare
    diffs = []
    all_codes = set(list(bim_counts.keys()) + list(engine_counts.keys()))
    for code in sorted(all_codes):
        bim_qty = bim_counts.get(code, 0)
        eng_qty = engine_counts.get(code, 0)
        if bim_qty != eng_qty:
            diffs.append({
                "code": code,
                "bim": bim_qty,
                "engine": eng_qty,
                "delta": bim_qty - eng_qty,
            })

    return {
        "match": len(diffs) == 0,
        "diffs": diffs,
        "bim_total": sum(bim_counts.values()),
        "engine_total": sum(engine_counts.values()),
    }
