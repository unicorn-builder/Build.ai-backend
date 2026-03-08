"""
Tijan AI — Générateur de Plans Structurels
Plan d'exécution : Vue en plan + Coupe + Cartouche
Format : SVG (web) + PDF (impression)
Référentiel : EN 1992-1-1, EN 1997-1
"""

import math
import io
import os
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import A1, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.colors import HexColor


# ============================================================
# COULEURS TIJAN
# ============================================================
VERT_FONCE   = HexColor("#2D6A4F")
VERT_MOYEN   = HexColor("#40916C")
VERT_CLAIR   = HexColor("#95D5B2")
VERT_PALE    = HexColor("#D8F3DC")
BLANC        = HexColor("#FFFFFF")
GRIS_FOND    = HexColor("#F8FAF8")
GRIS_LIGNE   = HexColor("#CCCCCC")
NOIR         = HexColor("#1A1A1A")
BETON_HATCH  = HexColor("#B0B8B0")
ACIER_COLOR  = HexColor("#C0392B")
POTEAU_FILL  = HexColor("#2D6A4F")
VOILE_FILL   = HexColor("#40916C")
POUTRE_COLOR = HexColor("#1A5C3A")
FOND_DALLE   = HexColor("#E8F5E9")


# ============================================================
# GÉNÉRATEUR SVG
# ============================================================

def generer_svg_plan(projet_data: dict, resultat_data: dict) -> str:
    """
    Génère un plan SVG complet avec :
    - Vue en plan RDC (grille poteaux, voiles, poutres, dalle)
    - Vue en coupe longitudinale (élévation)
    - Cartouche professionnel
    """

    # Extraction données projet
    nom = projet_data.get("nom", "Projet")
    nb_niveaux = projet_data.get("geometrie", {}).get("nb_niveaux", 5)
    surface = projet_data.get("geometrie", {}).get("surface_emprise_m2", 500)
    portee = projet_data.get("geometrie", {}).get("portee_max_m", 6.0)
    hauteur_etage = projet_data.get("geometrie", {}).get("hauteur_etage_m", 3.0)
    ville = projet_data.get("localisation", {}).get("ville", "dakar")

    # Extraction résultats
    resume = resultat_data.get("resume", {})
    poteau_section = resume.get("poteau_section", "25×25 cm")
    poteau_ferraillage = resume.get("poteau_ferraillage", "4HA12")
    poutre_section = resume.get("poutre_section", "25×50 cm")
    dalle_ep = resume.get("dalle_epaisseur", "20 cm")
    voile_ep = resume.get("voile_epaisseur", "20 cm")
    fondations_type = resume.get("fondations_type", "Radier général")
    beton = resume.get("beton", "C30/37")

    # Grille de poteaux estimée
    cote = math.sqrt(surface)
    nb_travees_x = max(2, round(cote / portee))
    nb_travees_y = max(2, round(cote / portee))
    nb_poteaux_x = nb_travees_x + 1
    nb_poteaux_y = nb_travees_y + 1

    # Dimensions SVG
    SVG_W = 1600
    SVG_H = 1100

    # Zones de dessin
    MARGIN = 40
    CARTOUCHE_H = 100
    PLAN_X = MARGIN + 60        # Offset pour axes Y
    PLAN_Y = MARGIN + 40        # Offset pour titre
    PLAN_W = 700
    PLAN_H = SVG_H - CARTOUCHE_H - PLAN_Y - MARGIN - 20

    COUPE_X = PLAN_X + PLAN_W + 80
    COUPE_Y = PLAN_Y
    COUPE_W = SVG_W - COUPE_X - MARGIN
    COUPE_H = PLAN_H

    # Échelles
    echelle_plan = min(PLAN_W / (nb_travees_x * portee), PLAN_H / (nb_travees_y * portee)) * 0.85
    grille_x = portee * echelle_plan
    grille_y = portee * echelle_plan
    plan_total_w = nb_travees_x * grille_x
    plan_total_h = nb_travees_y * grille_y
    plan_offset_x = PLAN_X + (PLAN_W - plan_total_w) / 2
    plan_offset_y = PLAN_Y + (PLAN_H - plan_total_h) / 2

    # Section poteau en pixels
    try:
        s = float(poteau_section.split("×")[0].replace("cm", "").strip())
    except:
        s = 25.0
    poteau_px = max(8, s * echelle_plan / 100)

    # Épaisseur voile en pixels
    try:
        ep_v = float(voile_ep.replace("cm", "").strip())
    except:
        ep_v = 20.0
    voile_px = max(6, ep_v * echelle_plan / 100)

    # Hauteur section poutre
    try:
        h_p = float(poutre_section.split("×")[1].replace("cm", "").strip())
    except:
        h_p = 50.0
    poutre_px = max(4, h_p * echelle_plan / 100 * 0.4)

    # Coupe — échelle
    hauteur_totale = nb_niveaux * hauteur_etage + 1.5  # +fondations
    echelle_coupe_h = (COUPE_H * 0.75) / hauteur_totale
    echelle_coupe_w = (COUPE_W * 0.6) / (nb_travees_x * portee)
    echelle_coupe = min(echelle_coupe_h, echelle_coupe_w)
    coupe_total_w = nb_travees_x * portee * echelle_coupe
    coupe_total_h = hauteur_totale * echelle_coupe
    coupe_offset_x = COUPE_X + (COUPE_W - coupe_total_w) / 2
    coupe_offset_y = COUPE_Y + COUPE_H - 20

    date_str = datetime.now().strftime("%d/%m/%Y")

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_W}" height="{SVG_H}" viewBox="0 0 {SVG_W} {SVG_H}">')

    # ── Fond ──────────────────────────────────────────────────
    lines.append(f'<rect width="{SVG_W}" height="{SVG_H}" fill="#F8FAF8"/>')

    # ── Bordure générale ──────────────────────────────────────
    lines.append(f'<rect x="{MARGIN}" y="{MARGIN}" width="{SVG_W-2*MARGIN}" height="{SVG_H-2*MARGIN}" fill="none" stroke="#2D6A4F" stroke-width="2"/>')

    # ── Double bordure intérieure ─────────────────────────────
    lines.append(f'<rect x="{MARGIN+4}" y="{MARGIN+4}" width="{SVG_W-2*MARGIN-8}" height="{SVG_H-2*MARGIN-8}" fill="none" stroke="#95D5B2" stroke-width="0.5"/>')

    # ── CARTOUCHE (bas) ───────────────────────────────────────
    cart_y = SVG_H - MARGIN - CARTOUCHE_H
    cart_x = MARGIN
    cart_w = SVG_W - 2*MARGIN

    lines.append(f'<rect x="{cart_x}" y="{cart_y}" width="{cart_w}" height="{CARTOUCHE_H}" fill="#2D6A4F"/>') 

    # Logo zone
    lines.append(f'<rect x="{cart_x}" y="{cart_y}" width="160" height="{CARTOUCHE_H}" fill="#1A5C3A"/>')
    lines.append(f'<text x="{cart_x+80}" y="{cart_y+38}" font-family="Arial" font-size="18" font-weight="bold" fill="white" text-anchor="middle">TIJAN AI</text>')
    lines.append(f'<text x="{cart_x+80}" y="{cart_y+55}" font-family="Arial" font-size="8" fill="#95D5B2" text-anchor="middle">Engineering Intelligence</text>')
    lines.append(f'<text x="{cart_x+80}" y="{cart_y+67}" font-family="Arial" font-size="8" fill="#95D5B2" text-anchor="middle">for Africa</text>')

    # Infos projet
    col2 = cart_x + 180
    lines.append(f'<text x="{col2}" y="{cart_y+22}" font-family="Arial" font-size="9" fill="#D8F3DC">PROJET</text>')
    lines.append(f'<text x="{col2}" y="{cart_y+38}" font-family="Arial" font-size="13" font-weight="bold" fill="white">{nom}</text>')
    lines.append(f'<text x="{col2}" y="{cart_y+54}" font-family="Arial" font-size="9" fill="#95D5B2">R+{nb_niveaux} — {surface} m² — {ville.upper()}</text>')
    lines.append(f'<text x="{col2}" y="{cart_y+68}" font-family="Arial" font-size="9" fill="#95D5B2">{beton} — {fondations_type}</text>')

    # Titre du plan
    col3 = cart_x + 480
    lines.append(f'<line x1="{col3-10}" y1="{cart_y+10}" x2="{col3-10}" y2="{cart_y+CARTOUCHE_H-10}" stroke="#40916C" stroke-width="1"/>')
    lines.append(f'<text x="{col3+100}" y="{cart_y+32}" font-family="Arial" font-size="16" font-weight="bold" fill="white" text-anchor="middle">PLAN D\'EXÉCUTION STRUCTUREL</text>')
    lines.append(f'<text x="{col3+100}" y="{cart_y+50}" font-family="Arial" font-size="10" fill="#D8F3DC" text-anchor="middle">Vue en plan RDC + Coupe longitudinale</text>')
    lines.append(f'<text x="{col3+100}" y="{cart_y+65}" font-family="Arial" font-size="8" fill="#95D5B2" text-anchor="middle">EN 1990 / EN 1992-1-1 / EN 1997-1</text>')

    # Infos techniques droite
    col4 = cart_x + cart_w - 320
    lines.append(f'<line x1="{col4-10}" y1="{cart_y+10}" x2="{col4-10}" y2="{cart_y+CARTOUCHE_H-10}" stroke="#40916C" stroke-width="1"/>')
    lines.append(f'<text x="{col4}" y="{cart_y+22}" font-family="Arial" font-size="8" fill="#D8F3DC">BÉTON</text>')
    lines.append(f'<text x="{col4+80}" y="{cart_y+22}" font-family="Arial" font-size="8" fill="white">{beton}</text>')
    lines.append(f'<text x="{col4}" y="{cart_y+36}" font-family="Arial" font-size="8" fill="#D8F3DC">POTEAUX</text>')
    lines.append(f'<text x="{col4+80}" y="{cart_y+36}" font-family="Arial" font-size="8" fill="white">{poteau_section}</text>')
    lines.append(f'<text x="{col4}" y="{cart_y+50}" font-family="Arial" font-size="8" fill="#D8F3DC">POUTRES</text>')
    lines.append(f'<text x="{col4+80}" y="{cart_y+50}" font-family="Arial" font-size="8" fill="white">{poutre_section}</text>')
    lines.append(f'<text x="{col4}" y="{cart_y+64}" font-family="Arial" font-size="8" fill="#D8F3DC">DALLE</text>')
    lines.append(f'<text x="{col4+80}" y="{cart_y+64}" font-family="Arial" font-size="8" fill="white">{dalle_ep}</text>')

    # Date / Échelle / Ref
    col5 = cart_x + cart_w - 130
    lines.append(f'<line x1="{col5-10}" y1="{cart_y+10}" x2="{col5-10}" y2="{cart_y+CARTOUCHE_H-10}" stroke="#40916C" stroke-width="1"/>')
    lines.append(f'<text x="{col5}" y="{cart_y+22}" font-family="Arial" font-size="8" fill="#D8F3DC">DATE</text>')
    lines.append(f'<text x="{col5+60}" y="{cart_y+22}" font-family="Arial" font-size="8" fill="white">{date_str}</text>')
    lines.append(f'<text x="{col5}" y="{cart_y+36}" font-family="Arial" font-size="8" fill="#D8F3DC">ÉCHELLE</text>')
    lines.append(f'<text x="{col5+60}" y="{cart_y+36}" font-family="Arial" font-size="8" fill="white">1/100</text>')
    lines.append(f'<text x="{col5}" y="{cart_y+50}" font-family="Arial" font-size="8" fill="#D8F3DC">FORMAT</text>')
    lines.append(f'<text x="{col5+60}" y="{cart_y+50}" font-family="Arial" font-size="8" fill="white">A1 Paysage</text>')
    lines.append(f'<text x="{col5}" y="{cart_y+64}" font-family="Arial" font-size="8" fill="#D8F3DC">FOLIO</text>')
    lines.append(f'<text x="{col5+60}" y="{cart_y+64}" font-family="Arial" font-size="8" fill="white">01/01</text>')

    # Avertissement
    lines.append(f'<text x="{cart_x + cart_w/2}" y="{cart_y+88}" font-family="Arial" font-size="7" fill="#95D5B2" text-anchor="middle" font-style="italic">Document d\'assistance à l\'ingénierie — Doit être vérifié et signé par un ingénieur habilité avant toute utilisation réglementaire</text>')

    # ── TITRE ZONES ───────────────────────────────────────────
    # Titre Vue en plan
    lines.append(f'<rect x="{PLAN_X}" y="{MARGIN+8}" width="{PLAN_W}" height="24" fill="#2D6A4F" rx="3"/>')
    lines.append(f'<text x="{PLAN_X + PLAN_W/2}" y="{MARGIN+24}" font-family="Arial" font-size="12" font-weight="bold" fill="white" text-anchor="middle">VUE EN PLAN — RDC (Niveau 0)</text>')

    # Titre Coupe
    lines.append(f'<rect x="{COUPE_X}" y="{MARGIN+8}" width="{COUPE_W}" height="24" fill="#2D6A4F" rx="3"/>')
    lines.append(f'<text x="{COUPE_X + COUPE_W/2}" y="{MARGIN+24}" font-family="Arial" font-size="12" font-weight="bold" fill="white" text-anchor="middle">COUPE A-A — Longitudinale</text>')

    # Séparateur vertical
    sep_x = PLAN_X + PLAN_W + 40
    lines.append(f'<line x1="{sep_x}" y1="{MARGIN+8}" x2="{sep_x}" y2="{cart_y-5}" stroke="#95D5B2" stroke-width="1" stroke-dasharray="4,3"/>')

    # ── VUE EN PLAN ───────────────────────────────────────────

    # Fond dalle
    lines.append(f'<rect x="{plan_offset_x}" y="{plan_offset_y}" width="{plan_total_w}" height="{plan_total_h}" fill="#E8F5E9" stroke="#2D6A4F" stroke-width="1.5"/>')

    # Hachures dalle (pattern)
    hatch_id = "hatch_dalle"
    lines.append(f'<defs><pattern id="{hatch_id}" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">')
    lines.append(f'<line x1="0" y1="0" x2="0" y2="10" stroke="#B8D8BA" stroke-width="0.5"/>')
    lines.append('</pattern></defs>')

    # Axes de la grille (lignes de construction)
    for i in range(nb_poteaux_x):
        ax = plan_offset_x + i * grille_x
        lines.append(f'<line x1="{ax}" y1="{plan_offset_y-30}" x2="{ax}" y2="{plan_offset_y+plan_total_h+30}" stroke="#95D5B2" stroke-width="0.5" stroke-dasharray="6,3"/>')
        # Cercle axe
        lines.append(f'<circle cx="{ax}" cy="{plan_offset_y-18}" r="10" fill="#2D6A4F" stroke="none"/>')
        label = chr(65 + i)  # A, B, C...
        lines.append(f'<text x="{ax}" y="{plan_offset_y-14}" font-family="Arial" font-size="9" font-weight="bold" fill="white" text-anchor="middle">{label}</text>')

    for j in range(nb_poteaux_y):
        ay = plan_offset_y + j * grille_y
        lines.append(f'<line x1="{plan_offset_x-30}" y1="{ay}" x2="{plan_offset_x+plan_total_w+30}" y2="{ay}" stroke="#95D5B2" stroke-width="0.5" stroke-dasharray="6,3"/>')
        # Cercle axe
        lines.append(f'<circle cx="{plan_offset_x-18}" cy="{ay}" r="10" fill="#2D6A4F" stroke="none"/>')
        lines.append(f'<text x="{plan_offset_x-18}" y="{ay+4}" font-family="Arial" font-size="9" font-weight="bold" fill="white" text-anchor="middle">{nb_poteaux_y-j}</text>')

    # Poutres (avant poteaux)
    for i in range(nb_poteaux_x):
        for j in range(nb_poteaux_y):
            px = plan_offset_x + i * grille_x
            py = plan_offset_y + j * grille_y
            # Poutre horizontale
            if i < nb_travees_x:
                lines.append(f'<rect x="{px}" y="{py - poutre_px/2}" width="{grille_x}" height="{poutre_px}" fill="#1A5C3A" opacity="0.85"/>')
            # Poutre verticale
            if j < nb_travees_y:
                lines.append(f'<rect x="{px - poutre_px/2}" y="{py}" width="{poutre_px}" height="{grille_y}" fill="#1A5C3A" opacity="0.85"/>')

    # Voiles (façades)
    # Façade bas
    lines.append(f'<rect x="{plan_offset_x}" y="{plan_offset_y+plan_total_h-voile_px}" width="{plan_total_w}" height="{voile_px}" fill="#40916C"/>')
    # Façade haut
    lines.append(f'<rect x="{plan_offset_x}" y="{plan_offset_y}" width="{plan_total_w}" height="{voile_px}" fill="#40916C"/>')
    # Façade gauche
    lines.append(f'<rect x="{plan_offset_x}" y="{plan_offset_y}" width="{voile_px}" height="{plan_total_h}" fill="#40916C"/>')
    # Façade droite
    lines.append(f'<rect x="{plan_offset_x+plan_total_w-voile_px}" y="{plan_offset_y}" width="{voile_px}" height="{plan_total_h}" fill="#40916C"/>')

    # Voiles intérieurs (refends)
    mid_y = plan_offset_y + plan_total_h / 2
    lines.append(f'<rect x="{plan_offset_x+voile_px}" y="{mid_y-voile_px/2}" width="{plan_total_w-2*voile_px}" height="{voile_px}" fill="#40916C" opacity="0.7"/>')

    # Poteaux
    for i in range(nb_poteaux_x):
        for j in range(nb_poteaux_y):
            px = plan_offset_x + i * grille_x
            py = plan_offset_y + j * grille_y
            half = poteau_px / 2
            lines.append(f'<rect x="{px-half}" y="{py-half}" width="{poteau_px}" height="{poteau_px}" fill="#2D6A4F" stroke="#1A3D2E" stroke-width="1"/>')
            # Croix ferraillage
            lines.append(f'<line x1="{px-half+1}" y1="{py}" x2="{px+half-1}" y2="{py}" stroke="#D8F3DC" stroke-width="0.8"/>')
            lines.append(f'<line x1="{px}" y1="{py-half+1}" x2="{px}" y2="{py+half-1}" stroke="#D8F3DC" stroke-width="0.8"/>')

    # Cotation horizontale (bas)
    cot_y = plan_offset_y + plan_total_h + 25
    for i in range(nb_travees_x):
        x1 = plan_offset_x + i * grille_x
        x2 = plan_offset_x + (i+1) * grille_x
        xm = (x1 + x2) / 2
        lines.append(f'<line x1="{x1+2}" y1="{cot_y}" x2="{x2-2}" y2="{cot_y}" stroke="#2D6A4F" stroke-width="1" marker-start="url(#arrow)" marker-end="url(#arrow)"/>')
        lines.append(f'<text x="{xm}" y="{cot_y-4}" font-family="Arial" font-size="8" fill="#2D6A4F" text-anchor="middle">{portee:.1f}m</text>')

    # Cotation totale
    lines.append(f'<line x1="{plan_offset_x}" y1="{cot_y+14}" x2="{plan_offset_x+plan_total_w}" y2="{cot_y+14}" stroke="#1A5C3A" stroke-width="1.2"/>')
    lines.append(f'<text x="{plan_offset_x+plan_total_w/2}" y="{cot_y+26}" font-family="Arial" font-size="9" font-weight="bold" fill="#1A5C3A" text-anchor="middle">{nb_travees_x*portee:.1f} m</text>')

    # Cotation verticale (gauche)
    cot_x = plan_offset_x - 35
    for j in range(nb_travees_y):
        y1 = plan_offset_y + j * grille_y
        y2 = plan_offset_y + (j+1) * grille_y
        ym = (y1 + y2) / 2
        lines.append(f'<text x="{cot_x}" y="{ym+4}" font-family="Arial" font-size="8" fill="#2D6A4F" text-anchor="middle">{portee:.1f}m</text>')

    # Indicateur Nord
    nord_x = plan_offset_x + plan_total_w + 20
    nord_y = plan_offset_y + 30
    lines.append(f'<circle cx="{nord_x}" cy="{nord_y}" r="16" fill="none" stroke="#2D6A4F" stroke-width="1.5"/>')
    lines.append(f'<polygon points="{nord_x},{nord_y-14} {nord_x-6},{nord_y+6} {nord_x+6},{nord_y+6}" fill="#2D6A4F"/>')
    lines.append(f'<text x="{nord_x}" y="{nord_y+26}" font-family="Arial" font-size="9" font-weight="bold" fill="#2D6A4F" text-anchor="middle">N</text>')

    # Ligne de coupe A-A
    coupe_line_y = plan_offset_y + plan_total_h / 2
    lines.append(f'<line x1="{plan_offset_x-5}" y1="{coupe_line_y}" x2="{plan_offset_x+plan_total_w+5}" y2="{coupe_line_y}" stroke="#C0392B" stroke-width="1.5" stroke-dasharray="8,4"/>')
    lines.append(f'<text x="{plan_offset_x-8}" y="{coupe_line_y-4}" font-family="Arial" font-size="10" font-weight="bold" fill="#C0392B" text-anchor="end">A</text>')
    lines.append(f'<text x="{plan_offset_x+plan_total_w+8}" y="{coupe_line_y-4}" font-family="Arial" font-size="10" font-weight="bold" fill="#C0392B">A</text>')

    # ── LÉGENDE PLAN ─────────────────────────────────────────
    leg_x = PLAN_X + 10
    leg_y = PLAN_Y + PLAN_H - 100
    lines.append(f'<rect x="{leg_x-5}" y="{leg_y-15}" width="180" height="105" fill="white" stroke="#95D5B2" stroke-width="1" rx="3" opacity="0.95"/>')
    lines.append(f'<text x="{leg_x+85}" y="{leg_y}" font-family="Arial" font-size="9" font-weight="bold" fill="#2D6A4F" text-anchor="middle">LÉGENDE</text>')

    items = [
        ("#2D6A4F", f"Poteau BA — {poteau_section}"),
        ("#40916C", f"Voile BA — e={voile_ep}"),
        ("#1A5C3A", f"Poutre — {poutre_section}"),
        ("#E8F5E9", f"Dalle — e={dalle_ep}"),
    ]
    for k, (col, label) in enumerate(items):
        iy = leg_y + 14 + k * 18
        lines.append(f'<rect x="{leg_x}" y="{iy-8}" width="14" height="10" fill="{col}" stroke="#2D6A4F" stroke-width="0.5"/>')
        lines.append(f'<text x="{leg_x+20}" y="{iy}" font-family="Arial" font-size="8" fill="#1A1A1A">{label}</text>')

    lines.append(f'<text x="{leg_x}" y="{leg_y+90}" font-family="Arial" font-size="7" fill="#666">Ferraillage : {poteau_ferraillage}</text>')

    # ── VUE EN COUPE ─────────────────────────────────────────

    sol_y = coupe_offset_y
    hauteur_etage_px = hauteur_etage * echelle_coupe
    ep_dalle_px = max(4, 0.20 * echelle_coupe)
    ep_voile_coupe = max(5, ep_v / 100 * echelle_coupe)
    coupe_poteau_w = max(8, s / 100 * echelle_coupe)

    # Sol + fondation
    fond_h = 1.0 * echelle_coupe
    if "radier" in fondations_type.lower():
        # Radier
        rad_ep = max(12, 0.5 * echelle_coupe)
        lines.append(f'<rect x="{coupe_offset_x - 20}" y="{sol_y+2}" width="{coupe_total_w + 40}" height="{rad_ep}" fill="#2D6A4F" stroke="#1A3D2E" stroke-width="1"/>')
        lines.append(f'<text x="{coupe_offset_x + coupe_total_w + 25}" y="{sol_y+14}" font-family="Arial" font-size="8" fill="#2D6A4F">Radier e=0.9m</text>')
        # Hachures sol
        for hx in range(int(coupe_offset_x-20), int(coupe_offset_x + coupe_total_w + 40), 12):
            lines.append(f'<line x1="{hx}" y1="{sol_y+rad_ep}" x2="{hx+10}" y2="{sol_y+rad_ep+15}" stroke="#888" stroke-width="0.8"/>')
    else:
        # Semelles
        for i in range(nb_poteaux_x):
            sx = coupe_offset_x + i * portee * echelle_coupe
            lines.append(f'<rect x="{sx-15}" y="{sol_y+2}" width="30" height="20" fill="#2D6A4F"/>')

    # Ligne de sol
    lines.append(f'<line x1="{coupe_offset_x-30}" y1="{sol_y}" x2="{coupe_offset_x+coupe_total_w+30}" y2="{sol_y}" stroke="#1A1A1A" stroke-width="2.5"/>')
    lines.append(f'<text x="{coupe_offset_x-32}" y="{sol_y-4}" font-family="Arial" font-size="8" fill="#1A1A1A" text-anchor="end">±0.00</text>')

    # Niveaux
    for n in range(nb_niveaux + 1):
        ny = sol_y - n * hauteur_etage_px
        cote = n * hauteur_etage

        # Dalle
        if n > 0:
            lines.append(f'<rect x="{coupe_offset_x}" y="{ny-ep_dalle_px}" width="{coupe_total_w}" height="{ep_dalle_px}" fill="#40916C" opacity="0.8"/>')

        # Cotation niveau
        lines.append(f'<line x1="{coupe_offset_x-28}" y1="{ny}" x2="{coupe_offset_x-2}" y2="{ny}" stroke="#2D6A4F" stroke-width="0.8"/>')
        lines.append(f'<text x="{coupe_offset_x-30}" y="{ny+4}" font-family="Arial" font-size="8" fill="#2D6A4F" text-anchor="end">+{cote:.1f}m</text>')

        # Poteaux entre niveaux
        if n < nb_niveaux:
            for i in range(nb_poteaux_x):
                px_c = coupe_offset_x + i * portee * echelle_coupe
                py_top = ny - hauteur_etage_px
                lines.append(f'<rect x="{px_c - coupe_poteau_w/2}" y="{py_top}" width="{coupe_poteau_w}" height="{hauteur_etage_px}" fill="#2D6A4F" stroke="#1A3D2E" stroke-width="0.8"/>')

        # Poutres
        if n > 0:
            for i in range(nb_travees_x):
                px1 = coupe_offset_x + i * portee * echelle_coupe
                px2 = coupe_offset_x + (i+1) * portee * echelle_coupe
                lines.append(f'<rect x="{px1}" y="{ny-ep_dalle_px-max(6,h_p/100*echelle_coupe*0.5)}" width="{px2-px1}" height="{max(6,h_p/100*echelle_coupe*0.5)}" fill="#1A5C3A" opacity="0.9"/>')

    # Voiles façade coupe
    lines.append(f'<rect x="{coupe_offset_x-ep_voile_coupe}" y="{sol_y-nb_niveaux*hauteur_etage_px}" width="{ep_voile_coupe}" height="{nb_niveaux*hauteur_etage_px}" fill="#40916C" opacity="0.85"/>')
    lines.append(f'<rect x="{coupe_offset_x+coupe_total_w}" y="{sol_y-nb_niveaux*hauteur_etage_px}" width="{ep_voile_coupe}" height="{nb_niveaux*hauteur_etage_px}" fill="#40916C" opacity="0.85"/>')

    # Cotation hauteur totale
    ht_x = coupe_offset_x + coupe_total_w + ep_voile_coupe + 25
    ht_y_top = sol_y - nb_niveaux * hauteur_etage_px
    ht_y_bot = sol_y
    lines.append(f'<line x1="{ht_x}" y1="{ht_y_top}" x2="{ht_x}" y2="{ht_y_bot}" stroke="#2D6A4F" stroke-width="1"/>')
    lines.append(f'<line x1="{ht_x-5}" y1="{ht_y_top}" x2="{ht_x+5}" y2="{ht_y_top}" stroke="#2D6A4F" stroke-width="1"/>')
    lines.append(f'<line x1="{ht_x-5}" y1="{ht_y_bot}" x2="{ht_x+5}" y2="{ht_y_bot}" stroke="#2D6A4F" stroke-width="1"/>')
    ht_total = nb_niveaux * hauteur_etage
    lines.append(f'<text x="{ht_x+8}" y="{(ht_y_top+ht_y_bot)/2+4}" font-family="Arial" font-size="9" font-weight="bold" fill="#2D6A4F">H={ht_total:.1f}m</text>')

    # Étiquette hauteur d'étage
    etiq_y = sol_y - hauteur_etage_px / 2
    lines.append(f'<text x="{coupe_offset_x - ep_voile_coupe - 8}" y="{etiq_y}" font-family="Arial" font-size="8" fill="#666" text-anchor="end" transform="rotate(-90,{coupe_offset_x-ep_voile_coupe-8},{etiq_y})">h={hauteur_etage}m</text>')

    # ── INFORMATIONS COMPLÉMENTAIRES ─────────────────────────
    info_x = COUPE_X + 10
    info_y = COUPE_Y + COUPE_H - 80
    lines.append(f'<rect x="{info_x-5}" y="{info_y-15}" width="{COUPE_W-20}" height="75" fill="white" stroke="#95D5B2" stroke-width="1" rx="3" opacity="0.95"/>')
    lines.append(f'<text x="{info_x + (COUPE_W-20)/2}" y="{info_y}" font-family="Arial" font-size="9" font-weight="bold" fill="#2D6A4F" text-anchor="middle">NOTES TECHNIQUES</text>')
    notes_text = [
        f"• Béton : {beton} — Acier FeE500 (fyk=500 MPa)",
        f"• Fondations : {fondations_type} — σ_sol calculée < σ_adm",
        f"• Poteaux : {poteau_section} — {poteau_ferraillage}",
        f"• Toutes sections vérifiées selon EN 1992-1-1",
    ]
    for k, note in enumerate(notes_text):
        lines.append(f'<text x="{info_x}" y="{info_y+14+k*13}" font-family="Arial" font-size="8" fill="#333">{note}</text>')

    lines.append('</svg>')
    return "\n".join(lines)


# ============================================================
# GÉNÉRATEUR PDF (ReportLab)
# ============================================================

def generer_pdf_plan(projet_data: dict, resultat_data: dict, output_path: str) -> str:
    """
    Génère le plan structurel en PDF format A1 paysage
    """
    # Générer SVG d'abord
    svg_content = generer_svg_plan(projet_data, resultat_data)

    # Créer PDF A1 paysage
    PAGE_W, PAGE_H = landscape(A1)

    c = rl_canvas.Canvas(output_path, pagesize=(PAGE_W, PAGE_H))

    # Fond
    c.setFillColor(HexColor("#F8FAF8"))
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # Extraction données
    nom = projet_data.get("nom", "Projet")
    nb_niveaux = projet_data.get("geometrie", {}).get("nb_niveaux", 5)
    surface = projet_data.get("geometrie", {}).get("surface_emprise_m2", 500)
    portee = projet_data.get("geometrie", {}).get("portee_max_m", 6.0)
    hauteur_etage = projet_data.get("geometrie", {}).get("hauteur_etage_m", 3.0)
    ville = projet_data.get("localisation", {}).get("ville", "dakar")
    resume = resultat_data.get("resume", {})
    poteau_section = resume.get("poteau_section", "25×25 cm")
    poutre_section = resume.get("poutre_section", "25×50 cm")
    dalle_ep = resume.get("dalle_epaisseur", "20 cm")
    voile_ep = resume.get("voile_epaisseur", "20 cm")
    fondations_type = resume.get("fondations_type", "Radier général")
    beton = resume.get("beton", "C30/37")
    poteau_ferraillage = resume.get("poteau_ferraillage", "4HA12")

    MARGIN = 20 * mm
    date_str = datetime.now().strftime("%d/%m/%Y")

    # ── CARTOUCHE ────────────────────────────────────────────
    cart_h = 28 * mm
    cart_y = MARGIN
    cart_x = MARGIN
    cart_w = PAGE_W - 2 * MARGIN

    # Fond cartouche
    c.setFillColor(VERT_FONCE)
    c.rect(cart_x, cart_y, cart_w, cart_h, fill=1, stroke=0)

    # Logo zone
    c.setFillColor(HexColor("#1A5C3A"))
    c.rect(cart_x, cart_y, 45*mm, cart_h, fill=1, stroke=0)
    c.setFillColor(BLANC)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(cart_x + 22.5*mm, cart_y + 18*mm, "TIJAN AI")
    c.setFont("Helvetica", 7)
    c.setFillColor(VERT_CLAIR)
    c.drawCentredString(cart_x + 22.5*mm, cart_y + 12*mm, "Engineering Intelligence")
    c.drawCentredString(cart_x + 22.5*mm, cart_y + 8*mm, "for Africa")

    # Infos projet
    c.setFillColor(VERT_PALE)
    c.setFont("Helvetica", 7)
    c.drawString(cart_x + 48*mm, cart_y + 22*mm, "PROJET")
    c.setFillColor(BLANC)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(cart_x + 48*mm, cart_y + 16*mm, nom)
    c.setFont("Helvetica", 8)
    c.setFillColor(VERT_CLAIR)
    c.drawString(cart_x + 48*mm, cart_y + 11*mm, f"R+{nb_niveaux} — {surface} m² — {ville.upper()}")
    c.drawString(cart_x + 48*mm, cart_y + 6*mm, f"{beton} — {fondations_type}")

    # Titre plan
    c.setFillColor(BLANC)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(cart_x + cart_w * 0.5, cart_y + 20*mm, "PLAN D'EXÉCUTION STRUCTUREL")
    c.setFont("Helvetica", 9)
    c.setFillColor(VERT_PALE)
    c.drawCentredString(cart_x + cart_w * 0.5, cart_y + 14*mm, "Vue en plan RDC + Coupe longitudinale A-A")
    c.setFont("Helvetica", 7)
    c.setFillColor(VERT_CLAIR)
    c.drawCentredString(cart_x + cart_w * 0.5, cart_y + 9*mm, "EN 1990 / EN 1992-1-1 / EN 1997-1")

    # Specs techniques
    specs_x = cart_x + cart_w * 0.72
    c.setFillColor(VERT_PALE)
    c.setFont("Helvetica", 7)
    specs = [
        (f"BÉTON : {beton}", f"POTEAUX : {poteau_section}"),
        (f"POUTRES : {poutre_section}", f"DALLE : {dalle_ep}"),
    ]
    for k, (s1, s2) in enumerate(specs):
        y_pos = cart_y + cart_h - 8*mm - k*8*mm
        c.drawString(specs_x, y_pos, s1)
        c.drawString(specs_x + 40*mm, y_pos, s2)

    # Date/échelle
    meta_x = cart_x + cart_w * 0.88
    c.setFillColor(BLANC)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(meta_x, cart_y + 22*mm, f"DATE : {date_str}")
    c.drawString(meta_x, cart_y + 16*mm, "ÉCHELLE : 1/100")
    c.drawString(meta_x, cart_y + 10*mm, "FORMAT : A1 Paysage")
    c.drawString(meta_x, cart_y + 4*mm, "FOLIO : 01/01")

    # Avertissement
    c.setFillColor(VERT_CLAIR)
    c.setFont("Helvetica-Oblique", 6)
    c.drawCentredString(PAGE_W/2, cart_y - 4*mm, "Document d'assistance à l'ingénierie — Doit être vérifié et signé par un ingénieur habilité avant toute utilisation réglementaire")

    # ── ZONES DE DESSIN ───────────────────────────────────────
    draw_y_top = cart_y + cart_h + 8*mm
    draw_h = PAGE_H - draw_y_top - MARGIN

    # Zone plan (gauche ~55%)
    plan_zone_w = (PAGE_W - 2*MARGIN) * 0.54
    plan_zone_x = MARGIN
    plan_zone_y = draw_y_top

    # Zone coupe (droite ~45%)
    coupe_zone_x = MARGIN + plan_zone_w + 10*mm
    coupe_zone_w = PAGE_W - MARGIN - coupe_zone_x
    coupe_zone_y = draw_y_top

    # Titres zones
    for (tx, tw, title) in [
        (plan_zone_x, plan_zone_w, "VUE EN PLAN — RDC (Niveau 0)"),
        (coupe_zone_x, coupe_zone_w, "COUPE A-A — Longitudinale"),
    ]:
        c.setFillColor(VERT_FONCE)
        c.rect(tx, PAGE_H - draw_y_top + MARGIN - 7*mm, tw, 6*mm, fill=1, stroke=0)
        c.setFillColor(BLANC)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(tx + tw/2, PAGE_H - draw_y_top + MARGIN - 4*mm, title)

    # ── DESSIN PLAN EN PLAN ───────────────────────────────────
    cote = math.sqrt(surface)
    nb_tx = max(2, round(cote / portee))
    nb_ty = max(2, round(cote / portee))
    nb_px = nb_tx + 1
    nb_py = nb_ty + 1

    margin_plan = 20*mm
    avail_w = plan_zone_w - 2*margin_plan
    avail_h = draw_h - 10*mm
    ech = min(avail_w / (nb_tx * portee), avail_h / (nb_ty * portee)) * 0.80

    gx = portee * ech
    gy = portee * ech
    ptw = nb_tx * gx
    pth = nb_ty * gy

    # Centrage dans zone
    off_x = plan_zone_x + margin_plan + (avail_w - ptw) / 2
    off_y = plan_zone_y + (draw_h - pth) / 2

    try:
        s_cm = float(poteau_section.split("×")[0].replace("cm","").strip())
    except:
        s_cm = 25.0
    p_px = max(4*mm, s_cm/100 * ech)

    try:
        ep_v_cm = float(voile_ep.replace("cm","").strip())
    except:
        ep_v_cm = 20.0
    v_px = max(3*mm, ep_v_cm/100 * ech)

    try:
        h_p_cm = float(poutre_section.split("×")[1].replace("cm","").strip())
    except:
        h_p_cm = 50.0
    pb_px = max(2*mm, h_p_cm/100 * ech * 0.35)

    # Fond dalle
    c.setFillColor(FOND_DALLE)
    c.setStrokeColor(VERT_FONCE)
    c.setLineWidth(1)
    c.rect(off_x, off_y, ptw, pth, fill=1, stroke=1)

    # Axes
    c.setStrokeColor(VERT_CLAIR)
    c.setLineWidth(0.3)
    c.setDash(4, 2)
    for i in range(nb_px):
        ax = off_x + i * gx
        c.line(ax, off_y - 15*mm, ax, off_y + pth + 8*mm)
        # Label axe
        c.setFillColor(VERT_FONCE)
        c.circle(ax, off_y + pth + 10*mm, 4*mm, fill=1, stroke=0)
        c.setFillColor(BLANC)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(ax, off_y + pth + 11.5*mm, chr(65+i))

    for j in range(nb_py):
        ay = off_y + j * gy
        c.line(off_x - 15*mm, ay, off_x + ptw + 5*mm, ay)
        c.setFillColor(VERT_FONCE)
        c.circle(off_x - 10*mm, ay, 4*mm, fill=1, stroke=0)
        c.setFillColor(BLANC)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(off_x - 10*mm, ay - 1.5*mm, str(nb_py - j))

    c.setDash()

    # Poutres
    c.setFillColor(POUTRE_COLOR)
    c.setStrokeColor(NOIR)
    c.setLineWidth(0.3)
    for i in range(nb_px):
        for j in range(nb_py):
            px_p = off_x + i * gx
            py_p = off_y + j * gy
            if i < nb_tx:
                c.rect(px_p, py_p - pb_px/2, gx, pb_px, fill=1, stroke=0)
            if j < nb_ty:
                c.rect(px_p - pb_px/2, py_p, pb_px, gy, fill=1, stroke=0)

    # Voiles
    c.setFillColor(VOILE_FILL)
    c.rect(off_x, off_y, ptw, v_px, fill=1, stroke=0)
    c.rect(off_x, off_y + pth - v_px, ptw, v_px, fill=1, stroke=0)
    c.rect(off_x, off_y, v_px, pth, fill=1, stroke=0)
    c.rect(off_x + ptw - v_px, off_y, v_px, pth, fill=1, stroke=0)
    # Refend
    c.setFillAlpha(0.7)
    mid = off_y + pth / 2
    c.rect(off_x + v_px, mid - v_px/2, ptw - 2*v_px, v_px, fill=1, stroke=0)
    c.setFillAlpha(1.0)

    # Poteaux
    c.setFillColor(POTEAU_FILL)
    c.setStrokeColor(HexColor("#1A3D2E"))
    c.setLineWidth(0.5)
    for i in range(nb_px):
        for j in range(nb_py):
            px_p = off_x + i * gx
            py_p = off_y + j * gy
            c.rect(px_p - p_px/2, py_p - p_px/2, p_px, p_px, fill=1, stroke=1)
            # Croix
            c.setStrokeColor(VERT_PALE)
            c.setLineWidth(0.3)
            c.line(px_p - p_px/2+1, py_p, px_p + p_px/2-1, py_p)
            c.line(px_p, py_p - p_px/2+1, px_p, py_p + p_px/2-1)
            c.setStrokeColor(HexColor("#1A3D2E"))
            c.setLineWidth(0.5)

    # Cotations plan
    c.setStrokeColor(VERT_FONCE)
    c.setFillColor(VERT_FONCE)
    c.setLineWidth(0.5)
    cot_y_pdf = off_y - 8*mm
    for i in range(nb_tx):
        x1 = off_x + i*gx
        x2 = off_x + (i+1)*gx
        xm = (x1+x2)/2
        c.line(x1+1, cot_y_pdf, x2-1, cot_y_pdf)
        c.setFont("Helvetica", 6)
        c.drawCentredString(xm, cot_y_pdf - 3*mm, f"{portee:.1f}m")

    # Total H
    c.setFont("Helvetica-Bold", 7)
    c.line(off_x, cot_y_pdf - 5*mm, off_x + ptw, cot_y_pdf - 5*mm)
    c.drawCentredString(off_x + ptw/2, cot_y_pdf - 8*mm, f"TOTAL = {nb_tx*portee:.1f} m")

    # Ligne coupe A-A
    coupe_pdf_y = off_y + pth / 2
    c.setStrokeColor(ACIER_COLOR)
    c.setLineWidth(1.2)
    c.setDash(6, 3)
    c.line(off_x - 5, coupe_pdf_y, off_x + ptw + 5, coupe_pdf_y)
    c.setDash()
    c.setFillColor(ACIER_COLOR)
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(off_x - 6, coupe_pdf_y + 2*mm, "A")
    c.drawString(off_x + ptw + 6, coupe_pdf_y + 2*mm, "A")

    # Nord
    nord_cx = off_x + ptw + 12*mm
    nord_cy = off_y + pth - 12*mm
    c.setStrokeColor(VERT_FONCE)
    c.setFillColor(VERT_FONCE)
    c.setLineWidth(1)
    c.circle(nord_cx, nord_cy, 7*mm, fill=0, stroke=1)
    from reportlab.lib.utils import simpleSplit
    c.triangle = None
    # Flèche nord simple
    c.setLineWidth(1.5)
    c.line(nord_cx, nord_cy - 5*mm, nord_cx, nord_cy + 6*mm)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(nord_cx, nord_cy + 8*mm, "N")

    # Légende plan
    leg_x_pdf = plan_zone_x + 5*mm
    leg_y_pdf = off_y - 22*mm
    c.setFillColor(BLANC)
    c.setStrokeColor(VERT_CLAIR)
    c.setLineWidth(0.5)
    c.rect(leg_x_pdf - 2*mm, leg_y_pdf - 2*mm, 80*mm, 18*mm, fill=1, stroke=1)
    leg_items = [
        (POTEAU_FILL, f"Poteau {poteau_section}"),
        (VOILE_FILL, f"Voile e={voile_ep}"),
        (POUTRE_COLOR, f"Poutre {poutre_section}"),
        (FOND_DALLE, f"Dalle e={dalle_ep}"),
    ]
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(VERT_FONCE)
    c.drawString(leg_x_pdf, leg_y_pdf + 13*mm, "LÉGENDE")
    for k, (col, label) in enumerate(leg_items):
        ix = leg_x_pdf + (k % 2) * 39*mm
        iy = leg_y_pdf + (1 - k//2) * 7*mm
        c.setFillColor(col)
        c.rect(ix, iy, 4*mm, 3*mm, fill=1, stroke=0)
        c.setFillColor(NOIR)
        c.setFont("Helvetica", 6)
        c.drawString(ix + 5*mm, iy + 1*mm, label)

    # ── DESSIN COUPE ─────────────────────────────────────────
    avail_coupe_w = coupe_zone_w - 30*mm
    avail_coupe_h = draw_h - 15*mm
    ht_tot = nb_niveaux * hauteur_etage + 1.5
    ech_c = min(avail_coupe_w / (nb_tx * portee), avail_coupe_h / ht_tot) * 0.75

    ctw = nb_tx * portee * ech_c
    cth = nb_niveaux * hauteur_etage * ech_c

    off_cx = coupe_zone_x + (coupe_zone_w - ctw) / 2 - 5*mm
    off_cy = draw_y_top + 8*mm

    h_eta_c = hauteur_etage * ech_c
    ep_dalle_c = max(2*mm, 0.20 * ech_c)
    try:
        s_c = float(poteau_section.split("×")[0].replace("cm","").strip())
    except:
        s_c = 25.0
    p_w_c = max(3*mm, s_c/100 * ech_c)
    try:
        ep_v_c = float(voile_ep.replace("cm","").strip())
    except:
        ep_v_c = 20.0
    v_w_c = max(2*mm, ep_v_c/100 * ech_c)
    try:
        h_p_c = float(poutre_section.split("×")[1].replace("cm","").strip())
    except:
        h_p_c = 50.0
    p_h_c = max(2*mm, h_p_c/100 * ech_c * 0.4)

    sol_pdf_y = off_cy + cth + 10*mm

    # Sol
    c.setStrokeColor(NOIR)
    c.setLineWidth(2)
    c.line(off_cx - 15*mm, sol_pdf_y, off_cx + ctw + 15*mm, sol_pdf_y)
    # Hachures sol
    c.setStrokeColor(HexColor("#888888"))
    c.setLineWidth(0.5)
    for hx in range(0, int((ctw + 30*mm)/mm), 8):
        bx = off_cx - 15*mm + hx*mm
        c.line(bx, sol_pdf_y, bx + 5*mm, sol_pdf_y - 5*mm)

    # Fondation radier
    c.setFillColor(VERT_FONCE)
    c.setStrokeColor(HexColor("#1A3D2E"))
    c.setLineWidth(0.5)
    rad_h = max(4*mm, 0.5 * ech_c)
    c.rect(off_cx - 8*mm, sol_pdf_y, ctw + 16*mm, rad_h, fill=1, stroke=1)
    c.setFillColor(VERT_PALE)
    c.setFont("Helvetica", 6)
    c.drawString(off_cx + ctw + 10*mm, sol_pdf_y + rad_h/2, "Radier e=0.9m")

    # Niveaux et éléments
    for n in range(nb_niveaux + 1):
        ny_c = sol_pdf_y - n * h_eta_c
        cote_c = n * hauteur_etage

        # Dalle
        if n > 0:
            c.setFillColor(VOILE_FILL)
            c.setLineWidth(0)
            c.rect(off_cx, ny_c, ctw, ep_dalle_c, fill=1, stroke=0)

        # Cotation niveau
        c.setStrokeColor(VERT_FONCE)
        c.setLineWidth(0.4)
        c.line(off_cx - 12*mm, ny_c, off_cx - 2, ny_c)
        c.setFillColor(VERT_FONCE)
        c.setFont("Helvetica-Bold", 6)
        c.drawRightString(off_cx - 13*mm, ny_c - 1*mm, f"+{cote_c:.2f}")

        # Poteaux
        if n < nb_niveaux:
            c.setFillColor(POTEAU_FILL)
            c.setStrokeColor(HexColor("#1A3D2E"))
            c.setLineWidth(0.4)
            for i in range(nb_px):
                px_c2 = off_cx + i * portee * ech_c
                c.rect(px_c2 - p_w_c/2, ny_c - h_eta_c, p_w_c, h_eta_c, fill=1, stroke=1)

        # Poutres
        if n > 0:
            c.setFillColor(POUTRE_COLOR)
            for i in range(nb_tx):
                px1_c = off_cx + i * portee * ech_c
                px2_c = off_cx + (i+1) * portee * ech_c
                c.rect(px1_c, ny_c - ep_dalle_c - p_h_c, px2_c - px1_c, p_h_c, fill=1, stroke=0)

    # Voiles façade coupe
    c.setFillColor(VOILE_FILL)
    c.setFillAlpha(0.85)
    c.rect(off_cx - v_w_c, sol_pdf_y - cth, v_w_c, cth, fill=1, stroke=0)
    c.rect(off_cx + ctw, sol_pdf_y - cth, v_w_c, cth, fill=1, stroke=0)
    c.setFillAlpha(1.0)

    # Cotation hauteur totale
    ht_line_x = off_cx + ctw + v_w_c + 12*mm
    c.setStrokeColor(VERT_FONCE)
    c.setLineWidth(0.8)
    c.line(ht_line_x, sol_pdf_y - cth, ht_line_x, sol_pdf_y)
    c.line(ht_line_x - 2*mm, sol_pdf_y - cth, ht_line_x + 2*mm, sol_pdf_y - cth)
    c.line(ht_line_x - 2*mm, sol_pdf_y, ht_line_x + 2*mm, sol_pdf_y)
    c.setFillColor(VERT_FONCE)
    c.setFont("Helvetica-Bold", 7)
    c.saveState()
    c.translate(ht_line_x + 5*mm, sol_pdf_y - cth/2)
    c.rotate(90)
    c.drawCentredString(0, 0, f"H total = {nb_niveaux*hauteur_etage:.1f} m")
    c.restoreState()

    # ── NOTES TECHNIQUES ─────────────────────────────────────
    notes_y = MARGIN + 5*mm
    c.setFillColor(BLANC)
    c.setStrokeColor(VERT_CLAIR)
    c.setLineWidth(0.5)
    c.rect(coupe_zone_x, notes_y, coupe_zone_w - 5*mm, 18*mm, fill=1, stroke=1)
    c.setFillColor(VERT_FONCE)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(coupe_zone_x + 2*mm, notes_y + 13*mm, "NOTES TECHNIQUES")
    notes_lines = [
        f"Béton : {beton} | Acier FeE500 fyk=500 MPa | Enrobage : {resume.get('enrobage','40 mm')}",
        f"Poteaux : {poteau_section} — {poteau_ferraillage} | Poutres : {poutre_section}",
        f"Fondations : {fondations_type} | Toutes sections vérifiées EN 1992-1-1",
    ]
    c.setFont("Helvetica", 6)
    c.setFillColor(NOIR)
    for k, nl in enumerate(notes_lines):
        c.drawString(coupe_zone_x + 2*mm, notes_y + 8*mm - k*4*mm, nl)

    c.save()
    return output_path


# ============================================================
# FONCTION PRINCIPALE
# ============================================================

def generer_plan_structurel(projet_data: dict, resultat_data: dict) -> dict:
    """
    Génère le plan structurel SVG + PDF
    Returns dict avec paths des fichiers générés
    """
    nom = projet_data.get("nom", "projet").replace(" ", "_")
    tmp_dir = tempfile.gettempdir()

    # SVG
    svg_path = os.path.join(tmp_dir, f"plan_structure_{nom}.svg")
    svg_content = generer_svg_plan(projet_data, resultat_data)
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg_content)

    # PDF
    pdf_path = os.path.join(tmp_dir, f"plan_structure_{nom}.pdf")
    generer_pdf_plan(projet_data, resultat_data, pdf_path)

    return {
        "svg_path": svg_path,
        "pdf_path": pdf_path,
        "svg_content": svg_content,
    }


# ── TEST LOCAL ──────────────────────────────────────────────
if __name__ == "__main__":
    projet_test = {
        "nom": "Tour Dakar R+12",
        "geometrie": {
            "surface_emprise_m2": 766,
            "nb_niveaux": 12,
            "hauteur_etage_m": 3.0,
            "portee_max_m": 6.0,
        },
        "localisation": {"ville": "dakar", "distance_mer_km": 0.2},
    }
    resultat_test = {
        "resume": {
            "beton": "C30/... — Exposition XS1",
            "enrobage": "40 mm",
            "poteau_section": "35×35 cm",
            "poteau_ferraillage": "10HA12 (11.3 cm²)",
            "poutre_section": "30×60 cm",
            "dalle_epaisseur": "20 cm",
            "voile_epaisseur": "20 cm",
            "fondations_type": "Radier général",
        }
    }
    result = generer_plan_structurel(projet_test, resultat_test)
    print(f"SVG : {result['svg_path']}")
    print(f"PDF : {result['pdf_path']}")
    print("OK ✓")
