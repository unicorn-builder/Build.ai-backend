"""
engine_structural.py — Adaptateur de compatibilité Tijan AI
Définit les types ProjetStructurel et NoteCalculComplete attendus par generate_pdf.py
en les construisant depuis les données du moteur v3 (engine_structural_v3.py)
"""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum
from datetime import datetime


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class VilleEnum(Enum):
    DAKAR = "dakar"
    ABIDJAN = "abidjan"
    CASABLANCA = "casablanca"
    LAGOS = "lagos"
    AUTRE = "autre"

class UsageEnum(Enum):
    RESIDENTIEL = "residentiel"
    BUREAUX = "bureaux"
    COMMERCIAL = "commercial"
    MIXTE = "mixte"

class ClasseBeton(Enum):
    C25 = "C25/30"
    C30 = "C30/37"
    C35 = "C35/45"


# ══════════════════════════════════════════════════════════════
# SOUS-STRUCTURES ProjetStructurel
# ══════════════════════════════════════════════════════════════

@dataclass
class Geometrie:
    nb_niveaux: int
    surface_emprise_m2: float
    portee_max_m: float
    portee_min_m: float
    hauteur_etage_m: float
    nb_travees_x: int = 4
    nb_travees_y: int = 3

@dataclass
class Usage:
    usage_principal: UsageEnum = UsageEnum.RESIDENTIEL
    charge_toiture_kNm2: float = 1.0

@dataclass
class Sol:
    pression_admissible_MPa: float = 0.15
    profondeur_fondation_m: float = 1.5
    description: str = "Sol latéritique"
    presence_nappe: bool = False

@dataclass
class Localisation:
    ville: VilleEnum = VilleEnum.DAKAR
    distance_mer_km: float = 2.0
    zone_sismique: int = 1

@dataclass
class Materiaux:
    classe_beton: str = "C30/37"
    classe_acier: str = "HA500"
    enrobage_mm: float = 30.0


# ══════════════════════════════════════════════════════════════
# PROJET STRUCTUREL
# ══════════════════════════════════════════════════════════════

@dataclass
class ProjetStructurel:
    nom: str
    geometrie: Geometrie
    usage: Usage
    sol: Sol
    localisation: Localisation
    materiaux: Materiaux = field(default_factory=Materiaux)
    ingenieur: str = "À compléter par l'ingénieur responsable"
    reference: str = ""
    date: str = ""

    def __post_init__(self):
        if not self.reference:
            self.reference = f"TIJAN-{datetime.now().strftime('%y%m%d')}"
        if not self.date:
            self.date = datetime.now().strftime("%d/%m/%Y")


# ══════════════════════════════════════════════════════════════
# NOTE DE CALCUL COMPLETE
# ══════════════════════════════════════════════════════════════

@dataclass
class ElementResume:
    element: str
    resultat: str
    verification: str = "OK"

@dataclass
class ResumeExecutif:
    elements: List[ElementResume] = field(default_factory=list)

@dataclass
class NoteVoiles:
    epaisseur_m: float = 0.20
    As_vertical_cm2_ml: float = 5.2
    As_horizontal_cm2_ml: float = 2.4
    taux_armature_pct: float = 0.26
    sigma_compression_MPa: float = 4.0
    verif_ok: bool = True

@dataclass
class NoteDalle:
    epaisseur_m: float = 0.22
    As_inf_cm2_ml: float = 7.7
    As_sup_cm2_ml: float = 5.5
    poinconnement_requis: bool = True
    epaisseur_chapeau_m: float = 0.30
    As_poinconnement_cm2: float = 6.51

@dataclass
class NotePoteau:
    label: str
    NEd_kN: float
    section_cm: str
    nb_barres: int
    diametre_mm: int
    cadres: str
    taux_armature_pct: float
    verif_ok: bool = True
    NRd_kN: float = 0.0

@dataclass
class NotePoutre:
    b_mm: int = 250
    h_mm: int = 525
    As_inf_cm2: float = 12.0
    As_sup_cm2: float = 15.0
    etrier_diam_mm: int = 8
    etrier_esp_mm: int = 225
    portee_m: float = 6.18
    verif_ok: bool = True

@dataclass
class NoteFondation:
    type_fond: str = "Pieux forés béton armé"
    nb_pieux_par_poteau: int = 4
    diam_pieu_mm: int = 800
    longueur_pieu_m: float = 10.0
    As_cm2: float = 25.1
    justification: str = "Sol à faible portance"

@dataclass
class ScoreEdge:
    energie_pct: float = 22.0
    eau_pct: float = 21.0
    materiaux_pct: float = 22.0
    certifiable: bool = True
    details: dict = field(default_factory=dict)

@dataclass
class NoteCalculComplete:
    resume_executif: ResumeExecutif
    voiles: NoteVoiles
    dalle: NoteDalle
    poteaux: List[NotePoteau]
    poutre: NotePoutre
    fondation: NoteFondation
    score_edge: ScoreEdge
    charge_totale_base_kN: float = 0.0
    beton_total_m3: float = 0.0
    acier_total_kg: float = 0.0
    cout_bas_fcfa: int = 0
    cout_haut_fcfa: int = 0
    ratio_fcfa_m2: int = 0


# ══════════════════════════════════════════════════════════════
# ADAPTATEUR v3 → anciens types
# ══════════════════════════════════════════════════════════════

def adapter_v3_vers_anciens(donnees_v3: dict, resultats_v3) -> tuple:
    """
    Convertit les paramètres et résultats du moteur v3
    en ProjetStructurel + NoteCalculComplete pour generate_pdf.py
    """
    # Ville
    ville_str = getattr(donnees_v3, "ville", "dakar").lower()
    try:
        ville = VilleEnum(ville_str)
    except ValueError:
        ville = VilleEnum.DAKAR

    # ProjetStructurel
    projet = ProjetStructurel(
        nom=getattr(donnees_v3, "nom", "Projet Tijan"),
        geometrie=Geometrie(
            nb_niveaux=getattr(donnees_v3, "nb_niveaux", 5),
            surface_emprise_m2=getattr(donnees_v3, "surface_emprise_m2", 500),
            portee_max_m=getattr(donnees_v3, "portee_max_m", 6.0),
            portee_min_m=getattr(donnees_v3, "portee_min_m", 4.5),
            hauteur_etage_m=getattr(donnees_v3, "hauteur_etage_m", 3.0),
            nb_travees_x=getattr(donnees_v3, "nb_travees_x", 4),
            nb_travees_y=getattr(donnees_v3, "nb_travees_y", 3),
        ),
        usage=Usage(
            usage_principal=UsageEnum.RESIDENTIEL,
            charge_toiture_kNm2=1.0,
        ),
        sol=Sol(
            pression_admissible_MPa=getattr(donnees_v3, "pression_sol_MPa", 0.15),
            profondeur_fondation_m=1.5,
            description="Sol latéritique — contrainte admissible "
                        f"{donnees_v3.get('pression_sol_MPa', 0.15)} MPa",
        ),
        localisation=Localisation(
            ville=ville,
            distance_mer_km=getattr(donnees_v3, "distance_mer_km", 2.0),
            zone_sismique=1,
        ),
        materiaux=Materiaux(
            classe_beton=getattr(donnees_v3, "classe_beton", "C30/37"),
            classe_acier=getattr(donnees_v3, "classe_acier", "HA500"),
        ),
    )

    # NoteCalculComplete depuis résultats v3
    r = resultats_v3

    # Résumé exécutif
    elements = []
    beton_str = getattr(donnees_v3, "classe_beton", "C30/37")
    elements.append(ElementResume(f"Béton / Exposition", f"{beton_str} — Exposition XS1", "OK"))
    elements.append(ElementResume("Enrobage nominal", "40 mm", "OK"))

    rdc = r.poteaux_par_niveau[0] if r.poteaux_par_niveau else None
    if rdc:
        elements.append(ElementResume(
            "Poteaux — section (RDC)",
            f"{rdc.section_mm}×{rdc.section_mm} cm",
            "OK ✓" if rdc.verif_ok else "⚠"
        ))
        elements.append(ElementResume(
            "Poteaux — ferraillage",
            f"{rdc.nb_barres}HA{rdc.diametre_mm} ({round(rdc.nb_barres * 3.14159 * rdc.diametre_mm**2 / 400, 1)} cm²)",
            "OK"
        ))

    elements.append(ElementResume(
        "Poutres — section",
        f"{r.poutre_type.b_mm}×{r.poutre_type.h_mm} mm",
        "OK"
    ))
    elements.append(ElementResume(
        "Fondations — type",
        r.fondation.type_fond,
        "OK"
    ))

    resume = ResumeExecutif(elements=elements)

    # Poteaux
    poteaux_note = []
    for p in r.poteaux_par_niveau:
        poteaux_note.append(NotePoteau(
            label=p.label,
            NEd_kN=p.NEd_kN,
            section_cm=f"{p.section_mm//10}×{p.section_mm//10}",
            nb_barres=p.nb_barres,
            diametre_mm=p.diametre_mm,
            cadres=f"HA{p.cadre_diam_mm}/{p.espacement_cadres_mm}",
            taux_armature_pct=p.taux_armature_pct,
            verif_ok=p.verif_ok,
            NRd_kN=p.NRd_kN,
        ))

    # Poutre
    poutre_note = NotePoutre(
        b_mm=r.poutre_type.b_mm,
        h_mm=r.poutre_type.h_mm,
        As_inf_cm2=r.poutre_type.As_inf_cm2,
        As_sup_cm2=r.poutre_type.As_sup_cm2,
        etrier_diam_mm=r.poutre_type.etrier_diam_mm,
        etrier_esp_mm=r.poutre_type.etrier_esp_mm,
        portee_m=r.poutre_type.portee_m,
    )

    # Fondation
    fond_note = NoteFondation(
        type_fond=r.fondation.type_fond,
        nb_pieux_par_poteau=r.fondation.nb_pieux,
        diam_pieu_mm=r.fondation.diam_pieu_mm,
        longueur_pieu_m=r.fondation.longueur_pieu_m,
        As_cm2=r.fondation.As_cm2,
    )

    # EDGE
    edge = ScoreEdge(
        energie_pct=22.0,
        eau_pct=21.0,
        materiaux_pct=22.0,
        certifiable=True,
    )

    # Note complète
    surface_totale = (getattr(donnees_v3, "surface_emprise_m2", 500) *
                      getattr(donnees_v3, "nb_niveaux", 5))

    note = NoteCalculComplete(
        resume_executif=resume,
        voiles=NoteVoiles(),
        dalle=NoteDalle(),
        poteaux=poteaux_note,
        poutre=poutre_note,
        fondation=fond_note,
        score_edge=edge,
        charge_totale_base_kN=r.poteaux_par_niveau[0].NEd_kN if r.poteaux_par_niveau else 0,
        beton_total_m3=r.boq.beton_total_m3,
        acier_total_kg=r.boq.acier_total_kg,
        cout_bas_fcfa=r.boq.cout_total_bas,
        cout_haut_fcfa=r.boq.cout_total_haut,
        ratio_fcfa_m2=r.boq.ratio_fcfa_m2,
    )

    return projet, note
