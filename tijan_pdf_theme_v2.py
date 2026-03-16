"""
tijan_pdf_theme_v2.py
Module de thème PDF Tijan AI — Version finale investisseurs
Format A4 paysage, tableaux propres, branding complet
"""
import os
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from datetime import datetime

# ── DIMENSIONS ────────────────────────────────────────────────
PAGE = landscape(A4)          # 297 × 210 mm
W, H = PAGE                   # 841.89 × 595.28 pt
MARGIN_H = 20 * mm
MARGIN_V = 22 * mm
CONTENT_W = W - 2 * MARGIN_H  # ~760pt disponibles

# ── COULEURS ──────────────────────────────────────────────────
VERT     = colors.HexColor('#43A956')
NOIR     = colors.HexColor('#111111')
GRIS1    = colors.HexColor('#F5F5F5')
GRIS2    = colors.HexColor('#E5E5E5')
GRIS3    = colors.HexColor('#888888')
BLANC    = colors.white
VERT_L   = colors.HexColor('#EBF7ED')

# ── LOGO PATH ─────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = None
for _c in [
    os.path.join(_HERE, 'tijan_logo_crop.png'),
    os.path.join(_HERE, 'tijan-ai-logo.png'),
    '/opt/render/project/src/tijan_logo_crop.png',
    '/opt/render/project/src/tijan-ai-logo.png',
]:
    if os.path.exists(_c):
        LOGO_PATH = _c
        break

# ── STYLES TEXTE ──────────────────────────────────────────────
def make_styles():
    return {
        'title': ParagraphStyle('title',
            fontName='Helvetica-Bold', fontSize=16,
            textColor=NOIR, spaceAfter=4, leading=20),
        'subtitle': ParagraphStyle('subtitle',
            fontName='Helvetica', fontSize=10,
            textColor=GRIS3, spaceAfter=2, leading=13),
        'h1': ParagraphStyle('h1',
            fontName='Helvetica-Bold', fontSize=11,
            textColor=VERT, spaceBefore=10, spaceAfter=4,
            leading=14, borderPad=0),
        'h2': ParagraphStyle('h2',
            fontName='Helvetica-Bold', fontSize=9,
            textColor=NOIR, spaceBefore=6, spaceAfter=3, leading=12),
        'body': ParagraphStyle('body',
            fontName='Helvetica', fontSize=8,
            textColor=NOIR, leading=11, spaceAfter=2),
        'small': ParagraphStyle('small',
            fontName='Helvetica', fontSize=7,
            textColor=GRIS3, leading=9),
        'table_header': ParagraphStyle('table_header',
            fontName='Helvetica-Bold', fontSize=7.5,
            textColor=BLANC, leading=10, alignment=TA_CENTER),
        'table_cell': ParagraphStyle('table_cell',
            fontName='Helvetica', fontSize=7.5,
            textColor=NOIR, leading=10, wordWrap='LTR'),
        'table_cell_r': ParagraphStyle('table_cell_r',
            fontName='Helvetica', fontSize=7.5,
            textColor=NOIR, leading=10, alignment=TA_RIGHT),
        'table_cell_bold': ParagraphStyle('table_cell_bold',
            fontName='Helvetica-Bold', fontSize=7.5,
            textColor=NOIR, leading=10),
        'disclaimer': ParagraphStyle('disclaimer',
            fontName='Helvetica-Oblique', fontSize=6.5,
            textColor=GRIS3, leading=9),
        'badge_ok': ParagraphStyle('badge_ok',
            fontName='Helvetica-Bold', fontSize=8,
            textColor=VERT),
        'badge_warn': ParagraphStyle('badge_warn',
            fontName='Helvetica-Bold', fontSize=8,
            textColor=colors.HexColor('#E07B00')),
    }

STYLES = make_styles()

# ── STYLE TABLEAU STANDARD ────────────────────────────────────
def table_style_base(header_rows=1, zebra=True):
    s = [
        # Header
        ('BACKGROUND',  (0,0), (-1, header_rows-1), VERT),
        ('TEXTCOLOR',   (0,0), (-1, header_rows-1), BLANC),
        ('FONTNAME',    (0,0), (-1, header_rows-1), 'Helvetica-Bold'),
        ('FONTSIZE',    (0,0), (-1, header_rows-1), 7.5),
        ('ALIGN',       (0,0), (-1, header_rows-1), 'CENTER'),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUND',(0, header_rows), (-1,-1),
            [GRIS1, BLANC] if zebra else [BLANC]),
        ('FONTNAME',    (0, header_rows), (-1,-1), 'Helvetica'),
        ('FONTSIZE',    (0, header_rows), (-1,-1), 7.5),
        ('GRID',        (0,0), (-1,-1), 0.3, GRIS2),
        ('LINEBELOW',   (0, header_rows-1), (-1, header_rows-1), 1.0, VERT),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING',(0,0), (-1,-1), 5),
        ('TOPPADDING',  (0,0), (-1,-1), 4),
        ('BOTTOMPADDING',(0,0), (-1,-1), 4),
        ('WORDWRAP',    (0,0), (-1,-1), True),
    ]
    return TableStyle(s)

def table_style_total():
    """Style pour ligne de total en bas"""
    return [
        ('BACKGROUND', (0,-1), (-1,-1), VERT_L),
        ('FONTNAME',   (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('LINEABOVE',  (0,-1), (-1,-1), 1.0, VERT),
    ]

# ── HEADER/FOOTER (canvas) ────────────────────────────────────
def draw_header_footer(canvas, doc, projet, doc_type, ref=""):
    canvas.saveState()
    w, h = PAGE

    # ── Header ──
    # Bande verte fine en haut
    canvas.setFillColor(VERT)
    canvas.rect(0, h - 8*mm, w, 8*mm, fill=1, stroke=0)

    # Logo ou texte
    if LOGO_PATH:
        try:
            canvas.drawImage(LOGO_PATH,
                MARGIN_H, h - 7*mm,
                width=28*mm, height=5.5*mm,
                preserveAspectRatio=True, mask='auto')
        except:
            canvas.setFont('Helvetica-Bold', 9)
            canvas.setFillColor(BLANC)
            canvas.drawString(MARGIN_H, h - 5.5*mm, "TIJAN AI")
    else:
        canvas.setFont('Helvetica-Bold', 9)
        canvas.setFillColor(BLANC)
        canvas.drawString(MARGIN_H, h - 5.5*mm, "TIJAN AI")

    # Tagline dans la bande verte
    canvas.setFont('Helvetica', 7)
    canvas.setFillColor(BLANC)
    canvas.drawString(MARGIN_H + 30*mm, h - 5.5*mm,
        "Engineering Intelligence for Africa")

    # Titre document (droite)
    canvas.setFont('Helvetica-Bold', 9)
    canvas.drawRightString(w - MARGIN_H, h - 5.5*mm, doc_type.upper())

    # ── Sous-header ──
    y_sub = h - 14*mm
    canvas.setFillColor(NOIR)
    canvas.setFont('Helvetica-Bold', 8)
    canvas.drawString(MARGIN_H, y_sub, projet)
    canvas.setFont('Helvetica', 7)
    canvas.setFillColor(GRIS3)
    if ref:
        canvas.drawString(MARGIN_H + 80*mm, y_sub, f"Réf. {ref}")
    canvas.drawRightString(w - MARGIN_H, y_sub,
        datetime.now().strftime("%d/%m/%Y"))

    # Ligne séparatrice
    canvas.setStrokeColor(GRIS2)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN_H, h - 16*mm, w - MARGIN_H, h - 16*mm)

    # ── Footer ──
    canvas.setStrokeColor(GRIS2)
    canvas.line(MARGIN_H, 10*mm, w - MARGIN_H, 10*mm)

    canvas.setFont('Helvetica-Oblique', 6)
    canvas.setFillColor(GRIS3)
    canvas.drawString(MARGIN_H, 6.5*mm,
        "Document d'assistance à l'ingénierie — Version bêta. "
        "Doit être vérifié et signé par un ingénieur structure habilité. "
        "Ne remplace pas l'intervention légalement obligatoire d'un bureau d'études.")

    canvas.setFont('Helvetica', 6.5)
    canvas.setFillColor(GRIS3)
    canvas.drawRightString(w - MARGIN_H, 6.5*mm,
        f"Page {doc.page} | Tijan AI © {datetime.now().year}")

    canvas.restoreState()

# ── CRÉER DOCUMENT ────────────────────────────────────────────
def creer_doc(buffer, projet, doc_type, ref=""):
    """Crée un SimpleDocTemplate paysage avec header/footer automatiques"""

    def on_page(canvas, doc):
        draw_header_footer(canvas, doc, projet, doc_type, ref)

    doc = SimpleDocTemplate(
        buffer,
        pagesize=PAGE,
        leftMargin=MARGIN_H,
        rightMargin=MARGIN_H,
        topMargin=MARGIN_V + 4*mm,
        bottomMargin=18*mm,
        title=f"{doc_type} — {projet}",
        author="Tijan AI",
        subject="Engineering Intelligence for Africa",
    )
    return doc, on_page

# ── HELPERS ───────────────────────────────────────────────────
def fmt_fcfa(v):
    """Formate un montant FCFA"""
    try:
        v = int(v)
        if v >= 1_000_000_000:
            return f"{v/1_000_000_000:.2f} Mds FCFA"
        elif v >= 1_000_000:
            return f"{v/1_000_000:.1f} M FCFA"
        else:
            return f"{v:,} FCFA".replace(',', ' ')
    except:
        return str(v)

def fmt_num(v, decimals=0, unit=""):
    try:
        if decimals == 0:
            s = f"{int(v):,}".replace(',', ' ')
        else:
            s = f"{v:.{decimals}f}"
        return f"{s} {unit}".strip()
    except:
        return str(v)

def section_header(titre, styles=STYLES):
    return [
        Spacer(1, 3*mm),
        HRFlowable(width="100%", thickness=1.5, color=VERT, spaceAfter=2),
        Paragraph(titre, styles['h1']),
    ]

def beta_banner(styles=STYLES):
    return Paragraph(
        "⚠ Version bêta — Calculs indicatifs à ±15%. "
        "Surface emprise à confirmer avec l'architecte. "
        "Tous les résultats doivent être vérifiés par un ingénieur habilité.",
        styles['disclaimer']
    )
