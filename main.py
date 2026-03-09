"""
Tijan AI — Backend FastAPI v2 — Lazy imports pour memory optimization
"""
import gc
gc.enable()
import os
import uuid
import tempfile

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field, validator
from typing import Optional, List

app = FastAPI(
    title="Tijan AI Engine",
    description="Moteur de calcul structurel Eurocodes — Engineering Intelligence for Africa",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# MODÈLES PYDANTIC
# ============================================================

class GeometrieInput(BaseModel):
    surface_emprise_m2: float = Field(..., gt=0)
    nb_niveaux: int = Field(..., ge=1, le=50)
    hauteur_etage_m: float = Field(3.0, ge=2.5, le=6.0)
    portee_max_m: float = Field(6.0, ge=3.0, le=12.0)
    nb_voiles_facade: int = Field(4, ge=2, le=20)
    nb_voiles_internes: int = Field(2, ge=0, le=10)
    epaisseur_voile_m: float = Field(0.20, ge=0.15, le=0.50)

class UsageInput(BaseModel):
    usage_principal: str = Field("residentiel")
    charge_toiture_kNm2: float = Field(1.0, ge=0.5, le=5.0)

    @validator('usage_principal')
    def valider_usage(cls, v):
        valides = ["residentiel", "bureaux", "mixte"]
        if v not in valides:
            raise ValueError(f"Usage doit être parmi : {valides}")
        return v

class SolInput(BaseModel):
    pression_admissible_MPa: float = Field(..., gt=0, le=1.0)
    profondeur_fondation_m: float = Field(1.5, ge=0.5, le=10.0)
    presence_nappe: bool = False
    description: str = Field("")

class LocalisationInput(BaseModel):
    ville: str = Field("dakar")
    distance_mer_km: float = Field(5.0, ge=0.0, le=500.0)
    zone_sismique: int = Field(1, ge=1, le=3)

    @validator('ville')
    def valider_ville(cls, v):
        valides = ["dakar", "abidjan", "casablanca", "lagos"]
        if v not in valides:
            raise ValueError(f"Ville doit être parmi : {valides}")
        return v

class ProjetInput(BaseModel):
    nom: str = Field(..., min_length=2, max_length=200, alias="nom_batiment")
    geometrie: GeometrieInput
    usage: UsageInput = UsageInput()
    sol: SolInput
    localisation: LocalisationInput = LocalisationInput()
    ingenieur: str = Field("")

    class Config:
        allow_population_by_field_name = True
        extra = "ignore"

class ResultatCompletOutput(BaseModel):
    projet_nom: str
    statut: str
    resume: dict
    score_edge: dict
    pdf_disponible: bool
    pdf_url: Optional[str] = None

class SpeckleRequest(BaseModel):
    resultats: dict
    nom_projet: str = "Projet Tijan AI"
    token: str = None
    server_url: str = None

# ============================================================
# UTILITAIRES
# ============================================================

def input_vers_projet(data: ProjetInput):
    from engine_structural import (
        ProjetStructurel, ParamsGeometrie, ParamsUsage,
        ParamsSol, ParamsLocalisation, UsageBatiment, ZoneVent
    )
    usage_map = {"residentiel": UsageBatiment.RESIDENTIEL, "bureaux": UsageBatiment.BUREAUX, "mixte": UsageBatiment.MIXTE}
    ville_map = {"dakar": ZoneVent.DAKAR, "abidjan": ZoneVent.ABIDJAN, "casablanca": ZoneVent.CASABLANCA, "lagos": ZoneVent.LAGOS}
    return ProjetStructurel(
        nom=data.nom,
        geometrie=ParamsGeometrie(
            surface_emprise_m2=data.geometrie.surface_emprise_m2,
            nb_niveaux=data.geometrie.nb_niveaux,
            hauteur_etage_m=data.geometrie.hauteur_etage_m,
            portee_max_m=data.geometrie.portee_max_m,
            nb_voiles_facade=data.geometrie.nb_voiles_facade,
            nb_voiles_internes=data.geometrie.nb_voiles_internes,
            epaisseur_voile_m=data.geometrie.epaisseur_voile_m,
        ),
        usage=ParamsUsage(
            usage_principal=usage_map[data.usage.usage_principal],
            usage_rdc=usage_map[data.usage.usage_principal],
            charge_toiture_kNm2=data.usage.charge_toiture_kNm2,
        ),
        sol=ParamsSol(
            pression_admissible_MPa=data.sol.pression_admissible_MPa,
            profondeur_fondation_m=data.sol.profondeur_fondation_m,
            presence_nappe=data.sol.presence_nappe,
            description=data.sol.description,
        ),
        localisation=ParamsLocalisation(
            ville=ville_map[data.localisation.ville],
            distance_mer_km=data.localisation.distance_mer_km,
            zone_sismique=data.localisation.zone_sismique,
        ),
    )

def nettoyer_pdf(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/")
def health():
    return {"status": "online", "service": "Tijan AI Engine v2", "version": "2.0.0"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/calculate", response_model=ResultatCompletOutput)
def calculer(data: ProjetInput):
    try:
        from engine_structural import calculer_structure_complete
        from generate_pdf import calculer_score_edge
        projet = input_vers_projet(data)
        resultat = calculer_structure_complete(projet)
        score = calculer_score_edge(projet, resultat)
        score_output = {
            "energie":   {"total_pct": score["energie"]["total_pct"],   "cible_pct": 20, "conforme": score["energie"]["conforme"],   "ecart": score["energie"]["ecart"]},
            "eau":       {"total_pct": score["eau"]["total_pct"],       "cible_pct": 20, "conforme": score["eau"]["conforme"],       "ecart": score["eau"]["ecart"]},
            "materiaux": {"total_pct": score["materiaux"]["total_pct"], "cible_pct": 20, "conforme": score["materiaux"]["conforme"], "ecart": score["materiaux"]["ecart"]},
            "certifiable": score["global"]["certifiable"],
            "statut": score["global"]["statut"],
        }
        return ResultatCompletOutput(
            projet_nom=resultat.projet_nom, statut="success",
            resume=resultat.resume_executif, score_edge=score_output, pdf_disponible=False,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur moteur : {str(e)}")
    finally:
        gc.collect()

@app.post("/generate")
def generer(data: ProjetInput, background_tasks: BackgroundTasks):
    try:
        from engine_structural import calculer_structure_complete
        from generate_pdf import generer_pdf
        projet = input_vers_projet(data)
        resultat = calculer_structure_complete(projet)
        pdf_id = str(uuid.uuid4())
        pdf_path = os.path.join(tempfile.gettempdir(), f"tijan_{pdf_id}.pdf")
        ingenieur = data.ingenieur or "A completer par l'ingenieur responsable"
        generer_pdf(resultat=resultat, projet=projet, output_path=pdf_path, ingenieur=ingenieur)
        background_tasks.add_task(nettoyer_pdf, pdf_path)
        nom_fichier = f"tijan_note_calcul_{projet.nom.replace(' ', '_')[:40]}.pdf"
        return FileResponse(path=pdf_path, media_type="application/pdf", filename=nom_fichier,
            headers={"Content-Disposition": f"attachment; filename={nom_fichier}"})
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur génération PDF : {str(e)}")
    finally:
        gc.collect()

@app.post("/calculate/structure-only")
def calculer_structure(data: ProjetInput):
    try:
        from engine_structural import calculer_structure_complete
        projet = input_vers_projet(data)
        resultat = calculer_structure_complete(projet)
        return {
            "statut": "success", "projet_nom": resultat.projet_nom,
            "beton": {"classe": resultat.beton.classe_exposition.value, "fc28_MPa": resultat.beton.fc28_MPa,
                      "enrobage_mm": resultat.beton.enrobage_mm},
            "poteau_rdc": {"section_cm": f"{int(resultat.poteau.section_b_m*100)}x{int(resultat.poteau.section_h_m*100)}",
                           "ferraillage": f"{resultat.poteau.nb_barres}HA{resultat.poteau.diametre_barres_mm}"},
            "fondations": {"type": resultat.fondations.type_fondation,
                           "diametre_pieux_m": resultat.fondations.diametre_pieux_m,
                           "longueur_pieux_m": resultat.fondations.longueur_pieux_m},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        gc.collect()

@app.post("/calculate/edge-only")
def calculer_edge(data: ProjetInput):
    try:
        from engine_structural import calculer_structure_complete
        from generate_pdf import calculer_score_edge
        projet = input_vers_projet(data)
        resultat = calculer_structure_complete(projet)
        score = calculer_score_edge(projet, resultat)
        return {"statut": "success", "projet_nom": data.nom, "score_edge": score}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        gc.collect()

@app.post("/parse-plans")
async def parse_plans(files: List[UploadFile] = File(...), pression_sol_mpa: float = Form(None)):
    try:
        from parse_plans import parser_plans_architecturaux
        resultat = await parser_plans_architecturaux(
            fichiers=files,
            pression_sol_mpa=pression_sol_mpa
        )
        return resultat
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur parsing : {str(e)}")
    finally:
        gc.collect()

@app.post("/parse-plans/preview")
async def parse_plans_preview(files: List[UploadFile] = File(...)):
    try:
        from parse_plans import parser_plans_architecturaux
        resultat = await parser_plans_architecturaux(fichiers=files)
        return {
            "projet": resultat.get("projet", {}),
            "localisation": {
                "ville": resultat.get("localisation", {}).get("ville"),
                "pays": resultat.get("localisation", {}).get("pays"),
                "zone_sismique": resultat.get("localisation", {}).get("zone_sismique"),
            },
            "geometrie": {
                "nb_niveaux_total": resultat.get("geometrie", {}).get("nb_niveaux_total"),
                "description_niveaux": resultat.get("geometrie", {}).get("description_niveaux"),
                "longueur_m": resultat.get("geometrie", {}).get("longueur_m"),
                "largeur_m": resultat.get("geometrie", {}).get("largeur_m"),
                "surface_emprise_m2": resultat.get("geometrie", {}).get("surface_emprise_m2"),
                "hauteur_etage_m": resultat.get("geometrie", {}).get("hauteur_etage_m"),
            },
            "trame": {
                "portee_max_m": resultat.get("trame_structurelle", {}).get("portee_max_m"),
                "portee_min_m": resultat.get("trame_structurelle", {}).get("portee_min_m"),
                "nb_poteaux_estime": resultat.get("trame_structurelle", {}).get("nb_poteaux_estime"),
                "description": resultat.get("trame_structurelle", {}).get("description_trame"),
            },
            "usage": {
                "type_principal": resultat.get("usage", {}).get("type_principal"),
                "nb_logements": resultat.get("usage", {}).get("nb_logements"),
            },
            "sol": {
                "pression_MPa": resultat.get("parametres_eurocodes", {}).get("sol_pression_admissible_MPa"),
                "type": resultat.get("parametres_eurocodes", {}).get("sol_type"),
                "source": resultat.get("parametres_eurocodes", {}).get("sol_source"),
            },
            "confiance": resultat.get("confiance"),
            "notes": resultat.get("notes_parser"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur preview : {str(e)}")
    finally:
        gc.collect()

@app.post("/generate-ifc")
async def generate_ifc_endpoint(projet: dict):
    try:
        from generate_ifc import generer_ifc
        nom = projet.get("nom", "Tijan_Projet")
        contenu_ifc = generer_ifc(projet, nom)
        return Response(content=contenu_ifc, media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={nom}.ifc"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        gc.collect()

@app.post("/generate-speckle")
async def generate_speckle_endpoint(req: SpeckleRequest):
    try:
        from generate_speckle import envoyer_sur_speckle
        result = envoyer_sur_speckle(
            resultats=req.resultats, nom_projet=req.nom_projet,
            token=req.token, server_url=req.server_url)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        gc.collect()
