#!/usr/bin/env python3
"""
test_dxf_renderer.py — Test the new ezdxf-based BIM renderer

Builds the Sakho R+8 model, generates DXF files + compiled PDF,
and validates output quality.

Usage:
    cd ~/tijan-repo
    python3 tests/test_dxf_renderer.py          # DXF + PDF
    python3 tests/test_dxf_renderer.py --dxf     # DXF only
    python3 tests/test_dxf_renderer.py --pdf     # PDF only

Output:
    tests/output/dxf/           — Individual DXF files
    tests/output/dossier_bim_sakho_dxf.pdf   — Compiled PDF
"""
import os
import sys
import time

# Ensure we can import from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_bim_phase4 import build_sakho, _walls_from_polygon
from room_rules import place_equipment_in_room
from mep_router import route_mep
from generate_plans_dxf import render_bim_dxf, compile_bim_pdf


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--all"

    print("=" * 60)
    print("TIJAN AI — Test DXF Renderer (ezdxf)")
    print("Résidence Papa Oumar Sakho R+8 — Dakar")
    print("=" * 60)

    # Step 1: Build model
    print("\n▶ [1/4] Construction du Building...")
    t0 = time.time()
    building = build_sakho()
    total_rooms = sum(len(l.rooms) for l in building.levels)
    print(f"  ✓ {len(building.levels)} niveaux, {total_rooms} pièces")

    # Step 2: Equipment
    print("\n▶ [2/4] Placement des équipements...")
    for level in building.levels:
        for room in level.rooms:
            room_walls = _walls_from_polygon(room)
            room.equipment = place_equipment_in_room(room, room_walls)
    total_equip = sum(len(r.equipment)
                      for l in building.levels for r in l.rooms)
    print(f"  ✓ {total_equip} équipements placés")

    # Step 3: MEP routing
    print("\n▶ [3/4] Routage MEP...")
    building = route_mep(building)
    total_segs = sum(len(r.network_segments)
                     for l in building.levels for r in l.rooms)
    total_segs += sum(len(l.network_segments) for l in building.levels)
    print(f"  ✓ {total_segs} segments routés")

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(out_dir, exist_ok=True)

    # Step 4a: DXF files
    if mode in ("--dxf", "--all"):
        print("\n▶ [4a] Génération des DXF...")
        dxf_dir = os.path.join(out_dir, "dxf")
        dxf_results = render_bim_dxf(building, dxf_dir)
        print(f"  ✓ {len(dxf_results)} fichiers DXF générés dans {dxf_dir}")
        # Show first 5
        for path, title, lvl_name in dxf_results[:5]:
            size_kb = os.path.getsize(path) / 1024
            print(f"    {os.path.basename(path)}: {size_kb:.0f} KB")
        if len(dxf_results) > 5:
            print(f"    ... et {len(dxf_results) - 5} autres")

    # Step 4b: Compiled PDF
    if mode in ("--pdf", "--all"):
        print("\n▶ [4b] Compilation du PDF...")
        pdf_path = os.path.join(out_dir, "dossier_bim_sakho_dxf.pdf")
        result = compile_bim_pdf(building, pdf_path, lang="fr")
        elapsed = time.time() - t0

        print(f"\n{'=' * 60}")
        print(f"✓ DOSSIER PDF GÉNÉRÉ EN {elapsed:.1f}s")
        print(f"  Pages: {result['pages']}")
        print(f"  Sublots: {len(result['sublots'])}")
        print(f"  Niveaux: {len(result['levels'])}")
        print(f"  Fichier: {result['file_path']}")
        print(f"  Taille: {result['file_size_kb']:.0f} KB")
        print(f"{'=' * 60}")

        # Sanity checks
        assert result["pages"] > 50, f"Expected 50+ pages, got {result['pages']}"
        assert total_equip > 1000, f"Expected 1000+ equip, got {total_equip}"
        print("\n✓ Tous les contrôles passés !")

    total_elapsed = time.time() - t0
    print(f"\n⏱ Temps total: {total_elapsed:.1f}s")


if __name__ == "__main__":
    main()
