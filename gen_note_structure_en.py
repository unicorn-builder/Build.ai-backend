"""
gen_note_structure_en.py — English Structural Calculation Note (9 pages)
Native EN generator. Mirrors gen_note_structure.py (FR).
Signature: generer(rs, params_dict) → bytes
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
PAGE_W,PAGE_H=A4; M=20*mm

def _S():
    s=getSampleStyleSheet()
    for n,c in {
        'TT':dict(fontName='Helvetica-Bold',fontSize=18,leading=22,textColor=TIJAN_BLACK,alignment=TA_CENTER,spaceAfter=6*mm),
        'H1':dict(fontName='Helvetica-Bold',fontSize=13,leading=16,textColor=TIJAN_BLACK,spaceBefore=8*mm,spaceAfter=3*mm),
        'H2':dict(fontName='Helvetica-Bold',fontSize=11,leading=14,textColor=TIJAN_GREY,spaceBefore=4*mm,spaceAfter=2*mm),
        'BD':dict(fontName='Helvetica',fontSize=9.5,leading=13,textColor=TIJAN_BLACK,alignment=TA_JUSTIFY,spaceAfter=2*mm),
        'SM':dict(fontName='Helvetica',fontSize=8,leading=10,textColor=TIJAN_GREY,alignment=TA_CENTER),
        'NT':dict(fontName='Helvetica-Oblique',fontSize=8.5,leading=11,textColor=HexColor("#E65100"),spaceAfter=2*mm),
        'BL':dict(fontName='Helvetica',fontSize=9.5,leading=13,textColor=HexColor("#1565C0"),alignment=TA_JUSTIFY,spaceAfter=2*mm),
        'TH':dict(fontName='Helvetica-Bold',fontSize=8.5,leading=11,textColor=TIJAN_WHITE,alignment=TA_CENTER),
        'TC':dict(fontName='Helvetica',fontSize=8.5,leading=11,textColor=TIJAN_BLACK,alignment=TA_CENTER),
        'TL':dict(fontName='Helvetica',fontSize=8.5,leading=11,textColor=TIJAN_BLACK,alignment=TA_LEFT),
        'TG':dict(fontName='Helvetica-Bold',fontSize=8.5,leading=11,textColor=HexColor("#2E7D32"),alignment=TA_CENTER),
        'TO':dict(fontName='Helvetica-Bold',fontSize=8.5,leading=11,textColor=HexColor("#E65100"),alignment=TA_CENTER),
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
    canvas.drawRightString(PAGE_W-M,PAGE_H-13*mm,"Structural Calculation Note")
    canvas.setStrokeColor(TIJAN_BORDER); canvas.setLineWidth(0.5)
    canvas.line(M,12*mm,PAGE_W-M,12*mm)
    canvas.setFont("Helvetica",7); canvas.setFillColor(TIJAN_GREY)
    canvas.drawString(M,8*mm,"Tijan AI — BIM & Structural Engineering Automation")
    canvas.drawRightString(PAGE_W-M,8*mm,f"Page {doc.page}")
    canvas.restoreState()

def _ts():
    """Standard table style."""
    return TableStyle([
        ('BACKGROUND',(0,0),(-1,0),TIJAN_GREEN), ('TEXTCOLOR',(0,0),(-1,0),white),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[TIJAN_WHITE,TIJAN_LIGHT]),
        ('GRID',(0,0),(-1,-1),0.5,TIJAN_BORDER), ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),4), ('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('LEFTPADDING',(0,0),(-1,-1),6), ('RIGHTPADDING',(0,0),(-1,-1),6),
    ])

def _fmt_fcfa(val):
    if val >= 1_000_000_000: return f"{val/1_000_000_000:.1f} B FCFA"
    if val >= 1_000_000: return f"{val/1_000_000:.1f} M FCFA"
    return f"{val:,.0f} FCFA"

CW = PAGE_W - 2*M  # content width

def generer(rs, params_dict: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=22*mm, bottomMargin=18*mm, leftMargin=M, rightMargin=M)
    S = _S(); story = []; p_ = params_dict or {}

    def p(text, style='BD'):
        return Paragraph(str(text), S[style])

    nom = p_.get('nom','Project'); ville = p_.get('ville','Dakar'); pays = p_.get('pays','Senegal')
    niv = p_.get('nb_niveaux',4); surf = p_.get('surface_emprise_m2',500)
    usage = p_.get('usage','residential'); pmax = p_.get('portee_max_m',5.5); pmin = p_.get('portee_min_m',4.0)
    boq = rs.boq; ana = rs.analyse; sism = rs.sismique; fond = rs.fondation

    # ── PAGE 1 — COVER ──
    story += [Spacer(1,25*mm), p("STRUCTURAL CALCULATION NOTE",'TT'), Spacer(1,2*mm),
              p(f"{nom} — {ville}, {pays}", 'SM'), Spacer(1,4*mm),
              HRFlowable(width="60%",thickness=2,color=TIJAN_GREEN,spaceAfter=8*mm)]

    cover_data = [
        [p('PARAMETER','TH'), p('VALUE','TH'), p('STANDARD','TH')],
        [p('Project'), p(nom), p('')],
        [p('Location'), p(f'{ville}, {pays}'), p('')],
        [p('Use'), p(usage.capitalize()), p(f'EC1 cat. A' if 'resid' in usage.lower() else f'EC1')],
        [p('Levels'), p(str(niv)), p('')],
        [p('Footprint'), p(f'{surf:,.0f} m²'), p('')],
        [p('Concrete'), p(rs.classe_beton), p(f'fck = {rs.fck_MPa:.0f} MPa')],
        [p('Steel'), p(rs.classe_acier), p(f'fyk = {rs.fyk_MPa:.0f} MPa')],
        [p('Bearing pressure'), p(f'{rs.pression_sol_MPa:.3f} MPa'), p('EC7 + geotechnical study')],
        [p('Seismic zone'), p(str(rs.zone_sismique)), p('EC8 — NF EN 1998-1')],
        [p('Foundations'), p('EC7 + DTU 13.2'), p(f'qadm={rs.pression_sol_MPa} MPa — {fond.type.value}')],
    ]
    ct = Table(cover_data, colWidths=[CW*0.28,CW*0.35,CW*0.37], repeatRows=1)
    ct.setStyle(_ts())
    story += [ct, Spacer(1,10*mm),
              p("This document has been automatically generated by the Tijan AI structural engine "
                "in compliance with Eurocodes EC2 and EC8.",'SM'), PageBreak()]

    # ── PAGE 2 — MATERIALS & LOADS ──
    story.append(p("1. MATERIALS AND LOADS",'H1'))
    story.append(p("1.1 Materials Selection",'H2'))
    story.append(p(ana.justification_materiaux, 'BD'))

    story.append(p("1.2 Loads (Eurocode 1)",'H2'))
    loads_data = [
        [p('LOAD','TH'), p('VALUE','TH'), p('REFERENCE','TH')],
        [p('Dead load G'), p(f'{rs.charge_G_kNm2:.2f} kN/m²'), p('Self-weight + finishes + partitions')],
        [p('Live load Q'), p(f'{rs.charge_Q_kNm2:.2f} kN/m²'), p(f'EC1 Table 6.2 — {usage}')],
        [p('ULS combination'), p(f'{1.35*rs.charge_G_kNm2 + 1.5*rs.charge_Q_kNm2:.2f} kN/m²'), p('1.35G + 1.5Q')],
    ]
    tl = Table(loads_data, colWidths=[CW*0.28,CW*0.30,CW*0.42], repeatRows=1)
    tl.setStyle(_ts())
    story += [tl, Spacer(1,3*mm)]

    story.append(p("1.3 Exposure and Durability",'H2'))
    expo = "XS1 (coastal — chlorides)" if rs.distance_mer_km < 5 else "XC1 (internal, dry)"
    story.append(p(f'Exposure class: {expo} — Distance to sea: {rs.distance_mer_km:.1f} km. '
                   f'Design service life: 50 years. Cover per EC2 §4.4.'))
    story.append(PageBreak())

    # ── PAGE 3 — SLAB ──
    story.append(p("2. SLAB DESIGN (EC2 §6.1 + §7.4)",'H1'))
    d = rs.dalle
    slab_data = [
        [p('PARAMETER','TH'), p('VALUE','TH'), p('REMARK','TH')],
        [p('Thickness'), p(f'{d.epaisseur_mm} mm'), p('Two-way slab')],
        [p('Span'), p(f'{d.portee_m:.2f} m'), p('')],
        [p('Reinforcement X'), p(f'{d.As_x_cm2_ml:.2f} cm²/ml'), p('Bottom — span direction')],
        [p('Reinforcement Y'), p(f'{d.As_y_cm2_ml:.2f} cm²/ml'), p('Transverse direction')],
        [p('Max deflection'), p(f'{d.fleche_admissible_mm:.1f} mm'), p('L/250 limit')],
        [p('Verification'), p('✓ OK' if d.verif_ok else '⚠ Check','TG' if d.verif_ok else 'TO'), p('')],
    ]
    ts = Table(slab_data, colWidths=[CW*0.28,CW*0.32,CW*0.40], repeatRows=1)
    ts.setStyle(_ts())
    story += [ts, PageBreak()]

    # ── PAGE 4 — BEAMS ──
    story.append(p("3. BEAM DESIGN (EC2 §6.1 + §6.2)",'H1'))
    for poutre in [rs.poutre_principale, rs.poutre_secondaire]:
        if poutre is None: continue
        label = "Main beam" if poutre.type == "principale" else "Secondary beam"
        story.append(p(f"3.{'1' if poutre.type=='principale' else '2'} {label}",'H2'))
        beam_data = [
            [p('PARAMETER','TH'), p('VALUE','TH'), p('REMARK','TH')],
            [p('Section b × h'), p(f'{poutre.b_mm} × {poutre.h_mm} mm'), p('')],
            [p('Span'), p(f'{poutre.portee_m:.2f} m'), p('')],
            [p('Bottom steel As_inf'), p(f'{poutre.As_inf_cm2:.2f} cm²'), p('Span reinforcement')],
            [p('Top steel As_sup'), p(f'{poutre.As_sup_cm2:.2f} cm²'), p('Support reinforcement')],
            [p('Stirrups'), p(f'Ø{poutre.etrier_diam_mm}@{poutre.etrier_esp_mm} mm'), p('Shear reinforcement')],
            [p('Deflection check'), p('✓ OK' if poutre.verif_fleche else '⚠','TG' if poutre.verif_fleche else 'TO'), p('EC2 §7.4')],
            [p('Shear check'), p('✓ OK' if poutre.verif_effort_t else '⚠','TG' if poutre.verif_effort_t else 'TO'), p('EC2 §6.2')],
        ]
        tb = Table(beam_data, colWidths=[CW*0.28,CW*0.32,CW*0.40], repeatRows=1)
        tb.setStyle(_ts())
        story += [tb, Spacer(1,4*mm)]
    story.append(PageBreak())

    # ── PAGE 5 — COLUMNS ──
    story.append(p("4. COLUMN DESIGN (EC2 §5.8 + §6.1)",'H1'))
    col_data = [
        [p('Level','TH'), p('NEd (kN)','TH'), p('Section (mm)','TH'),
         p('Bars','TH'), p('Ø (mm)','TH'), p('Ties','TH'),
         p('ρ (%)','TH'), p('NRd/NEd','TH'), p('Check','TH')],
    ]
    for po in rs.poteaux:
        ok = po.verif_ok
        col_data.append([
            p(po.niveau), p(f'{po.NEd_kN:.0f}'), p(f'{po.section_mm}×{po.section_mm}'),
            p(str(po.nb_barres)), p(str(po.diametre_mm)),
            p(f'Ø{po.cadre_diam_mm}@{po.espacement_cadres_mm}'),
            p(f'{po.taux_armature_pct:.2f}'), p(f'{po.ratio_NEd_NRd:.2f}'),
            p('✓' if ok else '⚠', 'TG' if ok else 'TO'),
        ])
    tc = Table(col_data, colWidths=[CW*0.10,CW*0.10,CW*0.12,CW*0.08,CW*0.08,CW*0.15,CW*0.10,CW*0.12,CW*0.08], repeatRows=1)
    tc.setStyle(_ts())
    story += [tc, PageBreak()]

    # ── PAGE 6 — FOUNDATIONS ──
    story.append(p("5. FOUNDATION DESIGN (EC7 + DTU 13.2)",'H1'))
    story.append(p(f'Justification: {fond.justification}'))
    story.append(Spacer(1,2*mm))

    fond_data = [
        [p('PARAMETER','TH'), p('VALUE','TH'), p('REMARK','TH')],
        [p('Type'), p(fond.type.value), p('Adapted to soil conditions and building height')],
    ]
    if fond.nb_pieux > 0:
        fond_data += [
            [p('Pile diameter'), p(f'Ø{fond.diam_pieu_mm} mm'), p('Continuous flight auger')],
            [p('Pile length'), p(f'{fond.longueur_pieu_m:.1f} m'), p('Down to bearing stratum')],
            [p('Reinforcement'), p(f'As = {fond.As_cm2:.1f} cm²'), p('B500B cage, full length')],
            [p('Total piles'), p(str(fond.nb_pieux)), p('Estimate — confirm with geotechnical engineer')],
        ]
        # Cost note
        try:
            from prix_marche import get_prix_structure
            px = get_prix_structure(rs.params.ville)
            cout_pieux = fond.nb_pieux * fond.longueur_pieu_m * px.pieu_fore_d800_ml
            story_note = p(f'ℹ Foundation cost impact: {_fmt_fcfa(cout_pieux)} estimated '
                          f'({cout_pieux/boq.total_bas_fcfa*100:.0f}% of structural budget). '
                          f'Deep foundations = highest cost item after superstructure.', 'NT')
        except:
            story_note = None
    else:
        fond_data += [
            [p('Footing width'), p(f'{fond.largeur_semelle_m:.2f} m'), p('Square section')],
            [p('Depth'), p(f'{fond.profondeur_m:.1f} m'), p('Below frost + bearing stratum')],
        ]
        story_note = None

    tf = Table(fond_data, colWidths=[CW*0.28,CW*0.22,CW*0.50], repeatRows=1)
    tf.setStyle(_ts())
    story.append(tf)
    if story_note:
        story += [Spacer(1,2*mm), story_note]
    story.append(PageBreak())

    # ── PAGE 7 — SEISMIC ──
    story.append(p("6. SEISMIC ANALYSIS (EC8 — NF EN 1998-1)",'H1'))
    story.append(p(f'Seismic zone {sism.zone} — ag = {sism.ag_g}g — T1 = {sism.T1_s}s — Fb = {sism.Fb_kN:.0f} kN'))
    story.append(Spacer(1,2*mm))

    sism_data = [
        [p('PARAMETER','TH'), p('VALUE','TH'), p('REFERENCE','TH')],
        [p('Acceleration ag'), p(f'{sism.ag_g}g = {sism.ag_g*9.81:.2f} m/s²'), p('National annex')],
        [p('Soil factor S'), p('1.15'), p('Soil type C — EC8 Table 3.2')],
        [p('Behaviour factor q'), p('1.5 (DCL)'), p('EC8 §5.2.2.2')],
        [p('Period T1'), p(f'{sism.T1_s} s'), p('EC8 §4.3.3.2 — approximate method')],
        [p('Base shear Fb'), p(f'{sism.Fb_kN:.0f} kN'), p('Fb = Sd(T1) × m × λ')],
        [p('DCL compliance'), p('✓ Compliant' if sism.conforme_DCL else '⚠ Further analysis needed',
                                'TG' if sism.conforme_DCL else 'TO'), p('')],
    ]
    tss = Table(sism_data, colWidths=[CW*0.35,CW*0.35,CW*0.30], repeatRows=1)
    tss.setStyle(_ts())
    story.append(tss)
    story.append(Spacer(1,3*mm))
    for disp in sism.dispositions:
        prefix = '⚠' if '⚠' in disp else '•'
        story.append(p(f'{prefix} {disp.replace("⚠ ","")}'))
    story.append(PageBreak())

    # ── PAGE 8 — ANALYSIS & RECOMMENDATIONS ──
    story.append(p("7. ENGINEERING ANALYSIS AND RECOMMENDATIONS",'H1'))

    story.append(p('Engineering Summary:','H2'))
    story.append(p(ana.note_ingenieur, 'BL'))
    story.append(Spacer(1,3*mm))

    story.append(p(ana.commentaire_global))
    story.append(Spacer(1,2*mm))

    story.append(p(f'EC2 compliance: {ana.conformite_ec2}'))
    story.append(p(f'EC8 compliance: {ana.conformite_ec8}'))
    story.append(Spacer(1,3*mm))

    if ana.points_forts:
        story.append(p('Strengths:','H2'))
        for pf in ana.points_forts:
            story.append(p(f'✓ {pf}'))

    if ana.alertes:
        story.append(p('Alerts:','H2'))
        for al in ana.alertes:
            story.append(p(f'⚠ {al}', 'NT'))

    if ana.recommandations:
        story.append(p('Recommendations:','H2'))
        for r in ana.recommandations:
            story.append(p(f'→ {r}'))
    story.append(PageBreak())

    # ── PAGE 9 — BOQ SUMMARY ──
    story.append(p("8. BILL OF QUANTITIES — SUMMARY",'H1'))
    boq_data = [
        [p('ITEM','TH'), p('QUANTITY','TH'), p('COST (FCFA)','TH')],
        [p('Foundation concrete'), p(f'{boq.beton_fondation_m3:.1f} m³'), p(_fmt_fcfa(boq.cout_fond_fcfa))],
        [p('Structural concrete'), p(f'{boq.beton_structure_m3:.1f} m³'), p(_fmt_fcfa(boq.cout_beton_fcfa))],
        [p('Total concrete'), p(f'{boq.beton_total_m3:.1f} m³'), p('')],
        [p('Reinforcement steel'), p(f'{boq.acier_kg:,.0f} kg'), p(_fmt_fcfa(boq.cout_acier_fcfa))],
        [p('Formwork'), p(f'{boq.coffrage_m2:,.0f} m²'), p(_fmt_fcfa(boq.cout_coffrage_fcfa))],
        [p('Earthworks'), p(f'{boq.terrassement_m3:,.0f} m³'), p(_fmt_fcfa(boq.cout_terr_fcfa))],
        [p('Masonry'), p(f'{boq.maconnerie_m2:,.0f} m²'), p(_fmt_fcfa(boq.cout_maco_fcfa))],
        [p('Waterproofing'), p(f'{boq.etancheite_m2:,.0f} m²'), p(_fmt_fcfa(boq.cout_etanch_fcfa))],
        [p('Miscellaneous'), p(''), p(_fmt_fcfa(boq.cout_divers_fcfa))],
    ]
    tq = Table(boq_data, colWidths=[CW*0.35,CW*0.30,CW*0.35], repeatRows=1)
    tq.setStyle(_ts())
    story.append(tq)
    story.append(Spacer(1,4*mm))
    story.append(p(f'<b>TOTAL (low estimate):</b> {_fmt_fcfa(boq.total_bas_fcfa)}'))
    story.append(p(f'<b>TOTAL (high estimate):</b> {_fmt_fcfa(boq.total_haut_fcfa)}'))
    story.append(p(f'Cost per m² built: {boq.ratio_fcfa_m2_bati:,.0f} FCFA/m² '
                   f'({boq.surface_batie_m2:,.0f} m² built area)'))
    story.append(Spacer(1,6*mm))
    story.append(p('Detailed BOQ (7 lots) available via the BOQ report.'))

    # REFERENCES & DISCLAIMER
    story += [Spacer(1,8*mm), p("REFERENCES",'H2'), p(
        "EN 1990 — Basis of structural design<br/>EN 1991 — Actions on structures<br/>"
        "EN 1992-1-1 — Design of concrete structures<br/>EN 1997-1 — Geotechnical design<br/>"
        "EN 1998-1 — Seismic design<br/>DTU 13.2 — Deep foundations")]
    story += [Spacer(1,8*mm), HRFlowable(width="100%",thickness=0.5,color=TIJAN_BORDER,spaceAfter=3*mm),
              p("<b>Disclaimer:</b> This document has been generated automatically by the Tijan AI engine. "
                "It must be reviewed and validated by a qualified structural engineer before any construction. "
                "Tijan AI accepts no liability for use without professional verification.",'SM')]

    doc.build(story, onFirstPage=_hf, onLaterPages=_hf)
    buf.seek(0); return buf.read()
