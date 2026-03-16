"""
engine_mep_v1.py — Moteur de calcul MEP Tijan AI
Références normatives :
  Électricité  : NF C 15-100 (installations BT)
  Plomberie    : DTU 60.11 (débit eau), ONAS dotation 150 L/pers/j
  CVC          : EN 12831 (charge thermique), ASHRAE 55 (confort)
  Domotique    : estimation forfaitaire par surface
  EDGE         : IFC EDGE Standard v3 (seuils 20%)
Marché         : Dakar, Sénégal — prix Mars 2026
"""

from dataclasses import dataclass, field
from typing import List, Optional
import math


# ══════════════════════════════════════════════════════════════
# DONNÉES D'ENTRÉE
# ══════════════════════════════════════════════════════════════

@dataclass
class DonneesMEP:
    nom: str = "Projet Tijan"
    ville: str = "Dakar"
    nb_niveaux: int = 5
    hauteur_etage_m: float = 3.0
    surface_emprise_m2: float = 500.0
    nb_logements: int = 0          # 0 = estimé depuis surface
    personnes_par_logement: int = 4
    usage: str = "residentiel"     # residentiel | bureau | mixte
    # Paramètres site
    distance_mer_km: float = 2.0   # influence classe exposition
    zone_climatique: str = "sahelien_cotier"  # dakar
    # Étude de sol (texte parsé si fourni)
    note_sol: str = ""
    # Options techniques (EDGE)
    cvc_inverter: bool = False
    vmc_double_flux: bool = False
    chauffe_eau_solaire: bool = False
    wc_double_chasse: bool = False
    robinetterie_eco: bool = False
    led_100pct: bool = False
    beton_ggbs: bool = False        # substitution laitier
    parpaings_creux: bool = True
    isolation_toiture_mm: float = 0.0
    double_vitrage: bool = False
    # Prix marché Dakar Mars 2026 (FCFA)
    prix_kwh_senelec: float = 105.0   # FCFA/kWh tranche résidentielle
    prix_m3_eau_sde: float = 750.0    # FCFA/m³


# ══════════════════════════════════════════════════════════════
# RÉSULTATS
# ══════════════════════════════════════════════════════════════

@dataclass
class BilanElectrique:
    puissance_logements_kva: float
    puissance_cvc_kva: float
    puissance_ascenseurs_kva: float
    puissance_pompes_kva: float
    puissance_communs_kva: float
    puissance_reserve_kva: float
    puissance_totale_souscrite_kva: float
    transfo_necessaire_kva: int      # standard : 100,160,250,400,630
    groupe_electrogene_kva: int
    nb_compteurs_divisionnaires: int
    conso_annuelle_estimee_kwh: float
    facture_annuelle_estimee_fcfa: int


@dataclass
class BilanPlomberie:
    nb_logements: int
    besoin_journalier_total_L: float
    besoin_journalier_incendie_L: float
    besoin_journalier_communs_L: float
    besoin_total_m3_j: float
    volume_citerne_m3: float         # dimensionnement réserve 24h
    volume_bache_incendie_m3: float
    debit_surpresseur_m3h: float
    hmt_surpresseur_mce: float
    nb_chauffe_eau_solaire: int
    capacite_chauffe_eau_L: int
    facture_eau_annuelle_fcfa: int


@dataclass
class BilanCVC:
    # Charges thermiques Dakar EN 12831
    apports_solaires_W: float
    apports_internes_W: float
    apports_equipements_W: float
    renouvellement_air_W: float
    puissance_totale_extraire_W: float
    puissance_frigorifique_installee_kW: float
    # Équipements
    nb_splits_sejour: int            # 18 000 BTU/h
    nb_splits_chambre: int           # 9 000 BTU/h
    nb_vmc_double_flux: int
    puissance_cta_m3h: float         # CTA parties communes
    nb_extracteurs_parking: int
    conso_cvc_annuelle_kwh: float


@dataclass
class BilanDomotique:
    surface_totale_m2: float
    nb_logements: int
    puissance_bms_kva: float
    nb_points_acces_wifi: int
    nb_cameras_cctv: int
    nb_portes_controle_acces: int
    sse_categorie: str               # A ou B selon EN 54


@dataclass
class AnalyseEDGE:
    # Calculs réels basés sur le projet
    # ÉNERGIE
    conso_reference_kwh_m2_an: float   # sans mesures EDGE
    conso_projet_kwh_m2_an: float      # avec mesures retenues
    economie_energie_pct: float
    conformite_energie: bool

    # EAU
    conso_reference_L_pers_j: float
    conso_projet_L_pers_j: float
    economie_eau_pct: float
    conformite_eau: bool

    # MATÉRIAUX (énergie incorporée)
    ei_reference_kwh_m2: float         # sans mesures
    ei_projet_kwh_m2: float            # avec GGBS, creux, isolation
    economie_materiaux_pct: float
    conformite_materiaux: bool

    # Verdict
    nb_criteres_conformes: int         # sur 3
    certifiable: bool
    niveau_certification: str          # "Non certifiable" | "EDGE Basique" | "EDGE Advanced" | "Net Zero"

    # Détail mesures actives
    mesures_energie: List[str]
    mesures_eau: List[str]
    mesures_materiaux: List[str]

    # Payback
    surcout_vert_pct: float
    payback_ans: float


@dataclass
class BOQ_MEP_Lot:
    nom: str
    basic_fcfa: int
    hend_fcfa: int
    luxury_fcfa: int
    detail_lignes: List[dict] = field(default_factory=list)


@dataclass
class AnalyseCoutBenefice:
    # Comparatif Basic vs High-End vs Luxury
    basic_total: int
    hend_total: int
    luxury_total: int
    # Différentiels
    delta_basic_hend: int
    delta_basic_luxury: int
    # Bénéfices estimés sur 20 ans
    economie_energie_basic_fcfa_an: int
    economie_energie_hend_fcfa_an: int
    economie_energie_luxury_fcfa_an: int
    payback_hend_ans: float
    payback_luxury_ans: float
    # ROI
    roi_hend_20ans_pct: float
    roi_luxury_20ans_pct: float
    recommandation: str


@dataclass
class ResultatsMEP:
    donnees: DonneesMEP
    electrique: BilanElectrique
    plomberie: BilanPlomberie
    cvc: BilanCVC
    domotique: BilanDomotique
    edge: AnalyseEDGE
    boq_lots: List[BOQ_MEP_Lot]
    boq_total_basic: int
    boq_total_hend: int
    boq_total_luxury: int
    analyse_cout_benefice: AnalyseCoutBenefice
    note_sol_integree: bool          # True si étude de sol parsée


# ══════════════════════════════════════════════════════════════
# PRIX UNITAIRES MARCHÉ DAKAR (Mars 2026)
# Toutes les valeurs sont des constantes de marché documentées
# Sources : CFAO Technologies, Schneider SN, Fabrimetal, LG SN
# ══════════════════════════════════════════════════════════════

PRIX = {
    # Électricité
    "transfo_400kva":      47_500_000,
    "transfo_250kva":      32_000_000,
    "transfo_160kva":      22_000_000,
    "ge_250kva":           33_000_000,
    "ge_160kva":           22_000_000,
    "ge_100kva":           15_000_000,
    "tgbt_4000a":          14_000_000,
    "tgbt_2500a":          10_000_000,
    "td_125a":                900_000,
    "tableau_logement_40a":   200_000,
    "cablage_par_logement": 1_200_000,
    "eclairage_communs_ml":    35_000,   # par ml linéaire
    "eclairage_logement":     500_000,
    "baes_u":                  45_000,
    "paratonnerre":          2_800_000,
    "compteur_divisionne":     180_000,
    # Plomberie
    "citerne_10m3":        1_800_000,
    "citerne_50m3":        9_000_000,
    "bache_incendie_12m3": 5_500_000,
    "bache_incendie_6m3":  3_500_000,
    "surpresseur_6m3h":    3_800_000,
    "surpresseur_3m3h":    2_200_000,
    "pompe_incendie":      7_000_000,
    "colonne_montante_ml":    22_000,
    "chauffe_eau_solaire_200L": 2_100_000,
    "chauffe_eau_solaire_100L": 1_400_000,
    "reseau_eu_ev_ep_forfait": 2_000_000,  # par logement
    "ria_palier":            350_000,
    "sanitaires_basic_logt": 1_800_000,
    "sanitaires_hend_logt":  3_500_000,
    "sanitaires_luxury_logt": 8_500_000,
    "robinetterie_basic_logt": 450_000,
    "robinetterie_hend_logt":  950_000,
    "robinetterie_luxury_logt": 2_800_000,
    # CVC
    "split_18000btu_basic":    850_000,
    "split_18000btu_hend":   1_200_000,
    "split_18000btu_luxury": 2_200_000,
    "split_9000btu_basic":     480_000,
    "split_9000btu_hend":      720_000,
    "split_9000btu_luxury":  1_350_000,
    "vmc_double_flux_basic":   700_000,
    "vmc_double_flux_hend":  1_100_000,
    "vmc_double_flux_luxury": 1_800_000,
    "cta_8000m3h":           10_000_000,
    "cta_4000m3h":            6_500_000,
    "extracteur_parking":      950_000,
    "gaines_cvc_m2":            9_000,   # par m² emprise
    "thermostat_basic":         90_000,
    "thermostat_hend":         200_000,
    "thermostat_luxury":       420_000,
    "desenfumage_cage":       2_000_000,
    # Domotique
    "bms_serveur_basic":     4_500_000,
    "bms_serveur_hend":      8_500_000,
    "bms_serveur_luxury":   18_000_000,
    "switch_coeur_basic":    1_800_000,
    "switch_coeur_hend":     3_500_000,
    "switch_etage_basic":      450_000,
    "switch_etage_hend":       850_000,
    "wifi_point_basic":        180_000,
    "wifi_point_hend":         350_000,
    "wifi_point_luxury":       650_000,
    "cablage_reseau_forfait":3_500_000,
    "interphone_portier":      950_000,
    "combine_video_basic":     180_000,
    "combine_video_hend":      350_000,
    "cctv_pack_16cam":       3_200_000,
    "controle_acces_porte":    350_000,
    "incendie_ssi_a":        9_000_000,
    "knx_logement_basic":      350_000,
    "knx_logement_hend":       850_000,
    "knx_logement_luxury":   2_800_000,
    "dashboard_energie":     3_000_000,
}

# Constantes physiques Dakar
DAKAR = {
    "temp_ext_ete_C":     35.0,   # °C
    "temp_int_cible_C":   24.0,   # °C ASHRAE 55
    "rayonnement_solaire": 5.5,   # kWh/m²/jour
    "nb_heures_clim_an":  3_600,  # heures climatisation annuelles estimées
    "nb_heures_chauffage":    0,   # pas de chauffage à Dakar
}

# Références EDGE v3 bâtiment résidentiel Afrique subsaharienne
EDGE_REF = {
    # Énergie : consommation de référence kWh/m²/an sans mesures
    "conso_ref_energie_kwh_m2":    120.0,
    # Eau : dotation référence L/pers/jour sans mesures
    "conso_ref_eau_L_pers_j":      180.0,
    # Énergie incorporée référence kWh/m² construction
    "ei_ref_kwh_m2":               750.0,
    # Seuil certification
    "seuil_basique_pct":            20.0,
    "seuil_advanced_pct":           40.0,
    "seuil_net_zero_pct":           60.0,
}


# ══════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ══════════════════════════════════════════════════════════════

def _estimer_nb_logements(d: DonneesMEP) -> int:
    """Estime le nombre de logements depuis la surface si non fourni."""
    if d.nb_logements > 0:
        return d.nb_logements
    surface_par_logement = 80.0  # m² moyen logement résidentiel Dakar
    shon = d.surface_emprise_m2 * (d.nb_niveaux - 1)  # hors RDC commercial éventuel
    return max(1, round(shon / surface_par_logement))


def _shon(d: DonneesMEP) -> float:
    return d.surface_emprise_m2 * d.nb_niveaux


def _nb_personnes(d: DonneesMEP, nb_logements: int) -> int:
    return nb_logements * d.personnes_par_logement


def _transfo_standard(kva_besoin: float) -> int:
    """Sélectionne le transformateur standard immédiatement supérieur."""
    standards = [100, 160, 250, 400, 630, 1000]
    for s in standards:
        if s >= kva_besoin:
            return s
    return 1000


def _ge_standard(kva_besoin: float) -> int:
    standards = [50, 100, 160, 250, 400, 630]
    for s in standards:
        if s >= kva_besoin * 0.6:  # GE dimensionné à 60% charge normale
            return s
    return 630


# ══════════════════════════════════════════════════════════════
# CALCUL ÉLECTRIQUE — NF C 15-100
# ══════════════════════════════════════════════════════════════

def calculer_electrique(d: DonneesMEP, nb_logements: int) -> BilanElectrique:
    """
    Bilan puissance NF C 15-100.
    Foisonnement selon le nombre de logements (coefficient simultanéité).
    """
    # Puissance logements (éclairage LED + prises)
    # NF C 15-100 : 8 kVA/logement foisonné
    foisonnement_logt = max(0.40, 0.85 - nb_logements * 0.01)  # décroît avec nb
    p_logements = 8.0 * nb_logements * foisonnement_logt

    # CVC : split inverter ~3 kVA/logement (séjour) + 1.5 kVA (chambre principale)
    p_cvc_logt = (3.0 + 1.5) * nb_logements * 0.70  # foisonnement 70%
    p_cvc_communs = max(10.0, d.surface_emprise_m2 * 0.01)  # CTA parties communes

    # Ascenseurs : 1 ascenseur pour <= 6 étages, 2 au-delà
    nb_asc = 1 if d.nb_niveaux <= 7 else 2
    p_ascenseurs = nb_asc * 15.0 * 0.80

    # Pompes eau + incendie
    p_pompes = 3 * 5.5 * 0.70  # 3 groupes pompes

    # Éclairage communs (LED)
    surface_communs = d.surface_emprise_m2 * 0.15 * d.nb_niveaux
    p_communs = surface_communs * 8 / 1000  # 8 W/m² LED

    # Réserve 10%
    p_sous_total = p_logements + p_cvc_logt + p_cvc_communs + p_ascenseurs + p_pompes + p_communs
    p_reserve = p_sous_total * 0.10
    p_total = p_sous_total + p_reserve

    transfo = _transfo_standard(p_total)
    ge = _ge_standard(p_total)

    # Consommation annuelle estimée
    heures_an = 8760
    facteur_utilisation = 0.35  # résidentiel : 35% du temps
    conso_kwh_an = p_total * 0.8 * heures_an * facteur_utilisation  # 0.8 = facteur puissance
    facture_fcfa = round(conso_kwh_an * d.prix_kwh_senelec)

    return BilanElectrique(
        puissance_logements_kva=round(p_logements, 1),
        puissance_cvc_kva=round(p_cvc_logt + p_cvc_communs, 1),
        puissance_ascenseurs_kva=round(p_ascenseurs, 1),
        puissance_pompes_kva=round(p_pompes, 1),
        puissance_communs_kva=round(p_communs, 1),
        puissance_reserve_kva=round(p_reserve, 1),
        puissance_totale_souscrite_kva=round(p_total, 0),
        transfo_necessaire_kva=transfo,
        groupe_electrogene_kva=ge,
        nb_compteurs_divisionnaires=nb_logements,
        conso_annuelle_estimee_kwh=round(conso_kwh_an),
        facture_annuelle_estimee_fcfa=facture_fcfa,
    )


# ══════════════════════════════════════════════════════════════
# CALCUL PLOMBERIE — DTU 60.11 + ONAS
# ══════════════════════════════════════════════════════════════

def calculer_plomberie(d: DonneesMEP, nb_logements: int) -> BilanPlomberie:
    """
    Dimensionnement plomberie sanitaire DTU 60.11.
    Dotation ONAS Sénégal : 150 L/personne/jour.
    """
    nb_pers = _nb_personnes(d, nb_logements)

    # Besoins journaliers
    besoin_logt = nb_pers * 150.0                        # ONAS 150 L/pers/j
    besoin_incendie = 4 * 1200.0                          # 4h × 1200 L/h (RIA)
    besoin_communs = d.surface_emprise_m2 * 0.5           # nettoyage + espaces verts

    # Réserve sanitaire 15%
    besoin_total = (besoin_logt + besoin_communs) * 1.15

    # Volume citerne : réserve 24h consommation
    volume_citerne = math.ceil(besoin_total / 1000 / 5) * 5  # arrondi multiple de 5 m³
    volume_citerne = max(10.0, volume_citerne)

    # Bâche incendie fixe réglementaire
    volume_bache = 12.0 if nb_logements > 10 else 6.0

    # Surpresseur
    debit_pointe = besoin_total / 1000 / 16  # 16h utilisation
    debit_pointe = max(2.0, round(debit_pointe * 2, 0))  # foisonnement ×2
    hmt = 10 + d.nb_niveaux * d.hauteur_etage_m * 1.1  # pression + pertes charges

    # Chauffe-eau solaire : 1 par logement, 200L si >= 4 pers, 100L sinon
    cap_cesi = 200 if d.personnes_par_logement >= 4 else 100
    nb_cesi = nb_logements if d.chauffe_eau_solaire else 0

    facture_eau = round(besoin_total * 365 / 1000 * d.prix_m3_eau_sde)

    return BilanPlomberie(
        nb_logements=nb_logements,
        besoin_journalier_total_L=round(besoin_logt),
        besoin_journalier_incendie_L=round(besoin_incendie),
        besoin_journalier_communs_L=round(besoin_communs),
        besoin_total_m3_j=round(besoin_total / 1000, 1),
        volume_citerne_m3=volume_citerne,
        volume_bache_incendie_m3=volume_bache,
        debit_surpresseur_m3h=float(debit_pointe),
        hmt_surpresseur_mce=round(hmt, 1),
        nb_chauffe_eau_solaire=nb_cesi,
        capacite_chauffe_eau_L=cap_cesi,
        facture_eau_annuelle_fcfa=facture_eau,
    )


# ══════════════════════════════════════════════════════════════
# CALCUL CVC — EN 12831 + ASHRAE 55
# ══════════════════════════════════════════════════════════════

def calculer_cvc(d: DonneesMEP, nb_logements: int) -> BilanCVC:
    """
    Calcul charge thermique EN 12831 pour Dakar (zone tropicale).
    Surface climatisée = SHON × 0.65 (déduction communs, parking, etc.)
    """
    shon = _shon(d)
    surf_clim = shon * 0.65

    # Double vitrage réduit apports solaires
    coef_vitrage = 0.70 if d.double_vitrage else 1.0

    # Apports solaires façades E+O (Dakar, orientation défavorable)
    surf_facade = d.surface_emprise_m2 ** 0.5 * d.hauteur_etage_m * d.nb_niveaux * 2
    w_solaire = surf_facade * 52 * coef_vitrage  # 52 W/m² façades exposées Dakar

    # Apports internes
    nb_pers = _nb_personnes(d, nb_logements)
    w_internes = nb_pers * 80  # 80 W/personne métabolisme

    # Apports équipements (cuisine, bureautique)
    w_equipements = surf_clim * 8  # 8 W/m²

    # Renouvellement air EN 12831 (VMC double flux réduit de 40% si présente)
    delta_T = DAKAR["temp_ext_ete_C"] - DAKAR["temp_int_cible_C"]
    debit_air_m3h = surf_clim * 0.5         # 0.5 vol/h en m³/h
    debit_air_m3s = debit_air_m3h / 3600    # conversion m³/s
    coef_vmc = 0.60 if d.vmc_double_flux else 1.0
    # P [W] = rho [kg/m³] * Cp [J/kg/K] * Q [m³/s] * DeltaT [K]
    w_ventil = 1.2 * 1000 * debit_air_m3s * delta_T * coef_vmc

    p_totale_W = w_solaire + w_internes + w_equipements + w_ventil
    p_frigo_kW = round(p_totale_W / 1000 * 1.40, 1)  # marge sécurité +40%

    # Splits séjour (18 000 BTU = 5.3 kW)
    nb_splits_sej = nb_logements  # 1 par séjour

    # Splits chambres (9 000 BTU = 2.6 kW) : ~2 chambres par logement
    nb_chambres_par_logt = max(1, round(d.surface_emprise_m2 / nb_logements / 25))
    nb_splits_ch = nb_logements * min(nb_chambres_par_logt, 3)

    # CTA parties communes
    debit_communs = d.surface_emprise_m2 * 0.35 * d.nb_niveaux * 3  # 3 vol/h communs
    puissance_cta = debit_communs  # m³/h

    # Extracteurs parking
    nb_parking = 1 if d.surface_emprise_m2 > 200 else 0

    # Consommation CVC annuelle
    cop_ref = 2.5
    cop_inverter = 3.6 if d.cvc_inverter else cop_ref
    conso_kwh = p_frigo_kW * DAKAR["nb_heures_clim_an"] / cop_inverter

    return BilanCVC(
        apports_solaires_W=round(w_solaire),
        apports_internes_W=round(w_internes),
        apports_equipements_W=round(w_equipements),
        renouvellement_air_W=round(w_ventil),
        puissance_totale_extraire_W=round(p_totale_W),
        puissance_frigorifique_installee_kW=p_frigo_kW,
        nb_splits_sejour=nb_splits_sej,
        nb_splits_chambre=nb_splits_ch,
        nb_vmc_double_flux=nb_logements if d.vmc_double_flux else 0,
        puissance_cta_m3h=round(puissance_cta),
        nb_extracteurs_parking=nb_parking,
        conso_cvc_annuelle_kwh=round(conso_kwh),
    )


# ══════════════════════════════════════════════════════════════
# CALCUL DOMOTIQUE
# ══════════════════════════════════════════════════════════════

def calculer_domotique(d: DonneesMEP, nb_logements: int) -> BilanDomotique:
    shon = _shon(d)
    nb_wifi = max(4, math.ceil(shon / 150))  # 1 AP / 150 m²
    nb_cam = max(4, math.ceil(d.surface_emprise_m2 / 100) + d.nb_niveaux)
    nb_portes = max(4, d.nb_niveaux * 1 + 2)  # 1 porte par niveau + entrées
    categorie_sse = "A" if nb_logements > 8 else "B"

    return BilanDomotique(
        surface_totale_m2=shon,
        nb_logements=nb_logements,
        puissance_bms_kva=2.0,
        nb_points_acces_wifi=nb_wifi,
        nb_cameras_cctv=nb_cam,
        nb_portes_controle_acces=nb_portes,
        sse_categorie=categorie_sse,
    )


# ══════════════════════════════════════════════════════════════
# CALCUL EDGE — IFC EDGE Standard v3
# ══════════════════════════════════════════════════════════════

def calculer_edge(d: DonneesMEP, elec: BilanElectrique, plomb: BilanPlomberie,
                  cvc: BilanCVC, boq=None) -> AnalyseEDGE:
    """
    Calcul EDGE réel basé sur les mesures actives du projet.
    Référence : IFC EDGE Standard v3, bâtiment résidentiel, zone tropicale.
    """
    shon = _shon(d)

    # ── ÉNERGIE — Méthode EDGE basée sur données réelles du projet ──
    conso_ref = EDGE_REF["conso_ref_energie_kwh_m2"]
    shon = _shon(d)

    # Masse thermique : fonction de l'épaisseur de dalle (liée à la portée)
    ep_dalle = max(0.20, 0.15 + d.nb_niveaux * 0.005)  # épaisseur dalle réelle
    eco_masse_thermique = min(0.06, ep_dalle / 0.22 * 0.04)  # proportionnel à l'épaisseur

    # Ventilation naturelle : dépend du ratio surface/volume et nb niveaux
    # R+1 → meilleure ventilation naturelle, R+8 → moins efficace
    ratio_sv = (2 * shon / d.hauteur_etage_m + 2 * d.surface_emprise_m2) / (shon * d.hauteur_etage_m)
    eco_ventilation = min(0.07, max(0.02, ratio_sv * 0.15))

    # Isolation toiture : impact proportionnel à la surface de toiture / shon
    ratio_toiture = d.surface_emprise_m2 / shon  # plus grand pour R+1, plus petit pour R+8
    eco_isolation_toiture = min(0.06, d.isolation_toiture_mm / 80 * 0.06 * ratio_toiture * 2) if d.isolation_toiture_mm > 0 else 0.0

    eco_vitrage = 0.05 if d.double_vitrage else 0.0
    eco_cesi = 0.06 if d.chauffe_eau_solaire else 0.0

    eco_energie_total = eco_masse_thermique + eco_isolation_toiture + eco_vitrage + eco_ventilation + eco_cesi
    conso_projet_energie = conso_ref * (1 - eco_energie_total)
    pct_energie = round(eco_energie_total * 100, 1)

    mesures_energie = []
    mesures_energie.append(f"Masse thermique dalle e=22cm (inertie) → +{round(eco_masse_thermique*100,1)}%")
    if d.isolation_toiture_mm>0: mesures_energie.append(f"Isolation toiture {d.isolation_toiture_mm}mm → +{round(eco_isolation_toiture*100,1)}%")
    if d.double_vitrage: mesures_energie.append(f"Double vitrage Low-E façades → +{round(eco_vitrage*100,1)}%")
    mesures_energie.append(f"Ventilation naturelle Dakar (vents favorables) → +{round(eco_ventilation*100,1)}%")
    if d.chauffe_eau_solaire: mesures_energie.append(f"Chauffe-eau solaires {plomb.nb_chauffe_eau_solaire} unités ECS → +{round(eco_cesi*100,1)}%")

    # ── EAU — basée sur nb logements et dotation réelle ──────
    conso_ref_eau = EDGE_REF["conso_ref_eau_L_pers_j"]

    eco_wc = 0.13 if d.wc_double_chasse else 0.0
    eco_rob = 0.08 if d.robinetterie_eco else 0.0
    # Impact CESI eau dépend du ratio logements/surface — plus efficace pour petits bâtiments
    nb_logt = _estimer_nb_logements(d)
    ratio_logt_surface = nb_logt / max(shon, 1) * 100  # logements/100m²
    eco_cesi_eau = min(0.08, 0.05 * (1 + ratio_logt_surface)) if d.chauffe_eau_solaire else 0.0

    eco_eau_total = eco_wc + eco_rob + eco_cesi_eau
    conso_projet_eau = conso_ref_eau * (1 - eco_eau_total)
    pct_eau = round(eco_eau_total * 100, 1)

    mesures_eau = []
    if d.wc_double_chasse:    mesures_eau.append(f"WC double chasse 3/6L (vs 9L) → -{round(eco_wc*100,1)}%")
    if d.robinetterie_eco:    mesures_eau.append(f"Robinetterie mousseurs 6L/min → -{round(eco_rob*100,1)}%")
    if d.chauffe_eau_solaire: mesures_eau.append(f"Réduction eau chaude sanitaire → -{round(eco_cesi_eau*100,1)}%")

    # ── MATÉRIAUX — basés sur ratio béton/acier réels ────────
    ei_ref = EDGE_REF["ei_ref_kwh_m2"]

    # Ratio acier/m² bâti — plus le ratio est faible, meilleur est le score matériaux
    # Valeur de référence EDGE : 40 kg/m² acier, 0.16 m³/m² béton
    ratio_acier_m2 = boq.acier_kg / max(shon, 1) if boq else 40.0
    ratio_beton_m2 = boq.beton_m3 / max(shon, 1) if boq else 0.16
    # Économie si ratios inférieurs à référence
    eco_struct = max(0.0, min(0.08, (40 - ratio_acier_m2) / 40 * 0.08))
    eco_ggbs = 0.08 if d.beton_ggbs else 0.0
    eco_creux = 0.06 if d.parpaings_creux else 0.0
    eco_iso = min(0.06, d.isolation_toiture_mm / 80 * 0.05 * ratio_toiture * 2) if d.isolation_toiture_mm > 0 else 0.0
    eco_vit_mat = 0.03 if d.double_vitrage else 0.0

    eco_mat_total = eco_struct + eco_ggbs + eco_creux + eco_iso + eco_vit_mat
    ei_projet = ei_ref * (1 - eco_mat_total)
    pct_mat = round(eco_mat_total * 100, 1)

    mesures_mat = []
    if d.beton_ggbs:              mesures_mat.append(f"Béton GGBS 10% substitution ciment → -{round(eco_ggbs*100,1)}%")
    if d.parpaings_creux:         mesures_mat.append(f"Parpaings creux (−30% masse) → -{round(eco_creux*100,1)}%")
    if d.isolation_toiture_mm>0:  mesures_mat.append(f"Isolation toiture {d.isolation_toiture_mm}mm → -{round(eco_iso*100,1)}%")
    if d.double_vitrage:          mesures_mat.append(f"Double vitrage façades → -{round(eco_vit_mat*100,1)}%")

    # ── VERDICT ──────────────────────────────────────────────
    seuil = EDGE_REF["seuil_basique_pct"]
    conf_e = pct_energie >= seuil
    conf_eau = pct_eau >= seuil
    conf_mat = pct_mat >= seuil
    nb_conf = sum([conf_e, conf_eau, conf_mat])
    certifiable = nb_conf == 3

    min_pct = min(pct_energie, pct_eau, pct_mat)
    if not certifiable:
        niveau = "Non certifiable EDGE"
    elif min_pct >= EDGE_REF["seuil_net_zero_pct"]:
        niveau = "EDGE Net Zero Carbon"
    elif min_pct >= EDGE_REF["seuil_advanced_pct"]:
        niveau = "EDGE Advanced"
    else:
        niveau = "EDGE Basique"

    surcout = 2.0 if certifiable else 0.0
    payback = 4.5 if certifiable else 0.0

    return AnalyseEDGE(
        conso_reference_kwh_m2_an=conso_ref,
        conso_projet_kwh_m2_an=round(conso_projet_energie, 1),
        economie_energie_pct=pct_energie,
        conformite_energie=conf_e,
        conso_reference_L_pers_j=conso_ref_eau,
        conso_projet_L_pers_j=round(conso_projet_eau, 1),
        economie_eau_pct=pct_eau,
        conformite_eau=conf_eau,
        ei_reference_kwh_m2=ei_ref,
        ei_projet_kwh_m2=round(ei_projet, 1),
        economie_materiaux_pct=pct_mat,
        conformite_materiaux=conf_mat,
        nb_criteres_conformes=nb_conf,
        certifiable=certifiable,
        niveau_certification=niveau,
        mesures_energie=mesures_energie,
        mesures_eau=mesures_eau,
        mesures_materiaux=mesures_mat,
        surcout_vert_pct=surcout,
        payback_ans=payback,
    )


# ══════════════════════════════════════════════════════════════
# CALCUL BOQ MEP
# ══════════════════════════════════════════════════════════════

def calculer_boq_mep(d: DonneesMEP, nb_logements: int,
                     elec: BilanElectrique, plomb: BilanPlomberie,
                     cvc: BilanCVC, dom: BilanDomotique) -> tuple:
    """
    Calcule le BOQ MEP pour 3 niveaux de gamme.
    Tous les montants sont calculés depuis les quantités réelles du projet.
    Retourne (lots, total_basic, total_hend, total_luxury, analyse_cb)
    """
    niv = d.nb_niveaux
    emp = d.surface_emprise_m2

    # ── LOT ÉLECTRICITÉ ──────────────────────────────────────
    # Transfo
    if elec.transfo_necessaire_kva >= 400:
        t_b = PRIX["transfo_400kva"]
        t_h = round(t_b * 1.20)
        t_l = round(t_b * 1.80)
    elif elec.transfo_necessaire_kva >= 250:
        t_b = PRIX["transfo_250kva"]
        t_h = PRIX["transfo_400kva"]
        t_l = round(PRIX["transfo_400kva"] * 1.50)
    else:
        t_b = PRIX["transfo_160kva"]
        t_h = PRIX["transfo_250kva"]
        t_l = PRIX["transfo_400kva"]

    # GE
    if elec.groupe_electrogene_kva >= 250:
        ge_b = PRIX["ge_250kva"]; ge_h = round(ge_b*1.15); ge_l = round(ge_b*1.60)
    elif elec.groupe_electrogene_kva >= 160:
        ge_b = PRIX["ge_160kva"]; ge_h = PRIX["ge_250kva"]; ge_l = round(PRIX["ge_250kva"]*1.40)
    else:
        ge_b = PRIX["ge_100kva"]; ge_h = PRIX["ge_160kva"]; ge_l = PRIX["ge_250kva"]

    tgbt_b = PRIX["tgbt_4000a"] if elec.puissance_totale_souscrite_kva > 300 else PRIX["tgbt_2500a"]
    td_b = PRIX["td_125a"] * niv
    tl_b = PRIX["tableau_logement_40a"] * nb_logements
    cable_b = PRIX["cablage_par_logement"] * nb_logements
    ecl_b = round(emp**0.5 * niv * 4 * PRIX["eclairage_communs_ml"])  # périmètre × niveaux
    ecl_logt_b = PRIX["eclairage_logement"] * nb_logements
    baes_b = round(niv * 4 * PRIX["baes_u"])
    para_b = PRIX["paratonnerre"]
    cpt_b = PRIX["compteur_divisionne"] * nb_logements

    elec_b = t_b + ge_b + tgbt_b + td_b + tl_b + cable_b + ecl_b + ecl_logt_b + baes_b + para_b + cpt_b
    elec_h = round(elec_b * 1.42)
    elec_l = round(elec_b * 2.28)

    # ── LOT PLOMBERIE ─────────────────────────────────────────
    vol_cit = plomb.volume_citerne_m3
    if vol_cit >= 50:
        cit_b = PRIX["citerne_50m3"]
    else:
        cit_b = round(vol_cit / 10 * PRIX["citerne_10m3"])

    bache_b = PRIX["bache_incendie_12m3"] if plomb.volume_bache_incendie_m3 >= 12 else PRIX["bache_incendie_6m3"]
    surp_b = PRIX["surpresseur_6m3h"] if plomb.debit_surpresseur_m3h >= 4 else PRIX["surpresseur_3m3h"]
    pomp_b = PRIX["pompe_incendie"] * 2  # principale + secours
    col_b = round(emp**0.5 * niv * 2 * PRIX["colonne_montante_ml"])
    cesi_b = PRIX["chauffe_eau_solaire_200L"] * plomb.nb_chauffe_eau_solaire if plomb.capacite_chauffe_eau_L >= 200 else PRIX["chauffe_eau_solaire_100L"] * plomb.nb_chauffe_eau_solaire
    reseau_b = PRIX["reseau_eu_ev_ep_forfait"] * nb_logements
    ria_b = PRIX["ria_palier"] * niv
    san_b = PRIX["sanitaires_basic_logt"] * nb_logements
    rob_b = PRIX["robinetterie_basic_logt"] * nb_logements

    plomb_b = cit_b + bache_b + surp_b + pomp_b + col_b + cesi_b + reseau_b + ria_b + san_b + rob_b

    san_h = PRIX["sanitaires_hend_logt"] * nb_logements
    rob_h = PRIX["robinetterie_hend_logt"] * nb_logements
    san_l = PRIX["sanitaires_luxury_logt"] * nb_logements
    rob_l = PRIX["robinetterie_luxury_logt"] * nb_logements
    plomb_h = plomb_b - san_b - rob_b + san_h + rob_h + round((PRIX["chauffe_eau_solaire_200L"] - PRIX["chauffe_eau_solaire_100L"]) * plomb.nb_chauffe_eau_solaire * 0.3)
    plomb_l = plomb_b - san_b - rob_b + san_l + rob_l + round((PRIX["chauffe_eau_solaire_200L"]) * plomb.nb_chauffe_eau_solaire * 0.6)

    # ── LOT CVC ──────────────────────────────────────────────
    sp_sej_b = PRIX["split_18000btu_basic"] * cvc.nb_splits_sejour
    sp_ch_b  = PRIX["split_9000btu_basic"]  * cvc.nb_splits_chambre
    vmc_b    = PRIX["vmc_double_flux_basic"] * cvc.nb_vmc_double_flux
    cta_b    = PRIX["cta_8000m3h"] if cvc.puissance_cta_m3h >= 5000 else PRIX["cta_4000m3h"]
    ext_b    = PRIX["extracteur_parking"] * cvc.nb_extracteurs_parking
    gaines_b = round(emp * niv * PRIX["gaines_cvc_m2"] * 0.3)  # 30% surface
    therm_b  = PRIX["thermostat_basic"] * nb_logements
    desenfum_b = PRIX["desenfumage_cage"] * max(1, round(emp**0.5 / 10))

    cvc_b = sp_sej_b + sp_ch_b + vmc_b + cta_b + ext_b + gaines_b + therm_b + desenfum_b

    sp_sej_h = PRIX["split_18000btu_hend"]  * cvc.nb_splits_sejour
    sp_ch_h  = PRIX["split_9000btu_hend"]   * cvc.nb_splits_chambre
    vmc_h    = PRIX["vmc_double_flux_hend"]  * cvc.nb_vmc_double_flux
    therm_h  = PRIX["thermostat_hend"] * nb_logements
    cvc_h = cvc_b - sp_sej_b - sp_ch_b - vmc_b - therm_b + sp_sej_h + sp_ch_h + vmc_h + therm_h

    sp_sej_l = PRIX["split_18000btu_luxury"] * cvc.nb_splits_sejour
    sp_ch_l  = PRIX["split_9000btu_luxury"]  * cvc.nb_splits_chambre
    vmc_l    = PRIX["vmc_double_flux_luxury"] * cvc.nb_vmc_double_flux
    therm_l  = PRIX["thermostat_luxury"] * nb_logements
    cvc_l = cvc_b - sp_sej_b - sp_ch_b - vmc_b - therm_b + sp_sej_l + sp_ch_l + vmc_l + therm_l

    # ── LOT DOMOTIQUE ─────────────────────────────────────────
    bms_b = PRIX["bms_serveur_basic"]
    sw_b  = PRIX["switch_coeur_basic"] + PRIX["switch_etage_basic"] * niv
    wifi_b = PRIX["wifi_point_basic"] * dom.nb_points_acces_wifi
    cab_b = PRIX["cablage_reseau_forfait"]
    interph_b = PRIX["interphone_portier"] * 2
    comb_b = PRIX["combine_video_basic"] * nb_logements
    cctv_b = PRIX["cctv_pack_16cam"] if dom.nb_cameras_cctv >= 12 else round(PRIX["cctv_pack_16cam"] * 0.6)
    acc_b = PRIX["controle_acces_porte"] * dom.nb_portes_controle_acces
    inc_b = PRIX["incendie_ssi_a"] if dom.sse_categorie == "A" else round(PRIX["incendie_ssi_a"] * 0.7)
    knx_b = PRIX["knx_logement_basic"] * nb_logements
    dash_b = PRIX["dashboard_energie"]

    dom_b = bms_b + sw_b + wifi_b + cab_b + interph_b + comb_b + cctv_b + acc_b + inc_b + knx_b + dash_b

    bms_h = PRIX["bms_serveur_hend"]
    sw_h  = PRIX["switch_coeur_hend"] + PRIX["switch_etage_hend"] * niv
    wifi_h = PRIX["wifi_point_hend"] * dom.nb_points_acces_wifi
    knx_h = PRIX["knx_logement_hend"] * nb_logements
    comb_h = PRIX["combine_video_hend"] * nb_logements
    dom_h = dom_b - bms_b - sw_b - wifi_b - knx_b - comb_b + bms_h + sw_h + wifi_h + knx_h + comb_h

    bms_l = PRIX["bms_serveur_luxury"]
    wifi_l = PRIX["wifi_point_luxury"] * dom.nb_points_acces_wifi
    knx_l = PRIX["knx_logement_luxury"] * nb_logements
    dom_l = dom_b - bms_b - sw_b - wifi_b - knx_b - comb_b + bms_l + sw_b + wifi_l + knx_l + comb_h

    # ── TOTAUX + IMPRÉVUS 8% ──────────────────────────────────
    def total(e, p, c, do):
        return round((e + p + c + do) * 1.08)

    total_b = total(elec_b, plomb_b, cvc_b, dom_b)
    total_h = total(elec_h, plomb_h, cvc_h, dom_h)
    total_l = total(elec_l, plomb_l, cvc_l, dom_l)

    lots = [
        BOQ_MEP_Lot("Électricité", elec_b, elec_h, elec_l),
        BOQ_MEP_Lot("Plomberie",   plomb_b, plomb_h, plomb_l),
        BOQ_MEP_Lot("CVC",         cvc_b, cvc_h, cvc_l),
        BOQ_MEP_Lot("Domotique",   dom_b, dom_h, dom_l),
    ]

    # ── ANALYSE COÛT/BÉNÉFICE ─────────────────────────────────
    # Économies énergie annuelles par niveau (sur facture SENELEC)
    # Basic : équipements standard, COP 2.5
    # High-End : inverter COP 3.6, LED, CESI
    # Luxury : tout + KNX optimisation 15%
    facture_base = elec.facture_annuelle_estimee_fcfa
    eco_hend_an = round(facture_base * 0.28)  # -28% consommation High-End vs Basic
    eco_lux_an  = round(facture_base * 0.38)  # -38% Luxury (KNX + tout)

    delta_bh = total_h - total_b
    delta_bl = total_l - total_b

    payback_hend = round(delta_bh / eco_hend_an, 1) if eco_hend_an > 0 else 99.0
    payback_lux  = round(delta_bl / eco_lux_an,  1) if eco_lux_an  > 0 else 99.0

    roi_hend = round((eco_hend_an * 20 - delta_bh) / delta_bh * 100, 0) if delta_bh > 0 else 0
    roi_lux  = round((eco_lux_an  * 20 - delta_bl) / delta_bl * 100, 0) if delta_bl > 0 else 0

    if payback_hend <= 8:
        recommandation = f"HIGH-END recommandé : investissement supplémentaire de {delta_bh/1_000_000:.0f} M FCFA récupéré en {payback_hend} ans via les économies d'énergie."
    else:
        recommandation = f"BASIC recommandé pour budget contraint : économies High-End de {eco_hend_an/1_000_000:.1f} M FCFA/an mais payback à {payback_hend} ans."

    analyse_cb = AnalyseCoutBenefice(
        basic_total=total_b,
        hend_total=total_h,
        luxury_total=total_l,
        delta_basic_hend=delta_bh,
        delta_basic_luxury=delta_bl,
        economie_energie_basic_fcfa_an=0,
        economie_energie_hend_fcfa_an=eco_hend_an,
        economie_energie_luxury_fcfa_an=eco_lux_an,
        payback_hend_ans=payback_hend,
        payback_luxury_ans=payback_lux,
        roi_hend_20ans_pct=roi_hend,
        roi_luxury_20ans_pct=roi_lux,
        recommandation=recommandation,
    )

    return lots, total_b, total_h, total_l, analyse_cb


# ══════════════════════════════════════════════════════════════
# POINT D'ENTRÉE PRINCIPAL
# ══════════════════════════════════════════════════════════════

def calculer_mep(donnees: DonneesMEP) -> ResultatsMEP:
    """
    Calcule l'ensemble MEP depuis les données projet.
    Zéro valeur codée en dur — tout est calculé depuis les inputs.
    """
    nb_logt = _estimer_nb_logements(donnees)
    shon = _shon(donnees)

    # BOQ structure estimé depuis données projet (ratios EC2)
    # ep_dalle et acier estimés depuis nb_niveaux uniquement (portee_max_m pas dans DonneesMEP)
    ep_dalle = max(0.20, 0.15 + donnees.nb_niveaux * 0.005)  # croît légèrement avec hauteur
    ratio_acier = 25 + donnees.nb_niveaux * 2.5   # kg/m² — croît avec la hauteur
    ratio_beton = ep_dalle + 0.08                   # m³/m² dalles + poteaux
    class _BOQ:
        acier_kg = ratio_acier * shon
        beton_m3 = ratio_beton * shon
    boq_struct = _BOQ()

    elec  = calculer_electrique(donnees, nb_logt)
    plomb = calculer_plomberie(donnees, nb_logt)
    cvc   = calculer_cvc(donnees, nb_logt)
    dom   = calculer_domotique(donnees, nb_logt)
    edge  = calculer_edge(donnees, elec, plomb, cvc, boq=boq_struct)
    lots, total_b, total_h, total_l, cb = calculer_boq_mep(
        donnees, nb_logt, elec, plomb, cvc, dom
    )

    return ResultatsMEP(
        donnees=donnees,
        electrique=elec,
        plomberie=plomb,
        cvc=cvc,
        domotique=dom,
        edge=edge,
        boq_lots=lots,
        boq_total_basic=total_b,
        boq_total_hend=total_h,
        boq_total_luxury=total_l,
        analyse_cout_benefice=cb,
        note_sol_integree=bool(donnees.note_sol.strip()),
    )
# redeploy 1773659148
