"""
tijan_theme.py — Thème PDF partagé Tijan AI
Toutes les couleurs, styles, header/footer en un seul endroit.
Tous les générateurs importent depuis ici.
"""
import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import Table, TableStyle, Paragraph, HRFlowable, Spacer

# ── Couleurs ──────────────────────────────────────────────────
VERT        = colors.HexColor('#43A956')
VERT_LIGHT  = colors.HexColor('#EBF7ED')
VERT_DARK   = colors.HexColor('#2D7A3A')
NOIR        = colors.HexColor('#111111')
GRIS1       = colors.HexColor('#F5F5F5')
GRIS2       = colors.HexColor('#E5E5E5')
GRIS3       = colors.HexColor('#888888')
BLANC       = colors.white
ORANGE      = colors.HexColor('#E07B00')
ORANGE_LT   = colors.HexColor('#FFF3E0')
BLEU        = colors.HexColor('#1565C0')
BLEU_LT     = colors.HexColor('#E3F2FD')
ROUGE       = colors.HexColor('#DC2626')

PAGE = A4
W, H = PAGE
ML = 18 * mm
MR = 18 * mm
CW = W - ML - MR

# ── Logo ──────────────────────────────────────────────────────
def get_logo():
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ['tijan_logo_crop.png', 'tijan_logo.png']:
        path = os.path.join(here, name)
        if os.path.exists(path):
            return path
    return None

# ── Styles ────────────────────────────────────────────────────
def make_styles():
    return {
        'titre':     ParagraphStyle('titre',     fontName='Helvetica-Bold', fontSize=22, textColor=NOIR, spaceAfter=4, leading=26),
        'sous_titre':ParagraphStyle('sous_titre',fontName='Helvetica',      fontSize=12, textColor=GRIS3, spaceAfter=3),
        'h1':        ParagraphStyle('h1',        fontName='Helvetica-Bold', fontSize=10, textColor=VERT,  spaceBefore=6, spaceAfter=3),
        'h2':        ParagraphStyle('h2',        fontName='Helvetica-Bold', fontSize=9,  textColor=VERT_DARK, spaceBefore=4, spaceAfter=2),
        'body':      ParagraphStyle('body',      fontName='Helvetica',      fontSize=8.5,textColor=NOIR,  leading=12, spaceAfter=2),
        'body_j':    ParagraphStyle('body_j',    fontName='Helvetica',      fontSize=8.5,textColor=NOIR,  leading=12, spaceAfter=2, alignment=TA_JUSTIFY),
        'small':     ParagraphStyle('small',     fontName='Helvetica',      fontSize=7,  textColor=GRIS3, leading=9),
        'note':      ParagraphStyle('note',      fontName='Helvetica-Oblique', fontSize=7.5, textColor=ORANGE, leading=10),
        'th':        ParagraphStyle('th',        fontName='Helvetica-Bold', fontSize=7.5,textColor=BLANC, alignment=TA_CENTER, leading=10),
        'th_l':      ParagraphStyle('th_l',      fontName='Helvetica-Bold', fontSize=7.5,textColor=BLANC, alignment=TA_LEFT,   leading=10),
        'td':        ParagraphStyle('td',        fontName='Helvetica',      fontSize=7.5,textColor=NOIR,  leading=10, wordWrap='LTR'),
        'td_r':      ParagraphStyle('td_r',      fontName='Helvetica',      fontSize=7.5,textColor=NOIR,  leading=10, alignment=TA_RIGHT),
        'td_b':      ParagraphStyle('td_b',      fontName='Helvetica-Bold', fontSize=7.5,textColor=NOIR,  leading=10),
        'td_b_r':    ParagraphStyle('td_b_r',    fontName='Helvetica-Bold', fontSize=7.5,textColor=NOIR,  leading=10, alignment=TA_RIGHT),
        'td_g':      ParagraphStyle('td_g',      fontName='Helvetica-Bold', fontSize=7.5,textColor=VERT,  leading=10),
        'td_g_r':    ParagraphStyle('td_g_r',    fontName='Helvetica-Bold', fontSize=7.5,textColor=VERT,  leading=10, alignment=TA_RIGHT),
        'td_o':      ParagraphStyle('td_o',      fontName='Helvetica-Bold', fontSize=7.5,textColor=ORANGE,leading=10),
        'ok':        ParagraphStyle('ok',        fontName='Helvetica-Bold', fontSize=7.5,textColor=VERT,  leading=10, alignment=TA_CENTER),
        'nok':       ParagraphStyle('nok',       fontName='Helvetica-Bold', fontSize=7.5,textColor=ORANGE,leading=10, alignment=TA_CENTER),
        'disc':      ParagraphStyle('disc',      fontName='Helvetica-Oblique', fontSize=6.5, textColor=GRIS3, leading=9),
        'bleu':      ParagraphStyle('bleu',      fontName='Helvetica-Oblique', fontSize=8.5, textColor=BLEU, leading=12),
    }

S = make_styles()

# ── Helpers ───────────────────────────────────────────────────
def p(txt, style='td'):
    return Paragraph(str(txt) if txt is not None else '—', S[style])

def fmt_fcfa(v):
    try:
        v = float(v)
        if v == 0: return '—'
        if v >= 1e9: return f'{v/1e9:.2f} Mds FCFA'
        if v >= 1e6: return f'{v/1e6:.1f} M FCFA'
        return f'{int(v):,} FCFA'.replace(',', ' ')
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

def table_style(zebra=True, header_color=VERT):
    cmds = [
        ('BACKGROUND',    (0,0), (-1,0), header_color),
        ('TEXTCOLOR',     (0,0), (-1,0), BLANC),
        ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 7.5),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING',   (0,0), (-1,-1), 4),
        ('RIGHTPADDING',  (0,0), (-1,-1), 4),
        ('TOPPADDING',    (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('GRID',          (0,0), (-1,-1), 0.3, GRIS2),
        ('LINEBELOW',     (0,0), (-1,0), 1.0, VERT),
    ]
    if zebra:
        for i in range(1, 50, 2):
            cmds.append(('ROWBACKGROUND', (0,i), (-1,i), GRIS1))
    return TableStyle(cmds)

def total_row_style(ts):
    ts.add('BACKGROUND', (0,-1), (-1,-1), VERT_LIGHT)
    ts.add('FONTNAME',   (0,-1), (-1,-1), 'Helvetica-Bold')
    ts.add('LINEABOVE',  (0,-1), (-1,-1), 1.0, VERT)
    return ts

# ── Header/Footer ──────────────────────────────────────────────
class HeaderFooter:
    def __init__(self, nom_projet, type_doc, ref='', lang='fr'):
        self.nom = nom_projet
        self.type_doc = type_doc
        self.ref = ref
        self.logo = get_logo()
        self.date = datetime.now().strftime('%d/%m/%Y')
        if lang == 'en':
            self.disclaimer = (
                'Engineering assistance document — Beta version ±15%. '
                'Must be verified by a licensed engineer. '
                'Does not replace the legally required involvement of a certified engineering firm.'
            )
        else:
            self.disclaimer = (
                'Document d\'assistance à l\'ingénierie — Version bêta ±15%. '
                'Doit être vérifié par un ingénieur habilité. '
                'Ne remplace pas l\'intervention légalement obligatoire d\'un bureau d\'études.'
            )

    def __call__(self, canv, doc):
        canv.saveState()
        w, h = PAGE
        # Bande verte header
        canv.setFillColor(VERT)
        canv.rect(0, h-14*mm, w, 14*mm, fill=1, stroke=0)
        # Logo
        if self.logo:
            try:
                canv.drawImage(self.logo, ML, h-12.5*mm, width=32*mm, height=9*mm,
                               preserveAspectRatio=True, mask='auto')
            except:
                canv.setFont('Helvetica-Bold', 9)
                canv.setFillColor(BLANC)
                canv.drawString(ML, h-9*mm, 'TIJAN AI')
        else:
            canv.setFont('Helvetica-Bold', 9)
            canv.setFillColor(BLANC)
            canv.drawString(ML, h-9*mm, 'TIJAN AI')
        # Tagline
        canv.setFont('Helvetica', 7)
        canv.setFillColor(BLANC)
        canv.drawString(ML+34*mm, h-9*mm, 'Engineering Intelligence for Africa')
        # Type document
        canv.setFont('Helvetica-Bold', 9)
        canv.drawRightString(w-MR, h-9*mm, self.type_doc.upper())
        # Sous-header
        canv.setFillColor(NOIR)
        canv.setFont('Helvetica-Bold', 8)
        canv.drawString(ML, h-18*mm, self.nom)
        if self.ref:
            canv.setFont('Helvetica', 7)
            canv.setFillColor(GRIS3)
            canv.drawString(ML+80*mm, h-18*mm, f'Réf. {self.ref}')
        canv.setFont('Helvetica', 7)
        canv.setFillColor(GRIS3)
        canv.drawRightString(w-MR, h-18*mm, self.date)
        # Ligne
        canv.setStrokeColor(GRIS2)
        canv.setLineWidth(0.5)
        canv.line(ML, h-20*mm, w-MR, h-20*mm)
        # Footer — 2 lignes séparées
        canv.line(ML, 14*mm, w-MR, 14*mm)
        canv.setFont('Helvetica-Oblique', 5.5)
        canv.setFillColor(GRIS3)
        # Ligne 1 — disclaimer (gauche)
        disclaimer = getattr(self, 'disclaimer',
            'Engineering assistance document — Beta ±15%. Must be verified by a licensed engineer.')
        canv.drawString(ML, 9.5*mm, disclaimer)
        # Ligne 2 — page number (droite, ligne séparée)
        canv.setFont('Helvetica', 6.5)
        canv.setFillColor(GRIS3)
        canv.drawRightString(w-MR, 5*mm, f'Page {doc.page} | Tijan AI © {datetime.now().year}')
        canv.restoreState()
