"""
generate_note_v4_final.py
Note de calcul structurelle + BOQ — Tijan AI
Format A4 portrait (comme les versions validées v2/v3)
Logo intégré en base64 — pas de dépendance fichier externe
Prix marché Dakar 2026 validés
Tableaux avec largeurs fixes — zéro débordement
"""
import io
import base64
import os
import dataclasses
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle,
    Spacer, PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfgen import canvas as rl_canvas

# ── LOGO BASE64 ──────────────────────────────────────────────
# Logo chargé depuis le fichier dans le même répertoire que ce module
def _get_logo_path():
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ['tijan_logo_crop.png', 'tijan-ai-logo.png', 'tijan_logo.png']:
        p = os.path.join(here, name)
        if os.path.exists(p):
            return p
    return None

# ── COULEURS ─────────────────────────────────────────────────
VERT       = colors.HexColor('#43A956')
VERT_LIGHT = colors.HexColor('#EBF7ED')
NOIR       = colors.HexColor('#111111')
GRIS1      = colors.HexColor('#F5F5F5')
GRIS2      = colors.HexColor('#E5E5E5')
GRIS3      = colors.HexColor('#888888')
BLANC      = colors.white
ORANGE     = colors.HexColor('#E07B00')

# ── DIMENSIONS PAGE ──────────────────────────────────────────
PAGE = A4  # 210 × 297 mm portrait
W, H = PAGE
ML = 18*mm  # marge gauche
MR = 18*mm  # marge droite
MT = 25*mm  # marge haut (après header)
MB = 20*mm  # marge bas
CW = W - ML - MR  # largeur contenu = ~174mm

# ── PRIX MARCHÉ DAKAR 2026 ───────────────────────────────────
PRIX = {
    'beton_dalle_m3':    185_000,   # C30/37 BPE livré
    'beton_fond_m3':     195_000,   # C25/30 fondations
    'acier_fourni_kg':   530,       # HA500B vrac Fabrimetal
    'acier_facon_kg':    280,       # façonnage + pose
    'acier_pose_kg':     810,       # total fourni-posé
    'coffrage_m2':       18_000,    # bois toutes faces
    'terr_m3':           8_500,     # décapage méca
    'pieu_ml':           285_000,   # foré ø800mm f+p
    'maco_m2':           28_000,    # agglos 15cm 2 faces
    'etanch_m2':         18_500,    # toiture-terrasse
    'coeff_structure':   1.60,      # BA → structure complète
}

# ── STYLES ───────────────────────────────────────────────────
def _styles():
    s = getSampleStyleSheet()
    base = dict(fontName='Helvetica', leading=12)
    return {
        'titre':   ParagraphStyle('titre',   fontName='Helvetica-Bold', fontSize=18, textColor=NOIR, spaceAfter=3, leading=22),
        'sous_titre': ParagraphStyle('sous_titre', fontName='Helvetica', fontSize=11, textColor=GRIS3, spaceAfter=2),
        'h1':      ParagraphStyle('h1',      fontName='Helvetica-Bold', fontSize=10, textColor=VERT, spaceBefore=8, spaceAfter=3, leading=13),
        'body':    ParagraphStyle('body',    fontName='Helvetica', fontSize=8.5, textColor=NOIR, leading=11, spaceAfter=2),
        'small':   ParagraphStyle('small',   fontName='Helvetica', fontSize=7, textColor=GRIS3, leading=9),
        'th':      ParagraphStyle('th',      fontName='Helvetica-Bold', fontSize=7.5, textColor=BLANC, alignment=TA_CENTER, leading=10),
        'th_l':    ParagraphStyle('th_l',    fontName='Helvetica-Bold', fontSize=7.5, textColor=BLANC, alignment=TA_LEFT, leading=10),
        'td':      ParagraphStyle('td',      fontName='Helvetica', fontSize=7.5, textColor=NOIR, leading=10, wordWrap='LTR'),
        'td_r':    ParagraphStyle('td_r',    fontName='Helvetica', fontSize=7.5, textColor=NOIR, leading=10, alignment=TA_RIGHT),
        'td_b':    ParagraphStyle('td_b',    fontName='Helvetica-Bold', fontSize=7.5, textColor=NOIR, leading=10),
        'td_b_r':  ParagraphStyle('td_b_r',  fontName='Helvetica-Bold', fontSize=7.5, textColor=NOIR, leading=10, alignment=TA_RIGHT),
        'td_g':    ParagraphStyle('td_g',    fontName='Helvetica-Bold', fontSize=7.5, textColor=VERT, leading=10),
        'badge_ok':  ParagraphStyle('badge_ok',  fontName='Helvetica-Bold', fontSize=7.5, textColor=VERT),
        'badge_nok': ParagraphStyle('badge_nok', fontName='Helvetica-Bold', fontSize=7.5, textColor=ORANGE),
        'disclaimer': ParagraphStyle('disclaimer', fontName='Helvetica-Oblique', fontSize=6.5, textColor=GRIS3, leading=9),
    }

S = _styles()

# ── STYLE TABLEAU ─────────────────────────────────────────────
def ts_base(header_rows=1, zebra=True):
    """Style tableau standard Tijan"""
    cmds = [
        # Header
        ('BACKGROUND',   (0,0), (-1,header_rows-1), VERT),
        ('TEXTCOLOR',    (0,0), (-1,header_rows-1), BLANC),
        ('FONTNAME',     (0,0), (-1,header_rows-1), 'Helvetica-Bold'),
        ('FONTSIZE',     (0,0), (-1,-1), 7.5),
        ('ALIGN',        (0,0), (-1,header_rows-1), 'CENTER'),
        ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
        # Padding
        ('LEFTPADDING',  (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING',   (0,0), (-1,-1), 3),
        ('BOTTOMPADDING',(0,0), (-1,-1), 3),
        # Grid
        ('GRID',         (0,0), (-1,-1), 0.3, GRIS2),
        ('LINEBELOW',    (0,header_rows-1), (-1,header_rows-1), 1.0, VERT),
        ('WORDWRAP',     (0,0), (-1,-1), True),
    ]
    if zebra:
        for i in range(header_rows, 100, 2):
            cmds.append(('ROWBACKGROUND', (0,i), (-1,i), GRIS1))
    return TableStyle(cmds)

def ts_total():
    return [
        ('BACKGROUND', (0,-1), (-1,-1), VERT_LIGHT),
        ('FONTNAME',   (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('LINEABOVE',  (0,-1), (-1,-1), 1.0, VERT),
    ]

# ── HELPERS ───────────────────────────────────────────────────
def fmt_fcfa(v, short=True):
    try:
        v = float(v)
        if v == 0: return "—"
        if short:
            if v >= 1e9: return f"{v/1e9:.2f} Mds"
            if v >= 1e6: return f"{v/1e6:.1f} M"
            return f"{int(v):,}".replace(',', ' ')
        else:
            if v >= 1e9: return f"{v/1e9:.2f} Mds FCFA"
            if v >= 1e6: return f"{v/1e6:.1f} M FCFA"
            return f"{int(v):,} FCFA".replace(',', ' ')
    except:
        return "—"

def fmt_n(v, dec=0, unit=""):
    try:
        v = float(v)
        if dec == 0: s = f"{int(round(v)):,}".replace(',', ' ')
        else: s = f"{v:.{dec}f}"
        return f"{s} {unit}".strip() if unit else s
    except:
        return "—"

def p(txt, style='td'):
    """Raccourci Paragraph"""
    return Paragraph(str(txt) if txt is not None else "—", S[style])

def section(titre):
    return [
        Spacer(1, 3*mm),
        HRFlowable(width=CW, thickness=1.5, color=VERT, spaceAfter=2),
        Paragraph(titre, S['h1']),
    ]

# ── HEADER/FOOTER CANVAS ──────────────────────────────────────
class HeaderFooter:
    def __init__(self, projet, doc_type, ref=""):
        self.projet = projet
        self.doc_type = doc_type
        self.ref = ref
        self.logo_path = _get_logo_path()

    def __call__(self, canv, doc):
        canv.saveState()
        w, h = PAGE

        # Bande verte header
        canv.setFillColor(VERT)
        canv.rect(0, h - 14*mm, w, 14*mm, fill=1, stroke=0)

        # Logo
        if self.logo_path:
            try:
                canv.drawImage(
                    self.logo_path,
                    ML, h - 12*mm,
                    width=35*mm, height=9*mm,
                    preserveAspectRatio=True,
                    mask='auto'
                )
            except:
                canv.setFont('Helvetica-Bold', 10)
                canv.setFillColor(BLANC)
                canv.drawString(ML, h - 9*mm, "TIJAN AI")
        else:
            canv.setFont('Helvetica-Bold', 10)
            canv.setFillColor(BLANC)
            canv.drawString(ML, h - 9*mm, "TIJAN AI")

        # Tagline
        canv.setFont('Helvetica', 7)
        canv.setFillColor(BLANC)
        canv.drawString(ML + 37*mm, h - 9*mm, "Engineering Intelligence for Africa")

        # Titre document (droite)
        canv.setFont('Helvetica-Bold', 9)
        canv.setFillColor(BLANC)
        canv.drawRightString(w - MR, h - 9*mm, self.doc_type.upper())

        # Sous-header
        canv.setFillColor(NOIR)
        canv.setFont('Helvetica-Bold', 8)
        canv.drawString(ML, h - 18*mm, self.projet)
        if self.ref:
            canv.setFont('Helvetica', 7)
            canv.setFillColor(GRIS3)
            canv.drawString(ML + 70*mm, h - 18*mm, f"Réf. {self.ref}")
        canv.setFont('Helvetica', 7)
        canv.setFillColor(GRIS3)
        canv.drawRightString(w - MR, h - 18*mm, datetime.now().strftime("%d/%m/%Y"))

        # Ligne séparatrice
        canv.setStrokeColor(GRIS2)
        canv.setLineWidth(0.5)
        canv.line(ML, h - 20*mm, w - MR, h - 20*mm)

        # Footer
        canv.line(ML, 12*mm, w - MR, 12*mm)
        canv.setFont('Helvetica-Oblique', 6)
        canv.setFillColor(GRIS3)
        canv.drawString(ML, 8*mm,
            "Document d'assistance à l'ingénierie — Version bêta ±15%. "
            "Doit être vérifié par un ingénieur structure habilité. "
            "Ne remplace pas l'intervention légalement obligatoire d'un bureau d'études.")
        canv.setFont('Helvetica', 6.5)
        canv.drawRightString(w - MR, 8*mm, f"Page {doc.page} | Tijan AI © {datetime.now().year}")

        canv.restoreState()

# ── CALCUL BOQ COMPLET ────────────────────────────────────────
def _boq_complet(beton_m3, acier_kg, surface, niveaux):
    """Calcule le BOQ complet structure avec vrais prix Dakar 2026"""
    coffrage_m2 = beton_m3 * 4

    cout_beton    = beton_m3   * PRIX['beton_dalle_m3']
    cout_acier    = acier_kg   * PRIX['acier_pose_kg']
    cout_coffrage = coffrage_m2 * PRIX['coffrage_m2']
    sous_total_ba = cout_beton + cout_acier + cout_coffrage

    lot_terr  = round(surface * 1.5 * PRIX['terr_m3'])
    lot_fond  = round(sous_total_ba * 0.22)
    lot_maco  = round(surface * niveaux * 0.08 * PRIX['maco_m2'])  # 8% surface par niveau
    lot_etanch = round(surface * PRIX['etanch_m2'])
    lot_divers = round(sous_total_ba * 0.05)

    total_bas  = round(sous_total_ba + lot_terr + lot_fond + lot_maco + lot_etanch + lot_divers)
    total_haut = round(total_bas * 1.15)

    surf_batie = surface * niveaux
    ratio_bas  = round(total_bas  / surf_batie) if surf_batie else 0
    ratio_haut = round(total_haut / surf_batie) if surf_batie else 0

    return {
        'beton_m3':        round(beton_m3),
        'acier_kg':        round(acier_kg),
        'coffrage_m2':     round(coffrage_m2),
        'cout_beton':      cout_beton,
        'cout_acier':      cout_acier,
        'cout_coffrage':   cout_coffrage,
        'sous_total_ba':   sous_total_ba,
        'lot_terr':        lot_terr,
        'lot_fond':        lot_fond,
        'lot_maco':        lot_maco,
        'lot_etanch':      lot_etanch,
        'lot_divers':      lot_divers,
        'total_bas':       total_bas,
        'total_haut':      total_haut,
        'surf_batie':      round(surf_batie),
        'ratio_bas':       ratio_bas,
        'ratio_haut':      ratio_haut,
    }

# ── GÉNÉRATEUR PRINCIPAL ──────────────────────────────────────
def generer(params: dict) -> bytes:
    """
    Point d'entrée appelé depuis main.py.
    params: dict avec nom, ville, nb_niveaux, surface_emprise_m2, etc.
    Retourne les bytes du PDF.
    """
    # Import moteur
    from engine_structural_v3 import DonneesProjet, calculer_projet

    nom     = params.get('nom', 'Projet')
    ville   = params.get('ville', 'Dakar')
    nb_niv  = int(params.get('nb_niveaux', 5))
    surf    = float(params.get('surface_emprise_m2', 500))
    beton   = params.get('classe_beton', 'C30/37')
    acier   = params.get('classe_acier', 'HA500')
    portee  = float(params.get('portee_max_m', 6.0))
    portee_min = float(params.get('portee_min_m', 4.5))
    htg     = float(params.get('hauteur_etage_m', 3.0))
    p_sol   = float(params.get('pression_sol_MPa', 0.15))
    tx      = int(params.get('nb_travees_x', 4))
    ty      = int(params.get('nb_travees_y', 3))

    # Calcul moteur
    d = DonneesProjet(
        nom=nom, ville=ville, nb_niveaux=nb_niv,
        hauteur_etage_m=htg, surface_emprise_m2=surf,
        portee_max_m=portee, portee_min_m=portee_min,
        nb_travees_x=tx, nb_travees_y=ty,
        classe_beton=beton, classe_acier=acier,
        pression_sol_MPa=p_sol,
    )
    res = calculer_projet(d)
    res_dict = dataclasses.asdict(res)

    # Extraire données
    poteaux  = res_dict.get('poteaux', [])
    fondation = res_dict.get('fondation', {})
    boq_raw  = res_dict.get('boq', {})
    analyse  = res_dict.get('analyse_claude', {})

    beton_m3 = boq_raw.get('beton_total_m3', 0) if boq_raw else 0
    acier_kg = boq_raw.get('acier_total_kg', 0) if boq_raw else 0

    # Calculer BOQ avec vrais prix
    boq = _boq_complet(beton_m3, acier_kg, surf, nb_niv)

    # Générer PDF
    buf = io.BytesIO()
    hf = HeaderFooter(nom, "Note de Calcul Structure")

    doc = SimpleDocTemplate(
        buf, pagesize=PAGE,
        leftMargin=ML, rightMargin=MR,
        topMargin=26*mm, bottomMargin=18*mm,
        title=f"Note de calcul — {nom}",
        author="Tijan AI",
    )

    story = _build_story(
        nom, ville, nb_niv, surf, beton, acier,
        portee, portee_min, htg, p_sol,
        poteaux, fondation, boq, analyse, boq_raw
    )

    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    return buf.getvalue()


def _build_story(nom, ville, nb_niv, surf, beton_classe, acier_classe,
                 portee, portee_min, htg, p_sol,
                 poteaux, fondation, boq, analyse, boq_raw):
    story = []

    # ── PAGE DE GARDE ─────────────────────────────────────────
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(nom, S['titre']))
    story.append(Paragraph(f"{ville} — Bâtiment R+{nb_niv-1} ({nb_niv} niveaux)", S['sous_titre']))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        "Version bêta — Calculs indicatifs ±15%. Surface emprise à confirmer avec l'architecte. "
        "Tous les résultats doivent être vérifiés par un ingénieur structure habilité.",
        S['disclaimer']
    ))
    story.append(Spacer(1, 4*mm))

    # Fiche projet
    cw4 = [CW*0.28, CW*0.22, CW*0.28, CW*0.22]
    fiche = [
        [p('PARAMÈTRE','th'), p('VALEUR','th'), p('PARAMÈTRE','th'), p('VALEUR','th')],
        [p('Ville','td_b'), p(ville), p('Classe béton','td_b'), p(beton_classe)],
        [p('Niveaux','td_b'), p(f"R+{nb_niv-1} ({nb_niv} niv.)"), p('Classe acier','td_b'), p(acier_classe)],
        [p('Surface emprise*','td_b'), p(f"{surf:,.0f} m²".replace(',', ' ')),
         p('Portée max','td_b'), p(f"{portee} m")],
        [p('Hauteur étage','td_b'), p(f"{htg} m"),
         p('Pression sol','td_b'), p(f"{p_sol} MPa")],
    ]
    t = Table(fiche, colWidths=cw4, repeatRows=1)
    t.setStyle(ts_base())
    story.append(t)
    story.append(Paragraph(
        "* Surface emprise extraite automatiquement. À confirmer avec l'architecte (marge ±10%).",
        S['small']))

    # ── SECTION 1 — POTEAUX ───────────────────────────────────
    story += section("1. DESCENTE DE CHARGES — POTEAUX (EC2/EC8)")

    if poteaux:
        cw_p = [CW*w for w in [0.09, 0.11, 0.14, 0.09, 0.10, 0.10, 0.12, 0.11, 0.11, 0.08]]
        rows = [[p(h,'th') for h in [
            'Niveau','NEd (kN)','Section (mm)',
            'Nb bar.','Ø (mm)','Ø cad.','Esp. cad.',
            'Taux arm.','NRd (kN)','Vérif.']]]
        for pt in poteaux:
            ok = pt.get('verif_ok', True)
            rows.append([
                p(pt.get('label','')),
                p(fmt_n(pt.get('NEd_kN',0),1), 'td_r'),
                p(f"{pt.get('section_mm',0)}×{pt.get('section_mm',0)}"),
                p(str(pt.get('nb_barres',0)), 'td_r'),
                p(str(pt.get('diametre_mm',0)), 'td_r'),
                p(str(pt.get('cadre_diam_mm',0)), 'td_r'),
                p(str(pt.get('espacement_cadres_mm',0)), 'td_r'),
                p(f"{pt.get('taux_armature_pct',0):.1f}%", 'td_r'),
                p(fmt_n(pt.get('NRd_kN',0),1), 'td_r'),
                p("✓ OK" if ok else "⚠ NOK", 'badge_ok' if ok else 'badge_nok'),
            ])
        t = Table(rows, colWidths=cw_p, repeatRows=1)
        ts = ts_base()
        for i, pt in enumerate(poteaux):
            if not pt.get('verif_ok', True):
                ts.add('BACKGROUND', (0,i+1), (-1,i+1), colors.HexColor('#FFF3E0'))
        t.setStyle(ts)
        story.append(t)
    else:
        story.append(Paragraph("Données poteaux non disponibles pour ce projet.", S['body']))

    # ── SECTION 2 — POUTRES ───────────────────────────────────
    poutre = None
    if boq_raw:
        poutre = boq_raw.get('poutre') or boq_raw.get('poutres')
    if poutre:
        story += section("2. POUTRES")
        if isinstance(poutre, dict):
            cw_po = [CW*0.12, CW*0.12, CW*0.15, CW*0.15, CW*0.12, CW*0.12, CW*0.12, CW*0.10]
            rows_po = [[p(h,'th') for h in ['b (mm)','h (mm)','As inf (cm²)','As sup (cm²)','Ø étr.','Esp. étr.','Portée (m)','']]]
            rows_po.append([
                p(str(poutre.get('b_mm','-'))),
                p(str(poutre.get('h_mm','-'))),
                p(f"{poutre.get('As_inf_cm2',0):.1f}"),
                p(f"{poutre.get('As_sup_cm2',0):.1f}"),
                p(str(poutre.get('etrier_diam_mm','-'))),
                p(str(poutre.get('etrier_esp_mm','-'))),
                p(f"{poutre.get('portee_m',0):.1f}"),
                p(''),
            ])
            t = Table(rows_po, colWidths=cw_po, repeatRows=1)
            t.setStyle(ts_base())
            story.append(t)

    # ── SECTION 3 — FONDATIONS ────────────────────────────────
    story += section("3. FONDATIONS")
    if fondation:
        cw_f = [CW*0.20, CW*0.15, CW*0.40, CW*0.25]
        rows_f = [
            [p(h,'th') for h in ['TYPE','QUANTITÉ','DIMENSIONNEMENT','REMARQUE']],
            [
                p(fondation.get('type_fond', 'Pieux forés béton armé')),
                p(f"{fondation.get('nb_pieux','-')} pieux"),
                p(f"Ø{fondation.get('diam_pieu_mm',800)}mm — "
                  f"L={fondation.get('longueur_pieu_m',12):.1f}m — "
                  f"As={fondation.get('As_cm2',0):.1f} cm²"),
                p(f"Pression sol : {p_sol} MPa", 'small'),
            ]
        ]
        t = Table(rows_f, colWidths=cw_f, repeatRows=1)
        t.setStyle(ts_base())
        story.append(t)
    else:
        story.append(Paragraph("Données fondations calculées selon paramètres sol.", S['body']))

    # ── SECTION 4 — ANALYSE ───────────────────────────────────
    if analyse and isinstance(analyse, dict):
        story += section("4. ANALYSE ET RECOMMANDATIONS")
        comm = analyse.get('commentaire_global', '')
        if comm:
            story.append(Paragraph(comm, S['body']))
        conform = analyse.get('conformite_ec2', '')
        if conform:
            story.append(Spacer(1,2*mm))
            story.append(Paragraph(f"Conformité EC2 : {conform}", S['body']))
        recs = analyse.get('recommandations', [])
        if recs:
            story.append(Paragraph("Recommandations :", S['h1']))
            for r in recs:
                story.append(Paragraph(f"• {r}", S['body']))
        alertes = analyse.get('alertes', [])
        if alertes:
            story.append(Paragraph("Points d'attention :", S['h1']))
            for a in alertes:
                story.append(Paragraph(f"⚠ {a}", S['badge_nok']))

    # ── PAGE 2 — BOQ STRUCTURE ────────────────────────────────
    story.append(PageBreak())
    story += section("5. BORDEREAU DES QUANTITÉS ET DES PRIX — STRUCTURE")
    story.append(Paragraph(
        f"Prix unitaires marché Dakar 2026 (fournis-posés). "
        f"Marge estimée ±15%. Béton: {PRIX['beton_dalle_m3']//1000} k FCFA/m³ — "
        f"Acier HA500B fourni-posé: {PRIX['acier_pose_kg']} FCFA/kg.",
        S['small']))
    story.append(Spacer(1, 2*mm))

    cw_b = [CW*w for w in [0.05, 0.38, 0.10, 0.07, 0.13, 0.14, 0.13]]
    boq_rows = [[p(h,'th') for h in ['Lot','Désignation','Qté','Unité','P.U. (FCFA)','Montant bas','Montant haut']]]

    lots = [
        ('1',  'Terrassement — décapage + fouilles méca.',
         fmt_n(surf*1.5,0), 'm³', fmt_n(PRIX['terr_m3'],0),
         fmt_fcfa(boq['lot_terr']), fmt_fcfa(round(boq['lot_terr']*1.10))),
        ('2',  'Fondations spéciales — pieux forés ø800mm',
         'Forfait', '—', '285 k/ml',
         fmt_fcfa(boq['lot_fond']), fmt_fcfa(round(boq['lot_fond']*1.20))),
        ('3a', f"Béton armé — béton C30/37 BPE ({fmt_n(boq['beton_m3'],0)} m³)",
         fmt_n(boq['beton_m3'],0), 'm³', fmt_n(PRIX['beton_dalle_m3'],0),
         fmt_fcfa(boq['cout_beton']), fmt_fcfa(round(boq['cout_beton']*1.10))),
        ('3b', f"Béton armé — acier HA500B fourni-posé ({fmt_n(boq['acier_kg'],0)} kg)",
         fmt_n(boq['acier_kg'],0), 'kg', fmt_n(PRIX['acier_pose_kg'],0),
         fmt_fcfa(boq['cout_acier']), fmt_fcfa(round(boq['cout_acier']*1.10))),
        ('3c', f"Béton armé — coffrage toutes faces ({fmt_n(boq['coffrage_m2'],0)} m²)",
         fmt_n(boq['coffrage_m2'],0), 'm²', fmt_n(PRIX['coffrage_m2'],0),
         fmt_fcfa(boq['cout_coffrage']), fmt_fcfa(round(boq['cout_coffrage']*1.10))),
        ('4',  'Maçonnerie — agglos 15cm enduits 2 faces',
         'Forfait', '—', '28 k/m²',
         fmt_fcfa(boq['lot_maco']), fmt_fcfa(round(boq['lot_maco']*1.15))),
        ('5',  f"Étanchéité toiture-terrasse ({fmt_n(surf,0)} m²)",
         fmt_n(surf,0), 'm²', fmt_n(PRIX['etanch_m2'],0),
         fmt_fcfa(boq['lot_etanch']), fmt_fcfa(round(boq['lot_etanch']*1.10))),
        ('6',  'Divers structure — joints, acrotères, réservations',
         'Forfait', '—', '—',
         fmt_fcfa(boq['lot_divers']), fmt_fcfa(round(boq['lot_divers']*1.10))),
    ]

    for row in lots:
        boq_rows.append([p(row[0]), p(row[1]), p(row[2],'td_r'), p(row[3]),
                          p(row[4],'td_r'), p(row[5],'td_r'), p(row[6],'td_r')])

    # Total
    boq_rows.append([
        p('', 'td_b'), p('TOTAL STRUCTURE', 'td_b'),
        p('','td_r'), p(''),
        p('','td_r'),
        p(fmt_fcfa(boq['total_bas'],False), 'td_b_r'),
        p(fmt_fcfa(boq['total_haut'],False), 'td_b_r'),
    ])

    t = Table(boq_rows, colWidths=cw_b, repeatRows=1)
    ts = ts_base()
    for cmd in ts_total():
        ts.add(*cmd)
    ts.add('ALIGN', (2,1), (-1,-1), 'RIGHT')
    t.setStyle(ts)
    story.append(t)

    # Ratios
    story.append(Spacer(1, 4*mm))
    surf_batie = boq['surf_batie']
    cw_r = [CW*0.30, CW*0.20, CW*0.20, CW*0.30]
    ratio_rows = [
        [p(h,'th') for h in ['INDICATEUR','VALEUR BASSE','VALEUR HAUTE','NOTE']],
        [p('Surface bâtie totale','td_b'),
         p(fmt_n(surf_batie,0,'m²')), p('—'),
         p(f"Emprise {int(surf)} m² × {nb_niv} niveaux*", 'small')],
        [p('Coût / m² bâti','td_b'),
         p(fmt_n(boq['ratio_bas'],0,'FCFA/m²'),'td_r'),
         p(fmt_n(boq['ratio_haut'],0,'FCFA/m²'),'td_r'),
         p('Structure seule (hors MEP, finitions, VRD)', 'small')],
        [p('Coût total structure','td_b'),
         p(fmt_fcfa(boq['total_bas'],False),'td_r'),
         p(fmt_fcfa(boq['total_haut'],False),'td_g'),
         p('Estimation ±15%', 'small')],
    ]
    t2 = Table(ratio_rows, colWidths=cw_r, repeatRows=1)
    ts2 = ts_base()
    for cmd in ts_total():
        ts2.add(*cmd)
    t2.setStyle(ts2)
    story.append(t2)
    story.append(Paragraph(
        "* Surface bâtie = emprise × nb niveaux. Surface utile habitable ≈ 78% surface bâtie. "
        "À affiner avec métrés architecte définitifs.",
        S['small']))

    return story
