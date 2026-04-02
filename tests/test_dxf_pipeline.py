"""
Test: DXF geometry extraction pipeline.
Tests _extract_dxf_geometry() and validates Sakho geometry data.

Run: pytest tests/test_dxf_pipeline.py -v
"""
import os
import json
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestDXFPipeline:
    def test_sakho_geometry_has_walls(self):
        """Sakho etages 1-7 geometry must have > 500 walls."""
        geom_path = os.path.join(REPO_ROOT, "sakho_etages_1_7_geom.json")
        assert os.path.exists(geom_path), f"Missing: {geom_path}"

        with open(geom_path) as f:
            geom = json.load(f)

        walls = geom.get("walls", [])
        assert len(walls) > 500, f"Expected > 500 walls, got {len(walls)}"
        assert "rooms" in geom
        assert "doors" in geom or "windows" in geom

    def test_extract_dxf_geometry_runs(self):
        """_extract_dxf_geometry() must parse a DXF file without error."""
        import sys
        sys.path.insert(0, REPO_ROOT)
        from main import _extract_dxf_geometry

        dxf_path = os.path.join(REPO_ROOT, "mep_output", "LOT_STRUCTURE_COMPLET_Sakho.dxf")
        if not os.path.exists(dxf_path):
            pytest.skip("Structure DXF not available")

        # Must not raise — returns geometry dict or None
        result = _extract_dxf_geometry(dxf_path)
        # Structure DXF uses ARCH_MURS layer (not in default wall_layers)
        # so result may be None — that's OK, the point is no crash
        if result is not None:
            assert "walls" in result
            assert isinstance(result["walls"], list)

    def test_all_sakho_geometry_files_valid(self):
        """All sakho geometry JSON files must be valid and contain walls."""
        geom_files = [
            "sakho_rdc_geom.json",
            "sakho_etages_1_7_geom.json",
            "sakho_etage_8_geom.json",
            "sakho_sous_sol_geom.json",
            "sakho_terrasse_geom.json",
        ]
        for fname in geom_files:
            path = os.path.join(REPO_ROOT, fname)
            if not os.path.exists(path):
                continue
            with open(path) as f:
                geom = json.load(f)
            assert "walls" in geom, f"{fname} missing 'walls' key"
            assert len(geom["walls"]) > 0, f"{fname} has 0 walls"

    def test_geometry_wall_format(self):
        """Each wall entity must have the correct structure."""
        geom_path = os.path.join(REPO_ROOT, "sakho_etages_1_7_geom.json")
        with open(geom_path) as f:
            geom = json.load(f)

        for wall in geom["walls"][:20]:
            assert "type" in wall
            if wall["type"] == "line":
                assert "start" in wall and "end" in wall
                assert len(wall["start"]) == 2
                assert len(wall["end"]) == 2
            elif wall["type"] == "polyline":
                assert "points" in wall
                assert len(wall["points"]) >= 2
