from pydantic import BaseModel, Field
from typing import List, Optional

class Mur(BaseModel):
    longueur: float
    hauteur: float
    epaisseur: float = 0.2  # Valeur par défaut si Lovable l'oublie

class Etage(BaseModel):
    nom: str
    murs: List[Mur]
    points_lumineux: int = 0

class EtudeSol(BaseModel):
    pression_admissible: float = Field(..., alias="pression_sol_kpa") # Accepte le nom envoyé par Lovable

class Projet(BaseModel):
    nom: str = Field(..., alias="nom_batiment") # Accepte le nom envoyé par Lovable
    etages: List[Etage]
    sol: Optional[EtudeSol] = None
    gamme: str = "Basic"
    
    class Config:
        populate_by_name = True # Permet d'utiliser à la fois les anciens et nouveaux noms
