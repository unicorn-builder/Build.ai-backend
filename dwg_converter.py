"""
dwg_converter.py — DWG ↔ DXF conversion

Strategy (in priority order):
  1. LibreDWG dwg2dxf (local, instant, ~1s/file, apt-get install libredwg-tools)
  2. ODA File Converter (local, instant, ~2s/file)
  3. APS Model Derivative (cloud, ~2min/file) — fallback

All inputs are converted to DXF (pivot format).
ezdxf reads the DXF for full geometry extraction.
"""
import os
import shutil
import subprocess
import tempfile
import logging
import time

logger = logging.getLogger("dwg_converter")


def _find_dwg2dxf():
    """Find LibreDWG dwg2dxf binary."""
    path = shutil.which('dwg2dxf')
    if path:
        return path
    for p in ['/usr/bin/dwg2dxf', '/usr/local/bin/dwg2dxf']:
        if os.path.isfile(p):
            return p
    return None


def _find_oda():
    """Find ODA File Converter binary."""
    for name in ['ODAFileConverter', 'TeighaFileConverter']:
        path = shutil.which(name)
        if path:
            return path
    for path in ['/usr/bin/ODAFileConverter', '/usr/local/bin/ODAFileConverter',
                 '/opt/ODAFileConverter/ODAFileConverter']:
        if os.path.isfile(path):
            return path
    return None


DWG2DXF_PATH = _find_dwg2dxf()
ODA_PATH = _find_oda()


def dwg_to_dxf_libredwg(dwg_path: str) -> str:
    """
    Convert DWG → DXF using LibreDWG dwg2dxf.
    ~1 second per file, no cloud, no API key.
    """
    if not DWG2DXF_PATH:
        return None

    try:
        output = tempfile.mktemp(suffix='.dxf', prefix='tijan_')
        cmd = [DWG2DXF_PATH, '-o', output, dwg_path]
        logger.info(f"dwg2dxf converting {os.path.basename(dwg_path)}...")
        start = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        elapsed = time.time() - start
        logger.info(f"dwg2dxf done in {elapsed:.1f}s (rc={result.returncode})")

        if os.path.isfile(output) and os.path.getsize(output) > 100:
            return output

        logger.warning(f"dwg2dxf produced no output: stderr={result.stderr[:200]}")
        try: os.unlink(output)
        except: pass
        return None

    except subprocess.TimeoutExpired:
        logger.warning("dwg2dxf timeout")
        return None
    except Exception as e:
        logger.warning(f"dwg2dxf error: {e}")
        return None


def dwg_to_dxf_oda(dwg_path: str) -> str:
    """
    Convert DWG → DXF using ODA File Converter.
    Returns path to generated DXF file, or None on failure.
    ~1-3 seconds per file.
    """
    if not ODA_PATH:
        return None

    input_dir = tempfile.mkdtemp(prefix="oda_in_")
    output_dir = tempfile.mkdtemp(prefix="oda_out_")

    try:
        # Copy DWG to input dir (ODA works on directories)
        base = os.path.basename(dwg_path)
        safe_name = base.replace(' ', '_')
        shutil.copy2(dwg_path, os.path.join(input_dir, safe_name))

        # Run ODA: input_dir output_dir version type recursive audit
        cmd = [ODA_PATH, input_dir, output_dir, "ACAD2018", "DXF", "0", "1"]
        logger.info(f"ODA converting {base}...")
        start = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        elapsed = time.time() - start
        logger.info(f"ODA done in {elapsed:.1f}s (returncode={result.returncode})")

        # Find the output DXF
        dxf_name = safe_name.rsplit('.', 1)[0] + '.dxf'
        dxf_path = os.path.join(output_dir, dxf_name)
        if os.path.isfile(dxf_path):
            # Move to a temp file that won't be cleaned up with dirs
            final = tempfile.mktemp(suffix='.dxf', prefix='tijan_')
            shutil.move(dxf_path, final)
            return final

        # Try finding any .dxf in output
        for f in os.listdir(output_dir):
            if f.lower().endswith('.dxf'):
                final = tempfile.mktemp(suffix='.dxf', prefix='tijan_')
                shutil.move(os.path.join(output_dir, f), final)
                return final

        logger.warning(f"ODA produced no DXF output for {base}")
        return None

    except subprocess.TimeoutExpired:
        logger.warning("ODA timeout")
        return None
    except Exception as e:
        logger.warning(f"ODA error: {e}")
        return None
    finally:
        shutil.rmtree(input_dir, ignore_errors=True)
        shutil.rmtree(output_dir, ignore_errors=True)


def dwg_to_dxf_aps(dwg_path: str, ville: str = "Dakar") -> str:
    """
    Convert DWG → DXF via APS (fallback when ODA not available).
    Uploads to APS, requests SVF2 translation, extracts properties,
    returns a synthetic DXF built from the extracted geometry.

    This is slower (~2min) but works without ODA installed.
    Returns path to generated DXF, or None.
    """
    try:
        from aps_parser_v2 import parser_dwg_aps
        result = parser_dwg_aps(dwg_path, ville=ville)
        if not result.get("ok") or not result.get("urn"):
            return None

        # We can't get a real DXF from APS free tier easily
        # But we CAN extract geometry via properties and write a DXF with ezdxf
        from main import _load_project_geometry
        geom = _load_project_geometry(result["urn"])
        if not geom or len(geom.get('walls', [])) < 5:
            return None

        # Write geometry to DXF using ezdxf
        return _write_geometry_to_dxf(geom)

    except Exception as e:
        logger.warning(f"APS fallback error: {e}")
        return None


def _write_geometry_to_dxf(geometry: dict) -> str:
    """Write extracted geometry dict to a DXF file using ezdxf."""
    import ezdxf

    doc = ezdxf.new('R2010')
    msp = doc.modelspace()

    doc.layers.new('MURS', dxfattribs={'color': 7})
    doc.layers.new('FENETRES', dxfattribs={'color': 4})
    doc.layers.new('PORTES', dxfattribs={'color': 30})
    doc.layers.new('PIECES', dxfattribs={'color': 2})

    for item in geometry.get('walls', []):
        if item['type'] == 'line':
            msp.add_line(item['start'], item['end'], dxfattribs={'layer': 'MURS'})
        elif item['type'] == 'polyline':
            pts = [tuple(p) for p in item['points']]
            poly = msp.add_lwpolyline(pts, dxfattribs={'layer': 'MURS'})
            if item.get('closed'):
                poly.close()

    for item in geometry.get('windows', []):
        if item['type'] == 'line':
            msp.add_line(item['start'], item['end'], dxfattribs={'layer': 'FENETRES'})
        elif item['type'] == 'polyline':
            msp.add_lwpolyline([tuple(p) for p in item['points']], dxfattribs={'layer': 'FENETRES'})

    for item in geometry.get('doors', []):
        if item['type'] == 'line':
            msp.add_line(item['start'], item['end'], dxfattribs={'layer': 'PORTES'})

    for room in geometry.get('rooms', []):
        msp.add_text(room['name'], height=200,
                     dxfattribs={'layer': 'PIECES', 'insert': (room['x'], room['y'])})

    path = tempfile.mktemp(suffix='.dxf', prefix='tijan_')
    doc.saveas(path)
    return path


def convert_to_dxf(input_path: str, ville: str = "Dakar") -> str:
    """
    Convert any supported input to DXF.
    Returns path to DXF file, or None.

    DXF → returns input_path as-is (already DXF)
    DWG → ODA (fast) or APS (slow fallback)
    """
    ext = os.path.splitext(input_path)[1].lower()

    if ext == '.dxf':
        return input_path  # already DXF

    if ext == '.dwg':
        # Try LibreDWG first (fastest, open source)
        if DWG2DXF_PATH:
            dxf = dwg_to_dxf_libredwg(input_path)
            if dxf:
                logger.info(f"DWG→DXF via LibreDWG: {dxf}")
                return dxf

        # Try ODA (fast, free)
        if ODA_PATH:
            dxf = dwg_to_dxf_oda(input_path)
            if dxf:
                logger.info(f"DWG→DXF via ODA: {dxf}")
                return dxf

        # Fallback to APS (slow but works)
        logger.info("No local converter, falling back to APS for DWG→DXF")
        dxf = dwg_to_dxf_aps(input_path, ville=ville)
        if dxf:
            logger.info(f"DWG→DXF via APS: {dxf}")
            return dxf

        logger.warning("DWG→DXF conversion failed")
        return None

    logger.warning(f"Unsupported format for DXF conversion: {ext}")
    return None


def dxf_to_dwg(dxf_path: str) -> str:
    """Convert DXF → DWG using ODA (for output). Returns DWG path or None."""
    if not ODA_PATH:
        return None

    input_dir = tempfile.mkdtemp(prefix="oda_in_")
    output_dir = tempfile.mkdtemp(prefix="oda_out_")

    try:
        base = os.path.basename(dxf_path)
        shutil.copy2(dxf_path, os.path.join(input_dir, base.replace(' ', '_')))
        cmd = [ODA_PATH, input_dir, output_dir, "ACAD2018", "DWG", "0", "1"]
        subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        for f in os.listdir(output_dir):
            if f.lower().endswith('.dwg'):
                final = tempfile.mktemp(suffix='.dwg', prefix='tijan_')
                shutil.move(os.path.join(output_dir, f), final)
                return final
        return None
    except Exception as e:
        logger.warning(f"DXF→DWG error: {e}")
        return None
    finally:
        shutil.rmtree(input_dir, ignore_errors=True)
        shutil.rmtree(output_dir, ignore_errors=True)


# Status
def converter_status():
    if DWG2DXF_PATH:
        return {"strategy": "LibreDWG (local, ~1s/file)", "tool": DWG2DXF_PATH}
    if ODA_PATH:
        return {"strategy": "ODA (local, ~2s/file)", "tool": ODA_PATH}
    return {"strategy": "APS (cloud, ~2min/file)", "tool": None}
