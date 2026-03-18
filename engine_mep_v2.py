"""
engine_mep_v2.py — Moteur de calcul MEP Tijan AI
═════════════════════════════════════════════════
Références normatives :
  Électricité   : NF C 15-100 (installations BT)
  Plomberie     : DTU 60.11 — ONAS dotation 150 L/pers/j
  CVC           : EN 12831 (charge thermique) — ASHRAE 55 (confort)
  Courants fbl  : NF C 15-100 titre 7 — câblage structuré
  Sécurité inc. : IT 246 (France/Sénégal) — ERP/IGH
  Ascenseurs    : EN 81-20/50 — NF EN 81-1/2
  Automatisation: KNX standard — protocole BACnet

Projets couverts : villa, résidentiel, bureau, hôtel, mixte
Pays couverts   : Sénégal, Côte d'Ivoire, Maroc, Nigeria, Ghana

Auteur : Tijan AI
Version : 2.0 — Mars 2026
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum


# ══════════════════════════════════════════════════════════════
# IMPORTS
# ══════════════════════════════════════════════════════════════

try:
    from engine_structure_v2 import DonneesProjet, Usage, ResultatsStructure
except ImportError:
    # Fallback si moteur structure absent
    from enum import Enum
    class Usage(str, Enum):
        RESIDENTIEL = "residentiel"
        BUREAU      = "bureau"
        HOTEL       = "hotel"
        MIXTE       = "mixte"
        COMMERCIAL  = "commercial"
        INDUSTRIEL  = "industriel"

    @dataclass
    class DonneesProjet:
        nom: str = "Projet"
        ville: str = "Dakar"
        pays: str = "Senegal"
        usage: Usage = Usage.RESIDENTIEL
        nb_niveaux: int = 5
        hauteur_etage_m: float = 3.0
        surface_emprise_m2: float = 500.0
        portee_max_m: float = 6.0
        portee_min_m: float = 4.5
        nb_travees_x: int = 4
        nb_travees_y: int = 3
        distance_mer_km: float = 2.0
        pression_sol_MPa: float = 0.15
        zone_sismique: int = 1
        classe_beton: str = "C30/37"
        classe_acier: str = "HA500"
        surface_terrain_m2: float = 0.0
        sol_context: str = ""
        avec_sous_sol: bool = False
        nb_sous_sols: int = 0


# ══════════════════════════════════════════════════════════════
# DONNÉES CLIMATIQUES DAKAR ET VILLES CIBLES
# ══════════════════════════════════════════════════════════════

CLIMAT = {
    "dakar":       {"T_ext": 35, "T_confort": 26, "humidite": 75, "ensoleillement": "fort"},
    "abidjan":     {"T_ext": 33, "T_confort": 25, "humidite": 85, "ensoleillement": "fort"},
    "casablanca":  {"T_ext": 30, "T_confort": 24, "humidite": 60, "ensoleillement": "moyen"},
    "rabat":       {"T_ext": 29, "T_confort": 24, "humidite": 65, "ensoleillement": "moyen"},
    "lagos":       {"T_ext": 34, "T_confort": 25, "humidite": 85, "ensoleillement": "fort"},
    "accra":       {"T_ext": 32, "T_confort": 25, "humidite": 80, "ensoleillement": "fort"},
}

# Dotation eau par usage (L/pers/j)
DOTATION_EAU = {
    Usage.RESIDENTIEL: 150,   # ONAS Sénégal
    Usage.BUREAU:      25,    # Bureaux
    Usage.HOTEL:       300,   # Hôtel (chambre + services)
    Usage.MIXTE:       120,
    Usage.COMMERCIAL:  20,
    Usage.INDUSTRIEL:  50,
}

# Puissance électrique par m² (W/m²) selon usage
PUISSANCE_ELEC_Wm2 = {
    Usage.RESIDENTIEL: 40,
    Usage.BUREAU:      80,
    Usage.HOTEL:       100,
    Usage.MIXTE:       60,
    Usage.COMMERCIAL:  120,
    Usage.INDUSTRIEL:  150,
}

# Tarifs énergie/eau par ville (FCFA)
TARIFS = {
    "dakar":       {"kwh": 105, "m3_eau": 750},
    "abidjan":     {"kwh": 95,  "m3_eau": 650},
    "casablanca":  {"kwh": 78,  "m3_eau": 420},
    "rabat":       {"kwh": 78,  "m3_eau": 420},
    "lagos":       {"kwh": 50,  "m3_eau": 300},
    "accra":       {"kwh": 85,  "m3_eau": 500},
}


# ══════════════════════════════════════════════════════════════
# RÉSULTATS
# ══════════════════════════════════════════════════════════════

@dataclass
class BilanElectrique:
    # Puissances
    puissance_totale_kva:       float
    puissance_eclairage_kw:     float
    puissance_prises_kw:        float
    puissance_cvc_kw:           float
    puissance_ascenseurs_kw:    float
    puissance_divers_kw:        float
    # Équipements
    transfo_kva:                int
    groupe_electrogene_kva:     int
    nb_compteurs:               int
    section_colonne_mm2:        int
    # Consommation
    conso_annuelle_kwh:         float
    facture_annuelle_fcfa:      int
    # Explication impact prix
    note_dimensionnement:       str
    marques_recommandees:       List[str]

@dataclass
class BilanPlomberie:
    nb_logements:               int
    nb_personnes:               int
    besoin_total_m3_j:          float
    # Équipements
    volume_citerne_m3:          float
    debit_surpresseur_m3h:      float
    nb_chauffe_eau_solaire:     int
    nb_wc_double_chasse:        int
    nb_robinets_eco:            int
    diam_colonne_montante_mm:   int
    # Consommation
    conso_eau_annuelle_m3:      float
    facture_eau_fcfa:           int
    # Explications
    note_dimensionnement:       str
    marques_recommandees:       List[str]

@dataclass
class BilanCVC:
    puissance_frigorifique_kw:  float
    nb_splits_sejour:           int
    nb_splits_chambre:          int
    nb_cassettes:               int
    nb_vmc:                     int
    type_vmc:                   str
    conso_cvc_kwh_an:           float
    # Explication
    note_dimensionnement:       str
    marques_recommandees:       List[str]

@dataclass
class BilanCourantsFaibles:
    nb_prises_rj45:             int
    nb_cameras_int:             int
    nb_cameras_ext:             int
    nb_portes_controle_acces:   int
    nb_interphones:             int
    baies_serveur:              int
    systeme_audio_video:        bool
    # Explication
    note_dimensionnement:       str
    marques_recommandees:       List[str]

@dataclass
class BilanSecuriteIncendie:
    categorie_erp:              str
    nb_detecteurs_fumee:        int
    nb_declencheurs_manuels:    int
    nb_sirenes:                 int
    nb_extincteurs_co2:         int
    nb_extincteurs_poudre:      int
    longueur_ria_ml:            float
    nb_tetes_sprinkler:         int
    centrale_zones:             int
    desenfumage_requis:         bool
    sprinklers_requis:          bool
    # Explication
    note_dimensionnement:       str
    marques_recommandees:       List[str]

@dataclass
class BilanAscenseurs:
    nb_ascenseurs:              int
    capacite_kg:                int
    vitesse_ms:                 float
    nb_monte_charges:           int
    nb_escalators:              int
    puissance_totale_kw:        float
    # Explication
    note_dimensionnement:       str
    note_impact_prix:           str
    marques_recommandees:       List[str]

@dataclass
class BilanAutomatisation:
    niveau:                     str  # "basic" | "standard" | "premium"
    protocole:                  str  # "KNX" | "BACnet" | "Modbus"
    nb_points_controle:         int
    gestion_eclairage:          bool
    gestion_cvc:                bool
    gestion_acces:              bool
    gestion_energie:            bool
    bms_requis:                 bool
    # Explication
    note_dimensionnement:       str
    marques_recommandees:       List[str]

@dataclass
class ScoreEDGE:
    # Scores calculés depuis données réelles
    economie_energie_pct:       float
    economie_eau_pct:           float
    economie_materiaux_pct:     float
    # Détail calcul énergie
    base_energie_kwh_m2_an:     float  # Bâtiment référence
    projet_energie_kwh_m2_an:   float  # Bâtiment projet
    mesures_energie:            List[Dict]  # {mesure, gain_pct, statut, impact_prix}
    # Détail calcul eau
    base_eau_L_pers_j:          float
    projet_eau_L_pers_j:        float
    mesures_eau:                List[Dict]
    # Détail calcul matériaux
    base_ei_kwh_m2:             float
    projet_ei_kwh_m2:           float
    mesures_materiaux:          List[Dict]
    # Verdict
    certifiable:                bool
    niveau_certification:       str
    # Plan d'action optimisation (si non certifiable)
    plan_action:                List[Dict]  # {action, gain_pct, cout_fcfa, pilier}
    cout_mise_conformite_fcfa:  int
    roi_ans:                    float
    # Meta
    methode_calcul:             str
    note_generale:              str

@dataclass
class BOQ_Lot:
    lot:            str
    designation:    str
    unite:          str
    quantite:       float
    pu_basic_fcfa:  int
    pu_hend_fcfa:   int
    pu_luxury_fcfa: int
    note_impact:    str  # Explication impact prix si significatif

@dataclass
class BOQ_MEP:
    lots:               List[BOQ_Lot]
    total_basic_fcfa:   int
    total_hend_fcfa:    int
    total_luxury_fcfa:  int
    ratio_basic_m2:     int
    ratio_hend_m2:      int
    recommandation:     str
    note_choix:         str

@dataclass
class ResultatsMEP:
    params:             DonneesProjet
    shon_m2:            float
    nb_logements:       int
    nb_personnes:       int
    # Bilans par corps d'état
    electrique:         BilanElectrique
    plomberie:          BilanPlomberie
    cvc:                BilanCVC
    courants_faibles:   BilanCourantsFaibles
    securite_incendie:  BilanSecuriteIncendie
    ascenseurs:         BilanAscenseurs
    automatisation:     BilanAutomatisation
    # EDGE
    edge:               ScoreEDGE
    # BOQ
    boq:                BOQ_MEP


# ══════════════════════════════════════════════════════════════
# UTILITAIRES
# ══════════════════════════════════════════════════════════════

def _shon(d: DonneesProjet) -> float:
    return d.surface_emprise_m2 * d.nb_niveaux

def _get_ville_key(ville: str) -> str:
    return ville.lower().strip()

def _estimer_logements(d: DonneesProjet, shon: float) -> int:
    if d.usage == Usage.RESIDENTIEL:
        return max(1, round(shon * 0.85 / 80))  # 80m² moyen/logement, 85% SHON habitable
    elif d.usage == Usage.HOTEL:
        return max(1, round(shon * 0.60 / 35))  # 35m² chambre, 60% SHON chambres
    elif d.usage == Usage.BUREAU:
        return max(1, round(shon * 0.85 / 15))  # 15m²/poste de travail
    elif d.usage == Usage.MIXTE:
        return max(1, round(shon * 0.50 / 80))
    return max(1, round(shon / 100))

def _get_tarifs(ville: str) -> dict:
    return TARIFS.get(_get_ville_key(ville), TARIFS["dakar"])

def _get_climat(ville: str) -> dict:
    return CLIMAT.get(_get_ville_key(ville), CLIMAT["dakar"])

def _categorie_erp(d: DonneesProjet, nb_personnes: int) -> str:
    """Catégorie ERP selon IT 246."""
    if d.usage == Usage.HOTEL:
        if nb_personnes > 1500: return "ERP 1ère catégorie"
        elif nb_personnes > 700: return "ERP 2ème catégorie"
        elif nb_personnes > 300: return "ERP 3ème catégorie"
        else: return "ERP 4ème catégorie"
    elif d.usage == Usage.BUREAU:
        if d.nb_niveaux >= 28: return "IGH — Immeuble Grande Hauteur"
        elif nb_personnes > 3000: return "ERP 1ère catégorie"
        else: return "ERP 3ème catégorie"
    else:
        if d.nb_niveaux >= 8: return "ERP 3ème catégorie (résidentiel collectif)"
        elif d.nb_niveaux >= 4: return "ERP 4ème catégorie"
        return "Bâtiment d'habitation — Code construction"


# ══════════════════════════════════════════════════════════════
# CALCUL ÉLECTRICITÉ
# ══════════════════════════════════════════════════════════════

def _calculer_electrique(d: DonneesProjet, shon: float,
                          nb_logements: int, prix_mep) -> BilanElectrique:
    ville_key = _get_ville_key(d.ville)
    tarifs = _get_tarifs(ville_key)

    # Puissances par poste (kW)
    p_eclairage = shon * 0.010   # 10 W/m²
    p_prises     = shon * PUISSANCE_ELEC_Wm2[d.usage] / 1000 * 0.4
    p_cvc        = shon * 0.060  # 60 W/m² CVC (tropiques)
    p_asc        = max(0, (d.nb_niveaux - 2) * 5.5) if d.nb_niveaux > 2 else 0
    p_divers     = shon * 0.008  # Divers (pompes, ventilation, secours)

    p_total_kw   = p_eclairage + p_prises + p_cvc + p_asc + p_divers
    foisonnement = max(0.55, 0.85 - nb_logements * 0.008)  # Décroît avec nb logements
    p_appelee_kw = p_total_kw * foisonnement
    p_kva        = p_appelee_kw / 0.85  # cos phi = 0.85

    # Transformateur (puissance normalisée)
    transfo_std = [100, 160, 250, 400, 630, 1000]
    transfo_kva = next((t for t in transfo_std if t >= p_kva * 1.25), 1000)

    # Groupe électrogène (60% transfo pour alimentation de sécurité)
    ge_std = [60, 100, 160, 200, 250, 400, 500]
    ge_kva = next((g for g in ge_std if g >= transfo_kva * 0.60), 400)

    # Compteurs
    nb_compteurs = nb_logements
    if d.usage in [Usage.BUREAU, Usage.COMMERCIAL]:
        nb_compteurs = max(1, d.nb_niveaux)

    # Section colonne montante
    I = p_appelee_kw * 1000 / (400 * math.sqrt(3) * 0.85)
    sections = [10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240]
    section_mm2 = next((s for s in sections if s >= I * 0.6), 240)

    # Consommation annuelle
    h_an = 8760
    taux_util = 0.35 if d.usage == Usage.RESIDENTIEL else 0.45
    conso_kwh = p_appelee_kw * h_an * taux_util
    facture = int(conso_kwh * tarifs["kwh"])

    # Note impact prix
    note = f"Puissance installée {p_kva:.0f} kVA → transformateur {transfo_kva} kVA"
    if transfo_kva >= 400:
        note += f". ⚠ Transformateur ≥400 kVA : coût élevé ({prix_mep.transfo_400kva/1e6:.0f} M FCFA)"
    if p_asc > 0:
        note += f". Ascenseurs représentent {p_asc/p_total_kw*100:.0f}% de la puissance installée"

    marques = ["Schneider Electric (Dakar : CFAO Technologies)",
               "ABB (représentant local : SENELEC partenaires)",
               "Siemens (bureau Dakar)"]

    return BilanElectrique(
        puissance_totale_kva=round(p_kva, 1),
        puissance_eclairage_kw=round(p_eclairage, 1),
        puissance_prises_kw=round(p_prises, 1),
        puissance_cvc_kw=round(p_cvc, 1),
        puissance_ascenseurs_kw=round(p_asc, 1),
        puissance_divers_kw=round(p_divers, 1),
        transfo_kva=transfo_kva,
        groupe_electrogene_kva=ge_kva,
        nb_compteurs=nb_compteurs,
        section_colonne_mm2=section_mm2,
        conso_annuelle_kwh=round(conso_kwh, 0),
        facture_annuelle_fcfa=facture,
        note_dimensionnement=note,
        marques_recommandees=marques,
    )


# ══════════════════════════════════════════════════════════════
# CALCUL PLOMBERIE
# ══════════════════════════════════════════════════════════════

def _calculer_plomberie(d: DonneesProjet, shon: float,
                         nb_logements: int, nb_personnes: int,
                         prix_mep) -> BilanPlomberie:
    tarifs = _get_tarifs(_get_ville_key(d.ville))
    dotation = DOTATION_EAU[d.usage]

    # Besoin journalier
    Q_j_m3 = nb_personnes * dotation / 1000

    # Citerne (autonomie 2 jours + 25% sécurité)
    V_cuve = Q_j_m3 * 2.5
    V_cuve_std = next((v for v in [5, 10, 15, 20, 30, 50] if v >= V_cuve), 50)

    # Débit surpresseur (débit de pointe = 0.3 * Q_j en m³/h)
    Q_pointe_m3h = Q_j_m3 * 0.3
    Q_surp_std = next((q for q in [2, 4, 6, 8, 12, 16, 20] if q >= Q_pointe_m3h), 20)

    # Chauffe-eau solaires (CESI)
    # 1 CESI 200L pour 4 personnes (ECS = 40L/pers/j)
    nb_cesi = max(0, math.ceil(nb_personnes / 4))
    if d.usage == Usage.BUREAU:
        nb_cesi = 0  # Pas d'ECS en bureau standard

    # WC double chasse et robinetterie éco
    nb_wc = nb_logements * 2 if d.usage in [Usage.RESIDENTIEL, Usage.HOTEL] else math.ceil(shon / 50)
    nb_rob = nb_logements * 3 if d.usage in [Usage.RESIDENTIEL, Usage.HOTEL] else math.ceil(shon / 30)

    # Diamètre colonne montante
    Q_max_ls = Q_pointe_m3h * 1000 / 3600  # L/s
    if Q_max_ls <= 2: diam_col = 40
    elif Q_max_ls <= 5: diam_col = 50
    elif Q_max_ls <= 10: diam_col = 63
    elif Q_max_ls <= 20: diam_col = 75
    else: diam_col = 100

    # Consommation annuelle
    conso_an_m3 = Q_j_m3 * 365
    facture = int(conso_an_m3 * tarifs["m3_eau"])

    # Note impact prix
    note = f"Dotation {dotation} L/pers/j × {nb_personnes} personnes = {Q_j_m3:.1f} m³/j"
    if V_cuve_std >= 20:
        note += f". Citerne {V_cuve_std}m³ : investissement significatif"
    if nb_cesi > 0:
        cout_cesi = nb_cesi * prix_mep.chauffe_eau_solaire_200l
        note += f". {nb_cesi} CESI : {cout_cesi/1e6:.1f} M FCFA — économies eau chaude ~30%"

    marques = ["Grundfos (pompes — représentant Dakar)",
               "Sandef (sanitaires locaux)",
               "Grohe / Roca (robinetterie premium — importé)"]

    return BilanPlomberie(
        nb_logements=nb_logements,
        nb_personnes=nb_personnes,
        besoin_total_m3_j=round(Q_j_m3, 2),
        volume_citerne_m3=float(V_cuve_std),
        debit_surpresseur_m3h=float(Q_surp_std),
        nb_chauffe_eau_solaire=nb_cesi,
        nb_wc_double_chasse=nb_wc,
        nb_robinets_eco=nb_rob,
        diam_colonne_montante_mm=diam_col,
        conso_eau_annuelle_m3=round(conso_an_m3, 0),
        facture_eau_fcfa=facture,
        note_dimensionnement=note,
        marques_recommandees=marques,
    )


# ══════════════════════════════════════════════════════════════
# CALCUL CVC
# ══════════════════════════════════════════════════════════════

def _calculer_cvc(d: DonneesProjet, shon: float,
                   nb_logements: int, prix_mep) -> BilanCVC:
    climat = _get_climat(_get_ville_key(d.ville))
    delta_T = climat["T_ext"] - climat["T_confort"]

    # Charge thermique EN 12831 (W/m²)
    # Dakar : fort ensoleillement → coefficient majoration
    coeff_soleil = 1.3 if climat["ensoleillement"] == "fort" else 1.1
    q_clim_Wm2 = 60 * coeff_soleil  # W/m² de base

    # Puissance frigorifique totale
    P_frigo_kW = shon * q_clim_Wm2 / 1000

    # Ventilation — VMC
    # Résidentiel : VMC simple flux (économique)
    # Hôtel/Bureau : VMC double flux (performance)
    type_vmc = "double_flux" if d.usage in [Usage.HOTEL, Usage.BUREAU] else "simple_flux"
    nb_vmc = nb_logements

    # Splits résidentiel
    surf_sejour_m2 = 25
    surf_chambre_m2 = 14
    nb_logements_eff = nb_logements
    nb_splits_sej = nb_logements_eff  # 1 split séjour par logement
    nb_splits_ch  = nb_logements_eff * 2  # 2 chambres/logement en moyenne

    # Cassettes pour bureaux/hôtels
    nb_cassettes = 0
    if d.usage in [Usage.BUREAU, Usage.HOTEL, Usage.COMMERCIAL]:
        nb_cassettes = math.ceil(shon / 60)  # 1 cassette / 60m²
        nb_splits_sej = 0
        nb_splits_ch  = 0

    # Consommation CVC
    COP = 3.0 if type_vmc == "double_flux" else 2.5
    h_clim = 2500  # heures climatisation/an (tropiques)
    conso_cvc_kwh = P_frigo_kW / COP * h_clim

    # Note impact prix
    note = f"Charge thermique {P_frigo_kW:.0f} kW pour {shon:.0f} m² (T ext={climat['T_ext']}°C)"
    if type_vmc == "double_flux":
        cout_vmc = nb_vmc * prix_mep.vmc_double_flux
        note += f". VMC double flux recommandée ({d.usage.value}) : {cout_vmc/1e6:.1f} M FCFA"
        note += f" — économie énergie 30-40% vs simple flux"
    if nb_cassettes > 0:
        note += f". {nb_cassettes} cassettes plafond recommandées pour {d.usage.value}"

    marques = ["Daikin (split — représentant Dakar : CFAO)",
               "Mitsubishi Electric (haute performance)",
               "Carrier (centrales — grands projets)",
               "Atlantic (VMC — importé)"]

    return BilanCVC(
        puissance_frigorifique_kw=round(P_frigo_kW, 1),
        nb_splits_sejour=nb_splits_sej,
        nb_splits_chambre=nb_splits_ch,
        nb_cassettes=nb_cassettes,
        nb_vmc=nb_vmc,
        type_vmc=type_vmc,
        conso_cvc_kwh_an=round(conso_cvc_kwh, 0),
        note_dimensionnement=note,
        marques_recommandees=marques,
    )


# ══════════════════════════════════════════════════════════════
# CALCUL COURANTS FAIBLES
# ══════════════════════════════════════════════════════════════

def _calculer_courants_faibles(d: DonneesProjet, shon: float,
                                 nb_logements: int) -> BilanCourantsFaibles:
    # Réseau informatique
    nb_rj45 = math.ceil(shon / 10)  # 1 prise RJ45 / 10m²

    # Vidéosurveillance
    perimetre_m = 4 * math.sqrt(d.surface_emprise_m2)
    nb_cam_ext = max(2, math.ceil(perimetre_m / 15))  # 1 caméra / 15m périmètre
    nb_cam_int = math.ceil(shon / 200)  # 1 caméra / 200m² intérieur
    if d.usage in [Usage.HOTEL, Usage.BUREAU, Usage.COMMERCIAL]:
        nb_cam_int = math.ceil(shon / 100)

    # Contrôle d'accès
    nb_portes_ca = d.nb_niveaux + 2  # 1 par palier + entrées
    if d.usage in [Usage.BUREAU, Usage.HOTEL]:
        nb_portes_ca = d.nb_niveaux * 2 + 4

    # Interphones
    nb_interphones = nb_logements

    # Baies serveur
    nb_baies = 1
    if shon > 3000 or d.usage in [Usage.BUREAU, Usage.HOTEL]:
        nb_baies = max(1, math.ceil(shon / 2000))

    # Audio/vidéo collectif
    audio_video = d.usage in [Usage.HOTEL, Usage.COMMERCIAL, Usage.MIXTE]

    note = f"Câblage structuré Cat6A pour {nb_rj45} prises réseau"
    if d.usage in [Usage.HOTEL, Usage.BUREAU]:
        note += ". Système de gestion hôtelière/immeuble intégré recommandé"

    marques = ["Legrand (câblage structuré — distribué localement)",
               "Axis Communications (vidéosurveillance IP)",
               "HID Global (contrôle d'accès)",
               "Siemens (intégration systèmes)"]

    return BilanCourantsFaibles(
        nb_prises_rj45=nb_rj45,
        nb_cameras_int=nb_cam_int,
        nb_cameras_ext=nb_cam_ext,
        nb_portes_controle_acces=nb_portes_ca,
        nb_interphones=nb_interphones,
        baies_serveur=nb_baies,
        systeme_audio_video=audio_video,
        note_dimensionnement=note,
        marques_recommandees=marques,
    )


# ══════════════════════════════════════════════════════════════
# CALCUL SÉCURITÉ INCENDIE
# ══════════════════════════════════════════════════════════════

def _calculer_securite_incendie(d: DonneesProjet, shon: float,
                                  nb_personnes: int) -> BilanSecuriteIncendie:
    cat = _categorie_erp(d, nb_personnes)
    igh = "IGH" in cat
    erp_cat = 1 if "1ère" in cat else (2 if "2ème" in cat else (3 if "3ème" in cat else 4))

    # Détecteurs fumée (1 / 60m²)
    nb_det = math.ceil(shon / 60)

    # Déclencheurs manuels (1 par palier, 2 par niveau bureaux/hôtel)
    nb_decl = d.nb_niveaux * (2 if d.usage in [Usage.BUREAU, Usage.HOTEL] else 1)

    # Sirènes (1 par niveau + 1 extérieure)
    nb_sir = d.nb_niveaux + 1

    # Extincteurs
    nb_ext_co2 = math.ceil(shon / 200)       # 1 CO2 / 200m²
    nb_ext_pdr = math.ceil(shon / 150)       # 1 poudre / 150m²

    # RIA (Robinet d'Incendie Armé) — obligatoire ERP cat 1-3
    L_ria = 0.0
    if erp_cat <= 3 or igh:
        L_ria = d.nb_niveaux * math.sqrt(d.surface_emprise_m2)

    # Sprinklers — obligatoire IGH et ERP cat 1-2
    sprinklers_requis = igh or erp_cat <= 2
    nb_sprinklers = math.ceil(shon / 9) if sprinklers_requis else 0  # 1 / 9m²

    # Désenfumage — obligatoire R+8 et plus, IGH, hôtel ERP 1-2
    desenfumage = d.nb_niveaux >= 8 or igh or (d.usage == Usage.HOTEL and erp_cat <= 2)

    # Centrale incendie
    nb_zones = max(d.nb_niveaux, math.ceil(shon / 500))
    centrale_zones = 32 if nb_zones > 16 else 16

    note = f"{cat} — IT 246 Sénégal/France"
    if sprinklers_requis:
        note += f". ⚠ Sprinklers obligatoires : coût significatif ({nb_sprinklers} têtes)"
    if desenfumage:
        note += ". ⚠ Désenfumage obligatoire — prévoir gaines et volets"

    marques = ["Schneider Electric / Esser (centrale incendie)",
               "Tyco / Johnson Controls (sprinklers)",
               "Siemens Fire Safety (systèmes intégrés)",
               "Amerex (extincteurs — importé)"]

    return BilanSecuriteIncendie(
        categorie_erp=cat,
        nb_detecteurs_fumee=nb_det,
        nb_declencheurs_manuels=nb_decl,
        nb_sirenes=nb_sir,
        nb_extincteurs_co2=nb_ext_co2,
        nb_extincteurs_poudre=nb_ext_pdr,
        longueur_ria_ml=round(L_ria, 0),
        nb_tetes_sprinkler=nb_sprinklers,
        centrale_zones=centrale_zones,
        desenfumage_requis=desenfumage,
        sprinklers_requis=sprinklers_requis,
        note_dimensionnement=note,
        marques_recommandees=marques,
    )


# ══════════════════════════════════════════════════════════════
# CALCUL ASCENSEURS
# ══════════════════════════════════════════════════════════════

def _calculer_ascenseurs(d: DonneesProjet, shon: float,
                          nb_personnes: int, prix_mep) -> BilanAscenseurs:
    nb_niv = d.nb_niveaux

    # Règle validée
    if nb_niv <= 2:
        nb_asc = 0
        cap_kg = 0
        vitesse = 0.0
    elif nb_niv <= 5:
        nb_asc = 1
        cap_kg = 630
        vitesse = 1.0
    elif nb_niv <= 10:
        nb_asc = 1
        cap_kg = 1000
        vitesse = 1.6
        if d.usage in [Usage.HOTEL, Usage.BUREAU]:
            nb_asc = 2
    else:
        nb_asc = 2
        cap_kg = 1000
        vitesse = 2.5
        if shon > 10000:
            nb_asc = max(2, math.ceil(shon / 5000))

    # Monte-charge
    nb_mc = 0
    if d.usage in [Usage.HOTEL, Usage.BUREAU] and nb_niv >= 4:
        nb_mc = 1
    if d.usage == Usage.COMMERCIAL and nb_niv >= 3:
        nb_mc = 1

    # Escalators (centres commerciaux)
    nb_esc = 0
    if d.usage == Usage.COMMERCIAL and nb_niv >= 2:
        nb_esc = nb_niv - 1

    # Puissance
    p_asc_kw = nb_asc * cap_kg / 100 * vitesse * 1.5 if nb_asc > 0 else 0

    # Note impact prix
    note = ""
    note_prix = ""
    if nb_asc == 0:
        note = f"R+{nb_niv-1} ≤ R+2 — pas d'ascenseur requis"
    else:
        cout_asc = 0
        if cap_kg == 630 and nb_niv <= 6:
            cout_asc = nb_asc * prix_mep.ascenseur_630kg_r4_r6
        elif cap_kg == 630:
            cout_asc = nb_asc * prix_mep.ascenseur_630kg_r7_r10
        elif nb_niv <= 10:
            cout_asc = nb_asc * prix_mep.ascenseur_1000kg_r6_r10
        else:
            cout_asc = nb_asc * prix_mep.ascenseur_1000kg_r11_plus

        note = f"{nb_asc} ascenseur(s) {cap_kg}kg à {vitesse} m/s — EN 81-20/50"
        note_prix = (f"Ascenseurs : {cout_asc/1e6:.1f} M FCFA "
                     f"({cout_asc/shon:.0f} FCFA/m² bâti). "
                     f"Marques Otis/Schindler/Kone disponibles à Dakar.")
        if d.usage in [Usage.HOTEL, Usage.BUREAU]:
            note += f" + {nb_mc} monte-charge (service)"

    marques = ["Otis (présence Dakar)",
               "Schindler (présence Dakar et Abidjan)",
               "Kone (présence régionale)",
               "Thyssen Krupp (grands projets)"]

    return BilanAscenseurs(
        nb_ascenseurs=nb_asc,
        capacite_kg=cap_kg,
        vitesse_ms=vitesse,
        nb_monte_charges=nb_mc,
        nb_escalators=nb_esc,
        puissance_totale_kw=round(p_asc_kw, 1),
        note_dimensionnement=note,
        note_impact_prix=note_prix,
        marques_recommandees=marques,
    )


# ══════════════════════════════════════════════════════════════
# CALCUL AUTOMATISATION
# ══════════════════════════════════════════════════════════════

def _calculer_automatisation(d: DonneesProjet, shon: float,
                               nb_logements: int) -> BilanAutomatisation:
    # Niveau selon usage
    if d.usage == Usage.RESIDENTIEL and d.nb_niveaux <= 4:
        niveau = "basic"
        protocole = "KNX"
        bms = False
    elif d.usage in [Usage.RESIDENTIEL] and d.nb_niveaux > 4:
        niveau = "standard"
        protocole = "KNX"
        bms = False
    elif d.usage in [Usage.HOTEL, Usage.BUREAU, Usage.COMMERCIAL]:
        niveau = "premium"
        protocole = "BACnet"
        bms = True
    else:
        niveau = "standard"
        protocole = "KNX"
        bms = d.nb_niveaux >= 8

    # Points de contrôle estimés
    pts_eclairage = math.ceil(shon / 30)
    pts_cvc       = nb_logements * 2
    pts_acces     = d.nb_niveaux * 3
    pts_total     = pts_eclairage + pts_cvc + pts_acces

    note = f"Niveau {niveau} — protocole {protocole}"
    if bms:
        note += f". BMS recommandé pour {d.usage.value} — économies énergie estimées 15-25%"
    if niveau == "basic":
        note += ". Domotique par logement optionnelle — ROI 5-8 ans"

    marques = ["Schneider Electric EcoStruxure (BMS)",
               "Siemens Desigo CC (hôtel/bureau)",
               "KNX partenaires locaux (résidentiel)",
               "Honeywell (automatisation industrielle)"]

    return BilanAutomatisation(
        niveau=niveau,
        protocole=protocole,
        nb_points_controle=pts_total,
        gestion_eclairage=True,
        gestion_cvc=True,
        gestion_acces=(niveau in ["standard", "premium"]),
        gestion_energie=(niveau == "premium"),
        bms_requis=bms,
        note_dimensionnement=note,
        marques_recommandees=marques,
    )


# ══════════════════════════════════════════════════════════════
# CALCUL EDGE V2 — SCORES RÉELS
# ══════════════════════════════════════════════════════════════

def _calculer_edge(d: DonneesProjet, shon: float,
                    nb_logements: int, nb_personnes: int,
                    elec: BilanElectrique, plomb: BilanPlomberie,
                    cvc: BilanCVC, struct_boq=None) -> ScoreEDGE:
    """
    Calcul scores EDGE réels depuis données projet.
    Référence IFC EDGE Standard v3 — Sénégal/Afrique Subsaharienne.
    """
    # ── Références EDGE ──
    REF_ENERGIE_KWH_M2_AN = 120.0   # Bâtiment référence résidentiel Afrique
    REF_EAU_L_PERS_J      = 165.0   # Référence EDGE Afrique
    REF_EI_KWH_M2         = 500.0   # Énergie incorporée référence

    if d.usage == Usage.BUREAU:
        REF_ENERGIE_KWH_M2_AN = 180.0
    elif d.usage == Usage.HOTEL:
        REF_ENERGIE_KWH_M2_AN = 200.0

    # ══ PILIER ÉNERGIE ══
    mesures_energie = []
    eco_energie = 0.0

    # 1. Masse thermique (dalle béton — toujours présent)
    ep_dalle = 0.20  # valeur par défaut
    if struct_boq:
        ep_dalle = struct_boq.get("epaisseur_dalle_m", 0.20)
    eco_dalle = min(0.06, ep_dalle / 0.22 * 0.04)
    mesures_energie.append({
        "mesure": f"Masse thermique dalle e={int(ep_dalle*1000)}mm",
        "gain_pct": round(eco_dalle * 100, 1),
        "statut": "Intégré — construction standard",
        "impact_prix": "Inclus dans coût structure",
    })
    eco_energie += eco_dalle

    # 2. Ventilation naturelle (selon ratio surface/volume et nb niveaux)
    ht_bat = d.nb_niveaux * d.hauteur_etage_m
    ratio_sv = (2 * shon / ht_bat + 2 * d.surface_emprise_m2) / max(shon * ht_bat, 1)
    eco_vent = min(0.07, max(0.02, ratio_sv * 0.15))
    # R+1 villa : meilleure ventilation naturelle possible
    if d.nb_niveaux <= 3:
        eco_vent = 0.07
    elif d.nb_niveaux >= 10:
        eco_vent = 0.02
    mesures_energie.append({
        "mesure": f"Ventilation naturelle ({d.ville} — vents favorables)",
        "gain_pct": round(eco_vent * 100, 1),
        "statut": "Intégré — orientation à optimiser",
        "impact_prix": "Aucun coût additionnel si orientation correcte",
    })
    eco_energie += eco_vent

    # 3. Éclairage LED (non standard = 0, si LED = +6%)
    eco_led = 0.0
    mesures_energie.append({
        "mesure": "Éclairage LED 100% (à spécifier)",
        "gain_pct": 6.0,
        "statut": "À spécifier — non intégré par défaut",
        "impact_prix": f"Surcoût ~{int(shon * 3500 / 1e6)}M FCFA vs tubes fluorescents — ROI 2-3 ans",
    })
    eco_energie += eco_led

    # 4. Isolation toiture (non standard Dakar = 0, si isolée = +8%)
    eco_iso = 0.0
    ratio_toiture = d.surface_emprise_m2 / max(shon, 1)
    mesures_energie.append({
        "mesure": "Isolation toiture terrasse (laine de roche 80mm + SBS)",
        "gain_pct": round(8 * ratio_toiture * 2, 1),
        "statut": "À spécifier — non inclus standard",
        "impact_prix": f"Surcoût ~{int(d.surface_emprise_m2 * 8500 / 1e6 + 1)}M FCFA",
    })
    eco_energie += eco_iso

    # 5. Double vitrage (non standard = 0, si spécifié = +5%)
    eco_vitrage = 0.0
    mesures_energie.append({
        "mesure": "Double vitrage Low-E (U ≤ 1.8 W/m²K)",
        "gain_pct": 5.0,
        "statut": "À spécifier — non inclus standard",
        "impact_prix": "Surcoût ~15-20% vs vitrage simple",
    })
    eco_energie += eco_vitrage

    pct_energie = round(eco_energie * 100, 1)
    projet_energie = REF_ENERGIE_KWH_M2_AN * (1 - eco_energie)

    # ══ PILIER EAU ══
    mesures_eau = []
    eco_eau = 0.0

    # 1. Dotation réelle vs référence EDGE
    dotation_projet = DOTATION_EAU[d.usage]
    eco_base_dotation = max(0, (REF_EAU_L_PERS_J - dotation_projet) / REF_EAU_L_PERS_J)
    if eco_base_dotation > 0:
        mesures_eau.append({
            "mesure": f"Dotation locale {dotation_projet} L/pers/j vs référence {REF_EAU_L_PERS_J} L/pers/j",
            "gain_pct": round(eco_base_dotation * 100, 1),
            "statut": "Intégré — pratiques locales",
            "impact_prix": "Aucun coût additionnel",
        })
        eco_eau += eco_base_dotation

    # 2. WC double chasse (non standard = 0)
    eco_wc = 0.0
    cout_wc = plomb.nb_wc_double_chasse * 45000  # surcoût vs WC standard
    mesures_eau.append({
        "mesure": "WC double chasse 3/6L (vs 9L standard)",
        "gain_pct": 13.0,
        "statut": "À spécifier — non inclus standard",
        "impact_prix": f"Surcoût {cout_wc/1e6:.1f} M FCFA pour {plomb.nb_wc_double_chasse} WC — économie eau 13%",
    })
    eco_eau += eco_wc

    # 3. Robinetterie éco (non standard = 0)
    eco_rob = 0.0
    cout_rob = plomb.nb_robinets_eco * 30000
    mesures_eau.append({
        "mesure": "Robinetterie mousseurs 6 L/min (vs 12 L/min standard)",
        "gain_pct": 8.0,
        "statut": "À spécifier — non inclus standard",
        "impact_prix": f"Surcoût {cout_rob/1e6:.1f} M FCFA pour {plomb.nb_robinets_eco} robinets — économie eau 8%",
    })
    eco_eau += eco_rob

    # 4. Récupération eaux pluviales
    surf_toiture = d.surface_emprise_m2
    pluie_mm_an = 500 if "dakar" in d.ville.lower() else 1200
    V_pluvial_m3_an = surf_toiture * pluie_mm_an / 1000 * 0.8
    eco_pluvial = min(0.10, V_pluvial_m3_an / max(plomb.conso_eau_annuelle_m3, 1) * 0.5)
    mesures_eau.append({
        "mesure": f"Récupération eaux pluviales (toiture {int(surf_toiture)} m²)",
        "gain_pct": round(eco_pluvial * 100, 1),
        "statut": "À spécifier — système cuve + filtration",
        "impact_prix": f"Investissement ~{int(surf_toiture * 5000 / 1e6 + 1)} M FCFA — ROI 4-6 ans",
    })
    eco_eau += 0.0  # Non intégré par défaut

    pct_eau = round(eco_eau * 100, 1)
    projet_eau = REF_EAU_L_PERS_J * (1 - eco_eau)

    # ══ PILIER MATÉRIAUX ══
    mesures_mat = []
    eco_mat = 0.0

    # 1. Ratio acier réel vs référence (40 kg/m² référence EDGE)
    ratio_acier_ref = 40.0
    if struct_boq:
        ratio_acier_reel = struct_boq.get("acier_kg", 0) / max(shon, 1)
    else:
        # Estimation depuis nb niveaux
        ratio_acier_reel = 25 + d.nb_niveaux * 2.5
    eco_acier = max(0, min(0.08, (ratio_acier_ref - ratio_acier_reel) / ratio_acier_ref * 0.4))
    mesures_mat.append({
        "mesure": f"Ratio acier réel {ratio_acier_reel:.0f} kg/m² (référence {ratio_acier_ref} kg/m²)",
        "gain_pct": round(eco_acier * 100, 1),
        "statut": "Calculé depuis moteur structure",
        "impact_prix": "Inclus dans coût structure",
    })
    eco_mat += eco_acier

    # 2. Parpaings creux (standard Dakar — toujours présent)
    eco_parpaings = 0.06
    mesures_mat.append({
        "mesure": "Maçonnerie agglos creux (vs agglos pleins référence)",
        "gain_pct": 6.0,
        "statut": "Intégré — pratique standard",
        "impact_prix": "Aucun surcoût — pratique locale standard",
    })
    eco_mat += eco_parpaings

    # 3. Béton GGBS (non standard = 0)
    eco_ggbs = 0.0
    mesures_mat.append({
        "mesure": "Substitution ciment par laitier GGBS 30% (béton bas carbone)",
        "gain_pct": 8.0,
        "statut": "À spécifier — disponibilité limitée Dakar",
        "impact_prix": "Surcoût béton ~5% — à négocier avec CIMAF/SOCOCIM",
    })
    eco_mat += eco_ggbs

    pct_mat = round(eco_mat * 100, 1)
    ei_projet = REF_EI_KWH_M2 * (1 - eco_mat)

    # ══ VERDICT ══
    seuil = 20.0
    certifiable = pct_energie >= seuil and pct_eau >= seuil and pct_mat >= seuil

    if not certifiable:
        min_score = min(pct_energie, pct_eau, pct_mat)
        niveau_cert = "Non certifiable EDGE Basique"
    elif min(pct_energie, pct_eau, pct_mat) >= 40:
        niveau_cert = "EDGE Advanced"
    else:
        niveau_cert = "EDGE Basique"

    # ══ PLAN D'ACTION OPTIMISATION ══
    plan_action = []
    cout_total_conformite = 0

    if pct_energie < seuil:
        deficit_e = seuil - pct_energie
        # LED + isolation + double vitrage pour combler le déficit
        if eco_led == 0:
            cout_led = int(shon * 3500)
            plan_action.append({
                "action": "Éclairage LED 100% sur tout le bâtiment",
                "gain_pct": 6.0, "pilier": "Énergie",
                "cout_fcfa": cout_led,
                "roi_ans": 3.0,
                "impact": f"+6% énergie — investissement {cout_led/1e6:.1f} M FCFA",
            })
            cout_total_conformite += cout_led
        if eco_iso == 0 and deficit_e > 0:
            cout_iso = int(d.surface_emprise_m2 * 8500)
            plan_action.append({
                "action": "Isolation toiture terrasse laine de roche 80mm",
                "gain_pct": round(8 * ratio_toiture * 2, 1),
                "pilier": "Énergie",
                "cout_fcfa": cout_iso,
                "roi_ans": 6.0,
                "impact": f"+{round(8*ratio_toiture*2,1)}% énergie — {cout_iso/1e6:.1f} M FCFA",
            })
            cout_total_conformite += cout_iso

    if pct_eau < seuil:
        cout_wc_plan = plomb.nb_wc_double_chasse * 45000
        plan_action.append({
            "action": f"WC double chasse 3/6L ({plomb.nb_wc_double_chasse} unités)",
            "gain_pct": 13.0, "pilier": "Eau",
            "cout_fcfa": cout_wc_plan,
            "roi_ans": 4.0,
            "impact": f"+13% eau — {cout_wc_plan/1e6:.1f} M FCFA",
        })
        cout_rob_plan = plomb.nb_robinets_eco * 30000
        plan_action.append({
            "action": f"Robinetterie économique 6 L/min ({plomb.nb_robinets_eco} unités)",
            "gain_pct": 8.0, "pilier": "Eau",
            "cout_fcfa": cout_rob_plan,
            "roi_ans": 3.0,
            "impact": f"+8% eau — {cout_rob_plan/1e6:.1f} M FCFA",
        })
        cout_total_conformite += cout_wc_plan + cout_rob_plan

    if pct_mat < seuil:
        plan_action.append({
            "action": "Béton avec 30% substitution ciment par laitier GGBS",
            "gain_pct": 8.0, "pilier": "Matériaux",
            "cout_fcfa": 0,
            "roi_ans": 0.0,
            "impact": "+8% matériaux — surcoût béton ~5% à négocier fournisseur",
        })

    # ROI global
    eco_annuelle = (plomb.facture_eau_fcfa * 0.20 +
                    elec.facture_annuelle_fcfa * 0.10)
    roi_ans = round(cout_total_conformite / max(eco_annuelle, 1), 1) if eco_annuelle > 0 else 0

    note_gen = (
        f"Énergie {pct_energie}% | Eau {pct_eau}% | Matériaux {pct_mat}% "
        f"(seuil EDGE : 20% sur les 3 piliers). "
        f"{'Certifiable EDGE Basique.' if certifiable else 'Non certifiable — voir plan d\'action.'}"
    )

    return ScoreEDGE(
        economie_energie_pct=pct_energie,
        economie_eau_pct=pct_eau,
        economie_materiaux_pct=pct_mat,
        base_energie_kwh_m2_an=REF_ENERGIE_KWH_M2_AN,
        projet_energie_kwh_m2_an=round(projet_energie, 1),
        mesures_energie=mesures_energie,
        base_eau_L_pers_j=REF_EAU_L_PERS_J,
        projet_eau_L_pers_j=round(projet_eau, 1),
        mesures_eau=mesures_eau,
        base_ei_kwh_m2=REF_EI_KWH_M2,
        projet_ei_kwh_m2=round(ei_projet, 1),
        mesures_materiaux=mesures_mat,
        certifiable=certifiable,
        niveau_certification=niveau_cert,
        plan_action=plan_action,
        cout_mise_conformite_fcfa=cout_total_conformite,
        roi_ans=roi_ans,
        methode_calcul="Méthode constructive EDGE v3 — données projet réelles",
        note_generale=note_gen,
    )


# ══════════════════════════════════════════════════════════════
# CALCUL BOQ MEP
# ══════════════════════════════════════════════════════════════

def _calculer_boq_mep(d: DonneesProjet, shon: float,
                       nb_logements: int, elec: BilanElectrique,
                       plomb: BilanPlomberie, cvc: BilanCVC,
                       cf: BilanCourantsFaibles, si: BilanSecuriteIncendie,
                       asc: BilanAscenseurs, auto: BilanAutomatisation,
                       prix_mep) -> BOQ_MEP:
    p = prix_mep

    lots = []

    # Lot 1 — Électricité courants forts
    cout_elec_basic  = int(elec.transfo_kva * p.transfo_160kva / 160 * 0.8 +
                            elec.nb_compteurs * p.compteur_monophase +
                            shon * p.canalisation_cuivre_ml * 0.8 +
                            shon / 15 * p.luminaire_led_standard)
    cout_elec_hend   = int(cout_elec_basic * 1.35)
    cout_elec_luxury = int(cout_elec_basic * 1.80)
    lots.append(BOQ_Lot("E1", "Électricité courants forts — TGBT, câblage, luminaires",
                         "forfait", 1, cout_elec_basic, cout_elec_hend, cout_elec_luxury,
                         f"Transformateur {elec.transfo_kva}kVA + GE {elec.groupe_electrogene_kva}kVA inclus"))

    # Lot 2 — Plomberie sanitaire
    cout_plomb_basic = int(plomb.nb_logements * (p.wc_standard + p.robinet_standard * 2) +
                            p.cuve_eau_5000l * max(1, plomb.volume_citerne_m3/5) +
                            p.pompe_surpresseur_1kw +
                            shon * p.tuyau_pvc_dn100_ml * 0.3)
    cout_plomb_hend   = int(cout_plomb_basic * 1.40)
    cout_plomb_luxury = int(cout_plomb_basic * 1.90)
    note_plomb = f"Citerne {int(plomb.volume_citerne_m3)}m³ + surpresseur {plomb.debit_surpresseur_m3h}m³/h"
    if plomb.nb_chauffe_eau_solaire > 0:
        note_plomb += f" + {plomb.nb_chauffe_eau_solaire} CESI"
    lots.append(BOQ_Lot("P1", "Plomberie sanitaire — réseau eau, citerne, surpresseur",
                         "forfait", 1, cout_plomb_basic, cout_plomb_hend, cout_plomb_luxury,
                         note_plomb))

    # Lot 3 — CVC
    if cvc.nb_splits_sejour > 0 or cvc.nb_splits_chambre > 0:
        nb_splits = cvc.nb_splits_sejour + cvc.nb_splits_chambre
        cout_cvc_basic = int(nb_splits * p.split_1cv + cvc.nb_vmc * p.vmc_simple_flux)
    else:
        cout_cvc_basic = int(cvc.nb_cassettes * p.split_cassette_4cv +
                              cvc.nb_vmc * (p.vmc_double_flux if cvc.type_vmc == "double_flux"
                                             else p.vmc_simple_flux))
    cout_cvc_hend   = int(cout_cvc_basic * 1.45)
    cout_cvc_luxury = int(cout_cvc_basic * 2.00)
    note_cvc = f"VMC {cvc.type_vmc}"
    if cvc.type_vmc == "double_flux":
        note_cvc += " — économie énergie 30-40% vs simple flux"
    lots.append(BOQ_Lot("C1", f"CVC — climatisation, ventilation ({cvc.puissance_frigorifique_kw:.0f} kW)",
                         "forfait", 1, cout_cvc_basic, cout_cvc_hend, cout_cvc_luxury, note_cvc))

    # Lot 4 — Courants faibles
    cout_cf_basic = int(cf.nb_prises_rj45 * p.prise_rj45 +
                         cf.nb_cameras_int * p.camera_ip_interieure +
                         cf.nb_cameras_ext * p.camera_ip_exterieure +
                         cf.nb_portes_controle_acces * p.systeme_controle_acces +
                         cf.nb_interphones * p.interphone_video +
                         cf.baies_serveur * p.baie_serveur_12u)
    cout_cf_hend   = int(cout_cf_basic * 1.50)
    cout_cf_luxury = int(cout_cf_basic * 2.20)
    lots.append(BOQ_Lot("CF", "Courants faibles — réseau, vidéo, contrôle accès, interphonie",
                         "forfait", 1, cout_cf_basic, cout_cf_hend, cout_cf_luxury,
                         f"{cf.nb_cameras_int + cf.nb_cameras_ext} caméras + {cf.nb_portes_controle_acces} contrôles accès"))

    # Lot 5 — Sécurité incendie
    cout_si_basic = int(si.nb_detecteurs_fumee * p.detecteur_fumee +
                         si.nb_declencheurs_manuels * p.declencheur_manuel +
                         si.nb_sirenes * p.sirene_flash +
                         si.nb_extincteurs_co2 * p.extincteur_6kg_co2 +
                         si.nb_extincteurs_poudre * p.extincteur_9kg_poudre +
                         si.longueur_ria_ml * p.ria_dn25_ml +
                         si.nb_tetes_sprinkler * p.sprinkler_tete +
                         (p.centrale_incendie_32zones if si.centrale_zones > 16
                          else p.centrale_incendie_16zones))
    cout_si_hend   = int(cout_si_basic * 1.30)
    cout_si_luxury = int(cout_si_basic * 1.60)
    note_si = si.categorie_erp
    if si.sprinklers_requis:
        note_si += f" — sprinklers obligatoires ({si.nb_tetes_sprinkler} têtes)"
    lots.append(BOQ_Lot("SI", f"Sécurité incendie — {si.categorie_erp}",
                         "forfait", 1, cout_si_basic, cout_si_hend, cout_si_luxury, note_si))

    # Lot 6 — Ascenseurs
    if asc.nb_ascenseurs > 0:
        if asc.capacite_kg == 630 and d.nb_niveaux <= 6:
            pu_asc = p.ascenseur_630kg_r4_r6
        elif asc.capacite_kg == 630:
            pu_asc = p.ascenseur_630kg_r7_r10
        elif d.nb_niveaux <= 10:
            pu_asc = p.ascenseur_1000kg_r6_r10
        else:
            pu_asc = p.ascenseur_1000kg_r11_plus

        cout_asc_basic = int(asc.nb_ascenseurs * pu_asc +
                              asc.nb_monte_charges * p.monte_charge_500kg)
        cout_asc_hend   = int(cout_asc_basic * 1.20)
        cout_asc_luxury = int(cout_asc_basic * 1.50)
        lots.append(BOQ_Lot("ASC", f"Ascenseurs — {asc.nb_ascenseurs}×{asc.capacite_kg}kg à {asc.vitesse_ms}m/s",
                             "forfait", 1, cout_asc_basic, cout_asc_hend, cout_asc_luxury,
                             asc.note_impact_prix))

    # Lot 7 — Automatisation
    if auto.niveau != "basic" or auto.bms_requis:
        cout_auto_basic  = int(nb_logements * p.domotique_logement * 0.3 +
                                auto.nb_points_controle * 50000)
        cout_auto_hend   = int(cout_auto_basic * 1.60)
        cout_auto_luxury = int((p.bms_systeme if auto.bms_requis else cout_auto_basic) * 1.20)
        lots.append(BOQ_Lot("AUTO", f"Automatisation — {auto.niveau} ({auto.protocole})",
                             "forfait", 1, cout_auto_basic, cout_auto_hend, cout_auto_luxury,
                             auto.note_dimensionnement))

    # Totaux
    tot_basic  = sum(l.pu_basic_fcfa for l in lots)
    tot_hend   = sum(l.pu_hend_fcfa for l in lots)
    tot_luxury = sum(l.pu_luxury_fcfa for l in lots)

    ratio_basic = int(tot_basic / shon) if shon > 0 else 0
    ratio_hend  = int(tot_hend / shon) if shon > 0 else 0

    # Recommandation
    if d.usage == Usage.RESIDENTIEL:
        reco = "Gamme Basic à High-End recommandée pour usage résidentiel standard"
    elif d.usage == Usage.HOTEL:
        reco = "Gamme High-End à Luxury recommandée — qualité hôtelière attendue par la clientèle"
    else:
        reco = "Gamme High-End recommandée — rapport qualité/prix optimal pour usage bureau"

    note_choix = f"Écart Basic → Luxury : {(tot_luxury-tot_basic)/1e6:.0f} M FCFA ({tot_luxury/tot_basic*100-100:.0f}% de surcoût)"

    return BOQ_MEP(
        lots=lots,
        total_basic_fcfa=tot_basic,
        total_hend_fcfa=tot_hend,
        total_luxury_fcfa=tot_luxury,
        ratio_basic_m2=ratio_basic,
        ratio_hend_m2=ratio_hend,
        recommandation=reco,
        note_choix=note_choix,
    )


# ══════════════════════════════════════════════════════════════
# POINT D'ENTRÉE PRINCIPAL
# ══════════════════════════════════════════════════════════════

def calculer_mep(d: DonneesProjet, struct_resultats=None) -> ResultatsMEP:
    """
    Calcule l'ensemble MEP depuis les données projet.
    Accepte optionnellement les résultats structure pour EDGE matériaux.
    """
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    try:
        from prix_marche import get_prix_mep
        prix_mep = get_prix_mep(d.ville)
    except ImportError:
        class _PrixFallback:
            transfo_160kva = 22_000_000; transfo_250kva = 32_000_000
            transfo_400kva = 48_000_000; groupe_electrogene_100kva = 18_000_000
            groupe_electrogene_200kva = 32_000_000; groupe_electrogene_400kva = 58_000_000
            compteur_monophase = 180_000; compteur_triphase = 280_000
            canalisation_cuivre_ml = 12_000; luminaire_led_standard = 35_000
            colonne_montante_ml = 22_000; tuyau_pvc_dn100_ml = 14_000
            robinet_standard = 45_000; robinet_eco = 75_000
            wc_standard = 85_000; wc_double_chasse = 130_000
            cuve_eau_5000l = 850_000; cuve_eau_10000l = 1_500_000
            pompe_surpresseur_1kw = 450_000; pompe_surpresseur_3kw = 850_000
            chauffe_eau_electrique_100l = 180_000; chauffe_eau_solaire_200l = 2_100_000
            split_1cv = 450_000; split_2cv = 750_000; split_cassette_4cv = 1_800_000
            vmc_simple_flux = 320_000; vmc_double_flux = 850_000
            ascenseur_630kg_r4_r6 = 28_000_000; ascenseur_630kg_r7_r10 = 38_000_000
            ascenseur_1000kg_r6_r10 = 45_000_000; ascenseur_1000kg_r11_plus = 58_000_000
            monte_charge_500kg = 22_000_000; cablage_rj45_ml = 3_500
            prise_rj45 = 18_000; baie_serveur_12u = 850_000
            camera_ip_interieure = 180_000; camera_ip_exterieure = 280_000
            systeme_controle_acces = 350_000; interphone_video = 220_000
            detecteur_fumee = 45_000; declencheur_manuel = 35_000
            sirene_flash = 55_000; centrale_incendie_16zones = 1_800_000
            centrale_incendie_32zones = 3_200_000; extincteur_6kg_co2 = 85_000
            extincteur_9kg_poudre = 65_000; ria_dn25_ml = 45_000
            sprinkler_tete = 85_000; sprinkler_centrale = 4_500_000
            domotique_logement = 850_000; bms_systeme = 12_000_000
            eclairage_detecteur_presence = 95_000
        prix_mep = _PrixFallback()

    shon = _shon(d)
    nb_log = _estimer_logements(d, shon)
    nb_pers = nb_log * d.personnes_par_logement if hasattr(d, 'personnes_par_logement') else nb_log * 4

    # Données BOQ structure pour EDGE
    struct_boq_dict = None
    if struct_resultats and hasattr(struct_resultats, 'boq'):
        struct_boq_dict = {
            "acier_kg": struct_resultats.boq.acier_kg,
            "beton_m3": struct_resultats.boq.beton_total_m3,
            "epaisseur_dalle_m": struct_resultats.dalle.epaisseur_mm / 1000
            if hasattr(struct_resultats, 'dalle') else 0.20,
        }

    elec  = _calculer_electrique(d, shon, nb_log, prix_mep)
    plomb = _calculer_plomberie(d, shon, nb_log, nb_pers, prix_mep)
    cvc_  = _calculer_cvc(d, shon, nb_log, prix_mep)
    cf    = _calculer_courants_faibles(d, shon, nb_log)
    si    = _calculer_securite_incendie(d, shon, nb_pers)
    asc   = _calculer_ascenseurs(d, shon, nb_pers, prix_mep)
    auto  = _calculer_automatisation(d, shon, nb_log)
    edge  = _calculer_edge(d, shon, nb_log, nb_pers, elec, plomb, cvc_, struct_boq_dict)
    boq   = _calculer_boq_mep(d, shon, nb_log, elec, plomb, cvc_, cf, si, asc, auto, prix_mep)

    return ResultatsMEP(
        params=d, shon_m2=shon,
        nb_logements=nb_log, nb_personnes=nb_pers,
        electrique=elec, plomberie=plomb, cvc=cvc_,
        courants_faibles=cf, securite_incendie=si,
        ascenseurs=asc, automatisation=auto,
        edge=edge, boq=boq,
    )


# ══════════════════════════════════════════════════════════════
# TEST
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=== TEST MOTEUR MEP V2 ===\n")

    projets = [
        DonneesProjet(nom="Villa Ngom", ville="Dakar", pays="Senegal",
                      usage=Usage.RESIDENTIEL, nb_niveaux=2,
                      surface_emprise_m2=300, portee_max_m=5.0, portee_min_m=4.0,
                      nb_travees_x=3, nb_travees_y=2),
        DonneesProjet(nom="Résidence Sakho", ville="Dakar", pays="Senegal",
                      usage=Usage.RESIDENTIEL, nb_niveaux=9,
                      surface_emprise_m2=980, portee_max_m=6.18, portee_min_m=4.13,
                      nb_travees_x=8, nb_travees_y=5),
        DonneesProjet(nom="Hotel Plateau", ville="Abidjan", pays="Cote d'Ivoire",
                      usage=Usage.HOTEL, nb_niveaux=6,
                      surface_emprise_m2=800, portee_max_m=7.0, portee_min_m=5.5,
                      nb_travees_x=5, nb_travees_y=4),
    ]

    for proj in projets:
        r = calculer_mep(proj)
        e = r.edge
        print(f"{'='*60}")
        print(f"PROJET : {proj.nom} ({proj.ville}) — R+{proj.nb_niveaux-1} {proj.usage.value}")
        print(f"SHON : {r.shon_m2:.0f} m² | Logements : {r.nb_logements} | Personnes : {r.nb_personnes}")
        print(f"ÉLEC  : {r.electrique.puissance_totale_kva:.0f} kVA | Transfo {r.electrique.transfo_kva} kVA")
        print(f"EAU   : {r.plomberie.besoin_total_m3_j:.1f} m³/j | Citerne {r.plomberie.volume_citerne_m3:.0f} m³")
        print(f"CVC   : {r.cvc.puissance_frigorifique_kw:.0f} kW | VMC {r.cvc.type_vmc}")
        print(f"ASCEN : {r.ascenseurs.nb_ascenseurs} × {r.ascenseurs.capacite_kg} kg")
        print(f"SÉCU  : {r.securite_incendie.categorie_erp}")
        print(f"EDGE  : Énergie {e.economie_energie_pct}% | Eau {e.economie_eau_pct}% | Mat {e.economie_materiaux_pct}%")
        print(f"        → {e.niveau_certification}")
        if e.plan_action:
            print(f"        Plan d'action : {len(e.plan_action)} mesures | Coût conformité : {e.cout_mise_conformite_fcfa/1e6:.1f} M FCFA")
        print(f"BOQ   : Basic {r.boq.total_basic_fcfa/1e6:.0f} M | High-End {r.boq.total_hend_fcfa/1e6:.0f} M | Luxury {r.boq.total_luxury_fcfa/1e6:.0f} M FCFA")
        print(f"        ({r.boq.ratio_basic_m2:,} FCFA/m²)".replace(',', ' '))
        print()
