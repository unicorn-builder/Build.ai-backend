"""
Tijan AI — main.py v6
Backend FastAPI — Render Standard (1 CPU / 2GB RAM)

Moteurs v2 :
  - engine_structure_v2.py  — Structure EC2/EC8 paramétrique tous usages
  - engine_mep_v2.py        — MEP complet (élec, plomberie, CVC, CF, SI, ASC, AUTO, EDGE)
  - prix_marche.py          — Base de prix multi-pays (Dakar, Abidjan, Casablanca, Lagos, Accra)

Générateurs PDF v2 (données 100% issues des moteurs) :
  - gen_note_structure.py   — Note de calcul structure 9 pages
  - gen_boq_structure.py    — BOQ structure détaillé 7 lots
  - gen_mep.py              — Note MEP, BOQ MEP résumé, EDGE, Rapport exécutif
  - gen_boq_mep_detail.py   — BOQ MEP détaillé 7 lots

Endpoints :
  GET  /health
  POST /parse                     → parse PDF/DWG → paramètres projet
  POST /parse-sol                 → parse étude de sol PDF
  POST /calculate                 → calcul structure EC2/EC8
  POST /calculate-mep             → calcul MEP complet
  POST /generate                  → note de calcul structure PDF
  POST /generate-boq              → BOQ structure détaillé PDF
  POST /generate-note-mep         → note de calcul MEP PDF
  POST /generate-boq-mep          → BOQ MEP détaillé PDF
  POST /generate-edge             → rapport EDGE PDF
  POST /generate-rapport-executif → rapport synthèse maître d'ouvrage PDF
  POST /generate-fiches-structure → fiches techniques structure PDF
  POST /generate-fiches-mep       → fiches techniques MEP PDF
  POST /generate-planches         → planches BA PDF
"""

import gc
import os
import io
import json as _json
import tempfile
import logging
import dataclasses
from datetime import datetime
from typing import Optional

from fastapi import Request, FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from tijan_theme import set_pdf_lang
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tijan")

app = FastAPI(
    title="Tijan AI API",
    description="Bureau d'études automatisé — Structure + MEP + BOQ + EDGE",
    version="6.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ════════════════════════════════════════════════════════════
# IMPORTS LAZY
# ════════════════════════════════════════════════════════════

def get_moteur_structure():
    from engine_structure_v2 import DonneesProjet, Usage, calculer_structure
    return DonneesProjet, Usage, calculer_structure

def get_moteur_mep():
    from engine_mep_v2 import calculer_mep
    return calculer_mep

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

def get_gen_edge():
    from gen_mep import generer_edge
    return generer_edge

def get_gen_executif():
    from gen_mep import generer_rapport_executif
    return generer_rapport_executif

def get_gen_fiches_structure():
    from generate_fiches_structure_v3 import generer_fiches_structure
    return generer_fiches_structure

def get_gen_fiches_mep():
    from generate_fiches_mep_v3 import generer_fiches_mep
    return generer_fiches_mep

def get_gen_planches():
    from generate_plans_v3 import generer_dossier_ba
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
    lang:               str   = 'fr'  # 'fr' | 'en'


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

def pdf_response(pdf_bytes: bytes, filename: str) -> StreamingResponse:
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

async def save_upload(file: UploadFile) -> str:
    suffix = os.path.splitext(file.filename)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        return tmp.name

def fname(params: ParamsProjet, prefix: str) -> str:
    return f"tijan_{prefix}_{params.nom.replace(' ','_')[:20]}.pdf"


# ════════════════════════════════════════════════════════════
# ENDPOINTS
# ════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "6.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "moteurs": {
            "structure": "engine_structure_v2",
            "mep":       "engine_mep_v2",
            "prix":      "prix_marche — Dakar/Abidjan/Casablanca/Lagos/Accra",
        },
    }


@app.post("/parse")
async def parse_fichier(
    file: UploadFile = File(...),
    nb_niveaux: Optional[int] = Form(None),
    ville: Optional[str] = Form(None),
    beton: Optional[str] = Form(None),
):
    from parse_plans import extraire_params
    tmp_path = await save_upload(file)
    try:
        result = extraire_params(tmp_path)
        if result.get("ok"):
            if nb_niveaux: result["nb_niveaux"] = nb_niveaux
            if ville:      result["ville"] = ville
            if beton:      result["classe_beton"] = beton
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"/parse error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try: os.unlink(tmp_path)
        except: pass


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
        except: pass


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
        }
    except Exception as e:
        logger.error(f"/calculate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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

        e = rm.edge
        return {
            "ok": True,
            "projet": params.nom,
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
        }
    except Exception as e:
        logger.error(f"/calculate-mep error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate")
async def generate_note_structure(params: ParamsProjet):
    """Note de calcul structure PDF — 9 pages EC2/EC8."""
    try:
        _, _, calculer_structure = get_moteur_structure()
        generer = get_gen_note_structure()
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        set_pdf_lang(getattr(params, 'lang', 'fr'))
        pdf_bytes = generer(rs, params.dict())
        gc.collect()
        return pdf_response(pdf_bytes, fname(params, "note_structure"))
    except Exception as e:
        logger.error(f"/generate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-boq")
async def generate_boq_structure(params: ParamsProjet):
    """BOQ structure détaillé PDF — 7 lots."""
    try:
        _, _, calculer_structure = get_moteur_structure()
        generer = get_gen_boq_structure()
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        set_pdf_lang(getattr(params, 'lang', 'fr'))
        pdf_bytes = generer(rs, params.dict())
        gc.collect()
        return pdf_response(pdf_bytes, fname(params, "boq_structure"))
    except Exception as e:
        logger.error(f"/generate-boq error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-note-mep")
async def generate_note_mep(params: ParamsProjet):
    """Note de calcul MEP complète PDF."""
    try:
        _, _, calculer_structure = get_moteur_structure()
        calculer_mep = get_moteur_mep()
        generer = get_gen_note_mep()
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        rm = calculer_mep(donnees, rs)
        set_pdf_lang(getattr(params, 'lang', 'fr'))
        pdf_bytes = generer(rm, params.dict())
        gc.collect()
        return pdf_response(pdf_bytes, fname(params, "note_mep"))
    except Exception as e:
        logger.error(f"/generate-note-mep error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-boq-mep")
async def generate_boq_mep(params: ParamsProjet):
    """BOQ MEP détaillé PDF — 7 lots × 3 gammes."""
    try:
        _, _, calculer_structure = get_moteur_structure()
        calculer_mep = get_moteur_mep()
        generer = get_gen_boq_mep()
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        rm = calculer_mep(donnees, rs)
        set_pdf_lang(getattr(params, 'lang', 'fr'))
        pdf_bytes = generer(rm, params.dict())
        gc.collect()
        return pdf_response(pdf_bytes, fname(params, "boq_mep"))
    except Exception as e:
        logger.error(f"/generate-boq-mep error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-edge")
async def generate_edge(params: ParamsProjet):
    """Rapport EDGE IFC v3 PDF — scores réels + plan d'action."""
    try:
        _, _, calculer_structure = get_moteur_structure()
        calculer_mep = get_moteur_mep()
        generer = get_gen_edge()
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        rm = calculer_mep(donnees, rs)
        set_pdf_lang(getattr(params, 'lang', 'fr'))
        pdf_bytes = generer(rm, params.dict())
        gc.collect()
        return pdf_response(pdf_bytes, fname(params, "edge"))
    except Exception as e:
        logger.error(f"/generate-edge error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-rapport-executif")
async def generate_rapport_executif(params: ParamsProjet):
    """Rapport de synthèse exécutif PDF — maître d'ouvrage."""
    try:
        _, _, calculer_structure = get_moteur_structure()
        calculer_mep = get_moteur_mep()
        generer = get_gen_executif()
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        rm = calculer_mep(donnees, rs)
        set_pdf_lang(getattr(params, 'lang', 'fr'))
        pdf_bytes = generer(rs, rm, params.dict())
        gc.collect()
        return pdf_response(pdf_bytes, fname(params, "rapport_executif"))
    except Exception as e:
        logger.error(f"/generate-rapport-executif error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-fiches-structure")
async def generate_fiches_structure(params: ParamsProjet):
    """Fiches techniques structure PDF."""
    try:
        _, _, calculer_structure = get_moteur_structure()
        generer = get_gen_fiches_structure()
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
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
    """Fiches techniques MEP PDF."""
    try:
        _, _, calculer_structure = get_moteur_structure()
        calculer_mep = get_moteur_mep()
        generer = get_gen_fiches_mep()
        donnees = params_to_donnees(params)
        rs = calculer_structure(donnees)
        rm = calculer_mep(donnees, rs)
        buf = io.BytesIO()
        generer(rm, buf, params.dict())
        pdf_bytes = buf.getvalue()
        gc.collect()
        return pdf_response(pdf_bytes, fname(params, "fiches_mep"))
    except Exception as e:
        logger.error(f"/generate-fiches-mep error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-planches")
async def generate_planches(params: ParamsProjet):
    """Planches BA PDF."""
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
        os.unlink(out_path)
        gc.collect()
        return pdf_response(pdf_bytes, fname(params, "planches_BA"))
    except Exception as e:
        logger.error(f"/generate-planches error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/chat")
async def chat_projet(request: Request):
    """Chat LLM avec contexte projet — fine-tuning outputs."""
    try:
        from chat_engine import chat
        body = await request.json()
        message = body.get("message", "")
        historique = body.get("historique", [])
        params = body.get("params", {})
        resultats_structure = body.get("resultats_structure", {})
        resultats_mep = body.get("resultats_mep", None)
        if not message:
            raise HTTPException(status_code=400, detail="Message manquant")
        reponse = chat(message, historique, params, resultats_structure, resultats_mep)
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
        # Coût mesures : LED + isolation + WC + robinetterie
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
# redeploy 1773678828


# ── PAYDUNYA ──────────────────────────────────────────────
import httpx

PAYDUNYA_URL = "https://app.paydunya.com/api/v1/checkout-invoice/create"
PAYDUNYA_HEADERS = {
    "Content-Type": "application/json",
    "PAYDUNYA-MASTER-KEY": "BQepwkZk-8QAT-Gn2L-Jaio-Chtp8s41cX3U",
    "PAYDUNYA-PRIVATE-KEY": "live_private_Ei0b9wQzTbBqKBcIVRDCun1FwPA",
    "PAYDUNYA-TOKEN": "wi0lPshMeBp4iaiEQ7Lw",
}

@app.post("/create-payment")
async def create_payment(request: Request):
    body = await request.json()
    credits = body.get("credits", 1)
    prix = body.get("prix", 150000)
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

    async with httpx.AsyncClient() as client:
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
        # Parse JSON array
        if response_text.startswith("["):
            translations = _json.loads(response_text)
        else:
            # Try to extract JSON from response
            start = response_text.find("[")
            end = response_text.rfind("]") + 1
            translations = _json.loads(response_text[start:end])
        return {"ok": True, "translations": translations}
    except Exception as e:
        return {"ok": False, "error": str(e), "translations": texts}
