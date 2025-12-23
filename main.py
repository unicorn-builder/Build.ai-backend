from fastapi import FastAPI
from models import Projet
from engine import calculer_fondations, estimer_boq
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Pour que Bolt/Lovable puisse parler au backend sans blocage
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/generate")
async def generate_project(projet: Projet):
    fondations = calculer_fondations(projet)
    boq = estimer_boq(projet)
    
    return {
        "structure": {"largeur_semelle_metres": fondations},
        "boq": boq,
        "message": f"Analyse Build.ai terminée pour le projet {projet.nom}"
    }

@app.get("/")
def home():
    return {"status": "Build.ai Backend is Online"}
