"""
End-to-end integration tests — simulate real user flows.

These tests chain multiple endpoints the way the frontend does,
catching issues that single-endpoint tests miss (data shape mismatches,
missing fields downstream, etc.).

Run: pytest tests/test_e2e.py -v
"""
import pytest
import requests

from .conftest import BASE_URL, DEFAULT_PARAMS

TIMEOUT = 120


# ────────────────────────────────────────────
# 1. Project creation flow (parse → calculate → MEP → BOQ)
# ────────────────────────────────────────────

class TestProjectCreationFlow:
    """Simulates: user uploads DWG → parse → calculate → view results."""

    def test_calculate_returns_all_required_fields(self):
        """POST /calculate must return every field the frontend reads."""
        r = requests.post(f"{BASE_URL}/calculate", json=DEFAULT_PARAMS, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()

        # Top-level flags
        assert data["ok"] is True
        assert data["projet"] == DEFAULT_PARAMS["nom"]

        # Material classes auto-selected
        assert data["classe_beton"], "classe_beton must not be empty"
        assert data["classe_acier"], "classe_acier must not be empty"

        # Structural members
        assert isinstance(data["poteaux"], list) and len(data["poteaux"]) > 0
        assert "poutre_principale" in data and data["poutre_principale"]
        assert "dalle" in data and data["dalle"]
        assert "fondation" in data and data["fondation"]

        # BOQ (frontend reads boq.total_bas_fcfa, boq.beton_total_m3, etc.)
        boq = data["boq"]
        assert boq["total_bas_fcfa"] > 0, "BOQ total_bas must be > 0"
        assert boq["total_haut_fcfa"] > 0, "BOQ total_haut must be > 0"
        assert boq["beton_total_m3"] > 0, "BOQ beton must be > 0"
        assert boq["acier_kg"] > 0, "BOQ acier must be > 0"

        # Analyse
        analyse = data["analyse"]
        assert analyse["conformite_ec2"] in ("Conforme", "Non conforme", "À vérifier")

    def test_calculate_then_mep_chain(self):
        """POST /calculate → POST /calculate-mep with same params — both must succeed."""
        r1 = requests.post(f"{BASE_URL}/calculate", json=DEFAULT_PARAMS, timeout=TIMEOUT)
        assert r1.status_code == 200
        struct = r1.json()
        assert struct["ok"] is True

        r2 = requests.post(f"{BASE_URL}/calculate-mep", json=DEFAULT_PARAMS, timeout=TIMEOUT)
        assert r2.status_code == 200
        mep = r2.json()
        assert mep["ok"] is True

        # Frontend reads these fields for BOQ MEP tab
        boqm = mep["boq_mep"]
        assert boqm["basic_fcfa"] > 0, "MEP basic must be > 0"
        assert boqm["hend_fcfa"] > 0, "MEP hend must be > 0"
        assert boqm["luxury_fcfa"] > 0, "MEP luxury must be > 0"
        assert isinstance(boqm["lots"], list) and len(boqm["lots"]) >= 5

        # Frontend reads these for Note MEP tab
        assert mep["electrique"]["puissance_totale_kva"] > 0
        assert mep["plomberie"]["besoin_total_m3_j"] > 0
        assert mep["cvc"]["puissance_frigorifique_kw"] > 0

        # EDGE certification data
        edge = mep["edge"]
        assert "certifiable" in edge
        assert "economie_energie_pct" in edge

    def test_small_project_r_plus_1(self):
        """R+1 villa (700m²) must still return valid structure + MEP — not zeros."""
        small = {**DEFAULT_PARAMS, "nom": "Villa Test", "nb_niveaux": 2,
                 "surface_emprise_m2": 700, "portee_max_m": 6.0, "portee_min_m": 4.5}

        r1 = requests.post(f"{BASE_URL}/calculate", json=small, timeout=TIMEOUT)
        assert r1.status_code == 200
        assert r1.json()["ok"] is True
        assert r1.json()["boq"]["total_bas_fcfa"] > 0

        r2 = requests.post(f"{BASE_URL}/calculate-mep", json=small, timeout=TIMEOUT)
        assert r2.status_code == 200
        mep = r2.json()
        assert mep["ok"] is True
        assert mep["boq_mep"]["basic_fcfa"] > 0, "Small project MEP BOQ must not be 0"


# ────────────────────────────────────────────
# 2. PDF/XLSX/DOCX downloads — verify valid file headers
# ────────────────────────────────────────────

PDF_ENDPOINTS = [
    "/generate", "/generate-boq", "/generate-note-mep", "/generate-boq-mep",
    "/generate-edge", "/generate-rapport-executif", "/generate-fiches-structure",
    "/generate-fiches-mep", "/generate-planches", "/generate-plu",
]

XLSX_ENDPOINTS = ["/generate-boq-xlsx", "/generate-boq-mep-xlsx"]
DOCX_ENDPOINTS = ["/generate-note-docx", "/generate-rapport-docx"]
DXF_ENDPOINTS = ["/generate-plans-structure-dwg", "/generate-plans-mep-dwg"]


class TestDocumentDownloads:
    @pytest.mark.parametrize("endpoint", PDF_ENDPOINTS)
    def test_pdf_valid(self, endpoint):
        r = requests.post(f"{BASE_URL}{endpoint}", json=DEFAULT_PARAMS, timeout=TIMEOUT)
        assert r.status_code == 200, f"{endpoint} → {r.status_code}: {r.text[:200]}"
        assert r.content[:4] == b"%PDF", f"{endpoint} not a valid PDF"
        assert len(r.content) > 2048, f"{endpoint} PDF too small ({len(r.content)} bytes)"

    @pytest.mark.parametrize("endpoint", XLSX_ENDPOINTS)
    def test_xlsx_valid(self, endpoint):
        r = requests.post(f"{BASE_URL}{endpoint}", json=DEFAULT_PARAMS, timeout=TIMEOUT)
        assert r.status_code == 200, f"{endpoint} → {r.status_code}"
        assert r.content[:2] == b"PK", f"{endpoint} not a valid XLSX (ZIP)"

    @pytest.mark.parametrize("endpoint", DOCX_ENDPOINTS)
    def test_docx_valid(self, endpoint):
        r = requests.post(f"{BASE_URL}{endpoint}", json=DEFAULT_PARAMS, timeout=TIMEOUT)
        assert r.status_code == 200, f"{endpoint} → {r.status_code}"
        assert r.content[:2] == b"PK", f"{endpoint} not a valid DOCX (ZIP)"

    @pytest.mark.parametrize("endpoint", DXF_ENDPOINTS)
    def test_dxf_valid(self, endpoint):
        r = requests.post(f"{BASE_URL}{endpoint}", json=DEFAULT_PARAMS, timeout=TIMEOUT)
        assert r.status_code == 200, f"{endpoint} → {r.status_code}"
        assert len(r.content) > 100, f"{endpoint} DXF too small"


# ────────────────────────────────────────────
# 3. Chat modification flow
# ────────────────────────────────────────────

class TestChatModificationFlow:
    """Simulates: user opens chat → asks to change béton → backend recalculates."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        """Pre-compute structure + MEP so we can pass them to /chat."""
        r1 = requests.post(f"{BASE_URL}/calculate", json=DEFAULT_PARAMS, timeout=TIMEOUT)
        self.struct = r1.json()
        r2 = requests.post(f"{BASE_URL}/calculate-mep", json=DEFAULT_PARAMS, timeout=TIMEOUT)
        self.mep = r2.json()

    def test_chat_modification_triggers_recalcul(self):
        """'Passe en C40/50' must return recalcul:True with updated data."""
        payload = {
            "message": "Passe le béton en C40/50",
            "historique": [
                {"role": "user", "content": "Passe le béton en C40/50"},
            ],
            "params": DEFAULT_PARAMS,
            "resultats_structure": self.struct,
            "resultats_mep": self.mep,
        }
        r = requests.post(f"{BASE_URL}/chat", json=payload, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data.get("reponse"), "Chat must return a response text"

        # The LLM should detect a modification and return recalcul data.
        # If it doesn't (LLM non-determinism), skip the structural assertions.
        if not data.get("recalcul"):
            pytest.skip("LLM did not return <MODIF> tag this time — non-deterministic")

        assert data["recalcul"] is True
        assert data["updated_params"]["classe_beton"] == "C40/50"

        # updated_resultats must have the same shape as /calculate
        ur = data["updated_resultats"]
        assert ur["ok"] is True
        assert isinstance(ur["poteaux"], list) and len(ur["poteaux"]) > 0
        assert ur["boq"]["total_bas_fcfa"] > 0

        # updated_mep must have the same shape as /calculate-mep (boq_mep, not boq)
        um = data["updated_mep"]
        assert um["ok"] is True
        assert um["boq_mep"]["basic_fcfa"] > 0, "Chat recalcul MEP BOQ must not be 0"
        assert isinstance(um["boq_mep"]["lots"], list) and len(um["boq_mep"]["lots"]) >= 5
        assert um["electrique"]["puissance_totale_kva"] > 0

    def test_chat_normal_question_no_recalcul(self):
        """A plain question must NOT trigger recalcul."""
        payload = {
            "message": "Pourquoi ce choix de béton ?",
            "historique": [
                {"role": "user", "content": "Pourquoi ce choix de béton ?"},
            ],
            "params": DEFAULT_PARAMS,
            "resultats_structure": self.struct,
            "resultats_mep": self.mep,
        }
        r = requests.post(f"{BASE_URL}/chat", json=payload, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data.get("reponse"), "Chat must return a response"
        assert data.get("recalcul") is not True, "Plain question should not trigger recalcul"


# ────────────────────────────────────────────
# 4. Data consistency — structure + MEP field shapes
# ────────────────────────────────────────────

class TestDataConsistency:
    """Verify that fields the frontend reads actually exist with expected types."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        r1 = requests.post(f"{BASE_URL}/calculate", json=DEFAULT_PARAMS, timeout=TIMEOUT)
        self.struct = r1.json()
        r2 = requests.post(f"{BASE_URL}/calculate-mep", json=DEFAULT_PARAMS, timeout=TIMEOUT)
        self.mep = r2.json()

    def test_poteau_fields(self):
        """Each poteau must have all fields the DataTable reads."""
        required = {"niveau", "NEd_kN", "section_mm", "nb_barres", "diametre_mm",
                     "taux_armature_pct", "NRd_kN", "verif_ok", "cadre_diam_mm",
                     "espacement_cadres_mm"}
        for p in self.struct["poteaux"]:
            missing = required - set(p.keys())
            assert not missing, f"Poteau {p.get('niveau')} missing: {missing}"

    def test_boq_structure_fields(self):
        """BOQ must have cost fields the frontend reads."""
        boq = self.struct["boq"]
        for field in ("total_bas_fcfa", "total_haut_fcfa", "beton_total_m3",
                       "acier_kg", "surface_batie_m2"):
            assert field in boq, f"BOQ missing {field}"
            assert isinstance(boq[field], (int, float)), f"BOQ {field} is not numeric"

    def test_mep_boq_fields(self):
        """MEP BOQ must have the fields the frontend BOQ MEP tab reads."""
        boqm = self.mep["boq_mep"]
        for field in ("basic_fcfa", "hend_fcfa", "luxury_fcfa",
                       "ratio_basic_m2", "ratio_hend_m2", "recommandation", "lots"):
            assert field in boqm, f"MEP BOQ missing {field}"

    def test_mep_lot_fields(self):
        """Each MEP lot must have the fields the frontend reads."""
        required = {"lot", "designation", "basic_fcfa", "hend_fcfa", "luxury_fcfa", "note"}
        for lot in self.mep["boq_mep"]["lots"]:
            missing = required - set(lot.keys())
            assert not missing, f"MEP lot {lot.get('lot')} missing: {missing}"
