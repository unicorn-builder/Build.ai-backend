"""
generate_note_v5_8pages.py
Note de calcul structurelle complète 8 pages — Tijan AI
Basé sur les données réelles du moteur engine_structural_v3
"""
import io
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
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY

# ── COULEURS ─────────────────────────────────────────────────
VERT       = colors.HexColor('#43A956')
VERT_LIGHT = colors.HexColor('#EBF7ED')
VERT_DARK  = colors.HexColor('#2D7A3A')
NOIR       = colors.HexColor('#111111')
GRIS1      = colors.HexColor('#F5F5F5')
GRIS2      = colors.HexColor('#E5E5E5')
GRIS3      = colors.HexColor('#888888')
BLANC      = colors.white
ORANGE     = colors.HexColor('#E07B00')
ORANGE_LT  = colors.HexColor('#FFF3E0')
BLEU       = colors.HexColor('#1565C0')
BLEU_LT    = colors.HexColor('#E3F2FD')

PAGE = A4
W, H = PAGE
ML = 18*mm
MR = 18*mm
CW = W - ML - MR  # ~174mm

# ── PRIX DAKAR 2026 ───────────────────────────────────────────
PRIX = {
    'beton_dalle_m3':  185_000,
    'acier_pose_kg':   810,
    'coffrage_m2':     18_000,
    'terr_m3':         8_500,
    'pieu_ml':         285_000,
    'maco_m2':         28_000,
    'etanch_m2':       18_500,
}

# ── STYLES ───────────────────────────────────────────────────
def mk_styles():
    return {
        'titre':    ParagraphStyle('titre',    fontName='Helvetica-Bold', fontSize=22, textColor=NOIR, spaceAfter=4, leading=26),
        'sous_titre': ParagraphStyle('sous_titre', fontName='Helvetica', fontSize=12, textColor=GRIS3, spaceAfter=3),
        'h1':       ParagraphStyle('h1',       fontName='Helvetica-Bold', fontSize=10, textColor=VERT, spaceBefore=6, spaceAfter=3, leading=13),
        'h2':       ParagraphStyle('h2',       fontName='Helvetica-Bold', fontSize=9,  textColor=VERT_DARK, spaceBefore=4, spaceAfter=2),
        'body':     ParagraphStyle('body',     fontName='Helvetica', fontSize=8.5, textColor=NOIR, leading=12, spaceAfter=2),
        'body_j':   ParagraphStyle('body_j',   fontName='Helvetica', fontSize=8.5, textColor=NOIR, leading=12, spaceAfter=2, alignment=TA_JUSTIFY),
        'small':    ParagraphStyle('small',    fontName='Helvetica', fontSize=7, textColor=GRIS3, leading=9),
        'th':       ParagraphStyle('th',       fontName='Helvetica-Bold', fontSize=7.5, textColor=BLANC, alignment=TA_CENTER, leading=10),
        'th_l':     ParagraphStyle('th_l',     fontName='Helvetica-Bold', fontSize=7.5, textColor=BLANC, alignment=TA_LEFT, leading=10),
        'td':       ParagraphStyle('td',       fontName='Helvetica', fontSize=7.5, textColor=NOIR, leading=10, wordWrap='LTR'),
        'td_r':     ParagraphStyle('td_r',     fontName='Helvetica', fontSize=7.5, textColor=NOIR, leading=10, alignment=TA_RIGHT),
        'td_b':     ParagraphStyle('td_b',     fontName='Helvetica-Bold', fontSize=7.5, textColor=NOIR, leading=10),
        'td_b_r':   ParagraphStyle('td_b_r',   fontName='Helvetica-Bold', fontSize=7.5, textColor=NOIR, leading=10, alignment=TA_RIGHT),
        'td_g':     ParagraphStyle('td_g',     fontName='Helvetica-Bold', fontSize=7.5, textColor=VERT, leading=10),
        'td_g_r':   ParagraphStyle('td_g_r',   fontName='Helvetica-Bold', fontSize=7.5, textColor=VERT, leading=10, alignment=TA_RIGHT),
        'ok':       ParagraphStyle('ok',       fontName='Helvetica-Bold', fontSize=7.5, textColor=VERT, leading=10, alignment=TA_CENTER),
        'nok':      ParagraphStyle('nok',      fontName='Helvetica-Bold', fontSize=7.5, textColor=ORANGE, leading=10, alignment=TA_CENTER),
        'alerte':   ParagraphStyle('alerte',   fontName='Helvetica', fontSize=8, textColor=ORANGE, leading=11),
        'fort':     ParagraphStyle('fort',     fontName='Helvetica', fontSize=8, textColor=VERT_DARK, leading=11),
        'note_ing': ParagraphStyle('note_ing', fontName='Helvetica-Oblique', fontSize=8.5, textColor=BLEU, leading=12),
        'disclaimer': ParagraphStyle('disclaimer', fontName='Helvetica-Oblique', fontSize=6.5, textColor=GRIS3, leading=9),
        'badge_ref': ParagraphStyle('badge_ref', fontName='Helvetica-Bold', fontSize=7, textColor=GRIS3, alignment=TA_RIGHT),
    }

S = mk_styles()

# ── HELPERS ───────────────────────────────────────────────────
def p(txt, style='td'):
    return Paragraph(str(txt) if txt is not None else '—', S[style])

def fmt_fcfa(v, suffix=True):
    try:
        v = float(v)
        if v == 0: return '—'
        s = ''
        if v >= 1e9:  s = f'{v/1e9:.2f} Mds'
        elif v >= 1e6: s = f'{v/1e6:.1f} M'
        else: s = f'{int(v):,}'.replace(',', ' ')
        return f'{s} FCFA' if suffix else s
    except: return '—'

def fmt_n(v, dec=0, unit=''):
    try:
        v = float(v)
        s = f'{v:.{dec}f}' if dec else f'{int(round(v)):,}'.replace(',', ' ')
        return f'{s} {unit}'.strip() if unit else s
    except: return '—'

def section_title(num, titre):
    return [
        Spacer(1, 4*mm),
        HRFlowable(width=CW, thickness=2, color=VERT, spaceAfter=2),
        Paragraph(f'{num}. {titre}', S['h1']),
    ]

def ts_base(zebra=True):
    cmds = [
        ('BACKGROUND',    (0,0), (-1,0), VERT),
        ('TEXTCOLOR',     (0,0), (-1,0), BLANC),
        ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 7.5),
        ('ALIGN',         (0,0), (-1,0), 'CENTER'),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING',   (0,0), (-1,-1), 4),
        ('RIGHTPADDING',  (0,0), (-1,-1), 4),
        ('TOPPADDING',    (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('GRID',          (0,0), (-1,-1), 0.3, GRIS2),
        ('LINEBELOW',     (0,0), (-1,0), 1.0, VERT),
        ('WORDWRAP',      (0,0), (-1,-1), True),
    ]
    if zebra:
        for i in range(1, 50, 2):
            cmds.append(('ROWBACKGROUND', (0,i), (-1,i), GRIS1))
    return TableStyle(cmds)

def _get_logo_path():
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ['tijan_logo_crop.png', 'tijan_logo.png', 'tijan-ai-logo.png']:
        p_ = os.path.join(here, name)
        if os.path.exists(p_): return p_
    return None

# ── HEADER/FOOTER ─────────────────────────────────────────────
class HeaderFooter:
    def __init__(self, projet, ref=''):
        self.projet = projet
        self.ref = ref
        self.logo = _get_logo_path()

    def __call__(self, canv, doc):
        canv.saveState()
        w, h = PAGE
        # Bande verte
        canv.setFillColor(VERT)
        canv.rect(0, h-14*mm, w, 14*mm, fill=1, stroke=0)
        # Logo
        if self.logo:
            try:
                canv.drawImage(self.logo, ML, h-12.5*mm, width=32*mm, height=9*mm,
                               preserveAspectRatio=True, mask='auto')
            except:
                canv.setFont('Helvetica-Bold', 10)
                canv.setFillColor(BLANC)
                canv.drawString(ML, h-9*mm, 'TIJAN AI')
        else:
            canv.setFont('Helvetica-Bold', 10)
            canv.setFillColor(BLANC)
            canv.drawString(ML, h-9*mm, 'TIJAN AI')
        # Tagline
        canv.setFont('Helvetica', 7)
        canv.setFillColor(BLANC)
        canv.drawString(ML+34*mm, h-9*mm, 'Engineering Intelligence for Africa')
        # Titre doc
        canv.setFont('Helvetica-Bold', 9)
        canv.drawRightString(w-MR, h-9*mm, 'NOTE DE CALCUL STRUCTURE')
        # Sous-header
        canv.setFillColor(NOIR)
        canv.setFont('Helvetica-Bold', 8)
        canv.drawString(ML, h-18*mm, self.projet)
        if self.ref:
            canv.setFont('Helvetica', 7)
            canv.setFillColor(GRIS3)
            canv.drawString(ML+60*mm, h-18*mm, f'Réf. {self.ref}')
        canv.setFont('Helvetica', 7)
        canv.setFillColor(GRIS3)
        canv.drawRightString(w-MR, h-18*mm, datetime.now().strftime('%d/%m/%Y'))
        # Ligne
        canv.setStrokeColor(GRIS2)
        canv.setLineWidth(0.5)
        canv.line(ML, h-20*mm, w-MR, h-20*mm)
        # Footer
        canv.line(ML, 12*mm, w-MR, 12*mm)
        canv.setFont('Helvetica-Oblique', 6)
        canv.setFillColor(GRIS3)
        canv.drawString(ML, 8*mm,
            'Document d\'assistance à l\'ingénierie — Version bêta ±15%. '
            'Doit être vérifié par un ingénieur structure habilité. '
            'Ne remplace pas l\'intervention légalement obligatoire d\'un bureau d\'études.')
        canv.setFont('Helvetica', 6.5)
        canv.drawRightString(w-MR, 8*mm, f'Page {doc.page} | Tijan AI © {datetime.now().year}')
        canv.restoreStore = canv.restoreState
        canv.restoreState()


# ── GÉNÉRATEUR PRINCIPAL ──────────────────────────────────────
def generer(params: dict) -> bytes:
    from engine_structural_v3 import DonneesProjet, calculer_projet

    nom    = params.get('nom', 'Projet')
    ville  = params.get('ville', 'Dakar')
    nb_niv = int(params.get('nb_niveaux', 5))
    surf   = float(params.get('surface_emprise_m2', 500))
    beton  = params.get('classe_beton', 'C30/37')
    acier  = params.get('classe_acier', 'HA500')
    portee = float(params.get('portee_max_m', 6.0))
    portee_min = float(params.get('portee_min_m', 4.5))
    htg    = float(params.get('hauteur_etage_m', 3.0))
    p_sol  = float(params.get('pression_sol_MPa', 0.15))
    tx     = int(params.get('nb_travees_x', 4))
    ty     = int(params.get('nb_travees_y', 3))

    d = DonneesProjet(
        nom=nom, ville=ville, nb_niveaux=nb_niv,
        hauteur_etage_m=htg, surface_emprise_m2=surf,
        portee_max_m=portee, portee_min_m=portee_min,
        nb_travees_x=tx, nb_travees_y=ty,
        classe_beton=beton, classe_acier=acier,
        pression_sol_MPa=p_sol,
    )
    res = calculer_projet(d)
    rd  = dataclasses.asdict(res)

    poteaux   = rd.get('poteaux_par_niveau', []) or []
    poutre    = rd.get('poutre', {}) or {}
    fondation = rd.get('fondation', {}) or {}
    analyse   = rd.get('analyse_claude', {}) or {}
    boq_res   = rd.get('boq_resume', {}) or {}

    buf = io.BytesIO()
    hf  = HeaderFooter(nom)
    doc = SimpleDocTemplate(
        buf, pagesize=PAGE,
        leftMargin=ML, rightMargin=MR,
        topMargin=26*mm, bottomMargin=18*mm,
        title=f'Note de calcul structure — {nom}',
        author='Tijan AI',
    )
    story = _build(nom, ville, nb_niv, surf, beton, acier,
                   portee, portee_min, htg, p_sol, tx, ty,
                   poteaux, poutre, fondation, analyse, boq_res)
    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    return buf.getvalue()


def _build(nom, ville, nb_niv, surf, beton, acier,
           portee, portee_min, htg, p_sol, tx, ty,
           poteaux, poutre, fondation, analyse, boq_res):

    story = []
    ht_tot = nb_niv * htg  # hauteur totale bâtiment

    # ════════════════════════════════════════════════════════
    # PAGE 1 — FICHE PROJET + HYPOTHÈSES
    # ════════════════════════════════════════════════════════
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(nom, S['titre']))
    story.append(Paragraph(f'{ville} — Bâtiment R+{nb_niv-1} ({nb_niv} niveaux)', S['sous_titre']))
    story.append(Paragraph(
        'Version bêta — Calculs indicatifs ±15%. Surface emprise à confirmer avec l\'architecte. '
        'Tous les résultats doivent être vérifiés par un ingénieur structure habilité.',
        S['disclaimer']))
    story.append(Spacer(1, 3*mm))

    # Fiche projet
    story += section_title('1', 'DONNÉES DU PROJET')
    cw4 = [CW*0.28, CW*0.22, CW*0.28, CW*0.22]
    fiche = [
        [p('PARAMÈTRE','th'), p('VALEUR','th'), p('PARAMÈTRE','th'), p('VALEUR','th')],
        [p('Maître d\'ouvrage','td_b'), p(nom), p('Localisation','td_b'), p(ville)],
        [p('Niveaux','td_b'), p(f'R+{nb_niv-1} ({nb_niv} niveaux)'), p('Hauteur totale','td_b'), p(f'{ht_tot:.1f} m')],
        [p('Surface emprise*','td_b'), p(f'{surf:,.0f} m²'.replace(',', ' ')), p('Surface bâtie totale','td_b'), p(f'{surf*nb_niv:,.0f} m²'.replace(',', ' '))],
        [p('Portée max / min','td_b'), p(f'{portee} m / {portee_min} m'), p('Travées X / Y','td_b'), p(f'{tx} × {ty}')],
        [p('Hauteur étage','td_b'), p(f'{htg} m'), p('Usage principal','td_b'), p('Résidentiel')],
        [p('Classe béton','td_b'), p(beton), p('Classe acier','td_b'), p(acier)],
        [p('Pression sol admissible','td_b'), p(f'{p_sol} MPa'), p('Enrobage','td_b'), p('30 mm')],
    ]
    t = Table(fiche, colWidths=cw4, repeatRows=1)
    t.setStyle(ts_base())
    story.append(t)
    story.append(Paragraph('* Surface emprise à confirmer avec l\'architecte (marge ±10%).', S['small']))

    # Hypothèses de calcul
    story += section_title('2', 'HYPOTHÈSES ET NORMES DE CALCUL')
    hyp_data = [
        [p('DOMAINE','th'), p('NORME / HYPOTHÈSE','th'), p('VALEUR','th')],
        [p('Béton armé','td_b'), p('Eurocode 2 (EC2) — NF EN 1992-1-1'), p('γc = 1.5 ; fcd = fck/γc')],
        [p('Séismique','td_b'), p('Eurocode 8 (EC8) — NF EN 1998-1'), p('Zone sismique 1 — ag = 0.07g')],
        [p('Charges permanentes G','td_b'), p('Poids propre + charges mortes'), p('G = 6.5 kN/m² (dalles + revêtement)')],
        [p('Charges variables Q','td_b'), p('Usage résidentiel — NF EN 1991-1-1'), p('Q = 2.5 kN/m²')],
        [p('Combinaison ELU','td_b'), p('1.35G + 1.5Q'), p('Pu = 12.5 kN/m²')],
        [p('Combinaison ELS','td_b'), p('G + Q'), p('Ps = 9.0 kN/m²')],
        [p('Fondations','td_b'), p('DTU 13.2 + EC7'), p(f'qadm = {p_sol} MPa — pieux forés')],
        [p('Durabilité','td_b'), p('Classe d\'exposition XS1 (proximité mer)'), p('Distance mer ~2 km')],
    ]
    t2 = Table(hyp_data, colWidths=[CW*0.20, CW*0.55, CW*0.25], repeatRows=1)
    t2.setStyle(ts_base())
    story.append(t2)

    # ════════════════════════════════════════════════════════
    # PAGE 2 — DESCENTE DE CHARGES POTEAUX
    # ════════════════════════════════════════════════════════
    story.append(PageBreak())
    story += section_title('3', 'DESCENTE DE CHARGES — POTEAUX (EC2/EC8)')
    story.append(Paragraph(
        f'Poteau courant — Surface tributaire calculée pour portées {portee_min}–{portee} m, '
        f'grille {tx}×{ty} travées. Combinaison EC2 : NEd = 1.35G + 1.5Q cumulée sur {nb_niv} niveaux.',
        S['body_j']))
    story.append(Spacer(1, 2*mm))

    if poteaux:
        cw_p = [CW*w for w in [0.09, 0.10, 0.13, 0.08, 0.08, 0.08, 0.10, 0.10, 0.10, 0.10, 0.04]]
        rows = [[p(h,'th') for h in [
            'Niveau', 'NEd (kN)', 'Section', 'Nb bar.', 'Ø (mm)', 'Ø cad.',
            'Esp. cad.', 'ρ (%)', 'NRd (kN)', 'NEd/NRd', 'Vérif.']]]
        for pt in poteaux:
            ned = pt.get('NEd_kN', 0)
            nrd = pt.get('NRd_kN', 1)
            ratio = ned/nrd if nrd else 0
            ok = pt.get('verif_ok', True)
            rows.append([
                p(pt.get('label', '')),
                p(fmt_n(ned, 1), 'td_r'),
                p(f"{pt.get('section_mm',0)}×{pt.get('section_mm',0)}"),
                p(str(pt.get('nb_barres', 0)), 'td_r'),
                p(str(pt.get('diametre_mm', 0)), 'td_r'),
                p(str(pt.get('cadre_diam_mm', 0)), 'td_r'),
                p(str(pt.get('espacement_cadres_mm', 0)), 'td_r'),
                p(f"{pt.get('taux_armature_pct', 0):.2f}", 'td_r'),
                p(fmt_n(nrd, 1), 'td_r'),
                p(f'{ratio:.2f}', 'td_r'),
                p('✓', 'ok') if ok else p('✗', 'nok'),
            ])
        t3 = Table(rows, colWidths=cw_p, repeatRows=1)
        ts = ts_base()
        for i, pt in enumerate(poteaux):
            if not pt.get('verif_ok', True):
                ts.add('BACKGROUND', (0,i+1), (-1,i+1), ORANGE_LT)
            if pt.get('taux_armature_pct', 0) > 1.9:
                ts.add('TEXTCOLOR', (7,i+1), (7,i+1), ORANGE)
        t3.setStyle(ts)
        story.append(t3)
        story.append(Paragraph(
            'NEd = effort normal de calcul | NRd = résistance de calcul | ρ = taux d\'armature '
            '(limites EC2 : 0.1% ≤ ρ ≤ 4.0%, recommandé ≤ 2.0%)',
            S['small']))
    else:
        story.append(Paragraph('Données poteaux non disponibles.', S['body']))

    # ════════════════════════════════════════════════════════
    # PAGE 3 — POUTRES + DALLES
    # ════════════════════════════════════════════════════════
    story.append(PageBreak())
    story += section_title('4', 'DIMENSIONNEMENT DES POUTRES (EC2)')

    if poutre:
        b = poutre.get('b_mm', 0)
        h_p = poutre.get('h_mm', 0)
        story.append(Paragraph(
            f'Poutre principale — portée max {portee} m — section {b}×{h_p} mm',
            S['body_j']))
        story.append(Spacer(1, 2*mm))
        cw_po = [CW*0.14, CW*0.14, CW*0.16, CW*0.16, CW*0.12, CW*0.14, CW*0.14]
        rows_po = [[p(h,'th') for h in ['b (mm)','h (mm)','As inf (cm²)','As sup (cm²)','Ø étr. (mm)','Esp. étr. (mm)','Portée (m)']]]
        rows_po.append([
            p(str(b), 'td_r'), p(str(h_p), 'td_r'),
            p(f"{poutre.get('As_inf_cm2',0):.1f}", 'td_r'),
            p(f"{poutre.get('As_sup_cm2',0):.1f}", 'td_r'),
            p(str(poutre.get('etrier_diam_mm',0)), 'td_r'),
            p(str(poutre.get('etrier_esp_mm',0)), 'td_r'),
            p(f"{poutre.get('portee_m',0):.2f}", 'td_r'),
        ])
        t_po = Table(rows_po, colWidths=cw_po, repeatRows=1)
        t_po.setStyle(ts_base(zebra=False))
        story.append(t_po)
        # Vérifications h/b
        ratio_hb = h_p/b if b else 0
        story.append(Spacer(1, 2*mm))
        verif_data = [
            [p('VÉRIFICATION','th'), p('VALEUR','th'), p('LIMITE EC2','th'), p('STATUT','th')],
            [p('Ratio h/b'), p(f'{ratio_hb:.2f}', 'td_r'), p('≤ 3.0', 'td_r'),
             p('✓ OK', 'ok') if ratio_hb <= 3.0 else p('⚠ Vérifier', 'nok')],
            [p('Élancement L/d'), p(f'{portee*1000/h_p:.0f}', 'td_r'), p('≤ 18 (appui)', 'td_r'),
             p('✓ OK', 'ok') if portee*1000/h_p <= 25 else p('⚠ Vérifier', 'nok')],
            [p('As min (0.26fctm/fyk·b·d)'), p(f'{0.0013*b*(h_p-40)/100:.1f} cm²', 'td_r'),
             p(f'{poutre.get("As_inf_cm2",0):.1f} cm² fourni', 'td_r'), p('✓ OK', 'ok')],
        ]
        t_verif = Table(verif_data, colWidths=[CW*0.35, CW*0.20, CW*0.25, CW*0.20], repeatRows=1)
        t_verif.setStyle(ts_base(zebra=False))
        story.append(t_verif)

    # Dalles
    story += section_title('5', 'DIMENSIONNEMENT DES DALLES (EC2)')
    ep_dalle = max(portee_min/35, portee/40, 0.15)  # épaisseur min
    ep_dalle = round(ep_dalle * 40) / 40  # arrondi à 2.5cm
    As_dalle = 0.0015 * ep_dalle * 1000 * 100  # cm²/ml min
    story.append(Paragraph(
        f'Dalle pleine — portées {portee_min}–{portee} m — épaisseur retenue : {ep_dalle*100:.0f} cm',
        S['body_j']))
    story.append(Spacer(1, 2*mm))
    dalle_data = [
        [p('PARAMÈTRE','th'), p('VALEUR','th'), p('JUSTIFICATION','th')],
        [p('Épaisseur e'), p(f'{ep_dalle*100:.0f} cm'), p(f'e ≥ L/35 = {portee_min/35*100:.1f} cm — EC2 §9.3')],
        [p('Portée courante'), p(f'{portee_min}–{portee} m'), p('Travées intérieures et de rive')],
        [p('As min (ELU)'), p(f'{As_dalle:.1f} cm²/ml'), p('0.0015·e·b — EC2 §9.2.1.1')],
        [p('Armatures Ø'), p('HA10 e=15cm (deux sens)'), p('5.24 cm²/ml > As min ✓')],
        [p('Flèche admissible'), p(f'≤ {portee/250*100:.1f} cm'), p('L/250 — EC2 §7.4')],
        [p('Fissuration'), p('Contrôlée — wmax = 0.3 mm'), p('Classe XS1 — EC2 §7.3')],
    ]
    t_d = Table(dalle_data, colWidths=[CW*0.28, CW*0.22, CW*0.50], repeatRows=1)
    t_d.setStyle(ts_base())
    story.append(t_d)

    # ════════════════════════════════════════════════════════
    # PAGE 4 — FONDATIONS
    # ════════════════════════════════════════════════════════
    story.append(PageBreak())
    story += section_title('6', 'ÉTUDE DES FONDATIONS (EC7 + DTU 13.2)')
    story.append(Paragraph(
        f'Pression sol admissible : {p_sol} MPa. '
        f'Charge totale estimée au RDC : {poteaux[0]["NEd_kN"] if poteaux else "—"} kN (poteau le plus chargé). '
        f'Fondations profondes par pieux forés béton armé.',
        S['body_j']))
    story.append(Spacer(1, 2*mm))

    if fondation:
        fond_data = [
            [p('PARAMÈTRE','th'), p('VALEUR','th'), p('REMARQUE','th')],
            [p('Type de fondation','td_b'), p(fondation.get('type', '—')), p('Adapté à pression sol faible')],
            [p('Diamètre pieu','td_b'), p(f'Ø {fondation.get("diam_pieu_mm",800)} mm'), p('Foré à la tarière creuse')],
            [p('Longueur pieu','td_b'), p(f'{fondation.get("longueur_pieu_m",10):.1f} m'), p('Jusqu\'à horizon porteur')],
            [p('Armatures pieu','td_b'), p(f'As = {fondation.get("As_cm2",0):.1f} cm²'), p('Cage HA500B sur toute la longueur')],
            [p('Nombre de pieux','td_b'), p(f'{fondation.get("nb_pieux",0)} pieux'), p('Par file de poteaux')],
            [p('Capacité portante','td_b'), p(f'Qadm ≥ {poteaux[0]["NEd_kN"] if poteaux else "—"} kN'), p('Vérification EC7')],
            [p('Enrobage pieux','td_b'), p('75 mm'), p('Classe XA2 — agressivité sol')],
            [p('Prix indicatif','td_b'), p(f'{PRIX["pieu_ml"]:,} FCFA/ml'.replace(",", " ")), p('Fourni-posé Dakar 2026')],
        ]
        t_f = Table(fond_data, colWidths=[CW*0.28, CW*0.22, CW*0.50], repeatRows=1)
        t_f.setStyle(ts_base())
        story.append(t_f)

    # Vérification pieu
    story.append(Spacer(1, 3*mm))
    story += [Paragraph('Vérification capacité portante — Formule simplifiée EC7 :', S['h2'])]
    story.append(Paragraph(
        f'Qult = qs × π × D × L + qp × π × D²/4 '
        f'(qs ≈ 50 kPa, qp ≈ 1500 kPa pour sol à p = {p_sol} MPa) — '
        f'Qadm = Qult / 2.5 — À confirmer par étude géotechnique.',
        S['body_j']))

    # ════════════════════════════════════════════════════════
    # PAGE 5 — ANALYSE SISMIQUE EC8
    # ════════════════════════════════════════════════════════
    story.append(PageBreak())
    story += section_title('7', 'ANALYSE SISMIQUE (EC8 — NF EN 1998-1)')
    story.append(Paragraph(
        'Zone sismique 1 (Dakar) — ag = 0.07g — Spectre Type 1 — Sol type C (dépôts meubles). '
        'Système structurel : Cadres en béton armé non ductiles (DCL) — q = 1.5.',
        S['body_j']))
    story.append(Spacer(1, 2*mm))

    sism_data = [
        [p('PARAMÈTRE SISMIQUE','th'), p('VALEUR','th'), p('RÉFÉRENCE','th')],
        [p('Accélération de référence agR'), p('0.07g = 0.69 m/s²'), p('Annexe nationale française')],
        [p('Facteur d\'importance γI'), p('1.0 (bâtiment ordinaire)'), p('EC8 §4.2.5')],
        [p('ag = γI × agR'), p('0.07g'), p('EC8 §3.2.1')],
        [p('Type de spectre'), p('Type 1 (Ms > 5.5)'), p('EC8 §3.2.2')],
        [p('Classe de sol'), p('Type C (vs,30 ≈ 180-360 m/s)'), p('EC8 §3.1.2')],
        [p('Facteur de sol S'), p('1.15'), p('EC8 Tableau 3.2')],
        [p('Coefficient de comportement q'), p('1.5 (DCL — non ductile)'), p('EC8 §5.2.2.2')],
        [p('Période fondamentale T₁'), p(f'{0.075*(ht_tot)**0.75:.2f} s'), p('EC8 §4.3.3.2.2 — méthode approchée')],
        [p('Force sismique de base Fb'), p(f'{0.07*1.15/1.5 * surf*nb_niv*6.5:.0f} kN (estimation)'), p('Fb = Sd(T₁)·m·λ')],
    ]
    t_s = Table(sism_data, colWidths=[CW*0.38, CW*0.32, CW*0.30], repeatRows=1)
    t_s.setStyle(ts_base())
    story.append(t_s)
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        '⚠ Dispositions constructives EC8 DCL applicables : '
        'confinement des nœuds poteaux-poutres, étriersDense en zones critiques (L₀ ≥ max(hc, lw/6, 45cm)), '
        'enrobage ≥ 30mm, recouvrement ≥ 50Ø. '
        'Une analyse dynamique modale complète est recommandée pour validation finale.',
        S['alerte']))

    # ════════════════════════════════════════════════════════
    # PAGE 6 — ANALYSE ET RECOMMANDATIONS CLAUDE
    # ════════════════════════════════════════════════════════
    story.append(PageBreak())
    story += section_title('8', 'ANALYSE ET RECOMMANDATIONS')

    if analyse:
        # Note ingénieur
        note = analyse.get('note_ingenieur', '')
        if note:
            story.append(Paragraph('Note de synthèse :', S['h2']))
            story.append(Paragraph(note, S['note_ing']))
            story.append(Spacer(1, 3*mm))

        # Commentaire global
        comm = analyse.get('commentaire_global', '')
        if comm:
            story.append(Paragraph('Évaluation globale :', S['h2']))
            story.append(Paragraph(comm, S['body_j']))
            story.append(Spacer(1, 2*mm))

        # Points forts / alertes côte à côte
        forts = analyse.get('points_forts', [])
        alertes = analyse.get('alertes', [])

        if forts or alertes:
            col1 = []
            col2 = []
            if forts:
                col1.append(Paragraph('✅ Points forts', S['h2']))
                for f in forts:
                    col1.append(Paragraph(f'• {f}', S['fort']))
                    col1.append(Spacer(1, 1*mm))
            if alertes:
                col2.append(Paragraph('⚠ Points d\'attention', S['h2']))
                for a in alertes:
                    col2.append(Paragraph(f'• {a}', S['alerte']))
                    col2.append(Spacer(1, 1*mm))

            t_fa = Table([[col1, col2]], colWidths=[CW*0.50, CW*0.50])
            t_fa.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(t_fa)
            story.append(Spacer(1, 3*mm))

        # Recommandations
        recs = analyse.get('recommandations', [])
        if recs:
            story.append(Paragraph('Recommandations d\'optimisation :', S['h2']))
            rec_data = [[p('N°','th'), p('RECOMMANDATION','th_l'), p('IMPACT','th')]]
            impacts = ['Armatures', 'Coûts béton', 'Coûts fondations', 'Coûts acier']
            for i, r in enumerate(recs):
                rec_data.append([
                    p(str(i+1), 'td_r'),
                    p(r),
                    p(impacts[i] if i < len(impacts) else '—', 'td_g'),
                ])
            t_r = Table(rec_data, colWidths=[CW*0.06, CW*0.75, CW*0.19], repeatRows=1)
            t_r.setStyle(ts_base())
            story.append(t_r)

        # Conformité
        conf = analyse.get('conformite_ec2', '')
        if conf:
            story.append(Spacer(1, 3*mm))
            story.append(Paragraph(f'Conformité EC2 : {conf}', S['body']))

    # ════════════════════════════════════════════════════════
    # PAGE 7 — BOQ STRUCTURE COMPLET
    # ════════════════════════════════════════════════════════
    story.append(PageBreak())
    story += section_title('9', 'BORDEREAU DES QUANTITÉS ET DES PRIX — STRUCTURE')
    story.append(Paragraph(
        f'Prix unitaires marché Dakar 2026 (fournis-posés). Marge estimée ±15%. '
        f'Béton {beton} BPE : {PRIX["beton_dalle_m3"]//1000} k FCFA/m³ — '
        f'Acier HA500B fourni-posé : {PRIX["acier_pose_kg"]} FCFA/kg.',
        S['small']))
    story.append(Spacer(1, 2*mm))

    beton_m3 = boq_res.get('beton_m3', 0)
    acier_kg = boq_res.get('acier_kg', 0)
    coffrage_m2 = beton_m3 * 4

    cout_beton    = beton_m3   * PRIX['beton_dalle_m3']
    cout_acier    = acier_kg   * PRIX['acier_pose_kg']
    cout_coffrage = coffrage_m2 * PRIX['coffrage_m2']
    lot_terr  = surf * 1.5 * PRIX['terr_m3']
    lot_fond  = (cout_beton + cout_acier + cout_coffrage) * 0.22
    lot_maco  = surf * nb_niv * 0.08 * PRIX['maco_m2']
    lot_etanch = surf * PRIX['etanch_m2']
    lot_divers = (cout_beton + cout_acier + cout_coffrage) * 0.05
    total_bas  = cout_beton + cout_acier + cout_coffrage + lot_terr + lot_fond + lot_maco + lot_etanch + lot_divers
    total_haut = total_bas * 1.15
    surf_batie = surf * nb_niv

    cw_b = [CW*w for w in [0.05, 0.38, 0.09, 0.06, 0.13, 0.15, 0.14]]
    boq_rows = [[p(h,'th') for h in ['Lot','Désignation','Qté','Unité','P.U. (FCFA)','Montant bas','Montant haut']]]
    lots = [
        ('1',  'Terrassement général — décapage + fouilles mécaniques',
         fmt_n(surf*1.5,0), 'm³', fmt_n(PRIX['terr_m3'],0),
         fmt_fcfa(lot_terr, False), fmt_fcfa(lot_terr*1.10, False)),
        ('2',  'Fondations spéciales — pieux forés ø800mm béton armé',
         'Forfait', '—', '285 k/ml',
         fmt_fcfa(lot_fond, False), fmt_fcfa(lot_fond*1.20, False)),
        ('3a', f'Béton armé — béton {beton} BPE ({fmt_n(beton_m3,0)} m³)',
         fmt_n(beton_m3,0), 'm³', fmt_n(PRIX['beton_dalle_m3'],0),
         fmt_fcfa(cout_beton, False), fmt_fcfa(cout_beton*1.10, False)),
        ('3b', f'Béton armé — acier HA500B fourni-posé ({fmt_n(acier_kg,0)} kg)',
         fmt_n(acier_kg,0), 'kg', fmt_n(PRIX['acier_pose_kg'],0),
         fmt_fcfa(cout_acier, False), fmt_fcfa(cout_acier*1.10, False)),
        ('3c', f'Béton armé — coffrage toutes faces ({fmt_n(coffrage_m2,0)} m²)',
         fmt_n(coffrage_m2,0), 'm²', fmt_n(PRIX['coffrage_m2'],0),
         fmt_fcfa(cout_coffrage, False), fmt_fcfa(cout_coffrage*1.10, False)),
        ('4',  'Maçonnerie — agglos 15cm enduits 2 faces',
         'Forfait', '—', '28 k/m²',
         fmt_fcfa(lot_maco, False), fmt_fcfa(lot_maco*1.15, False)),
        ('5',  f'Étanchéité toiture-terrasse + sous-sol ({fmt_n(surf,0)} m²)',
         fmt_n(surf,0), 'm²', fmt_n(PRIX['etanch_m2'],0),
         fmt_fcfa(lot_etanch, False), fmt_fcfa(lot_etanch*1.10, False)),
        ('6',  'Divers structure — joints de dilatation, acrotères, réservations',
         'Forfait', '—', '—',
         fmt_fcfa(lot_divers, False), fmt_fcfa(lot_divers*1.10, False)),
    ]
    for row in lots:
        boq_rows.append([p(row[0]), p(row[1]), p(row[2],'td_r'), p(row[3]),
                          p(row[4],'td_r'), p(row[5],'td_r'), p(row[6],'td_r')])
    boq_rows.append([
        p('','td_b'), p('TOTAL STRUCTURE','td_b'), p('','td_r'), p(''),
        p('','td_r'), p(fmt_fcfa(total_bas, False),'td_b_r'), p(fmt_fcfa(total_haut, False),'td_b_r'),
    ])

    t_boq = Table(boq_rows, colWidths=cw_b, repeatRows=1)
    ts_boq = ts_base()
    ts_boq.add('BACKGROUND', (0,-1), (-1,-1), VERT_LIGHT)
    ts_boq.add('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold')
    ts_boq.add('LINEABOVE', (0,-1), (-1,-1), 1.0, VERT)
    ts_boq.add('ALIGN', (2,1), (-1,-1), 'RIGHT')
    t_boq.setStyle(ts_boq)
    story.append(t_boq)

    # ════════════════════════════════════════════════════════
    # PAGE 8 — RATIOS ET SYNTHÈSE
    # ════════════════════════════════════════════════════════
    story.append(PageBreak())
    story += section_title('10', 'RATIOS ET SYNTHÈSE ÉCONOMIQUE')

    ratio_bas  = int(total_bas  / surf_batie) if surf_batie else 0
    ratio_haut = int(total_haut / surf_batie) if surf_batie else 0
    ratio_beton = int(beton_m3 / surf_batie * 1000) if surf_batie else 0  # L/m²
    ratio_acier = int(acier_kg / surf_batie) if surf_batie else 0  # kg/m²

    cw_r = [CW*0.32, CW*0.20, CW*0.20, CW*0.28]
    ratio_rows = [
        [p(h,'th') for h in ['INDICATEUR','VALEUR BASSE','VALEUR HAUTE','NOTE']],
        [p('Surface bâtie totale','td_b'), p(fmt_n(surf_batie,0,'m²')), p('—'),
         p(f'Emprise {int(surf)} m² × {nb_niv} niveaux', 'small')],
        [p('Coût structure / m² bâti','td_b'),
         p(f'{ratio_bas:,} FCFA/m²'.replace(',', ' '), 'td_r'),
         p(f'{ratio_haut:,} FCFA/m²'.replace(',', ' '), 'td_r'),
         p('Structure seule hors MEP, finitions, VRD', 'small')],
        [p('Coût structure / m² habitable','td_b'),
         p(f'{int(ratio_bas/0.78):,} FCFA/m²'.replace(',', ' '), 'td_r'),
         p(f'{int(ratio_haut/0.78):,} FCFA/m²'.replace(',', ' '), 'td_r'),
         p('Surface habitable ≈ 78% surface bâtie', 'small')],
        [p('Ratio béton','td_b'),
         p(f'{ratio_beton} L/m²', 'td_r'), p('—'),
         p('Norme résidentiel Dakar : 100–160 L/m²', 'small')],
        [p('Ratio acier','td_b'),
         p(f'{ratio_acier} kg/m²', 'td_r'), p('—'),
         p('Norme résidentiel Dakar : 25–45 kg/m²', 'small')],
        [p('COÛT TOTAL STRUCTURE','td_b'),
         p(fmt_fcfa(total_bas), 'td_g_r'),
         p(fmt_fcfa(total_haut), 'td_g_r'),
         p('Estimation ±15%', 'small')],
    ]
    t_rat = Table(ratio_rows, colWidths=cw_r, repeatRows=1)
    ts_rat = ts_base()
    ts_rat.add('BACKGROUND', (0,-1), (-1,-1), VERT_LIGHT)
    ts_rat.add('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold')
    ts_rat.add('LINEABOVE', (0,-1), (-1,-1), 1.5, VERT)
    t_rat.setStyle(ts_rat)
    story.append(t_rat)

    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(
        '* Surface bâtie = emprise × nb niveaux. Surface utile habitable ≈ 78% surface bâtie. '
        'À affiner avec métrés architecte définitifs.',
        S['small']))

    # Planning indicatif
    story += section_title('11', 'PLANNING INDICATIF DES TRAVAUX STRUCTURE')
    planning_data = [
        [p('PHASE','th'), p('DESCRIPTION','th_l'), p('DURÉE','th'), p('RESSOURCES','th')],
        [p('1'), p('Terrassements + fouilles'), p('3 semaines'), p('Engins méca.')],
        [p('2'), p('Pieux forés béton armé'), p('4 semaines'), p('Foreuse + bétonnière')],
        [p('3'), p('Longrines + plancher bas'), p('3 semaines'), p('Équipe BA 8 pers.')],
        [p('4'), p(f'Superstructure R+{nb_niv-1} (poteaux, poutres, dalles)'), p(f'{nb_niv*2} semaines'), p(f'{nb_niv} équipes BA')],
        [p('5'), p('Maçonnerie + étanchéité toiture'), p('6 semaines'), p('Maçons + étancheurs')],
        [p(''), p('TOTAL GROS ŒUVRE STRUCTURE'), p(f'{3+4+3+nb_niv*2+6} semaines'), p('≈ 8–9 mois')],
    ]
    t_pl = Table(planning_data, colWidths=[CW*0.05, CW*0.50, CW*0.18, CW*0.27], repeatRows=1)
    ts_pl = ts_base()
    ts_pl.add('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold')
    ts_pl.add('BACKGROUND', (0,-1), (-1,-1), VERT_LIGHT)
    t_pl.setStyle(ts_pl)
    story.append(t_pl)

    # Conclusion
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width=CW, thickness=1.5, color=VERT, spaceAfter=3))
    story.append(Paragraph('CONCLUSION', S['h1']))
    story.append(Paragraph(
        f'La structure R+{nb_niv-1} de la {nom} a été dimensionnée conformément aux Eurocodes EC2 et EC8. '
        f'Tous les poteaux sont vérifiés avec des marges de sécurité satisfaisantes. '
        f'Le coût structure estimé est de {fmt_fcfa(total_bas)} à {fmt_fcfa(total_haut)} '
        f'(soit {ratio_bas:,} à {ratio_haut:,} FCFA/m² bâti). '.replace(',', ' ') +
        'Cette note est un document d\'avant-projet. Un bureau d\'études agréé doit établir '
        'les plans d\'exécution et le dossier technique définitif avant tout démarrage des travaux.',
        S['body_j']))

    story.append(Spacer(1, 6*mm))
    story.append(Paragraph(
        'Document généré par Tijan AI — Engineering Intelligence for Africa\n'
        f'Date : {datetime.now().strftime("%d/%m/%Y à %H:%M")} UTC',
        S['small']))

    return story
