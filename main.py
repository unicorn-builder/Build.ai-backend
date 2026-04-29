"""
Tijan AI — main.py v6.1
Backend FastAPI — Render Standard (1 CPU / 2GB RAM)

v6.1: i18n — native EN PDF generators, lang routing on all /generate-* endpoints.

Moteurs v2 :
  - engine_structure_v2.py  — Structure EC2/EC8 paramétrique tous usages
  - engine_mep_v2.py        — MEP complet (élec, plomberie, CVC, CF, SI, ASC, AUTO, EDGE)
  - prix_marche.py          — Base de prix multi-pays (Dakar, Abidjan, Casablanca, Lagos, Accra)

Générateurs PDF v2 (données 100% issues des moteurs) :
  FR: gen_note_structure / gen_boq_structure / gen_mep / gen_boq_mep_detail
  EN: gen_note_structure_en / gen_boq_structure_en / gen_mep_en / gen_boq_mep_detail_en

Endpoints :
  GET  /health
  POST /parse                     → parse PDF/DWG → paramètres projet
  POST /parse-sol                 → parse étude de sol PDF
  POST /calculate                 → calcul structure EC2/EC8
  POST /calculate-mep             → calcul MEP complet
  POST /generate                  → note de calcul structure PDF (FR/EN)
  POST /generate-boq              → BOQ structure détaillé PDF (FR/EN)
  POST /generate-note-mep         → note de calcul MEP PDF (FR/EN)
  POST /generate-boq-mep          → BOQ MEP détaillé PDF (FR/EN)
  POST /generate-rapport-executif → rapport synthèse maître d'ouvrage PDF (FR/EN)
  POST /generate-fiches-structure → fiches techniques structure PDF
  POST /generate-fiches-mep       → fiches techniques MEP PDF
  POST /generate-planches         → planches BA PDF
  POST /generate-plans-structure  → plans structure PDF (coffrage, ferraillage, voiles) — géo DXF + EC2
  POST /generate-plans-mep        → plans MEP PDF (7 lots × niveaux) — géo DXF + moteur MEP
"""

import gc
import os
import io
import json as _json
import tempfile
import logging
import dataclasses
import httpx
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import Request, FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from tijan_theme import set_pdf_lang, set_pdf_devise
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tijan")

app = FastAPI(
    title="Tijan AI API",
    description="Bureau d'études automatisé — Structure + MEP + BOQ + EDGE",
    version="6.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tijan.ai", "https://api.tijan.ai", "https://admin.tijan.ai", "https://tijan-frontend.vercel.app", "https://tijan-admin.vercel.app", "http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Surface FastAPI request-validation errors (422) in logs ──
# Default 422s give zero info in Render — this prints the actual offending
# field + value so we can diagnose multipart/form bugs from logs alone.
from fastapi.exceptions import RequestValidationError as _RVErr
from starlette.requests import Request as _StRequest

@app.exception_handler(_RVErr)
async def _log_validation_error(request: _StRequest, exc: _RVErr):
    try:
        errs = exc.errors()
    except Exception:
        errs = [{"msg": str(exc)}]
    # Compact summary per error: loc + type + msg
    summary = []
    for e in errs[:8]:
        loc = ".".join(str(p) for p in (e.get("loc") or []))
        summary.append(f"{loc}: {e.get('type','?')} — {e.get('msg','?')}")
    logger.warning("422 on %s %s — %d error(s): %s",
                   request.method, request.url.path, len(errs), " | ".join(summary))
    # Echo a structured response so the frontend can show the real reason
    return JSONResponse(status_code=422,
                        content={"ok": False, "error": "validation",
                                 "path": request.url.path, "errors": errs})


# ════════════════════════════════════════════════════════════
# PROMO / SUBSCRIPTION CONSTANTS
# ════════════════════════════════════════════════════════════
DEFAULT_PRICE_FCFA = 500000
PRIX_UNITE_FCFA = 200000
ALLOWED_DURATIONS_MONTHS = [3, 6]
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
TIJAN_FROM_EMAIL = "Tijan AI <noreply@tijan.ai>"


def _send_welcome_email(to_email: str, name: str, price: int, discount_percent: int = 0,
                        duration_months: int = 0, revert_date: str = ""):
    """Send welcome email after subscription. Non-blocking — failures logged, never raised."""
    if not RESEND_API_KEY:
        logger.warning("[email] RESEND_API_KEY not set — skipping welcome email")
        return
    try:
        import resend
        resend.api_key = RESEND_API_KEY

        if discount_percent > 0:
            subject = f"Bienvenue sur Tijan AI — Offre {discount_percent}% pendant {duration_months} mois"
            promo_block = f"""
            <div style="background:#F0FFF4;border-left:4px solid #43A956;padding:16px;margin:20px 0;border-radius:8px">
              <strong>Votre offre partenaire</strong><br>
              Tarif : <strong>{price:,} FCFA/mois</strong> (au lieu de {DEFAULT_PRICE_FCFA:,} FCFA)<br>
              Durée : <strong>{duration_months} mois</strong><br>
              Bascule automatique : <strong>{revert_date}</strong> → {DEFAULT_PRICE_FCFA:,} FCFA/mois
            </div>
            <p style="color:#888;font-size:13px">
              À l'issue de la période promotionnelle, votre abonnement passe automatiquement
              à {DEFAULT_PRICE_FCFA:,} FCFA/mois. Aucune action requise de votre part.
              Vous pouvez résilier à tout moment sans frais.
            </p>"""
        else:
            subject = "Bienvenue sur Tijan AI — Votre abonnement est actif"
            promo_block = ""

        html = f"""
        <div style="font-family:-apple-system,sans-serif;max-width:560px;margin:0 auto;padding:24px">
          <div style="text-align:center;margin-bottom:24px">
            <span style="font-size:24px;font-weight:800;color:#43A956">TIJAN AI</span>
            <div style="font-size:12px;color:#888">Automated Engineering Bureau</div>
          </div>
          <h2 style="color:#1B2A4A;font-size:20px">Bonjour {name},</h2>
          <p>Votre abonnement Tijan AI est maintenant actif. Vous disposez de
          <strong>3 études complètes par mois</strong> — structure, MEP, BOQ, EDGE,
          plans d'exécution et schémas inclus.</p>
          {promo_block}
          <div style="text-align:center;margin:28px 0">
            <a href="https://tijan.ai/projects/new" style="background:#43A956;color:#fff;
               padding:14px 32px;border-radius:10px;text-decoration:none;font-weight:700;
               font-size:15px">Lancer ma première étude →</a>
          </div>
          <p style="font-size:13px;color:#888">
            Support prioritaire : <a href="mailto:malicktall@gmail.com">malicktall@gmail.com</a><br>
            <a href="https://tijan.ai">tijan.ai</a>
          </p>
        </div>"""

        resend.Emails.send({
            "from": TIJAN_FROM_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": html,
        })
        logger.info(f"[email] Welcome email sent to {to_email}")
    except Exception as e:
        logger.warning(f"[email] Failed to send welcome email to {to_email}: {e}")
ADMIN_EMAILS = ["malicktall@gmail.com"]


# ════════════════════════════════════════════════════════════
# SUPABASE REST HELPER (lightweight — no SDK dependency)
# ════════════════════════════════════════════════════════════

class _SupabaseResult:
    def __init__(self, data):
        self.data = data

class _SupabaseQuery:
    """Chainable builder that mirrors supabase-py .table().select().eq()… .execute()."""

    def __init__(self, base_url: str, key: str, table: str):
        self._base = f"{base_url}/rest/v1/{table}"
        self._headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "",
        }
        self._params: dict = {}
        self._method = "GET"
        self._body = None
        self._single = False
        self._filters: list = []
        self._order_col = None
        self._order_desc = False

    # ── verbs ──
    def select(self, cols="*"):
        self._method = "GET"
        self._params["select"] = cols
        return self

    def insert(self, data: dict):
        self._method = "POST"
        self._body = data
        self._headers["Prefer"] = "return=representation"
        return self

    def update(self, data: dict):
        self._method = "PATCH"
        self._body = data
        self._headers["Prefer"] = "return=representation"
        return self

    # ── filters ──
    def eq(self, col: str, val):
        self._filters.append((col, f"eq.{val}"))
        return self

    def order(self, col: str, *, desc: bool = False):
        self._order_col = col
        self._order_desc = desc
        return self

    def maybeSingle(self):
        self._single = True
        return self

    # ── execute ──
    def execute(self) -> _SupabaseResult:
        import urllib.parse
        url = self._base
        params = dict(self._params)
        for col, filt in self._filters:
            params[col] = filt
        if self._order_col:
            direction = "desc" if self._order_desc else "asc"
            params["order"] = f"{self._order_col}.{direction}"
        qs = urllib.parse.urlencode(params)
        if qs:
            url = f"{url}?{qs}"

        with httpx.Client(timeout=15) as c:
            if self._method == "GET":
                r = c.get(url, headers=self._headers)
            elif self._method == "POST":
                r = c.post(url, json=self._body, headers=self._headers)
            elif self._method == "PATCH":
                r = c.patch(url, json=self._body, headers=self._headers)
            else:
                raise ValueError(f"Unsupported method {self._method}")

        r.raise_for_status()
        data = r.json()
        if self._single:
            if isinstance(data, list):
                data = data[0] if data else None
        return _SupabaseResult(data)


class _SupabaseClient:
    def __init__(self):
        self._url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        self._key = os.environ.get("SUPABASE_SERVICE_ROLE") or os.environ.get("SUPABASE_SERVICE_KEY") or ""

    def table(self, name: str) -> _SupabaseQuery:
        return _SupabaseQuery(self._url, self._key, name)

supabase = _SupabaseClient()


# ════════════════════════════════════════════════════════════
# IMPORTS LAZY
# ════════════════════════════════════════════════════════════

def get_moteur_structure():
    from engine_structure_v2 import DonneesProjet, Usage, calculer_structure
    return DonneesProjet, Usage, calculer_structure

def get_moteur_mep():
    from engine_mep_v2 import calculer_mep
    return calculer_mep

# ── FR generators ──
def get_gen_note_structure():
    from gen_note_structure import generer
    return generer

def get_gen_boq_structure():
    from gen_boq_structure import generer_boq_structure
    return generer_boq_structure

def get_gen_note_mep():
    from gen_mep import generer_note_mep
    return generer_note_mep

def get_gen_boq_mep():
    from gen_boq_mep_detail import generer_boq_mep_detail
    return generer_boq_mep_detail

def get_gen_executif():
    from gen_mep import generer_rapport_executif
    return generer_rapport_executif

# ── EN generators ──
def get_gen_note_structure_en():
    from gen_note_structure_en import generer
    return generer

def get_gen_boq_structure_en():
    from gen_boq_structure_en import generer_boq_structure
    return generer_boq_structure

def get_gen_note_mep_en():
    from gen_mep_en import generer_note_mep
    return generer_note_mep

def get_gen_boq_mep_en():
    from gen_boq_mep_detail_en import generer_boq_mep_detail
    return generer_boq_mep_detail

def get_gen_executif_en():
    from gen_mep_en import generer_rapport_executif
    return generer_rapport_executif

# ── Other generators (no EN version yet) ──
def get_gen_fiches_structure():
    from generate_fiches_structure_v3 import generer_fiches_structure
    return generer_fiches_structure

def get_gen_fiches_structure_en():
    from generate_fiches_structure_en import generer_fiches_structure
    return generer_fiches_structure

def get_gen_fiches_mep_en():
    from generate_fiches_mep_en import generer_fiches_mep
    return generer_fiches_mep

def get_gen_fiches_mep():
    from generate_fiches_mep_v3 import generer_fiches_mep
    return generer_fiches_mep

def get_gen_planches():
    from generate_plans_v4 import generer_dossier_ba
    return generer_dossier_ba


# ════════════════════════════════════════════════════════════
# MODÈLE PYDANTIC
# ════════════════════════════════════════════════════════════

class ParamsProjet(BaseModel):
    nom:                str   = "Projet Tijan"
    ville:              str   = "Dakar"
    pays:               str   = "Senegal"
    usage:              str   = "residentiel"
    nb_niveaux:         int   = 4
    hauteur_etage_m:    float = 3.0
    surface_emprise_m2: float = 500.0
    surface_terrain_m2: float = 0.0
    nb_logements:       Optional[int] = None
    portee_max_m:       float = 5.5
    portee_min_m:       float = 4.0
    nb_travees_x:       int   = 3
    nb_travees_y:       int   = 2
    # Matériaux — vide = auto-sélection par le moteur
    classe_beton:       str   = ""
    classe_acier:       str   = ""
    # Site — 0 = auto depuis ville
    pression_sol_MPa:   float = 0.0
    distance_mer_km:    float = 0.0
    zone_sismique:      int   = -1
    lang:               str   = "fr"
    # Optionnel
    sol_context:        Optional[str] = None
    avec_sous_sol:      bool  = False
    urn:                Optional[str] = None
    dwg_geometry:       Optional[dict] = None
    archi_pdf_url:      Optional[str] = None  # URL of uploaded archi PDF for plan background
    archi_pdf_ref:      Optional[str] = None  # Temp key for cached archi PDF (from /parse)
    geom_ref:           Optional[str] = None  # Temp key for cached geometry (from /parse)
    project_id:         Optional[str] = None  # Supabase projets.id — used for server-side plan archival
    # EDGE Assessment optional inputs
    typologies:         Optional[list] = None   # list of {name,bedrooms,area,units,occupancy,...}
    orientations:       Optional[dict] = None   # {N:{len,exposed_pct},...} (auto-calc if absent)
    irrigated_area_m2:  Optional[float] = None
    pool_m2:            Optional[float] = None
    car_wash:           Optional[bool] = None
    washing_clothes:    Optional[bool] = None
    process_water:      Optional[bool] = None
    dishwasher:         Optional[bool] = None
    pre_rinse:          Optional[bool] = None
    cost_construction_xof_m2: Optional[float] = None
    sale_value_xof_m2:  Optional[float] = None
    nb_sous_sols:       Optional[int] = None
    roof_area_m2:       Optional[float] = None


# ════════════════════════════════════════════════════════════
# UTILITAIRES
# ════════════════════════════════════════════════════════════

def params_to_donnees(params: ParamsProjet):
    """Convertit ParamsProjet → DonneesProjet v2."""
    DonneesProjet, Usage, _ = get_moteur_structure()

    # Mapping usage
    usage_map = {
        "residentiel": Usage.RESIDENTIEL,
        "bureau":      Usage.BUREAU,
        "hotel":       Usage.HOTEL,
        "mixte":       Usage.MIXTE,
        "commercial":  Usage.COMMERCIAL,
        "industriel":  Usage.INDUSTRIEL,
    }
    usage = usage_map.get(params.usage.lower(), Usage.RESIDENTIEL)

    # Pression sol depuis étude de sol si fournie
    pression_sol = params.pression_sol_MPa
    if params.sol_context:
        try:
            sol_data = _json.loads(params.sol_context)
            if sol_data.get('pression_admissible_MPa'):
                pression_sol = float(sol_data['pression_admissible_MPa'])
                logger.info(f"Étude sol : {sol_data.get('type_sol')} / {pression_sol} MPa")
        except Exception as e:
            logger.warning(f"sol_context parse error: {e}")

    return DonneesProjet(
        nom=params.nom,
        ville=params.ville,
        pays=params.pays,
        usage=usage,
        nb_niveaux=params.nb_niveaux,
        hauteur_etage_m=params.hauteur_etage_m,
        surface_emprise_m2=params.surface_emprise_m2,
        surface_terrain_m2=params.surface_terrain_m2,
        nb_logements=params.nb_logements or 0,
        portee_max_m=params.portee_max_m,
        portee_min_m=params.portee_min_m,
        nb_travees_x=params.nb_travees_x,
        nb_travees_y=params.nb_travees_y,
        classe_beton=params.classe_beton,
        classe_acier=params.classe_acier,
        pression_sol_MPa=pression_sol,
        distance_mer_km=params.distance_mer_km,
        zone_sismique=params.zone_sismique,
        avec_sous_sol=params.avec_sous_sol,
        nb_sous_sols=1 if params.avec_sous_sol else 0,
    )

def pdf_response(pdf_bytes: bytes, filename: str, archive_url: Optional[str] = None) -> StreamingResponse:
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    if archive_url:
        headers["X-Plan-Archive-URL"] = archive_url
        headers["Access-Control-Expose-Headers"] = "X-Plan-Archive-URL,Content-Disposition"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers=headers,
    )

async def save_upload(file: UploadFile) -> str:
    suffix = os.path.splitext(file.filename)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        logger.info(f"Saved upload: {tmp.name} ({len(content)} bytes)")
        return tmp.name

def fname(params: ParamsProjet, prefix: str) -> str:
    return f"tijan_{prefix}_{params.nom.replace(' ','_')[:20]}.pdf"

def is_en(params: ParamsProjet) -> bool:
    """Check if English output is requested."""
    return getattr(params, 'lang', 'fr').lower().startswith('en')

def get_devise_info(ville: str) -> dict:
    """Get currency info for a city."""
    try:
        from prix_marche import get_prix, TAUX_CHANGE
        p = get_prix(ville)
        taux = TAUX_CHANGE.get(p.devise, 1.0)
        return {
            "devise": p.devise,
            "symbole": {"XOF": "FCFA", "NGN": "₦", "MAD": "MAD", "GHS": "GH₵", "EUR": "€", "USD": "$"}.get(p.devise, p.devise),
            "taux_vers_fcfa": taux,
            "taux_depuis_fcfa": round(1.0 / taux, 6) if taux else 1.0,
            "pays": p.pays,
        }
    except Exception:
        return {"devise": "XOF", "symbole": "FCFA", "taux_vers_fcfa": 1.0, "taux_depuis_fcfa": 1.0, "pays": "Senegal"}


def _get_converter_status():
    try:
        from dwg_converter import converter_status
        return converter_status()["strategy"]
    except Exception:
        return "unknown"


# ════════════════════════════════════════════════════════════
# ENDPOINTS
# ════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "6.1.0",
        "timestamp": datetime.utcnow().isoformat(),
        "i18n": ["fr", "en"],
        "moteurs": {
            "structure": "engine_structure_v2",
            "mep":       "engine_mep_v2",
            "prix":      "prix_marche — Dakar/Abidjan/Casablanca/Lagos/Accra",
            "dwg_converter": _get_converter_status(),
        },
    }


@app.get("/version")
async def version():
    """Returns git commit hash + build timestamp so we know exactly what is deployed."""
    import subprocess
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL, timeout=5
        ).decode().strip()
    except Exception:
        commit = os.environ.get("RENDER_GIT_COMMIT", "unknown")[:7]
    try:
        commit_time = subprocess.check_output(
            ["git", "log", "-1", "--format=%cI"],
            stderr=subprocess.DEVNULL, timeout=5
        ).decode().strip()
    except Exception:
        commit_time = "unknown"
    return {
        "commit": commit,
        "commit_time": commit_time,
        "version": "6.1.0",
        "deployed_at": datetime.utcnow().isoformat(),
    }


@app.post("/parse")
async def parse_fichier(
    file: UploadFile = File(...),
    nb_niveaux: Optional[int] = Form(None),
    ville: Optional[str] = Form(None),
    beton: Optional[str] = Form(None),
):
    """
    Parse a single plan file. Extracts params + geometry.
    DWG → try local DWG→DXF (LibreDWG/ODA) then ezdxf, else APS cloud
    DXF → ezdxf directly (instant, full geometry)
    PDF → text extraction + Claude AI (params only)
    """
    tmp_path = await save_upload(file)
    dxf_path = None
    try:
        filename = file.filename or ""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if ext == "dxf":
            # DXF: ezdxf reads directly — instant, full geometry
            from parse_plans import extraire_params
            result = extraire_params(tmp_path)
            try:
                dxf_geom = _extract_dxf_geometry(tmp_path)
                if dxf_geom:
                    result["dwg_geometry"] = dxf_geom
                    logger.info("DXF geometry: %d walls, %d rooms",
                                len(dxf_geom.get('walls',[])), len(dxf_geom.get('rooms',[])))
            except Exception as e:
                logger.warning("DXF geometry extraction failed: %s", e)

        elif ext == "dwg":
            # DWG → try convert to DXF (local or APS), then ezdxf
            from dwg_converter import convert_to_dxf
            dxf_path = convert_to_dxf(tmp_path, ville=ville or "Dakar")
            dwg_geom_found = False

            if dxf_path and os.path.isfile(dxf_path):
                # Got a real DXF — extract everything via ezdxf
                from parse_plans import extraire_params
                result = extraire_params(dxf_path)
                try:
                    dxf_geom = _extract_dxf_geometry(dxf_path)
                    if dxf_geom:
                        result["dwg_geometry"] = dxf_geom
                        dwg_geom_found = True
                        logger.info("DWG→DXF→geometry: %d walls, %d rooms",
                                    len(dxf_geom.get('walls',[])), len(dxf_geom.get('rooms',[])))
                    else:
                        logger.warning("DWG→DXF succeeded but geometry extraction returned None (no walls found in named layers)")
                except Exception as e:
                    logger.warning("DXF geometry extraction failed: %s", e)
            else:
                logger.warning("DWG→DXF conversion failed entirely — no local converter produced output")
                # Parse params via APS (no geometry)
                try:
                    from aps_parser_v2 import parser_dwg_aps
                    result = parser_dwg_aps(tmp_path, nb_niveaux=nb_niveaux, ville=ville or "Dakar")
                except Exception as e:
                    logger.warning("APS parser also failed: %s", e)
                    from parse_plans import extraire_params
                    result = extraire_params(tmp_path)

            # FALLBACK: if DWG produced no geometry, try rasterizing DXF to images → CV pipeline
            if not dwg_geom_found and dxf_path and os.path.isfile(dxf_path):
                logger.info("[DWG fallback] No geometry from ezdxf — trying DXF→PDF→CV pipeline")
                try:
                    # Convert DXF to PDF for CV extraction
                    import ezdxf
                    from ezdxf.addons.drawing import matplotlib as ezdxf_mpl
                    import matplotlib
                    matplotlib.use('Agg')
                    import matplotlib.pyplot as plt

                    doc = ezdxf.readfile(dxf_path)
                    fig = plt.figure(figsize=(42, 29.7))  # A3 landscape
                    ax = fig.add_axes([0, 0, 1, 1])
                    ctx = ezdxf_mpl.RenderContext(doc)
                    out = ezdxf_mpl.MatplotlibBackend(ax)
                    ezdxf_mpl.Frontend(ctx, out).draw_layout(doc.modelspace())
                    ax.set_aspect('equal')
                    ax.autoscale()

                    tmp_pdf = tempfile.mktemp(suffix='.pdf', prefix='tijan_dwg_render_')
                    fig.savefig(tmp_pdf, format='pdf', bbox_inches='tight', dpi=200)
                    plt.close(fig)

                    # Now use CV pipeline on the rendered PDF
                    from cv_geometry_extractor import extract_geometry_per_page_cv
                    cv_geom = extract_geometry_per_page_cv(tmp_pdf, use_vision=True)
                    if cv_geom:
                        usable = cv_geom if 'walls' in cv_geom else {
                            k: v for k, v in cv_geom.items()
                            if isinstance(v, dict) and len(v.get('walls', [])) >= 3
                        }
                        if usable and (isinstance(usable, dict) and
                                       (len(usable.get('walls', [])) >= 3 or len(usable) >= 1)):
                            result["dwg_geometry"] = usable
                            dwg_geom_found = True
                            logger.info("[DWG fallback] CV pipeline succeeded: %s",
                                        f"{len(usable.get('walls', []))} walls" if 'walls' in usable
                                        else f"{len(usable)} levels")
                    try:
                        os.unlink(tmp_pdf)
                    except:
                        pass
                except Exception as e:
                    logger.warning("[DWG fallback] DXF→PDF→CV pipeline failed: %s", e)

            # LAST RESORT: if still no geometry, save archi ref for Priority 4 fallback
            if not dwg_geom_found:
                logger.warning("[DWG] No geometry extracted — plans will use parametric grid. "
                               "User should try uploading as PDF instead.")
                if dxf_path:
                    try:
                        result["archi_pdf_ref"] = _save_archi_pdf(dxf_path)
                    except:
                        pass

        elif ext == "pdf":
            # PDF: extract params via Claude + try vector geometry extraction
            from parse_plans import extraire_params
            result = extraire_params(tmp_path)
            # Save original PDF for use as plan background later
            try:
                result["archi_pdf_ref"] = _save_archi_pdf(tmp_path)
            except Exception as e:
                logger.warning(f"Failed to cache archi PDF: {e}")
            # Try extracting geometry from PDF — cascade:
            # 0. PER-PAGE CV (best for multi-page PDFs — one geom per level)
            # 1. CV pipeline single-page (OpenCV + Claude Vision)
            # 2. dwg_converter.pdf_to_geometry (vector extraction)
            # 3. extract_pdf_geometry (fallback vector, supports multi-page)
            if not result.get("dwg_geometry"):
                # Primary: per-page CV (each page becomes a level)
                try:
                    from cv_geometry_extractor import extract_geometry_per_page_cv
                    multi_geom = extract_geometry_per_page_cv(tmp_path, use_vision=True)
                    if multi_geom:
                        # If dict of levels (multi-page), use as-is
                        if 'walls' not in multi_geom:
                            # Require at least one level with usable geometry,
                            # else fall through to the older fallback chain.
                            usable = sum(1 for v in multi_geom.values()
                                         if isinstance(v, dict) and len(v.get('walls', [])) >= 3)
                            if usable >= 1:
                                result["dwg_geometry"] = multi_geom
                                logger.info("PDF per-page CV: %d levels (%d usable) → %s",
                                            len(multi_geom), usable, sorted(multi_geom.keys()))
                            else:
                                logger.info("Per-page CV produced %d levels but none usable — falling through",
                                            len(multi_geom))
                        elif len(multi_geom.get('walls', [])) >= 3:
                            result["dwg_geometry"] = multi_geom
                            logger.info("PDF per-page CV (single): %d walls",
                                        len(multi_geom.get('walls', [])))
                except Exception as e:
                    logger.warning("Per-page CV extraction failed: %s", e)

                # Fallback to single-page CV if per-page produced nothing
                if not result.get("dwg_geometry"):
                    try:
                        from cv_geometry_extractor import extract_geometry_from_pdf_cv
                        cv_geom = extract_geometry_from_pdf_cv(tmp_path, use_vision=True)
                        if cv_geom and len(cv_geom.get('walls', [])) >= 5:
                            result["dwg_geometry"] = cv_geom
                            logger.info("PDF geometry (CV pipeline): %d walls, %d rooms, quality=%s",
                                        len(cv_geom.get('walls', [])),
                                        len(cv_geom.get('rooms', [])),
                                        cv_geom.get('_cv_meta', {}).get('quality', '?'))
                    except Exception as e:
                        logger.warning("CV geometry extraction failed: %s", e)

                # Fallback 1: dwg_converter.pdf_to_geometry (vector)
                if not result.get("dwg_geometry"):
                    try:
                        from dwg_converter import pdf_to_geometry
                        pdf_geom = pdf_to_geometry(tmp_path)
                        if pdf_geom:
                            result["dwg_geometry"] = pdf_geom
                            logger.info("PDF geometry (dwg_converter): %d walls, %d rooms",
                                        len(pdf_geom.get('walls',[])), len(pdf_geom.get('rooms',[])))
                    except Exception as e:
                        logger.warning("PDF geometry extraction (dwg_converter) failed: %s", e)

                # Fallback 2: extract_pdf_geometry
                if not result.get("dwg_geometry"):
                    try:
                        from extract_pdf_geometry import extract_geometry_from_pdf
                        pdf_geom = extract_geometry_from_pdf(tmp_path, max_pages=5)
                        if pdf_geom:
                            result["dwg_geometry"] = pdf_geom
                            n_walls = len(pdf_geom.get('walls', [])) if 'walls' in pdf_geom else sum(
                                len(v.get('walls', [])) for v in pdf_geom.values() if isinstance(v, dict))
                            logger.info("PDF geometry (extract_pdf_geometry): %d walls", n_walls)
                    except Exception as e:
                        logger.warning("PDF geometry extraction (extract_pdf_geometry) failed: %s", e)

        else:
            from parse_plans import extraire_params
            result = extraire_params(tmp_path)

        if result.get("ok"):
            dm = result.get("donnees_moteur", {})
            if dm:
                if nb_niveaux: dm["nb_niveaux"] = nb_niveaux
                if ville: dm["ville"] = ville
                if beton: dm["classe_beton"] = beton
            if nb_niveaux: result["nb_niveaux"] = nb_niveaux
            if ville:      result["ville"] = ville
            if beton:      result["classe_beton"] = beton

            # Estimate occupants from room labels if geometry available
            geom = result.get("dwg_geometry")
            if geom and isinstance(geom, dict):
                rooms = geom.get('rooms', [])
                nb_occ = _estimate_occupants_from_rooms(rooms)
                if nb_occ > 0:
                    result["nb_occupants"] = nb_occ
                    if dm:
                        dm["nb_occupants"] = nb_occ

        # Cache geometry server-side so it survives page refreshes
        geom = result.get("dwg_geometry")
        if geom and isinstance(geom, dict):
            try:
                result["geom_ref"] = _save_geometry(geom)
            except Exception as e:
                logger.warning(f"Failed to cache geometry: {e}")

        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"/parse error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try: os.unlink(tmp_path)
        except OSError: pass
        if dxf_path and dxf_path != tmp_path:
            try: os.unlink(dxf_path)
            except OSError: pass


# ══════════════════════════════════════════════════════════════
# ASYNC MULTI-DWG PARSING
# ══════════════════════════════════════════════════════════════

import threading
import uuid

_parse_jobs = {}  # job_id → {status, progress, result, files, error}
_parse_jobs_lock = threading.Lock()


@app.post("/parse-multi")
async def parse_multi_start(
    request: Request,
    files: List[UploadFile] = File(...),
    nb_niveaux: Optional[str] = Form(None),   # accept str then coerce
    ville: Optional[str] = Form(None),
    beton: Optional[str] = Form(None),
    # NOTE: read levels manually from form below — declaring it here as
    # List[str] caused intermittent 422s when the field is empty/missing.
):
    # Coerce nb_niveaux defensively (frontend may send '', 'null', 'NaN', '8')
    try:
        nb_niveaux = int(nb_niveaux) if nb_niveaux not in (None, '', 'null', 'NaN', 'undefined') else None
    except (TypeError, ValueError):
        nb_niveaux = None
    # Pull `levels` manually so we tolerate any number (including zero) of values
    try:
        _form = await request.form()
        levels = [str(v) for v in _form.getlist('levels')] if _form else None
    except Exception:
        levels = None
    """
    Parse N DWG/DXF files — one per building level.
    Optional `levels` form field: array of level labels parallel to files
    (e.g. ["SOUS_SOL", "RDC", "ETAGE_1", "TERRASSE"]). When provided, overrides
    filename heuristics. When omitted, level is inferred from filename.
    With ODA: converts all to DXF locally (~2s each) → ezdxf geometry → returns immediately.
    Without ODA: falls back to async APS processing.
    """
    from dwg_converter import converter_status, convert_to_dxf

    saved = []
    for idx, f in enumerate(files):
        label = None
        if levels and idx < len(levels):
            lv = (levels[idx] or "").strip()
            if lv:
                label = lv
        saved.append((f.filename, await save_upload(f), label))
    logger.info(f"/parse-multi: {len(saved)} files, labels={[s[2] for s in saved]}, converter: {converter_status()['strategy']}")

    status = converter_status()

    if status.get("tool"):
        # FAST PATH: ODA converts all DWG→DXF locally, then ezdxf reads them
        return await _parse_multi_fast(saved, nb_niveaux, ville or "Dakar", beton)
    else:
        # SLOW PATH: async APS — launch background thread
        job_id = str(uuid.uuid4())[:12]
        with _parse_jobs_lock:
            _parse_jobs[job_id] = {
                "status": "processing", "progress": f"0/{len(saved)}",
                "total": len(saved), "done": 0, "result": None, "error": None,
            }
        t = threading.Thread(target=_parse_multi_worker,
                             args=(job_id, saved, nb_niveaux, ville or "Dakar", beton),
                             daemon=True)
        t.start()
        return JSONResponse(content={"ok": True, "job_id": job_id, "files_count": len(saved),
                                     "async": True, "strategy": "aps"})


async def _parse_multi_fast(saved_files, nb_niveaux, ville, beton):
    """Fast multi-file parsing via ODA + ezdxf. Returns result directly (no polling)."""
    from dwg_converter import convert_to_dxf
    import time as _time

    start = _time.time()
    niv = nb_niveaux or len(saved_files)
    dwg_geometry = {}
    main_result = None
    dxf_temps = []

    # Normalize to 3-tuples (filename, filepath, explicit_label_or_none)
    normalized = []
    for item in saved_files:
        if len(item) == 3:
            normalized.append(item)
        else:
            normalized.append((item[0], item[1], None))

    # Sort by size desc — biggest first for main params
    sorted_files = sorted(normalized, key=lambda x: os.path.getsize(x[1]), reverse=True)

    for i, (filename, filepath, explicit_label) in enumerate(sorted_files):
        dxf_path = None
        try:
            ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

            # ── PDF path: per-page extraction so multi-page PDFs add multiple levels
            if ext == 'pdf':
                # Extract params from biggest PDF
                if i == 0:
                    from parse_plans import extraire_params
                    main_result = extraire_params(filepath)
                # Per-page CV → dict of levels (or flat geom)
                try:
                    from cv_geometry_extractor import extract_geometry_per_page_cv
                    pdf_multi = extract_geometry_per_page_cv(filepath, use_vision=True)
                except Exception as e:
                    logger.warning(f"  {filename} per-page CV failed: {e}")
                    pdf_multi = None
                if pdf_multi:
                    if 'walls' in pdf_multi:
                        # Single page only — classify by filename or explicit label
                        level_key = explicit_label or _classify_level_from_name(filename, len(dwg_geometry))
                        pdf_multi['label'] = filename.rsplit('.', 1)[0]
                        # Don't overwrite an existing better level
                        if level_key not in dwg_geometry or len(pdf_multi.get('walls', [])) > len(dwg_geometry[level_key].get('walls', [])):
                            dwg_geometry[level_key] = pdf_multi
                            logger.info(f"  {level_key} (PDF): {len(pdf_multi.get('walls',[]))} walls")
                    else:
                        # Multi-level dict — merge each page
                        for plvl, pgeom in pdf_multi.items():
                            pgeom['label'] = f"{filename.rsplit('.',1)[0]} — {plvl}"
                            if plvl not in dwg_geometry or len(pgeom.get('walls', [])) > len(dwg_geometry[plvl].get('walls', [])):
                                dwg_geometry[plvl] = pgeom
                                logger.info(f"  {plvl} (PDF p.{pgeom.get('_cv_meta',{}).get('source_page_idx','?')}): {len(pgeom.get('walls',[]))} walls")
                continue

            # ── DWG/DXF path: convert to DXF, extract via ezdxf
            dxf_path = convert_to_dxf(filepath, ville)
            if not dxf_path:
                logger.warning(f"  {filename}: DXF conversion failed")
                continue
            dxf_geom = _extract_dxf_geometry(dxf_path)
            if i == 0:
                from parse_plans import extraire_params
                main_result = extraire_params(dxf_path)
            if dxf_geom:
                level_key = explicit_label or _classify_level_from_name(filename, i)
                dxf_geom['label'] = filename.rsplit('.', 1)[0]
                if level_key in dwg_geometry and len(dxf_geom.get('walls', [])) <= len(dwg_geometry[level_key].get('walls', [])):
                    pass  # keep existing richer geom
                else:
                    dwg_geometry[level_key] = dxf_geom
                walls = len(dxf_geom.get('walls', []))
                rooms = len(dxf_geom.get('rooms', []))
                logger.info(f"  {level_key}: {walls} walls, {rooms} rooms")

        except Exception as e:
            logger.warning(f"  {filename} failed: {e}")
        finally:
            if dxf_path and dxf_path != filepath:
                try: os.unlink(dxf_path)
                except OSError: pass
            try: os.unlink(filepath)
            except OSError: pass

    elapsed = _time.time() - start
    logger.info(f"/parse-multi FAST: {len(dwg_geometry)} levels in {elapsed:.1f}s")

    if not main_result or not main_result.get("ok"):
        main_result = {"ok": True, "source": "multi_dwg"}

    # Auto-detect nb_niveaux from DXF level keys if user didn't specify
    detected_levels = _count_levels_from_geometry(dwg_geometry)
    if detected_levels > 0 and not nb_niveaux:
        niv = detected_levels
        logger.info(f"Auto-detected {niv} levels from DXF filenames")

    # Estimate occupants from room labels across all levels
    all_rooms = []
    for geom in dwg_geometry.values():
        if isinstance(geom, dict):
            all_rooms.extend(geom.get('rooms', []))
    nb_occupants = _estimate_occupants_from_rooms(all_rooms)
    if nb_occupants > 0:
        logger.info(f"Estimated {nb_occupants} occupants from {len(all_rooms)} room labels")

    main_result["nb_niveaux"] = niv
    main_result["nb_occupants"] = nb_occupants
    main_result["files_count"] = len(saved_files)
    main_result["levels_detected"] = list(dwg_geometry.keys())
    main_result["parse_time_s"] = round(elapsed, 1)
    if main_result.get("donnees_moteur"):
        main_result["donnees_moteur"]["nb_niveaux"] = niv
        if nb_occupants > 0:
            main_result["donnees_moteur"]["nb_occupants"] = nb_occupants
    else:
        dm = {"nb_niveaux": niv, "ville": ville}
        if nb_occupants > 0:
            dm["nb_occupants"] = nb_occupants
        main_result["donnees_moteur"] = dm

    if dwg_geometry:
        main_result["dwg_geometry"] = dwg_geometry
        try:
            main_result["geom_ref"] = _save_geometry(dwg_geometry)
        except Exception as e:
            logger.warning(f"Failed to cache multi-level geometry: {e}")

    return JSONResponse(content=main_result)


@app.get("/parse-status/{job_id}")
async def parse_multi_status(job_id: str):
    """Poll for multi-DWG parse job status."""
    with _parse_jobs_lock:
        job = _parse_jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        # Make a copy to return outside the lock
        job_snapshot = {
            "status": job["status"],
            "progress": job["progress"],
            "done": job["done"],
            "total": job["total"],
            "result": job["result"],
            "error": job["error"],
        }
    return JSONResponse(content=job_snapshot)


def _update_job(job_id: str, **kwargs):
    """Thread-safe job state update."""
    with _parse_jobs_lock:
        if job_id in _parse_jobs:
            _parse_jobs[job_id].update(kwargs)

def _parse_multi_worker(job_id, saved_files, nb_niveaux, ville, beton):
    """Background worker: parse each DWG file via APS."""
    import re as _re
    try:
        from aps_parser_v2 import parser_dwg_aps

        # Normalize to 3-tuples: (filename, filepath, explicit_label_or_none)
        normalized = []
        for item in saved_files:
            if len(item) == 3:
                normalized.append(item)
            else:
                normalized.append((item[0], item[1], None))

        # Sort by size descending — largest file first (most geometry)
        sorted_files = sorted(normalized, key=lambda x: os.path.getsize(x[1]), reverse=True)

        # Parse main file first (largest) for params
        main_name, main_path, main_label = sorted_files[0]
        logger.info(f"  Job {job_id}: parsing main file {main_name}")
        main_result = parser_dwg_aps(main_path, nb_niveaux=nb_niveaux or len(saved_files),
                                      ville=ville)
        _update_job(job_id, done=1, progress=f"1/{len(saved_files)}")

        if not main_result.get("ok"):
            _update_job(job_id, status="error", error=main_result.get("message", "Main file parse failed"))
            return

        result = main_result
        nb_niv = nb_niveaux or len(saved_files)
        result["nb_niveaux"] = nb_niv
        result["donnees_moteur"]["nb_niveaux"] = nb_niv
        result["files_count"] = len(saved_files)

        # Extract geometry from main file
        main_geom = None
        if result.get("urn"):
            try:
                main_geom = _load_project_geometry(result["urn"])
            except Exception as e:
                logger.warning(f"  Main geometry extraction failed: {e}")

        # Parse remaining files for their geometry
        dwg_geometry = {}
        if main_geom:
            # Classify main file (use explicit label if provided)
            level_key = main_label or _classify_level_from_name(main_name, len(dwg_geometry))
            main_geom['label'] = main_name.replace('.dwg', '').replace('.DWG', '')
            dwg_geometry[level_key] = main_geom

        for i, (filename, filepath, explicit_label) in enumerate(sorted_files[1:], start=2):
            try:
                logger.info(f"  Job {job_id}: parsing {filename} ({i}/{len(sorted_files)})")
                level_result = parser_dwg_aps(filepath, nb_niveaux=nb_niv, ville=ville)
                _update_job(job_id, done=i, progress=f"{i}/{len(sorted_files)}")

                if level_result.get("ok") and level_result.get("urn"):
                    geom = _load_project_geometry(level_result["urn"])
                    if geom:
                        level_key = explicit_label or _classify_level_from_name(filename, len(dwg_geometry))
                        geom['label'] = filename.replace('.dwg', '').replace('.DWG', '')
                        dwg_geometry[level_key] = geom
                        logger.info(f"    {level_key}: {len(geom.get('walls', []))} walls")
            except Exception as e:
                logger.warning(f"    {filename} parse failed: {e}")

        if dwg_geometry:
            result["dwg_geometry"] = dwg_geometry
            result["levels_detected"] = list(dwg_geometry.keys())
            try:
                result["geom_ref"] = _save_geometry(dwg_geometry)
            except Exception as e:
                logger.warning(f"Failed to cache batch geometry: {e}")

        _update_job(job_id, result=result, status="done",
                   progress=f"{len(sorted_files)}/{len(sorted_files)}")
        logger.info(f"  Job {job_id}: DONE — {len(dwg_geometry)} levels parsed")

    except Exception as e:
        logger.error(f"  Job {job_id} error: {e}")
        _update_job(job_id, status="error", error=str(e))
    finally:
        # Cleanup temp files (accept both 2-tuple and 3-tuple shapes)
        for item in saved_files:
            p = item[1] if len(item) >= 2 else None
            if p:
                try: os.unlink(p)
                except OSError: pass


def _count_levels_from_geometry(dwg_geometry: dict) -> int:
    """
    Count real building levels from DWG geometry keys.
    Keys like SOUS_SOL, RDC, ETAGE_1, ETAGE_1_7, TERRASSE → count distinct levels.
    Returns 0 if level count cannot be determined.
    """
    import re as _re
    if not dwg_geometry or 'walls' in dwg_geometry:
        return 0  # single geometry, can't count levels

    count = 0
    for key in dwg_geometry.keys():
        upper = str(key).upper()
        if 'SOUS' in upper or 'BASEMENT' in upper or 'PARKING' in upper:
            count += 1
        elif 'RDC' in upper or 'REZ' in upper or 'GROUND' in upper:
            count += 1
        elif 'TERRASSE' in upper or 'ROOFTOP' in upper or 'TOITURE' in upper:
            count += 1
        else:
            # ETAGE_1_7 means floors 1 through 7 = 7 levels
            nums = _re.findall(r'(\d+)', upper)
            if len(nums) >= 2:
                lo, hi = int(nums[0]), int(nums[-1])
                count += max(1, hi - lo + 1)
            elif len(nums) == 1:
                count += 1
            else:
                count += 1
    return count


def _estimate_occupants_from_rooms(rooms: list) -> int:
    """
    Estimate nb_occupants from room labels using DTU ratios:
    chambre=2, studio=1, salon/séjour=3, bureau=1, salle=4,
    restaurant=10, magasin=5, hotel room=2.
    """
    import re as _re
    if not rooms:
        return 0

    total = 0
    for r in rooms:
        name = r.get('name', '').lower().strip()
        if not name:
            continue
        if any(k in name for k in ['chambre', 'bedroom', 'ch.']):
            total += 2
        elif any(k in name for k in ['studio', 'f1']):
            total += 1
        elif any(k in name for k in ['salon', 'séjour', 'sejour', 'living']):
            total += 3
        elif any(k in name for k in ['cuisine', 'kitchen']):
            total += 2
        elif any(k in name for k in ['bureau', 'office']):
            total += 1
        elif any(k in name for k in ['salle', 'room']):
            total += 4
        elif any(k in name for k in ['restaurant', 'bar']):
            total += 10
        elif any(k in name for k in ['magasin', 'shop', 'boutique']):
            total += 5
        elif any(k in name for k in ['gym', 'piscine', 'pool']):
            total += 8
    return total


def _classify_level_from_name(filename, fallback_index):
    """Classify a DWG file as a building level from its filename."""
    import re as _re
    upper = filename.upper()
    if any(k in upper for k in ['SOUS-SOL', 'SOUS SOL', 'PARKING', 'BASEMENT']):
        return 'SOUS_SOL'
    if any(k in upper for k in ['REZ', 'RDC', 'GROUND']):
        return 'RDC'
    if any(k in upper for k in ['TERRASSE', 'ROOFTOP', 'TOITURE']):
        return 'TERRASSE'
    # Extract etage numbers
    if 'ETAGE' in upper or 'FLOOR' in upper or 'LEVEL' in upper:
        nums = _re.findall(r'(\d+)', upper.split('ETAGE')[-1] if 'ETAGE' in upper else upper)
        etage_nums = [int(n) for n in nums if 0 < int(n) < 50]
        if etage_nums:
            if len(etage_nums) > 1:
                return f"ETAGE_{min(etage_nums)}_{max(etage_nums)}"
            return f"ETAGE_{etage_nums[0]}"
    return f"LEVEL_{fallback_index}"


def _extract_dxf_geometry(filepath: str) -> dict:
    """Extract full geometry from a DXF file using ezdxf — same format as sakho_*_geom.json.

    Strategy:
    1) Try named layers (MUR, WALL, A-WALL, etc.)
    2) If <5 walls found, try fuzzy layer matching (any layer containing 'mur', 'wall', etc.)
    3) If still <5 walls, fallback: treat ALL LINE/LWPOLYLINE as potential walls (universal mode)
    This ensures geometry extraction works regardless of layer naming conventions.
    """
    import ezdxf, re
    doc = ezdxf.readfile(filepath)
    msp = doc.modelspace()

    # Exact match layers
    wall_layers = {'MUR', 'MURS', 'A-MUR', '0_MURS', 'WALL', 'WALLS', 'A-WALL', 'I-WALL',
                   'A-WALL-FULL', 'A-WALL-INTR', 'A-WALL-EXTR', 'S_Walls', 'Walls',
                   'MURS_EXT', 'MURS_INT', 'MURS EXTERIEURS', 'MURS INTERIEURS',
                   'STR_WALLS', 'STRUCTURE_WALLS', 'CLOISONS'}
    window_layers = {'A-ALUMINIUM', 'ALUMINIUM', 'A-GLAZ', 'A-VERRE', 'A-HACH VERRE', 'A-GLAZ',
                     'WINDOW', 'WINDOWS', 'A-WINDOW', 'FENETRES', 'FENETRE', 'VITRAGE',
                     'S_Windows', 'Windows', 'A-GLAZ-SILL'}
    door_layers = {'DOOR', 'S_Doors', 'BOIS', 'PORTE', 'A-DOOR', 'PORTES', 'DOORS',
                   'A-DOOR-FULL', 'A-DOOR-INTR', 'Doors', 'MENUISERIES'}
    sanitary_layers = {'SANITAIRE', 'A-SANITAIRES', 'AM FITTING-SANITARY', 'STR_SANITARY',
                       'PLUMBING', 'A-PLUMBING', 'SANITARY'}

    # Fuzzy keywords for layer name detection
    _wall_keywords = ['mur', 'wall', 'cloison', 'paroi', 'partition']
    _window_keywords = ['window', 'fenêtre', 'fenetre', 'glaz', 'vitrage', 'alumin']
    _door_keywords = ['door', 'porte', 'menuiser']

    def _layer_matches(layer_name, keywords):
        ln = layer_name.lower().strip()
        return any(k in ln for k in keywords)

    # Log all layers for diagnostics
    all_layers = sorted(set(e.dxf.layer for e in msp))
    logger.info(f"[DXF] File: {filepath} — {len(all_layers)} layers: {all_layers[:30]}")

    geometry = {'walls': [], 'windows': [], 'doors': [], 'sanitary': [], 'rooms': [], 'axes_x': [], 'axes_y': []}

    def _add_entity(entity, target):
        if entity.dxftype() == 'LINE':
            target.append({'type': 'line',
                           'start': [round(entity.dxf.start.x, 1), round(entity.dxf.start.y, 1)],
                           'end': [round(entity.dxf.end.x, 1), round(entity.dxf.end.y, 1)]})
        elif entity.dxftype() == 'LWPOLYLINE':
            pts = [[round(p[0], 1), round(p[1], 1)] for p in entity.get_points()]
            target.append({'type': 'polyline', 'points': pts, 'closed': entity.closed})
        elif entity.dxftype() == 'CIRCLE':
            target.append({'type': 'circle',
                           'center': [round(entity.dxf.center.x, 1), round(entity.dxf.center.y, 1)],
                           'radius': round(entity.dxf.radius, 1)})
        elif entity.dxftype() == 'ARC':
            target.append({'type': 'arc',
                           'center': [round(entity.dxf.center.x, 1), round(entity.dxf.center.y, 1)],
                           'radius': round(entity.dxf.radius, 1),
                           'start_angle': round(entity.dxf.start_angle, 1),
                           'end_angle': round(entity.dxf.end_angle, 1)})

    # ── PASS 1: Exact layer name matching ──
    for e in msp:
        layer = e.dxf.layer
        if layer in wall_layers:
            _add_entity(e, geometry['walls'])
        elif layer in window_layers:
            _add_entity(e, geometry['windows'])
        elif layer in door_layers:
            _add_entity(e, geometry['doors'])
        elif layer in sanitary_layers:
            _add_entity(e, geometry['sanitary'])
        elif e.dxftype() in ('TEXT', 'MTEXT'):
            room_label_layers = {
                'etiquettes de pièces', 'etiquettes de pieces', 'etiquettes',
                'room', 'rooms', 'room labels', 'room_labels', 'a-room',
                'a-room-name', 'a-room-iden', 'a-anno-room', 'pièces', 'pieces',
                'text', 'texte', 'textes', 'labels', 'a-area', 'a-area-iden',
                'annotation', 'annotations', 'a-anno', 'a-text',
                'noms', 'noms de pièces', 'noms_pieces',
            }
            layer_low = layer.lower().strip()
            if layer_low in room_label_layers or 'room' in layer_low or 'pièce' in layer_low or 'piece' in layer_low or 'etiquette' in layer_low:
                try:
                    txt = e.text if e.dxftype() == 'MTEXT' else e.dxf.text
                    txt = re.sub(r'\\[^;]*;', '', txt).strip()
                    if txt and len(txt) >= 2 and len(txt) <= 50:
                        pos = e.dxf.insert
                        geometry['rooms'].append({'name': txt, 'x': round(pos.x, 1), 'y': round(pos.y, 1)})
                except Exception:
                    pass

    logger.info(f"[DXF] Pass 1 (exact layers): {len(geometry['walls'])} walls, "
                f"{len(geometry['windows'])} windows, {len(geometry['doors'])} doors, "
                f"{len(geometry['rooms'])} rooms")

    # ── PASS 2: Fuzzy layer name matching (if pass 1 found <5 walls) ──
    if len(geometry['walls']) < 5:
        logger.info("[DXF] Pass 1 insufficient — trying fuzzy layer matching")
        for e in msp:
            layer = e.dxf.layer
            if e.dxftype() in ('LINE', 'LWPOLYLINE', 'POLYLINE'):
                if _layer_matches(layer, _wall_keywords) and layer not in wall_layers:
                    _add_entity(e, geometry['walls'])
                elif _layer_matches(layer, _window_keywords) and layer not in window_layers:
                    _add_entity(e, geometry['windows'])
                elif _layer_matches(layer, _door_keywords) and layer not in door_layers:
                    _add_entity(e, geometry['doors'])
        logger.info(f"[DXF] Pass 2 (fuzzy): {len(geometry['walls'])} walls")

    # ── PASS 3: Universal fallback — ALL geometric entities as walls ──
    if len(geometry['walls']) < 5:
        logger.warning("[DXF] Pass 2 insufficient — universal fallback: scanning ALL entities")
        # Collect ALL LINE/LWPOLYLINE from ALL layers (except known non-wall layers)
        skip_layers = {'DEFPOINTS', 'DIMENSIONS', 'DIM', 'HATCH', 'VIEWPORT', 'TITLE',
                       'TITLEBLOCK', 'CARTOUCHE', 'BORDER', 'CADRE', 'LOGO'}
        all_entities = []
        for e in msp:
            layer_up = e.dxf.layer.upper()
            if layer_up in skip_layers or 'DIM' in layer_up or 'HATCH' in layer_up:
                continue
            if e.dxftype() in ('LINE', 'LWPOLYLINE', 'POLYLINE'):
                _add_entity(e, all_entities)

        if len(all_entities) >= 5:
            # Filter: keep only entities with significant length (>500mm)
            # to exclude dimension ticks, leader lines, etc.
            def _entity_length(ent):
                if ent['type'] == 'line':
                    dx = ent['end'][0] - ent['start'][0]
                    dy = ent['end'][1] - ent['start'][1]
                    return (dx**2 + dy**2) ** 0.5
                elif ent['type'] == 'polyline' and len(ent.get('points', [])) >= 2:
                    total = 0
                    pts = ent['points']
                    for i in range(len(pts) - 1):
                        dx = pts[i+1][0] - pts[i][0]
                        dy = pts[i+1][1] - pts[i][1]
                        total += (dx**2 + dy**2) ** 0.5
                    return total
                return 0

            significant = [e for e in all_entities if _entity_length(e) > 500]
            if len(significant) >= 5:
                geometry['walls'] = significant
                geometry['_fallback_mode'] = 'universal'
                logger.info(f"[DXF] Universal fallback: {len(significant)} wall-like entities "
                            f"(from {len(all_entities)} total, filtered >500mm)")

        # Also scan ALL text entities for room labels
        if not geometry['rooms']:
            for e in msp:
                if e.dxftype() in ('TEXT', 'MTEXT'):
                    try:
                        txt = e.text if e.dxftype() == 'MTEXT' else e.dxf.text
                        txt = re.sub(r'\\[^;]*;', '', txt).strip()
                        if txt and 2 <= len(txt) <= 50:
                            pos = e.dxf.insert
                            geometry['rooms'].append({'name': txt, 'x': round(pos.x, 1), 'y': round(pos.y, 1)})
                    except Exception:
                        pass
            if geometry['rooms']:
                logger.info(f"[DXF] Universal fallback: {len(geometry['rooms'])} room labels from all text")

    # Extract structural axes from dedicated layers
    axis_layers = {'AXES', 'A-AXES', 'GRILLE', 'S-GRID', 'GRID', 'AXE', 'STRUCTURE_AXES'}
    axes_x_set = set()
    axes_y_set = set()
    tolerance = 50.0  # 50mm tolerance for deduplication

    for e in msp:
        if e.dxf.layer in axis_layers and e.dxftype() == 'LINE':
            x1, y1 = e.dxf.start.x, e.dxf.start.y
            x2, y2 = e.dxf.end.x, e.dxf.end.y
            dx = abs(x2 - x1)
            dy = abs(y2 - y1)

            # Mostly vertical line → extract X coordinate
            if dx < dy:
                x_val = round(x1)
                # Add if not already close to existing value
                if not any(abs(x_val - existing) < tolerance for existing in axes_x_set):
                    axes_x_set.add(x_val)

            # Mostly horizontal line → extract Y coordinate
            elif dy < dx:
                y_val = round(y1)
                # Add if not already close to existing value
                if not any(abs(y_val - existing) < tolerance for existing in axes_y_set):
                    axes_y_set.add(y_val)

    # Sort and store as lists
    geometry['axes_x'] = sorted(list(axes_x_set))
    geometry['axes_y'] = sorted(list(axes_y_set))

    # If no rooms detected from labels, infer from wall topology
    if not geometry['rooms'] and len(geometry['walls']) >= 10:
        try:
            inferred = _infer_rooms_from_walls(geometry)
            if inferred:
                geometry['rooms'] = inferred
                logger.info(f"Inferred {len(inferred)} rooms from wall topology")
        except Exception as e:
            logger.warning(f"Room inference failed (non-fatal): {e}")

    n_walls = len(geometry['walls'])
    n_axes = len(geometry.get('axes_x', [])) + len(geometry.get('axes_y', []))
    # Accept if we have enough walls OR if we have axes + some walls
    if n_walls >= 5 or (n_walls >= 3 and n_axes >= 4):
        logger.info(f"[DXF] Geometry accepted: {n_walls} walls, {n_axes} axes, "
                    f"{len(geometry.get('rooms', []))} rooms, "
                    f"mode={'universal' if geometry.get('_fallback_mode') else 'named_layers'}")
        return geometry
    logger.warning(f"[DXF] Geometry REJECTED: only {n_walls} walls, {n_axes} axes — "
                   f"layers in file: {all_layers[:20]}")
    return None


def _infer_rooms_from_walls(geom: dict) -> list:
    """Infer rooms from wall geometry using rasterization + contour detection.

    Rasterizes walls onto a binary grid, finds enclosed contour regions,
    then classifies rooms by area (small=wet, medium=bedroom, large=living).
    Returns list of {'name': str, 'x': float, 'y': float} in model-space coords.
    """
    try:
        import numpy as np
    except ImportError:
        return []

    walls = geom.get('walls', [])
    if len(walls) < 10:
        return []

    # Collect all wall endpoints to find bounds
    pts = []
    for w in walls:
        if w.get('type') == 'line':
            pts.append(w['start'])
            pts.append(w['end'])
        elif w.get('type') == 'polyline':
            pts.extend(w.get('points', []))
    if len(pts) < 4:
        return []

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    w_range = xmax - xmin
    h_range = ymax - ymin
    if w_range < 100 or h_range < 100:
        return []

    # Rasterize at ~100mm per pixel (enough for room detection, fast)
    CELL = 100.0  # mm per pixel
    img_w = int(w_range / CELL) + 2
    img_h = int(h_range / CELL) + 2
    # Cap image size to avoid memory issues
    if img_w > 2000 or img_h > 2000:
        CELL = max(w_range, h_range) / 1500.0
        img_w = int(w_range / CELL) + 2
        img_h = int(h_range / CELL) + 2

    grid = np.zeros((img_h, img_w), dtype=np.uint8)

    def to_px(x, y):
        px = int((x - xmin) / CELL)
        py = int((y - ymin) / CELL)
        return max(0, min(px, img_w - 1)), max(0, min(py, img_h - 1))

    # Draw walls on grid using Bresenham-like line rasterization
    def draw_line(x1, y1, x2, y2):
        px1, py1 = to_px(x1, y1)
        px2, py2 = to_px(x2, y2)
        # Simple DDA line drawing with wall thickness = 2px
        steps = max(abs(px2 - px1), abs(py2 - py1), 1)
        for i in range(steps + 1):
            t = i / steps
            cx = int(px1 + t * (px2 - px1))
            cy = int(py1 + t * (py2 - py1))
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < img_w and 0 <= ny < img_h:
                        grid[ny, nx] = 255

    for w in walls:
        if w.get('type') == 'line':
            draw_line(w['start'][0], w['start'][1], w['end'][0], w['end'][1])
        elif w.get('type') == 'polyline':
            wpts = w.get('points', [])
            for i in range(len(wpts) - 1):
                draw_line(wpts[i][0], wpts[i][1], wpts[i + 1][0], wpts[i + 1][1])
            if w.get('closed') and len(wpts) >= 3:
                draw_line(wpts[-1][0], wpts[-1][1], wpts[0][0], wpts[0][1])

    # Flood-fill from border to mark exterior
    exterior = np.zeros_like(grid)
    # Use simple scanline flood fill from all border pixels
    from collections import deque
    queue = deque()
    for x in range(img_w):
        if grid[0, x] == 0 and exterior[0, x] == 0:
            queue.append((x, 0))
            exterior[0, x] = 1
        if grid[img_h - 1, x] == 0 and exterior[img_h - 1, x] == 0:
            queue.append((x, img_h - 1))
            exterior[img_h - 1, x] = 1
    for y in range(img_h):
        if grid[y, 0] == 0 and exterior[y, 0] == 0:
            queue.append((0, y))
            exterior[y, 0] = 1
        if grid[y, img_w - 1] == 0 and exterior[y, img_w - 1] == 0:
            queue.append((img_w - 1, y))
            exterior[y, img_w - 1] = 1

    while queue:
        cx, cy = queue.popleft()
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < img_w and 0 <= ny < img_h and grid[ny, nx] == 0 and exterior[ny, nx] == 0:
                exterior[ny, nx] = 1
                queue.append((nx, ny))

    # Interior pixels = not wall and not exterior
    interior = (grid == 0) & (exterior == 0)

    # Connected component labeling on interior pixels
    labels = np.zeros_like(grid, dtype=np.int32)
    label_id = 0
    regions = []  # (label_id, pixel_count, sum_x, sum_y)

    for y in range(img_h):
        for x in range(img_w):
            if interior[y, x] and labels[y, x] == 0:
                label_id += 1
                # BFS to label this region
                rq = deque()
                rq.append((x, y))
                labels[y, x] = label_id
                count = 0
                sx, sy = 0.0, 0.0
                while rq:
                    rx, ry = rq.popleft()
                    count += 1
                    sx += rx
                    sy += ry
                    for ddx, ddy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                        nnx, nny = rx + ddx, ry + ddy
                        if 0 <= nnx < img_w and 0 <= nny < img_h and interior[nny, nnx] and labels[nny, nnx] == 0:
                            labels[nny, nnx] = label_id
                            rq.append((nnx, nny))
                if count >= 5:  # Minimum 5 pixels (~0.5m² at 100mm/px)
                    regions.append((label_id, count, sx / count, sy / count))

    if not regions:
        return []

    # Sort by area descending, take top 50 max
    regions.sort(key=lambda r: r[1], reverse=True)
    regions = regions[:50]

    # Classify rooms by area and assign names
    rooms = []
    # Area thresholds in pixels (at CELL mm/px):
    # 1 pixel = CELL² mm² → area_mm2 = count * CELL²
    # Wet room: 2-8 m² → 20000-80000 mm² → 2-8 pixels at 100mm/px
    # Actually at 100mm/px, 1px = 0.01m², so 2m² = 200px, 8m² = 800px
    px_per_m2 = (1000 / CELL) ** 2  # pixels per m²
    wet_count = 0
    bed_count = 0
    living_count = 0
    service_count = 0
    other_count = 0

    for lid, count, cx, cy in regions:
        area_m2 = count / px_per_m2
        # Convert centroid back to model-space
        mx = round(xmin + cx * CELL, 1)
        my = round(ymin + cy * CELL, 1)

        if area_m2 < 1.5:
            continue  # Too small, likely artifact
        elif area_m2 < 5:
            wet_count += 1
            name = f"SDB {wet_count}" if wet_count % 2 == 1 else f"WC {wet_count // 2}"
        elif area_m2 < 10:
            bed_count += 1
            name = f"Chambre {bed_count}"
        elif area_m2 < 25:
            living_count += 1
            if living_count == 1:
                name = "Salon/Séjour"
            elif living_count == 2:
                name = "Cuisine"
            else:
                name = f"Pièce {living_count}"
        elif area_m2 < 50:
            service_count += 1
            if service_count == 1:
                name = "Hall"
            else:
                name = f"Palier {service_count}"
        else:
            other_count += 1
            name = f"Espace {other_count}"

        rooms.append({'name': name, 'x': mx, 'y': my})

    logger.info(f"Room inference: {len(rooms)} rooms from {len(walls)} walls "
                f"(grid {img_w}x{img_h}, CELL={CELL}mm, {len(regions)} regions)")
    return rooms


@app.post("/parse-sol")
async def parse_sol(file: UploadFile = File(...)):
    from parse_sol import extraire_params_sol
    tmp_path = await save_upload(file)
    try:
        result = extraire_params_sol(tmp_path)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"/parse-sol error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try: os.unlink(tmp_path)
        except OSError: pass


@app.post("/calculate")
async def calculate(params: ParamsProjet):
    """Calcul structure EC2/EC8 — retourne tous les résultats."""
    try:
        _, _, calculer_structure = get_moteur_structure()
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        gc.collect()

        return {
            "ok": True,
            "params_input": params.dict(),
            "projet": params.nom,
            "classe_beton": rs.classe_beton,
            "classe_acier": rs.classe_acier,
            "distance_mer_km": rs.distance_mer_km,
            "pression_sol_MPa": rs.pression_sol_MPa,
            "zone_sismique": rs.zone_sismique,
            "charge_G_kNm2": rs.charge_G_kNm2,
            "charge_Q_kNm2": rs.charge_Q_kNm2,
            "poteaux": [dataclasses.asdict(p) for p in rs.poteaux],
            "poutre_principale": dataclasses.asdict(rs.poutre_principale),
            "poutre_secondaire": dataclasses.asdict(rs.poutre_secondaire) if rs.poutre_secondaire else None,
            "dalle": dataclasses.asdict(rs.dalle),
            "cloisons": {
                "surface_totale_m2": rs.cloisons.surface_totale_m2,
                "option_recommandee": rs.cloisons.option_recommandee.value,
                "charge_dalle_kn_m2": rs.cloisons.charge_dalle_kn_m2,
                "options": [
                    {
                        "type": o.type.value,
                        "materiau": o.materiau,
                        "epaisseur_cm": o.epaisseur_cm,
                        "prix_fcfa_m2": o.prix_fcfa_m2,
                        "avantages": o.avantages,
                        "inconvenients": o.inconvenients,
                    }
                    for o in rs.cloisons.options
                ],
            },
            "fondation": dataclasses.asdict(rs.fondation),
            "sismique": dataclasses.asdict(rs.sismique),
            "boq": dataclasses.asdict(rs.boq),
            "analyse": dataclasses.asdict(rs.analyse),
            "devise_info": get_devise_info(params.ville),
        }
    except Exception as e:
        logger.error(f"/calculate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _serialize_mep(rm, ville: str = None) -> dict:
    """Serialize ResultatsMEP to the JSON format expected by the frontend."""
    e = rm.edge
    return {
        "ok": True,
        "surf_batie_m2": rm.surf_batie_m2,
        "nb_logements": rm.nb_logements,
        "nb_personnes": rm.nb_personnes,
        "electrique": dataclasses.asdict(rm.electrique),
        "plomberie": dataclasses.asdict(rm.plomberie),
        "cvc": dataclasses.asdict(rm.cvc),
        "courants_faibles": dataclasses.asdict(rm.courants_faibles),
        "securite_incendie": dataclasses.asdict(rm.securite_incendie),
        "ascenseurs": dataclasses.asdict(rm.ascenseurs),
        "automatisation": dataclasses.asdict(rm.automatisation),
        "edge": {
            "economie_energie_pct": e.economie_energie_pct,
            "economie_eau_pct": e.economie_eau_pct,
            "economie_materiaux_pct": e.economie_materiaux_pct,
            "certifiable": e.certifiable,
            "niveau_certification": e.niveau_certification,
            "mesures_energie": e.mesures_energie,
            "mesures_eau": e.mesures_eau,
            "mesures_materiaux": e.mesures_materiaux,
            "plan_action": e.plan_action,
            "cout_mise_conformite_fcfa": e.cout_mise_conformite_fcfa,
            "roi_ans": e.roi_ans,
            "methode_calcul": e.methode_calcul,
            "note_generale": e.note_generale,
        },
        "boq_mep": {
            "basic_fcfa": rm.boq.total_basic_fcfa,
            "hend_fcfa": rm.boq.total_hend_fcfa,
            "luxury_fcfa": rm.boq.total_luxury_fcfa,
            "ratio_basic_m2": rm.boq.ratio_basic_m2,
            "ratio_hend_m2": rm.boq.ratio_hend_m2,
            "recommandation": rm.boq.recommandation,
            "note_choix": rm.boq.note_choix,
            "lots": [
                {
                    "lot": l.lot,
                    "designation": l.designation,
                    "basic_fcfa": l.pu_basic_fcfa,
                    "hend_fcfa": l.pu_hend_fcfa,
                    "luxury_fcfa": l.pu_luxury_fcfa,
                    "note": l.note_impact,
                }
                for l in rm.boq.lots
            ],
        },
        "devise_info": get_devise_info(ville) if ville else None,
    }


@app.post("/calculate-mep")
async def calculate_mep_endpoint(params: ParamsProjet):
    """Calcul MEP complet — retourne tous les résultats."""
    try:
        _, _, calculer_structure = get_moteur_structure()
        calculer_mep = get_moteur_mep()
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        rm = calculer_mep(donnees, rs)
        gc.collect()

        result = _serialize_mep(rm, params.ville)
        result["projet"] = params.nom
        return result
    except Exception as e:
        logger.error(f"/calculate-mep error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ════════════════════════════════════════════════════════════
# PDF GENERATION — FR/EN ROUTING
# ════════════════════════════════════════════════════════════

@app.post("/generate")
async def generate_note_structure(params: ParamsProjet):
    """Note de calcul structure PDF — 9 pages EC2/EC8 (FR/EN)."""
    try:
        _, _, calculer_structure = get_moteur_structure()
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        set_pdf_lang(getattr(params, 'lang', 'fr'))
        set_pdf_devise(get_devise_info(params.ville))

        if is_en(params):
            generer = get_gen_note_structure_en()
        else:
            generer = get_gen_note_structure()

        pdf_bytes = generer(rs, params.dict())
        gc.collect()
        return pdf_response(pdf_bytes, fname(params, "note_structure"))
    except Exception as e:
        logger.error(f"/generate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-boq")
async def generate_boq_structure(params: ParamsProjet):
    """BOQ structure détaillé PDF — 7 lots (FR/EN)."""
    try:
        _, _, calculer_structure = get_moteur_structure()
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        set_pdf_lang(getattr(params, 'lang', 'fr'))
        set_pdf_devise(get_devise_info(params.ville))

        if is_en(params):
            generer = get_gen_boq_structure_en()
        else:
            generer = get_gen_boq_structure()

        pdf_bytes = generer(rs, params.dict())
        gc.collect()
        return pdf_response(pdf_bytes, fname(params, "boq_structure"))
    except Exception as e:
        logger.error(f"/generate-boq error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-note-mep")
async def generate_note_mep(params: ParamsProjet):
    """Note de calcul MEP complète PDF (FR/EN)."""
    try:
        _, _, calculer_structure = get_moteur_structure()
        calculer_mep = get_moteur_mep()
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        rm = calculer_mep(donnees, rs)
        set_pdf_lang(getattr(params, 'lang', 'fr'))
        set_pdf_devise(get_devise_info(params.ville))

        if is_en(params):
            generer = get_gen_note_mep_en()
        else:
            generer = get_gen_note_mep()

        pdf_bytes = generer(rm, params.dict())
        gc.collect()
        return pdf_response(pdf_bytes, fname(params, "note_mep"))
    except Exception as e:
        logger.error(f"/generate-note-mep error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-boq-mep")
async def generate_boq_mep(params: ParamsProjet):
    """BOQ MEP détaillé PDF — 7 lots × 3 gammes (FR/EN)."""
    try:
        _, _, calculer_structure = get_moteur_structure()
        calculer_mep = get_moteur_mep()
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        rm = calculer_mep(donnees, rs)
        set_pdf_lang(getattr(params, 'lang', 'fr'))
        set_pdf_devise(get_devise_info(params.ville))

        if is_en(params):
            generer = get_gen_boq_mep_en()
        else:
            generer = get_gen_boq_mep()

        pdf_bytes = generer(rm, params.dict())
        gc.collect()
        return pdf_response(pdf_bytes, fname(params, "boq_mep"))
    except Exception as e:
        logger.error(f"/generate-boq-mep error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-edge-assessment")
async def generate_edge_assessment(params: ParamsProjet):
    """
    EDGE Assessment officiel (IFC EDGE v3.0.0) — PDF calqué sur le layout
    de la plateforme app.edgebuildings.com, calculs 100% locaux Tijan AI.
    """
    try:
        _, _, calculer_structure = get_moteur_structure()
        calculer_mep = get_moteur_mep()
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        rm = calculer_mep(donnees, rs)
        set_pdf_lang(getattr(params, 'lang', 'fr'))
        set_pdf_devise(get_devise_info(params.ville))

        from gen_edge_assessment import generer_edge_assessment
        params_dict = params.dict()
        # Auto-compute facade orientations from DXF geometry if available
        try:
            from geometry_orientations import compute_facade_orientations
            geom = _resolve_geometry(params)
            if geom and not params_dict.get('orientations'):
                orient = compute_facade_orientations(geom)
                if orient:
                    params_dict['orientations'] = orient
                    logger.info(f"/generate-edge-assessment: facade orientations from DXF "
                                f"({sum(o['len'] for o in orient.values()):.0f} m perimeter)")
        except Exception as e:
            logger.warning(f"Facade orientations extraction failed: {e}")
        pdf_bytes = generer_edge_assessment(rm, params_dict)
        gc.collect()
        return pdf_response(pdf_bytes, fname(params, "edge_assessment"))
    except Exception as e:
        logger.error(f"/generate-edge-assessment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-boq-xlsx")
async def generate_boq_xlsx(request: Request):
    """BOQ Structure as Excel (.xlsx) — Bilingual FR/EN."""
    try:
        body = await request.json()
        lang = body.pop("lang", "fr")
        params = ParamsProjet(**body)
        _, _, calculer_structure = get_moteur_structure()
        from gen_boq_xlsx import generer_boq_structure_xlsx
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        xlsx_bytes = generer_boq_structure_xlsx(rs, params.dict(), lang=lang)
        gc.collect()
        xlsx_name = f"tijan_boq_structure_{params.nom.replace(' ','_')[:20]}.xlsx"
        return StreamingResponse(
            io.BytesIO(xlsx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={xlsx_name}"},
        )
    except Exception as e:
        logger.error(f"/generate-boq-xlsx error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-boq-mep-xlsx")
async def generate_boq_mep_xlsx(request: Request):
    """BOQ MEP as Excel (.xlsx) — Bilingual FR/EN."""
    try:
        body = await request.json()
        lang = body.pop("lang", "fr")
        params = ParamsProjet(**body)
        _, _, calculer_structure = get_moteur_structure()
        calculer_mep = get_moteur_mep()
        from gen_boq_mep_xlsx import generer_boq_mep_xlsx
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        rm = calculer_mep(donnees, rs)
        xlsx_bytes = generer_boq_mep_xlsx(rm, params.dict(), lang=lang)
        gc.collect()
        xlsx_name = f"tijan_boq_mep_{params.nom.replace(' ','_')[:20]}.xlsx"
        return StreamingResponse(
            io.BytesIO(xlsx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={xlsx_name}"},
        )
    except Exception as e:
        logger.error(f"/generate-boq-mep-xlsx error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-boq-finitions")
async def generate_boq_finitions(params: ParamsProjet):
    """BOQ Finitions — 3 gammes Basic/High-End/Luxury — PDF"""
    try:
        from gen_boq_finitions import calculer_finitions, generer_boq_finitions_pdf
        resultats = calculer_finitions(
            surface_emprise_m2=params.surface_emprise_m2 or 300,
            nb_niveaux=params.nb_niveaux or 4,
            ville=params.ville or "Dakar"
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            out_path = tmp.name
        generer_boq_finitions_pdf(out_path, resultats, vars(params))
        with open(out_path, "rb") as f:
            pdf_bytes = f.read()
        os.unlink(out_path)
        gc.collect()
        return pdf_response(pdf_bytes, fname(params, "boq_finitions"))
    except Exception as e:
        logger.error(f"/generate-boq-finitions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/calculate-finitions")
async def calculate_finitions_endpoint(params: ParamsProjet):
    """Calcul finitions — retourne les 3 gammes en JSON"""
    try:
        from gen_boq_finitions import calculer_finitions
        resultats = calculer_finitions(
            surface_emprise_m2=params.surface_emprise_m2 or 300,
            nb_niveaux=params.nb_niveaux or 4,
            ville=params.ville or "Dakar"
        )
        return {"ok": True, "finitions": resultats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-note-docx")
async def generate_note_docx(request: Request):
    """Note de calcul structure as Word (.docx) — Bilingual FR/EN."""
    try:
        body = await request.json()
        lang = body.pop("lang", "fr")  # Extract lang (fr or en)
        params = ParamsProjet(**body)
        _, _, calculer_structure = get_moteur_structure()
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)

        if lang == "en":
            from gen_note_docx_en import generer as generer_note_docx_en
            docx_bytes = generer_note_docx_en(donnees, rs)
        else:
            from gen_note_docx import generer as generer_note_docx
            docx_bytes = generer_note_docx(donnees, rs)

        gc.collect()
        docx_name = f"tijan_note_structure_{params.nom.replace(' ','_')[:20]}.docx"
        return StreamingResponse(
            io.BytesIO(docx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={docx_name}"},
        )
    except Exception as e:
        logger.error(f"/generate-note-docx error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-rapport-docx")
async def generate_rapport_docx(request: Request):
    """Rapport exécutif as Word (.docx) — Bilingual FR/EN."""
    try:
        body = await request.json()
        lang = body.pop("lang", "fr")  # Extract lang (fr or en)
        params = ParamsProjet(**body)
        _, _, calculer_structure = get_moteur_structure()
        calculer_mep = get_moteur_mep()
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        rm = calculer_mep(donnees, rs)

        if lang == "en":
            from gen_rapport_docx_en import generer_rapport_executif_docx as generer_rapport_en
            docx_bytes = generer_rapport_en(rs, rm, params.dict())
        else:
            from gen_rapport_docx import generer_rapport_executif_docx
            docx_bytes = generer_rapport_executif_docx(rs, rm, params.dict())

        gc.collect()
        docx_name = f"tijan_rapport_executif_{params.nom.replace(' ','_')[:20]}.docx"
        return StreamingResponse(
            io.BytesIO(docx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={docx_name}"},
        )
    except Exception as e:
        logger.error(f"/generate-rapport-docx error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-rapport-executif")
async def generate_rapport_executif(params: ParamsProjet):
    """Rapport de synthèse exécutif PDF — maître d'ouvrage (FR/EN)."""
    try:
        _, _, calculer_structure = get_moteur_structure()
        calculer_mep = get_moteur_mep()
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        rm = calculer_mep(donnees, rs)
        set_pdf_lang(getattr(params, 'lang', 'fr'))
        set_pdf_devise(get_devise_info(params.ville))

        if is_en(params):
            generer = get_gen_executif_en()
        else:
            generer = get_gen_executif()

        pdf_bytes = generer(rs, rm, params.dict())
        gc.collect()
        return pdf_response(pdf_bytes, fname(params, "rapport_executif"))
    except Exception as e:
        logger.error(f"/generate-rapport-executif error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ════════════════════════════════════════════════════════════
# PDF GENERATION — FICHES (FR/EN)
# ════════════════════════════════════════════════════════════

@app.post("/generate-fiches-structure")
async def generate_fiches_structure(params: ParamsProjet):
    """Fiches techniques structure PDF (FR/EN)."""
    try:
        _, _, calculer_structure = get_moteur_structure()
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)

        if is_en(params):
            generer = get_gen_fiches_structure_en()
        else:
            generer = get_gen_fiches_structure()

        buf = io.BytesIO()
        generer(rs, buf, params.dict())
        pdf_bytes = buf.getvalue()
        gc.collect()
        return pdf_response(pdf_bytes, fname(params, "fiches_structure"))
    except Exception as e:
        logger.error(f"/generate-fiches-structure error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-fiches-mep")
async def generate_fiches_mep(params: ParamsProjet):
    """Fiches techniques MEP PDF (FR/EN)."""
    try:
        _, _, calculer_structure = get_moteur_structure()
        calculer_mep = get_moteur_mep()
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        rm = calculer_mep(donnees, rs)

        if is_en(params):
            generer = get_gen_fiches_mep_en()
        else:
            generer = get_gen_fiches_mep()

        buf = io.BytesIO()
        generer(rm, buf, params.dict())
        pdf_bytes = buf.getvalue()
        gc.collect()
        return pdf_response(pdf_bytes, fname(params, "fiches_mep"))
    except Exception as e:
        logger.error(f"/generate-fiches-mep error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-schemas-ferraillage")
async def generate_schemas_ferraillage(params: ParamsProjet):
    """Schemas de ferraillage (poteau, poutre, fondation) — propre onglet."""
    try:
        _, _, calculer_structure = get_moteur_structure()
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        set_pdf_lang(getattr(params, 'lang', 'fr'))
        set_pdf_devise(get_devise_info(params.ville))
        from gen_schemas_ferraillage import generer_schemas_ferraillage
        pdf_bytes = generer_schemas_ferraillage(rs, params.dict())
        gc.collect()
        return pdf_response(pdf_bytes, fname(params, "schemas_ferraillage"))
    except Exception as e:
        logger.error(f"/generate-schemas-ferraillage error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-schemas-mep")
async def generate_schemas_mep(params: ParamsProjet):
    """Schemas isometriques MEP (plomberie + electricite) — propre onglet."""
    try:
        _, _, calculer_structure = get_moteur_structure()
        calculer_mep = get_moteur_mep()
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        rm = calculer_mep(donnees, rs)
        set_pdf_lang(getattr(params, 'lang', 'fr'))
        set_pdf_devise(get_devise_info(params.ville))
        from gen_schemas_mep_iso import generer_schemas_mep_iso
        pdf_bytes = generer_schemas_mep_iso(rm, params.dict())
        gc.collect()
        return pdf_response(pdf_bytes, fname(params, "schemas_mep"))
    except Exception as e:
        logger.error(f"/generate-schemas-mep error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-planches")
async def generate_planches(params: ParamsProjet):
    """Planches BA PDF."""
    out_path = None
    try:
        _, _, calculer_structure = get_moteur_structure()
        generer = get_gen_planches()
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            out_path = tmp.name
        generer(out_path, resultats=rs, params=params.dict())
        with open(out_path, "rb") as f:
            pdf_bytes = f.read()
        return pdf_response(pdf_bytes, fname(params, "planches_BA"))
    except Exception as e:
        logger.error(f"/generate-planches error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if out_path:
            try:
                os.unlink(out_path)
            except OSError:
                pass
        gc.collect()




@app.post("/generate-plu")
async def generate_plu(params: ParamsProjet):
    """Plans PLU (plomberie/sanitaire) PDF — 11 planches A3."""
    out_path = None
    try:
        from generate_plans_plu_v1 import generer_plans_plu
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            out_path = tmp.name
        generer_plans_plu(out_path, params=params.dict())
        with open(out_path, "rb") as f:
            pdf_bytes = f.read()
        return pdf_response(pdf_bytes, fname(params, "plans_PLU"))
    except Exception as e:
        logger.error(f"/generate-plu error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if out_path:
            try:
                os.unlink(out_path)
            except OSError:
                pass
        gc.collect()


def _is_pdf_sourced_geometry(geom) -> bool:
    """True if geometry is explicitly marked as PDF-CV-sourced (unreliable for plans)."""
    if not geom or not isinstance(geom, dict):
        return False
    def _is_pdf(d):
        if not isinstance(d, dict):
            return False
        meta = d.get('_cv_meta') or {}
        return str(meta.get('source', '')).lower() == 'pdf'
    if _is_pdf(geom):
        return True
    return any(_is_pdf(v) for v in geom.values())


def _params_signal_pdf_input(params) -> bool:
    """True if the request carries archi_pdf_* markers WITHOUT a DWG signal (urn/geom_ref)."""
    def _get(name):
        return getattr(params, name, None) or (params.get(name) if isinstance(params, dict) else None)
    has_pdf_marker = bool(_get('archi_pdf_url') or _get('archi_pdf_ref'))
    has_dwg_marker = bool(_get('urn') or _get('geom_ref') or _get('dwg_geometry'))
    return has_pdf_marker and not has_dwg_marker


def _is_dwg_sourced_geometry(geom) -> bool:
    """Deprecated name kept for compatibility — inverse of PDF-sourced check."""
    return not _is_pdf_sourced_geometry(geom)


@app.post("/generate-plans-structure")
async def generate_plans_structure(params: ParamsProjet):
    """Plans structure PDF — nécessite une géométrie DWG/DXF réelle (input PDF refusé)."""
    out_path = None
    archi_pdf_path = None
    try:
        _, _, calculer_structure = get_moteur_structure()
        from generate_plans_structure_mep import generer_plans_structure
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        # Geometry priority: body > cache ref > APS URN > None (grid fallback)
        dwg_geometry = _resolve_geometry(params)
        # DWG-only policy: refuse only when explicitly PDF-sourced (CV pipeline
        # marker) OR when request carries PDF markers without any DWG signal.
        # If geom is missing and no PDF markers, fall through to parametric grid.
        if _is_pdf_sourced_geometry(dwg_geometry) or _params_signal_pdf_input(params):
            raise HTTPException(
                status_code=422,
                detail="Les plans structure nécessitent un fichier DWG/DXF en entrée. "
                       "L'import PDF est désactivé pour les plans (calculs et autres livrables restent disponibles)."
            )
        logger.info(f"/generate-plans-structure: geometry={'yes' if dwg_geometry else 'no'}"
                     f" walls={len(dwg_geometry.get('walls',[])) if dwg_geometry and 'walls' in dwg_geometry else '?'}")
        # Resolve archi PDF for background (from cache ref or URL)
        archi_pdf_path = _resolve_archi_pdf(params)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            out_path = tmp.name
        generer_plans_structure(out_path, resultats=rs, params=params.dict(),
                                dwg_geometry=dwg_geometry,
                                archi_pdf_path=archi_pdf_path)
        with open(out_path, "rb") as f:
            pdf_bytes = f.read()
        # Server-side persistence (best-effort, non-blocking)
        _archive_url = _supabase_archive_plan(
            getattr(params, 'project_id', None) or params.dict().get('project_id'),
            "plans_structure", pdf_bytes
        )
        return pdf_response(pdf_bytes, fname(params, "plans_structure"), archive_url=_archive_url)
    except HTTPException:
        raise  # Preserve 422 (DWG-only guard) and other explicit status codes
    except Exception as e:
        logger.error(f"/generate-plans-structure error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if out_path:
            try:
                os.unlink(out_path)
            except OSError:
                pass
        # Don't delete cached archi PDFs — they're managed by TTL in _save_archi_pdf
        if archi_pdf_path and _ARCHI_PDF_CACHE_DIR not in archi_pdf_path:
            try:
                os.unlink(archi_pdf_path)
            except OSError:
                pass
        gc.collect()


@app.post("/generate-plans-mep")
async def generate_plans_mep(params: ParamsProjet):
    """Plans MEP PDF — nécessite une géométrie DWG/DXF réelle (input PDF refusé)."""
    out_path = None
    archi_pdf_path = None
    try:
        _, _, calculer_structure = get_moteur_structure()
        calculer_mep = get_moteur_mep()
        from generate_plans_structure_mep import generer_plans_mep
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        rm = calculer_mep(donnees, rs)
        # Geometry priority: body > cache ref > APS URN > None (grid fallback)
        dwg_geometry = _resolve_geometry(params)
        # DWG-only policy: refuse only when explicitly PDF-sourced or when
        # request carries PDF markers without any DWG signal.
        if _is_pdf_sourced_geometry(dwg_geometry) or _params_signal_pdf_input(params):
            raise HTTPException(
                status_code=422,
                detail="Les plans MEP nécessitent un fichier DWG/DXF en entrée. "
                       "L'import PDF est désactivé pour les plans (calculs et autres livrables restent disponibles)."
            )
        logger.info(f"/generate-plans-mep: geometry={'yes' if dwg_geometry else 'no'}")
        # Resolve archi PDF for background (from cache ref or URL)
        archi_pdf_path = _resolve_archi_pdf(params)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            out_path = tmp.name
        generer_plans_mep(out_path, resultats_mep=rm, resultats_structure=rs,
                          params=params.dict(), dwg_geometry=dwg_geometry,
                          archi_pdf_path=archi_pdf_path)
        with open(out_path, "rb") as f:
            pdf_bytes = f.read()
        _archive_url = _supabase_archive_plan(
            getattr(params, 'project_id', None) or params.dict().get('project_id'),
            "plans_mep", pdf_bytes
        )
        return pdf_response(pdf_bytes, fname(params, "plans_mep"), archive_url=_archive_url)
    except HTTPException:
        raise  # Preserve 422 (DWG-only guard) and other explicit status codes
    except Exception as e:
        logger.error(f"/generate-plans-mep error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if out_path:
            try:
                os.unlink(out_path)
            except OSError:
                pass
        # Don't delete cached archi PDFs — they're managed by TTL in _save_archi_pdf
        if archi_pdf_path and _ARCHI_PDF_CACHE_DIR not in archi_pdf_path:
            try:
                os.unlink(archi_pdf_path)
            except OSError:
                pass
        gc.collect()


@app.post("/generate-plans-structure-dwg")
async def generate_plans_structure_dwg(params: ParamsProjet):
    """Plans structure as DXF file — architecture + poteaux/poutres/dalles on layers."""
    out_path = None
    try:
        _, _, calculer_structure = get_moteur_structure()
        from generate_plans_structure_mep import generer_plans_structure_dxf
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        dwg_geometry = _resolve_geometry(params)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
            out_path = tmp.name
        generer_plans_structure_dxf(out_path, resultats=rs, params=params.dict(),
                                    dwg_geometry=dwg_geometry)
        with open(out_path, "rb") as f:
            dxf_bytes = f.read()
        _supabase_archive_plan(getattr(params, 'project_id', None) or params.dict().get('project_id'),
                               "plans_structure_dxf", dxf_bytes, content_type="application/dxf")
        dxf_name = f"tijan_plans_structure_{params.nom.replace(' ','_')[:20]}.dxf"
        return StreamingResponse(
            io.BytesIO(dxf_bytes),
            media_type="application/dxf",
            headers={"Content-Disposition": f"attachment; filename={dxf_name}"},
        )
    except Exception as e:
        logger.error(f"/generate-plans-structure-dwg error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if out_path:
            try:
                os.unlink(out_path)
            except OSError:
                pass
        gc.collect()


@app.post("/generate-plans-mep-dwg")
async def generate_plans_mep_dwg(params: ParamsProjet):
    """Plans MEP as DXF file — architecture + MEP equipment on layers per lot."""
    out_path = None
    try:
        _, _, calculer_structure = get_moteur_structure()
        calculer_mep = get_moteur_mep()
        from generate_plans_structure_mep import generer_plans_mep_dxf
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        rm = calculer_mep(donnees, rs)
        dwg_geometry = _resolve_geometry(params)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
            out_path = tmp.name
        generer_plans_mep_dxf(out_path, resultats_mep=rm, resultats_structure=rs,
                              params=params.dict(), dwg_geometry=dwg_geometry)
        with open(out_path, "rb") as f:
            dxf_bytes = f.read()
        _supabase_archive_plan(getattr(params, 'project_id', None) or params.dict().get('project_id'),
                               "plans_mep_dxf", dxf_bytes, content_type="application/dxf")
        dxf_name = f"tijan_plans_mep_{params.nom.replace(' ','_')[:20]}.dxf"
        return StreamingResponse(
            io.BytesIO(dxf_bytes),
            media_type="application/dxf",
            headers={"Content-Disposition": f"attachment; filename={dxf_name}"},
        )
    except Exception as e:
        logger.error(f"/generate-plans-mep-dwg error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if out_path:
            try:
                os.unlink(out_path)
            except OSError:
                pass
        gc.collect()


def _supabase_archive_plan(project_id: str, kind: str, data: bytes, content_type: str = "application/pdf") -> Optional[str]:
    """Best-effort server-side upload of a generated plan to Supabase Storage.
    Uses SUPABASE_URL + SUPABASE_SERVICE_ROLE env vars (never exposed to client).
    Also merges the public URL into projets.plans_urls jsonb column.
    Never raises — silent failure if env missing or Supabase unreachable.
    Returns the public URL or None.
    """
    if not project_id or not kind or not data:
        return None
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key  = os.environ.get("SUPABASE_SERVICE_ROLE") or os.environ.get("SUPABASE_SERVICE_KEY")
    if not base or not key:
        return None
    ext = "dxf" if kind.endswith("_dxf") else "pdf"
    path = f"{project_id}/{kind}.{ext}"
    try:
        with httpx.Client(timeout=15) as client:
            # Upload (upsert)
            r = client.post(
                f"{base}/storage/v1/object/plans/{path}",
                content=data,
                headers={
                    "Authorization": f"Bearer {key}",
                    "apikey": key,
                    "Content-Type": content_type,
                    "x-upsert": "true",
                    "cache-control": "3600",
                },
            )
            if r.status_code not in (200, 201):
                logger.warning(f"[plan-archive] upload failed {r.status_code}: {r.text[:120]}")
                return None
            public_url = f"{base}/storage/v1/object/public/plans/{path}"
            # Merge into projets.plans_urls
            try:
                # Read current row
                g = client.get(
                    f"{base}/rest/v1/projets?id=eq.{project_id}&select=plans_urls",
                    headers={"Authorization": f"Bearer {key}", "apikey": key},
                )
                current = {}
                if g.status_code == 200 and g.json():
                    current = g.json()[0].get("plans_urls") or {}
                current[kind] = {"url": public_url, "updated_at": datetime.now(timezone.utc).isoformat()}
                client.patch(
                    f"{base}/rest/v1/projets?id=eq.{project_id}",
                    json={"plans_urls": current},
                    headers={
                        "Authorization": f"Bearer {key}", "apikey": key,
                        "Content-Type": "application/json",
                        "Prefer": "return=minimal",
                    },
                )
            except Exception as e:
                logger.warning(f"[plan-archive] metadata patch failed: {e}")
            return public_url
    except Exception as e:
        logger.warning(f"[plan-archive] error: {e}")
        return None


def _download_archi_pdf(url: str) -> str:
    """Download architectural PDF from URL to temp file. Returns path or None."""
    if not url:
        return None
    try:
        with httpx.Client(timeout=20) as client:
            resp = client.get(url)
            resp.raise_for_status()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(resp.content)
                return tmp.name
    except Exception as e:
        logger.warning(f"Failed to download archi PDF from {url[:80]}: {e}")
        return None


# ── Geometry + Archi PDF cache — persists between /parse and /generate-plans-* ──
_ARCHI_PDF_CACHE_DIR = os.path.join(tempfile.gettempdir(), "tijan_archi_cache")
os.makedirs(_ARCHI_PDF_CACHE_DIR, exist_ok=True)

_GEOM_CACHE_DIR = os.path.join(tempfile.gettempdir(), "tijan_geom_cache")
os.makedirs(_GEOM_CACHE_DIR, exist_ok=True)


def _save_geometry(geom: dict) -> str:
    """Save extracted geometry to cache. Returns a unique reference key."""
    import hashlib, time, json
    geom_json = json.dumps(geom, default=str, ensure_ascii=False)
    content_hash = hashlib.md5(geom_json[:4096].encode()).hexdigest()[:12]
    ref_key = f"{int(time.time())}_{content_hash}"
    cached_path = os.path.join(_GEOM_CACHE_DIR, f"{ref_key}.json")
    with open(cached_path, "w") as f:
        f.write(geom_json)
    # Cleanup old cached geometry (older than 2 hours)
    try:
        now = time.time()
        for fn in os.listdir(_GEOM_CACHE_DIR):
            fp = os.path.join(_GEOM_CACHE_DIR, fn)
            if now - os.path.getmtime(fp) > 7200:
                os.unlink(fp)
    except OSError:
        pass
    logger.info(f"Cached geometry: {ref_key} ({len(geom.get('walls', []))} walls)")
    return ref_key


def _resolve_geometry(params) -> dict:
    """Resolve geometry: body dict > cache ref > APS URN > None."""
    import json
    # Priority 1: geometry in request body
    geom = getattr(params, 'dwg_geometry', None)
    if isinstance(params, dict):
        geom = params.get('dwg_geometry')
    if geom and isinstance(geom, dict):
        # Check it has actual content
        has_walls = 'walls' in geom and len(geom.get('walls', [])) >= 3
        has_levels = any(isinstance(v, dict) and len(v.get('walls', [])) >= 3 for v in geom.values() if isinstance(v, dict))
        if has_walls or has_levels:
            return geom

    # Priority 2: cached geometry ref
    ref = getattr(params, 'geom_ref', None) or (params.get('geom_ref') if isinstance(params, dict) else None)
    if ref:
        cached_path = os.path.join(_GEOM_CACHE_DIR, f"{ref}.json")
        if os.path.isfile(cached_path):
            try:
                with open(cached_path) as f:
                    cached_geom = json.load(f)
                logger.info(f"Loaded cached geometry: {ref}")
                return cached_geom
            except Exception as e:
                logger.warning(f"Failed to load cached geometry {ref}: {e}")
        else:
            logger.warning(f"Cached geometry not found: {ref}")

    # Priority 3: APS URN re-extraction
    urn = getattr(params, 'urn', None) or (params.get('urn') if isinstance(params, dict) else None)
    if urn:
        urn_geom = _load_project_geometry(urn)
        if urn_geom:
            return urn_geom

    # Priority 4: re-extract from persisted archi PDF (makes projects opened
    # from /dashboard work even when dwg_geometry wasn't persisted to Supabase
    # or was cleared, as long as the archi PDF was uploaded to storage).
    url = getattr(params, 'archi_pdf_url', None) or (params.get('archi_pdf_url') if isinstance(params, dict) else None)
    ref = getattr(params, 'archi_pdf_ref', None) or (params.get('archi_pdf_ref') if isinstance(params, dict) else None)
    if url or ref:
        pdf_path = _resolve_archi_pdf(params)
        if pdf_path and os.path.isfile(pdf_path):
            try:
                from cv_geometry_extractor import extract_geometry_per_page_cv
                pages_geom = extract_geometry_per_page_cv(pdf_path, use_vision=True) or {}
                if pages_geom:
                    # Keep only the pages that actually carried geometry
                    clean = {k: v for k, v in pages_geom.items()
                             if isinstance(v, dict) and len(v.get('walls', [])) >= 3}
                    if clean:
                        total = sum(len(v.get('walls', [])) for v in clean.values())
                        logger.info(f"[persistence] re-extracted geometry from archi PDF: "
                                    f"{len(clean)} levels, {total} walls")
                        return clean
            except Exception as e:
                logger.warning(f"[persistence] archi PDF re-extraction failed: {e}")

    return None


def _save_archi_pdf(file_path: str) -> str:
    """Save an uploaded PDF to the cache dir. Returns a unique reference key."""
    import hashlib, shutil, time
    with open(file_path, "rb") as f:
        content_hash = hashlib.md5(f.read(8192)).hexdigest()[:12]
    ref_key = f"{int(time.time())}_{content_hash}"
    cached_path = os.path.join(_ARCHI_PDF_CACHE_DIR, f"{ref_key}.pdf")
    shutil.copy2(file_path, cached_path)
    # Cleanup old cached PDFs (older than 30 min)
    try:
        now = time.time()
        for fn in os.listdir(_ARCHI_PDF_CACHE_DIR):
            fp = os.path.join(_ARCHI_PDF_CACHE_DIR, fn)
            if now - os.path.getmtime(fp) > 1800:
                os.unlink(fp)
    except OSError:
        pass
    logger.info(f"Cached archi PDF: {ref_key}")
    return ref_key


def _resolve_archi_pdf(params) -> str:
    """Resolve archi PDF path from params. Checks cache ref first, then URL.
    Returns temp file path or None."""
    # Priority 1: cached ref from /parse
    ref = getattr(params, 'archi_pdf_ref', None) or (params.get('archi_pdf_ref') if isinstance(params, dict) else None)
    if ref:
        cached_path = os.path.join(_ARCHI_PDF_CACHE_DIR, f"{ref}.pdf")
        if os.path.isfile(cached_path):
            logger.info(f"Using cached archi PDF: {ref}")
            return cached_path
        else:
            logger.warning(f"Cached archi PDF not found: {ref}")
    # Priority 2: download from URL
    url = getattr(params, 'archi_pdf_url', None) or (params.get('archi_pdf_url') if isinstance(params, dict) else None)
    if url:
        return _download_archi_pdf(url)
    return None


def _load_project_geometry(urn: str) -> dict:
    """
    Load real DWG geometry for THIS specific project from APS.
    Returns dict with walls, axes, rooms, dimensions — or None on failure.
    Each project has its own URN, its own geometry, its own calculations.
    """
    if not urn:
        return None
    try:
        from aps_parser_v2 import get_token, get_viewable_guids, get_properties, extract_layer_objects
        token = get_token()

        # Get 2D viewable
        viewables = get_viewable_guids(urn, token)
        guid = None
        for v in viewables:
            if v.get("role") == "2d":
                guid = v["guid"]; break
        if not guid and viewables:
            guid = viewables[0]["guid"]
        if not guid:
            logger.warning("No viewable found for URN %s", urn[:20])
            return None

        token = get_token()
        properties = get_properties(urn, guid, token)
        if not properties:
            logger.warning("No properties for URN %s", urn[:20])
            return None

        # Extract geometry per architectural layer
        wall_layers = ['MUR', 'MURS', 'A-MUR', 'WALL', 'WALLS', '0_MURS', 'A-WALL', 'I-WALL']
        window_layers = ['A-ALUMINIUM', 'ALUMINIUM', 'A-GLAZ', 'A-VERRE', 'A-GLAZ']
        door_layers = ['DOOR', 'S_Doors', 'BOIS', 'PORTE', 'A-DOOR']
        sanitary_layers = ['SANITAIRE', 'A-SANITAIRES', 'AM FITTING-SANITARY']

        geometry = {'walls': [], 'windows': [], 'doors': [], 'sanitary': [], 'rooms': []}

        for layer_name in wall_layers:
            objs = extract_layer_objects(properties, layer_name)
            for obj in objs:
                if 'x' in obj and 'y' in obj:
                    if 'x2' in obj and 'y2' in obj:
                        geometry['walls'].append({
                            'type': 'line',
                            'start': [obj['x'], obj['y']],
                            'end': [obj['x2'], obj['y2']]
                        })
                    else:
                        geometry['walls'].append({
                            'type': 'point', 'x': obj['x'], 'y': obj['y']
                        })

        for layer_name in window_layers:
            objs = extract_layer_objects(properties, layer_name)
            for obj in objs:
                if 'x' in obj and 'y' in obj and 'x2' in obj and 'y2' in obj:
                    geometry['windows'].append({
                        'type': 'line',
                        'start': [obj['x'], obj['y']],
                        'end': [obj['x2'], obj['y2']]
                    })

        for layer_name in door_layers:
            objs = extract_layer_objects(properties, layer_name)
            for obj in objs:
                if 'x' in obj and 'y' in obj:
                    geometry['doors'].append({
                        'type': 'line',
                        'start': [obj['x'], obj['y']],
                        'end': [obj.get('x2', obj['x']+500), obj.get('y2', obj['y'])]
                    })

        # Room labels
        for layer_name in ['Etiquettes de pièces', 'TEXTES', 'TEXT_3']:
            objs = extract_layer_objects(properties, layer_name)
            for obj in objs:
                if 'x' in obj and 'y' in obj and obj.get('text'):
                    geometry['rooms'].append({
                        'name': obj['text'], 'x': obj['x'], 'y': obj['y']
                    })

        wall_count = len(geometry['walls'])
        logger.info("Loaded %d walls, %d windows, %d rooms from APS URN %s",
                     wall_count, len(geometry['windows']), len(geometry['rooms']), urn[:20])

        return geometry if wall_count > 5 else None

    except Exception as e:
        logger.warning("Failed to load geometry from APS: %s", e)
        return None


@app.get("/parse/layer")
async def parse_layer(urn: str, layer: str = "SANITAIRE", guid: str = None):
    """Extrait les objets d un layer DWG depuis APS (coordonnees XY reelles)."""
    try:
        from aps_parser_v2 import get_token, get_viewable_guids, get_properties, extract_layer_objects
        token = get_token()
        if not guid:
            guids = get_viewable_guids(urn, token)
            if not guids:
                raise HTTPException(status_code=400, detail="No viewables found for this project")
            guid = next((g["guid"] for g in guids if g.get("role") == "2d"), guids[0]["guid"])
        properties = get_properties(urn, guid, token)
        objects = extract_layer_objects(properties, layer)
        return {"ok": True, "layer": layer, "count": len(objects), "objects": objects[:200]}
    except Exception as e:
        logger.error(f"/parse/layer error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/parse/manifest")
async def parse_manifest(urn: str):
    """Retourne le manifest SVF2 complet pour inspecter les fichiers geometry."""
    try:
        from aps_parser_v2 import get_token
        import urllib.request
        token = get_token()
        url = f"https://developer.api.autodesk.com/modelderivative/v2/designdata/{urn}/manifest"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req) as resp:
            data = _json.loads(resp.read())
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat_projet(request: Request):
    """Chat LLM avec contexte projet — fine-tuning outputs.
    When Claude returns <MODIF>{...}</MODIF>, auto-recalculate and return updated results."""
    try:
        from chat_engine import chat
        import re as _re
        body = await request.json()
        message = body.get("message", "")
        historique = body.get("historique", [])
        chat_params = body.get("params", {})
        resultats_structure = body.get("resultats_structure", {})
        resultats_mep = body.get("resultats_mep", None)
        lang = body.get("lang", "fr")  # Langue par défaut FR
        if not message:
            raise HTTPException(status_code=400, detail="Message manquant" if lang == "fr" else "Missing message")
        reponse = chat(message, historique, chat_params, resultats_structure, resultats_mep, lang=lang)

        # Detect <MODIF>{...}</MODIF> in Claude's response
        modif_match = _re.search(r'<MODIF>(.*?)</MODIF>', reponse, _re.DOTALL)
        if modif_match:
            try:
                modif = _json.loads(modif_match.group(1))
                # Merge modifications into current params
                updated_params = {**chat_params, **modif}
                # Strip MODIF tag from displayed response
                clean_reponse = _re.sub(r'<MODIF>.*?</MODIF>\s*', '', reponse, flags=_re.DOTALL).strip()

                # Recalculate with updated params
                _, _, calculer_structure = get_moteur_structure()
                calculer_mep_fn = get_moteur_mep()
                pp = ParamsProjet(**{k: v for k, v in updated_params.items() if k in ParamsProjet.model_fields})
                donnees = params_to_donnees(pp)
                rs = calculer_structure(donnees)
                rm = calculer_mep_fn(donnees, rs)

                # Serialize results
                import dataclasses
                def _ser(obj):
                    if dataclasses.is_dataclass(obj):
                        return dataclasses.asdict(obj)
                    if hasattr(obj, '__dict__'):
                        return {k: _ser(v) for k, v in obj.__dict__.items() if not k.startswith('_')}
                    if isinstance(obj, list):
                        return [_ser(i) for i in obj]
                    if isinstance(obj, dict):
                        return {k: _ser(v) for k, v in obj.items()}
                    return obj

                rs_dict = _ser(rs)
                rs_dict['ok'] = True
                rm_dict = _serialize_mep(rm, updated_params.get('ville'))

                gc.collect()
                return {
                    "ok": True,
                    "reponse": clean_reponse,
                    "recalcul": True,
                    "modif": modif,
                    "updated_params": updated_params,
                    "updated_resultats": rs_dict,
                    "updated_mep": rm_dict,
                }
            except Exception as e:
                logger.warning(f"/chat MODIF recalcul failed: {e}")
                # Fall through to normal response with MODIF tags stripped
                reponse = _re.sub(r'<MODIF>.*?</MODIF>\s*', '', reponse, flags=_re.DOTALL).strip()

        gc.collect()
        return {"ok": True, "reponse": reponse}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"/chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/calculate-mep-edge")
async def calculate_mep_edge_optimise(params: ParamsProjet):
    """Recalcul MEP avec toutes les mesures EDGE activées."""
    try:
        _, _, calculer_structure = get_moteur_structure()
        calculer_mep = get_moteur_mep()
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        rm = calculer_mep(donnees, rs, edge_optimise=True)
        gc.collect()

        e = rm.edge
        boqm = rm.boq

        # Calculer surcoût EDGE
        surf_batie = rm.surf_batie_m2
        cout_led   = int(surf_batie * 3500)
        cout_iso   = int(donnees.surface_emprise_m2 * 8500)
        cout_wc    = rm.plomberie.nb_wc_double_chasse * 45000
        cout_rob   = rm.plomberie.nb_robinets_eco * 30000
        surcout_total = cout_led + cout_iso + cout_wc + cout_rob

        return {
            "ok": True,
            "edge_optimise": True,
            "projet": params.nom,
            "surf_batie_m2": surf_batie,
            "edge": {
                "economie_energie_pct": e.economie_energie_pct,
                "economie_eau_pct": e.economie_eau_pct,
                "economie_materiaux_pct": e.economie_materiaux_pct,
                "certifiable": e.certifiable,
                "niveau_certification": e.niveau_certification,
                "mesures_energie": e.mesures_energie,
                "mesures_eau": e.mesures_eau,
                "mesures_materiaux": e.mesures_materiaux,
                "note_generale": e.note_generale,
            },
            "surcout_edge": {
                "led_fcfa": cout_led,
                "isolation_fcfa": cout_iso,
                "wc_fcfa": cout_wc,
                "robinetterie_fcfa": cout_rob,
                "total_fcfa": surcout_total,
                "pct_boq_mep": round(surcout_total / max(boqm.total_basic_fcfa, 1) * 100, 1),
            },
            "boq_mep": {
                "basic_fcfa": boqm.total_basic_fcfa,
                "hend_fcfa": boqm.total_hend_fcfa,
                "luxury_fcfa": boqm.total_luxury_fcfa,
            },
        }
    except Exception as e:
        logger.error(f"/calculate-mep-edge error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ════════════════════════════════════════════════════════════
# ENTRÉE
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)




# ── ENGINEER REVIEW ───────────────────────────────────────

class ReviewRequest(BaseModel):
    """Validation model for engineer review requests."""
    project_id: str
    user_id: str
    scopes: List[str]  # List of review scopes: structure, mep, edge


@app.post("/request-review")
async def request_review(req: ReviewRequest):
    """
    Request an engineer review for a project.

    Stores review metadata (project_id, user_id, scopes, status, cost_credits, created_at, reviewer_notes).
    Cost is fixed at 2 credits per review (regardless of scope count).
    """
    # Input validation
    if not req.project_id or not req.user_id:
        raise HTTPException(status_code=400, detail="project_id and user_id required")

    if not req.scopes or len(req.scopes) == 0:
        raise HTTPException(status_code=400, detail="scopes list cannot be empty")

    # Validate scopes
    valid_scopes = {"structure", "mep", "edge"}
    for scope in req.scopes:
        if scope not in valid_scopes:
            raise HTTPException(status_code=400, detail=f"Invalid scope: {scope}. Must be one of {valid_scopes}")

    # Fixed cost: 2 credits always
    cost_credits = 2

    # We don't need Supabase integration for this endpoint
    # The frontend will handle the Supabase insert after credit deduction
    # This endpoint returns the review metadata that will be stored

    from datetime import datetime
    review_id = f"rev_{int(datetime.utcnow().timestamp() * 1000)}"

    return {
        "ok": True,
        "review_id": review_id,
        "project_id": req.project_id,
        "user_id": req.user_id,
        "scopes": req.scopes,
        "status": "pending",
        "cost_credits": cost_credits,
        "created_at": datetime.utcnow().isoformat(),
        "reviewer_notes": "",
    }


@app.get("/reviews")
async def get_user_reviews(user_id: str):
    """
    Get all reviews for a specific user.

    Query param: user_id (required)
    Returns list of reviews with their current status.
    """
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id query parameter required")

    # Note: This endpoint signature is for frontend compatibility.
    # Actual Supabase querying will be handled by the frontend via useAuth hook.
    # This endpoint can be extended later to do server-side filtering if needed.

    return {
        "ok": True,
        "user_id": user_id,
        "message": "Frontend should query Supabase directly via useAuth().supabase.from('engineer_reviews').select(...)",
    }


@app.get("/review/{review_id}/status")
async def get_review_status(review_id: str):
    """
    Get the status of a specific review.

    Returns current status: pending, in_review, or delivered.
    Also includes any reviewer notes if status is delivered.
    """
    if not review_id:
        raise HTTPException(status_code=400, detail="review_id required")

    # Note: This endpoint signature is for frontend compatibility.
    # Actual status queries will be handled by the frontend via Supabase RLS.
    # This endpoint can be extended later to do server-side lookups if needed.

    return {
        "ok": True,
        "review_id": review_id,
        "message": "Frontend should query Supabase directly via useAuth().supabase.from('engineer_reviews').select(...).eq('id', review_id)",
    }


@app.get("/review/{project_id}/info")
async def get_review_info(project_id: str):
    """Get engineer review availability and pricing info for a project."""
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id required")

    return {
        "ok": True,
        "project_id": project_id,
        "available": True,
        "cost_credits": 2,
        "turnaround_hours": "48-72",
        "scope_options": ["structure", "mep", "edge"],
        "description": {
            "en": "Engineer review includes annotated PDF with comments, signed validation letter with professional stamp, and delivery within 48-72 hours",
            "fr": "Revue ingénieur inclut PDF annoté avec commentaires, lettre de validation signée avec tampon professionnel, et livraison sous 48-72 heures",
        },
    }


# ── PAYDUNYA ──────────────────────────────────────────────
PAYDUNYA_URL = "https://app.paydunya.com/api/v1/checkout-invoice/create"
PAYDUNYA_HEADERS = {
    "Content-Type": "application/json",
    "PAYDUNYA-MASTER-KEY": os.environ.get("PAYDUNYA_MASTER_KEY", ""),
    "PAYDUNYA-PRIVATE-KEY": os.environ.get("PAYDUNYA_PRIVATE_KEY", ""),
    "PAYDUNYA-TOKEN": os.environ.get("PAYDUNYA_TOKEN", ""),
}

# Check for PayDunya configuration at startup
if not PAYDUNYA_HEADERS.get("PAYDUNYA-MASTER-KEY"):
    logger.warning("PayDunya PAYDUNYA_MASTER_KEY not set")
if not PAYDUNYA_HEADERS.get("PAYDUNYA-PRIVATE-KEY"):
    logger.warning("PayDunya PAYDUNYA_PRIVATE_KEY not set")
if not PAYDUNYA_HEADERS.get("PAYDUNYA-TOKEN"):
    logger.warning("PayDunya PAYDUNYA_TOKEN not set")

@app.post("/create-payment")
async def create_payment(request: Request):
    body = await request.json()
    credits = body.get("credits", 1)
    prix = body.get("prix", 200000)
    user_id = body.get("user_id", "")

    payload = {
        "invoice": {
            "total_amount": prix,
            "description": f"Tijan AI — {credits} crédit{'s' if credits > 1 else ''} technique{'s' if credits > 1 else ''}",
        },
        "store": {
            "name": "Tijan AI",
            "tagline": "Engineering Intelligence for Africa",
            "website_url": "https://tijan-frontend.vercel.app",
        },
        "custom_data": {
            "user_id": user_id,
            "nb_credits": credits,
        },
        "actions": {
            "return_url": f"https://tijan-frontend.vercel.app/payment-success?credits={credits}",
            "cancel_url": "https://tijan-frontend.vercel.app/pricing",
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(PAYDUNYA_URL, json=payload, headers=PAYDUNYA_HEADERS)
        data = resp.json()

    if data.get("response_code") == "00":
        return {"ok": True, "url": data.get("response_text"), "token": data.get("token")}
    else:
        return {"ok": False, "error": data.get("response_text", "Erreur PayDunya")}


# ── TRADUCTION VIA CLAUDE API ─────────────────────────────
@app.post("/translate")
async def translate_text(request: Request):
    body = await request.json()
    texts = body.get("texts", [])
    target_lang = body.get("lang", "en")

    if not isinstance(texts, list) or len(texts) > 500:
        raise HTTPException(status_code=400, detail="texts must be a list with max 500 items")

    if not texts:
        return {"ok": True, "translations": []}
    
    prompt = f"""Translate the following technical construction/engineering texts from French to English.
Return ONLY a JSON array of translated strings, in the same order. No explanation, no markdown.
Keep technical terms accurate (EC2, EC8, FCFA, kVA, m², m³, kW, etc.).
Keep numbers and units unchanged.

Texts to translate:
{_json.dumps(texts, ensure_ascii=False)}"""

    try:
        import anthropic
        client = anthropic.Anthropic()
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message.content[0].text.strip()
        # Parse JSON array with bounds check
        if response_text.startswith("["):
            translations = _json.loads(response_text)
        else:
            # Try to extract JSON from response
            start = response_text.find("[")
            end = response_text.rfind("]")
            if start >= 0 and end > start:
                translations = _json.loads(response_text[start:end+1])
            else:
                raise ValueError("No JSON array found in translation response")
        return {"ok": True, "translations": translations}
    except Exception as e:
        return {"ok": False, "error": str(e), "translations": texts}

@app.get("/parse/download-f2d")
async def download_f2d(urn: str, f2d_path: str):
    """Telecharge un fichier F2D depuis APS et retourne sa taille et premiers bytes."""
    try:
        from aps_parser_v2 import get_token
        import urllib.request as ur
        import base64
        import urllib.parse
        token = get_token()
        # URL APS pour telecharger un fichier derivatif
        encoded_urn = urn
        safe_urn = urllib.parse.quote(urn, safe='')
        safe_path = urllib.parse.quote(f2d_path, safe='')
        url = f"https://developer.api.autodesk.com/modelderivative/v2/designdata/{safe_urn}/manifest/{safe_path}"
        req = ur.Request(url, headers={"Authorization": f"Bearer {token}"})
        with ur.urlopen(req) as resp:
            data = resp.read()
        return {
            "size": len(data),
            "first_bytes_hex": data[:64].hex(),
            "first_bytes_b64": base64.b64encode(data[:256]).decode()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# manifest fix Sun Mar 29 01:38:44 GMT 2026


# ════════════════════════════════════════════════════════════
# PROMO CODES & SUBSCRIPTIONS
# ════════════════════════════════════════════════════════════

@app.post("/admin/promo-codes")
async def create_promo_code(request: Request):
    """Create a promo code for a prospect. Admin only."""
    body = await request.json()

    prospect_name = body.get("prospect_name", "").strip()
    prospect_email = body.get("prospect_email", "").strip()
    prospect_company = body.get("prospect_company", "").strip() or None
    discount_percent = int(body.get("discount_percent", 0))
    duration_months = int(body.get("duration_months", 3))
    expires_at = body.get("expires_at")  # ISO string
    notes = body.get("notes", "").strip() or None

    if not prospect_name or not prospect_email:
        return JSONResponse({"ok": False, "error": "prospect_name et prospect_email requis"}, 400)
    if discount_percent < 1 or discount_percent > 99:
        return JSONResponse({"ok": False, "error": "discount_percent doit \u00eatre entre 1 et 99"}, 400)
    if duration_months not in ALLOWED_DURATIONS_MONTHS:
        return JSONResponse({"ok": False, "error": f"duration_months doit \u00eatre {ALLOWED_DURATIONS_MONTHS}"}, 400)

    import random
    import string as _string_mod
    name_part = ''.join(c for c in prospect_name.upper() if c.isalpha())[:3].ljust(3, 'X')
    rand_part = ''.join(random.choices(_string_mod.ascii_uppercase + _string_mod.digits, k=4))
    code = f"TIJAN-{name_part}-{rand_part}"

    data = {
        "code": code,
        "prospect_name": prospect_name,
        "prospect_email": prospect_email,
        "prospect_company": prospect_company,
        "discount_percent": discount_percent,
        "duration_months": duration_months,
        "expires_at": expires_at,
        "notes": notes,
    }

    result = supabase.table("promo_codes").insert(data).execute()

    share_url = f"https://tijan.ai/pricing?promo={code}"

    return {"ok": True, "code": code, "share_url": share_url, "data": result.data[0] if result.data else data}


@app.get("/admin/promo-codes")
async def list_promo_codes(request: Request):
    """List all promo codes with computed status. Admin only."""
    result = supabase.table("promo_codes_with_status").select("*").order("created_at", desc=True).execute()
    return {"ok": True, "codes": result.data or []}


@app.post("/promo-codes/validate")
async def validate_promo_code(request: Request):
    """Validate a promo code. Public endpoint."""
    body = await request.json()
    code = body.get("code", "").strip().upper()

    if not code:
        return {"valid": False, "reason": "Code requis"}

    result = supabase.table("promo_codes_with_status").select("*").eq("code", code).maybeSingle().execute()

    if not result.data:
        return {"valid": False, "reason": "Code invalide"}

    pc = result.data

    if pc.get("statut") == "expired":
        return {"valid": False, "reason": "Ce code a expir\u00e9"}
    if pc.get("statut") == "used":
        return {"valid": False, "reason": "Ce code a d\u00e9j\u00e0 \u00e9t\u00e9 utilis\u00e9"}

    discount = pc["discount_percent"]
    discounted_price = int(DEFAULT_PRICE_FCFA * (100 - discount) / 100)

    return {
        "valid": True,
        "discount_percent": discount,
        "monthly_price": discounted_price,
        "original_price": DEFAULT_PRICE_FCFA,
        "duration_months": pc["duration_months"],
        "expires_at": pc["expires_at"],
        "prospect_name": pc["prospect_name"],
    }


@app.post("/subscriptions/create")
async def create_subscription(request: Request):
    """Create a subscription, optionally with a promo code. Auth required."""
    body = await request.json()
    user_id = body.get("user_id")
    promo_code = body.get("promo_code", "").strip().upper() or None

    if not user_id:
        return JSONResponse({"ok": False, "error": "user_id requis"}, 400)

    price = DEFAULT_PRICE_FCFA
    discount_percent = 0
    duration_months = 0
    promo_code_id = None

    if promo_code:
        pc_result = supabase.table("promo_codes_with_status").select("*").eq("code", promo_code).maybeSingle().execute()
        if not pc_result.data:
            return JSONResponse({"ok": False, "error": "Code promo invalide"}, 400)
        pc = pc_result.data
        if pc.get("statut") != "active":
            return JSONResponse({"ok": False, "error": f"Code promo {pc.get('statut', 'invalide')}"}, 400)

        discount_percent = pc["discount_percent"]
        duration_months = pc["duration_months"]
        price = int(DEFAULT_PRICE_FCFA * (100 - discount_percent) / 100)
        promo_code_id = pc["id"]

        supabase.table("promo_codes").update({
            "used_at": datetime.utcnow().isoformat(),
            "used_by_user_id": user_id,
        }).eq("id", promo_code_id).execute()

    from datetime import timedelta
    now = datetime.utcnow()
    period_end = now + timedelta(days=30)
    discount_end = (now + timedelta(days=30 * duration_months)) if duration_months > 0 else None

    sub_data = {
        "user_id": user_id,
        "plan": "cabinet_mensuel",
        "status": "active",
        "base_price_fcfa": DEFAULT_PRICE_FCFA,
        "current_price_fcfa": price,
        "promo_code_id": promo_code_id,
        "discount_percent": discount_percent,
        "discount_start_at": now.isoformat() if discount_percent > 0 else None,
        "discount_end_at": discount_end.isoformat() if discount_end else None,
        "credits_per_month": 3,
        "current_period_start": now.isoformat(),
        "current_period_end": period_end.isoformat(),
    }

    sub_result = supabase.table("subscriptions").insert(sub_data).execute()

    # Send welcome email (non-blocking)
    user_email = body.get("user_email", "")
    user_name = body.get("user_name", "").strip() or "Client"
    revert_date_str = discount_end.strftime("%d/%m/%Y") if discount_end else ""
    if user_email:
        _send_welcome_email(
            to_email=user_email,
            name=user_name,
            price=price,
            discount_percent=discount_percent,
            duration_months=duration_months,
            revert_date=revert_date_str,
        )

    return {
        "ok": True,
        "subscription": sub_result.data[0] if sub_result.data else sub_data,
        "price": price,
        "original_price": DEFAULT_PRICE_FCFA,
        "discount_percent": discount_percent,
        "discount_months": duration_months,
    }
