"""Shared fixtures for Tijan AI test suite."""
import pytest

BASE_URL = "https://build-ai-backend.onrender.com"

DEFAULT_PARAMS = {
    "nom": "Projet Test",
    "ville": "Dakar",
    "pays": "Senegal",
    "usage": "residentiel",
    "nb_niveaux": 4,
    "hauteur_etage_m": 3.0,
    "surface_emprise_m2": 500.0,
    "surface_terrain_m2": 1200.0,
    "portee_max_m": 5.5,
    "portee_min_m": 4.0,
    "nb_travees_x": 3,
    "nb_travees_y": 2,
    "classe_beton": "",
    "classe_acier": "",
    "pression_sol_MPa": 0.0,
    "distance_mer_km": 0.0,
    "zone_sismique": -1,
    "lang": "fr",
}


@pytest.fixture
def base_url():
    return BASE_URL


@pytest.fixture
def default_params():
    return DEFAULT_PARAMS.copy()
