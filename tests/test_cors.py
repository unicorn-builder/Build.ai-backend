"""
Test: CORS configuration — tijan.ai must be allowed on all endpoints.

Run: pytest tests/test_cors.py -v
"""
import pytest
import requests

from .conftest import BASE_URL, DEFAULT_PARAMS

TIMEOUT = 120
ORIGIN = "https://tijan.ai"

# All PDF endpoints that the frontend calls
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


class TestCORSConfig:
    def test_cors_health(self):
        """Health endpoint must allow tijan.ai origin."""
        r = requests.get(
            f"{BASE_URL}/health",
            headers={"Origin": ORIGIN},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        acao = r.headers.get("access-control-allow-origin", "")
        assert ORIGIN in acao, f"CORS missing tijan.ai: got '{acao}'"

    def test_cors_preflight(self):
        """OPTIONS preflight must return correct CORS headers."""
        r = requests.options(
            f"{BASE_URL}/calculate",
            headers={
                "Origin": ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        acao = r.headers.get("access-control-allow-origin", "")
        assert ORIGIN in acao, f"Preflight CORS missing tijan.ai: got '{acao}'"

    @pytest.mark.parametrize("endpoint", PDF_ENDPOINTS)
    def test_cors_pdf_endpoint(self, endpoint):
        """Every PDF endpoint must return CORS header for tijan.ai."""
        r = requests.post(
            f"{BASE_URL}{endpoint}",
            json=DEFAULT_PARAMS,
            headers={"Origin": ORIGIN},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        acao = r.headers.get("access-control-allow-origin", "")
        assert ORIGIN in acao, f"{endpoint} CORS missing tijan.ai: got '{acao}'"
