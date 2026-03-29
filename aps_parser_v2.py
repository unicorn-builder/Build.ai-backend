"""
Tijan AI — aps_parser_v2.py
Pipeline DWG parsing via Autodesk Platform Services (APS).
Validated workflow: Auth → S3 Upload → Model Derivative → Property Extraction.

Uses Developer Hub app "Tijan AI Backend" (NOT @personal).
All endpoints validated on Free tier, March 28, 2026.
"""

import os
import time
import json
import base64
import logging
import tempfile
from typing import Optional, Dict, List, Any
from collections import Counter

import requests

logger = logging.getLogger("aps_parser")

# ════════════════════════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════════════════════════

APS_CLIENT_ID = os.getenv("APS_CLIENT_ID", "")
APS_CLIENT_SECRET = os.getenv("APS_CLIENT_SECRET", "")
APS_BUCKET = os.getenv("APS_BUCKET", "tijan-ai-prod")

APS_AUTH_URL = "https://developer.api.autodesk.com/authentication/v2/token"
APS_OSS_URL = "https://developer.api.autodesk.com/oss/v2/buckets"
APS_MD_URL = "https://developer.api.autodesk.com/modelderivative/v2/designdata"

# ════════════════════════════════════════════════════════════
# AUTH — token cache
# ════════════════════════════════════════════════════════════

_token_cache: Dict[str, Any] = {"token": None, "expires_at": 0}


def get_token() -> str:
    """Get or refresh APS access token."""
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 120:
        return _token_cache["token"]

    if not APS_CLIENT_ID or not APS_CLIENT_SECRET:
        raise EnvironmentError(
            "APS_CLIENT_ID et APS_CLIENT_SECRET requis. "
            "Configurez-les dans les variables d'environnement Render."
        )

    r = requests.post(APS_AUTH_URL, data={
        "client_id": APS_CLIENT_ID,
        "client_secret": APS_CLIENT_SECRET,
        "grant_type": "client_credentials",
        "scope": "data:read data:write data:create bucket:create bucket:read viewables:read",
    }, timeout=15)
    r.raise_for_status()
    data = r.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = now + data["expires_in"]
    logger.info("APS token refreshed, expires in %ds", data["expires_in"])
    return _token_cache["token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ════════════════════════════════════════════════════════════
# BUCKET — ensure exists
# ════════════════════════════════════════════════════════════

def ensure_bucket(token: str) -> None:
    """Create bucket if it doesn't exist. 409 = already exists = OK."""
    r = requests.post(
        APS_OSS_URL,
        headers={**auth_headers(token), "Content-Type": "application/json"},
        json={"bucketKey": APS_BUCKET, "policyKey": "transient"},
        timeout=15,
    )
    if r.status_code not in (200, 409):
        logger.error("Bucket creation failed: %s %s", r.status_code, r.text[:200])
        r.raise_for_status()
    logger.info("Bucket '%s' ready", APS_BUCKET)


# ════════════════════════════════════════════════════════════
# UPLOAD — Direct-to-S3 (signed URL workflow)
# ════════════════════════════════════════════════════════════

def upload_file(filepath: str, object_key: str, token: str) -> str:
    """
    Upload file to APS OSS via signed S3 URL.
    Returns the base64-encoded URN for Model Derivative.
    """
    with open(filepath, "rb") as f:
        content = f.read()

    file_size = len(content)
    logger.info("Uploading %s (%.1f MB)...", object_key, file_size / 1024 / 1024)

    # Step 1: Get signed URL
    url = f"{APS_OSS_URL}/{APS_BUCKET}/objects/{object_key}/signeds3upload"
    r = requests.get(url, headers=auth_headers(token), timeout=15)
    r.raise_for_status()
    signed_data = r.json()
    upload_url = signed_data["urls"][0]
    upload_key = signed_data["uploadKey"]

    # Step 2: PUT to S3
    r = requests.put(upload_url, data=content, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"S3 upload failed: {r.status_code} {r.text[:200]}")
    etag = r.headers.get("ETag", "").strip('"')
    logger.info("S3 upload OK, ETag=%s", etag)

    # Step 3: Finalize
    r = requests.post(
        url,
        headers={**auth_headers(token), "Content-Type": "application/json"},
        json={"uploadKey": upload_key, "size": file_size, "eTags": [etag]},
        timeout=30,
    )
    r.raise_for_status()
    object_id = r.json().get("objectId", f"urn:adsk.objects:os.object:{APS_BUCKET}/{object_key}")
    logger.info("Finalize OK: %s", object_id)

    # Encode URN for Model Derivative
    urn = base64.urlsafe_b64encode(object_id.encode()).decode().rstrip("=")
    return urn


# ════════════════════════════════════════════════════════════
# MODEL DERIVATIVE — translation + polling
# ════════════════════════════════════════════════════════════

def start_translation(urn: str, token: str) -> dict:
    """Start DWG → SVF2 translation job."""
    r = requests.post(
        f"{APS_MD_URL}/job",
        headers={**auth_headers(token), "Content-Type": "application/json"},
        json={
            "input": {"urn": urn},
            "output": {"formats": [{"type": "svf2", "views": ["2d", "3d"]}]},
        },
        timeout=30,
    )
    r.raise_for_status()
    result = r.json()
    logger.info("Translation started: %s", result.get("result", "?"))
    return result


def wait_for_translation(urn: str, token: str, timeout_s: int = 300) -> dict:
    """Poll manifest until translation is complete or timeout."""
    start = time.time()
    while time.time() - start < timeout_s:
        r = requests.get(
            f"{APS_MD_URL}/{urn}/manifest",
            headers=auth_headers(token),
            timeout=15,
        )
        if r.status_code != 200:
            time.sleep(5)
            continue
        manifest = r.json()
        progress = manifest.get("progress", "")
        status = manifest.get("status", "")
        logger.info("Translation: progress=%s status=%s", progress, status)

        if progress == "complete":
            if status == "success":
                return manifest
            elif status == "failed":
                raise RuntimeError(f"Translation failed: {json.dumps(manifest)[:500]}")

        time.sleep(5)

    raise TimeoutError(f"Translation timeout after {timeout_s}s")


# ════════════════════════════════════════════════════════════
# METADATA — extract geometry from properties
# ════════════════════════════════════════════════════════════

def get_viewable_guids(urn: str, token: str) -> List[Dict]:
    """Get list of viewable GUIDs from metadata."""
    r = requests.get(
        f"{APS_MD_URL}/{urn}/metadata",
        headers=auth_headers(token),
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("data", {}).get("metadata", [])


def get_properties(urn: str, guid: str, token: str, max_retries: int = 10) -> List[Dict]:
    """
    Get all object properties for a viewable.
    Retries on 202 (processing) up to max_retries times.
    """
    url = f"{APS_MD_URL}/{urn}/metadata/{guid}/properties?forceget=true"
    for attempt in range(max_retries):
        r = requests.get(url, headers=auth_headers(token), timeout=60)
        if r.status_code == 200:
            return r.json().get("data", {}).get("collection", [])
        elif r.status_code == 202:
            logger.info("Properties processing (attempt %d/%d)...", attempt + 1, max_retries)
            time.sleep(10)
        else:
            logger.warning("Properties request failed: %s", r.status_code)
            time.sleep(5)
    logger.warning("Properties not ready after %d attempts", max_retries)
    return []


def extract_geometry(properties: List[Dict]) -> Dict[str, Any]:
    """
    Extract structural geometry from APS properties.
    Returns axes, dimensions, layers, emprise for the Eurocodes engine.

    Logic for axes:
    - Axes in DWG are lines on the "axes" layer, all drawn at same angle (e.g. 180°).
    - Axes in one direction (X) have one length, axes in the other (Y) have a different length.
    - The longer group = axes spanning the longer dimension of the building.
    - Count per group = number of axes in that direction.
    - Axes are duplicated per floor level, so we divide by estimated nb_niveaux_in_dwg.

    Logic for dimensions:
    - Measurement field in Text properties = dimension value in display units.
    - Dim scale linear tells us the conversion (0.1 = drawing in mm, display in cm).
    - Portées = dimensions between 200-1000 cm (structural spans).
    - Mur épaisseurs = dimensions 10-50 cm.
    """
    layers = Counter()
    axes_lines = []
    dimensions = []
    mur_count = 0
    texts = []

    for item in properties:
        p = item.get("properties", {})
        gen = p.get("General", {})
        geom = p.get("Geometry", {})
        text_props = p.get("Text", {})

        layer = gen.get("Layer", "")
        obj_type = gen.get("Name ", "")

        if layer:
            layers[layer] += 1

        # Axes
        if layer.lower() in ("axes", "axe", "axis", "a-axes", "grille"):
            length_str = geom.get("Length", "0")
            angle_str = geom.get("Angle", "0")
            try:
                length = float(length_str.replace(",", "."))
                angle = float(angle_str.replace(" deg", "").replace(",", "."))
            except (ValueError, AttributeError):
                length, angle = 0, 0
            if length > 100:  # ignore tiny lines
                axes_lines.append({"length_mm": length, "angle_deg": angle})

        # Dimensions (cotations)
        if obj_type in ("Rotated Dimension", "Aligned Dimension", "Linear Dimension"):
            measurement = text_props.get("Measurement", "")
            dim_scale = p.get("Primary Units", {}).get("Dim scale linear", "1")
            try:
                value = float(measurement.replace(",", ".")) if measurement else 0
                scale = float(dim_scale.replace(",", ".")) if dim_scale else 1
            except (ValueError, AttributeError):
                value, scale = 0, 1
            if value > 0:
                dimensions.append({
                    "value": value,
                    "scale": scale,
                    "layer": layer,
                })

        # Walls
        if layer.upper() in ("MUR", "MURS", "A-MUR", "WALL", "WALLS"):
            mur_count += 1

        # Texts (room labels, etc.)
        if obj_type in ("MText", "Text") and layer in ("Etiquettes de pièces", "TEXTES", "TEXT_3"):
            name = item.get("name", "")
            if name:
                texts.append(name)

    # ── Analyze axes: group by length to find X vs Y directions ──
    # In a typical DWG, axes in X-direction all have the same length (spanning Y),
    # and axes in Y-direction all have the same length (spanning X).
    length_counts = Counter()
    for ax in axes_lines:
        # Round to nearest 100mm to group similar lengths
        rounded = round(ax["length_mm"] / 100) * 100
        length_counts[rounded] += 1

    # Sort by count descending — the two most common lengths are our axis groups
    top_lengths = length_counts.most_common()
    logger.info("Axis length groups: %s", top_lengths[:5])

    if len(top_lengths) >= 2:
        # Two groups: longer length = emprise in that direction
        len_a, count_a = top_lengths[0]
        len_b, count_b = top_lengths[1]
        # The longer lines span the longer dimension
        if len_a >= len_b:
            emprise_long_mm = len_a
            emprise_short_mm = len_b
            axes_along_long = count_a  # axes parallel to long side
            axes_along_short = count_b  # axes parallel to short side
        else:
            emprise_long_mm = len_b
            emprise_short_mm = len_a
            axes_along_long = count_b
            axes_along_short = count_a

        # Axes are duplicated per floor in the DWG.
        # Estimate floors from the repetition pattern.
        # If we have N total axes and they repeat for each floor,
        # the true count per direction = total / nb_floors_in_dwg.
        # For Sakho: 9 levels in DWG, axes repeated per layout.
        # Heuristic: if count > 20, likely duplicated across floors.
        # Use GCD or simple division to find the base count.
        def deduplicate_axes(count, length_mm):
            """Estimate real axis count by finding likely duplication factor."""
            if count <= 15:
                return count
            # Try common floor counts (2-12)
            for floors in range(12, 1, -1):
                if count % floors == 0:
                    base = count // floors
                    if 3 <= base <= 15:  # reasonable axis count
                        return base
            # Fallback: assume axes repeated for ~8 floors
            base = round(count / 8)
            return max(base, 3)

        nb_axes_x = deduplicate_axes(axes_along_short, emprise_short_mm)
        nb_axes_y = deduplicate_axes(axes_along_long, emprise_long_mm)

        # Emprise: axes spanning X = emprise_x, axes spanning Y = emprise_y
        # Axes along short side span the long dimension
        emprise_x_mm = emprise_long_mm
        emprise_y_mm = emprise_short_mm

    elif len(top_lengths) == 1:
        # All axes same length — square building or single direction
        length, count = top_lengths[0]
        emprise_x_mm = length
        emprise_y_mm = length * 0.7  # estimate
        nb_axes_x = min(count, 8)
        nb_axes_y = max(int(nb_axes_x * 0.7), 3)

    else:
        # No axes found
        emprise_x_mm = 0
        emprise_y_mm = 0
        nb_axes_x = 0
        nb_axes_y = 0

    # ── Analyze dimensions to find portées ──
    dim_values = sorted(set(d["value"] for d in dimensions))
    # Portées structurelles = entre-axes typiques (300-1000 cm)
    portees = [v for v in dim_values if 250 <= v <= 1000]
    # Épaisseurs murs (15-30 cm)
    mur_eps = [v for v in dim_values if 10 <= v <= 50]

    # ── Calculate portées from axes if dimensions don't give clear spans ──
    nb_travees_x = max(nb_axes_x - 1, 1)
    nb_travees_y = max(nb_axes_y - 1, 1)

    if portees:
        portee_max = max(portees) / 100  # cm → m
        portee_min = min(portees) / 100
    elif nb_travees_x > 0 and emprise_x_mm > 0:
        # Estimate portée from emprise / nb_travées
        portee_x = (emprise_x_mm / nb_travees_x) / 1000  # mm → m
        portee_y = (emprise_y_mm / nb_travees_y) / 1000
        portee_max = max(portee_x, portee_y)
        portee_min = min(portee_x, portee_y)
    else:
        portee_max = 5.0
        portee_min = 4.0

    # Clamp portées to reasonable structural range
    portee_max = min(max(portee_max, 3.0), 12.0)
    portee_min = min(max(portee_min, 2.5), portee_max)

    # ── Surface emprise ──
    emprise_x_m = emprise_x_mm / 1000
    emprise_y_m = emprise_y_mm / 1000
    surface = emprise_x_m * emprise_y_m
    # For very large values (axes span full drawing), use 70% as building footprint
    if surface > 5000:
        surface = surface * 0.7

    return {
        "layers": dict(layers.most_common(20)),
        "nb_axes_x": nb_axes_x,
        "nb_axes_y": nb_axes_y,
        "axes_raw_count": len(axes_lines),
        "axes_length_groups": [(l, c) for l, c in top_lengths[:5]],
        "emprise_x_mm": emprise_x_mm,
        "emprise_y_mm": emprise_y_mm,
        "emprise_x_m": round(emprise_x_m, 2),
        "emprise_y_m": round(emprise_y_m, 2),
        "surface_emprise_m2": round(surface, 1),
        "nb_travees_x": nb_travees_x,
        "nb_travees_y": nb_travees_y,
        "portee_max_m": round(portee_max, 2),
        "portee_min_m": round(portee_min, 2),
        "portees_cm": portees[:20],
        "epaisseurs_mur_cm": mur_eps[:10],
        "nb_murs": mur_count,
        "nb_dimensions": len(dimensions),
        "nb_total_objects": len(properties),
        "room_labels": texts[:20],
    }


# ════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ════════════════════════════════════════════════════════════



def extract_layer_objects(properties: list, layer_name: str) -> list:
    """
    Extract all objects from a specific DWG layer with their coordinates.
    Returns list of {type, layer, x, y, x2, y2, width, height, text, ...}
    """
    objects = []
    for item in properties:
        p = item.get("properties", {})
        gen = p.get("General", {})
        geom = p.get("Geometry", {})
        text_props = p.get("Text", {})

        layer = gen.get("Layer", "")
        if layer.upper() != layer_name.upper():
            continue

        obj_type = gen.get("Name ", "") or gen.get("Name", "")

        # Extract coordinates
        obj = {
            "id": item.get("objectid", ""),
            "name": item.get("name", ""),
            "type": obj_type,
            "layer": layer,
        }

        # Dump ALL property groups for debugging
        obj["all_props"] = {grp: dict(vals) for grp, vals in p.items()
                           if isinstance(vals, dict)}

        # Position
        for key in ("Position X", "Start X", "Center X", "Insertion Point X",
                    "X", "Origin X", "Base Point X"):
            if key in geom:
                try: obj["x"] = float(str(geom[key]).replace(",","."))
                except: pass
                break

        for key in ("Position Y", "Start Y", "Center Y", "Insertion Point Y"):
            if key in geom:
                try: obj["y"] = float(str(geom[key]).replace(",","."))
                except: pass
                break

        for key in ("End X", "Position X 2"):
            if key in geom:
                try: obj["x2"] = float(str(geom[key]).replace(",","."))
                except: pass
                break

        for key in ("End Y", "Position Y 2"):
            if key in geom:
                try: obj["y2"] = float(str(geom[key]).replace(",","."))
                except: pass
                break

        # Dimensions
        for key in ("Width", "Length", "Radius"):
            if key in geom:
                try: obj[key.lower()] = float(str(geom[key]).replace(",","."))
                except: pass

        # Text content
        if text_props.get("Contents"):
            obj["text"] = text_props["Contents"]

        objects.append(obj)

    return objects

def parser_dwg_aps(filepath: str, nb_niveaux: int = None, ville: str = "Dakar") -> Dict[str, Any]:
    """
    Full pipeline: DWG file → APS → structured geometry for Eurocodes engine.

    Args:
        filepath: Path to DWG file on disk
        nb_niveaux: Number of levels (if known)
        ville: City name

    Returns:
        Dict with ok=True and geometry data, or ok=False with error message.
    """
    try:
        token = get_token()
        ensure_bucket(token)

        # Generate unique object key
        timestamp = int(time.time())
        filename = os.path.basename(filepath).replace(" ", "_")
        object_key = f"tijan_{timestamp}_{filename}"

        # Upload
        urn = upload_file(filepath, object_key, token)
        logger.info("URN: %s", urn)

        # Translate
        token = get_token()  # refresh if needed
        start_translation(urn, token)
        manifest = wait_for_translation(urn, token, timeout_s=300)

        # Get DWG metadata
        dwg_info = {}
        for deriv in manifest.get("derivatives", []):
            doc_info = deriv.get("properties", {}).get("Document Information", {})
            if doc_info:
                dwg_info = doc_info
                break

        # Get viewables and extract 2D properties
        token = get_token()
        viewables = get_viewable_guids(urn, token)
        logger.info("Viewables: %s", [(v["name"], v["role"]) for v in viewables])

        # Prefer 2D view for property extraction
        target_guid = None
        for v in viewables:
            if v.get("role") == "2d" and v.get("name") in ("2D View", "Model"):
                target_guid = v["guid"]
                break
        if not target_guid:
            for v in viewables:
                if v.get("role") == "2d":
                    target_guid = v["guid"]
                    break
        if not target_guid and viewables:
            target_guid = viewables[0]["guid"]

        if not target_guid:
            return {"ok": False, "message": "Aucune vue trouvée dans le DWG"}

        # Extract properties
        token = get_token()
        properties = get_properties(urn, target_guid, token)
        if not properties:
            return {"ok": False, "message": "Impossible d'extraire les propriétés du DWG"}

        # Analyze geometry
        geo = extract_geometry(properties)

        # Surface comes from extract_geometry now
        surface = geo["surface_emprise_m2"]

        # Build engine input
        donnees_moteur = {
            "nom": dwg_info.get("Name", filename).replace(".dwg", ""),
            "ville": ville,
            "nb_niveaux": nb_niveaux or 4,
            "hauteur_etage_m": 3.0,
            "surface_emprise_m2": round(surface, 1),
            "portee_max_m": geo["portee_max_m"] or 5.0,
            "portee_min_m": geo["portee_min_m"] or 4.0,
            "nb_travees_x": geo["nb_travees_x"],
            "nb_travees_y": geo["nb_travees_y"],
            "usage_principal": "residentiel",
            "classe_beton": "C30/37",
            "classe_acier": "HA500",
            "pression_sol_MPa": 0.15,
            "profondeur_fondation_m": 1.5,
            "distance_mer_km": 2.0,
            "zone_sismique": 1,
            "enrobage_mm": 30.0,
        }

        return {
            "ok": True,
            "source": "aps",
            "urn": urn,
            "viewable_guid": target_guid,
            "dwg_info": dwg_info,
            "geometrie": {
                "nb_axes_x": geo["nb_axes_x"],
                "nb_axes_y": geo["nb_axes_y"],
                "axes_raw_count": geo["axes_raw_count"],
                "axes_length_groups": geo["axes_length_groups"],
                "emprise_x_m": geo["emprise_x_m"],
                "emprise_y_m": geo["emprise_y_m"],
                "surface_emprise_m2": geo["surface_emprise_m2"],
                "portee_max_m": geo["portee_max_m"],
                "portee_min_m": geo["portee_min_m"],
                "nb_travees_x": geo["nb_travees_x"],
                "nb_travees_y": geo["nb_travees_y"],
                "nb_murs": geo["nb_murs"],
                "nb_dimensions": geo["nb_dimensions"],
                "nb_total_objects": geo["nb_total_objects"],
                "portees_cm": geo["portees_cm"],
                "epaisseurs_mur_cm": geo["epaisseurs_mur_cm"],
                "layers": geo["layers"],
                "room_labels": geo["room_labels"],
            },
            "donnees_moteur": donnees_moteur,
        }

    except EnvironmentError as e:
        return {"ok": False, "message": str(e)}
    except TimeoutError as e:
        return {"ok": False, "message": f"Timeout traduction APS: {e}"}
    except requests.HTTPError as e:
        return {"ok": False, "message": f"Erreur API APS: {e}"}
    except Exception as e:
        logger.exception("APS parser error")
        return {"ok": False, "message": f"Erreur parsing APS: {e}"}


# ════════════════════════════════════════════════════════════
# CLI TEST
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) > 1:
        result = parser_dwg_aps(sys.argv[1])
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("Usage: python aps_parser_v2.py <fichier.dwg>")
