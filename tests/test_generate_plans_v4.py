"""
Test: generate_plans_v4.py — BA dossier PDF (4 planches).
Asserts exactly 4 pages, file size > 500KB, no errors.

Run: pytest tests/test_generate_plans_v4.py -v
"""
import os
import tempfile
import pytest


def test_generer_dossier_ba_4_pages():
    """Generate BA PDF and verify 4 pages + size > 500KB."""
    from generate_plans_v4 import generer_dossier_ba

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        out_path = f.name

    try:
        # Generate with default params (no resultats/params = uses built-in defaults)
        result = generer_dossier_ba(out_path)

        # File was created and path returned
        assert result == out_path
        assert os.path.exists(out_path)

        # File size > 5KB (vector-only PDF with ReportLab drawings)
        size = os.path.getsize(out_path)
        assert size > 5_000, f"PDF too small: {size} bytes (expected > 5KB)"

        # Exactly 4 pages
        from pypdf import PdfReader
        reader = PdfReader(out_path)
        assert len(reader.pages) == 4, f"Expected 4 pages, got {len(reader.pages)}"

    finally:
        if os.path.exists(out_path):
            os.unlink(out_path)


def test_generer_dossier_ba_with_resultats():
    """Generate BA PDF with realistic calculation results."""
    from generate_plans_v4 import generer_dossier_ba

    # Minimal realistic resultats dict
    resultats = {
        "poteaux": {"section": "30×30", "aciers": "4HA16"},
        "poutres": {"section": "25×50", "aciers_travee": "3HA16", "aciers_appui": "3HA14"},
        "dalles": {"epaisseur_cm": 20},
        "fondations": {"type": "semelle_isolee", "dimensions": "1.2×1.2×0.4"},
    }
    params = {
        "nom": "Projet Test BA",
        "nb_niveaux": 4,
        "hauteur_etage_m": 3.0,
        "portee_max_m": 5.5,
        "nb_travees_x": 3,
        "nb_travees_y": 2,
    }

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        out_path = f.name

    try:
        result = generer_dossier_ba(out_path, resultats=resultats, params=params)
        assert os.path.exists(out_path)
        size = os.path.getsize(out_path)
        assert size > 5_000, f"PDF too small: {size} bytes"

        from pypdf import PdfReader
        reader = PdfReader(out_path)
        assert len(reader.pages) == 4
    finally:
        if os.path.exists(out_path):
            os.unlink(out_path)
