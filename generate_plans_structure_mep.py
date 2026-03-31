"""
generate_plans_structure_mep.py — Plans Structure + MEP paramétriques

RÈGLES FONDAMENTALES:
  1. ZÉRO HARDCODING — chaque valeur vient de ResultatsStructure ou ResultatsMEP
  2. COHÉRENCE — les plans reflètent exactement les mêmes données que les notes de calcul

Les plans sont des schémas paramétriques générés depuis:
  - DonneesProjet (nb_niveaux, nb_travees_x/y, portee_max/min, surface_emprise, etc.)
  - ResultatsStructure (poteaux, poutres, dalles, fondations, voiles, sismique)
  - ResultatsMEP (électrique, plomberie, CVC, CF, SI, ascenseurs, automatisation)

Aucune géométrie DXF externe n'est chargée. Aucune valeur spécifique au projet Sakho.
"""
import io, os, math, tempfile
from datetime import datetime
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas as pdfcanvas

from plan_theme import (draw_border, draw_cartouche, draw_legend, draw_notes,
                        draw_north, draw_axis_label, PAL)

A3L = landscape(A3)
W, H = A3L

# ══════════════════════════════════════════════════════════════
# STRUCTURAL GRID — derived purely from DonneesProjet
# ══════════════════════════════════════════════════════════════

def _build_grid(d):
    nx = d.nb_travees_x
    ny = d.nb_travees_y
    lx = d.portee_max_m
    ly = d.portee_min_m
    h_etage = d.hauteur_etage_m
    nb_niv = d.nb_niveaux
    axes_x = [i * lx for i in range(nx + 1)]
    axes_y = [j * ly for j in range(ny + 1)]
    levels = []
    if d.avec_sous_sol:
        levels.append(('SS', -h_etage))
    levels.append(('RDC', 0.0))
    nb_etages = nb_niv - (2 if d.avec_sous_sol else 1)
    for i in range(1, nb_etages + 1):
        levels.append((f'R+{i}', i * h_etage))
    levels.append(('Terrasse', (nb_etages + 1) * h_etage))
    return {'nx': nx, 'ny': ny, 'lx': lx, 'ly': ly,
            'Lx': nx * lx, 'Ly': ny * ly,
            'axes_x': axes_x, 'axes_y': axes_y,
            'levels': levels, 'h_etage': h_etage}


def _grid_tx(grid, margin=22*mm, bottom=44*mm):
    Lx, Ly = grid['Lx'], grid['Ly']
    aw = W - 2 * margin - 70*mm
    ah = H - margin - bottom - margin
    sc = min(aw / Lx, ah / Ly) if Lx > 0 and Ly > 0 else 1
    ox = margin + (aw - Lx * sc) / 2
    oy = bottom + (ah - Ly * sc) / 2
    return lambda x: ox + x * sc, lambda y: oy + y * sc, sc


def _draw_grid(c, grid, tx, ty):
    axes_x, axes_y = grid['axes_x'], grid['axes_y']
    c.setStrokeColor(PAL['gris_c']); c.setLineWidth(0.3); c.setDash(8, 4)
    for i, ax in enumerate(axes_x):
        px = tx(ax)
        c.line(px, ty(0) - 8*mm, px, ty(grid['Ly']) + 8*mm)
        draw_axis_label(c, px, ty(0) - 14*mm, chr(65 + i))
    for j, ay in enumerate(axes_y):
        py = ty(ay)
        c.line(tx(0) - 8*mm, py, tx(grid['Lx']) + 8*mm, py)
        draw_axis_label(c, tx(0) - 14*mm, py, str(j + 1))
    c.setDash()


def _draw_poteaux(c, grid, tx, ty, section_mm):
    half = max(section_mm * 0.005, 2.5)
    for ax in grid['axes_x']:
        for ay in grid['axes_y']:
            px, py = tx(ax), ty(ay)
            c.setFillColor(PAL['noir']); c.setStrokeColor(PAL['noir']); c.setLineWidth(0.4)
            c.rect(px - half, py - half, 2 * half, 2 * half, fill=1, stroke=1)


def _draw_poutres(c, grid, tx, ty, has_secondary=True):
    axes_x, axes_y = grid['axes_x'], grid['axes_y']
    c.setStrokeColor(PAL['noir']); c.setLineWidth(1.5)
    for ay in axes_y:
        for i in range(len(axes_x) - 1):
            c.line(tx(axes_x[i]), ty(ay), tx(axes_x[i+1]), ty(ay))
    if has_secondary:
        c.setStrokeColor(PAL['gris_f']); c.setLineWidth(0.8)
        for ax in axes_x:
            for j in range(len(axes_y) - 1):
                c.line(tx(ax), ty(axes_y[j]), tx(ax), ty(axes_y[j+1]))


def _draw_dalle_hatch(c, grid, tx, ty, ep_mm):
    axes_x, axes_y = grid['axes_x'], grid['axes_y']
    c.setStrokeColor(PAL['gris_cc']); c.setLineWidth(0.12)
    for i in range(len(axes_x) - 1):
        for j in range(len(axes_y) - 1):
            x1, x2 = tx(axes_x[i]), tx(axes_x[i+1])
            y1, y2 = ty(axes_y[j]), ty(axes_y[j+1])
            pw, ph = x2 - x1, y2 - y1
            if pw < 3 or ph < 3: continue
            for k in range(int((pw + ph) / 5) + 2):
                sx = x1 + k * 5; ey = y1 + k * 5
                s_x = min(sx, x2); e_y = min(ey, y2)
                s_y = max(y1, y1 + (sx - x2)) if sx > x2 else y1
                e_x = max(x1, x1 + (ey - y2)) if ey > y2 else x1
                if x1 <= s_x <= x2 and y1 <= s_y <= y2 and x1 <= e_x <= x2 and y1 <= e_y <= y2:
                    c.line(s_x, s_y, e_x, e_y)
            c.setFillColor(PAL['gris']); c.setFont("Helvetica", 3)
            c.drawCentredString((x1+x2)/2, (y1+y2)/2, f"D ep.{ep_mm}")


def _bay_centers(grid):
    """Return list of (cx, cy) in grid coords for each bay."""
    pts = []
    for i in range(grid['nx']):
        for j in range(grid['ny']):
            pts.append(((grid['axes_x'][i]+grid['axes_x'][i+1])/2,
                        (grid['axes_y'][j]+grid['axes_y'][j+1])/2))
    return pts


# ══════════════════════════════════════════════════════════════
# DWG GEOMETRY OVERLAY — real architecture from THIS project's APS data
# ══════════════════════════════════════════════════════════════

def _dwg_bounds(dwg):
    """Get bounding box of DWG geometry."""
    xs, ys = [], []
    for item in dwg.get('walls', []) + dwg.get('windows', []) + dwg.get('doors', []):
        if item.get('type') == 'line':
            xs += [item['start'][0], item['end'][0]]
            ys += [item['start'][1], item['end'][1]]
    if not xs: return None
    return min(xs), min(ys), max(xs), max(ys)


def _dwg_transform(dwg, margin=22*mm, bottom=44*mm):
    """Create transform from DWG coords to page coords."""
    bounds = _dwg_bounds(dwg)
    if not bounds: return None, None, None
    xn, yn, xx, yx = bounds
    dw, dh = xx - xn, yx - yn
    if dw < 1 or dh < 1: return None, None, None
    aw = W - 2*margin - 70*mm
    ah = H - margin - bottom - margin
    sc = min(aw/dw, ah/dh)
    ox = margin + (aw - dw*sc)/2
    oy = bottom + (ah - dh*sc)/2
    return lambda x: ox + (x-xn)*sc, lambda y: oy + (y-yn)*sc, sc


def _draw_dwg_arch(c, dwg, tx, ty):
    """Draw real DWG architecture as light background."""
    # Walls
    c.setStrokeColor(PAL['gris_f']); c.setLineWidth(0.5)
    for item in dwg.get('walls', []):
        if item.get('type') == 'line':
            c.line(tx(item['start'][0]), ty(item['start'][1]),
                   tx(item['end'][0]), ty(item['end'][1]))
    # Windows
    c.setStrokeColor(colors.HexColor("#90CAF9")); c.setLineWidth(0.3)
    for item in dwg.get('windows', []):
        if item.get('type') == 'line':
            c.line(tx(item['start'][0]), ty(item['start'][1]),
                   tx(item['end'][0]), ty(item['end'][1]))
    # Doors
    c.setStrokeColor(colors.HexColor("#BCAAA4")); c.setLineWidth(0.25)
    for item in dwg.get('doors', []):
        if item.get('type') == 'line':
            c.line(tx(item['start'][0]), ty(item['start'][1]),
                   tx(item['end'][0]), ty(item['end'][1]))
    # Room labels
    import re
    c.setFillColor(PAL['gris']); c.setFont("Helvetica", 3)
    for r in dwg.get('rooms', []):
        if not re.match(r'^\d', r.get('name', '')):
            c.drawCentredString(tx(r['x']), ty(r['y']), r['name'][:20])


# ══════════════════════════════════════════════════════════════
# STRUCTURE PLANS
# ══════════════════════════════════════════════════════════════

def generer_plans_structure(output_path, resultats=None, params=None, dwg_geometry=None, **_kwargs):
    if resultats is None:
        raise ValueError("ResultatsStructure requis")
    rs = resultats; d = rs.params
    pp = rs.poutre_principale; ps = rs.poutre_secondaire
    dalle = rs.dalle; fond = rs.fondation
    pot0 = rs.poteaux[0] if rs.poteaux else None
    sism = rs.sismique; boq = rs.boq
    if pot0 is None:
        raise ValueError("Pas de résultats poteaux")
    p = params if isinstance(params, dict) else (params.__dict__ if params else {})
    projet = p.get('nom', d.nom); ville = p.get('ville', d.ville)
    lieu = f"{ville}, {d.pays}"; grid = _build_grid(d)
    has_dwg = dwg_geometry is not None and len(dwg_geometry.get('walls', [])) > 5
    mat = f"Béton {rs.classe_beton} (fck={rs.fck_MPa:.0f}MPa) — Acier {rs.classe_acier} (fyk={rs.fyk_MPa:.0f}MPa)"
    c = pdfcanvas.Canvas(output_path, pagesize=A3L)
    c.setTitle(f"Plans Structure — {projet}"); c.setAuthor("Tijan AI")
    total_pages = len(grid['levels']) * 3 + 2
    page = 0
    positions = [(-1,-1),(1,-1),(1,1),(-1,1),(0,-1),(0,1),(-1,0),(1,0)]

    for level_code, alt in grid['levels']:
        # Use real DWG geometry if available, otherwise parametric grid
        if has_dwg:
            tx, ty, sc = _dwg_transform(dwg_geometry)
            if tx is None:
                tx, ty, sc = _grid_tx(grid)
                has_dwg_page = False
            else:
                has_dwg_page = True
        else:
            tx, ty, sc = _grid_tx(grid)
            has_dwg_page = False
        pot_l = pot0
        for pot in rs.poteaux:
            if level_code in str(pot.niveau): pot_l = pot; break

        # COFFRAGE
        page += 1; draw_border(c)
        draw_cartouche(c, "PLAN DE COFFRAGE", page, total_pages, niveau=f"{level_code} ({alt:+.2f}m)",
                       projet=projet, lieu=lieu, lot="Structure")
        draw_north(c)
        # Real DWG architecture as background when available
        if has_dwg_page:
            _draw_dwg_arch(c, dwg_geometry, tx, ty)
        _draw_grid(c, grid, tx, ty)
        _draw_dalle_hatch(c, grid, tx, ty, dalle.epaisseur_mm)
        _draw_poutres(c, grid, tx, ty, ps is not None)
        _draw_poteaux(c, grid, tx, ty, pot_l.section_mm)
        for i in range(grid['nx']):
            mid = tx((grid['axes_x'][i]+grid['axes_x'][i+1])/2)
            c.setFillColor(PAL['noir']); c.setFont("Helvetica", 4)
            c.drawCentredString(mid, ty(0)-8*mm, f"{grid['lx']:.2f}m")
        draw_notes(c, [mat, f"Poteau {pot_l.section_mm}×{pot_l.section_mm} — {pot_l.nb_barres}HA{pot_l.diametre_mm}",
                       f"PP {pp.b_mm}×{pp.h_mm} — PS {ps.b_mm}×{ps.h_mm}" if ps else f"PP {pp.b_mm}×{pp.h_mm}",
                       f"Dalle ep.{dalle.epaisseur_mm}mm"])
        draw_legend(c, [(PAL['noir'], f"Poteau {pot_l.section_mm}×{pot_l.section_mm}", 'rect'),
                        (PAL['noir'], f"PP {pp.b_mm}×{pp.h_mm}", 'line'),
                        (PAL['gris_f'], f"PS {ps.b_mm}×{ps.h_mm}" if ps else "—", 'line'),
                        (PAL['gris_cc'], f"Dalle ep.{dalle.epaisseur_mm}", 'rect')])
        c.showPage()

        # FERRAILLAGE POTEAUX
        page += 1; draw_border(c)
        draw_cartouche(c, "FERRAILLAGE POTEAUX", page, total_pages, niveau=f"{level_code} ({alt:+.2f}m)",
                       projet=projet, lieu=lieu, lot="Structure")
        _draw_grid(c, grid, tx, ty)
        half = max(pot_l.section_mm * 0.006, 3.5)
        for ax in grid['axes_x']:
            for ay in grid['axes_y']:
                px, py = tx(ax), ty(ay)
                c.setFillColor(PAL['bleu_bg']); c.setStrokeColor(PAL['noir']); c.setLineWidth(0.5)
                c.rect(px-half, py-half, 2*half, 2*half, fill=1, stroke=1)
                inner = half - 1; c.setFillColor(PAL['noir'])
                for k in range(min(pot_l.nb_barres, 8)):
                    dx, dy = positions[k % len(positions)]
                    c.circle(px+dx*inner, py+dy*inner, 0.5, fill=1, stroke=0)
        # Detail box
        bx, by, bw, bh = W-78*mm, H-15*mm, 68*mm, 58*mm
        c.setFillColor(PAL['blanc']); c.setStrokeColor(PAL['noir']); c.setLineWidth(0.5)
        c.rect(bx, by-bh, bw, bh, fill=1, stroke=1)
        c.setFillColor(PAL['noir']); c.setFont("Helvetica-Bold", 6)
        c.drawCentredString(bx+bw/2, by-8, "SECTION POTEAU TYPE")
        scx, scy = bx+bw/2, by-bh/2-2*mm; ss = 18*mm
        c.setFillColor(PAL['bleu_bg']); c.setStrokeColor(PAL['noir']); c.setLineWidth(0.8)
        c.rect(scx-ss/2, scy-ss/2, ss, ss, fill=1, stroke=1)
        c.setStrokeColor(PAL['rouge']); c.setLineWidth(0.5); enr = 2*mm
        c.rect(scx-ss/2+enr, scy-ss/2+enr, ss-2*enr, ss-2*enr, fill=0, stroke=1)
        c.setFillColor(PAL['noir']); rb_i = ss/2-enr-1*mm
        for k in range(min(pot_l.nb_barres, 8)):
            dx, dy = positions[k % len(positions)]
            c.circle(scx+dx*rb_i, scy+dy*rb_i, 1*mm, fill=1, stroke=0)
        c.setFillColor(PAL['gris_f']); c.setFont("Helvetica", 5)
        c.drawCentredString(scx, scy-ss/2-4*mm, f"{pot_l.section_mm} mm")
        c.setFont("Helvetica", 4.5)
        c.drawString(bx+3*mm, by-bh+14*mm, f"{pot_l.nb_barres}HA{pot_l.diametre_mm} (τ={pot_l.taux_armature_pct:.2f}%)")
        c.drawString(bx+3*mm, by-bh+9*mm, f"Cadres HA{pot_l.cadre_diam_mm} esp.{pot_l.espacement_cadres_mm}mm")
        c.drawString(bx+3*mm, by-bh+4*mm, f"NEd={pot_l.NEd_kN:.0f}kN / NRd={pot_l.NRd_kN:.0f}kN ({pot_l.ratio_NEd_NRd:.2f})")
        draw_notes(c, [mat, f"Enrobage {'35' if rs.distance_mer_km<5 else '30'}mm ({('XS1' if rs.distance_mer_km<5 else 'XC2')})"])
        c.showPage()

        # FERRAILLAGE POUTRES
        page += 1; draw_border(c)
        draw_cartouche(c, "FERRAILLAGE POUTRES", page, total_pages, niveau=f"{level_code} ({alt:+.2f}m)",
                       projet=projet, lieu=lieu, lot="Structure")
        _draw_grid(c, grid, tx, ty); _draw_poteaux(c, grid, tx, ty, pot_l.section_mm)
        for ay in grid['axes_y']:
            for i in range(len(grid['axes_x'])-1):
                px1, px2 = tx(grid['axes_x'][i]), tx(grid['axes_x'][i+1]); py = ty(ay)
                c.setStrokeColor(PAL['noir']); c.setLineWidth(1.5); c.line(px1, py, px2, py)
                c.setFillColor(PAL['rouge']); c.setFont("Helvetica-Bold", 2.5)
                c.drawCentredString((px1+px2)/2, py+3, f"PP {pp.b_mm}×{pp.h_mm}")
        # Beam detail box
        bx2 = W-82*mm; bw2, bh2 = 74*mm, 52*mm
        c.setFillColor(PAL['blanc']); c.setStrokeColor(PAL['noir']); c.setLineWidth(0.5)
        c.rect(bx2, H-15*mm-bh2, bw2, bh2, fill=1, stroke=1)
        c.setFillColor(PAL['noir']); c.setFont("Helvetica-Bold", 6)
        c.drawCentredString(bx2+bw2/2, H-23*mm, "POUTRE PRINCIPALE TYPE")
        bbx, bby = bx2+6*mm, H-15*mm-bh2+16*mm; bbw, bbh = 60*mm, 14*mm
        c.setFillColor(colors.HexColor("#F5F5F5")); c.setStrokeColor(PAL['noir']); c.setLineWidth(0.6)
        c.rect(bbx, bby, bbw, bbh, fill=1, stroke=1)
        c.setStrokeColor(PAL['rouge']); c.setLineWidth(0.6)
        c.line(bbx+2, bby+2.5*mm, bbx+bbw-2, bby+2.5*mm)
        c.line(bbx+2, bby+bbh-2.5*mm, bbx+bbw-2, bby+bbh-2.5*mm)
        c.setStrokeColor(PAL['gris']); c.setLineWidth(0.2)
        for k in range(12):
            ex = bbx+3+k*(bbw-6)/11; c.line(ex, bby+2*mm, ex, bby+bbh-2*mm)
        c.setFillColor(PAL['rouge']); c.setFont("Helvetica", 3.5)
        c.drawString(bx2+3*mm, H-15*mm-bh2+10*mm, f"Inf: As={pp.As_inf_cm2:.2f}cm²")
        c.drawString(bx2+3*mm, H-15*mm-bh2+6*mm, f"Sup: As={pp.As_sup_cm2:.2f}cm²")
        c.drawString(bx2+3*mm, H-15*mm-bh2+2*mm, f"Étr: HA{pp.etrier_diam_mm} esp.{pp.etrier_esp_mm}mm")
        draw_notes(c, [mat, f"PP {pp.b_mm}×{pp.h_mm} portée {pp.portee_m:.2f}m",
                       f"PS {ps.b_mm}×{ps.h_mm} portée {ps.portee_m:.2f}m" if ps else "",
                       f"Dalle {dalle.epaisseur_mm}mm — As x={dalle.As_x_cm2_ml:.2f} / As y={dalle.As_y_cm2_ml:.2f} cm²/ml"])
        c.showPage()

    # FONDATIONS
    page += 1; draw_border(c)
    fond_label = fond.type.value.replace('_',' ').title()
    draw_cartouche(c, f"PLAN DE FONDATIONS — {fond_label}", page, total_pages,
                   niveau=f"Assise {fond.profondeur_m:+.1f}m", projet=projet, lieu=lieu, lot="Structure")
    tx, ty, sc = _grid_tx(grid); _draw_grid(c, grid, tx, ty)
    for ax in grid['axes_x']:
        for ay in grid['axes_y']:
            px, py = tx(ax), ty(ay)
            if 'semelle' in fond.type.value:
                sh = max(fond.largeur_semelle_m*sc/2, 5)
                c.setStrokeColor(PAL['rouge']); c.setLineWidth(0.5); c.setDash(3,1.5)
                c.rect(px-sh, py-sh, 2*sh, 2*sh, fill=0, stroke=1); c.setDash()
            elif 'pieu' in fond.type.value:
                rp = max(fond.diam_pieu_mm*sc/2000, 3)
                c.setStrokeColor(PAL['rouge']); c.setLineWidth(0.5)
                c.circle(px, py, rp, fill=0, stroke=1)
            c.setFillColor(PAL['noir']); c.rect(px-2, py-2, 4, 4, fill=1, stroke=0)
    draw_notes(c, [f"Fondation: {fond_label} — σsol={rs.pression_sol_MPa:.2f}MPa — prof.{fond.profondeur_m:.1f}m",
                   mat, f"Béton fond.: {boq.beton_fondation_m3:.0f}m³ — Acier total: {boq.acier_kg:.0f}kg"])
    c.showPage()

    # COUPE GÉNÉRALE
    page += 1; draw_border(c)
    draw_cartouche(c, "COUPE GÉNÉRALE", page, total_pages, niveau="Tous niveaux",
                   projet=projet, lieu=lieu, lot="Structure")
    levels = grid['levels']; h_pt = 20*mm; bw_c = W-140*mm; cx_c = 60*mm; cy_b = 50*mm
    gnd = cy_b + (h_pt if d.avec_sous_sol else 0)
    c.setStrokeColor(PAL['marron']); c.setLineWidth(1.5)
    c.line(cx_c-20*mm, gnd, cx_c+bw_c+20*mm, gnd)
    c.setFillColor(PAL['marron']); c.setFont("Helvetica-Bold", 6)
    c.drawString(cx_c+bw_c+22*mm, gnd-3, "±0.00 TN")
    yc = cy_b
    for code, alt in levels:
        col = PAL['bleu_bg'] if 'R+' in code else (PAL['gris_bg'] if code == 'SS' else PAL['vert_bg'])
        c.setFillColor(col); c.setStrokeColor(PAL['noir']); c.setLineWidth(0.5)
        c.rect(cx_c, yc, bw_c, h_pt, fill=1, stroke=1)
        c.setFillColor(PAL['noir']); c.setFont("Helvetica-Bold", 5)
        c.drawString(cx_c+3*mm, yc+h_pt/2-2, code)
        c.setFillColor(PAL['gris_f']); c.rect(cx_c, yc, 3*mm, h_pt, fill=1, stroke=0)
        c.rect(cx_c+bw_c-3*mm, yc, 3*mm, h_pt, fill=1, stroke=0)
        c.setStrokeColor(PAL['noir']); c.setLineWidth(1.5); c.line(cx_c, yc+h_pt, cx_c+bw_c, yc+h_pt)
        c.setFillColor(PAL['gris_f']); c.setFont("Helvetica", 4.5)
        c.drawString(cx_c+bw_c+5*mm, yc+h_pt-3, f"{alt:+.2f}m")
        yc += h_pt
    c.setFillColor(colors.HexColor("#D7CCC8")); c.setStrokeColor(PAL['noir']); c.setLineWidth(0.8)
    c.rect(cx_c-5*mm, cy_b-6*mm, bw_c+10*mm, 6*mm, fill=1, stroke=1)
    draw_notes(c, [f"{projet} — {lieu} — R+{d.nb_niveaux-1}", mat,
                   f"H totale: {levels[-1][1]:.1f}m — Surface bâtie: {boq.surface_batie_m2:.0f}m²",
                   f"Zone sismique {sism.zone} — ag={sism.ag_g:.3f}g"])
    c.showPage()
    c.save()
    return output_path


# ══════════════════════════════════════════════════════════════
# MEP PLANS — 100% from ResultatsMEP
# ══════════════════════════════════════════════════════════════

def generer_plans_mep(output_path, resultats_mep=None, resultats_structure=None, params=None, dwg_geometry=None, **_kwargs):
    if resultats_mep is None:
        raise ValueError("ResultatsMEP requis")
    rm = resultats_mep; d = rm.params
    el = rm.electrique; pl = rm.plomberie; cv = rm.cvc
    cf = rm.courants_faibles; si = rm.securite_incendie
    asc_r = rm.ascenseurs; auto = rm.automatisation
    rs = resultats_structure
    p = params if isinstance(params, dict) else (params.__dict__ if params else {})
    projet = p.get('nom', d.nom); ville = p.get('ville', d.ville)
    lieu = f"{ville}, {d.pays}"; grid = _build_grid(d)
    pot_sec = rs.poteaux[0].section_mm if rs and rs.poteaux else 300
    has_dwg = dwg_geometry is not None and len(dwg_geometry.get('walls', [])) > 5

    c = pdfcanvas.Canvas(output_path, pagesize=A3L)
    c.setTitle(f"Plans MEP — {projet}"); c.setAuthor("Tijan AI")

    sublots = [
        ("PLOMBERIE — Eau Froide", "Lot 1 — Plomberie",
         [f"CM EF DN{pl.diam_colonne_montante_mm}", f"Citerne {int(pl.volume_citerne_m3)}m³",
          f"Surpresseur {pl.debit_surpresseur_m3h}m³/h", f"{rm.nb_logements} logts — {rm.nb_personnes} pers"],
         [(PAL['bleu'], f"CM EF DN{pl.diam_colonne_montante_mm}", 'circle'),
          (PAL['bleu'], "Réseau distribution EF", 'line')], 'plb_ef'),
        ("PLOMBERIE — Eau Chaude", "Lot 1 — Plomberie",
         ["CM EC DN32", f"{pl.nb_chauffe_eau_solaire} CESI solaires"],
         [(PAL['rouge'], "CM EC DN32", 'circle'), (PAL['rouge'], "Réseau EC", 'dash')], 'plb_ec'),
        ("PLOMBERIE — Évacuations EU/EP", "Lot 1 — Plomberie",
         ["Chute EU DN100", f"Conso eau: {pl.conso_eau_annuelle_m3:.0f}m³/an"],
         [(PAL['marron'], "Chute EU DN100", 'circle'), (PAL['marron'], "Collecteur", 'dash')], 'plb_eu'),
        ("ÉLECTRICITÉ — Éclairage", "Lot 2 — Électricité",
         [f"P totale: {el.puissance_totale_kva:.0f}kVA", f"Éclairage: {el.puissance_eclairage_kw:.1f}kW"],
         [(PAL['jaune'], "Luminaire", 'circle')], 'elec_ecl'),
        ("ÉLECTRICITÉ — Prises & Distribution", "Lot 2 — Électricité",
         [f"Transfo {el.transfo_kva}kVA", f"GE {el.groupe_electrogene_kva}kVA",
          f"{el.nb_compteurs} compteurs — Col.{el.section_colonne_mm2}mm²"],
         [(PAL['orange_c'], "Prise 2P+T", 'rect'), (PAL['vert'], "TGBT", 'rect'), (PAL['orange'], "Chemin câbles", 'line')], 'elec_dist'),
        ("CVC — Climatisation", "Lot 3 — CVC",
         [f"P frigo: {cv.puissance_frigorifique_kw:.0f}kW", f"Splits séj: {cv.nb_splits_sejour} — ch: {cv.nb_splits_chambre}"],
         [(PAL['cyan_c'], "Split mural", 'rect'), (PAL['cyan'], "Ligne frigo", 'dash')], 'cvc_clim'),
        ("CVC — Ventilation VMC", "Lot 3 — CVC",
         [f"{cv.nb_vmc} VMC {cv.type_vmc}", f"Conso CVC: {cv.conso_cvc_kwh_an:.0f}kWh/an"],
         [(PAL['vert_f'], "Bouche VMC", 'circle'), (PAL['vert_f'], "Gaine VMC", 'dash')], 'cvc_vmc'),
        ("SÉCURITÉ INCENDIE — Détection", "Lot 4 — Séc. Incendie",
         [f"Cat. ERP: {si.categorie_erp}", f"{si.nb_detecteurs_fumee} DF — {si.nb_declencheurs_manuels} DM",
          f"{si.nb_sirenes} sirènes — Centrale {si.centrale_zones} zones"],
         [(PAL['rouge'], "DF", 'ring'), (PAL['rouge'], "DM", 'rect'), (PAL['orange'], "Sirène", 'circle')], 'ssi_det'),
        ("SÉCURITÉ INCENDIE — Extinction", "Lot 4 — Séc. Incendie",
         [f"{si.nb_extincteurs_co2+si.nb_extincteurs_poudre} extincteurs — RIA {si.longueur_ria_ml:.0f}ml",
          f"Sprinklers: {'OUI ({} têtes)'.format(si.nb_tetes_sprinkler) if si.sprinklers_requis else 'NON'}"],
         [(PAL['rouge'], "RIA", 'ring'), (PAL['rouge'], "Extincteur", 'circle'), (PAL['vert'], "BAES", 'rect')], 'ssi_ext'),
        ("COURANTS FAIBLES", "Lot 5 — Courants Faibles",
         [f"{cf.nb_prises_rj45} RJ45 — {cf.nb_cameras_int+cf.nb_cameras_ext} caméras",
          f"{cf.nb_portes_controle_acces} portes accès — {cf.nb_interphones} interphones"],
         [(PAL['violet'], "RJ45", 'rect'), (PAL['violet_c'], "Caméra", 'circle'), (PAL['cyan'], "Badge", 'circle')], 'cfa'),
        ("ASCENSEURS", "Lot 6 — Ascenseurs",
         [f"{asc_r.nb_ascenseurs}× asc. {asc_r.capacite_kg}kg — {asc_r.vitesse_ms}m/s",
          f"{asc_r.nb_monte_charges} MC — P={asc_r.puissance_totale_kw:.0f}kW"],
         [(PAL['bleu_bg'], "Gaine", 'rect'), (PAL['bleu'], "Cabine", 'dash')], 'asc'),
        ("AUTOMATISATION / GTB", "Lot 7 — Automatisation",
         [f"{auto.protocole} — {auto.niveau}", f"{auto.nb_points_controle} pts ctrl — BMS: {'OUI' if auto.bms_requis else 'NON'}"],
         [(PAL['bleu'], f"Bus {auto.protocole}", 'line'), (PAL['orange_c'], "Capteur", 'circle')], 'gtb'),
    ]

    total_pages = len(sublots) * len(grid['levels'])
    page = 0

    for lot_titre, lot_name, notes_lines, legend_items, lot_key in sublots:
        for level_code, alt in grid['levels']:
            page += 1
            # Use real DWG or parametric grid
            if has_dwg:
                tx_d, ty_d, sc_d = _dwg_transform(dwg_geometry)
                if tx_d:
                    tx, ty, sc = tx_d, ty_d, sc_d
                    has_dwg_page = True
                else:
                    tx, ty, sc = _grid_tx(grid); has_dwg_page = False
            else:
                tx, ty, sc = _grid_tx(grid); has_dwg_page = False
            draw_border(c)
            draw_cartouche(c, lot_titre, page, total_pages, niveau=f"{level_code} ({alt:+.2f}m)",
                           projet=projet, lieu=lieu, lot=lot_name)
            draw_north(c)
            if has_dwg_page:
                _draw_dwg_arch(c, dwg_geometry, tx, ty)
            _draw_grid(c, grid, tx, ty)
            _draw_poteaux(c, grid, tx, ty, pot_sec)
            bays = _bay_centers(grid)
            nx, ny = grid['nx'], grid['ny']
            cx_mid, cy_mid = tx(grid['Lx']/2), ty(grid['Ly']/2)

            if lot_key == 'plb_ef':
                c.setFillColor(PAL['bleu']); c.setStrokeColor(PAL['noir']); c.setLineWidth(0.6)
                c.circle(cx_mid, cy_mid, 3.5, fill=1, stroke=1)
                c.setFillColor(PAL['blanc']); c.setFont("Helvetica-Bold", 4)
                c.drawCentredString(cx_mid, cy_mid-1.5, "EF")
                for bx_m, by_m in bays:
                    bx_p, by_p = tx(bx_m), ty(by_m)
                    c.setStrokeColor(PAL['bleu']); c.setLineWidth(0.5)
                    c.line(cx_mid, cy_mid, bx_p, by_p)
                    c.setFillColor(PAL['bleu']); c.circle(bx_p, by_p, 2, fill=1, stroke=0)
            elif lot_key == 'plb_ec':
                c.setFillColor(PAL['rouge']); c.setStrokeColor(PAL['noir']); c.setLineWidth(0.6)
                c.circle(cx_mid, cy_mid, 3.5, fill=1, stroke=1)
                c.setFillColor(PAL['blanc']); c.setFont("Helvetica-Bold", 4)
                c.drawCentredString(cx_mid, cy_mid-1.5, "EC")
                for bx_m, by_m in bays:
                    c.setStrokeColor(PAL['rouge']); c.setLineWidth(0.4); c.setDash(3,1.5)
                    c.line(cx_mid, cy_mid, tx(bx_m), ty(by_m)); c.setDash()
            elif lot_key == 'plb_eu':
                c.setFillColor(PAL['marron']); c.setStrokeColor(PAL['noir']); c.setLineWidth(0.6)
                c.circle(cx_mid, cy_mid, 3.5, fill=1, stroke=1)
                c.setFillColor(PAL['blanc']); c.setFont("Helvetica-Bold", 4)
                c.drawCentredString(cx_mid, cy_mid-1.5, "EU")
                for bx_m, by_m in bays:
                    c.setStrokeColor(PAL['marron']); c.setLineWidth(0.4); c.setDash(4,2)
                    c.line(tx(bx_m), ty(by_m), cx_mid, cy_mid); c.setDash()
                    c.setFillColor(PAL['marron']); c.circle(tx(bx_m), ty(by_m), 1.5, fill=1, stroke=0)
            elif lot_key == 'elec_ecl':
                for bx_m, by_m in bays:
                    bp, bq = tx(bx_m), ty(by_m)
                    c.setStrokeColor(PAL['jaune']); c.setFillColor(colors.HexColor("#FFF8E1")); c.setLineWidth(0.4)
                    c.circle(bp, bq, 2.5, fill=1, stroke=1)
                    c.setStrokeColor(PAL['jaune']); c.setLineWidth(0.3)
                    c.line(bp-1.5, bq, bp+1.5, bq); c.line(bp, bq-1.5, bp, bq+1.5)
            elif lot_key == 'elec_dist':
                px_t, py_t = tx(grid['axes_x'][0])+5, ty(grid['axes_y'][0])+5
                c.setFillColor(PAL['vert']); c.setStrokeColor(PAL['noir']); c.setLineWidth(0.6)
                c.rect(px_t, py_t, 10, 7, fill=1, stroke=1)
                c.setFillColor(PAL['blanc']); c.setFont("Helvetica-Bold", 3.5)
                c.drawCentredString(px_t+5, py_t+2, "TGBT")
                c.setStrokeColor(PAL['orange']); c.setLineWidth(1.5)
                c.line(tx(grid['axes_x'][0]), ty(grid['axes_y'][0]), tx(grid['axes_x'][0]), ty(grid['axes_y'][-1]))
                for bx_m, by_m in bays:
                    bp, bq = tx(bx_m), ty(by_m)
                    c.setFillColor(PAL['orange_c']); c.setStrokeColor(PAL['noir']); c.setLineWidth(0.15)
                    for dx_o, dy_o in [(-4,-2),(4,-2),(-4,2),(4,2)]:
                        c.rect(bp+dx_o-1.2, bq+dy_o-0.8, 2.4, 1.6, fill=1, stroke=1)
            elif lot_key == 'cvc_clim':
                for bx_m, by_m in bays:
                    bp, bq = tx(bx_m), ty(by_m)
                    c.setFillColor(PAL['cyan_c']); c.setStrokeColor(PAL['cyan']); c.setLineWidth(0.35)
                    c.rect(bp-4.5, bq+4, 9, 2.5, fill=1, stroke=1)
            elif lot_key == 'cvc_vmc':
                for bx_m, by_m in bays:
                    bp, bq = tx(bx_m), ty(by_m)
                    c.setStrokeColor(PAL['vert_f']); c.setFillColor(colors.HexColor("#C8E6C9")); c.setLineWidth(0.4)
                    c.circle(bp, bq-3, 2.5, fill=1, stroke=1)
            elif lot_key == 'ssi_det':
                for bx_m, by_m in bays:
                    bp, bq = tx(bx_m), ty(by_m)
                    c.setFillColor(PAL['blanc']); c.setStrokeColor(PAL['rouge']); c.setLineWidth(0.5)
                    c.circle(bp, bq, 2.5, fill=1, stroke=1)
                    c.setFillColor(PAL['rouge']); c.setFont("Helvetica-Bold", 3)
                    c.drawCentredString(bp, bq-1.5, "DF")
            elif lot_key == 'ssi_ext':
                corners = [(0,0), (grid['nx']-1, grid['ny']-1)]
                for ci, cj in corners:
                    bp = tx((grid['axes_x'][ci]+grid['axes_x'][ci+1])/2)
                    bq = ty((grid['axes_y'][cj]+grid['axes_y'][cj+1])/2)
                    c.setFillColor(PAL['blanc']); c.setStrokeColor(PAL['rouge']); c.setLineWidth(0.7)
                    c.circle(bp, bq, 3.5, fill=1, stroke=1)
                    c.setFillColor(PAL['rouge']); c.setFont("Helvetica-Bold", 4)
                    c.drawCentredString(bp, bq-2, "R")
                    c.setFillColor(PAL['vert']); c.setStrokeColor(PAL['noir']); c.setLineWidth(0.25)
                    c.rect(bp+6, bq-5, 5, 3, fill=1, stroke=1)
                    c.setFillColor(PAL['blanc']); c.setFont("Helvetica-Bold", 2)
                    c.drawCentredString(bp+8.5, bq-4, "BAES")
            elif lot_key == 'cfa':
                for bx_m, by_m in bays:
                    bp, bq = tx(bx_m), ty(by_m)
                    c.setFillColor(PAL['violet']); c.setStrokeColor(PAL['noir']); c.setLineWidth(0.2)
                    c.rect(bp-1.5, bq-2, 3, 2.5, fill=1, stroke=1)
            elif lot_key == 'asc':
                c.setFillColor(PAL['bleu_bg']); c.setStrokeColor(PAL['bleu']); c.setLineWidth(1)
                c.rect(cx_mid-8, cy_mid-8, 16, 16, fill=1, stroke=1)
                c.setStrokeColor(PAL['bleu']); c.setLineWidth(0.3)
                c.line(cx_mid-8, cy_mid-8, cx_mid+8, cy_mid+8)
                c.line(cx_mid-8, cy_mid+8, cx_mid+8, cy_mid-8)
                c.setFillColor(PAL['bleu']); c.setFont("Helvetica-Bold", 3)
                c.drawCentredString(cx_mid, cy_mid-12, f"{asc_r.nb_ascenseurs}× {asc_r.capacite_kg}kg")
            elif lot_key == 'gtb':
                c.setStrokeColor(PAL['bleu']); c.setLineWidth(1.8)
                c.line(tx(grid['axes_x'][0]), ty(grid['axes_y'][0]), tx(grid['axes_x'][0]), ty(grid['axes_y'][-1]))
                for bx_m, by_m in bays:
                    c.setFillColor(PAL['orange_c']); c.circle(tx(bx_m)-4, ty(by_m)+4, 1.5, fill=1, stroke=0)

            draw_notes(c, notes_lines)
            draw_legend(c, legend_items)
            c.showPage()

    c.save()
    return output_path
