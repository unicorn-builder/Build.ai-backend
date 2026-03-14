"""
Tijan AI — aps_parser.py
Parsing DWG/DXF via Autodesk APS (ex-Forge).
Lit nativement tous les formats DWG sans conversion.
"""

import gc
import os
import time
import tempfile
import requests
from typing import Optional
from dataclasses import dataclass, field
from typing import List

# ════════════════════════════════════════════════════════════
# CONFIG APS
# ════════════════════════════════════════════════════════════

APS_CLIENT_ID     = os.getenv("APS_CLIENT_ID", "")
APS_CLIENT_SECRET = os.getenv("APS_CLIENT_SECRET", "")
APS_BUCKET = os.getenv("APS_BUCKET", "tijan-test-bucket-001")

APS_AUTH_URL   = "https://developer.api.autodesk.com/authentication/v2/token"
APS_OSS_URL    = "https://developer.api.autodesk.com/oss/v2/buckets"
APS_MODEL_URL  = "https://developer.api.autodesk.com/modelderivative/v2"


# ════════════════════════════════════════════════════════════
# AUTH
# ════════════════════════════════════════════════════════════

_token_cache = {"token": None, "expires_at": 0}

def get_token() -> str:
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["token"]

    r = requests.post(APS_AUTH_URL, data={
        "client_id": APS_CLIENT_ID,
        "client_secret": APS_CLIENT_SECRET,
        "grant_type": "client_credentials",
        "scope": "data:read data:write data:create bucket:create bucket:read bucket:update",
    }, timeout=15)
    r.raise_for_status()
    data = r.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = now + data["expires_in"]
    return _token_cache["token"]


def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}",
            "Content-Type": "application/json"}


# ════════════════════════════════════════════════════════════
# BUCKET
# ════════════════════════════════════════════════════════════

def ensure_bucket(token: str):
    """Crée le bucket si inexistant."""
    r = requests.post(f"{APS_OSS_URL}", json={
        "bucketKey": APS_BUCKET,
        "policyKey": "transient"  # supprimé après 24h
    }, headers=headers(token), timeout=15)
    if r.status_code not in (200, 409):  # 409 = déjà existant
        r.raise_for_status()


# ════════════════════════════════════════════════════════════
# UPLOAD
# ════════════════════════════════════════════════════════════

def upload_dwg(filepath: str, token: str) -> str:
    """
    Upload le DWG vers APS OSS.
    Retourne l'URN base64 du fichier.
    """
    import base64
    fname = os.path.basename(filepath)
    object_key = f"tijan_{int(time.time())}_{fname}"

    # Signed URL upload (simple pour fichiers < 100MB)
    url = f"{APS_OSS_URL}/{APS_BUCKET}/objects/{requests.utils.quote(object_key)}"
    with open(filepath, "rb") as f:
        data = f.read()

    r = requests.put(url, data=data, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream",
    }, timeout=120)
    r.raise_for_status()

    object_id = r.json()["objectId"]
    urn = base64.b64encode(object_id.encode()).decode().rstrip("=")
    return urn


# ════════════════════════════════════════════════════════════
# TRANSLATION (DWG → SVF)
# ════════════════════════════════════════════════════════════

def lancer_translation(urn: str, token: str):
    """Lance la conversion DWG → SVF2 sur APS."""
    r = requests.post(f"{APS_MODEL_URL}/designdata/job", json={
        "input": {"urn": urn},
        "output": {
            "formats": [{
                "type": "svf2",
                "views": ["2d", "3d"]
            }]
        }
    }, headers=headers(token), timeout=30)
    r.raise_for_status()


def attendre_translation(urn: str, token: str, timeout_s: int = 120) -> dict:
    """Poll jusqu'à ce que la translation soit terminée."""
    import base64
    urn_padded = urn + "=" * (4 - len(urn) % 4)
    url = f"{APS_MODEL_URL}/designdata/{urn}/manifest"
    debut = time.time()

    while time.time() - debut < timeout_s:
        r = requests.get(url, headers={
            "Authorization": f"Bearer {token}"}, timeout=15)
        r.raise_for_status()
        data = r.json()
        status = data.get("status", "")
        progress = data.get("progress", "")

        if status == "success":
            return data
        if status == "failed":
            raise ValueError(f"Translation APS échouée : {data}")

        time.sleep(3)

    raise TimeoutError("Translation APS timeout après 120s")


# ════════════════════════════════════════════════════════════
# EXTRACTION GÉOMÉTRIE
# ════════════════════════════════════════════════════════════

@dataclass
class GeometrieAPS:
    axes_x: List[float]    = field(default_factory=list)
    axes_y: List[float]    = field(default_factory=list)
    portees_x: List[float] = field(default_factory=list)
    portees_y: List[float] = field(default_factory=list)
    emprise_x: float = 0.0
    emprise_y: float = 0.0
    nb_niveaux: int  = 0
    projet_nom: str  = ""
    score: int       = 0
    viewable_guid: str = ""


def extraire_guid_2d(manifest: dict) -> Optional[str]:
    """Extrait le GUID de la vue 2D (plan) depuis le manifest."""
    for deriv in manifest.get("derivatives", []):
        for child in deriv.get("children", []):
            if child.get("role") == "2d":
                return child.get("guid")
            for sub in child.get("children", []):
                if sub.get("role") == "2d":
                    return sub.get("guid")
    # Fallback : première vue disponible
    for deriv in manifest.get("derivatives", []):
        for child in deriv.get("children", []):
            if child.get("type") == "geometry":
                return child.get("guid")
    return None


def extraire_geometrie_properties(urn: str, guid: str, token: str) -> GeometrieAPS:
    """
    Extrait les propriétés des objets depuis APS Model Derivative.
    Analyse les layers et coordonnées pour reconstruire la géométrie.
    """
    geo = GeometrieAPS()
    geo.viewable_guid = guid

    # Récupérer toutes les propriétés
    url = f"{APS_MODEL_URL}/designdata/{urn}/metadata/{guid}/properties"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"},
                     params={"forceget": "true"}, timeout=60)

    if r.status_code != 200:
        return geo

    props = r.json().get("data", {}).get("collection", [])

    # Analyser les objets pour extraire axes et poteaux
    xs_candidates = set()
    ys_candidates = set()
    noms_projet = []

    for obj in props:
        name = (obj.get("name") or "").lower()
        obj_props = obj.get("properties", {})

        # Chercher coordonnées dans les propriétés
        for cat, vals in obj_props.items():
            if not isinstance(vals, dict):
                continue
            for key, val in vals.items():
                if not isinstance(val, (int, float)):
                    continue
                key_low = key.lower()
                if "position x" in key_low or key_low == "x":
                    if 100 < abs(val) < 500000:
                        xs_candidates.add(round(val, -1))
                if "position y" in key_low or key_low == "y":
                    if 100 < abs(val) < 500000:
                        ys_candidates.add(round(val, -1))

        # Chercher nom projet
        if any(k in name for k in ["projet", "title", "nom", "name"]):
            for cat, vals in obj_props.items():
                if isinstance(vals, dict):
                    for k, v in vals.items():
                        if isinstance(v, str) and 5 < len(v) < 60:
                            noms_projet.append(v)

    # Calculer portées depuis coordonnées uniques
    if xs_candidates:
        xs = sorted(xs_candidates)
        geo.axes_x = xs
        diffs = [xs[i+1]-xs[i] for i in range(len(xs)-1) if xs[i+1]-xs[i] > 500]
        geo.portees_x = diffs
        geo.emprise_x = max(xs) - min(xs) if len(xs) > 1 else 0

    if ys_candidates:
        ys = sorted(ys_candidates)
        geo.axes_y = ys
        diffs = [ys[i+1]-ys[i] for i in range(len(ys)-1) if ys[i+1]-ys[i] > 500]
        geo.portees_y = diffs
        geo.emprise_y = max(ys) - min(ys) if len(ys) > 1 else 0

    if noms_projet:
        geo.projet_nom = noms_projet[0]

    # Score qualité
    s = 0
    if geo.axes_x:    s += 30
    if geo.axes_y:    s += 30
    if geo.portees_x: s += 20
    if geo.emprise_x: s += 10
    if geo.projet_nom: s += 10
    geo.score = s

    return geo


# ════════════════════════════════════════════════════════════
# PIPELINE PRINCIPAL
# ════════════════════════════════════════════════════════════

def parser_dwg_aps(filepath: str) -> dict:
    """
    Pipeline complet APS :
    1. Auth → 2. Bucket → 3. Upload → 4. Translation → 5. Extraction géométrie
    Retourne dict compatible avec le moteur Eurocodes.
    """
    if not APS_CLIENT_ID or not APS_CLIENT_SECRET:
        raise EnvironmentError(
            "APS_CLIENT_ID et APS_CLIENT_SECRET requis. "
            "Configurez-les dans les variables d'environnement Render."
        )

    token = get_token()
    ensure_bucket(token)

    urn = upload_dwg(filepath, token)
    lancer_translation(urn, token)
    manifest = attendre_translation(urn, token)

    guid = extraire_guid_2d(manifest)
    if not guid:
        raise ValueError("Aucune vue 2D trouvée dans ce fichier DWG.")

    # Refresh token si nécessaire
    token = get_token()
    geo = extraire_geometrie_properties(urn, guid, token)

    # Convertir en format moteur Eurocodes
    portees = geo.portees_x + geo.portees_y
    portee_max = max(portees) / 1000 if portees else 5.0
    portee_min = min([p for p in portees if p > 500]) / 1000 if portees else 4.0
    surface = (geo.emprise_x * geo.emprise_y) / 1e6
    if surface < 50:
        nx = max(len(geo.axes_x) - 1, 1)
        ny = max(len(geo.axes_y) - 1, 1)
        surface = portee_max * portee_min * nx * ny

    nb_travees_x = max(len(geo.axes_x) - 1, 1)
    nb_travees_y = max(len(geo.axes_y) - 1, 1)

    return {
        "ok": True,
        "niveau_output": "complet",
        "source": "aps",
        "score_qualite": geo.score,
        "projet_nom": geo.projet_nom or "Projet importé",
        "urn": urn,
        "viewable_guid": geo.viewable_guid,
        "nb_axes_x": len(geo.axes_x),
        "nb_axes_y": len(geo.axes_y),
        "portees_x_m": [round(p/1000, 2) for p in geo.portees_x],
        "portees_y_m": [round(p/1000, 2) for p in geo.portees_y],
        "emprise_x_m": round(geo.emprise_x / 1000, 2),
        "emprise_y_m": round(geo.emprise_y / 1000, 2),
        "donnees_moteur": {
            "nom": geo.projet_nom or "Projet importé",
            "ville": "Dakar",
            "nb_niveaux": geo.nb_niveaux or 4,
            "hauteur_etage_m": 3.0,
            "surface_emprise_m2": round(surface, 1),
            "portee_max_m": round(portee_max, 2),
            "portee_min_m": round(portee_min, 2),
            "nb_travees_x": nb_travees_x,
            "nb_travees_y": nb_travees_y,
            "usage_principal": "residentiel",
            "classe_beton": "C30/37",
            "classe_acier": "HA500",
            "pression_sol_MPa": 0.15,
            "profondeur_fondation_m": 1.5,
            "distance_mer_km": 2.0,
            "zone_sismique": 1,
            "enrobage_mm": 30.0,
        }
    }


if __name__ == "__main__":
    import sys, json
    if len(sys.argv) > 1:
        try:
            result = parser_dwg_aps(sys.argv[1])
            print(json.dumps({k: v for k, v in result.items() if k != "geo"}, indent=2))
        except Exception as e:
            print(f"Erreur : {e}")
