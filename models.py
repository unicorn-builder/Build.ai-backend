from pydantic import BaseModel, Field, validator
from typing import List, Optional, Any

class Mur(BaseModel):
    longueur: float
    hauteur: float
    epaisseur: float = 0.2

class Etage(BaseModel):
    nom: str
    murs: List[Mur]
    # On accepte n'importe quel type pour points_lumineux et on le convertit en nombre
    points_lumineux: Any = 0

    @validator('points_lumineux', pre=True, always=True)
    def decode_points(cls, v):
        if isinstance(v, list): return len(v) # Si c'est une liste d'objets, on compte le nombre
        try: return int(v)
        except: return 0

class EtudeSol(BaseModel):
    pression_admissible: float = Field(0.1, alias="pression_sol_kpa")

class Projet(BaseModel):
    # Accepte 'nom' OU 'nom_batiment'
    nom: str = Field(..., alias="nom_batiment")
    etages: List[Etage]
    # Rend 'sol' optionnel pour éviter le crash si Lovable l'oublie
    sol: Optional[EtudeSol] = Field(default_factory=lambda: EtudeSol(pression_sol_kpa=150))
    gamme: str = "Basic"
    
    class Config:
        allow_population_by_field_name = True
        antialiasing = True
