"""
Tijan AI — Backend FastAPI v2
Moteur de calcul structurel Eurocodes + Génération PDF + Score Edge
Remplace l'ancien main.py avec un vrai moteur de calcul
"""
import gc
gc.enable()

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List
import os
import uuid
import tempfile

from engine_structural import (
    ProjetStructurel, ParamsGeometrie, ParamsUsage,
    ParamsSol, ParamsLocalisation,
    UsageBatiment, ZoneVent,
    calculer_structure_complete
)
from generate_pdf import generer_pdf, calculer_score_edge

# ============================================================
# APP
# ============================================================

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
# MODÈLES PYDANTIC — INPUTS
# ============================================================

class GeometrieInput(BaseModel):
    surface_emprise_m2: float = Field(..., gt=0, description="Surface au sol en m²")
    nb_niveaux: int = Field(..., ge=1, le=50, description="Nombre de niveaux hors RDC")
    hauteur_etage_m: float = Field(3.0, ge=2.5, le=6.0, description="Hauteur entre niveaux en m")
    portee_max_m: float = Field(6.0, ge=3.0, le=12.0, description="Portée maximale libre en m")
    nb_voiles_facade: int = Field(4, ge=2, le=20)
    nb_voiles_internes: int = Field(2, ge=0, le=10)
    epaisseur_voile_m: float = Field(0.20, ge=0.15, le=0.50)

class UsageInput(BaseModel):
    usage_principal: str = Field("residentiel", description="residentiel | bureaux | mixte")
    charge_toiture_kNm2: float = Field(1.0, ge=0.5, le=5.0)

    @validator('usage_principal')
    def valider_usage(cls, v):
        valides = ["residentiel", "bureaux", "mixte"]
        if v not in valides:
            raise ValueError(f"Usage doit être parmi : {valides}")
        return v

class SolInput(BaseModel):
    pression_admissible_MPa: float = Field(..., gt=0, le=1.0,
        description="Contrainte admissible en MPa (ex: 0.12)")
    profondeur_fondation_m: float = Field(1.5, ge=0.5, le=10.0)
    presence_nappe: bool = False
    description: str = Field("", description="Description textuelle du sol")

class LocalisationInput(BaseModel):
    ville: str = Field("dakar", description="dakar | abidjan | casablanca | lagos")
    distance_mer_km: float = Field(5.0, ge=0.0, le=500.0)
    zone_sismique: int = Field(1, ge=1, le=3)

    @validator('ville')
    def valider_ville(cls, v):
        valides = ["dakar", "abidjan", "casablanca", "lagos"]
        if v not in valides:
            raise ValueError(f"Ville doit être parmi : {valides}")
        return v

class ProjetInput(BaseModel):
    nom: str = Field(..., min_length=2, max_length=200,
        alias="nom_batiment",
        description="Nom du projet")
    geometrie: GeometrieInput
    usage: UsageInput = UsageInput()
    sol: SolInput
    localisation: LocalisationInput = LocalisationInput()
    ingenieur: str = Field("", description="Nom de l'ingénieur responsable")

    class Config:
        allow_population_by_field_name = True
        extra = "ignore"

# ============================================================
# MODÈLES — OUTPUTS
# ============================================================

class VerificationsOutput(BaseModel):
    flambement_voile: str
    fleche_dalle: str
    poinconnement_dalle: str
    flambement_poteau: str
    cisaillement_poutre: str

class ResumeStructurelOutput(BaseModel):
    beton: str
    enrobage: str
    voile_epaisseur: str
    voile_ferraillage_vertical: str
    dalle_epaisseur: str
    dalle_ferraillage_inf: str
    poteau_section: str
    poteau_ferraillage: str
    poteau_cadres: str
    poutre_section: str
    poutre_ferraillage_inf: str
    poutre_ferraillage_sup: str
    poutre_etriers: str
    fondations_type: str
    fondations_detail: str
    charge_totale_base: str
    verifications: VerificationsOutput

class ScorePilierOutput(BaseModel):
    total_pct: int
    cible_pct: int
    conforme: bool
    ecart: int

class ScoreEdgeOutput(BaseModel):
    energie: ScorePilierOutput
    eau: ScorePilierOutput
    materiaux: ScorePilierOutput
    certifiable: bool
    statut: str

class ResultatCompletOutput(BaseModel):
    projet_nom: str
    statut: str
    resume: dict
    score_edge: dict
    pdf_disponible: bool
    pdf_url: Optional[str] = None


# ============================================================
# UTILITAIRES
# ============================================================

def input_vers_projet(data: ProjetInput) -> ProjetStructurel:
    usage_map = {
        "residentiel": UsageBatiment.RESIDENTIEL,
        "bureaux": UsageBatiment.BUREAUX,
        "mixte": UsageBatiment.MIXTE,
    }
    ville_map = {
        "dakar": ZoneVent.DAKAR,
        "abidjan": ZoneVent.ABIDJAN,
        "casablanca": ZoneVent.CASABLANCA,
        "lagos": ZoneVent.LAGOS,
    }
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

PDF_STORE = {}

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
    return {
        "status": "online",
        "service": "Tijan AI Engine v2",
        "moteur": "Eurocodes EN 1990 / EN 1991 / EN 1992 / EN 1997",
        "version": "2.0.0"
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/calculate", response_model=ResultatCompletOutput)
def calculer(data: ProjetInput):
    try:
        projet = input_vers_projet(data)
        resultat = calculer_structure_complete(projet)
        score = calculer_score_edge(projet, resultat)
        score_output = {
            "energie": {"total_pct": score["energie"]["total_pct"], "cible_pct": 20,
                        "conforme": score["energie"]["conforme"], "ecart": score["energie"]["ecart"]},
            "eau":     {"total_pct": score["eau"]["total_pct"], "cible_pct": 20,
                        "conforme": score["eau"]["conforme"], "ecart": score["eau"]["ecart"]},
            "materiaux":{"total_pct": score["materiaux"]["total_pct"], "cible_pct": 20,
                        "conforme": score["materiaux"]["conforme"], "ecart": score["materiaux"]["ecart"]},
            "certifiable": score["global"]["certifiable"],
            "statut": score["global"]["statut"],
        }
        return ResultatCompletOutput(
            projet_nom=resultat.projet_nom,
            statut="success",
            resume=resultat.resume_executif,
            score_edge=score_output,
            pdf_disponible=False,
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
        projet = input_vers_projet(data)
        resultat = calculer_structure_complete(projet)
        pdf_id = str(uuid.uuid4())
        pdf_path = os.path.join(tempfile.gettempdir(), f"tijan_{pdf_id}.pdf")
        ingenieur = data.ingenieur or "A completer par l'ingenieur responsable"
        generer_pdf(resultat=resultat, projet=projet, output_path=pdf_path, ingenieur=ingenieur)
        background_tasks.add_task(nettoyer_pdf, pdf_path)
        nom_fichier = f"tijan_note_calcul_{projet.nom.replace(' ', '_')[:40]}.pdf"
        return FileResponse(
            path=pdf_path, media_type="application/pdf", filename=nom_fichier,
            headers={"Content-Disposition": f"attachment; filename={nom_fichier}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur génération PDF : {str(e)}")
    finally:
        gc.collect()


@app.post("/calculate/structure-only")
def calculer_structure(data: ProjetInput):
    try:
        projet = input_vers_projet(data)
        resultat = calculer_structure_complete(projet)
        return {
            "statut": "success",
            "projet_nom": resultat.projet_nom,
            "beton": {"classe": resultat.beton.classe_exposition.value, "fc28_MPa": resultat.beton.fc28_MPa,
                      "fcd_MPa": resultat.beton.fcd_MPa, "fyd_MPa": resultat.beton.fyd_MPa,
                      "enrobage_mm": resultat.beton.enrobage_mm},
            "charges": {"G_kNm2": resultat.descente_charges.charge_permanente_G_kNm2,
                        "Q_kNm2": resultat.descente_charges.charge_exploitation_Q_kNm2,
                        "ELU_kNm2": resultat.descente_charges.combinaison_ELU_kNm2,
                        "charge_base_kN": resultat.descente_charges.charge_totale_base_kN},
            "voile": {"epaisseur_cm": int(resultat.voile.epaisseur_retenue_m*100),
                      "As_vertical_cm2_ml": resultat.voile.ferraillage_vertical_cm2_m,
                      "As_horizontal_cm2_ml": resultat.voile.ferraillage_horizontal_cm2_m},
            "dalle": {"epaisseur_cm": int(resultat.dalle.epaisseur_retenue_m*100),
                      "As_inf_cm2_ml": resultat.dalle.ferraillage_inferieur_cm2_m,
                      "As_sup_cm2_ml": resultat.dalle.ferraillage_superieur_cm2_m,
                      "chapeau_requis": resultat.dalle.epaisseur_chapeau_m is not None,
                      "epaisseur_chapeau_cm": int(resultat.dalle.epaisseur_chapeau_m*100) if resultat.dalle.epaisseur_chapeau_m else None},
            "poteau_rdc": {"section_cm": f"{int(resultat.poteau.section_b_m*100)}x{int(resultat.poteau.section_h_m*100)}",
                           "ferraillage": f"{resultat.poteau.nb_barres}HA{resultat.poteau.diametre_barres_mm}",
                           "cadres": f"HA{resultat.poteau.ferraillage_transversal_mm}/{resultat.poteau.espacement_cadres_mm}mm"},
            "poutre": {"section_cm": f"{int(resultat.poutre.largeur_b_m*100)}x{int(resultat.poutre.hauteur_h_m*100)}",
                       "ferraillage_inf": f"{resultat.poutre.nb_barres_inf}HA{resultat.poutre.diametre_barres_mm}",
                       "ferraillage_sup": f"{resultat.poutre.nb_barres_sup}HA{resultat.poutre.diametre_barres_mm}",
                       "etriers": f"HA{resultat.poutre.ferraillage_transversal_mm}/{resultat.poutre.espacement_cadres_mm}mm"},
            "fondations": {"type": resultat.fondations.type_fondation, "justification": resultat.fondations.justification,
                           "largeur_semelle_m": resultat.fondations.largeur_semelle_m,
                           "epaisseur_radier_m": resultat.fondations.epaisseur_radier_m,
                           "diametre_pieux_m": resultat.fondations.diametre_pieux_m,
                           "longueur_pieux_m": resultat.fondations.longueur_pieux_m,
                           "nb_pieux_par_poteau": resultat.fondations.nb_pieux_par_poteau},
            "verifications": resultat.resume_executif.get("verifications", {}),
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur calcul : {str(e)}")
    finally:
        gc.collect()


@app.post("/calculate/edge-only")
def calculer_edge(data: ProjetInput):
    try:
        projet = input_vers_projet(data)
        resultat = calculer_structure_complete(projet)
        score = calculer_score_edge(projet, resultat)
        return {"statut": "success", "projet_nom": data.nom, "score_edge": score}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        gc.collect()


from fastapi import UploadFile, File, Form
import shutil
from parse_plans import parser_plans_architecte

@app.post("/parse-plans")
async def parse_plans(
    files: List[UploadFile] = File(...),
    pression_sol_mpa: float = Form(0.12),
):
    tmp_paths = []
    try:
        for f in files:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            shutil.copyfileobj(f.file, tmp)
            tmp.close()
            tmp_paths.append(tmp.name)
        resultat = parser_plans_architecte(tmp_paths, pression_sol_mpa)
        return {"statut": "success", "data": resultat}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur parsing : {str(e)}")
    finally:
        for p in tmp_paths:
            try: os.remove(p)
            except: pass
        gc.collect()


from generate_ifc import generer_ifc
from fastapi.responses import Response

@app.post("/generate-ifc")
async def generate_ifc_endpoint(projet: dict):
    try:
        nom = projet.get("nom", "Tijan_Projet")
        contenu_ifc = generer_ifc(projet, nom)
        return Response(
            content=contenu_ifc,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={nom}.ifc"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        gc.collect()


from generate_speckle import envoyer_sur_speckle

class SpeckleRequest(BaseModel):
    resultats: dict
    nom_projet: str = "Projet Tijan AI"
    token: str = None
    server_url: str = None

@app.post("/generate-speckle")
async def generate_speckle_endpoint(req: SpeckleRequest):
    try:
        result = envoyer_sur_speckle(
            resultats=req.resultats,
            nom_projet=req.nom_projet,
            token=req.token,
            server_url=req.server_url
        )
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        gc.collect()
