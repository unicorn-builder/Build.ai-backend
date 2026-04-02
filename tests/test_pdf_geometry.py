"""
Test: PDF geometry extraction via pdf_to_geometry().
Asserts vector extraction works on sample PDFs.

Run: pytest tests/test_pdf_geometry.py -v
"""
import os
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestPDFGeometry:
    def test_pdf_to_geometry_structure_pdf(self):
        """pdf_to_geometry() must extract walls from a structure PDF."""
        import sys
        sys.path.insert(0, REPO_ROOT)
        from dwg_converter import pdf_to_geometry

        # Use coffrage PDF — should have structural walls drawn as vectors
        pdf_path = os.path.join(REPO_ROOT, "mep_output", "LOT_COFFRAGE_Sakho.pdf")
        if not os.path.exists(pdf_path):
            pytest.skip("Coffrage PDF not available")

        result = pdf_to_geometry(pdf_path)
        assert result is not None, "pdf_to_geometry returned None — expected walls"
        assert "walls" in result
        walls = result["walls"]
        assert len(walls) > 10, f"Expected > 10 walls, got {len(walls)}"

    def test_pdf_to_geometry_returns_correct_format(self):
        """Geometry dict must have walls, windows, doors, rooms keys."""
        import sys
        sys.path.insert(0, REPO_ROOT)
        from dwg_converter import pdf_to_geometry

        pdf_path = os.path.join(REPO_ROOT, "mep_output", "LOT_COFFRAGE_Sakho.pdf")
        if not os.path.exists(pdf_path):
            pytest.skip("Coffrage PDF not available")

        result = pdf_to_geometry(pdf_path)
        if result is None:
            pytest.skip("PDF did not yield geometry")

        for key in ("walls", "windows", "doors", "rooms"):
            assert key in result, f"Missing key: {key}"
            assert isinstance(result[key], list)

    def test_pdf_wall_format(self):
        """Each wall from PDF must be a line with start/end coords."""
        import sys
        sys.path.insert(0, REPO_ROOT)
        from dwg_converter import pdf_to_geometry

        pdf_path = os.path.join(REPO_ROOT, "mep_output", "LOT_COFFRAGE_Sakho.pdf")
        if not os.path.exists(pdf_path):
            pytest.skip("Coffrage PDF not available")

        result = pdf_to_geometry(pdf_path)
        if result is None:
            pytest.skip("PDF did not yield geometry")

        for wall in result["walls"][:20]:
            assert wall["type"] == "line"
            assert len(wall["start"]) == 2
            assert len(wall["end"]) == 2
            assert all(isinstance(v, (int, float)) for v in wall["start"])
