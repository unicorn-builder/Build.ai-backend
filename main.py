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

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
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
    from generate_planches_ba_v4 import generer_dossier_ba
    return generer_dossier_ba


def get_planches_mep():
    from generate_planches_mep_v4 import generer_dossier_mep
    return generer_dossier_mep


def get_note():
    from generate_note_v3 import generer_note
    return generer_note


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
    profondeur_fondation_m: float = 1.5
    distance_mer_km: float = 2.0
    zone_sismique: int = 1
    enrobage_mm: float = 30.0


# ════════════════════════════════════════════════════════════
# UTILITAIRES
# ════════════════════════════════════════════════════════════

def params_to_donnees(params: ParamsProjet):
    """Convertit ParamsProjet → DonneesProjet du moteur v3"""
    DonneesProjet, _ = get_moteur()
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
        usage_principal=params.usage_principal,
        classe_beton=params.classe_beton,
        classe_acier=params.classe_acier,
        pression_sol_MPa=params.pression_sol_MPa,
        profondeur_fondation_m=params.profondeur_fondation_m,
        distance_mer_km=params.distance_mer_km,
        zone_sismique=params.zone_sismique,
        enrobage_mm=params.enrobage_mm,
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
    Parse un fichier DWG/DXF/IFC via Autodesk APS (lecture native DWG).
    Retourne le diagnostic + géométrie extraite.
    """
    from pathlib import Path

    ext = Path(file.filename).suffix.lower()
    REFUSES = {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff",
               ".bmp", ".gif", ".webp", ".svg"}

    if ext in REFUSES:
        return JSONResponse(status_code=422, content={
            "ok": False,
            "niveau_output": "refuse",
            "message": (
                "✗ Format non supporté. "
                "Fournissez un fichier DWG, DXF ou IFC. "
                "Les PDF et images ne sont pas acceptés — "
                "utilisez la saisie paramétrique pour les calculs sans plans."
            )
        })

    tmp_path = await save_upload(file)
    try:
        overrides = {}
        if nb_niveaux: overrides["nb_niveaux"] = nb_niveaux
        if ville: overrides["ville"] = ville
        if beton: overrides["beton"] = beton

        if ext in (".dwg", ".dxf"):
            # APS — lecture native, tous formats AutoCAD
            parser_dwg_aps = get_aps_parser()
            result = parser_dwg_aps(tmp_path)
            if overrides:
                dm = result.get("donnees_moteur", {})
                dm.update(overrides)

        elif ext in (".ifc", ".ifczip"):
            # IFC — ifcopenshell
            (_, _, traiter_fichier, _, _, _, _) = get_parser()
            result = traiter_fichier(tmp_path, overrides)
            if result.get("geo"):
                geo = result.pop("geo")
                result["geometrie"] = {
                    "projet_nom": geo.projet_nom,
                    "emprise_x_m": round(geo.emprise_x/1000, 2),
                    "emprise_y_m": round(geo.emprise_y/1000, 2),
                    "nb_axes_x": len(geo.axes_x),
                    "nb_axes_y": len(geo.axes_y),
                    "portees_x_m": [round(p/1000, 2) for p in geo.portees_x],
                    "portees_y_m": [round(p/1000, 2) for p in geo.portees_y],
                    "score_qualite": geo.score_qualite,
                }
        else:
            return JSONResponse(status_code=422, content={
                "ok": False,
                "niveau_output": "refuse",
                "message": f"Format '{ext}' non reconnu. Acceptés : DWG, DXF, IFC."
            })

        gc.collect()
        if not result.get("ok"):
            return JSONResponse(status_code=422, content={
                "ok": False,
                "niveau_output": result.get("niveau_output", "refuse"),
                "message": result.get("message", "Erreur de parsing"),
            })

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Erreur /parse : {e}")
        return JSONResponse(status_code=500, content={
            "ok": False,
            "message": f"Erreur parsing : {str(e)[:300]}"
        })
    finally:
        try: os.unlink(tmp_path)
        except: pass
        gc.collect()


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
        generer_note = get_note()
        donnees = params_to_donnees(params)
        resultats = calculer_projet(donnees)

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
async def generate_planches(
    file: UploadFile = File(...),
    nb_niveaux: Optional[int] = Form(None),
    ville: Optional[str] = Form(None),
    beton: Optional[str] = Form(None),
):
    """
    Planches BA PDF — nécessite DWG/DXF/IFC.
    Refus propre si PDF/image fourni.
    """
    (_, _, traiter_fichier, _, geo_vers_donnees,
     TypeInput, NiveauOutput) = get_parser()

    tmp_path = await save_upload(file)
    try:
        overrides = {}
        if nb_niveaux: overrides["nb_niveaux"] = nb_niveaux
        if ville:      overrides["ville"] = ville
        if beton:      overrides["beton"] = beton

        result = traiter_fichier(tmp_path, overrides)

        if not result["ok"] or result["niveau_output"] != "complet":
            return JSONResponse(
                status_code=422,
                content={
                    "ok": False,
                    "message": result.get("message"),
                    "conseil": (
                        "Les plans ne peuvent être générés qu'à partir d'un fichier "
                        "DWG, DXF ou IFC. Pour une note de calcul sans plans, "
                        "utilisez /generate avec saisie paramétrique."
                    )
                }
            )

        geo = result["geo"]
        donnees_dict = result["donnees_moteur"]

        DonneesProjet, calculer_projet = get_moteur()
        generer_dossier_ba = get_planches_ba()

        # Construire DonneesProjet depuis le dict
        donnees = DonneesProjet(**donnees_dict)
        resultats = calculer_projet(donnees)

        # Paramètres géométriques pour les planches
        portees_x = geo.portees_x if geo.portees_x else None
        portees_y = geo.portees_y if geo.portees_y else None

        # Construire poteaux depuis résultats moteur
        poteaux = [
            {
                "label": p.label,
                "b": p.section_mm,
                "nb": p.nb_barres,
                "diam": p.diametre_mm,
                "cd": p.cadre_diam_mm,
                "ce": p.espacement_cadres_mm,
                "NEd": p.NEd_kN,
            }
            for p in resultats.poteaux_par_niveau
        ]

        poutre = {
            "b": resultats.poutre_type.b_mm,
            "h": resultats.poutre_type.h_mm,
            "As_inf": resultats.poutre_type.As_inf_cm2,
            "As_sup": resultats.poutre_type.As_sup_cm2,
            "etrier_d": resultats.poutre_type.etrier_diam_mm,
            "etrier_e": resultats.poutre_type.etrier_esp_mm,
            "portee": int((portees_x[0] if portees_x else 5000)),
        }

        fond = {
            "type": resultats.fondation.type_fond,
            "nb": resultats.fondation.nb_pieux,
            "diam": resultats.fondation.diam_pieu_mm,
            "L": resultats.fondation.longueur_pieu_m,
            "As_cm2": resultats.fondation.As_cm2,
            "cerce_d": 12,
            "cerce_e": 200,
        }

        proj = {
            "nom": donnees.nom,
            "ref": f"TIJAN-{datetime.now().strftime('%y%m')}",
            "ville": donnees.ville,
            "beton": donnees.classe_beton,
            "acier": donnees.classe_acier,
            "norme": "EN 1992-1-1",
        }

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_out:
            out_path = tmp_out.name

        generer_dossier_ba(out_path, proj, portees_x, portees_y,
                           poteaux, poutre, fond)

        with open(out_path, "rb") as f:
            pdf_bytes = f.read()

        os.unlink(out_path)
        gc.collect()

        return pdf_response(
            pdf_bytes,
            f"tijan_planches_BA_{donnees.nom.replace(' ', '_')[:20]}.pdf"
        )

    finally:
        os.unlink(tmp_path)


@app.post("/generate-mep")
async def generate_mep(
    file: UploadFile = File(...),
    nb_niveaux: Optional[int] = Form(None),
):
    """
    Planches MEP PDF — nécessite DWG/DXF/IFC.
    Refus propre si PDF/image fourni.
    """
    (_, _, traiter_fichier, _, _,
     TypeInput, NiveauOutput) = get_parser()

    tmp_path = await save_upload(file)
    try:
        result = traiter_fichier(tmp_path, {"nb_niveaux": nb_niveaux} if nb_niveaux else {})

        if not result["ok"] or result["niveau_output"] != "complet":
            return JSONResponse(
                status_code=422,
                content={
                    "ok": False,
                    "message": result.get("message"),
                    "conseil": (
                        "Les plans MEP nécessitent un fichier DWG, DXF ou IFC."
                    )
                }
            )

        generer_dossier_mep = get_planches_mep()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_out:
            out_path = tmp_out.name

        generer_dossier_mep(out_path)

        with open(out_path, "rb") as f:
            pdf_bytes = f.read()

        os.unlink(out_path)
        gc.collect()

        return pdf_response(pdf_bytes, "tijan_planches_MEP.pdf")

    finally:
        os.unlink(tmp_path)


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

# ════════════════════════════════════════════════════════════
# ENTRÉE
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
