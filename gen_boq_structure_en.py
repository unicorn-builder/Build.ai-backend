"""
gen_boq_structure_en.py — English Structural Bill of Quantities (7 lots)
Native EN generator. Mirrors gen_boq_structure.py (FR).
Signature: generer_boq_structure(rs, params_dict) → bytes
Uses REAL dataclass fields from engine_structure_v2.py.
"""

import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.platypus.flowables import HRFlowable

TIJAN_BLACK=HexColor("#111111"); TIJAN_GREY=HexColor("#555555"); TIJAN_GREEN=HexColor("#43A956")
TIJAN_LIGHT=HexColor("#FAFAFA"); TIJAN_WHITE=HexColor("#FFFFFF"); TIJAN_BORDER=HexColor("#E0E0E0")
TIJAN_SUB=HexColor("#E8F5E9")
PAGE_W,PAGE_H=A4; M=20*mm

def _S():
    s=getSampleStyleSheet()
    for n,c in {
        'TT':dict(fontName='Helvetica-Bold',fontSize=18,leading=22,textColor=TIJAN_BLACK,alignment=TA_CENTER,spaceAfter=6*mm),
        'H1':dict(fontName='Helvetica-Bold',fontSize=13,leading=16,textColor=TIJAN_BLACK,spaceBefore=8*mm,spaceAfter=3*mm),
        'H2':dict(fontName='Helvetica-Bold',fontSize=11,leading=14,textColor=TIJAN_GREY,spaceBefore=4*mm,spaceAfter=2*mm),
        'BD':dict(fontName='Helvetica',fontSize=9.5,leading=13,textColor=TIJAN_BLACK,alignment=TA_JUSTIFY,spaceAfter=2*mm),
        'SM':dict(fontName='Helvetica',fontSize=8,leading=10,textColor=TIJAN_GREY,alignment=TA_CENTER),
        'TH':dict(fontName='Helvetica-Bold',fontSize=8.5,leading=11,textColor=TIJAN_WHITE,alignment=TA_CENTER),
        'TC':dict(fontName='Helvetica',fontSize=8.5,leading=11,textColor=TIJAN_BLACK,alignment=TA_CENTER),
        'TL':dict(fontName='Helvetica',fontSize=8.5,leading=11,textColor=TIJAN_BLACK,alignment=TA_LEFT),
        'TR':dict(fontName='Helvetica',fontSize=8.5,leading=11,textColor=TIJAN_BLACK,alignment=TA_RIGHT),
        'TB':dict(fontName='Helvetica-Bold',fontSize=8.5,leading=11,textColor=TIJAN_BLACK,alignment=TA_RIGHT),
        'TBW':dict(fontName='Helvetica-Bold',fontSize=8.5,leading=11,textColor=TIJAN_WHITE,alignment=TA_RIGHT),
    }.items():
        s.add(ParagraphStyle(name=n,**c))
    return s

def _hf(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(TIJAN_GREEN); canvas.setLineWidth(1.5)
    canvas.line(M,PAGE_H-15*mm,PAGE_W-M,PAGE_H-15*mm)
    canvas.setFont("Helvetica-Bold",8); canvas.setFillColor(TIJAN_BLACK)
    canvas.drawString(M,PAGE_H-13*mm,"TIJAN AI")
    canvas.setFont("Helvetica",8); canvas.setFillColor(TIJAN_GREY)
    canvas.drawRightString(PAGE_W-M,PAGE_H-13*mm,"Structural Bill of Quantities")
    canvas.setStrokeColor(TIJAN_BORDER); canvas.setLineWidth(0.5)
    canvas.line(M,12*mm,PAGE_W-M,12*mm)
    canvas.setFont("Helvetica",7); canvas.setFillColor(TIJAN_GREY)
    canvas.drawString(M,8*mm,"Tijan AI — BIM & Structural Engineering Automation")
    canvas.drawRightString(PAGE_W-M,8*mm,f"Page {doc.page}")
    canvas.restoreState()

def _fmt(v):
    if isinstance(v,(int,float)):
        if v>=1_000_000: return f"{v/1_000_000:.1f} M"
        return f"{v:,.0f}"
    return str(v)

CW = PAGE_W - 2*M

def generer_boq_structure(rs, params_dict: dict) -> bytes:
    buf=io.BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,topMargin=22*mm,bottomMargin=18*mm,leftMargin=M,rightMargin=M)
    S=_S(); story=[]; p_=params_dict or {}
    boq=rs.boq

    def p(text,style='BD'): return Paragraph(str(text),S[style])

    # COVER
    story += [Spacer(1,25*mm), p("STRUCTURAL BILL OF QUANTITIES",'TT'),
              p(f"{p_.get('nom','Project')} — {p_.get('ville','Dakar')}, {p_.get('pays','Senegal')}", 'SM'),
              Spacer(1,4*mm), HRFlowable(width="60%",thickness=2,color=TIJAN_GREEN,spaceAfter=8*mm)]

    cover = [
        [p('PARAMETER','TH'), p('VALUE','TH')],
        [p('Project'), p(p_.get('nom','Project'))],
        [p('Location'), p(f"{p_.get('ville','Dakar')}, {p_.get('pays','Senegal')}")],
        [p('Concrete'), p(rs.classe_beton)],
        [p('Steel'), p(rs.classe_acier)],
        [p('Currency'), p('FCFA (XOF)')],
        [p('Built area'), p(f'{boq.surface_batie_m2:,.0f} m²')],
    ]
    ct=Table(cover,colWidths=[CW*0.35,CW*0.65],repeatRows=1); ct.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),TIJAN_GREEN),('TEXTCOLOR',(0,0),(-1,0),white),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[TIJAN_WHITE,TIJAN_LIGHT]),
        ('GRID',(0,0),(-1,-1),0.5,TIJAN_BORDER),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LEFTPADDING',(0,0),(-1,-1),8),
    ]))
    story += [ct, Spacer(1,8*mm),
              p("Quantities from Tijan AI structural engine. Prices from validated local market data.",'SM'),
              PageBreak()]

    # BOQ TABLE
    story.append(p("DETAILED BILL OF QUANTITIES",'H1'))

    rows = [
        [p('LOT','TH'), p('DESCRIPTION','TH'), p('QUANTITY','TH'), p('LOW EST. (FCFA)','TH'), p('HIGH EST. (FCFA)','TH')],
        [p('1'), p('Earthworks'), p(f'{boq.terrassement_m3:,.0f} m³'), p(_fmt(boq.cout_terr_fcfa),'TR'), p('','TR')],
        [p('2'), p('Foundations'), p(f'{boq.beton_fondation_m3:,.1f} m³ concrete'), p(_fmt(boq.cout_fond_fcfa),'TR'), p('','TR')],
        [p('3'), p('Concrete — Superstructure'), p(f'{boq.beton_structure_m3:,.1f} m³'), p(_fmt(boq.cout_beton_fcfa),'TR'), p('','TR')],
        [p('4'), p('Reinforcement steel'), p(f'{boq.acier_kg:,.0f} kg'), p(_fmt(boq.cout_acier_fcfa),'TR'), p('','TR')],
        [p('5'), p('Formwork'), p(f'{boq.coffrage_m2:,.0f} m²'), p(_fmt(boq.cout_coffrage_fcfa),'TR'), p('','TR')],
        [p('6'), p('Masonry / Partitions'), p(f'{boq.maconnerie_m2:,.0f} m²'), p(_fmt(boq.cout_maco_fcfa),'TR'), p('','TR')],
        [p('7'), p('Waterproofing + Misc.'), p(f'{boq.etancheite_m2:,.0f} m² + misc'), p(_fmt(boq.cout_etanch_fcfa + boq.cout_divers_fcfa),'TR'), p('','TR')],
    ]
    # Total rows
    rows.append([p(''), p('<b>TOTAL EXCL. TAX</b>'), p(''), p(f'<b>{_fmt(boq.total_bas_fcfa)}</b>','TBW'), p(f'<b>{_fmt(boq.total_haut_fcfa)}</b>','TBW')])
    tva_b = int(boq.total_bas_fcfa*0.18); tva_h = int(boq.total_haut_fcfa*0.18)
    rows.append([p(''), p('<b>VAT (18%)</b>'), p(''), p(f'<b>{_fmt(tva_b)}</b>','TBW'), p(f'<b>{_fmt(tva_h)}</b>','TBW')])
    rows.append([p(''), p('<b>TOTAL INCL. TAX</b>'), p(''), p(f'<b>{_fmt(boq.total_bas_fcfa+tva_b)}</b>','TBW'), p(f'<b>{_fmt(boq.total_haut_fcfa+tva_h)}</b>','TBW')])

    tb=Table(rows,colWidths=[CW*0.06,CW*0.30,CW*0.24,CW*0.20,CW*0.20],repeatRows=1)
    tb.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),TIJAN_GREEN),('TEXTCOLOR',(0,0),(-1,0),white),
        ('ROWBACKGROUNDS',(0,1),(-1,-4),[TIJAN_WHITE,TIJAN_LIGHT]),
        ('BACKGROUND',(0,-3),(-1,-1),TIJAN_GREEN),('TEXTCOLOR',(0,-3),(-1,-1),white),
        ('GRID',(0,0),(-1,-1),0.5,TIJAN_BORDER),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
    ]))
    story.append(tb)

    # RATIOS
    story += [Spacer(1,6*mm), p("COST RATIOS",'H2'),
              p(f'Cost per m² built: {boq.ratio_fcfa_m2_bati:,.0f} FCFA/m²<br/>'
                f'Built area: {boq.surface_batie_m2:,.0f} m² — Habitable: {boq.surface_habitable_m2:,.0f} m²')]

    # NOTES
    story += [Spacer(1,6*mm), p("NOTES",'H2'), p(
        "1. Steel: Fabrimetal Sénégal (Sébikotane), 480–600 FCFA/kg.<br/>"
        "2. Concrete: ready-mix C30/37, CIMAF/SOCOCIM, 185,000 FCFA/m³ delivered.<br/>"
        "3. Low/High estimates reflect market price range.<br/>"
        "4. Quantities from structural engine — may vary ±10% during detailed design.<br/>"
        "5. Prices valid at date of generation — subject to market fluctuation.")]

    story += [Spacer(1,8*mm), HRFlowable(width="100%",thickness=0.5,color=TIJAN_BORDER,spaceAfter=3*mm),
              p("<b>Disclaimer:</b> This BOQ has been generated automatically. "
                "Final quantities and prices must be confirmed with the contractor.",'SM')]

    doc.build(story,onFirstPage=_hf,onLaterPages=_hf)
    buf.seek(0); return buf.read()
