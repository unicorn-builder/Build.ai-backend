"""
generate_plans_v4.py — Dossier BA Tijan AI — v4.3 rewrite
4 planches structure niveau BET (Innov' Structures / SERTEM quality)

Layout validé :
  1. Plan de coffrage (A3 paysage) — grille 2D centrée, poteaux, poutres, dalles
  2. Ferraillage poutre type (A4 portrait) — format Ngom : élévation + coupe A-A + tableau
  3. Ferraillage poteau type (A4 portrait) — coupe + élévation schématique + tableau niveaux
  4. Fondations + coupe générale (A3 paysage) — plan gauche, coupe droite

Charte : fond blanc, traits noirs, texte #111/#555, accents vert #43A956
"""

import math
from datetime import datetime
from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdfcanvas

# ── Colors ──
NOIR = colors.HexColor("#111111")
GRIS2 = colors.HexColor("#555555")
GRIS3 = colors.HexColor("#888888")
GRIS4 = colors.HexColor("#CCCCCC")
GRIS5 = colors.HexColor("#E8E8E8")
BLANC = colors.white
VERT = colors.HexColor("#43A956")
VERT_P = colors.HexColor("#E8F5E9")
ROUGE = colors.HexColor("#C62828")      # Lit inférieur — rouge foncé (pas criard)
ROUGE_CLAIR = colors.HexColor("#E57373") # Ancrage / crochets
VERT_FERR = colors.HexColor("#2E7D32")  # Lit supérieur — vert foncé
VIOLET_FERR = colors.HexColor("#7B1FA2") # 2e lit / renforts
BLEU_B = colors.HexColor("#D6E4F0")

A3L = landscape(A3)
A4P = A4


# ════════════════════════════════════════
# CARTOUCHE
# ════════════════════════════════════════
def cartouche(c, w, h, p, titre, pg, total, ech="1/100"):
    cw, ch = 180*mm, 28*mm
    cx = w - cw - 8*mm
    cy = 6*mm
    c.setFillColor(BLANC); c.setStrokeColor(NOIR); c.setLineWidth(0.7)
    c.rect(cx, cy, cw, ch, fill=1, stroke=1)
    c1, c2 = 38*mm, 108*mm
    c.setLineWidth(0.3)
    c.line(cx+c1, cy, cx+c1, cy+ch)
    c.line(cx+c2, cy, cx+c2, cy+ch)
    c.line(cx+c1, cy+ch/2, cx+cw, cy+ch/2)
    c.setFillColor(VERT); c.setFont("Helvetica-Bold", 10)
    c.drawString(cx+3*mm, cy+ch-9*mm, "TIJAN AI")
    c.setFillColor(GRIS2); c.setFont("Helvetica", 5.5)
    c.drawString(cx+3*mm, cy+ch-14*mm, "Engineering Intelligence")
    c.drawString(cx+3*mm, cy+5*mm, f"Date: {datetime.now().strftime('%d/%m/%Y')}")
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 8)
    c.drawString(cx+c1+3*mm, cy+ch-9*mm, p.get("nom","Projet")[:30])
    c.setFillColor(VERT); c.setFont("Helvetica-Bold", 7)
    c.drawString(cx+c1+3*mm, cy+ch/2-8*mm, titre)
    c.setFillColor(GRIS2); c.setFont("Helvetica", 6)
    c.drawString(cx+c2+3*mm, cy+ch-9*mm, f"Éch: {ech}")
    c.drawString(cx+c2+3*mm, cy+ch-14*mm, p.get("ville","Dakar"))
    c.drawString(cx+c2+3*mm, cy+5*mm, f"Pl. {pg}/{total}")


def border(c, w, h):
    m = 8*mm
    c.setStrokeColor(NOIR); c.setLineWidth(0.5)
    c.rect(m, m, w-2*m, h-2*m)


def axis_label(c, x, y, label):
    r = 4.5*mm
    c.setStrokeColor(NOIR); c.setLineWidth(0.4)
    c.setFillColor(BLANC)
    c.circle(x, y, r, fill=1, stroke=1)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 7)
    tw = c.stringWidth(str(label), "Helvetica-Bold", 7)
    c.drawString(x - tw/2, y - 2.5, str(label))


# ════════════════════════════════════════
# SECTION BA — target_h controls page size
# ════════════════════════════════════════
def section_ba(c, cx, cy, bw, bh, nb, dia, target_h=35*mm):
    sc = target_h / max(bh, bw, 1)
    W = bw * sc; H = bh * sc
    enr = max(30*sc, 2)
    c.setFillColor(BLEU_B); c.setStrokeColor(NOIR); c.setLineWidth(0.5)
    c.rect(cx - W/2, cy - H/2, W, H, fill=1, stroke=1)
    c.setStrokeColor(GRIS2); c.setLineWidth(0.3); c.setDash(2,1)
    c.rect(cx - W/2 + enr, cy - H/2 + enr, W - 2*enr, H - 2*enr)
    c.setDash()
    iw = W - 2*enr; ih = H - 2*enr
    ix = cx - W/2 + enr; iy = cy - H/2 + enr
    br = max(dia * sc / 2, 1.2)
    nb_bot = max(nb // 2, 2); nb_top = nb - nb_bot
    positions = []
    for i in range(nb_bot):
        t = i / max(nb_bot - 1, 1)
        positions.append((ix + iw * t, iy))
    for i in range(nb_top):
        t = i / max(nb_top - 1, 1)
        positions.append((ix + iw * t, iy + ih))
    # Bottom bars in red, top bars in green (matches elevation convention)
    for idx, (px, py) in enumerate(positions[:nb]):
        c.setFillColor(ROUGE if idx < nb_bot else VERT_FERR)
        c.circle(px, py, br, fill=1, stroke=0)
    c.setFillColor(GRIS2); c.setFont("Helvetica", 6)
    c.drawCentredString(cx, cy - H/2 - 7, f"{bw}")
    c.saveState()
    c.translate(cx - W/2 - 7, cy); c.rotate(90)
    c.drawCentredString(0, 0, f"{bh}")
    c.restoreState()
    return W, H


# ════════════════════════════════════════
# ELEVATION POUTRE — format Ngom
# ════════════════════════════════════════
def elevation_poutre(c, x, y, avail_w, portee_mm, h_mm, nb_inf, nb_sup,
                     etr_dia, etr_esp, target_h=20*mm):
    sc = target_h / h_mm
    L = min(portee_mm * sc, avail_w)
    sc = L / portee_mm
    H = h_mm * sc
    enr = max(30 * sc, 1.5)
    c.setFillColor(colors.Color(0.96, 0.96, 0.96))
    c.setStrokeColor(NOIR); c.setLineWidth(0.5)
    c.rect(x, y, L, H, fill=1, stroke=1)
    # Lit inférieur (rouge) — barres de travée
    c.setStrokeColor(ROUGE); c.setLineWidth(0.5)
    for i in range(nb_inf):
        by = y + enr + i * max((enr * 0.6), 1)
        c.line(x + 2, by, x + L - 2, by)
    # Lit supérieur (vert) — chapeaux sur appuis
    c.setStrokeColor(VERT_FERR); c.setLineWidth(0.5)
    for i in range(nb_sup):
        ty = y + H - enr - i * max((enr * 0.6), 1)
        c.line(x + 2, ty, x + L - 2, ty)
    # Étriers (gris fin)
    nb_etr = max(int(portee_mm / etr_esp), 3)
    c.setStrokeColor(GRIS3); c.setLineWidth(0.25)
    for i in range(nb_etr + 1):
        ex = x + enr + i * (L - 2*enr) / nb_etr
        c.line(ex, y + enr - 1, ex, y + H - enr + 1)
    # Crochets d'ancrage (rouge clair, discret)
    hk = min(5*sc, 4)
    c.setStrokeColor(ROUGE_CLAIR); c.setLineWidth(0.4)
    c.line(x + 2, y + enr, x + 2 - hk, y + enr + hk)
    c.line(x + 2, y + H - enr, x + 2 - hk, y + H - enr - hk)
    c.line(x + L - 2, y + enr, x + L - 2 + hk, y + enr + hk)
    c.line(x + L - 2, y + H - enr, x + L - 2 + hk, y + H - enr - hk)
    cot_y = y - 6
    c.setStrokeColor(GRIS3); c.setLineWidth(0.25)
    c.line(x, cot_y, x + L, cot_y)
    c.line(x, cot_y-2, x, cot_y+2)
    c.line(x+L, cot_y-2, x+L, cot_y+2)
    c.setFillColor(GRIS2); c.setFont("Helvetica", 5.5)
    c.drawCentredString(x + L/2, cot_y - 7, f"{portee_mm/1000:.1f} m")
    cx_r = x + L + 5
    c.line(cx_r, y, cx_r, y+H)
    c.line(cx_r-2, y, cx_r+2, y); c.line(cx_r-2, y+H, cx_r+2, y+H)
    c.drawString(cx_r + 3, y + H/2 - 3, f"{h_mm}")
    mid = x + L/2
    c.setStrokeColor(NOIR); c.setLineWidth(0.4)
    c.line(mid, y + H + 3, mid, y + H + 8)
    c.setFont("Helvetica-Bold", 6); c.setFillColor(NOIR)
    c.drawCentredString(mid, y + H + 10, "A")
    c.line(mid, y - 10, mid, y - 15)
    c.drawCentredString(mid, y - 20, "A")
    return L, H


# ════════════════════════════════════════
# ARMATURES TABLE — format Ngom
# ════════════════════════════════════════
def table_armatures(c, x, y, rows):
    cols = [18*mm, 40*mm, 22*mm, 18*mm]
    headers = ["Pos.", "Armature", "l (m)", "Code"]
    rh = 11
    hx = x
    for i, (cw, hd) in enumerate(zip(cols, headers)):
        c.setFillColor(VERT_P); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
        c.rect(hx, y, cw, rh, fill=1, stroke=1)
        c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 5.5)
        c.drawCentredString(hx + cw/2, y + 3, hd)
        hx += cw
    for j, (pos, desc, length, code) in enumerate(rows):
        ry = y - (j+1) * rh
        hx = x
        for cw in cols:
            c.setFillColor(BLANC)
            c.rect(hx, ry, cw, rh, fill=1, stroke=1)
            hx += cw
        c.setFillColor(NOIR); c.setFont("Helvetica", 5.5)
        pcx = x + cols[0]/2; pcy = ry + rh/2
        c.circle(pcx, pcy, 4, fill=0, stroke=1)
        c.drawCentredString(pcx, pcy - 2, str(pos))
        c.drawString(x + cols[0] + 2, ry + 3, desc)
        c.drawCentredString(x + cols[0] + cols[1] + cols[2]/2, ry + 3, f"{length:.2f}")
        c.drawCentredString(x + cols[0] + cols[1] + cols[2] + cols[3]/2, ry + 3, code)
    return (len(rows) + 1) * rh


def table_specs(c, x, y, specs):
    lw, vw, rh = 42*mm, 55*mm, 10
    for i, (label, val) in enumerate(specs):
        ry = y - i * rh
        c.setFillColor(VERT_P if i == 0 else BLANC)
        c.rect(x, ry, lw, rh, fill=1, stroke=1)
        c.rect(x + lw, ry, vw, rh, fill=1, stroke=1)
        c.setFillColor(NOIR)
        c.setFont("Helvetica-Bold" if i == 0 else "Helvetica", 5.5)
        c.drawString(x + 2, ry + 3, label)
        c.setFont("Helvetica", 5.5)
        c.drawString(x + lw + 2, ry + 3, val)
    return len(specs) * rh


# ════════════════════════════════════════
# PLANCHE 1 — PLAN DE COFFRAGE (A3L)
# ════════════════════════════════════════
def pl_coffrage(c, r, p):
    w, h = A3L; c.setPageSize(A3L); border(c, w, h)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 13)
    c.drawString(14*mm, h - 17*mm, "PLAN DE COFFRAGE — NIVEAU COURANT")

    nx_r = p.get("nb_travees_x", 4); ny_r = p.get("nb_travees_y", 3)
    nx = min(nx_r, 8); ny = max(min(ny_r, 6), 3)
    px_m = p.get("portee_max_m", 5.0)
    py_m = p.get("portee_min_m", 4.0)
    if py_m < 2.0: py_m = px_m * 0.65

    ml, mb = 42*mm, 48*mm
    dw = w - ml - 65*mm; dh = h - mb - 28*mm
    tot_x = px_m * nx; tot_y = py_m * ny
    sc = min(dw / tot_x, dh / tot_y)
    gw = tot_x * sc; gh = tot_y * sc
    ox = ml + (dw - gw) / 2; oy = mb + (dh - gh) / 2

    pot_s = getattr(r.poteaux[0], 'section_mm', 300) if hasattr(r, 'poteaux') and r.poteaux else 300
    pp_b = getattr(r.poutre_principale, 'b_mm', 250) if hasattr(r, 'poutre_principale') else 250
    pp_h = getattr(r.poutre_principale, 'h_mm', 500) if hasattr(r, 'poutre_principale') else 500

    c.setStrokeColor(GRIS4); c.setLineWidth(0.2); c.setDash(4, 2)
    for i in range(nx + 1):
        xp = ox + i * px_m * sc
        c.line(xp, oy - 8*mm, xp, oy + gh + 8*mm)
    for j in range(ny + 1):
        yp = oy + j * py_m * sc
        c.line(ox - 8*mm, yp, ox + gw + 8*mm, yp)
    c.setDash()

    for i in range(nx + 1):
        axis_label(c, ox + i * px_m * sc, oy - 15*mm, str(i + 1))
    for j in range(ny + 1):
        axis_label(c, ox - 15*mm, oy + j * py_m * sc, chr(65 + j))

    c.setFillColor(GRIS2); c.setFont("Helvetica", 5.5)
    for i in range(nx):
        mid = ox + (i + 0.5) * px_m * sc
        c.drawCentredString(mid, oy - 9*mm, f"{px_m*1000:.0f}")
    for j in range(ny):
        mid_y = oy + (j + 0.5) * py_m * sc
        c.saveState(); c.translate(ox - 9*mm, mid_y); c.rotate(90)
        c.drawCentredString(0, 0, f"{py_m*1000:.0f}")
        c.restoreState()

    pd = max(pp_b * sc / 1000, 1.5)
    for j in range(ny + 1):
        yp = oy + j * py_m * sc
        for i in range(nx):
            x1 = ox + i * px_m * sc; x2 = ox + (i+1) * px_m * sc
            c.setStrokeColor(NOIR); c.setLineWidth(0.8)
            c.line(x1, yp - pd/2, x2, yp - pd/2)
            c.line(x1, yp + pd/2, x2, yp + pd/2)

    for i in range(nx + 1):
        xp = ox + i * px_m * sc
        for j in range(ny):
            y1 = oy + j * py_m * sc; y2 = oy + (j+1) * py_m * sc
            c.setStrokeColor(GRIS3); c.setLineWidth(0.4)
            c.line(xp, y1, xp, y2)

    c.setStrokeColor(GRIS4); c.setLineWidth(0.1)
    for i in range(nx):
        for j in range(ny):
            sx = ox + i * px_m * sc + 2; sy = oy + j * py_m * sc + 2
            sw = px_m * sc - 4; sh = py_m * sc - 4
            step = max(6, int(sw / 15))
            for k in range(0, int(sw + sh), step):
                lx1 = sx + min(k, sw); ly1 = sy + max(0, k - sw)
                lx2 = sx + max(0, k - sh); ly2 = sy + min(k, sh)
                c.line(lx1, ly1, lx2, ly2)

    pt_d = max(pot_s * sc / 1000, 3)
    for i in range(nx + 1):
        for j in range(ny + 1):
            xp = ox + i * px_m * sc; yp = oy + j * py_m * sc
            c.setFillColor(NOIR); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
            c.rect(xp - pt_d/2, yp - pt_d/2, pt_d, pt_d, fill=1, stroke=1)

    if nx_r > nx or ny_r != ny:
        c.setFont("Helvetica-Oblique", 5.5); c.setFillColor(GRIS3)
        c.drawString(14*mm, h - 23*mm, f"Grille affichée {nx}×{ny} (projet: {nx_r}×{ny_r})")

    lx = w - 58*mm; ly = h - 28*mm
    c.setFont("Helvetica-Bold", 7); c.setFillColor(NOIR)
    c.drawString(lx, ly, "LÉGENDE"); ly -= 12
    c.setFont("Helvetica", 5.5); c.setFillColor(NOIR)
    c.rect(lx, ly, 5, 5, fill=1, stroke=1)
    c.drawString(lx + 8, ly + 1, f"Poteau {pot_s}×{pot_s}"); ly -= 10
    c.setStrokeColor(NOIR); c.setLineWidth(0.8)
    c.line(lx, ly + 3, lx + 15, ly + 3)
    c.setFillColor(NOIR)
    c.drawString(lx + 18, ly + 1, f"PP {pp_b}×{pp_h}"); ly -= 10
    c.setStrokeColor(GRIS3); c.setLineWidth(0.4)
    c.line(lx, ly + 3, lx + 15, ly + 3)
    ps_b = getattr(r.poutre_secondaire, 'b_mm', 0) if hasattr(r, 'poutre_secondaire') and r.poutre_secondaire else 0
    ps_h = getattr(r.poutre_secondaire, 'h_mm', 0) if hasattr(r, 'poutre_secondaire') and r.poutre_secondaire else 0
    c.setFillColor(NOIR)
    if ps_b: c.drawString(lx + 18, ly + 1, f"PS {ps_b}×{ps_h}")

    cartouche(c, w, h, p, "PLAN DE COFFRAGE", 1, 4)
    c.showPage()


# ════════════════════════════════════════
# PLANCHE 2 — FERRAILLAGE POUTRE TYPE (A4P)
# ════════════════════════════════════════
def pl_poutre(c, r, p):
    w, h = A4P; c.setPageSize(A4P); border(c, w, h)
    pt = getattr(r, 'poutre_principale', None)
    if not pt:
        c.setFont("Helvetica", 9); c.drawString(30*mm, h/2, "Données poutre non disponibles")
        cartouche(c, w, h, p, "FERRAILLAGE POUTRE", 2, 4); c.showPage(); return

    portee_mm = pt.portee_m * 1000
    bw, bh = pt.b_mm, pt.h_mm
    as_i, as_s = pt.As_inf_cm2, pt.As_sup_cm2
    ed, ee = pt.etrier_diam_mm, pt.etrier_esp_mm
    nb_i = max(int(as_i / (math.pi * 6**2 / 10000)), 2)
    nb_s = max(int(as_s / (math.pi * 5**2 / 10000)), 2)

    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 11)
    c.drawString(12*mm, h - 15*mm, "FERRAILLAGE POUTRE PRINCIPALE")
    c.setFont("Helvetica", 6.5); c.setFillColor(GRIS2)
    c.drawString(12*mm, h - 21*mm, f"PP1 — Section {bw}×{bh} mm — Portée {pt.portee_m:.1f} m")

    # ── TOP ZONE: elevation left + armatures table right ──
    elev_x = 15*mm; elev_y = h - 75*mm
    avail_elev_w = 110*mm
    eL, eH = elevation_poutre(c, elev_x, elev_y, avail_elev_w, portee_mm, bh,
                               nb_i, nb_s, ed, ee, target_h=18*mm)

    c.setFillColor(NOIR); c.setFont("Helvetica", 5)
    c.circle(elev_x - 5, elev_y + 4, 3.5, fill=0, stroke=1)
    c.drawCentredString(elev_x - 5, elev_y + 2, "1")
    c.circle(elev_x - 5, elev_y + eH - 4, 3.5, fill=0, stroke=1)
    c.drawCentredString(elev_x - 5, elev_y + eH - 6, "2")

    tab_x = 133*mm; tab_y = h - 30*mm
    arm_rows = [
        (1, f"{nb_i}HA 12  l={pt.portee_m+0.2:.2f}", pt.portee_m + 0.2, "00"),
        (2, f"{nb_s}HA 10  l={pt.portee_m+0.4:.2f}", pt.portee_m + 0.4, "00"),
        (3, f"2HA 8  l={pt.portee_m+0.1:.2f}", pt.portee_m + 0.1, "00"),
        (4, f"{int(portee_mm/ee)}HA {ed}  cadres", (bw+bh)*2/1000+0.2, "31"),
    ]
    table_armatures(c, tab_x, tab_y, arm_rows)

    # ── BOTTOM ZONE: section A-A left + specs right ──
    c.setFillColor(VERT); c.setFont("Helvetica-Bold", 7)
    c.drawString(15*mm, h - 105*mm, "COUPE A-A")
    sec_cx = 42*mm; sec_cy = h - 138*mm
    section_ba(c, sec_cx, sec_cy, bw, bh, nb_i + nb_s, 12, target_h=38*mm)
    c.setFillColor(NOIR); c.setFont("Helvetica", 5.5)
    c.drawCentredString(sec_cx, sec_cy - 28*mm, f"Section {bw}×{bh}")
    c.drawCentredString(sec_cx, sec_cy - 33*mm, f"{nb_i+nb_s} barres")

    c.setFillColor(VERT); c.setFont("Helvetica-Bold", 7)
    c.drawString(85*mm, h - 105*mm, "CARACTÉRISTIQUES")
    specs = [
        ("Section", f"{bw} × {bh} mm"),
        ("As inf (travée)", f"{as_i:.2f} cm² — {nb_i} barres"),
        ("As sup (appuis)", f"{as_s:.2f} cm² — {nb_s} barres"),
        ("Étriers", f"HA{ed} / {ee} mm"),
        ("Portée", f"{pt.portee_m:.1f} m"),
        ("Béton", p.get("classe_beton", "C30/37")),
        ("Acier", "HA 500"),
        ("Enrobage", "30 mm"),
    ]
    table_specs(c, 85*mm, h - 112*mm, specs)

    c.setFont("Helvetica", 5); c.setFillColor(GRIS3)
    c.drawString(12*mm, 42*mm, f"Béton {p.get('classe_beton','C30/37')}  —  Acier HA 500  —  Enrobage 3 cm  —  Fissuration peu préjudiciable")
    cartouche(c, w, h, p, "FERRAILLAGE POUTRE PRINCIPALE", 2, 4)
    c.showPage()


# ════════════════════════════════════════
# PLANCHE 3 — FERRAILLAGE POTEAU TYPE (A4P)
# ════════════════════════════════════════
def pl_poteau(c, r, p):
    w, h = A4P; c.setPageSize(A4P); border(c, w, h)
    poteaux = getattr(r, 'poteaux', [])
    if not poteaux:
        c.setFont("Helvetica", 9); c.drawString(30*mm, h/2, "Données poteaux non disponibles")
        cartouche(c, w, h, p, "FERRAILLAGE POTEAUX", 3, 4); c.showPage(); return

    pot0 = poteaux[0]
    sec = pot0.section_mm; nb_b = pot0.nb_barres
    dia = pot0.diametre_mm; cad = pot0.cadre_diam_mm; esp = pot0.espacement_cadres_mm

    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 11)
    c.drawString(12*mm, h - 15*mm, "FERRAILLAGE POTEAUX")
    c.setFont("Helvetica", 6.5); c.setFillColor(GRIS2)
    c.drawString(12*mm, h - 21*mm, "Coupes transversales et sections par niveau")

    # ── TOP: section left + schematic elevation right ──
    c.setFillColor(VERT); c.setFont("Helvetica-Bold", 7)
    c.drawString(15*mm, h - 32*mm, "COUPE POTEAU RDC")
    sec_cx = 42*mm; sec_cy = h - 60*mm
    section_ba(c, sec_cx, sec_cy, sec, sec, nb_b, dia, target_h=30*mm)
    c.setFillColor(NOIR); c.setFont("Helvetica", 5.5)
    c.drawCentredString(sec_cx, sec_cy - 22*mm, f"{sec}×{sec}")
    c.drawCentredString(sec_cx, sec_cy - 27*mm, f"{nb_b}HA{dia}")
    c.drawCentredString(sec_cx, sec_cy - 32*mm, f"Cadres HA{cad}/{esp}")

    c.setFillColor(VERT); c.setFont("Helvetica-Bold", 7)
    c.drawString(85*mm, h - 32*mm, "ÉLÉVATION SCHÉMATIQUE")

    he = p.get("hauteur_etage_m", 3.0)
    nb_niv = len(poteaux)
    elev_x = 105*mm; elev_bot = h - 90*mm
    avail_h = 55*mm
    niv_h = avail_h / max(nb_niv, 1)
    col_w = 6

    for k, pot_k in enumerate(poteaux):
        by = elev_bot + k * niv_h
        c.setFillColor(GRIS5); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
        c.rect(elev_x - col_w/2, by, col_w, niv_h - 1, fill=1, stroke=1)
        c.setStrokeColor(NOIR); c.setLineWidth(0.5)
        c.line(elev_x - 12, by + niv_h - 1, elev_x + 12, by + niv_h - 1)
        niv_label = getattr(pot_k, 'niveau', f'N{k}')
        c.setFillColor(GRIS2); c.setFont("Helvetica", 4.5)
        c.drawString(elev_x + 14, by + niv_h/2 - 2, f"{niv_label} — {pot_k.section_mm}×{pot_k.section_mm}")

    c.setStrokeColor(NOIR); c.setLineWidth(0.6)
    c.line(elev_x - 15, elev_bot, elev_x + 15, elev_bot)
    c.setFillColor(GRIS2); c.setFont("Helvetica", 4.5)
    c.drawCentredString(elev_x, elev_bot - 6, "FOND.")

    # ── BOTTOM: table ──
    c.setFillColor(VERT); c.setFont("Helvetica-Bold", 7)
    c.drawString(12*mm, h - 105*mm, "TABLEAU DES SECTIONS PAR NIVEAU")

    tab_y = h - 113*mm; tab_x = 12*mm
    cols_w = [22*mm, 22*mm, 28*mm, 28*mm, 26*mm, 22*mm]
    hdrs = ["Niveau", "NEd (kN)", "Section", "Armatures", "Cadres", "ρ (%)"]
    rh = 10

    hx = tab_x
    for cw_t, hd in zip(cols_w, hdrs):
        c.setFillColor(VERT_P); c.rect(hx, tab_y, cw_t, rh, fill=1, stroke=1)
        c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 5)
        c.drawCentredString(hx + cw_t/2, tab_y + 3, hd)
        hx += cw_t

    for k, pot_k in enumerate(poteaux):
        ry = tab_y - (k+1) * rh
        hx = tab_x
        for cw_t in cols_w:
            c.setFillColor(BLANC); c.rect(hx, ry, cw_t, rh, fill=1, stroke=1)
            hx += cw_t
        c.setFillColor(NOIR); c.setFont("Helvetica", 5)
        hx = tab_x
        niv_label = getattr(pot_k, 'niveau', f'N{k}')
        vals = [niv_label, f"{pot_k.NEd_kN:.0f}", f"{pot_k.section_mm}×{pot_k.section_mm}",
                f"{pot_k.nb_barres}HA{pot_k.diametre_mm}", f"HA{pot_k.cadre_diam_mm}/{pot_k.espacement_cadres_mm}",
                f"{pot_k.taux_armature_pct:.2f}"]
        for i, v in enumerate(vals):
            c.drawCentredString(hx + cols_w[i]/2, ry + 3, v)
            hx += cols_w[i]

    cartouche(c, w, h, p, "FERRAILLAGE POTEAUX", 3, 4)
    c.showPage()


# ════════════════════════════════════════
# PLANCHE 4 — FONDATIONS + COUPE (A3L)
# ════════════════════════════════════════
def pl_fondations_coupe(c, r, p):
    w, h = A3L; c.setPageSize(A3L); border(c, w, h)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 13)
    c.drawString(14*mm, h - 17*mm, "FONDATIONS ET COUPE GÉNÉRALE")

    mid_x = w / 2

    # ── LEFT: fondations ──
    c.setFillColor(VERT); c.setFont("Helvetica-Bold", 8)
    c.drawString(14*mm, h - 28*mm, "PLAN DE FONDATIONS")

    fd = getattr(r, 'fondation', None)
    nx = min(p.get("nb_travees_x", 4), 8)
    ny = max(min(p.get("nb_travees_y", 3), 6), 3)
    px_m = p.get("portee_max_m", 5.0)
    py_m = p.get("portee_min_m", 4.0)
    if py_m < 2.0: py_m = px_m * 0.65

    lml = 40*mm; lmb = 48*mm
    ldw = mid_x - lml - 15*mm; ldh = h - lmb - 35*mm
    tot_x = px_m * nx; tot_y = py_m * ny
    sc = min(ldw / tot_x, ldh / tot_y)
    gw = tot_x * sc; gh = tot_y * sc
    ox = lml + (ldw - gw) / 2; oy = lmb + (ldh - gh) / 2

    c.setStrokeColor(GRIS4); c.setLineWidth(0.2); c.setDash(4, 2)
    for i in range(nx + 1):
        xp = ox + i * px_m * sc
        c.line(xp, oy - 6*mm, xp, oy + gh + 6*mm)
    for j in range(ny + 1):
        yp = oy + j * py_m * sc
        c.line(ox - 6*mm, yp, ox + gw + 6*mm, yp)
    c.setDash()

    for i in range(nx + 1):
        axis_label(c, ox + i * px_m * sc, oy - 12*mm, str(i+1))
    for j in range(ny + 1):
        axis_label(c, ox - 12*mm, oy + j * py_m * sc, chr(65+j))

    nb_pieux = getattr(fd, 'nb_pieux', 0) if fd else 0
    diam_p = getattr(fd, 'diam_pieu_mm', 600) if fd else 600
    pr = max(min(diam_p * sc / 2000, 8), 3)

    for i in range(nx + 1):
        for j in range(ny + 1):
            xp = ox + i * px_m * sc; yp = oy + j * py_m * sc
            c.setFillColor(VERT_P); c.setStrokeColor(VERT); c.setLineWidth(0.4)
            if nb_pieux > 0:
                c.circle(xp, yp, pr, fill=1, stroke=1)
            else:
                c.rect(xp - pr, yp - pr, 2*pr, 2*pr, fill=1, stroke=1)

    c.setStrokeColor(NOIR); c.setLineWidth(0.8)
    for j in range(ny + 1):
        for i in range(nx):
            x1 = ox + i * px_m * sc + pr; x2 = ox + (i+1) * px_m * sc - pr
            yp = oy + j * py_m * sc; c.line(x1, yp, x2, yp)
    for i in range(nx + 1):
        for j in range(ny):
            xp = ox + i * px_m * sc
            y1 = oy + j * py_m * sc + pr; y2 = oy + (j+1) * py_m * sc - pr
            c.line(xp, y1, xp, y2)

    c.setFont("Helvetica", 5); c.setFillColor(GRIS2)
    type_f = "Pieux forés" if nb_pieux > 0 else "Semelles"
    c.drawString(14*mm, lmb - 12*mm, f"{type_f} — ø{diam_p}mm" if nb_pieux else type_f)

    # ── RIGHT: coupe générale ──
    c.setFillColor(VERT); c.setFont("Helvetica-Bold", 8)
    c.drawString(mid_x + 10*mm, h - 28*mm, "COUPE GÉNÉRALE — ÉLÉVATION")

    poteaux = getattr(r, 'poteaux', [])
    nb_niv = p.get("nb_niveaux", len(poteaux) if poteaux else 5)
    he = p.get("hauteur_etage_m", 3.0)
    nc = min(p.get("nb_travees_x", 4), 5)

    rml = mid_x + 25*mm; rmb = 48*mm
    rdw = w - rml - 25*mm; rdh = h - rmb - 35*mm
    tot_hm = nb_niv * he; tot_wm = px_m * nc
    rsc = min(rdw / tot_wm, rdh / tot_hm)
    cgw = tot_wm * rsc; cgh = tot_hm * rsc
    cox = rml + (rdw - cgw) / 2; coy = rmb + (rdh - cgh) / 2

    for niv in range(nb_niv):
        yb = coy + niv * he * rsc; yt = coy + (niv + 1) * he * rsc
        pot_k = poteaux[niv] if niv < len(poteaux) else None
        sec_k = pot_k.section_mm if pot_k else 300
        pw = max(sec_k * rsc / 1000, 2.5)
        dh_s = max(200 * rsc / 1000, 1.5)
        c.setFillColor(GRIS5); c.setStrokeColor(NOIR); c.setLineWidth(0.3)
        c.rect(cox, yt - dh_s, cgw, dh_s, fill=1, stroke=1)
        for i in range(nc + 1):
            cpx = cox + i * px_m * rsc
            c.setFillColor(colors.Color(0.88, 0.88, 0.88))
            c.rect(cpx - pw/2, yb, pw, yt - yb - dh_s, fill=1, stroke=1)
        niv_label = getattr(pot_k, 'niveau', f'N{niv}') if pot_k else f'N{niv}'
        c.setFillColor(NOIR); c.setFont("Helvetica", 5)
        c.drawString(cox - 18*mm, yb + (yt - yb)/2 - 2, niv_label)
        c.setFillColor(GRIS2); c.setFont("Helvetica", 4.5)
        c.drawString(cox + cgw + 3, yb + (yt - yb)/2 - 2, f"{sec_k}×{sec_k}")

    fd_h = max(6, 500 * rsc / 1000)
    c.setFillColor(GRIS4); c.setStrokeColor(NOIR); c.setLineWidth(0.4)
    c.rect(cox - 5, coy - fd_h, cgw + 10, fd_h, fill=1, stroke=1)
    c.setFillColor(NOIR); c.setFont("Helvetica", 5)
    c.drawCentredString(cox + cgw/2, coy - fd_h + 2, "FONDATIONS")

    for i in range(nc + 1):
        axis_label(c, cox + i * px_m * rsc, coy - fd_h - 10*mm, str(i+1))

    c.setFont("Helvetica-Bold", 6); c.setFillColor(NOIR)
    c.drawString(cox + cgw + 3, coy + cgh/2, f"H = {tot_hm:.1f} m")

    cartouche(c, w, h, p, "FONDATIONS + COUPE", 4, 4, ech="1/200")
    c.showPage()


# ════════════════════════════════════════
# ASSEMBLAGE
# ════════════════════════════════════════
def generer_dossier_ba(output_path, resultats=None, params=None):
    if params is None: params = {}
    if hasattr(params, "__dict__"):
        params = {k: v for k, v in vars(params).items() if not k.startswith("_")}
    r = resultats
    if r is not None:
        if hasattr(r, 'poteaux'):
            for pot in r.poteaux:
                if not hasattr(pot, 'niveau'):
                    pot.niveau = f"N{r.poteaux.index(pot)}"
        if hasattr(r, 'fondation'):
            fd = r.fondation
            if not hasattr(fd, 'type_fond') and hasattr(fd, 'type'):
                fd.type_fond = str(getattr(fd.type, 'value', fd.type))

    c = pdfcanvas.Canvas(output_path, pagesize=A3L)
    c.setTitle(f"Dossier BA — {params.get('nom', 'Projet Tijan')}")
    c.setAuthor("Tijan AI")

    pl_coffrage(c, r, p=params)
    pl_poutre(c, r, p=params)
    pl_poteau(c, r, p=params)
    pl_fondations_coupe(c, r, p=params)

    c.save()
    return output_path


def generer_planches(resultats, output_path, params=None):
    return generer_dossier_ba(output_path, resultats, params)
