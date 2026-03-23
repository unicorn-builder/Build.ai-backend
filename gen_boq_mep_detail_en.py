"""
gen_boq_mep_detail_en.py — English MEP Detailed Bill of Quantities (7 lots × 3 tiers)
Native EN generator. Mirrors gen_boq_mep_detail.py (FR).
Signature: generer_boq_mep_detail(rm, params_dict) → bytes
Uses REAL dataclass fields from engine_mep_v2.py.
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
PAGE_W,PAGE_H=A4; M=20*mm; CW=PAGE_W-2*M

LOT_EN = {
    "Électricité":"Electrical","Electricité":"Electrical",
    "Plomberie":"Plumbing","CVC / Climatisation":"HVAC","CVC":"HVAC","Climatisation":"HVAC",
    "Courants faibles":"Low Current","Sécurité incendie":"Fire Safety",
    "Ascenseurs":"Lifts","Automatisation":"Building Automation",
}

def _S():
    s=getSampleStyleSheet()
    for n,c in {
        'TT':dict(fontName='Helvetica-Bold',fontSize=18,leading=22,textColor=TIJAN_BLACK,alignment=TA_CENTER,spaceAfter=6*mm),
        'H1':dict(fontName='Helvetica-Bold',fontSize=13,leading=16,textColor=TIJAN_BLACK,spaceBefore=6*mm,spaceAfter=3*mm),
        'H2':dict(fontName='Helvetica-Bold',fontSize=11,leading=14,textColor=TIJAN_GREY,spaceBefore=4*mm,spaceAfter=2*mm),
        'BD':dict(fontName='Helvetica',fontSize=9.5,leading=13,textColor=TIJAN_BLACK,alignment=TA_JUSTIFY,spaceAfter=2*mm),
        'SM':dict(fontName='Helvetica',fontSize=8,leading=10,textColor=TIJAN_GREY,alignment=TA_CENTER),
        'NT':dict(fontName='Helvetica-Oblique',fontSize=8.5,leading=11,textColor=HexColor("#E65100"),spaceAfter=2*mm),
        'TH':dict(fontName='Helvetica-Bold',fontSize=7.5,leading=10,textColor=TIJAN_WHITE,alignment=TA_CENTER),
        'TC':dict(fontName='Helvetica',fontSize=7.5,leading=10,textColor=TIJAN_BLACK,alignment=TA_CENTER),
        'TL':dict(fontName='Helvetica',fontSize=7.5,leading=10,textColor=TIJAN_BLACK,alignment=TA_LEFT),
        'TR':dict(fontName='Helvetica',fontSize=7.5,leading=10,textColor=TIJAN_BLACK,alignment=TA_RIGHT),
        'TB':dict(fontName='Helvetica-Bold',fontSize=7.5,leading=10,textColor=TIJAN_BLACK,alignment=TA_RIGHT),
        'TBW':dict(fontName='Helvetica-Bold',fontSize=7.5,leading=10,textColor=TIJAN_WHITE,alignment=TA_RIGHT),
        'TLW':dict(fontName='Helvetica-Bold',fontSize=7.5,leading=10,textColor=TIJAN_WHITE,alignment=TA_LEFT),
    }.items():
        s.add(ParagraphStyle(name=n,**c))
    return s

def _hf(canvas,doc):
    canvas.saveState()
    canvas.setStrokeColor(TIJAN_GREEN);canvas.setLineWidth(1.5)
    canvas.line(M,PAGE_H-15*mm,PAGE_W-M,PAGE_H-15*mm)
    canvas.setFont("Helvetica-Bold",8);canvas.setFillColor(TIJAN_BLACK)
    canvas.drawString(M,PAGE_H-13*mm,"TIJAN AI")
    canvas.setFont("Helvetica",8);canvas.setFillColor(TIJAN_GREY)
    canvas.drawRightString(PAGE_W-M,PAGE_H-13*mm,"MEP Bill of Quantities")
    canvas.setStrokeColor(TIJAN_BORDER);canvas.setLineWidth(0.5)
    canvas.line(M,12*mm,PAGE_W-M,12*mm)
    canvas.setFont("Helvetica",7);canvas.setFillColor(TIJAN_GREY)
    canvas.drawString(M,8*mm,"Tijan AI — BIM & MEP Engineering Automation")
    canvas.drawRightString(PAGE_W-M,8*mm,f"Page {doc.page}")
    canvas.restoreState()

def _fmt(v):
    if isinstance(v,(int,float)):
        if v>=1e9: return f"{v/1e9:.1f}B"
        if v>=1e6: return f"{v/1e6:.1f}M"
        return f"{v:,.0f}"
    return str(v)

def _ts():
    return TableStyle([
        ('BACKGROUND',(0,0),(-1,0),TIJAN_GREEN),('TEXTCOLOR',(0,0),(-1,0),white),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[TIJAN_WHITE,TIJAN_LIGHT]),
        ('GRID',(0,0),(-1,-1),0.5,TIJAN_BORDER),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
    ])


def generer_boq_mep_detail(rm, params_dict: dict) -> bytes:
    buf=io.BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,topMargin=22*mm,bottomMargin=18*mm,leftMargin=M,rightMargin=M)
    S=_S();story=[];p_=params_dict or{}
    bmep=rm.boq

    def p(t,st='BD'): return Paragraph(str(t),S[st])

    # COVER
    story+=[Spacer(1,25*mm),p("MEP BILL OF QUANTITIES",'TT'),
            p("Electrical · Plumbing · HVAC · Fire · Lifts · Automation",'SM'),
            Spacer(1,3*mm),HRFlowable(width="60%",thickness=2,color=TIJAN_GREEN,spaceAfter=8*mm)]

    cover=[
        [p('PARAMETER','TH'),p('VALUE','TH')],
        [p('Project'),p(p_.get('nom','Project'))],
        [p('Location'),p(f"{p_.get('ville','Dakar')}, {p_.get('pays','Senegal')}")],
        [p('Built area'),p(f'{rm.surf_batie_m2:,.0f} m²')],
        [p('Units'),p(str(rm.nb_logements))],
        [p('Currency'),p('FCFA (XOF)')],
        [p('Tiers'),p('Basic / High-End / Luxury')],
    ]
    ct=Table(cover,colWidths=[CW*0.30,CW*0.70],repeatRows=1);ct.setStyle(_ts())
    story+=[ct,Spacer(1,8*mm),
            p("Three pricing tiers allow the owner to choose finish level per lot.",'SM'),PageBreak()]

    # DETAIL BY LOT
    story.append(p("DETAILED BREAKDOWN BY LOT",'H1'))
    for lot in bmep.lots:
        designation_en = LOT_EN.get(lot.designation, lot.designation)
        story.append(p(f"Lot {lot.lot} — {designation_en}",'H2'))
        lot_data=[
            [p('PARAMETER','TH'),p('VALUE','TH')],
            [p('Unit'),p(lot.unite)],
            [p('Quantity'),p(f'{lot.quantite:,.0f}')],
            [p('Basic (FCFA)'),p(f'{_fmt(lot.pu_basic_fcfa)}','TR')],
            [p('High-End (FCFA)'),p(f'{_fmt(lot.pu_hend_fcfa)}','TR')],
            [p('Luxury (FCFA)'),p(f'{_fmt(lot.pu_luxury_fcfa)}','TR')],
        ]
        tl=Table(lot_data,colWidths=[CW*0.40,CW*0.60],repeatRows=1);tl.setStyle(_ts())
        story.append(tl)
        if lot.note_impact:
            story.append(p(f'ℹ {lot.note_impact}','NT'))
        story.append(Spacer(1,3*mm))

    story.append(PageBreak())

    # SUMMARY TABLE
    story.append(p("SUMMARY BY LOT",'H1'))
    sum_data=[
        [p('LOT','TH'),p('DESCRIPTION','TH'),p('BASIC','TH'),p('HIGH-END','TH'),p('LUXURY','TH')],
    ]
    for lot in bmep.lots:
        designation_en=LOT_EN.get(lot.designation,lot.designation)
        sum_data.append([
            p(lot.lot),p(designation_en,'TL'),
            p(_fmt(lot.pu_basic_fcfa),'TR'),p(_fmt(lot.pu_hend_fcfa),'TR'),p(_fmt(lot.pu_luxury_fcfa),'TR'),
        ])
    # Totals
    sum_data.append([p(''),p('<b>TOTAL EXCL. TAX</b>','TLW'),
                     p(f'<b>{_fmt(bmep.total_basic_fcfa)}</b>','TBW'),
                     p(f'<b>{_fmt(bmep.total_hend_fcfa)}</b>','TBW'),
                     p(f'<b>{_fmt(bmep.total_luxury_fcfa)}</b>','TBW')])
    tva_b=int(bmep.total_basic_fcfa*0.18);tva_h=int(bmep.total_hend_fcfa*0.18);tva_l=int(bmep.total_luxury_fcfa*0.18)
    sum_data.append([p(''),p('<b>VAT (18%)</b>','TLW'),
                     p(f'<b>{_fmt(tva_b)}</b>','TBW'),p(f'<b>{_fmt(tva_h)}</b>','TBW'),p(f'<b>{_fmt(tva_l)}</b>','TBW')])
    sum_data.append([p(''),p('<b>TOTAL INCL. TAX</b>','TLW'),
                     p(f'<b>{_fmt(bmep.total_basic_fcfa+tva_b)}</b>','TBW'),
                     p(f'<b>{_fmt(bmep.total_hend_fcfa+tva_h)}</b>','TBW'),
                     p(f'<b>{_fmt(bmep.total_luxury_fcfa+tva_l)}</b>','TBW')])

    ts=Table(sum_data,colWidths=[CW*0.08,CW*0.32,CW*0.20,CW*0.20,CW*0.20],repeatRows=1)
    ts.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),TIJAN_GREEN),('TEXTCOLOR',(0,0),(-1,0),white),
        ('ROWBACKGROUNDS',(0,1),(-1,-4),[TIJAN_WHITE,TIJAN_LIGHT]),
        ('BACKGROUND',(0,-3),(-1,-1),TIJAN_GREEN),('TEXTCOLOR',(0,-3),(-1,-1),white),
        ('GRID',(0,0),(-1,-1),0.5,TIJAN_BORDER),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
    ]))
    story.append(ts)

    # RATIOS
    story+=[Spacer(1,6*mm),p("COST RATIOS",'H2'),
            p(f'<b>Basic:</b> {bmep.ratio_basic_m2:,.0f} FCFA/m² | '
              f'<b>High-End:</b> {bmep.ratio_hend_m2:,.0f} FCFA/m²<br/>'
              f'<b>Recommendation:</b> {bmep.recommandation}')]
    if bmep.note_choix:
        story.append(p(f'<i>{bmep.note_choix}</i>'))

    # NOTES
    story+=[Spacer(1,6*mm),p("NOTES",'H2'),p(
        "1. Three tiers: Basic (standard), High-End (quality), Luxury (premium).<br/>"
        "2. Prices from validated local market data (Senegal, Côte d'Ivoire, Morocco).<br/>"
        "3. Labour, testing, and commissioning included per lot.<br/>"
        "4. Owner selects tier per lot — mix-and-match is supported.<br/>"
        "5. Prices valid at date of generation — subject to market fluctuation.")]

    story+=[Spacer(1,8*mm),HRFlowable(width="100%",thickness=0.5,color=TIJAN_BORDER,spaceAfter=3*mm),
            p("<b>Disclaimer:</b> This BOQ has been generated automatically. "
              "Final prices must be confirmed with the MEP contractor.",'SM')]

    doc.build(story,onFirstPage=_hf,onLaterPages=_hf)
    buf.seek(0);return buf.read()
