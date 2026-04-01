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
    # Check app-local bin (Render installs here)
    here = os.path.dirname(os.path.abspath(__file__))
    for p in [os.path.join(here, 'bin', 'dwg2dxf'),
              '/opt/render/project/src/bin/dwg2dxf',
              '/usr/local/bin/dwg2dxf', '/usr/bin/dwg2dxf']:
        if os.path.isfile(p) and os.access(p, os.X_OK):
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
    Convert DWG → DXF via APS Model Derivative.
    Uploads DWG, requests DXF output format, downloads the real DXF.
    ~2 min per file. Returns path to downloaded DXF, or None.
    """
    try:
        from aps_parser_v2 import (get_token, ensure_bucket, upload_file,
                                    wait_for_translation, auth_headers, APS_MD_URL)
        import requests

        token = get_token()
        ensure_bucket(token)

        # Upload
        timestamp = int(time.time())
        filename = os.path.basename(dwg_path).replace(" ", "_")
        object_key = f"tijan_{timestamp}_{filename}"
        urn = upload_file(dwg_path, object_key, token)
        logger.info(f"APS DXF conversion: uploaded {filename}, urn={urn[:20]}...")

        # Request DXF translation (not SVF2)
        token = get_token()
        r = requests.post(
            f"{APS_MD_URL}/job",
            headers={**auth_headers(token), "Content-Type": "application/json"},
            json={
                "input": {"urn": urn},
                "output": {"formats": [{"type": "dxf"}]},
            },
            timeout=30,
        )
        r.raise_for_status()
        logger.info(f"APS DXF translation started")

        # Wait for translation
        token = get_token()
        manifest = wait_for_translation(urn, token, timeout_s=300)

        # Find the DXF derivative in the manifest
        token = get_token()
        dxf_url = None
        for deriv in manifest.get("derivatives", []):
            for child in deriv.get("children", []):
                if child.get("type") == "resource" and child.get("urn", "").endswith(".dxf"):
                    dxf_url = child["urn"]
                    break
                # Also check in nested children
                for grandchild in child.get("children", []):
                    if grandchild.get("type") == "resource" and grandchild.get("urn", "").endswith(".dxf"):
                        dxf_url = grandchild["urn"]
                        break

        if not dxf_url:
            logger.warning("APS produced no DXF derivative")
            return None

        # Download the DXF
        import urllib.parse
        encoded_derivative = urllib.parse.quote(dxf_url, safe='')
        dl_url = f"{APS_MD_URL}/{urn}/manifest/{encoded_derivative}"
        r = requests.get(dl_url, headers=auth_headers(token), timeout=60)
        if r.status_code != 200:
            logger.warning(f"DXF download failed: {r.status_code}")
            return None

        output = tempfile.mktemp(suffix='.dxf', prefix='tijan_aps_')
        with open(output, 'wb') as f:
            f.write(r.content)

        if os.path.getsize(output) > 100:
            logger.info(f"APS DXF downloaded: {os.path.getsize(output)/1024:.0f}KB")
            return output

        os.unlink(output)
        return None

    except Exception as e:
        logger.warning(f"APS DXF conversion error: {e}")
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


def pdf_to_geometry(pdf_path: str) -> dict:
    """
    Extract vector geometry from a PDF (plans exported from AutoCAD/Revit).
    Uses pymupdf get_drawings() to extract lines, curves with real XY coords.
    Returns geometry dict compatible with plan generators, or None.
    """
    try:
        import fitz
    except ImportError:
        logger.warning("pymupdf not installed — cannot extract PDF geometry")
        return None

    try:
        doc = fitz.open(pdf_path)
        if len(doc) == 0:
            return None

        geometry = {'walls': [], 'windows': [], 'doors': [], 'rooms': []}

        # Process each page (typically 1 page per level)
        for page_idx in range(min(len(doc), 5)):  # max 5 pages
            page = doc[page_idx]
            drawings = page.get_drawings()

            for drawing in drawings:
                color = drawing.get("color", (0, 0, 0))
                width = drawing.get("width", 0)
                items = drawing.get("items", [])

                for item in items:
                    if item[0] == "l":  # line
                        p1, p2 = item[1], item[2]
                        # Scale: PDF coords are in points (72 dpi)
                        # Convert to mm (typical CAD units)
                        scale = 25.4 / 72  # points to mm... but PDF from CAD
                        # may already be in real-world coords
                        line = {
                            'type': 'line',
                            'start': [round(p1.x, 1), round(p1.y, 1)],
                            'end': [round(p2.x, 1), round(p2.y, 1)]
                        }
                        # Thick lines = walls, thin = other
                        if width >= 0.5:
                            geometry['walls'].append(line)
                        elif width >= 0.2:
                            geometry['windows'].append(line)

            # Extract text annotations (room labels)
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text and 3 <= len(text) <= 30:
                            bbox = span.get("bbox", (0, 0, 0, 0))
                            geometry['rooms'].append({
                                'name': text,
                                'x': round((bbox[0] + bbox[2]) / 2, 1),
                                'y': round((bbox[1] + bbox[3]) / 2, 1)
                            })

        doc.close()

        wall_count = len(geometry['walls'])
        logger.info(f"PDF geometry: {wall_count} walls, {len(geometry['rooms'])} rooms")

        return geometry if wall_count > 10 else None

    except Exception as e:
        logger.warning(f"PDF geometry extraction error: {e}")
        return None


def convert_to_dxf(input_path: str, ville: str = "Dakar") -> str:
    """
    Convert any supported input to DXF.
    Returns path to DXF file, or None.

    DXF → returns input_path as-is (already DXF)
    DWG → LibreDWG/ODA (fast) or APS DXF output (slow)
    PDF → extract vector geometry → write DXF
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

    if ext == '.pdf':
        # PDF vectoriel → extract geometry → write DXF
        geom = pdf_to_geometry(input_path)
        if geom:
            dxf = _write_geometry_to_dxf(geom)
            if dxf:
                logger.info(f"PDF→DXF: {dxf}")
                return dxf
        logger.warning("PDF→DXF: no vector geometry found")
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
