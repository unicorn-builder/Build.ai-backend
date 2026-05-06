"""
bim_model.py — TijanBIM: Internal Building Information Model

Core data structure for Tijan AI. Every plan, calculation, and 3D view
is derived from this model. It replaces the flat parameter dict with
a topology-aware building graph.

Architecture:
    Building
      └── Level (RDC, Étage 1, ..., Terrasse)
            └── Room (typed: SDB, cuisine, chambre, séjour, couloir, ...)
                  ├── Wall (bearing/partition, interior/exterior faces, coords)
                  │     └── Opening (door/window, width/height)
                  ├── Equipment (placed ON a wall face or AT room center)
                  └── Network segments (plumbing, HVAC, electrical, fire)

All coordinates are in meters, origin bottom-left of building footprint.
"""
from __future__ import annotations
import math
import uuid
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Tuple, Any

logger = logging.getLogger("tijan.bim")


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class RoomType(Enum):
    """Room classification — drives equipment rules and MEP routing."""
    SEJOUR = "sejour"             # Living room / salon
    CHAMBRE = "chambre"           # Bedroom
    CUISINE = "cuisine"           # Kitchen
    SDB = "sdb"                   # Salle de bain (bathroom with shower/tub)
    WC = "wc"                     # Toilettes (separate WC)
    COULOIR = "couloir"           # Corridor / circulation
    FOYER = "foyer"               # Entrance foyer
    DRESSING = "dressing"         # Walk-in closet
    BUREAU = "bureau"             # Home office / workspace
    BUANDERIE = "buanderie"       # Laundry
    RANGEMENT = "rangement"       # Storage / linen
    BALCON = "balcon"             # Balcony (exterior)
    TERRASSE = "terrasse"         # Terrace (exterior)
    LOCAL_TECHNIQUE = "local_tech"  # Mechanical room
    PARKING = "parking"           # Parking
    COMMERCE = "commerce"         # Commercial space (ground floor)
    HALL = "hall"                 # Common hall / lobby
    ESCALIER = "escalier"         # Stairwell
    ASCENSEUR = "ascenseur"       # Elevator shaft
    INCONNU = "inconnu"           # Unknown — needs classification


class WallType(Enum):
    """Structural classification of walls."""
    PORTEUR = "porteur"           # Load-bearing (béton armé or CMU porteur)
    CLOISON = "cloison"           # Partition (non-bearing)
    FACADE = "facade"             # Exterior facade
    MITOYEN = "mitoyen"           # Party wall (between apartments)


class OpeningType(Enum):
    DOOR = "door"
    WINDOW = "window"
    BAIE_VITREE = "baie_vitree"   # Floor-to-ceiling glazing


class EquipmentType(Enum):
    """MEP equipment that gets placed in rooms."""
    # Plumbing
    WC_UNIT = "wc"
    LAVABO = "lavabo"
    DOUCHE = "douche"
    BAIGNOIRE = "baignoire"
    EVIER = "evier"               # Kitchen sink
    LAVE_LINGE = "lave_linge"
    LAVE_VAISSELLE = "lave_vaisselle"
    CHAUFFE_EAU = "chauffe_eau"
    # HVAC
    CLIMATISEUR = "climatiseur"   # Split unit (indoor)
    UNITE_EXT = "unite_ext"       # Outdoor unit
    BOUCHE_VMC = "bouche_vmc"     # VMC extraction grille
    BOUCHE_SOUFFLAGE = "bouche_soufflage"  # Supply air diffuser
    HOTTE = "hotte"               # Kitchen hood
    # Electrical — high current
    PRISE = "prise"               # Socket outlet 2P+T 16A
    PRISE_PLAN_TRAVAIL = "prise_plan_travail"  # Kitchen worktop socket
    PRISE_ETANCHE = "prise_etanche"  # Waterproof socket (SDB)
    INTERRUPTEUR = "interrupteur"
    LUMINAIRE = "luminaire"       # Ceiling light
    APPLIQUE = "applique"         # Wall light
    TABLEAU_ELEC = "tableau_elec"  # Electrical panel
    # Electrical — low current
    PRISE_RJ45 = "prise_rj45"    # Data outlet
    PRISE_TV = "prise_tv"         # TV outlet
    INTERPHONE = "interphone"
    DETECTEUR_FUMEE = "detecteur_fumee"
    DETECTEUR_CHALEUR = "detecteur_chaleur"
    BOUTON_PANIQUE = "bouton_panique"
    WIFI_AP = "wifi_ap"           # Wireless access point
    # Fire safety
    SPRINKLER = "sprinkler"
    SIRENE = "sirene"             # Wall-mounted sounder
    CDI = "cdi"                   # Fire panel
    RIA = "ria"                   # Robinet d'incendie armé


class NetworkType(Enum):
    """MEP network categories — matches Crystal Residence trade codes."""
    PLU_EF = "plu_ef"             # Eau froide (cold water) — blue
    PLU_EC = "plu_ec"             # Eau chaude (hot water) — red
    PLU_EU = "plu_eu"             # Eaux usées (waste water) — green
    PLU_EP = "plu_ep"             # Eaux pluviales (rainwater) — brown
    HVC_SOUFFLAGE = "hvc_soufflage"  # Supply air duct — blue
    HVC_REPRISE = "hvc_reprise"   # Return air duct — green
    HVC_VMC = "hvc_vmc"           # VMC extraction duct — purple
    HVC_REF = "hvc_ref"           # Refrigerant pipe — orange
    HVC_CONDENSAT = "hvc_condensat"  # Condensate drain
    ELEC_FORT = "elec_fort"       # High current circuit
    ELEC_FAIBLE = "elec_faible"   # Low current circuit
    FIRE_SPK = "fire_spk"         # Sprinkler pipe — red
    FIRE_DETECT = "fire_detect"   # Fire detection loop


class PlacementType(Enum):
    """How equipment is positioned in a room."""
    ON_WALL = "on_wall"           # Mounted on wall face (prises, lavabo, etc.)
    FLOOR_AGAINST_WALL = "floor_against_wall"  # On floor touching wall (WC, meuble)
    CEILING_CENTER = "ceiling_center"  # Centered on ceiling (luminaire)
    CEILING_ZONE = "ceiling_zone"  # In ceiling zone (sprinkler, VMC grille)
    FLOOR_CENTER = "floor_center"  # Floor center (shower tray)
    WALL_HIGH = "wall_high"       # High on wall (climatiseur, hotte)


# ══════════════════════════════════════════════════════════════
# GEOMETRY PRIMITIVES
# ══════════════════════════════════════════════════════════════

@dataclass
class Point:
    """2D point in meters from building origin."""
    x: float
    y: float

    def distance_to(self, other: Point) -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def midpoint(self, other: Point) -> Point:
        return Point((self.x + other.x) / 2, (self.y + other.y) / 2)

    def __add__(self, other: Point) -> Point:
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Point) -> Point:
        return Point(self.x - other.x, self.y - other.y)

    def to_3d(self, z: float = 0.0) -> Point3D:
        return Point3D(self.x, self.y, z)


@dataclass
class Point3D:
    """3D point in meters."""
    x: float
    y: float
    z: float


@dataclass
class BBox:
    """Axis-aligned bounding box."""
    min_pt: Point
    max_pt: Point

    @property
    def width(self) -> float:
        return abs(self.max_pt.x - self.min_pt.x)

    @property
    def height(self) -> float:
        return abs(self.max_pt.y - self.min_pt.y)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> Point:
        return self.min_pt.midpoint(self.max_pt)

    def contains(self, pt: Point) -> bool:
        return (self.min_pt.x <= pt.x <= self.max_pt.x and
                self.min_pt.y <= pt.y <= self.max_pt.y)


# ══════════════════════════════════════════════════════════════
# BUILDING ELEMENTS
# ══════════════════════════════════════════════════════════════

@dataclass
class Opening:
    """Door or window in a wall."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: OpeningType = OpeningType.DOOR
    width_m: float = 0.9            # Standard door width
    height_m: float = 2.1           # Standard door height
    sill_height_m: float = 0.0      # 0 for doors, ~1.0 for windows
    offset_along_wall_m: float = 0.0  # Distance from wall start to opening center
    label: str = ""


@dataclass
class Wall:
    """A wall segment with topology."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    start: Point = field(default_factory=lambda: Point(0, 0))
    end: Point = field(default_factory=lambda: Point(0, 0))
    thickness_m: float = 0.20       # Wall thickness in meters
    type: WallType = WallType.CLOISON
    openings: List[Opening] = field(default_factory=list)
    # Rooms on each side (set during graph construction)
    room_left_id: Optional[str] = None    # Room on left side (looking start→end)
    room_right_id: Optional[str] = None   # Room on right side

    @property
    def length_m(self) -> float:
        return self.start.distance_to(self.end)

    @property
    def midpoint(self) -> Point:
        return self.start.midpoint(self.end)

    @property
    def direction(self) -> Tuple[float, float]:
        """Unit vector from start to end."""
        d = self.length_m
        if d < 0.001:
            return (1.0, 0.0)
        return ((self.end.x - self.start.x) / d,
                (self.end.y - self.start.y) / d)

    @property
    def normal(self) -> Tuple[float, float]:
        """Normal vector pointing left (interior convention)."""
        dx, dy = self.direction
        return (-dy, dx)

    @property
    def is_horizontal(self) -> bool:
        return abs(self.end.y - self.start.y) < 0.05

    @property
    def is_vertical(self) -> bool:
        return abs(self.end.x - self.start.x) < 0.05

    def point_at_offset(self, offset_m: float) -> Point:
        """Point along wall at given offset from start."""
        dx, dy = self.direction
        return Point(self.start.x + dx * offset_m,
                     self.start.y + dy * offset_m)

    def interior_face_point(self, offset_m: float, room_id: str,
                            standoff_m: float = 0.05) -> Point:
        """Point on the interior face of the wall facing a given room."""
        pt = self.point_at_offset(offset_m)
        nx, ny = self.normal
        if self.room_left_id == room_id:
            return Point(pt.x + nx * standoff_m, pt.y + ny * standoff_m)
        else:
            return Point(pt.x - nx * standoff_m, pt.y - ny * standoff_m)


@dataclass
class EquipmentInstance:
    """A placed piece of equipment in a room."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: EquipmentType = EquipmentType.PRISE
    placement: PlacementType = PlacementType.ON_WALL
    position: Point = field(default_factory=lambda: Point(0, 0))
    wall_id: Optional[str] = None   # Which wall it's on (if ON_WALL)
    wall_offset_m: float = 0.0      # Offset along wall from wall start
    height_m: float = 0.3           # Installation height above floor
    label: str = ""
    # For dimensioned equipment (WC, lavabo, etc.)
    width_m: float = 0.0
    depth_m: float = 0.0


@dataclass
class NetworkSegment:
    """A pipe, duct, or cable segment in 3D space."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: NetworkType = NetworkType.PLU_EF
    start: Point3D = field(default_factory=lambda: Point3D(0, 0, 0))
    end: Point3D = field(default_factory=lambda: Point3D(0, 0, 0))
    diameter_mm: float = 25.0       # Pipe diameter or duct equivalent
    is_vertical: bool = False       # Riser / drop
    connects_to: Optional[str] = None  # Equipment or segment ID
    label: str = ""                 # e.g. "EF 25mm +290"


# ══════════════════════════════════════════════════════════════
# ROOM
# ══════════════════════════════════════════════════════════════

@dataclass
class Room:
    """A room with its walls, equipment, and network connections."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: RoomType = RoomType.INCONNU
    label: str = ""                 # Display name (e.g. "103-09")
    name: str = ""                  # Human name (e.g. "Master Bedroom")
    level_id: str = ""              # Parent level ID

    # Geometry
    polygon: List[Point] = field(default_factory=list)  # Room boundary (closed)
    wall_ids: List[str] = field(default_factory=list)    # Ordered wall references

    # Equipment and networks (populated by Phase 2 routers)
    equipment: List[EquipmentInstance] = field(default_factory=list)
    network_segments: List[NetworkSegment] = field(default_factory=list)

    # Computed properties (set during finalization)
    _area_m2: Optional[float] = field(default=None, repr=False)
    _perimeter_m: Optional[float] = field(default=None, repr=False)

    @property
    def area_m2(self) -> float:
        if self._area_m2 is not None:
            return self._area_m2
        if len(self.polygon) < 3:
            return 0.0
        # Shoelace formula
        n = len(self.polygon)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += self.polygon[i].x * self.polygon[j].y
            area -= self.polygon[j].x * self.polygon[i].y
        self._area_m2 = abs(area) / 2.0
        return self._area_m2

    @property
    def perimeter_m(self) -> float:
        if self._perimeter_m is not None:
            return self._perimeter_m
        if len(self.polygon) < 2:
            return 0.0
        p = sum(self.polygon[i].distance_to(self.polygon[(i + 1) % len(self.polygon)])
                for i in range(len(self.polygon)))
        self._perimeter_m = p
        return self._perimeter_m

    @property
    def center(self) -> Point:
        if not self.polygon:
            return Point(0, 0)
        cx = sum(p.x for p in self.polygon) / len(self.polygon)
        cy = sum(p.y for p in self.polygon) / len(self.polygon)
        return Point(cx, cy)

    @property
    def bbox(self) -> BBox:
        if not self.polygon:
            return BBox(Point(0, 0), Point(0, 0))
        xs = [p.x for p in self.polygon]
        ys = [p.y for p in self.polygon]
        return BBox(Point(min(xs), min(ys)), Point(max(xs), max(ys)))

    @property
    def is_wet(self) -> bool:
        """Is this a wet room (needs waterproofing, floor drain, etc.)."""
        return self.type in (RoomType.SDB, RoomType.WC, RoomType.CUISINE,
                             RoomType.BUANDERIE)

    @property
    def is_exterior(self) -> bool:
        return self.type in (RoomType.BALCON, RoomType.TERRASSE)

    @property
    def needs_hvac(self) -> bool:
        """Does this room need active cooling/heating."""
        return self.type in (RoomType.SEJOUR, RoomType.CHAMBRE, RoomType.BUREAU,
                             RoomType.CUISINE, RoomType.COMMERCE)

    @property
    def needs_vmc_extraction(self) -> bool:
        """Does this room need VMC extraction (humid air out)."""
        return self.type in (RoomType.SDB, RoomType.WC, RoomType.CUISINE,
                             RoomType.BUANDERIE)


# ══════════════════════════════════════════════════════════════
# LEVEL
# ══════════════════════════════════════════════════════════════

@dataclass
class Level:
    """A floor level of the building."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "RDC"               # Display name
    index: int = 0                  # 0 = RDC, -1 = sous-sol, 1+ = étages
    elevation_m: float = 0.0        # Floor elevation from ground
    height_m: float = 3.0           # Floor-to-floor height

    rooms: List[Room] = field(default_factory=list)
    walls: List[Wall] = field(default_factory=list)

    # Structural grid (from engine_structure calculations)
    axes_x: List[float] = field(default_factory=list)  # X coordinates of vertical axes
    axes_y: List[float] = field(default_factory=list)  # Y coordinates of horizontal axes
    axis_labels_x: List[str] = field(default_factory=list)  # "7", "7'", "8", "9", "10"
    axis_labels_y: List[str] = field(default_factory=list)  # "A", "B", "C", "D"

    # Network risers passing through this level
    network_segments: List[NetworkSegment] = field(default_factory=list)

    def room_by_id(self, room_id: str) -> Optional[Room]:
        for r in self.rooms:
            if r.id == room_id:
                return r
        return None

    def wall_by_id(self, wall_id: str) -> Optional[Wall]:
        for w in self.walls:
            if w.id == wall_id:
                return w
        return None

    def rooms_by_type(self, room_type: RoomType) -> List[Room]:
        return [r for r in self.rooms if r.type == room_type]

    @property
    def footprint_m2(self) -> float:
        return sum(r.area_m2 for r in self.rooms if not r.is_exterior)

    @property
    def bbox(self) -> BBox:
        all_pts = [p for r in self.rooms for p in r.polygon]
        if not all_pts:
            return BBox(Point(0, 0), Point(0, 0))
        xs = [p.x for p in all_pts]
        ys = [p.y for p in all_pts]
        return BBox(Point(min(xs), min(ys)), Point(max(xs), max(ys)))


# ══════════════════════════════════════════════════════════════
# BUILDING
# ══════════════════════════════════════════════════════════════

@dataclass
class Building:
    """Top-level BIM container for a Tijan project."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Projet Tijan"
    city: str = "Dakar"
    country: str = "Senegal"
    usage: str = "residentiel"       # residentiel / bureau / hotel / commercial
    reference: str = ""              # Project reference number

    levels: List[Level] = field(default_factory=list)

    # Global structural info (from ParamsProjet / ResultatsStructure)
    classe_beton: str = "C30/37"
    classe_acier: str = "HA500"
    zone_sismique: int = 2
    pression_sol_MPa: float = 0.15
    distance_mer_km: float = 5.0

    # Parsing metadata
    source_format: str = ""          # "pdf" / "dwg" / "dxf" / "manual"
    source_file: str = ""
    parse_confidence: float = 0.0    # 0.0-1.0

    # ── Level management ──

    def add_level(self, name: str, index: int, height_m: float = 3.0,
                  elevation_m: Optional[float] = None) -> Level:
        if elevation_m is None:
            elevation_m = index * height_m
        lvl = Level(name=name, index=index, elevation_m=elevation_m,
                    height_m=height_m)
        self.levels.append(lvl)
        self.levels.sort(key=lambda l: l.index)
        return lvl

    def level_by_index(self, index: int) -> Optional[Level]:
        for lvl in self.levels:
            if lvl.index == index:
                return lvl
        return None

    def level_by_name(self, name: str) -> Optional[Level]:
        for lvl in self.levels:
            if lvl.name == name:
                return lvl
        return None

    @property
    def nb_niveaux(self) -> int:
        return len([l for l in self.levels if l.index >= 0])

    @property
    def nb_sous_sols(self) -> int:
        return len([l for l in self.levels if l.index < 0])

    @property
    def hauteur_totale_m(self) -> float:
        if not self.levels:
            return 0.0
        return max(l.elevation_m + l.height_m for l in self.levels) - \
               min(l.elevation_m for l in self.levels)

    @property
    def surface_emprise_m2(self) -> float:
        """Footprint = largest level footprint."""
        if not self.levels:
            return 0.0
        return max(l.footprint_m2 for l in self.levels)

    @property
    def all_rooms(self) -> List[Room]:
        return [r for lvl in self.levels for r in lvl.rooms]

    @property
    def all_walls(self) -> List[Wall]:
        return [w for lvl in self.levels for w in lvl.walls]

    # ── Statistics ──

    def stats(self) -> Dict[str, Any]:
        """Summary statistics for the building model."""
        rooms = self.all_rooms
        return {
            "name": self.name,
            "city": self.city,
            "levels": len(self.levels),
            "rooms": len(rooms),
            "walls": len(self.all_walls),
            "surface_emprise_m2": round(self.surface_emprise_m2, 1),
            "hauteur_totale_m": round(self.hauteur_totale_m, 1),
            "room_types": {rt.value: len([r for r in rooms if r.type == rt])
                          for rt in RoomType if any(r.type == rt for r in rooms)},
            "equipment_count": sum(len(r.equipment) for r in rooms),
            "network_segments": sum(len(r.network_segments) for r in rooms) +
                               sum(len(l.network_segments) for l in self.levels),
        }

    # ── Conversion to/from legacy ParamsProjet ──

    def to_params_dict(self) -> Dict[str, Any]:
        """Convert to flat ParamsProjet-compatible dict for engine compatibility."""
        bbox = self.levels[0].bbox if self.levels else BBox(Point(0, 0), Point(10, 10))
        # Estimate grid from axes
        lvl = self.levels[0] if self.levels else None
        axes_x = lvl.axes_x if lvl else []
        axes_y = lvl.axes_y if lvl else []
        portees_x = [axes_x[i + 1] - axes_x[i] for i in range(len(axes_x) - 1)] if len(axes_x) > 1 else [5.5]
        portees_y = [axes_y[i + 1] - axes_y[i] for i in range(len(axes_y) - 1)] if len(axes_y) > 1 else [4.0]

        return {
            "nom": self.name,
            "ville": self.city,
            "pays": self.country,
            "usage": self.usage,
            "nb_niveaux": self.nb_niveaux,
            "hauteur_etage_m": self.levels[0].height_m if self.levels else 3.0,
            "surface_emprise_m2": round(self.surface_emprise_m2, 1),
            "portee_max_m": round(max(portees_x + portees_y), 2) if portees_x else 5.5,
            "portee_min_m": round(min(portees_x + portees_y), 2) if portees_x else 4.0,
            "nb_travees_x": max(len(axes_x) - 1, 1),
            "nb_travees_y": max(len(axes_y) - 1, 1),
            "classe_beton": self.classe_beton,
            "classe_acier": self.classe_acier,
            "pression_sol_MPa": self.pression_sol_MPa,
            "distance_mer_km": self.distance_mer_km,
            "zone_sismique": self.zone_sismique,
        }

    @classmethod
    def from_params_dict(cls, params: Dict[str, Any]) -> Building:
        """Create a Building from legacy ParamsProjet dict with parametric grid.
        This is the backward-compatibility bridge."""
        b = cls(
            name=params.get("nom", "Projet Tijan"),
            city=params.get("ville", "Dakar"),
            country=params.get("pays", "Senegal"),
            usage=params.get("usage", "residentiel"),
            classe_beton=params.get("classe_beton", "C30/37"),
            classe_acier=params.get("classe_acier", "HA500"),
            zone_sismique=params.get("zone_sismique", 2),
            pression_sol_MPa=params.get("pression_sol_MPa", 0.15),
            distance_mer_km=params.get("distance_mer_km", 5.0),
            source_format="params_dict",
        )

        nb_niveaux = params.get("nb_niveaux", 4)
        he = params.get("hauteur_etage_m", 3.0)
        nx = params.get("nb_travees_x", 3)
        ny = params.get("nb_travees_y", 2)
        px = params.get("portee_max_m", 5.5)
        py = params.get("portee_min_m", 4.0)

        # Build axis grid
        axes_x = [i * px for i in range(nx + 1)]
        axes_y = [j * py for j in range(ny + 1)]
        labels_x = [str(i + 1) for i in range(nx + 1)]
        labels_y = [chr(65 + j) for j in range(ny + 1)]  # A, B, C, ...

        # Create levels
        for idx in range(nb_niveaux):
            if idx == 0:
                name = "RDC"
            else:
                name = f"Étage {idx}"
            lvl = b.add_level(name=name, index=idx, height_m=he)
            lvl.axes_x = list(axes_x)
            lvl.axes_y = list(axes_y)
            lvl.axis_labels_x = list(labels_x)
            lvl.axis_labels_y = list(labels_y)

            # Create rooms from grid cells (basic parametric layout)
            _create_parametric_rooms(lvl, nx, ny, axes_x, axes_y)

        return b

    # ── Serialization ──

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the full building to a dict (for JSON storage / API)."""
        return {
            "id": self.id,
            "name": self.name,
            "city": self.city,
            "country": self.country,
            "usage": self.usage,
            "reference": self.reference,
            "classe_beton": self.classe_beton,
            "classe_acier": self.classe_acier,
            "zone_sismique": self.zone_sismique,
            "source_format": self.source_format,
            "levels": [_level_to_dict(lvl) for lvl in self.levels],
            "stats": self.stats(),
        }


# ══════════════════════════════════════════════════════════════
# PARAMETRIC ROOM LAYOUT (backward compat)
# ══════════════════════════════════════════════════════════════

def _create_parametric_rooms(level: Level, nx: int, ny: int,
                              axes_x: List[float], axes_y: List[float]):
    """Fill a level with rooms from a parametric grid.
    Used when we only have ParamsProjet (no parsed geometry).
    Assigns room types based on typical West African residential layout."""

    # For a typical residential floor:
    # Row 0 (bottom): foyer, cuisine, WC invité, rangement
    # Row 1+ (middle/top): séjour, chambres, SDB, couloir

    usage_grid = _residential_grid(nx, ny)

    for j in range(ny):
        for i in range(nx):
            x0, x1 = axes_x[i], axes_x[i + 1]
            y0, y1 = axes_y[j], axes_y[j + 1]

            room_type, room_name = usage_grid[j][i]

            polygon = [Point(x0, y0), Point(x1, y0),
                       Point(x1, y1), Point(x0, y1)]

            room = Room(
                type=room_type,
                name=room_name,
                label=f"{level.name}-{chr(65 + j)}{i + 1}",
                level_id=level.id,
                polygon=polygon,
            )

            # Create walls for this cell
            walls = _create_cell_walls(room, x0, y0, x1, y1, i, j, nx, ny, level)
            room.wall_ids = [w.id for w in walls]
            level.rooms.append(room)


def _residential_grid(nx: int, ny: int) -> List[List[Tuple[RoomType, str]]]:
    """Generate a plausible room type grid for residential usage."""
    grid = []

    for j in range(ny):
        row = []
        for i in range(nx):
            if j == 0:
                # Bottom row: entrance zone
                if i == 0:
                    rt = (RoomType.CUISINE, "Cuisine")
                elif i == nx - 1:
                    rt = (RoomType.RANGEMENT, "Rangement")
                elif i == 1:
                    rt = (RoomType.FOYER, "Foyer")
                else:
                    rt = (RoomType.WC, "WC Invité")
            elif j == ny - 1:
                # Top row: bedrooms
                if i == 0:
                    rt = (RoomType.SEJOUR, "Séjour + Salle à manger")
                elif i == nx - 1:
                    rt = (RoomType.CHAMBRE, "Chambre Amis")
                else:
                    rt = (RoomType.CHAMBRE, f"Chambre {i}")
            else:
                # Middle rows
                if i == 0:
                    rt = (RoomType.BUREAU, "Bureau")
                elif i == nx - 1:
                    rt = (RoomType.SDB, f"Salle de Bain {j}")
                elif i == nx - 2:
                    rt = (RoomType.DRESSING, "Dressing")
                else:
                    rt = (RoomType.COULOIR, "Circulation")
            row.append(rt)
        grid.append(row)

    return grid


def _create_cell_walls(room: Room, x0: float, y0: float, x1: float, y1: float,
                        i: int, j: int, nx: int, ny: int,
                        level: Level) -> List[Wall]:
    """Create walls for a grid cell. Shares walls with adjacent cells."""
    walls = []

    # Bottom wall
    w_bottom = Wall(
        start=Point(x0, y0), end=Point(x1, y0),
        thickness_m=0.20 if j == 0 else 0.10,
        type=WallType.FACADE if j == 0 else WallType.CLOISON,
        room_left_id=room.id,
    )
    walls.append(w_bottom)
    level.walls.append(w_bottom)

    # Right wall
    w_right = Wall(
        start=Point(x1, y0), end=Point(x1, y1),
        thickness_m=0.20 if i == nx - 1 else 0.10,
        type=WallType.FACADE if i == nx - 1 else WallType.CLOISON,
        room_left_id=room.id,
    )
    walls.append(w_right)
    level.walls.append(w_right)

    # Top wall
    w_top = Wall(
        start=Point(x1, y1), end=Point(x0, y1),
        thickness_m=0.20 if j == ny - 1 else 0.10,
        type=WallType.FACADE if j == ny - 1 else WallType.CLOISON,
        room_left_id=room.id,
    )
    walls.append(w_top)
    level.walls.append(w_top)

    # Left wall
    w_left = Wall(
        start=Point(x0, y1), end=Point(x0, y0),
        thickness_m=0.20 if i == 0 else 0.10,
        type=WallType.FACADE if i == 0 else WallType.CLOISON,
        room_left_id=room.id,
    )
    walls.append(w_left)
    level.walls.append(w_left)

    # Add a door on one interior wall
    for w in walls:
        if w.type == WallType.CLOISON and w.length_m > 1.5:
            w.openings.append(Opening(
                type=OpeningType.DOOR,
                width_m=0.9,
                height_m=2.1,
                offset_along_wall_m=w.length_m / 2,
            ))
            break

    # Add windows on facade walls for habitable rooms
    habitable = room.type in (RoomType.SEJOUR, RoomType.CHAMBRE, RoomType.BUREAU,
                               RoomType.CUISINE)
    if habitable:
        for w in walls:
            if w.type == WallType.FACADE and w.length_m > 2.0:
                w.openings.append(Opening(
                    type=OpeningType.WINDOW,
                    width_m=1.4,
                    height_m=1.2,
                    sill_height_m=1.0,
                    offset_along_wall_m=w.length_m / 2,
                ))

    return walls


# ══════════════════════════════════════════════════════════════
# SERIALIZATION HELPERS
# ══════════════════════════════════════════════════════════════

def _point_to_dict(p: Point) -> Dict:
    return {"x": round(p.x, 3), "y": round(p.y, 3)}

def _point3d_to_dict(p: Point3D) -> Dict:
    return {"x": round(p.x, 3), "y": round(p.y, 3), "z": round(p.z, 3)}

def _opening_to_dict(o: Opening) -> Dict:
    return {
        "id": o.id, "type": o.type.value,
        "width_m": o.width_m, "height_m": o.height_m,
        "sill_height_m": o.sill_height_m,
        "offset_along_wall_m": round(o.offset_along_wall_m, 3),
        "label": o.label,
    }

def _wall_to_dict(w: Wall) -> Dict:
    return {
        "id": w.id,
        "start": _point_to_dict(w.start), "end": _point_to_dict(w.end),
        "thickness_m": w.thickness_m, "type": w.type.value,
        "length_m": round(w.length_m, 3),
        "openings": [_opening_to_dict(o) for o in w.openings],
        "room_left_id": w.room_left_id, "room_right_id": w.room_right_id,
    }

def _equipment_to_dict(e: EquipmentInstance) -> Dict:
    return {
        "id": e.id, "type": e.type.value, "placement": e.placement.value,
        "position": _point_to_dict(e.position),
        "wall_id": e.wall_id, "wall_offset_m": round(e.wall_offset_m, 3),
        "height_m": e.height_m, "label": e.label,
    }

def _segment_to_dict(s: NetworkSegment) -> Dict:
    return {
        "id": s.id, "type": s.type.value,
        "start": _point3d_to_dict(s.start), "end": _point3d_to_dict(s.end),
        "diameter_mm": s.diameter_mm, "is_vertical": s.is_vertical,
        "connects_to": s.connects_to, "label": s.label,
    }

def _room_to_dict(r: Room) -> Dict:
    return {
        "id": r.id, "type": r.type.value, "label": r.label, "name": r.name,
        "polygon": [_point_to_dict(p) for p in r.polygon],
        "wall_ids": r.wall_ids,
        "area_m2": round(r.area_m2, 2),
        "center": _point_to_dict(r.center),
        "equipment": [_equipment_to_dict(e) for e in r.equipment],
        "network_segments": [_segment_to_dict(s) for s in r.network_segments],
    }

def _level_to_dict(lvl: Level) -> Dict:
    return {
        "id": lvl.id, "name": lvl.name, "index": lvl.index,
        "elevation_m": lvl.elevation_m, "height_m": lvl.height_m,
        "axes_x": [round(x, 3) for x in lvl.axes_x],
        "axes_y": [round(y, 3) for y in lvl.axes_y],
        "axis_labels_x": lvl.axis_labels_x,
        "axis_labels_y": lvl.axis_labels_y,
        "rooms": [_room_to_dict(r) for r in lvl.rooms],
        "walls": [_wall_to_dict(w) for w in lvl.walls],
        "footprint_m2": round(lvl.footprint_m2, 1),
        "network_segments": [_segment_to_dict(s) for s in lvl.network_segments],
    }
