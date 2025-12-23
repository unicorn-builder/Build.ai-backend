from pydantic import BaseModel, Field, validator
from typing import List, Optional, Any

class Mur(BaseModel):
    longueur: float = 0
    hauteur: float = 0
    epaisseur: float = 0.2

class Etage(BaseModel):
    nom: str = "Etage"
    murs: List[Mur] = []
    # Any permet d'accepter une liste de lampes ou un chiffre
    points_lumineux: Any = 0

    @validator('points_lumineux', pre=True, always=True)
    def clean_lights(cls, v):
        # Si Lovable envoie une liste d'objets (lampes), on additionne les quantités
        if isinstance(v, list):
            total = 0
            for item in v:
                if isinstance(item, dict):
                    total += item.get('quantite', 1)
            return total
        # Si c'est déjà un chiffre, on le garde
        try: return int(v)
        except: return 0

class EtudeSol(BaseModel):
    # On accepte 'pression_admissible' OU 'pression_sol_kpa'
    pression_admissible: float = Field(0.1, alias="pression_sol_kpa")

class Projet(BaseModel):
    # On accepte 'nom' OU 'nom_batiment'
    nom: str = Field("Nouveau Projet", alias="nom_batiment")
    etages: List[Etage] = []
    # On rend l'objet sol robuste aux données manquantes
    sol: Optional[Any] = None
    gamme: str = "Basic"

    @validator('sol', pre=True, always=True)
    def clean_sol(cls, v):
        if isinstance(v, dict):
            # Si Lovable envoie {'pression_sol_kpa': 150}
            val = v.get('pression_sol_kpa') or v.get('pression_admissible') or 0.1
            return {"pression_admissible": float(val)}
        return {"pression_admissible": 0.1}

    class Config:
        # Autorise l'utilisation des alias (nom_batiment -> nom)
        populate_by_name = True
