from pydantic import BaseModel, Field, validator
from typing import List, Optional, Any

class Mur(BaseModel):
    longueur: float = 0
    hauteur: float = 0
    epaisseur: float = 0.2

class Etage(BaseModel):
    nom: str = "Etage"
    murs: List[Mur] = []
    points_lumineux: Any = 0

    @validator('points_lumineux', pre=True, always=True)
    def clean_lights(cls, v):
        if isinstance(v, list):
            total = 0
            for item in v:
                if isinstance(item, dict):
                    total += item.get('quantite', 1)
                else:
                    total += 1
            return total
        try: return int(v)
        except: return 0

class EtudeSol(BaseModel):
    pression_admissible: float = Field(0.1, alias="pression_sol_kpa")

class Projet(BaseModel):
    nom: str = Field("Nouveau Projet", alias="nom_batiment")
    etages: List[Etage] = []
    sol: Optional[Any] = None
    gamme: str = "Basic"

    @validator('sol', pre=True, always=True)
    def clean_sol(cls, v):
        if isinstance(v, dict):
            val = v.get('pression_sol_kpa') or v.get('pression_admissible') or 0.1
            return {"pression_admissible": float(val)}
        return {"pression_admissible": 0.1}

    class Config:
        allow_population_by_field_name = True
        extra = "ignore"
