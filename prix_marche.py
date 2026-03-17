"""
prix_marche.py — Base de prix construction multi-pays Tijan AI
═══════════════════════════════════════════════════════════════
Sources :
  Dakar      : Prix validés terrain par Malick Tall (Mars 2026)
  Abidjan    : BNETD, SICOGI, marchés locaux (estimation Mars 2026)
  Casablanca : CSMC, CPC Maroc, Ordre des Architectes Maroc (estimation Mars 2026)
  Lagos      : NBRRI, NIOB, Builders Magazine Nigeria (estimation Mars 2026)
  Rabat      : CSMC, marchés publics Maroc (estimation Mars 2026)
  Accra      : Ghana Institute of Engineers, GIBB (estimation Mars 2026)

Devise de référence : FCFA (XOF) pour Dakar/Abidjan
Autres devises converties en FCFA équivalent pour comparaison.

Mise à jour : Mars 2026
Prochaine révision : Avril 2026
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import date

# ══════════════════════════════════════════════════════════════
# TAUX DE CHANGE (Mars 2026 — à réviser mensuellement)
# ══════════════════════════════════════════════════════════════
TAUX_CHANGE = {
    "XOF": 1.0,           # FCFA — référence
    "MAD": 60.5,          # 1 MAD = 60.5 FCFA (Dirham marocain)
    "NGN": 0.48,          # 1 NGN = 0.48 FCFA (Naira nigérian)
    "GHS": 57.0,          # 1 GHS = 57 FCFA (Cedi ghanéen)
    "EUR": 655.957,       # 1 EUR = 655.957 FCFA (fixe Zone CFA)
    "USD": 607.0,         # 1 USD ≈ 607 FCFA (Mars 2026)
}

def to_fcfa(montant: float, devise: str) -> float:
    """Convertit un montant en FCFA."""
    return montant * TAUX_CHANGE.get(devise, 1.0)

# ══════════════════════════════════════════════════════════════
# STRUCTURE DE DONNÉES PRIX
# ══════════════════════════════════════════════════════════════
@dataclass
class PrixStructure:
    """Prix matériaux et main d'œuvre — Structure."""
    # Béton (FCFA/m³ — fourni posé BPE)
    beton_c2530_m3: float       # Fondations, éléments peu sollicités
    beton_c3037_m3: float       # Standard résidentiel R+4 à R+8
    beton_c3545_m3: float       # Haute résistance R+9 et plus
    beton_c4050_m3: float       # Tours, IGH

    # Acier (FCFA/kg — fourni posé façonné)
    acier_ha400_kg: float       # Petits ouvrages R+1 à R+3
    acier_ha500_kg: float       # Standard résidentiel/bureau
    acier_ha500_vrac_kg: float  # Prix vrac (sans façonnage)

    # Coffrage (FCFA/m²)
    coffrage_bois_m2: float     # Coffrage traditionnel bois
    coffrage_metal_m2: float    # Coffrage métallique réutilisable

    # Fondations
    pieu_fore_d600_ml: float    # Pieu foré Ø600mm (FCFA/ml)
    pieu_fore_d800_ml: float    # Pieu foré Ø800mm (FCFA/ml)
    pieu_fore_d1000_ml: float   # Pieu foré Ø1000mm (FCFA/ml)
    semelle_filante_ml: float   # Semelle filante béton armé (FCFA/ml)
    radier_m2: float            # Radier général (FCFA/m²)

    # Maçonnerie (FCFA/m²)
    agglo_creux_10_m2: float    # Agglos creux 10cm (cloisons légères)
    agglo_creux_15_m2: float    # Agglos creux 15cm (cloisons standard)
    agglo_creux_20_m2: float    # Agglos creux 20cm (murs porteurs)
    agglo_plein_25_m2: float    # Agglos pleins 25cm (façades)
    brique_pleine_m2: float     # Briques pleines (premium)
    ba13_simple_m2: float       # Cloison BA13 simple rail
    ba13_double_m2: float       # Cloison BA13 double rail (séparatif)

    # Étanchéité (FCFA/m²)
    etanch_sbs_m2: float        # Étanchéité SBS bicouche toiture
    etanch_pvc_m2: float        # Étanchéité PVC membrane
    etanch_liquide_m2: float    # Étanchéité liquide salles de bain

    # Terrassement (FCFA/m³)
    terr_mecanique_m3: float    # Terrassement mécanique
    terr_manuel_m3: float       # Terrassement manuel
    remblai_m3: float           # Remblai compacté

    # Main d'œuvre (FCFA/jour)
    mo_chef_chantier_j: float
    mo_macon_j: float
    mo_ferrailleur_j: float
    mo_electricien_j: float
    mo_plombier_j: float
    mo_manœuvre_j: float


@dataclass
class PrixMEP:
    """Prix équipements MEP (FCFA — fournis posés)."""
    # Électricité
    tableau_general_bt: float       # TGBT complet (forfait)
    transfo_160kva: float           # Transformateur HTA/BT 160kVA
    transfo_250kva: float
    transfo_400kva: float
    groupe_electrogene_100kva: float
    groupe_electrogene_200kva: float
    groupe_electrogene_400kva: float
    compteur_monophase: float       # Compteur + coffret (par logement)
    compteur_triphase: float
    canalisation_cuivre_ml: float   # Câblage cuivre (FCFA/ml moyen)
    luminaire_led_standard: float   # Luminaire LED plafonnier (unité)
    luminaire_led_premium: float

    # Plomberie
    colonne_montante_ml: float      # Colonne montante acier galva (FCFA/ml)
    tuyau_pvc_dn50_ml: float
    tuyau_pvc_dn100_ml: float
    tuyau_pvc_dn150_ml: float
    robinet_standard: float         # Robinet mélangeur standard
    robinet_eco: float              # Robinet économique 6L/min
    wc_standard: float              # WC standard
    wc_double_chasse: float         # WC double chasse 3/6L
    cuve_eau_5000l: float           # Citerne polyéthylène 5000L
    cuve_eau_10000l: float
    pompe_surpresseur_1kw: float
    pompe_surpresseur_3kw: float
    chauffe_eau_electrique_100l: float
    chauffe_eau_solaire_200l: float  # CESI 200L

    # CVC
    split_1cv: float                # Split mural 1CV (9000 BTU)
    split_2cv: float                # Split mural 2CV (18000 BTU)
    split_cassette_4cv: float       # Cassette plafond 4CV
    vmc_simple_flux: float          # VMC simple flux (par logement)
    vmc_double_flux: float          # VMC double flux (par logement)
    climatiseur_central_kw: float   # Clim centrale (FCFA/kW)

    # Ascenseurs
    ascenseur_630kg_r4_r6: float    # Ascenseur 630kg 4-6 niveaux
    ascenseur_630kg_r7_r10: float   # Ascenseur 630kg 7-10 niveaux
    ascenseur_1000kg_r6_r10: float  # Ascenseur 1000kg 6-10 niveaux
    ascenseur_1000kg_r11_plus: float
    monte_charge_500kg: float

    # Courants faibles
    cablage_rj45_ml: float          # Câblage réseau RJ45 (FCFA/ml)
    prise_rj45: float               # Prise réseau (unité)
    baie_serveur_12u: float         # Baie serveur 12U
    camera_ip_interieure: float     # Caméra IP intérieure
    camera_ip_exterieure: float
    systeme_controle_acces: float   # Contrôle d'accès (par porte)
    interphone_video: float         # Interphone vidéo (par logement)

    # Sécurité incendie
    detecteur_fumee: float          # Détecteur fumée optique
    declencheur_manuel: float       # Déclencheur manuel
    sirene_flash: float             # Sirène + flash
    centrale_incendie_16zones: float
    centrale_incendie_32zones: float
    extincteur_6kg_co2: float
    extincteur_9kg_poudre: float
    ria_dn25_ml: float              # RIA DN25 (FCFA/ml)
    sprinkler_tete: float           # Tête de sprinkler (unité)
    sprinkler_centrale: float       # Centrale sprinkler

    # Automatisation
    domotique_logement: float       # Domotique par logement (basic)
    bms_systeme: float              # BMS bâtiment (forfait)
    eclairage_detecteur_presence: float  # Éclairage + détecteur


@dataclass
class PrixPays:
    """Prix complets pour un pays donné."""
    pays: str
    ville_reference: str
    devise: str
    date_maj: str
    structure: PrixStructure
    mep: PrixMEP
    notes: str = ""
    fiabilite: str = "estimation"  # "validé_terrain" | "estimation" | "à_confirmer"


# ══════════════════════════════════════════════════════════════
# DAKAR, SÉNÉGAL — PRIX VALIDÉS TERRAIN (Mars 2026)
# ══════════════════════════════════════════════════════════════
DAKAR = PrixPays(
    pays="Sénégal",
    ville_reference="Dakar",
    devise="XOF",
    date_maj="2026-03",
    fiabilite="validé_terrain",
    notes="Prix validés par Malick Tall. Fournisseurs ref: Fabrimetal (acier), CIMAF/SOCOCIM (ciment), SONETEL (élec).",
    structure=PrixStructure(
        # Béton BPE (FCFA/m³)
        beton_c2530_m3=170_000,
        beton_c3037_m3=185_000,
        beton_c3545_m3=210_000,
        beton_c4050_m3=240_000,
        # Acier (FCFA/kg)
        acier_ha400_kg=750,
        acier_ha500_kg=810,
        acier_ha500_vrac_kg=530,
        # Coffrage
        coffrage_bois_m2=18_000,
        coffrage_metal_m2=25_000,
        # Fondations
        pieu_fore_d600_ml=220_000,
        pieu_fore_d800_ml=285_000,
        pieu_fore_d1000_ml=360_000,
        semelle_filante_ml=85_000,
        radier_m2=95_000,
        # Maçonnerie
        agglo_creux_10_m2=18_000,
        agglo_creux_15_m2=24_000,
        agglo_creux_20_m2=30_000,
        agglo_plein_25_m2=38_000,
        brique_pleine_m2=52_000,
        ba13_simple_m2=28_000,
        ba13_double_m2=42_000,
        # Étanchéité
        etanch_sbs_m2=18_500,
        etanch_pvc_m2=22_000,
        etanch_liquide_m2=12_000,
        # Terrassement
        terr_mecanique_m3=8_500,
        terr_manuel_m3=5_000,
        remblai_m3=6_500,
        # Main d'œuvre (FCFA/jour)
        mo_chef_chantier_j=35_000,
        mo_macon_j=18_000,
        mo_ferrailleur_j=20_000,
        mo_electricien_j=22_000,
        mo_plombier_j=22_000,
        mo_manœuvre_j=8_000,
    ),
    mep=PrixMEP(
        # Électricité
        tableau_general_bt=3_500_000,
        transfo_160kva=22_000_000,
        transfo_250kva=32_000_000,
        transfo_400kva=48_000_000,
        groupe_electrogene_100kva=18_000_000,
        groupe_electrogene_200kva=32_000_000,
        groupe_electrogene_400kva=58_000_000,
        compteur_monophase=180_000,
        compteur_triphase=280_000,
        canalisation_cuivre_ml=12_000,
        luminaire_led_standard=35_000,
        luminaire_led_premium=85_000,
        # Plomberie
        colonne_montante_ml=22_000,
        tuyau_pvc_dn50_ml=8_500,
        tuyau_pvc_dn100_ml=14_000,
        tuyau_pvc_dn150_ml=22_000,
        robinet_standard=45_000,
        robinet_eco=75_000,
        wc_standard=85_000,
        wc_double_chasse=130_000,
        cuve_eau_5000l=850_000,
        cuve_eau_10000l=1_500_000,
        pompe_surpresseur_1kw=450_000,
        pompe_surpresseur_3kw=850_000,
        chauffe_eau_electrique_100l=180_000,
        chauffe_eau_solaire_200l=2_100_000,
        # CVC
        split_1cv=450_000,
        split_2cv=750_000,
        split_cassette_4cv=1_800_000,
        vmc_simple_flux=320_000,
        vmc_double_flux=850_000,
        climatiseur_central_kw=280_000,
        # Ascenseurs (fournis posés)
        ascenseur_630kg_r4_r6=28_000_000,
        ascenseur_630kg_r7_r10=38_000_000,
        ascenseur_1000kg_r6_r10=45_000_000,
        ascenseur_1000kg_r11_plus=58_000_000,
        monte_charge_500kg=22_000_000,
        # Courants faibles
        cablage_rj45_ml=3_500,
        prise_rj45=18_000,
        baie_serveur_12u=850_000,
        camera_ip_interieure=180_000,
        camera_ip_exterieure=280_000,
        systeme_controle_acces=350_000,
        interphone_video=220_000,
        # Sécurité incendie
        detecteur_fumee=45_000,
        declencheur_manuel=35_000,
        sirene_flash=55_000,
        centrale_incendie_16zones=1_800_000,
        centrale_incendie_32zones=3_200_000,
        extincteur_6kg_co2=85_000,
        extincteur_9kg_poudre=65_000,
        ria_dn25_ml=45_000,
        sprinkler_tete=85_000,
        sprinkler_centrale=4_500_000,
        # Automatisation
        domotique_logement=850_000,
        bms_systeme=12_000_000,
        eclairage_detecteur_presence=95_000,
    )
)

# ══════════════════════════════════════════════════════════════
# ABIDJAN, CÔTE D'IVOIRE (estimation Mars 2026)
# ══════════════════════════════════════════════════════════════
ABIDJAN = PrixPays(
    pays="Côte d'Ivoire",
    ville_reference="Abidjan",
    devise="XOF",
    date_maj="2026-03",
    fiabilite="estimation",
    notes="Estimation basée sur BNETD, SICOGI et marchés locaux. Légèrement supérieur à Dakar (logistique port). À confirmer terrain.",
    structure=PrixStructure(
        # Béton BPE (marché Abidjan ~8-12% > Dakar — ciment CIMAF CI + transport)
        beton_c2530_m3=182_000,
        beton_c3037_m3=198_000,
        beton_c3545_m3=225_000,
        beton_c4050_m3=258_000,
        # Acier (importé Europe/Chine — transit port Abidjan)
        acier_ha400_kg=780,
        acier_ha500_kg=850,
        acier_ha500_vrac_kg=560,
        # Coffrage
        coffrage_bois_m2=20_000,
        coffrage_metal_m2=28_000,
        # Fondations (sol latéritique Abidjan — pieux moins profonds en général)
        pieu_fore_d600_ml=230_000,
        pieu_fore_d800_ml=295_000,
        pieu_fore_d1000_ml=375_000,
        semelle_filante_ml=90_000,
        radier_m2=100_000,
        # Maçonnerie (briques locales disponibles)
        agglo_creux_10_m2=20_000,
        agglo_creux_15_m2=26_000,
        agglo_creux_20_m2=33_000,
        agglo_plein_25_m2=42_000,
        brique_pleine_m2=55_000,
        ba13_simple_m2=32_000,
        ba13_double_m2=48_000,
        # Étanchéité
        etanch_sbs_m2=20_000,
        etanch_pvc_m2=24_000,
        etanch_liquide_m2=13_500,
        # Terrassement
        terr_mecanique_m3=9_500,
        terr_manuel_m3=5_500,
        remblai_m3=7_000,
        # MO (salaires CI légèrement supérieurs SN)
        mo_chef_chantier_j=40_000,
        mo_macon_j=22_000,
        mo_ferrailleur_j=24_000,
        mo_electricien_j=26_000,
        mo_plombier_j=26_000,
        mo_manœuvre_j=10_000,
    ),
    mep=PrixMEP(
        tableau_general_bt=4_000_000,
        transfo_160kva=24_000_000,
        transfo_250kva=35_000_000,
        transfo_400kva=52_000_000,
        groupe_electrogene_100kva=20_000_000,
        groupe_electrogene_200kva=35_000_000,
        groupe_electrogene_400kva=62_000_000,
        compteur_monophase=200_000,
        compteur_triphase=310_000,
        canalisation_cuivre_ml=13_500,
        luminaire_led_standard=40_000,
        luminaire_led_premium=95_000,
        colonne_montante_ml=25_000,
        tuyau_pvc_dn50_ml=9_500,
        tuyau_pvc_dn100_ml=15_500,
        tuyau_pvc_dn150_ml=24_000,
        robinet_standard=50_000,
        robinet_eco=82_000,
        wc_standard=95_000,
        wc_double_chasse=145_000,
        cuve_eau_5000l=950_000,
        cuve_eau_10000l=1_700_000,
        pompe_surpresseur_1kw=500_000,
        pompe_surpresseur_3kw=950_000,
        chauffe_eau_electrique_100l=200_000,
        chauffe_eau_solaire_200l=2_400_000,
        split_1cv=500_000,
        split_2cv=850_000,
        split_cassette_4cv=2_000_000,
        vmc_simple_flux=360_000,
        vmc_double_flux=950_000,
        climatiseur_central_kw=310_000,
        ascenseur_630kg_r4_r6=32_000_000,
        ascenseur_630kg_r7_r10=43_000_000,
        ascenseur_1000kg_r6_r10=51_000_000,
        ascenseur_1000kg_r11_plus=65_000_000,
        monte_charge_500kg=25_000_000,
        cablage_rj45_ml=4_000,
        prise_rj45=20_000,
        baie_serveur_12u=950_000,
        camera_ip_interieure=200_000,
        camera_ip_exterieure=310_000,
        systeme_controle_acces=390_000,
        interphone_video=250_000,
        detecteur_fumee=50_000,
        declencheur_manuel=40_000,
        sirene_flash=62_000,
        centrale_incendie_16zones=2_000_000,
        centrale_incendie_32zones=3_600_000,
        extincteur_6kg_co2=95_000,
        extincteur_9kg_poudre=72_000,
        ria_dn25_ml=50_000,
        sprinkler_tete=95_000,
        sprinkler_centrale=5_000_000,
        domotique_logement=950_000,
        bms_systeme=14_000_000,
        eclairage_detecteur_presence=108_000,
    )
)

# ══════════════════════════════════════════════════════════════
# CASABLANCA, MAROC (estimation Mars 2026)
# ══════════════════════════════════════════════════════════════
CASABLANCA = PrixPays(
    pays="Maroc",
    ville_reference="Casablanca",
    devise="MAD",
    date_maj="2026-03",
    fiabilite="estimation",
    notes="Estimation basée sur CSMC, CPC Maroc, bordereau DPT. 1 MAD = 60.5 FCFA. Marché plus mature, matériaux locaux abondants.",
    structure=PrixStructure(
        # Béton BPE (MAD/m³ → stocké en FCFA équivalent)
        beton_c2530_m3=int(to_fcfa(850, "MAD")),    # ~850 MAD/m³
        beton_c3037_m3=int(to_fcfa(950, "MAD")),    # ~950 MAD/m³
        beton_c3545_m3=int(to_fcfa(1100, "MAD")),
        beton_c4050_m3=int(to_fcfa(1300, "MAD")),
        # Acier (MAD/kg — production locale Sonasid/Longometal)
        acier_ha400_kg=int(to_fcfa(7.5, "MAD")),    # ~7.5 MAD/kg
        acier_ha500_kg=int(to_fcfa(8.2, "MAD")),
        acier_ha500_vrac_kg=int(to_fcfa(6.8, "MAD")),
        coffrage_bois_m2=int(to_fcfa(120, "MAD")),
        coffrage_metal_m2=int(to_fcfa(180, "MAD")),
        pieu_fore_d600_ml=int(to_fcfa(1800, "MAD")),
        pieu_fore_d800_ml=int(to_fcfa(2400, "MAD")),
        pieu_fore_d1000_ml=int(to_fcfa(3200, "MAD")),
        semelle_filante_ml=int(to_fcfa(750, "MAD")),
        radier_m2=int(to_fcfa(850, "MAD")),
        agglo_creux_10_m2=int(to_fcfa(180, "MAD")),
        agglo_creux_15_m2=int(to_fcfa(220, "MAD")),
        agglo_creux_20_m2=int(to_fcfa(280, "MAD")),
        agglo_plein_25_m2=int(to_fcfa(350, "MAD")),
        brique_pleine_m2=int(to_fcfa(420, "MAD")),
        ba13_simple_m2=int(to_fcfa(280, "MAD")),
        ba13_double_m2=int(to_fcfa(420, "MAD")),
        etanch_sbs_m2=int(to_fcfa(180, "MAD")),
        etanch_pvc_m2=int(to_fcfa(220, "MAD")),
        etanch_liquide_m2=int(to_fcfa(120, "MAD")),
        terr_mecanique_m3=int(to_fcfa(85, "MAD")),
        terr_manuel_m3=int(to_fcfa(50, "MAD")),
        remblai_m3=int(to_fcfa(65, "MAD")),
        mo_chef_chantier_j=int(to_fcfa(500, "MAD")),
        mo_macon_j=int(to_fcfa(280, "MAD")),
        mo_ferrailleur_j=int(to_fcfa(300, "MAD")),
        mo_electricien_j=int(to_fcfa(350, "MAD")),
        mo_plombier_j=int(to_fcfa(350, "MAD")),
        mo_manœuvre_j=int(to_fcfa(150, "MAD")),
    ),
    mep=PrixMEP(
        tableau_general_bt=int(to_fcfa(55_000, "MAD")),
        transfo_160kva=int(to_fcfa(380_000, "MAD")),
        transfo_250kva=int(to_fcfa(560_000, "MAD")),
        transfo_400kva=int(to_fcfa(820_000, "MAD")),
        groupe_electrogene_100kva=int(to_fcfa(320_000, "MAD")),
        groupe_electrogene_200kva=int(to_fcfa(580_000, "MAD")),
        groupe_electrogene_400kva=int(to_fcfa(980_000, "MAD")),
        compteur_monophase=int(to_fcfa(3_500, "MAD")),
        compteur_triphase=int(to_fcfa(5_500, "MAD")),
        canalisation_cuivre_ml=int(to_fcfa(220, "MAD")),
        luminaire_led_standard=int(to_fcfa(650, "MAD")),
        luminaire_led_premium=int(to_fcfa(1_800, "MAD")),
        colonne_montante_ml=int(to_fcfa(420, "MAD")),
        tuyau_pvc_dn50_ml=int(to_fcfa(160, "MAD")),
        tuyau_pvc_dn100_ml=int(to_fcfa(280, "MAD")),
        tuyau_pvc_dn150_ml=int(to_fcfa(420, "MAD")),
        robinet_standard=int(to_fcfa(850, "MAD")),
        robinet_eco=int(to_fcfa(1_400, "MAD")),
        wc_standard=int(to_fcfa(1_600, "MAD")),
        wc_double_chasse=int(to_fcfa(2_500, "MAD")),
        cuve_eau_5000l=int(to_fcfa(15_000, "MAD")),
        cuve_eau_10000l=int(to_fcfa(26_000, "MAD")),
        pompe_surpresseur_1kw=int(to_fcfa(8_500, "MAD")),
        pompe_surpresseur_3kw=int(to_fcfa(15_000, "MAD")),
        chauffe_eau_electrique_100l=int(to_fcfa(3_200, "MAD")),
        chauffe_eau_solaire_200l=int(to_fcfa(38_000, "MAD")),
        split_1cv=int(to_fcfa(8_500, "MAD")),
        split_2cv=int(to_fcfa(14_000, "MAD")),
        split_cassette_4cv=int(to_fcfa(32_000, "MAD")),
        vmc_simple_flux=int(to_fcfa(6_500, "MAD")),
        vmc_double_flux=int(to_fcfa(16_000, "MAD")),
        climatiseur_central_kw=int(to_fcfa(4_800, "MAD")),
        ascenseur_630kg_r4_r6=int(to_fcfa(480_000, "MAD")),
        ascenseur_630kg_r7_r10=int(to_fcfa(650_000, "MAD")),
        ascenseur_1000kg_r6_r10=int(to_fcfa(780_000, "MAD")),
        ascenseur_1000kg_r11_plus=int(to_fcfa(980_000, "MAD")),
        monte_charge_500kg=int(to_fcfa(380_000, "MAD")),
        cablage_rj45_ml=int(to_fcfa(65, "MAD")),
        prise_rj45=int(to_fcfa(380, "MAD")),
        baie_serveur_12u=int(to_fcfa(16_000, "MAD")),
        camera_ip_interieure=int(to_fcfa(3_500, "MAD")),
        camera_ip_exterieure=int(to_fcfa(5_500, "MAD")),
        systeme_controle_acces=int(to_fcfa(7_500, "MAD")),
        interphone_video=int(to_fcfa(4_500, "MAD")),
        detecteur_fumee=int(to_fcfa(850, "MAD")),
        declencheur_manuel=int(to_fcfa(650, "MAD")),
        sirene_flash=int(to_fcfa(1_200, "MAD")),
        centrale_incendie_16zones=int(to_fcfa(35_000, "MAD")),
        centrale_incendie_32zones=int(to_fcfa(62_000, "MAD")),
        extincteur_6kg_co2=int(to_fcfa(1_800, "MAD")),
        extincteur_9kg_poudre=int(to_fcfa(1_200, "MAD")),
        ria_dn25_ml=int(to_fcfa(850, "MAD")),
        sprinkler_tete=int(to_fcfa(1_800, "MAD")),
        sprinkler_centrale=int(to_fcfa(85_000, "MAD")),
        domotique_logement=int(to_fcfa(18_000, "MAD")),
        bms_systeme=int(to_fcfa(220_000, "MAD")),
        eclairage_detecteur_presence=int(to_fcfa(2_200, "MAD")),
    )
)

# ══════════════════════════════════════════════════════════════
# LAGOS, NIGERIA (estimation Mars 2026)
# ══════════════════════════════════════════════════════════════
LAGOS = PrixPays(
    pays="Nigeria",
    ville_reference="Lagos",
    devise="NGN",
    date_maj="2026-03",
    fiabilite="estimation",
    notes="Estimation basée sur NBRRI, NIOB, Builders Magazine Nigeria. Marché volatile (NGN instable). 1 NGN = 0.48 FCFA. À confirmer terrain urgence.",
    structure=PrixStructure(
        # NGN/m³ → FCFA (dévaluation NGN significative 2024-2026)
        beton_c2530_m3=int(to_fcfa(420_000, "NGN")),   # ~420k NGN/m³
        beton_c3037_m3=int(to_fcfa(480_000, "NGN")),
        beton_c3545_m3=int(to_fcfa(560_000, "NGN")),
        beton_c4050_m3=int(to_fcfa(650_000, "NGN")),
        acier_ha400_kg=int(to_fcfa(1_850, "NGN")),     # ~1850 NGN/kg
        acier_ha500_kg=int(to_fcfa(2_100, "NGN")),
        acier_ha500_vrac_kg=int(to_fcfa(1_600, "NGN")),
        coffrage_bois_m2=int(to_fcfa(45_000, "NGN")),
        coffrage_metal_m2=int(to_fcfa(65_000, "NGN")),
        pieu_fore_d600_ml=int(to_fcfa(580_000, "NGN")),
        pieu_fore_d800_ml=int(to_fcfa(780_000, "NGN")),
        pieu_fore_d1000_ml=int(to_fcfa(1_050_000, "NGN")),
        semelle_filante_ml=int(to_fcfa(220_000, "NGN")),
        radier_m2=int(to_fcfa(280_000, "NGN")),
        agglo_creux_10_m2=int(to_fcfa(48_000, "NGN")),
        agglo_creux_15_m2=int(to_fcfa(62_000, "NGN")),
        agglo_creux_20_m2=int(to_fcfa(78_000, "NGN")),
        agglo_plein_25_m2=int(to_fcfa(95_000, "NGN")),
        brique_pleine_m2=int(to_fcfa(120_000, "NGN")),
        ba13_simple_m2=int(to_fcfa(85_000, "NGN")),
        ba13_double_m2=int(to_fcfa(130_000, "NGN")),
        etanch_sbs_m2=int(to_fcfa(55_000, "NGN")),
        etanch_pvc_m2=int(to_fcfa(68_000, "NGN")),
        etanch_liquide_m2=int(to_fcfa(38_000, "NGN")),
        terr_mecanique_m3=int(to_fcfa(28_000, "NGN")),
        terr_manuel_m3=int(to_fcfa(15_000, "NGN")),
        remblai_m3=int(to_fcfa(20_000, "NGN")),
        mo_chef_chantier_j=int(to_fcfa(120_000, "NGN")),
        mo_macon_j=int(to_fcfa(65_000, "NGN")),
        mo_ferrailleur_j=int(to_fcfa(72_000, "NGN")),
        mo_electricien_j=int(to_fcfa(85_000, "NGN")),
        mo_plombier_j=int(to_fcfa(85_000, "NGN")),
        mo_manœuvre_j=int(to_fcfa(28_000, "NGN")),
    ),
    mep=PrixMEP(
        tableau_general_bt=int(to_fcfa(12_000_000, "NGN")),
        transfo_160kva=int(to_fcfa(85_000_000, "NGN")),
        transfo_250kva=int(to_fcfa(125_000_000, "NGN")),
        transfo_400kva=int(to_fcfa(185_000_000, "NGN")),
        groupe_electrogene_100kva=int(to_fcfa(75_000_000, "NGN")),
        groupe_electrogene_200kva=int(to_fcfa(130_000_000, "NGN")),
        groupe_electrogene_400kva=int(to_fcfa(220_000_000, "NGN")),
        compteur_monophase=int(to_fcfa(650_000, "NGN")),
        compteur_triphase=int(to_fcfa(1_100_000, "NGN")),
        canalisation_cuivre_ml=int(to_fcfa(48_000, "NGN")),
        luminaire_led_standard=int(to_fcfa(145_000, "NGN")),
        luminaire_led_premium=int(to_fcfa(380_000, "NGN")),
        colonne_montante_ml=int(to_fcfa(95_000, "NGN")),
        tuyau_pvc_dn50_ml=int(to_fcfa(38_000, "NGN")),
        tuyau_pvc_dn100_ml=int(to_fcfa(62_000, "NGN")),
        tuyau_pvc_dn150_ml=int(to_fcfa(95_000, "NGN")),
        robinet_standard=int(to_fcfa(185_000, "NGN")),
        robinet_eco=int(to_fcfa(320_000, "NGN")),
        wc_standard=int(to_fcfa(380_000, "NGN")),
        wc_double_chasse=int(to_fcfa(580_000, "NGN")),
        cuve_eau_5000l=int(to_fcfa(3_800_000, "NGN")),
        cuve_eau_10000l=int(to_fcfa(6_500_000, "NGN")),
        pompe_surpresseur_1kw=int(to_fcfa(2_200_000, "NGN")),
        pompe_surpresseur_3kw=int(to_fcfa(4_500_000, "NGN")),
        chauffe_eau_electrique_100l=int(to_fcfa(850_000, "NGN")),
        chauffe_eau_solaire_200l=int(to_fcfa(9_500_000, "NGN")),
        split_1cv=int(to_fcfa(2_200_000, "NGN")),
        split_2cv=int(to_fcfa(3_800_000, "NGN")),
        split_cassette_4cv=int(to_fcfa(8_500_000, "NGN")),
        vmc_simple_flux=int(to_fcfa(1_800_000, "NGN")),
        vmc_double_flux=int(to_fcfa(4_200_000, "NGN")),
        climatiseur_central_kw=int(to_fcfa(1_350_000, "NGN")),
        ascenseur_630kg_r4_r6=int(to_fcfa(120_000_000, "NGN")),
        ascenseur_630kg_r7_r10=int(to_fcfa(165_000_000, "NGN")),
        ascenseur_1000kg_r6_r10=int(to_fcfa(200_000_000, "NGN")),
        ascenseur_1000kg_r11_plus=int(to_fcfa(260_000_000, "NGN")),
        monte_charge_500kg=int(to_fcfa(95_000_000, "NGN")),
        cablage_rj45_ml=int(to_fcfa(14_000, "NGN")),
        prise_rj45=int(to_fcfa(85_000, "NGN")),
        baie_serveur_12u=int(to_fcfa(3_800_000, "NGN")),
        camera_ip_interieure=int(to_fcfa(850_000, "NGN")),
        camera_ip_exterieure=int(to_fcfa(1_400_000, "NGN")),
        systeme_controle_acces=int(to_fcfa(1_800_000, "NGN")),
        interphone_video=int(to_fcfa(1_050_000, "NGN")),
        detecteur_fumee=int(to_fcfa(220_000, "NGN")),
        declencheur_manuel=int(to_fcfa(165_000, "NGN")),
        sirene_flash=int(to_fcfa(280_000, "NGN")),
        centrale_incendie_16zones=int(to_fcfa(8_500_000, "NGN")),
        centrale_incendie_32zones=int(to_fcfa(15_000_000, "NGN")),
        extincteur_6kg_co2=int(to_fcfa(420_000, "NGN")),
        extincteur_9kg_poudre=int(to_fcfa(320_000, "NGN")),
        ria_dn25_ml=int(to_fcfa(220_000, "NGN")),
        sprinkler_tete=int(to_fcfa(420_000, "NGN")),
        sprinkler_centrale=int(to_fcfa(22_000_000, "NGN")),
        domotique_logement=int(to_fcfa(4_200_000, "NGN")),
        bms_systeme=int(to_fcfa(58_000_000, "NGN")),
        eclairage_detecteur_presence=int(to_fcfa(480_000, "NGN")),
    )
)

# ══════════════════════════════════════════════════════════════
# ACCRA, GHANA (estimation Mars 2026)
# ══════════════════════════════════════════════════════════════
ACCRA = PrixPays(
    pays="Ghana",
    ville_reference="Accra",
    devise="GHS",
    date_maj="2026-03",
    fiabilite="estimation",
    notes="Estimation basée sur Ghana Institute of Engineers, GIBB Africa. 1 GHS = 57 FCFA. Marché en croissance rapide.",
    structure=PrixStructure(
        beton_c2530_m3=int(to_fcfa(3_200, "GHS")),
        beton_c3037_m3=int(to_fcfa(3_600, "GHS")),
        beton_c3545_m3=int(to_fcfa(4_200, "GHS")),
        beton_c4050_m3=int(to_fcfa(4_900, "GHS")),
        acier_ha400_kg=int(to_fcfa(14, "GHS")),
        acier_ha500_kg=int(to_fcfa(16, "GHS")),
        acier_ha500_vrac_kg=int(to_fcfa(12, "GHS")),
        coffrage_bois_m2=int(to_fcfa(320, "GHS")),
        coffrage_metal_m2=int(to_fcfa(480, "GHS")),
        pieu_fore_d600_ml=int(to_fcfa(4_200, "GHS")),
        pieu_fore_d800_ml=int(to_fcfa(5_800, "GHS")),
        pieu_fore_d1000_ml=int(to_fcfa(7_800, "GHS")),
        semelle_filante_ml=int(to_fcfa(1_600, "GHS")),
        radier_m2=int(to_fcfa(1_850, "GHS")),
        agglo_creux_10_m2=int(to_fcfa(340, "GHS")),
        agglo_creux_15_m2=int(to_fcfa(420, "GHS")),
        agglo_creux_20_m2=int(to_fcfa(520, "GHS")),
        agglo_plein_25_m2=int(to_fcfa(650, "GHS")),
        brique_pleine_m2=int(to_fcfa(820, "GHS")),
        ba13_simple_m2=int(to_fcfa(580, "GHS")),
        ba13_double_m2=int(to_fcfa(880, "GHS")),
        etanch_sbs_m2=int(to_fcfa(380, "GHS")),
        etanch_pvc_m2=int(to_fcfa(460, "GHS")),
        etanch_liquide_m2=int(to_fcfa(260, "GHS")),
        terr_mecanique_m3=int(to_fcfa(180, "GHS")),
        terr_manuel_m3=int(to_fcfa(95, "GHS")),
        remblai_m3=int(to_fcfa(130, "GHS")),
        mo_chef_chantier_j=int(to_fcfa(850, "GHS")),
        mo_macon_j=int(to_fcfa(480, "GHS")),
        mo_ferrailleur_j=int(to_fcfa(520, "GHS")),
        mo_electricien_j=int(to_fcfa(620, "GHS")),
        mo_plombier_j=int(to_fcfa(620, "GHS")),
        mo_manœuvre_j=int(to_fcfa(220, "GHS")),
    ),
    mep=PrixMEP(
        tableau_general_bt=int(to_fcfa(82_000, "GHS")),
        transfo_160kva=int(to_fcfa(580_000, "GHS")),
        transfo_250kva=int(to_fcfa(850_000, "GHS")),
        transfo_400kva=int(to_fcfa(1_280_000, "GHS")),
        groupe_electrogene_100kva=int(to_fcfa(520_000, "GHS")),
        groupe_electrogene_200kva=int(to_fcfa(920_000, "GHS")),
        groupe_electrogene_400kva=int(to_fcfa(1_580_000, "GHS")),
        compteur_monophase=int(to_fcfa(4_800, "GHS")),
        compteur_triphase=int(to_fcfa(8_200, "GHS")),
        canalisation_cuivre_ml=int(to_fcfa(340, "GHS")),
        luminaire_led_standard=int(to_fcfa(980, "GHS")),
        luminaire_led_premium=int(to_fcfa(2_600, "GHS")),
        colonne_montante_ml=int(to_fcfa(650, "GHS")),
        tuyau_pvc_dn50_ml=int(to_fcfa(240, "GHS")),
        tuyau_pvc_dn100_ml=int(to_fcfa(420, "GHS")),
        tuyau_pvc_dn150_ml=int(to_fcfa(650, "GHS")),
        robinet_standard=int(to_fcfa(1_280, "GHS")),
        robinet_eco=int(to_fcfa(2_100, "GHS")),
        wc_standard=int(to_fcfa(2_400, "GHS")),
        wc_double_chasse=int(to_fcfa(3_800, "GHS")),
        cuve_eau_5000l=int(to_fcfa(22_000, "GHS")),
        cuve_eau_10000l=int(to_fcfa(38_000, "GHS")),
        pompe_surpresseur_1kw=int(to_fcfa(12_000, "GHS")),
        pompe_surpresseur_3kw=int(to_fcfa(22_000, "GHS")),
        chauffe_eau_electrique_100l=int(to_fcfa(4_800, "GHS")),
        chauffe_eau_solaire_200l=int(to_fcfa(56_000, "GHS")),
        split_1cv=int(to_fcfa(12_500, "GHS")),
        split_2cv=int(to_fcfa(21_000, "GHS")),
        split_cassette_4cv=int(to_fcfa(48_000, "GHS")),
        vmc_simple_flux=int(to_fcfa(9_500, "GHS")),
        vmc_double_flux=int(to_fcfa(24_000, "GHS")),
        climatiseur_central_kw=int(to_fcfa(7_200, "GHS")),
        ascenseur_630kg_r4_r6=int(to_fcfa(720_000, "GHS")),
        ascenseur_630kg_r7_r10=int(to_fcfa(980_000, "GHS")),
        ascenseur_1000kg_r6_r10=int(to_fcfa(1_180_000, "GHS")),
        ascenseur_1000kg_r11_plus=int(to_fcfa(1_520_000, "GHS")),
        monte_charge_500kg=int(to_fcfa(580_000, "GHS")),
        cablage_rj45_ml=int(to_fcfa(98, "GHS")),
        prise_rj45=int(to_fcfa(580, "GHS")),
        baie_serveur_12u=int(to_fcfa(24_000, "GHS")),
        camera_ip_interieure=int(to_fcfa(5_200, "GHS")),
        camera_ip_exterieure=int(to_fcfa(8_500, "GHS")),
        systeme_controle_acces=int(to_fcfa(11_000, "GHS")),
        interphone_video=int(to_fcfa(6_500, "GHS")),
        detecteur_fumee=int(to_fcfa(1_280, "GHS")),
        declencheur_manuel=int(to_fcfa(980, "GHS")),
        sirene_flash=int(to_fcfa(1_800, "GHS")),
        centrale_incendie_16zones=int(to_fcfa(52_000, "GHS")),
        centrale_incendie_32zones=int(to_fcfa(92_000, "GHS")),
        extincteur_6kg_co2=int(to_fcfa(2_600, "GHS")),
        extincteur_9kg_poudre=int(to_fcfa(1_900, "GHS")),
        ria_dn25_ml=int(to_fcfa(1_280, "GHS")),
        sprinkler_tete=int(to_fcfa(2_600, "GHS")),
        sprinkler_centrale=int(to_fcfa(130_000, "GHS")),
        domotique_logement=int(to_fcfa(26_000, "GHS")),
        bms_systeme=int(to_fcfa(340_000, "GHS")),
        eclairage_detecteur_presence=int(to_fcfa(3_200, "GHS")),
    )
)

# ══════════════════════════════════════════════════════════════
# INDEX PAYS
# ══════════════════════════════════════════════════════════════
PAYS = {
    "dakar":       DAKAR,
    "senegal":     DAKAR,
    "abidjan":     ABIDJAN,
    "cote_ivoire": ABIDJAN,
    "casablanca":  CASABLANCA,
    "rabat":       CASABLANCA,  # Rabat ≈ Casablanca + 5%
    "maroc":       CASABLANCA,
    "lagos":       LAGOS,
    "nigeria":     LAGOS,
    "accra":       ACCRA,
    "ghana":       ACCRA,
}

def get_prix(ville: str) -> PrixPays:
    """
    Retourne la grille de prix pour une ville donnée.
    Fallback sur Dakar si ville inconnue.
    """
    key = ville.lower().strip()
    # Correspondance partielle
    for k, v in PAYS.items():
        if k in key or key in k:
            return v
    return DAKAR  # fallback

def get_prix_structure(ville: str) -> PrixStructure:
    return get_prix(ville).structure

def get_prix_mep(ville: str) -> PrixMEP:
    return get_prix(ville).mep

def comparer_prix(poste: str, villes: list = None) -> dict:
    """
    Compare un poste de prix entre plusieurs villes.
    Utile pour le rapport multi-pays.
    """
    if villes is None:
        villes = ["dakar", "abidjan", "casablanca", "lagos", "accra"]
    result = {}
    for v in villes:
        p = get_prix(v)
        val_s = getattr(p.structure, poste, None)
        val_m = getattr(p.mep, poste, None)
        val = val_s or val_m
        if val:
            result[p.ville_reference] = {
                "prix_fcfa": val,
                "devise": p.devise,
                "fiabilite": p.fiabilite,
            }
    return result


# ══════════════════════════════════════════════════════════════
# TEST
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=== BASE DE PRIX TIJAN AI — MULTI-PAYS ===\n")
    for ville in ["dakar", "abidjan", "casablanca", "lagos", "accra"]:
        p = get_prix(ville)
        s = p.structure
        print(f"{p.pays} ({p.ville_reference}) — {p.fiabilite}")
        print(f"  Béton C30/37    : {s.beton_c3037_m3:>12,} FCFA/m³")
        print(f"  Acier HA500     : {s.acier_ha500_kg:>12,} FCFA/kg")
        print(f"  Pieu Ø800       : {s.pieu_fore_d800_ml:>12,} FCFA/ml")
        print(f"  Agglos 15cm     : {s.agglo_creux_15_m2:>12,} FCFA/m²")
        m = p.mep
        print(f"  Split 1CV       : {m.split_1cv:>12,} FCFA")
        print(f"  Asc. 630kg R4-6 : {m.ascenseur_630kg_r4_r6:>12,} FCFA")
        print()
