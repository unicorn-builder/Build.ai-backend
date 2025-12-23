from pydantic import BaseModel
from typing import List, Optional

class Mur(BaseModel):
    longueur: float
    hauteur: float
    epaisseur: float

class Etage(BaseModel):
    nom: str
    murs: List[Mur]
    points_lumineux: int

class EtudeSol(BaseModel):
    pression_admissible: float # en MPa

class Projet(BaseModel):
    nom: str
    etages: List[Etage]
    sol: EtudeSol
    gamme: str # 'Basic', 'High-end', 'Luxury'
