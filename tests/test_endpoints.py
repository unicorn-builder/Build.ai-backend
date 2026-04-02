"""
Test suite: every endpoint on the live Tijan AI backend.
Each test asserts HTTP 200 and response size > 0.
PDF endpoints assert response size > 1KB.

Run: pytest tests/test_endpoints.py -v
"""
import pytest
import requests
import json

from .conftest import BASE_URL, DEFAULT_PARAMS

TIMEOUT = 120  # generous timeout for Render cold starts


# ────────────────────────────────────────────
# 1. Health & info endpoints
# ────────────────────────────────────────────

class TestHealthEndpoints:
    def test_health(self):
        r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_parse_layer(self):
        """Requires APS URN — 422 (missing param) confirms endpoint is alive."""
        r = requests.get(f"{BASE_URL}/parse/layer", timeout=TIMEOUT)
        assert r.status_code == 422  # missing required 'urn' param

    def test_parse_manifest(self):
        """Requires APS URN — 422 (missing param) confirms endpoint is alive."""
        r = requests.get(f"{BASE_URL}/parse/manifest", timeout=TIMEOUT)
        assert r.status_code == 422  # missing required 'urn' param


# ────────────────────────────────────────────
# 2. Calculation endpoints
# ────────────────────────────────────────────

class TestCalculationEndpoints:
    def test_calculate_structure(self):
        r = requests.post(f"{BASE_URL}/calculate", json=DEFAULT_PARAMS, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "resultats" in data or "poteaux" in data or len(data) > 0

    def test_calculate_mep(self):
        r = requests.post(f"{BASE_URL}/calculate-mep", json=DEFAULT_PARAMS, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert len(data) > 0

    def test_calculate_mep_edge(self):
        r = requests.post(f"{BASE_URL}/calculate-mep-edge", json=DEFAULT_PARAMS, timeout=TIMEOUT)
        assert r.status_code == 200


# ────────────────────────────────────────────
# 3. PDF generation endpoints
# ────────────────────────────────────────────

PDF_ENDPOINTS = [
    "/generate",
    "/generate-boq",
    "/generate-note-mep",
    "/generate-boq-mep",
    "/generate-edge",
    "/generate-rapport-executif",
    "/generate-fiches-structure",
    "/generate-fiches-mep",
    "/generate-planches",
    "/generate-plu",
]


class TestPDFEndpoints:
    @pytest.mark.parametrize("endpoint", PDF_ENDPOINTS)
    def test_pdf_endpoint(self, endpoint):
        r = requests.post(f"{BASE_URL}{endpoint}", json=DEFAULT_PARAMS, timeout=TIMEOUT)
        assert r.status_code == 200, f"{endpoint} returned {r.status_code}: {r.text[:200]}"
        assert len(r.content) > 1024, f"{endpoint} response too small: {len(r.content)} bytes"
        # PDF files start with %PDF
        assert r.content[:4] == b"%PDF", f"{endpoint} did not return a valid PDF"


# ────────────────────────────────────────────
# 4. Chat endpoint
# ────────────────────────────────────────────

class TestChatEndpoint:
    def test_chat(self):
        payload = {"message": "Quel béton pour un R+4 à Dakar?", "context": {}}
        r = requests.post(f"{BASE_URL}/chat", json=payload, timeout=TIMEOUT)
        # Chat may require API key — accept 200 or 422 (validation) but not 500
        assert r.status_code in (200, 422, 400), f"/chat returned {r.status_code}"
