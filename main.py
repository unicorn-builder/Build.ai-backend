"""
Tijan AI — main.py v5
Backend FastAPI — Render Standard (1 CPU / 2GB RAM)

Nouveauté v5 :
  - /parse utilise Autodesk APS pour lecture native DWG (tous formats)
  - Plus de conversion DWG→DXF, lecture directe via API Autodesk officielle

Endpoints :
  GET  /health              → statut serveur
  POST /parse               → parse DWG/DXF/IFC → diagnostic + géométrie (APS)
  POST /calculate           → calcul Eurocodes (paramètres ou géométrie parsée)
  POST /generate            → génère note de calcul PDF
  POST /generate-boq        → génère BOQ structure PDF
  POST /generate-planches   → génère planches BA PDF (nécessite DWG/DXF/IFC)
  POST /generate-mep        → génère planches MEP PDF (nécessite DWG/DXF/IFC)
  POST /generate-ifc        → export IFC structurel
  POST /dossier-complet     → pipeline complet depuis fichier

Règle produit :
  DWG/DXF/IFC → output complet (plans + note + BOQ + IFC)
  Paramètres  → output partiel (note + BOQ, pas de plans)
  PDF/image   → refus avec message explicite
"""

import gc

# Claude Brain — lazy import
def get_claude_brain():
    try:
        from claude_brain import analyser_resultats_calcul, raffiner_output, generer_synthese_projet
        return analyser_resultats_calcul, raffiner_output, generer_synthese_projet
    except Exception as e:
        logger.warning(f"Claude Brain non disponible: {e}")
        return None, None, None
import os
import io
import tempfile
import logging
from datetime import datetime
from typing import Optional

from fastapi import Request, FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tijan")

app = FastAPI(
    title="Tijan AI API",
    description="Bureau d'études automatisé — Structure + MEP + BOQ + IFC",
    version="4.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ════════════════════════════════════════════════════════════
# IMPORTS LAZY (évite crash au démarrage sur Render)
# ════════════════════════════════════════════════════════════

def get_moteur():
    from engine_structural_v3 import DonneesProjet, calculer_projet
    return DonneesProjet, calculer_projet

def get_moteur_mep():
    from engine_mep_v1 import DonneesMEP, calculer_mep
    return DonneesMEP, calculer_mep




def get_aps_parser():
    from aps_parser import parser_dwg_aps
    return parser_dwg_aps


def get_parser():
    from parse_dxf_v4 import (
        diagnostiquer_input, diagnostiquer_parametres,
        traiter_fichier, geo_depuis_parametres, geo_vers_donnees,
        TypeInput, NiveauOutput,
    )
    return (diagnostiquer_input, diagnostiquer_parametres,
            traiter_fichier, geo_depuis_parametres, geo_vers_donnees,
            TypeInput, NiveauOutput)


def get_planches_ba():
    from generate_plans_v3 import generer_dossier_ba
    return generer_dossier_ba


def get_planches_mep():
    from generate_planches_mep_v4 import generer_dossier_mep
    return generer_dossier_mep


def get_note():
    from generate_note_v3 import generer_note
    return generer_note

def get_fiches_structure():
    from generate_fiches_structure_v3 import generer_fiches_structure
    return generer_fiches_structure

def get_boq_mep():
    from generate_boq_mep_v3 import generer_boq_mep
    return generer_boq_mep

def get_edge():
    from generate_edge_v3 import generer_edge
    return generer_edge


def get_fiches_mep():
    from generate_fiches_mep_v3 import generer_fiches_mep
    return generer_fiches_mep


def get_note_mep():
    from generate_note_mep_v3 import generer_note_mep
    return generer_note_mep



def get_boq():
    from generate_boq_v3 import generer_boq
    return generer_boq


def get_ifc():
    from generate_ifc import generer_ifc
    return generer_ifc


# ════════════════════════════════════════════════════════════
# MODÈLES PYDANTIC
# ════════════════════════════════════════════════════════════

class ParamsProjet(BaseModel):
    nom: str = "Projet Tijan"
    ville: str = "Dakar"
    nb_niveaux: int = 4
    hauteur_etage_m: float = 3.0
    surface_emprise_m2: float = 500.0
    portee_max_m: float = 5.5
    portee_min_m: float = 4.0
    nb_travees_x: int = 3
    nb_travees_y: int = 2
    usage_principal: str = "residentiel"
    classe_beton: str = "C30/37"
    classe_acier: str = "HA500"
    pression_sol_MPa: float = 0.15
    sol_context: Optional[str] = None  # JSON stringifié des params sol
    profondeur_fondation_m: float = 1.5
    distance_mer_km: float = 2.0
    zone_sismique: int = 1
    enrobage_mm: float = 30.0


# ════════════════════════════════════════════════════════════
# UTILITAIRES
# ════════════════════════════════════════════════════════════

def params_to_donnees(params: ParamsProjet):
    """Convertit ParamsProjet → DonneesProjet du moteur v3.
    Si sol_context fourni, utilise la pression admissible réelle de l'étude de sol."""
    import json as _json
    DonneesProjet, _ = get_moteur()

    # Pression sol : priorité à l'étude de sol si fournie
    pression_sol = params.pression_sol_MPa
    sol_data = {}
    if params.sol_context:
        try:
            sol_data = _json.loads(params.sol_context)
            if sol_data.get('pression_admissible_MPa'):
                pression_sol = float(sol_data['pression_admissible_MPa'])
                logger.info(f"Étude sol intégrée : {sol_data.get('type_sol')} / {pression_sol} MPa")
        except Exception as e:
            logger.warning(f"sol_context parse error: {e}")

    return DonneesProjet(
        nom=params.nom,
        ville=params.ville,
        nb_niveaux=params.nb_niveaux,
        hauteur_etage_m=params.hauteur_etage_m,
        surface_emprise_m2=params.surface_emprise_m2,
        portee_max_m=params.portee_max_m,
        portee_min_m=params.portee_min_m,
        nb_travees_x=params.nb_travees_x,
        nb_travees_y=params.nb_travees_y,
        classe_beton=params.classe_beton,
        classe_acier=params.classe_acier,
        pression_sol_MPa=pression_sol,
        zone_sismique=getattr(params, 'zone_sismique', 'faible'),
    )


def pdf_response(pdf_bytes: bytes, filename: str) -> StreamingResponse:
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


async def save_upload(file: UploadFile) -> str:
    """Sauvegarde l'upload dans un fichier temporaire et retourne le chemin"""
    suffix = os.path.splitext(file.filename)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        return tmp.name


# ════════════════════════════════════════════════════════════
# ENDPOINTS
# ════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    """Statut serveur + disponibilité des modules"""
    modules = {}
    try:
        import ezdxf
        modules["ezdxf"] = ezdxf.__version__
    except ImportError:
        modules["ezdxf"] = "non installé"

    try:
        import ifcopenshell
        modules["ifcopenshell"] = "ok"
    except ImportError:
        modules["ifcopenshell"] = "non installé"

    aps_ok = bool(os.getenv("APS_CLIENT_ID"))
    modules["aps"] = "configuré" if aps_ok else "non configuré"

    return {
        "status": "ok",
        "version": "5.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "modules": modules,
    }


@app.post("/parse")
async def parse_fichier(
    file: UploadFile = File(...),
    nb_niveaux: Optional[int] = Form(None),
    ville: Optional[str] = Form(None),
    beton: Optional[str] = Form(None),
):
    """
    Parse universel : PDF vectoriel, PDF scanne, DWG, DXF.
    PDF vectoriel  -> pymupdf + Claude API texte
    PDF scanne     -> pymupdf image + Claude API vision
    DWG/DXF        -> ezdxf + Claude API interpretation
    """
    from parse_plans import extraire_params
    from pathlib import Path

    tmp_path = await save_upload(file)
    try:
        result = extraire_params(tmp_path)

        # Appliquer les overrides manuels si fournis
        if result.get("ok"):
            if nb_niveaux: result["nb_niveaux"] = nb_niveaux
            if ville:      result["ville"]       = ville
            if beton:      result["classe_beton"] = beton

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"/parse error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass



@app.post("/parse-sol")
async def parse_sol_fichier(file: UploadFile = File(...)):
    """
    Parse un PDF d'étude de sol.
    Extrait : type sol, pression admissible, nappe, ancrage, agressivité, recommandation fondation.
    """
    from parse_sol import extraire_params_sol
    tmp_path = await save_upload(file)
    try:
        result = extraire_params_sol(tmp_path)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"/parse-sol error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

@app.post("/calculate")
async def calculate(params: ParamsProjet):
    """
    Calcul Eurocodes depuis paramètres.
    Toujours disponible (pas besoin de fichier).
    """
    try:
        DonneesProjet, calculer_projet = get_moteur()
        donnees = params_to_donnees(params)
        resultats = calculer_projet(donnees)
        gc.collect()


        # Analyse Claude — cerveau intelligent
        analyse_claude = {}
        try:
            analyser_fn, _, _ = get_claude_brain()
            if analyser_fn:
                _calcul = {
                    "poteaux": [{"label": p.label, "NEd_kN": p.NEd_kN, "section_mm": p.section_mm,
                                 "nb_barres": p.nb_barres, "diametre_mm": p.diametre_mm,
                                 "taux_armature_pct": p.taux_armature_pct, "verif_ok": p.verif_ok}
                                for p in resultats.poteaux_par_niveau],
                    "poutre": {"b_mm": resultats.poutre_type.b_mm, "h_mm": resultats.poutre_type.h_mm,
                               "As_inf_cm2": resultats.poutre_type.As_inf_cm2, "portee_m": resultats.poutre_type.portee_m},
                    "fondation": {"type": resultats.fondation.type_fond, "nb_pieux": resultats.fondation.nb_pieux},
                    "boq_resume": {"beton_m3": resultats.boq.beton_total_m3, "acier_kg": resultats.boq.acier_total_kg,
                                   "cout_bas_FCFA": resultats.boq.cout_total_bas, "cout_haut_FCFA": resultats.boq.cout_total_haut,
                                   "ratio_FCFA_m2": resultats.boq.ratio_fcfa_m2},
                }
                analyse_claude = analyser_fn(params.dict(), _calcul)
        except Exception as e:
            logger.warning(f"Claude analyse: {e}")
        return {
            "ok": True,
        "params_input": params.dict(),
            "projet": params.nom,
            "niveau_output": "partiel",
            "poteaux": [
                {
                    "label": p.label,
                    "NEd_kN": p.NEd_kN,
                    "section_mm": p.section_mm,
                    "nb_barres": p.nb_barres,
                    "diametre_mm": p.diametre_mm,
                    "cadre_diam_mm": p.cadre_diam_mm,
                    "espacement_cadres_mm": p.espacement_cadres_mm,
                    "taux_armature_pct": p.taux_armature_pct,
                    "NRd_kN": p.NRd_kN,
                    "verif_ok": p.verif_ok,
                }
                for p in resultats.poteaux_par_niveau
            ],
            "poutre": {
                "b_mm": resultats.poutre_type.b_mm,
                "h_mm": resultats.poutre_type.h_mm,
                "As_inf_cm2": resultats.poutre_type.As_inf_cm2,
                "As_sup_cm2": resultats.poutre_type.As_sup_cm2,
                "etrier_diam_mm": resultats.poutre_type.etrier_diam_mm,
                "etrier_esp_mm": resultats.poutre_type.etrier_esp_mm,
                "portee_m": resultats.poutre_type.portee_m,
            },
            "fondation": {
                "type": resultats.fondation.type_fond,
                "nb_pieux": resultats.fondation.nb_pieux,
                "diam_pieu_mm": resultats.fondation.diam_pieu_mm,
                "longueur_pieu_m": resultats.fondation.longueur_pieu_m,
                "As_cm2": resultats.fondation.As_cm2,
            },
            "analyse_claude": analyse_claude,
            "boq_resume": {
                "beton_m3": resultats.boq.beton_total_m3,
                "acier_kg": resultats.boq.acier_total_kg,
                "cout_bas_FCFA": resultats.boq.cout_total_bas,
                "cout_haut_FCFA": resultats.boq.cout_total_haut,
                "ratio_FCFA_m2": resultats.boq.ratio_fcfa_m2,
            },
        }

    except Exception as e:
        logger.error(f"/calculate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate")
async def generate_note(params: ParamsProjet):
    """Note de calcul PDF — disponible avec paramètres seuls"""
    try:
        DonneesProjet, calculer_projet = get_moteur()
        donnees = params_to_donnees(params)
        resultats = calculer_projet(donnees)

        # Attacher les métadonnées au résultat pour le générateur
        resultats._nom = params.nom
        resultats._ville = params.ville
        resultats._surface = params.surface_emprise_m2
        resultats._portee_max = params.portee_max_m
        resultats._portee_min = params.portee_min_m
        resultats._classe_beton = params.classe_beton
        resultats._classe_acier = params.classe_acier
        resultats._pression_sol = params.pression_sol_MPa

        try:
            from generate_note_v3 import generer_note_avec_donnees
            buf = io.BytesIO()
            generer_note_avec_donnees(resultats, donnees, buf)
            pdf_bytes = buf.getvalue()
        except Exception as e2:
            logger.warning(f"Vrai PDF échoué ({e2}), fallback simple")
            generer_note = get_note()
            buf = io.BytesIO()
            generer_note(resultats, buf)
            pdf_bytes = buf.getvalue()

        gc.collect()
        return pdf_response(
            pdf_bytes,
            f"tijan_note_{params.nom.replace(' ', '_')[:20]}.pdf"
        )
    except Exception as e:
        logger.error(f"/generate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-boq")
async def generate_boq(params: ParamsProjet):
    """BOQ structure PDF — disponible avec paramètres seuls"""
    try:
        DonneesProjet, calculer_projet = get_moteur()
        generer_boq = get_boq()
        donnees = params_to_donnees(params)
        resultats = calculer_projet(donnees)

        buf = io.BytesIO()
        generer_boq(resultats, buf)
        pdf_bytes = buf.getvalue()
        gc.collect()

        return pdf_response(
            pdf_bytes,
            f"tijan_boq_{params.nom.replace(' ', '_')[:20]}.pdf"
        )
    except Exception as e:
        logger.error(f"/generate-boq error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-planches")
async def generate_planches(params: ParamsProjet):
    """Planches BA PDF — disponible avec paramètres seuls"""
    try:
        DonneesProjet, calculer_projet = get_moteur()
        generer_planches = get_planches_ba()
        donnees = params_to_donnees(params)
        resultats = calculer_projet(donnees)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_out:
            out_path = tmp_out.name

        # Adapter ResultatsCalcul v3 vers arguments generer_dossier_ba
        
        proj = {'nom': params.nom, 'ville': params.ville + ', Senegal', 'beton': params.classe_beton, 'acier': params.classe_acier, 'ref': 'TIJAN-STR', 'norme': 'EN 1992-1-1'}
        portees_x = [params.portee_max_m] * params.nb_travees_x
        portees_y = [params.portee_min_m] * params.nb_travees_y
        params_dict = {'nom': params.nom, 'ville': params.ville, 'nb_niveaux': params.nb_niveaux, 'surface_emprise_m2': params.surface_emprise_m2, 'portee_max_m': params.portee_max_m, 'portee_min_m': params.portee_min_m, 'nb_travees_x': params.nb_travees_x, 'nb_travees_y': params.nb_travees_y, 'classe_beton': params.classe_beton, 'hauteur_etage_m': params.hauteur_etage_m}
        generer_planches(out_path, resultats=resultats, params=params_dict)

        with open(out_path, "rb") as f:
            pdf_bytes = f.read()

        os.unlink(out_path)
        gc.collect()

        return pdf_response(pdf_bytes, f"tijan_planches_BA_{params.nom.replace(' ', '_')[:20]}.pdf")

    except Exception as e:
        logger.error(f"/generate-planches error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-mep")
async def generate_mep(params: ParamsProjet):
    """Planches MEP PDF — disponible avec paramètres seuls"""
    try:
        generer_dossier_mep = get_planches_mep()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_out:
            out_path = tmp_out.name

        generer_dossier_mep(out_path)

        with open(out_path, "rb") as f:
            pdf_bytes = f.read()

        os.unlink(out_path)
        gc.collect()

        return pdf_response(pdf_bytes, f"tijan_MEP_{params.nom.replace(' ', '_')[:20]}.pdf")

    except Exception as e:
        logger.error(f"/generate-mep error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-ifc")
async def generate_ifc_endpoint(params: ParamsProjet):
    """Export IFC structurel — disponible avec paramètres seuls"""
    try:
        DonneesProjet, calculer_projet = get_moteur()
        generer_ifc = get_ifc()
        donnees = params_to_donnees(params)
        resultats = calculer_projet(donnees)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
            out_path = tmp.name

        generer_ifc(resultats, out_path)

        with open(out_path, "rb") as f:
            ifc_bytes = f.read()
        os.unlink(out_path)
        gc.collect()

        return StreamingResponse(
            io.BytesIO(ifc_bytes),
            media_type="application/x-step",
            headers={
                "Content-Disposition":
                f"attachment; filename=tijan_{params.nom.replace(' ','_')[:20]}.ifc"
            },
        )
    except Exception as e:
        logger.error(f"/generate-ifc error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/dossier-complet")
async def dossier_complet(
    file: UploadFile = File(...),
    nb_niveaux: Optional[int] = Form(None),
    ville: Optional[str] = Form(None),
    beton: Optional[str] = Form(None),
):
    """
    Pipeline complet depuis un fichier DWG/DXF/IFC.
    Retourne un JSON avec :
      - diagnostic
      - résultats de calcul
      - URLs de téléchargement (si déployé avec stockage)
    ou refus propre si format non supporté.
    """
    (_, _, traiter_fichier, _, _,
     TypeInput, NiveauOutput) = get_parser()

    tmp_path = await save_upload(file)
    try:
        overrides = {}
        if nb_niveaux: overrides["nb_niveaux"] = nb_niveaux
        if ville:      overrides["ville"] = ville
        if beton:      overrides["beton"] = beton

        result = traiter_fichier(tmp_path, overrides)

        if not result["ok"]:
            return JSONResponse(
                status_code=422,
                content={
                    "ok": False,
                    "message": result.get("message"),
                }
            )

        # Calcul moteur
        donnees_dict = result["donnees_moteur"]
        DonneesProjet, calculer_projet = get_moteur()
        donnees = DonneesProjet(**donnees_dict)
        resultats = calculer_projet(donnees)

        response = {
            "ok": True,
            "niveau_output": result["niveau_output"],
            "message": result["message"],
            "geometrie": result.get("geometrie"),
            "score_qualite": result.get("score_qualite"),
            "calcul": {
                "nb_niveaux": donnees.nb_niveaux,
                "section_rdc": f"{resultats.poteaux_par_niveau[0].section_mm}mm",
                "armatures_rdc": (
                    f"{resultats.poteaux_par_niveau[0].nb_barres}"
                    f"HA{resultats.poteaux_par_niveau[0].diametre_mm}"
                ),
                "poutre": (
                    f"{resultats.poutre_type.b_mm}×"
                    f"{resultats.poutre_type.h_mm}mm"
                ),
                "fondation": resultats.fondation.type_fond,
                "boq_ratio_fcfa_m2": resultats.boq.ratio_fcfa_m2,
            },
            "outputs_disponibles": (
                ["note_calcul", "boq", "planches_ba", "planches_mep", "ifc"]
                if result["niveau_output"] == "complet"
                else ["note_calcul", "boq"]
            ),
        }

        gc.collect()
        return JSONResponse(content=response)

    finally:
        os.unlink(tmp_path)



@app.post("/refine")
async def refine_output(request: Request):
    """Peaufinage d output par prompt utilisateur."""
    try:
        body = await request.json()
        output_existant = body.get("output_existant", {})
        prompt_utilisateur = body.get("prompt", "")
        contexte_projet = body.get("contexte_projet", {})

        if not prompt_utilisateur:
            raise HTTPException(status_code=400, detail="Prompt manquant")

        _, raffiner_fn, _ = get_claude_brain()
        if not raffiner_fn:
            raise HTTPException(status_code=503, detail="Claude Brain non disponible")

        result = raffiner_fn(output_existant, prompt_utilisateur, contexte_projet)
        gc.collect()
        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"/refine error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/synthese")
async def synthese_projet(params: ParamsProjet):
    """Synthese narrative du projet via Claude."""
    try:
        DonneesProjet, calculer_projet = get_moteur()
        donnees = params_to_donnees(params)
        resultats = calculer_projet(donnees)

        _, _, synthese_fn = get_claude_brain()
        if not synthese_fn:
            raise HTTPException(status_code=503, detail="Claude Brain non disponible")

        _calcul = {
            "poteaux": [{"section_mm": p.section_mm} for p in resultats.poteaux_par_niveau],
            "boq_resume": {"ratio_FCFA_m2": resultats.boq.ratio_fcfa_m2},
        }
        synthese = synthese_fn(params.dict(), _calcul)
        gc.collect()
        return JSONResponse(content={"ok": True, "synthese": synthese})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"/synthese error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-fiches-structure")
async def generate_fiches_structure(params: ParamsProjet):
    """Fiches techniques materiaux structure PDF"""
    try:
        DonneesProjet, calculer_projet = get_moteur()
        generer = get_fiches_structure()
        donnees = params_to_donnees(params)
        resultats = calculer_projet(donnees)
        buf = io.BytesIO()
        generer(resultats, buf, params.dict())
        pdf_bytes = buf.getvalue()
        gc.collect()
        return pdf_response(pdf_bytes, f"tijan_fiches_structure_{params.nom.replace(' ','_')[:20]}.pdf")
    except Exception as e:
        logger.error(f"/generate-fiches-structure error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/calculate-mep")
async def calculate_mep(params: ParamsProjet):
    """Calcul MEP réel depuis paramètres projet — moteur engine_mep_v1"""
    try:
        import json as _json
        DonneesMEP, calculer_mep = get_moteur_mep()

        # Intégrer étude de sol si fournie
        sol_data = {}
        if params.sol_context:
            try:
                sol_data = _json.loads(params.sol_context)
            except Exception:
                pass

        donnees = DonneesMEP(
            nom=params.nom,
            ville=params.ville,
            nb_niveaux=params.nb_niveaux,
            hauteur_etage_m=params.hauteur_etage_m,
            surface_emprise_m2=params.surface_emprise_m2,
            personnes_par_logement=4,
            usage="residentiel",
            distance_mer_km=getattr(params, 'distance_mer_km', 2.0),
            note_sol=sol_data.get('observations', '') + (
                f" Type : {sol_data.get('type_sol','')}."
                f" Nappe : {sol_data.get('profondeur_nappe_m','?')}m."
                f" Agressivité : {sol_data.get('classe_agressivite','?')}."
            ) if sol_data else "",
        )
        r = calculer_mep(donnees)
        gc.collect()
        return {
            "ok": True,
            "projet": params.nom,
            "electrique": {
                "puissance_totale_kva": r.electrique.puissance_totale_souscrite_kva,
                "transfo_kva": r.electrique.transfo_necessaire_kva,
                "groupe_electrogene_kva": r.electrique.groupe_electrogene_kva,
                "nb_compteurs": r.electrique.nb_compteurs_divisionnaires,
                "conso_annuelle_kwh": r.electrique.conso_annuelle_estimee_kwh,
                "facture_annuelle_fcfa": r.electrique.facture_annuelle_estimee_fcfa,
            },
            "plomberie": {
                "nb_logements": r.plomberie.nb_logements,
                "besoin_total_m3_j": r.plomberie.besoin_total_m3_j,
                "volume_citerne_m3": r.plomberie.volume_citerne_m3,
                "volume_bache_m3": r.plomberie.volume_bache_incendie_m3,
                "debit_surpresseur_m3h": r.plomberie.debit_surpresseur_m3h,
                "nb_chauffe_eau_solaire": r.plomberie.nb_chauffe_eau_solaire,
                "facture_eau_fcfa": r.plomberie.facture_eau_annuelle_fcfa,
            },
            "cvc": {
                "puissance_frigorifique_kw": r.cvc.puissance_frigorifique_installee_kW,
                "nb_splits_sejour": r.cvc.nb_splits_sejour,
                "nb_splits_chambre": r.cvc.nb_splits_chambre,
                "nb_vmc": r.cvc.nb_vmc_double_flux,
                "conso_cvc_kwh_an": r.cvc.conso_cvc_annuelle_kwh,
            },
            "edge": {
                "economie_energie_pct": r.edge.economie_energie_pct,
                "economie_eau_pct": r.edge.economie_eau_pct,
                "economie_materiaux_pct": r.edge.economie_materiaux_pct,
                "nb_criteres_conformes": r.edge.nb_criteres_conformes,
                "certifiable": r.edge.certifiable,
                "niveau_certification": r.edge.niveau_certification,
                "mesures_energie": r.edge.mesures_energie,
                "mesures_eau": r.edge.mesures_eau,
                "mesures_materiaux": r.edge.mesures_materiaux,
                "surcout_vert_pct": r.edge.surcout_vert_pct,
                "payback_ans": r.edge.payback_ans,
                "conso_ref_kwh_m2": r.edge.conso_reference_kwh_m2_an,
                "conso_projet_kwh_m2": r.edge.conso_projet_kwh_m2_an,
            },
            "boq_mep": {
                "basic_fcfa": r.boq_total_basic,
                "hend_fcfa": r.boq_total_hend,
                "luxury_fcfa": r.boq_total_luxury,
                "lots": [
                    {"nom": l.nom, "basic": l.basic_fcfa, "hend": l.hend_fcfa, "luxury": l.luxury_fcfa}
                    for l in r.boq_lots
                ],
            },
            "analyse_cout_benefice": {
                "delta_basic_hend": r.analyse_cout_benefice.delta_basic_hend,
                "delta_basic_luxury": r.analyse_cout_benefice.delta_basic_luxury,
                "economie_hend_fcfa_an": r.analyse_cout_benefice.economie_energie_hend_fcfa_an,
                "economie_luxury_fcfa_an": r.analyse_cout_benefice.economie_energie_luxury_fcfa_an,
                "payback_hend_ans": r.analyse_cout_benefice.payback_hend_ans,
                "payback_luxury_ans": r.analyse_cout_benefice.payback_luxury_ans,
                "roi_hend_20ans_pct": r.analyse_cout_benefice.roi_hend_20ans_pct,
                "roi_luxury_20ans_pct": r.analyse_cout_benefice.roi_luxury_20ans_pct,
                "recommandation": r.analyse_cout_benefice.recommandation,
            },
        }
    except Exception as e:
        logger.error(f"/calculate-mep error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-note-mep")
async def generate_note_mep(params: ParamsProjet):
    """Note de calcul MEP & Automation PDF"""
    try:
        DonneesProjet, calculer_projet = get_moteur()
        generer = get_note_mep()
        donnees = params_to_donnees(params)
        resultats = calculer_projet(donnees)
        buf = io.BytesIO()
        generer(resultats, buf, params.dict())
        pdf_bytes = buf.getvalue()
        gc.collect()
        return pdf_response(pdf_bytes, f"tijan_note_mep_{params.nom.replace(' ','_')[:20]}.pdf")
    except Exception as e:
        logger.error(f"/generate-note-mep error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-boq-mep")
async def generate_boq_mep(params: ParamsProjet):
    """BOQ MEP & Automation — 3 niveaux PDF"""
    try:
        DonneesProjet, calculer_projet = get_moteur()
        generer = get_boq_mep()
        donnees = params_to_donnees(params)
        resultats = calculer_projet(donnees)
        buf = io.BytesIO()
        generer(resultats, buf, params.dict())
        pdf_bytes = buf.getvalue()
        gc.collect()
        return pdf_response(pdf_bytes, f"tijan_boq_mep_{params.nom.replace(' ','_')[:20]}.pdf")
    except Exception as e:
        logger.error(f"/generate-boq-mep error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-fiches-mep")
async def generate_fiches_mep(params: ParamsProjet):
    """Fiches techniques equipements MEP PDF"""
    try:
        DonneesProjet, calculer_projet = get_moteur()
        generer = get_fiches_mep()
        donnees = params_to_donnees(params)
        resultats = calculer_projet(donnees)
        buf = io.BytesIO()
        generer(resultats, buf, params.dict())
        pdf_bytes = buf.getvalue()
        gc.collect()
        return pdf_response(pdf_bytes, f"tijan_fiches_mep_{params.nom.replace(' ','_')[:20]}.pdf")
    except Exception as e:
        logger.error(f"/generate-fiches-mep error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-edge")
async def generate_edge(params: ParamsProjet):
    """Rapport conformite EDGE PDF"""
    try:
        DonneesProjet, calculer_projet = get_moteur()
        generer = get_edge()
        donnees = params_to_donnees(params)
        resultats = calculer_projet(donnees)
        buf = io.BytesIO()
        generer(resultats, buf, params.dict())
        pdf_bytes = buf.getvalue()
        gc.collect()
        return pdf_response(pdf_bytes, f"tijan_edge_{params.nom.replace(' ','_')[:20]}.pdf")
    except Exception as e:
        logger.error(f"/generate-edge error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ════════════════════════════════════════════════════════════
# ENTRÉE
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
# redeploy 1773678828
