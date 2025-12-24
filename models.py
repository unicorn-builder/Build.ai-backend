from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Any

class Mur(BaseModel):
    longueur: float = 0
    hauteur: float = 0
    epaisseur: float = 0.2

class Etage(BaseModel):
    nom: str = "Etage"
    murs: List[Mur] = []
    points_lumineux: Any = 0

    @field_validator('points_lumineux', mode='before')
    @classmethod
    def clean_lights(cls, v):
        if isinstance(v, list):
            return sum(item.get('quantite', 1) if isinstance(item, dict) else 1 for item in v)
        try: return int(v)
        except: return 0

class EtudeSol(BaseModel):
    pression_admissible: float = Field(0.1, alias="pression_sol_kpa")

class Projet(BaseModel):
    nom: str = Field("Nouveau Projet", alias="nom_batiment")
    etages: List[Etage] = []
    sol: Optional[Any] = None
    gamme: str = "Basic"

    @field_validator('sol', mode='before')
    @classmethod
    def clean_sol(cls, v):
        if isinstance(v, dict):
            val = v.get('pression_sol_kpa') or v.get('pression_admissible') or 0.1
            return {"pression_admissible": float(val)}
        return {"pression_admissible": 0.1}

    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }
