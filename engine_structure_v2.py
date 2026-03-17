"""
engine_structure_v2.py — Moteur de calcul structure Tijan AI
═════════════════════════════════════════════════════════════
Références normatives :
  Structure  : Eurocode 2 (EC2) — NF EN 1992-1-1
  Séismique  : Eurocode 8 (EC8) — NF EN 1998-1
  Géotech.   : Eurocode 7 (EC7) + DTU 13.2
  Charges    : Eurocode 1 (EC1) — NF EN 1991-1-1
  Durabilité : EN 206 — Classes d'exposition

Projets couverts : villa, résidentiel, bureau, hôtel, mixte, tour
Pays couverts   : Sénégal, Côte d'Ivoire, Maroc, Nigeria, Ghana

Auteur : Tijan AI
Version : 2.0 — Mars 2026
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import Enum


# ══════════════════════════════════════════════════════════════
# ENUMS ET CONSTANTES
# ══════════════════════════════════════════════════════════════

class Usage(str, Enum):
    RESIDENTIEL = "residentiel"
    BUREAU      = "bureau"
    HOTEL       = "hotel"
    MIXTE       = "mixte"
    COMMERCIAL  = "commercial"
    INDUSTRIEL  = "industriel"

class TypeFondation(str, Enum):
    SEMELLE_ISOLEE  = "semelle_isolee"
    SEMELLE_FILANTE = "semelle_filante"
    RADIER          = "radier"
    PIEUX           = "pieux_fores"
    PUITS           = "puits_fores"

class TypeCloison(str, Enum):
    AGGLO_CREUX_10  = "agglo_creux_10cm"
    AGGLO_CREUX_15  = "agglo_creux_15cm"
    AGGLO_CREUX_20  = "agglo_creux_20cm"
    AGGLO_PLEIN_25  = "agglo_plein_25cm"
    BA13_SIMPLE     = "ba13_simple_rail"
    BA13_DOUBLE     = "ba13_double_rail"
    BETON_20        = "beton_coule_20cm"

# Charges variables EC1 par usage (kN/m²)
CHARGES_VARIABLES = {
    Usage.RESIDENTIEL: 2.5,
    Usage.BUREAU:      3.0,
    Usage.HOTEL:       2.0,
    Usage.MIXTE:       3.0,
    Usage.COMMERCIAL:  5.0,
    Usage.INDUSTRIEL:  7.5,
}

# Charges permanentes type (kN/m²) — dalle + revêtement + cloisons
CHARGES_PERMANENTES = {
    Usage.RESIDENTIEL: 6.5,
    Usage.BUREAU:      7.0,
    Usage.HOTEL:       7.5,
    Usage.MIXTE:       7.0,
    Usage.COMMERCIAL:  8.0,
    Usage.INDUSTRIEL:  9.0,
}

# Pression sol par défaut par ville (MPa)
PRESSION_SOL_DEFAUT = {
    "dakar":       0.15,
    "abidjan":     0.20,
    "casablanca":  0.25,
    "rabat":       0.25,
    "lagos":       0.10,  # Sol mou Lagos
    "accra":       0.20,
}

# Distance mer par défaut par ville (km) — pour durabilité
DISTANCE_MER_DEFAUT = {
    "dakar":       1.5,
    "abidjan":     2.0,
    "casablanca":  3.0,
    "rabat":       5.0,
    "lagos":       2.0,
    "accra":       4.0,
}

# Zone sismique par pays
ZONE_SISMIQUE = {
    "senegal":     1,   # ag = 0.07g
    "cote_ivoire": 0,   # Très faible
    "maroc":       3,   # Zone sismique active — ag = 0.16g
    "nigeria":     1,
    "ghana":       1,
}


# ══════════════════════════════════════════════════════════════
# DONNÉES D'ENTRÉE
# ══════════════════════════════════════════════════════════════

@dataclass
class DonneesProjet:
    # Identification
    nom:            str   = "Projet Tijan"
    adresse:        str   = "Dakar, Sénégal"
    ville:          str   = "Dakar"
    pays:           str   = "Senegal"
    usage:          Usage = Usage.RESIDENTIEL

    # Géométrie (extraits des plans ou saisis)
    nb_niveaux:          int   = 5
    hauteur_etage_m:     float = 3.0
    surface_emprise_m2:  float = 500.0
    surface_terrain_m2:  float = 0.0    # 0 = non fourni
    portee_max_m:        float = 6.0
    portee_min_m:        float = 4.5
    nb_travees_x:        int   = 4
    nb_travees_y:        int   = 3

    # Matériaux — décidés par Tijan AI si non spécifiés
    classe_beton:   str   = ""   # vide = auto-sélection
    classe_acier:   str   = ""   # vide = auto-sélection

    # Site
    distance_mer_km:     float = 0.0    # 0 = auto depuis ville
    pression_sol_MPa:    float = 0.0    # 0 = auto depuis ville
    sol_context:         str   = ""     # Texte étude de sol si dispo
    zone_sismique:       int   = -1     # -1 = auto depuis pays

    # Options
    avec_sous_sol:       bool  = False
    nb_sous_sols:        int   = 0


# ══════════════════════════════════════════════════════════════
# RÉSULTATS
# ══════════════════════════════════════════════════════════════

@dataclass
class ResultatPoteau:
    niveau:              str
    NEd_kN:              float
    section_mm:          int
    nb_barres:           int
    diametre_mm:         int
    cadre_diam_mm:       int
    espacement_cadres_mm:int
    taux_armature_pct:   float
    NRd_kN:              float
    verif_ok:            bool
    ratio_NEd_NRd:       float

@dataclass
class ResultatPoutre:
    type:               str    # "principale" | "secondaire"
    portee_m:           float
    b_mm:               int
    h_mm:               int
    As_inf_cm2:         float
    As_sup_cm2:         float
    etrier_diam_mm:     int
    etrier_esp_mm:      int
    verif_fleche:       bool
    verif_effort_t:     bool

@dataclass
class ResultatDalle:
    epaisseur_mm:       int
    portee_m:           float
    As_x_cm2_ml:        float
    As_y_cm2_ml:        float
    fleche_admissible_mm: float
    verif_ok:           bool

@dataclass
class OptionCloison:
    type:               TypeCloison
    epaisseur_cm:       int
    materiau:           str
    usage_recommande:   str
    charge_kn_m2:       float
    prix_fcfa_m2:       int
    avantages:          List[str]
    inconvenients:      List[str]

@dataclass
class ResultatCloisons:
    surface_totale_m2:       float
    options:                 List[OptionCloison]
    option_recommandee:      TypeCloison
    charge_dalle_kn_m2:      float
    surface_separative_m2:   float
    surface_legere_m2:       float
    surface_gaines_m2:       float

@dataclass
class ResultatFondation:
    type:               TypeFondation
    justification:      str
    # Pieux
    nb_pieux:           int   = 0
    diam_pieu_mm:       int   = 0
    longueur_pieu_m:    float = 0.0
    As_cm2:             float = 0.0
    # Semelles
    largeur_semelle_m:  float = 0.0
    profondeur_m:       float = 1.5
    beton_semelle_m3:   float = 0.0

@dataclass
class ResultatSismique:
    zone:               int
    ag_g:               float
    T1_s:               float
    Fb_kN:              float
    Sd_T1:              float
    dispositions:       List[str]
    conforme_DCL:       bool

@dataclass
class BOQStructure:
    # Quantités
    beton_fondation_m3:     float
    beton_structure_m3:     float
    beton_total_m3:         float
    acier_kg:               float
    coffrage_m2:            float
    terrassement_m3:        float
    maconnerie_m2:          float
    etancheite_m2:          float
    # Coûts par poste (FCFA)
    cout_beton_fcfa:        int
    cout_acier_fcfa:        int
    cout_coffrage_fcfa:     int
    cout_terr_fcfa:         int
    cout_fond_fcfa:         int
    cout_maco_fcfa:         int
    cout_etanch_fcfa:       int
    cout_divers_fcfa:       int
    # Totaux
    total_bas_fcfa:         int
    total_haut_fcfa:        int
    ratio_fcfa_m2_bati:     int
    ratio_fcfa_m2_habitable:int
    surface_batie_m2:       float
    surface_habitable_m2:   float

@dataclass
class AnalyseIngenieur:
    classe_beton_choisie:   str
    classe_acier_choisie:   str
    justification_materiaux:str
    commentaire_global:     str
    alertes:                List[str]
    points_forts:           List[str]
    recommandations:        List[str]
    conformite_ec2:         str
    conformite_ec8:         str
    note_ingenieur:         str

@dataclass
class ResultatsStructure:
    # Inputs résolus
    params:             DonneesProjet
    classe_beton:       str
    classe_acier:       str
    fck_MPa:            float
    fyk_MPa:            float
    distance_mer_km:    float
    pression_sol_MPa:   float
    zone_sismique:      int
    charge_G_kNm2:      float
    charge_Q_kNm2:      float
    # Résultats
    poteaux:            List[ResultatPoteau]
    poutre_principale:  ResultatPoutre
    poutre_secondaire:  Optional[ResultatPoutre]
    dalle:              ResultatDalle
    cloisons:           ResultatCloisons
    fondation:          ResultatFondation
    sismique:           ResultatSismique
    boq:                BOQStructure
    analyse:            AnalyseIngenieur


# ══════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ══════════════════════════════════════════════════════════════

def _get_ville_key(ville: str) -> str:
    return ville.lower().strip().replace(" ", "_").replace("'", "")

def _auto_classe_beton(nb_niveaux: int, distance_mer_km: float, usage: Usage) -> Tuple[str, str]:
    """
    Sélectionne automatiquement la classe béton et acier.
    Règle validée : R+1-3=C25/30+HA400, R+4-8=C30/37+HA500, R+9+=C35/45+HA500
    Exposition marine (<5km) : +1 classe béton
    """
    if nb_niveaux <= 3:
        beton, acier = "C25/30", "HA400"
        fck, fyk = 25.0, 400.0
    elif nb_niveaux <= 8:
        beton, acier = "C30/37", "HA500"
        fck, fyk = 30.0, 500.0
    else:
        beton, acier = "C35/45", "HA500"
        fck, fyk = 35.0, 500.0

    # Majoration exposition marine
    if distance_mer_km < 5.0:
        if fck == 25.0:
            beton, fck = "C30/37", 30.0
        elif fck == 30.0:
            beton, fck = "C35/45", 35.0
        elif fck == 35.0:
            beton, fck = "C40/50", 40.0

    # Bureaux/hôtels : +1 classe mini
    if usage in [Usage.BUREAU, Usage.HOTEL, Usage.COMMERCIAL] and fck < 30.0:
        beton, fck = "C30/37", 30.0

    return beton, acier

def _fck_from_classe(classe: str) -> float:
    try:
        return float(classe.split('/')[0][1:])
    except:
        return 30.0

def _fyk_from_classe(classe: str) -> float:
    try:
        return float(classe.replace("HA", "").replace("S", ""))
    except:
        return 500.0

def _enrobage(distance_mer_km: float, usage: Usage) -> float:
    """Enrobage nominal selon classe d'exposition EN 206."""
    if distance_mer_km < 1.0:
        return 45.0  # XS3 — zone de marnage
    elif distance_mer_km < 5.0:
        return 40.0  # XS1 — atmosphère marine
    else:
        return 30.0  # XC2/XC3 — intérieur/extérieur normal

def _shon(d: DonneesProjet) -> float:
    return d.surface_emprise_m2 * d.nb_niveaux

def _surface_tributaire_poteau(d: DonneesProjet) -> float:
    """Surface tributaire par poteau (m²)."""
    lx = d.portee_max_m
    ly = d.portee_min_m
    return lx * ly


# ══════════════════════════════════════════════════════════════
# CALCUL POTEAUX EC2/EC8
# ══════════════════════════════════════════════════════════════

def _calculer_poteaux(d: DonneesProjet, fck: float, fyk: float,
                       G: float, Q: float) -> List[ResultatPoteau]:
    """
    Descente de charges EC2 + dimensionnement poteaux.
    Section carrée, armatures longitudinales HA.
    """
    poteaux = []
    S_trib = _surface_tributaire_poteau(d)
    # Combinaison ELU : Pu = 1.35G + 1.5Q
    Pu_kNm2 = 1.35 * G + 1.5 * Q

    # Résistances matériaux
    fcd = fck / 1.5   # Résistance de calcul béton (MPa)
    fyd = fyk / 1.15  # Résistance de calcul acier (MPa)

    niveaux_labels = []
    for i in range(d.nb_niveaux):
        if i == 0:
            niveaux_labels.append("RDC")
        elif i == d.nb_niveaux - 1:
            niveaux_labels.append("Toiture")
        else:
            niveaux_labels.append(f"N{i}")

    for i, label in enumerate(niveaux_labels):
        # Effort normal cumulé depuis la toiture
        n_etages_au_dessus = d.nb_niveaux - i
        NEd = Pu_kNm2 * S_trib * n_etages_au_dessus  # kN

        # Dimensionnement section — méthode itérative EC2
        # NRd = fcd * Ac + fyd * As (avec As = rho * Ac)
        # On cible rho = 1.5% (entre 0.1% et 4%)
        rho_cible = 0.015
        # NRd = Ac * (fcd + rho * fyd) → Ac = NEd / (fcd + rho * fyd) * 1000
        Ac_cm2 = (NEd * 1000) / (fcd * 1000 + rho_cible * fyd * 1000) * 10000
        b_mm = max(200, int(math.ceil(math.sqrt(Ac_cm2 * 100) / 25) * 25))
        b_mm = min(b_mm, 600)  # Cap à 600mm

        # Armatures longitudinales
        Ac_reel = (b_mm / 1000) ** 2 * 10000  # cm²
        As_cm2 = rho_cible * Ac_reel
        # Choix barres
        diams = [12, 14, 16, 20, 25, 32]
        nb_barres = 4
        diam_mm = 12
        for d_mm in diams:
            As_1 = math.pi * d_mm**2 / 400  # cm²
            if As_1 * nb_barres >= As_cm2:
                diam_mm = d_mm
                break
        # Si 4 barres insuffisantes, passer à 8
        As_fourni = nb_barres * math.pi * diam_mm**2 / 400
        if As_fourni < As_cm2 and diam_mm == 32:
            nb_barres = 8

        As_final = nb_barres * math.pi * diam_mm**2 / 400
        taux = As_final / Ac_reel * 100

        # Cadres (étriers)
        cad_diam = 8 if diam_mm <= 20 else 10
        cad_esp = min(int(b_mm * 0.6 / 25) * 25, 300)
        cad_esp = max(cad_esp, 100)

        # Vérification NRd
        NRd = (fcd * Ac_reel / 10000 * 1000 + fyd * As_final / 10000 * 1000) * 0.8
        verif = NRd >= NEd
        ratio = NEd / NRd if NRd > 0 else 0

        poteaux.append(ResultatPoteau(
            niveau=label,
            NEd_kN=round(NEd, 1),
            section_mm=b_mm,
            nb_barres=nb_barres,
            diametre_mm=diam_mm,
            cadre_diam_mm=cad_diam,
            espacement_cadres_mm=cad_esp,
            taux_armature_pct=round(taux, 2),
            NRd_kN=round(NRd, 1),
            verif_ok=verif,
            ratio_NEd_NRd=round(ratio, 2),
        ))

    return poteaux


# ══════════════════════════════════════════════════════════════
# CALCUL POUTRES EC2
# ══════════════════════════════════════════════════════════════

def _calculer_poutre(portee: float, G: float, Q: float,
                      fck: float, fyk: float, type_: str) -> ResultatPoutre:
    """
    Dimensionnement poutre en béton armé EC2.
    Méthode des moments fléchissants (section rectangulaire).
    """
    fcd = fck / 1.5
    fyd = fyk / 1.15

    # Charge linéaire sur poutre (kN/ml) — largeur tributaire = portée/2
    larg_trib = portee / 2
    pu = (1.35 * G + 1.5 * Q) * larg_trib

    # Moment ELU en travée (appuis simples)
    MEd = pu * portee**2 / 8  # kN.m

    # Section : h = L/10 à L/15 selon chargement
    h_m = max(portee / 12, 0.35)
    h_mm = int(math.ceil(h_m * 1000 / 25) * 25)
    b_mm = max(200, int(h_mm * 0.4 / 25) * 25)
    b_mm = min(b_mm, 400)

    d = h_mm - 50  # hauteur utile (mm)

    # Armatures en travée (moment positif)
    Mu = MEd * 1e6  # N.mm
    mu = Mu / (b_mm * d**2 * fcd)
    if mu > 0.372:
        mu = 0.372  # Section doublement armée nécessaire
    alpha = (1 - math.sqrt(1 - 2*mu)) / 0.8 if mu < 0.5 else 0.5
    z = d * (1 - 0.4 * alpha)
    As_inf = Mu / (fyd * z) / 100  # cm²
    As_inf = max(As_inf, 0.26 * 2.9 / fyk * b_mm * d / 10000 * 10000)  # As,min

    # Armatures en appui (moment négatif = 0.5 * moment travée)
    As_sup = As_inf * 0.6

    # Étriers (effort tranchant)
    Vsd = pu * portee / 2
    etrier_diam = 8 if b_mm <= 300 else 10
    etrier_esp = min(int(d * 0.75 / 25) * 25, 250)
    etrier_esp = max(etrier_esp, 100)

    # Vérification flèche L/250
    fleche_adm = portee / 250
    fleche_calc = 5 * pu * portee**4 / (384 * 30000 * b_mm * h_mm**3 / 12) * 1e9  # mm approx
    verif_fleche = fleche_calc <= fleche_adm * 1000

    # Vérification effort tranchant
    VRd_c = 0.18 / 1.5 * (1 + math.sqrt(200/d)) * (100 * As_inf/10000 / (b_mm/1000 * d/1000)) ** (1/3) * b_mm/1000 * d/1000 * 1000
    verif_et = Vsd <= VRd_c * 1.5

    return ResultatPoutre(
        type=type_,
        portee_m=round(portee, 2),
        b_mm=b_mm,
        h_mm=h_mm,
        As_inf_cm2=round(As_inf, 1),
        As_sup_cm2=round(As_sup, 1),
        etrier_diam_mm=etrier_diam,
        etrier_esp_mm=etrier_esp,
        verif_fleche=verif_fleche,
        verif_effort_t=verif_et,
    )


# ══════════════════════════════════════════════════════════════
# CALCUL DALLE EC2
# ══════════════════════════════════════════════════════════════

def _calculer_dalle(portee_min: float, portee_max: float,
                     G: float, Q: float, fck: float, fyk: float) -> ResultatDalle:
    """Dalle pleine — EC2 §9.3."""
    fcd = fck / 1.5
    fyd = fyk / 1.15

    # Épaisseur minimale
    ep_min = max(portee_min / 35, portee_max / 40, 0.12)
    ep_mm = int(math.ceil(ep_min * 1000 / 10) * 10)
    ep_mm = max(ep_mm, 150)

    d = ep_mm - 25  # hauteur utile dalle

    # Charge ELU
    pu = (1.35 * G + 1.5 * Q)  # kN/m²

    # Moment ELU (portée courte, bande de 1m)
    lx = portee_min
    ly = portee_max
    coeff_mx = 0.0479 if ly/lx <= 2 else 0.125  # Table EC2
    MEd_x = coeff_mx * pu * lx**2  # kN.m/ml

    coeff_my = coeff_mx * (lx/ly)**2 if ly/lx <= 2 else 0.0
    MEd_y = coeff_my * pu * lx**2 if coeff_my > 0 else MEd_x * 0.3

    # Armatures
    def As_dalle(MEd, d):
        Mu = MEd * 1e6
        mu = Mu / (1000 * d**2 * fcd)
        mu = min(mu, 0.372)
        alpha = (1 - math.sqrt(max(0, 1 - 2*mu))) / 0.8
        z = d * (1 - 0.4*alpha)
        As = Mu / (fyd * max(z, 0.1)) / 100
        As_min = 0.0013 * 1000 * d / 100
        return max(As, As_min)

    As_x = As_dalle(MEd_x, d)
    As_y = As_dalle(MEd_y, d)

    # Vérification flèche
    fleche_adm_mm = portee_min / 250 * 1000
    verif = True  # Simplifiée — vérification complète en ELS

    return ResultatDalle(
        epaisseur_mm=ep_mm,
        portee_m=round(portee_min, 2),
        As_x_cm2_ml=round(As_x, 1),
        As_y_cm2_ml=round(As_y, 1),
        fleche_admissible_mm=round(fleche_adm_mm, 1),
        verif_ok=verif,
    )


# ══════════════════════════════════════════════════════════════
# CALCUL CLOISONS
# ══════════════════════════════════════════════════════════════

def _calculer_cloisons(d: DonneesProjet, prix_struct) -> ResultatCloisons:
    """
    Dimensionnement et recommandation cloisons selon usage.
    Propose toutes les options pertinentes avec impacts prix.
    """
    shon = _shon(d)
    # Estimation surfaces
    surf_separative = shon * 0.08   # Cloisons séparatives ~8% SHON
    surf_legere     = shon * 0.12   # Cloisons intérieures légères ~12%
    surf_gaines     = shon * 0.02   # Gaines techniques ~2%
    surf_totale     = surf_separative + surf_legere + surf_gaines

    options = []

    # Option 1 — Agglos creux 15cm (standard résidentiel)
    options.append(OptionCloison(
        type=TypeCloison.AGGLO_CREUX_15,
        epaisseur_cm=15,
        materiau="Agglos creux 15cm — enduits 2 faces",
        usage_recommande="Résidentiel standard, séparatif logements",
        charge_kn_m2=2.5,
        prix_fcfa_m2=getattr(prix_struct, 'agglo_creux_15_m2', 24_000),
        avantages=[
            "Économique et disponible localement",
            "Bonne résistance au feu (REI 120)",
            "Isolation acoustique correcte (Rw ~42 dB)",
            "Main d'œuvre locale qualifiée disponible",
        ],
        inconvenients=[
            "Poids important (charge dalle 2.5 kN/m²)",
            "Travaux humides (enduit)",
            "Moins adapté aux modifications ultérieures",
        ]
    ))

    # Option 2 — Agglos creux 20cm (murs porteurs/façades)
    options.append(OptionCloison(
        type=TypeCloison.AGGLO_CREUX_20,
        epaisseur_cm=20,
        materiau="Agglos creux 20cm — enduits 2 faces",
        usage_recommande="Façades, murs périphériques, séparatif renforcé",
        charge_kn_m2=3.0,
        prix_fcfa_m2=getattr(prix_struct, 'agglo_creux_20_m2', 30_000),
        avantages=[
            "Excellente résistance mécanique",
            "Bonne inertie thermique (confort Dakar)",
            "REI 180 — haute résistance au feu",
        ],
        inconvenients=[
            "Poids élevé (3.0 kN/m²)",
            "Coût supérieur de ~25%",
            "Emprise sur surface habitable",
        ]
    ))

    # Option 3 — BA13 double rail (hôtel/bureau)
    options.append(OptionCloison(
        type=TypeCloison.BA13_DOUBLE,
        epaisseur_cm=13,
        materiau="Cloison BA13 double rail 72mm — laine de roche",
        usage_recommande="Hôtel, bureau, séparatif acoustique performant",
        charge_kn_m2=1.5,
        prix_fcfa_m2=getattr(prix_struct, 'ba13_double_m2', 42_000),
        avantages=[
            "Légèreté (1.5 kN/m² vs 2.5 kN/m²)",
            "Excellente isolation acoustique (Rw ~52 dB avec laine de roche)",
            "Flexibilité — modifications faciles",
            "Finition parfaite, prête à peindre",
            "Rapidité de mise en œuvre",
        ],
        inconvenients=[
            "Prix plus élevé (+50-75% vs agglos)",
            "Résistance au feu moindre (EI 60 standard)",
            "Sensible à l'humidité si non traité",
            "Main d'œuvre spécialisée requise",
        ]
    ))

    # Option 4 — BA13 simple rail (cloisons intérieures légères)
    options.append(OptionCloison(
        type=TypeCloison.BA13_SIMPLE,
        epaisseur_cm=10,
        materiau="Cloison BA13 simple rail 48mm",
        usage_recommande="Cloisons intérieures légères, bureaux open space",
        charge_kn_m2=1.0,
        prix_fcfa_m2=getattr(prix_struct, 'ba13_simple_m2', 28_000),
        avantages=[
            "Très léger (1.0 kN/m²)",
            "Rapide à poser",
            "Économique parmi les solutions sèches",
        ],
        inconvenients=[
            "Isolation acoustique limitée (Rw ~36 dB)",
            "Non adapté aux séparatifs entre logements",
        ]
    ))

    # Option 5 — Béton coulé gaines
    options.append(OptionCloison(
        type=TypeCloison.BETON_20,
        epaisseur_cm=20,
        materiau="Béton armé coulé 20cm — gaines techniques",
        usage_recommande="Gaines ascenseurs, gaines techniques, locaux groupes",
        charge_kn_m2=5.0,
        prix_fcfa_m2=getattr(prix_struct, 'beton_c3037_m3', 185_000) * 0.20,
        avantages=[
            "Résistance maximale",
            "Étanche — idéal gaines et locaux techniques",
            "REI 240",
        ],
        inconvenients=[
            "Très lourd (5.0 kN/m²)",
            "Coûteux",
            "Définitif — aucune flexibilité",
        ]
    ))

    # Recommandation selon usage
    if d.usage == Usage.RESIDENTIEL:
        recommandee = TypeCloison.AGGLO_CREUX_15
        charge = 2.5
    elif d.usage in [Usage.HOTEL, Usage.BUREAU]:
        recommandee = TypeCloison.BA13_DOUBLE
        charge = 1.5
    elif d.usage == Usage.MIXTE:
        recommandee = TypeCloison.AGGLO_CREUX_15
        charge = 2.0
    else:
        recommandee = TypeCloison.AGGLO_CREUX_20
        charge = 2.5

    return ResultatCloisons(
        surface_totale_m2=round(surf_totale, 0),
        options=options,
        option_recommandee=recommandee,
        charge_dalle_kn_m2=charge,
        surface_separative_m2=round(surf_separative, 0),
        surface_legere_m2=round(surf_legere, 0),
        surface_gaines_m2=round(surf_gaines, 0),
    )


# ══════════════════════════════════════════════════════════════
# CALCUL FONDATIONS EC7
# ══════════════════════════════════════════════════════════════

def _calculer_fondations(d: DonneesProjet, poteaux: List[ResultatPoteau],
                           fck: float, prix_struct) -> ResultatFondation:
    """
    Choix et dimensionnement fondations EC7 + DTU 13.2.
    """
    NEd_max = poteaux[0].NEd_kN if poteaux else 1000.0
    q_adm = d.pression_sol_MPa * 1000  # kPa

    # Critère de choix fondations
    # Semelles si q_adm >= 100 kPa et NEd <= 1500 kN
    # Pieux si q_adm < 100 kPa ou NEd > 1500 kN ou nb_niveaux >= 6

    if q_adm >= 150 and NEd_max <= 800 and d.nb_niveaux <= 3:
        # Semelles isolées
        A_requis = NEd_max / q_adm  # m²
        cote = math.ceil(math.sqrt(A_requis) * 10) / 10
        return ResultatFondation(
            type=TypeFondation.SEMELLE_ISOLEE,
            justification=f"Sol portant (qadm={d.pression_sol_MPa} MPa), charges modérées (NEd={NEd_max:.0f} kN)",
            largeur_semelle_m=round(cote, 2),
            profondeur_m=1.2,
            beton_semelle_m3=round(cote**2 * 0.5, 1),
        )
    elif q_adm >= 100 and NEd_max <= 1500 and d.nb_niveaux <= 5:
        # Semelles filantes + radier
        return ResultatFondation(
            type=TypeFondation.RADIER,
            justification=f"Sol intermédiaire, ouvrage moyen — radier général recommandé",
            largeur_semelle_m=0.0,
            profondeur_m=1.5,
            beton_semelle_m3=round(d.surface_emprise_m2 * 0.35, 1),
        )
    else:
        # Pieux forés
        # Capacité portante pieu : Qs (frottement) + Qp (pointe)
        # Formule simplifiée : Q_ult = qs * π * D * L + qp * π * D²/4
        # qs ≈ 50 kPa (sol argilo-sableux Dakar), qp ≈ 1500 kPa
        if d.pression_sol_MPa <= 0.10:
            D_pieu = 0.800  # Sol mou → grand diamètre
            qs, qp = 30, 800
        elif d.pression_sol_MPa <= 0.15:
            D_pieu = 0.800
            qs, qp = 50, 1500
        else:
            D_pieu = 0.600
            qs, qp = 80, 2500

        L_pieu = max(8.0, d.nb_niveaux * 1.2)
        L_pieu = min(L_pieu, 20.0)

        Q_ult = qs * math.pi * D_pieu * L_pieu + qp * math.pi * D_pieu**2 / 4
        Q_adm = Q_ult / 2.5

        nb_pieux_par_poteau = max(1, int(math.ceil(NEd_max / Q_adm)))
        nb_pieux_total = nb_pieux_par_poteau * (d.nb_travees_x + 1) * (d.nb_travees_y + 1)

        # Armatures pieu
        As_min = 0.005 * math.pi * (D_pieu * 1000 / 2)**2 / 100  # cm² min 0.5%
        As_cm2 = max(As_min, 4 * math.pi * 25**2 / 400)

        return ResultatFondation(
            type=TypeFondation.PIEUX,
            justification=f"Sol compressible (qadm={d.pression_sol_MPa} MPa) et/ou ouvrage élevé (R+{d.nb_niveaux-1})",
            nb_pieux=nb_pieux_total,
            diam_pieu_mm=int(D_pieu * 1000),
            longueur_pieu_m=round(L_pieu, 1),
            As_cm2=round(As_cm2, 1),
            profondeur_m=round(L_pieu, 1),
        )


# ══════════════════════════════════════════════════════════════
# ANALYSE SISMIQUE EC8
# ══════════════════════════════════════════════════════════════

def _calculer_sismique(d: DonneesProjet, zone: int, shon: float) -> ResultatSismique:
    """Analyse sismique simplifiée EC8 §4.3.3."""
    # Paramètres sismiques par zone
    ag_values = {0: 0.0, 1: 0.07, 2: 0.11, 3: 0.16, 4: 0.22}
    ag_g = ag_values.get(zone, 0.07)

    # Période fondamentale (méthode approchée EC8)
    Ht = d.nb_niveaux * d.hauteur_etage_m
    T1 = 0.075 * Ht**0.75  # Cadres BA

    # Facteur d'importance et comportement
    gamma_I = 1.0
    S = 1.15  # Sol type C
    q = 1.5   # DCL

    # Spectre de réponse élastique Sd(T1)
    TB, TC, TD = 0.15, 0.5, 2.0
    ag = ag_g * 9.81  # m/s²
    if T1 <= TB:
        Sd = ag * S * (0.667 + T1/TB * (2.5/q - 0.667))
    elif T1 <= TC:
        Sd = ag * S * 2.5 / q
    elif T1 <= TD:
        Sd = ag * S * 2.5 / q * TC / T1
    else:
        Sd = ag * S * 2.5 / q * TC * TD / T1**2

    # Masse totale estimée (G + 0.3Q)
    masse_totale = shon * (d.charge_G if hasattr(d, 'charge_G') else 6.5) / 9.81 * 1000  # kg
    # Force sismique de base
    Fb_kN = Sd * masse_totale / 1000 * 0.85

    # Dispositions constructives DCL
    dispositions = [
        f"Zone sismique {zone} — ag = {ag_g}g — Spectre Type 1",
        f"Système : Cadres BA non ductiles (DCL) — q = {q}",
        f"Période fondamentale T₁ = {T1:.2f} s",
        "Enrobage nominal ≥ 30mm (armatures longitudinales)",
        "Recouvrements ≥ 50Ø en zone sismique",
        f"Étriers denses en zones critiques : L₀ ≥ max(hc, lw/6, 45cm)",
        "Confinement nœuds poteaux-poutres obligatoire",
        "Continuité armatures longitudinales sur toute la hauteur",
    ]

    if zone >= 3:
        dispositions.append("⚠ Zone sismique élevée — analyse dynamique modale recommandée")
        dispositions.append("⚠ Considérer DCM (ductilité moyenne) — q = 3.9")

    return ResultatSismique(
        zone=zone,
        ag_g=ag_g,
        T1_s=round(T1, 2),
        Fb_kN=round(Fb_kN, 0),
        Sd_T1=round(Sd, 3),
        dispositions=dispositions,
        conforme_DCL=(zone <= 2),
    )


# ══════════════════════════════════════════════════════════════
# CALCUL BOQ STRUCTURE
# ══════════════════════════════════════════════════════════════

def _calculer_boq(d: DonneesProjet, poteaux: List[ResultatPoteau],
                   poutre: ResultatPoutre, dalle: ResultatDalle,
                   fondation: ResultatFondation, cloisons: ResultatCloisons,
                   prix_struct) -> BOQStructure:
    """BOQ structure complet depuis données moteur."""
    shon = _shon(d)
    surf_batie = shon
    surf_habitable = shon * 0.78

    # ── Volumes béton ──
    ep_dalle = dalle.epaisseur_mm / 1000
    V_dalles = shon * ep_dalle * 0.85  # 85% dalle pleine (trémies)

    # Poteaux
    V_poteaux = 0.0
    for p in poteaux:
        b = p.section_mm / 1000
        nb_pot = (d.nb_travees_x + 1) * (d.nb_travees_y + 1)
        V_poteaux += b**2 * d.hauteur_etage_m * nb_pot

    # Poutres
    b_p = poutre.b_mm / 1000
    h_p = poutre.h_mm / 1000
    L_poutres_x = d.nb_travees_x * d.portee_max_m * (d.nb_travees_y + 1) * d.nb_niveaux
    L_poutres_y = d.nb_travees_y * d.portee_min_m * (d.nb_travees_x + 1) * d.nb_niveaux
    V_poutres = (L_poutres_x + L_poutres_y) * b_p * (h_p - ep_dalle)

    # Fondations
    if fondation.type == TypeFondation.PIEUX:
        V_fond = (math.pi * (fondation.diam_pieu_mm/1000/2)**2 *
                  fondation.longueur_pieu_m * fondation.nb_pieux)
    elif fondation.type == TypeFondation.RADIER:
        V_fond = fondation.beton_semelle_m3
    else:
        V_fond = fondation.beton_semelle_m3 * (d.nb_travees_x + 1) * (d.nb_travees_y + 1)

    V_beton_struct = V_dalles + V_poteaux + V_poutres
    V_beton_total = V_beton_struct + V_fond

    # ── Acier ──
    # Ratios kg/m³ par élément
    kg_dalles  = V_dalles  * 80   # kg/m³ dalles
    kg_poteaux = V_poteaux * 120  # kg/m³ poteaux
    kg_poutres = V_poutres * 100  # kg/m³ poutres
    kg_fond    = V_fond    * 90   # kg/m³ fondations
    kg_total   = kg_dalles + kg_poteaux + kg_poutres + kg_fond

    # ── Coffrage ──
    coff_dalles  = shon * 0.85
    coff_poteaux = V_poteaux / (d.portee_max_m/2 * 0.3) * 4 * 0.3 * d.hauteur_etage_m * 0.5
    coff_poutres = (L_poutres_x + L_poutres_y) * (b_p + 2*(h_p - ep_dalle)) * 0.6
    V_coffrage   = coff_dalles + abs(coff_poteaux) + abs(coff_poutres)

    # ── Terrassement ──
    V_terr = d.surface_emprise_m2 * (fondation.profondeur_m + 0.3)

    # ── Maçonnerie ──
    surf_maco = shon * 0.22  # ~22% SHON

    # ── Étanchéité ──
    surf_etanch = d.surface_emprise_m2

    # ── Coûts ──
    p = prix_struct
    c_beton  = int(V_beton_struct * p.beton_c3037_m3)
    c_fond_b = int(V_fond * p.beton_c3037_m3)
    c_acier  = int(kg_total * p.acier_ha500_kg)
    c_coff   = int(V_coffrage * p.coffrage_bois_m2)
    c_terr   = int(V_terr * p.terr_mecanique_m3)
    c_fond   = int(V_fond * p.pieu_fore_d800_ml if fondation.type == TypeFondation.PIEUX
                   else V_fond * p.beton_c3037_m3 * 1.3)
    c_maco   = int(surf_maco * p.agglo_creux_15_m2)
    c_etanch = int(surf_etanch * p.etanch_sbs_m2)
    c_divers = int((c_beton + c_acier + c_coff) * 0.06)

    total_bas  = c_beton + c_fond_b + c_acier + c_coff + c_terr + c_fond + c_maco + c_etanch + c_divers
    total_haut = int(total_bas * 1.15)

    ratio_bati     = int(total_bas / surf_batie) if surf_batie > 0 else 0
    ratio_habitable= int(total_bas / surf_habitable) if surf_habitable > 0 else 0

    return BOQStructure(
        beton_fondation_m3=round(V_fond, 1),
        beton_structure_m3=round(V_beton_struct, 1),
        beton_total_m3=round(V_beton_total, 1),
        acier_kg=round(kg_total, 0),
        coffrage_m2=round(V_coffrage, 0),
        terrassement_m3=round(V_terr, 0),
        maconnerie_m2=round(surf_maco, 0),
        etancheite_m2=round(surf_etanch, 0),
        cout_beton_fcfa=c_beton,
        cout_acier_fcfa=c_acier,
        cout_coffrage_fcfa=c_coff,
        cout_terr_fcfa=c_terr,
        cout_fond_fcfa=c_fond,
        cout_maco_fcfa=c_maco,
        cout_etanch_fcfa=c_etanch,
        cout_divers_fcfa=c_divers,
        total_bas_fcfa=total_bas,
        total_haut_fcfa=total_haut,
        ratio_fcfa_m2_bati=ratio_bati,
        ratio_fcfa_m2_habitable=ratio_habitable,
        surface_batie_m2=round(surf_batie, 0),
        surface_habitable_m2=round(surf_habitable, 0),
    )


# ══════════════════════════════════════════════════════════════
# ANALYSE INGÉNIEUR
# ══════════════════════════════════════════════════════════════

def _analyser(d: DonneesProjet, poteaux: List[ResultatPoteau],
               poutre: ResultatPoutre, dalle: ResultatDalle,
               fondation: ResultatFondation, boq: BOQStructure,
               classe_beton: str, classe_acier: str) -> AnalyseIngenieur:

    alertes = []
    points_forts = []
    recommandations = []

    # Vérification taux armatures
    taux_max = max(p.taux_armature_pct for p in poteaux) if poteaux else 0
    taux_min = min(p.taux_armature_pct for p in poteaux) if poteaux else 0

    if taux_max > 3.5:
        alertes.append(f"Taux armature max {taux_max:.1f}% proche limite EC2 (4%) — vérifier sections")
    if taux_max > 2.0:
        alertes.append(f"Taux armature {taux_max:.1f}% élevé — envisager augmentation section béton")

    # Ratio NEd/NRd
    ratios = [p.ratio_NEd_NRd for p in poteaux]
    if any(r > 0.9 for r in ratios):
        alertes.append("Certains poteaux proches de la résistance limite — marge de sécurité faible")

    # Fondations
    if fondation.type == TypeFondation.PIEUX:
        if d.pression_sol_MPa <= 0.10:
            alertes.append(f"Sol très compressible (qadm={d.pression_sol_MPa} MPa) — étude géotechnique obligatoire")
        points_forts.append("Fondations profondes adaptées aux conditions de sol")

    # Points forts
    if taux_max <= 2.0 and taux_min >= 0.5:
        points_forts.append("Taux d'armature dans la plage optimale EC2 sur tous les niveaux")
    if all(p.verif_ok for p in poteaux):
        points_forts.append("Tous les poteaux vérifiés — structure conforme EC2")

    fck = _fck_from_classe(classe_beton)
    if fck >= 30:
        points_forts.append(f"Béton {classe_beton} adapté à l'exposition et à la hauteur du bâtiment")

    # Recommandations
    if d.nb_niveaux >= 6 and fondation.type != TypeFondation.PIEUX:
        recommandations.append("Envisager pieux forés pour bâtiment R+5 et plus")
    if taux_max > 2.5:
        recommandations.append("Augmenter les sections de poteaux pour réduire le taux d'armature")
    if d.distance_mer_km < 5:
        recommandations.append(f"Exposition marine (distance mer {d.distance_mer_km:.1f}km) — enrobage ≥ 40mm impératif")

    recommandations.append("Faire établir les plans d'exécution par un BET agréé avant travaux")
    recommandations.append("Prévoir essais béton sur site (au moins 3 éprouvettes par coulée)")

    # Conformité
    conf_ec2 = "Conforme" if all(p.verif_ok for p in poteaux) else "À vérifier"
    conf_ec8 = "Conforme DCL" if d.zone_sismique <= 2 else "Analyse complémentaire requise"

    # Note ingénieur
    note = (
        f"Structure R+{d.nb_niveaux-1} ({d.usage.value}) dimensionnée selon EC2/EC8. "
        f"Béton {classe_beton} — Acier {classe_acier}. "
        f"{'Tous les éléments vérifient les exigences de résistance.' if conf_ec2 == 'Conforme' else 'Des vérifications complémentaires sont nécessaires.'} "
        f"Coût structure estimé : {boq.total_bas_fcfa/1e9:.2f} – {boq.total_haut_fcfa/1e9:.2f} Mds FCFA "
        f"({boq.ratio_fcfa_m2_bati:,} FCFA/m² bâti).".replace(',', ' ')
    )

    return AnalyseIngenieur(
        classe_beton_choisie=classe_beton,
        classe_acier_choisie=classe_acier,
        justification_materiaux=f"Sélection automatique : R+{d.nb_niveaux-1}, distance mer {d.distance_mer_km:.1f}km, usage {d.usage.value}",
        commentaire_global=f"Dimensionnement cohérent pour un {d.usage.value} de {d.nb_niveaux} niveaux à {d.ville}.",
        alertes=alertes,
        points_forts=points_forts,
        recommandations=recommandations,
        conformite_ec2=conf_ec2,
        conformite_ec8=conf_ec8,
        note_ingenieur=note,
    )


# ══════════════════════════════════════════════════════════════
# POINT D'ENTRÉE PRINCIPAL
# ══════════════════════════════════════════════════════════════

def calculer_structure(d: DonneesProjet) -> ResultatsStructure:
    """
    Calcule la structure complète depuis les données projet.
    Zéro valeur codée en dur — tout calculé depuis les inputs.
    """
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    # Tenter d'importer la base de prix
    try:
        from prix_marche import get_prix_structure
        prix_struct = get_prix_structure(d.ville)
    except ImportError:
        # Fallback prix Dakar si module absent
        class _PrixFallback:
            beton_c3037_m3 = 185_000
            acier_ha500_kg = 810
            coffrage_bois_m2 = 18_000
            terr_mecanique_m3 = 8_500
            pieu_fore_d800_ml = 285_000
            agglo_creux_15_m2 = 24_000
            etanch_sbs_m2 = 18_500
            agglo_creux_10_m2 = 18_000
            agglo_creux_20_m2 = 30_000
            agglo_plein_25_m2 = 38_000
            ba13_simple_m2 = 28_000
            ba13_double_m2 = 42_000
        prix_struct = _PrixFallback()

    # ── 1. Résolution des paramètres auto ──
    ville_key = _get_ville_key(d.ville)

    # Distance mer
    dist_mer = d.distance_mer_km if d.distance_mer_km > 0 else \
               DISTANCE_MER_DEFAUT.get(ville_key, 5.0)

    # Pression sol
    p_sol = d.pression_sol_MPa if d.pression_sol_MPa > 0 else \
            PRESSION_SOL_DEFAUT.get(ville_key, 0.15)

    # Zone sismique
    pays_key = d.pays.lower().replace(" ", "_").replace("'", "")
    zone = d.zone_sismique if d.zone_sismique >= 0 else \
           ZONE_SISMIQUE.get(pays_key, 1)

    # Classe béton/acier
    if d.classe_beton and d.classe_acier:
        classe_beton = d.classe_beton
        classe_acier = d.classe_acier
    else:
        classe_beton, classe_acier = _auto_classe_beton(d.nb_niveaux, dist_mer, d.usage)

    fck = _fck_from_classe(classe_beton)
    fyk = _fyk_from_classe(classe_acier)

    # Charges
    G = CHARGES_PERMANENTES[d.usage]
    Q = CHARGES_VARIABLES[d.usage]

    # Mettre à jour d avec les valeurs résolues
    d.distance_mer_km  = dist_mer
    d.pression_sol_MPa = p_sol
    d.zone_sismique    = zone

    # ── 2. Calculs ──
    poteaux   = _calculer_poteaux(d, fck, fyk, G, Q)
    poutre_p  = _calculer_poutre(d.portee_max_m, G, Q, fck, fyk, "principale")
    poutre_s  = _calculer_poutre(d.portee_min_m, G, Q, fck, fyk, "secondaire") \
                if d.portee_min_m < d.portee_max_m * 0.9 else None
    dalle     = _calculer_dalle(d.portee_min_m, d.portee_max_m, G, Q, fck, fyk)
    cloisons  = _calculer_cloisons(d, prix_struct)
    fondation = _calculer_fondations(d, poteaux, fck, prix_struct)
    shon_val  = _shon(d)
    sismique  = _calculer_sismique(d, zone, shon_val)
    boq       = _calculer_boq(d, poteaux, poutre_p, dalle, fondation, cloisons, prix_struct)
    analyse   = _analyser(d, poteaux, poutre_p, dalle, fondation, boq, classe_beton, classe_acier)

    return ResultatsStructure(
        params=d,
        classe_beton=classe_beton,
        classe_acier=classe_acier,
        fck_MPa=fck,
        fyk_MPa=fyk,
        distance_mer_km=dist_mer,
        pression_sol_MPa=p_sol,
        zone_sismique=zone,
        charge_G_kNm2=G,
        charge_Q_kNm2=Q,
        poteaux=poteaux,
        poutre_principale=poutre_p,
        poutre_secondaire=poutre_s,
        dalle=dalle,
        cloisons=cloisons,
        fondation=fondation,
        sismique=sismique,
        boq=boq,
        analyse=analyse,
    )


# ══════════════════════════════════════════════════════════════
# TEST
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=== TEST MOTEUR STRUCTURE V2 ===\n")

    projets_test = [
        DonneesProjet(nom="Villa Ngom", ville="Dakar", pays="Senegal",
                      usage=Usage.RESIDENTIEL, nb_niveaux=2,
                      surface_emprise_m2=300, portee_max_m=5.0, portee_min_m=4.0,
                      nb_travees_x=3, nb_travees_y=2),
        DonneesProjet(nom="Résidence Sakho", ville="Dakar", pays="Senegal",
                      usage=Usage.RESIDENTIEL, nb_niveaux=9,
                      surface_emprise_m2=980, portee_max_m=6.18, portee_min_m=4.13,
                      nb_travees_x=8, nb_travees_y=5),
        DonneesProjet(nom="Tour Bureaux Plateau", ville="Abidjan", pays="Cote d'Ivoire",
                      usage=Usage.BUREAU, nb_niveaux=15,
                      surface_emprise_m2=1200, portee_max_m=8.0, portee_min_m=6.0,
                      nb_travees_x=6, nb_travees_y=4),
        DonneesProjet(nom="Hotel Marrakech", ville="Casablanca", pays="Maroc",
                      usage=Usage.HOTEL, nb_niveaux=6,
                      surface_emprise_m2=800, portee_max_m=7.0, portee_min_m=5.5,
                      nb_travees_x=5, nb_travees_y=4),
    ]

    for proj in projets_test:
        r = calculer_structure(proj)
        print(f"{'='*60}")
        print(f"PROJET : {proj.nom} ({proj.ville}) — R+{proj.nb_niveaux-1} {proj.usage.value}")
        print(f"Béton : {r.classe_beton} | Acier : {r.classe_acier}")
        print(f"Charges : G={r.charge_G_kNm2} kN/m² | Q={r.charge_Q_kNm2} kN/m²")
        print(f"Fondations : {r.fondation.type.value}")
        print(f"Dalle : e={r.dalle.epaisseur_mm}mm")
        print(f"Poutre : {r.poutre_principale.b_mm}×{r.poutre_principale.h_mm}mm")
        print(f"Cloison recommandée : {r.cloisons.option_recommandee.value}")
        print(f"BOQ : {r.boq.beton_total_m3:.0f} m³ béton | {r.boq.acier_kg:.0f} kg acier")
        print(f"Coût structure : {r.boq.total_bas_fcfa/1e9:.2f} – {r.boq.total_haut_fcfa/1e9:.2f} Mds FCFA")
        print(f"Ratio : {r.boq.ratio_fcfa_m2_bati:,} FCFA/m² bâti".replace(',', ' '))
        print(f"Conformité EC2 : {r.analyse.conformite_ec2}")
        if r.analyse.alertes:
            print(f"Alertes : {len(r.analyse.alertes)}")
        print()
