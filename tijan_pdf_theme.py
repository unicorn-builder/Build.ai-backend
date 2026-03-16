"""
tijan_pdf_theme.py — Module commun Tijan AI
Header/footer avec logo, styles typographiques, palette couleurs
Utilisé par tous les générateurs PDF
"""
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage
)

# ── Palette ────────────────────────────────────────────────
VERT    = colors.HexColor('#43A956')
NOIR    = colors.HexColor('#111111')
GRIS    = colors.HexColor('#555555')
GRIS_L  = colors.HexColor('#888888')
FOND    = colors.HexColor('#FAFAFA')
BORD    = colors.HexColor('#E5E5E5')
BLANC   = colors.white
VERT_P  = colors.HexColor('#F0FAF1')
ROUGE   = colors.HexColor('#DC2626')
ORANGE  = colors.HexColor('#F59E0B')

# Chemin logo — cherche dans le répertoire du fichier puis /opt/render/project/src
_HERE = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = None
for candidate in [
    os.path.join(_HERE, 'tijan_logo_crop.png'),
    os.path.join(_HERE, 'tijan_logo.png'),
    '/opt/render/project/src/tijan_logo_crop.png',
    '/opt/render/project/src/tijan_logo.png',
]:
    if os.path.exists(candidate):
        LOGO_PATH = candidate
        break


def get_styles():
    """Retourne le dictionnaire de styles typographiques Tijan."""
    def ps(n, **kw):
        d = dict(fontName='Helvetica', fontSize=8, leading=11,
                 textColor=NOIR, wordWrap='LTR')
        d.update(kw)
        return ParagraphStyle(n, **d)

    return {
        'brand':    ps('brand', fontSize=7, textColor=VERT, fontName='Helvetica-Bold'),
        'ei':       ps('ei', fontSize=7, textColor=GRIS_L),
        'titre':    ps('titre', fontSize=16, fontName='Helvetica-Bold', leading=20, textColor=NOIR),
        'sous_titre': ps('sous_titre', fontSize=10, textColor=VERT, fontName='Helvetica-Bold', leading=14),
        'sub':      ps('sub', fontSize=8, textColor=GRIS),
        'h2':       ps('h2', fontSize=10, fontName='Helvetica-Bold', textColor=VERT,
                       spaceBefore=8, spaceAfter=4),
        'h3':       ps('h3', fontSize=9, fontName='Helvetica-Bold', spaceBefore=5, spaceAfter=3),
        'normal':   ps('normal'),
        'small':    ps('small', fontSize=7, textColor=GRIS_L),
        'bold':     ps('bold', fontName='Helvetica-Bold'),
        'center':   ps('center', alignment=TA_CENTER),
        'right':    ps('right', alignment=TA_RIGHT),
        'vert':     ps('vert', textColor=VERT, fontName='Helvetica-Bold'),
        'rouge':    ps('rouge', textColor=ROUGE, fontName='Helvetica-Bold'),
        'rb':       ps('rb', fontName='Helvetica-Bold', alignment=TA_RIGHT),
        'cb':       ps('cb', fontName='Helvetica-Bold', alignment=TA_CENTER),
        'green9':   ps('green9', fontSize=9, fontName='Helvetica-Bold', textColor=VERT),
        'disc':     ps('disc', fontSize=7, textColor=GRIS_L, leading=10),
        'warn':     ps('warn', fontSize=7, textColor=colors.HexColor('#92400E')),
    }


def fmt(n, sep=' '):
    """Formate un nombre avec séparateur de milliers."""
    try:
        return f"{int(round(float(n))):,}".replace(',', sep)
    except Exception:
        return str(n)


def build_header_footer(canvas, doc, projet_nom, doc_type, page_ref=""):
    """
    En-tête et pied de page Tijan AI sur chaque page.
    Logo à gauche, infos projet à droite.
    """
    canvas.saveState()
    w, h = A4

    # ── EN-TÊTE ───────────────────────────────────────────
    # Ligne verte en haut
    canvas.setStrokeColor(VERT)
    canvas.setLineWidth(1.5)
    canvas.line(15*mm, h - 12*mm, w - 15*mm, h - 12*mm)

    # Logo à gauche
    if LOGO_PATH:
        try:
            logo_h = 7*mm
            logo_w = logo_h * (1022 / 192)  # ratio logo
            canvas.drawImage(LOGO_PATH, 15*mm, h - 11*mm,
                           width=logo_w, height=logo_h,
                           preserveAspectRatio=True, mask='auto')
        except Exception:
            # Fallback texte si logo indispo
            canvas.setFont('Helvetica-Bold', 9)
            canvas.setFillColor(VERT)
            canvas.drawString(15*mm, h - 10*mm, "TIJAN AI")

    # Infos projet à droite
    canvas.setFont('Helvetica', 7)
    canvas.setFillColor(GRIS)
    canvas.drawRightString(w - 15*mm, h - 9*mm, projet_nom)
    canvas.setFont('Helvetica', 6)
    canvas.setFillColor(GRIS_L)
    canvas.drawRightString(w - 15*mm, h - 12.5*mm, doc_type)

    # ── PIED DE PAGE ─────────────────────────────────────
    # Ligne grise en bas
    canvas.setStrokeColor(BORD)
    canvas.setLineWidth(0.5)
    canvas.line(15*mm, 12*mm, w - 15*mm, 12*mm)

    # Tagline gauche
    canvas.setFont('Helvetica', 6)
    canvas.setFillColor(GRIS_L)
    canvas.drawString(15*mm, 8*mm, "Tijan AI — Engineering Intelligence for Africa")

    # Numéro de page droite
    canvas.drawRightString(w - 15*mm, 8*mm,
        f"Page {doc.page}  |  {datetime.now().strftime('%d/%m/%Y')}")

    # Disclaimer centré
    canvas.setFont('Helvetica', 5.5)
    canvas.setFillColor(GRIS_L)
    disclaimer = "Document d'assistance — Doit être vérifié et signé par un ingénieur habilité avant tout usage officiel"
    canvas.drawCentredString(w/2, 5*mm, disclaimer)

    canvas.restoreState()


def make_doc(buf, nom_projet, doc_type, marges=(15, 15, 20, 16)):
    """Crée un SimpleDocTemplate avec les marges standard Tijan."""
    l, r, t, b = marges
    return SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=l*mm, rightMargin=r*mm,
        topMargin=t*mm, bottomMargin=b*mm,
        title=f"{doc_type} — {nom_projet}",
        author="Tijan AI",
    )


def page_garde(nom, ville, doc_type, sous_titre, ref="1711-STR", extra_infos=None):
    """
    Génère les éléments de la page de garde.
    Retourne une liste d'éléments Platypus.
    """
    s = get_styles()
    story = []

    # Logo grande taille
    if LOGO_PATH:
        try:
            logo_h = 14*mm
            logo_w = logo_h * (1022 / 192)
            story.append(RLImage(LOGO_PATH, width=logo_w, height=logo_h))
        except Exception:
            story.append(Paragraph("TIJAN AI", ParagraphStyle('lg', fontSize=18,
                                   fontName='Helvetica-Bold', textColor=VERT)))
    else:
        story.append(Paragraph("TIJAN AI", ParagraphStyle('lg', fontSize=18,
                               fontName='Helvetica-Bold', textColor=VERT)))

    story += [
        Paragraph("Engineering Intelligence for Africa", s['ei']),
        Spacer(1, 6*mm),
        HRFlowable(width="100%", thickness=1.5, color=VERT),
        Spacer(1, 5*mm),
        Paragraph(doc_type.upper(), s['titre']),
        Paragraph(sous_titre, s['sous_titre']),
        Spacer(1, 6*mm),
    ]

    # Tableau infos projet
    infos = [
        ["PROJET", nom],
        ["RÉFÉRENCE", ref],
        ["LOCALISATION", f"{ville}, Sénégal"],
        ["DATE", datetime.now().strftime("%d %B %Y")],
        ["INGÉNIEUR", "À compléter par l'ingénieur responsable"],
    ]
    if extra_infos:
        infos.extend(extra_infos)

    ti = Table(infos, colWidths=[42*mm, 133*mm])
    ti.setStyle(TableStyle([
        ('FONTNAME',   (0,0),(0,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR',  (0,0),(0,-1), VERT),
        ('FONTSIZE',   (0,0),(-1,-1), 8),
        ('GRID',       (0,0),(-1,-1), 0.3, BORD),
        ('BACKGROUND', (0,0),(-1,-1), FOND),
        ('TOPPADDING',    (0,0),(-1,-1), 5),
        ('BOTTOMPADDING', (0,0),(-1,-1), 5),
        ('LEFTPADDING',   (0,0),(-1,-1), 8),
        ('VALIGN',     (0,0),(-1,-1), 'MIDDLE'),
    ]))
    story.append(ti)

    # Zone signature
    story += [
        Spacer(1, 8*mm),
        HRFlowable(width="100%", thickness=0.5, color=BORD),
        Spacer(1, 3*mm),
    ]
    sig = Table([
        [Paragraph("VÉRIFIÉ PAR", s['small']),
         Paragraph("DATE DE VALIDATION", s['small']),
         Paragraph("SIGNATURE & CACHET", s['small'])],
        ["", "", ""],
    ], colWidths=[58*mm, 58*mm, 59*mm])
    sig.setStyle(TableStyle([
        ('FONTSIZE',   (0,0),(-1,-1), 7),
        ('GRID',       (0,0),(-1,-1), 0.3, BORD),
        ('BACKGROUND', (0,0),(-1,0), FOND),
        ('ROWHEIGHTS', (0,1),(-1,1), 18*mm),
        ('TOPPADDING',    (0,0),(-1,-1), 4),
        ('BOTTOMPADDING', (0,0),(-1,-1), 4),
        ('LEFTPADDING',   (0,0),(-1,-1), 6),
    ]))
    story.append(sig)
    story += [
        Spacer(1, 5*mm),
        Paragraph(
            "Ce document constitue une assistance à la conception. Il doit être vérifié et signé "
            "par un ingénieur habilité avant toute utilisation officielle. "
            "Tijan AI ne se substitue pas à un bureau d'études, dont l'intervention est légalement obligatoire.",
            s['disc']
        ),
    ]
    return story


def table_style_base(n_rows, header=True):
    """Style de tableau standard Tijan."""
    style = [
        ('GRID',          (0,0),(-1,-1), 0.3, BORD),
        ('FONTSIZE',      (0,0),(-1,-1), 8),
        ('TOPPADDING',    (0,0),(-1,-1), 4),
        ('BOTTOMPADDING', (0,0),(-1,-1), 4),
        ('LEFTPADDING',   (0,0),(-1,-1), 6),
        ('RIGHTPADDING',  (0,0),(-1,-1), 6),
        ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
        ('WORDWRAP',      (0,0),(-1,-1), 'LTR'),
    ]
    if header:
        style += [
            ('BACKGROUND', (0,0),(-1,0), VERT),
            ('TEXTCOLOR',  (0,0),(-1,0), BLANC),
            ('FONTNAME',   (0,0),(-1,0), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0,1),(-1,-1), [BLANC, FOND]),
        ]
    return TableStyle(style)


def section_header(titre, story, s):
    """Ajoute un séparateur de section."""
    story += [
        Spacer(1, 2*mm),
        Paragraph("TIJAN AI", s['brand']),
        HRFlowable(width="100%", thickness=0.5, color=BORD),
        Spacer(1, 2*mm),
    ]
