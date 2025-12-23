from fastapi import FastAPI
from models import Projet
from engine import calculer_fondations, recuperer_boq_supabase, generer_synthese_ia
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/generate")
async def generate_project(projet: Projet):
    # 1. Calcul technique
    fondations = calculer_fondations(projet)
    
    # 2. Récupération des données réelles Supabase
    equipements = recuperer_boq_supabase(projet.gamme)
    
    # 3. Génération de la note par Gemini
    note_ia = generer_synthese_ia(projet, fondations, equipements)
    
    return {
        "projet_nom": projet.nom,
        "structure": {"largeur_semelle_m": fondations},
        "boq_reel": equipements,
        "note_ingenieur": note_ia
    }

@app.get("/")
def home():
    return {"status": "Build.ai Engine v2 (AI + DB) is Online"}
