"""
gen_mep_en.py — English MEP Technical Note + EDGE Report + Executive Report
Native EN generator. Mirrors gen_mep.py (FR).
Signatures:
  generer_note_mep(rm, params_dict) → bytes
  generer_edge(rm, params_dict) → bytes
  generer_rapport_executif(rs, rm, params_dict) → bytes
Uses REAL dataclass fields from engine_mep_v2.py and engine_structure_v2.py.
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
        'TR':dict(fontName='Helvetica',fontSize=8.5,leading=11,textColor=TIJAN_BLACK,alignment=TA_RIGHT),
        'TG':dict(fontName='Helvetica-Bold',fontSize=8.5,leading=11,textColor=HexColor("#2E7D32"),alignment=TA_CENTER),
    }.items():
        s.add(ParagraphStyle(name=n,**c))
    return s

def _hf(title_en):
    def _cb(canvas,doc):
        canvas.saveState()
        canvas.setStrokeColor(TIJAN_GREEN);canvas.setLineWidth(1.5)
        canvas.line(M,PAGE_H-15*mm,PAGE_W-M,PAGE_H-15*mm)
        canvas.setFont("Helvetica-Bold",8);canvas.setFillColor(TIJAN_BLACK)
        canvas.drawString(M,PAGE_H-13*mm,"TIJAN AI")
        canvas.setFont("Helvetica",8);canvas.setFillColor(TIJAN_GREY)
        canvas.drawRightString(PAGE_W-M,PAGE_H-13*mm,title_en)
        canvas.setStrokeColor(TIJAN_BORDER);canvas.setLineWidth(0.5)
        canvas.line(M,12*mm,PAGE_W-M,12*mm)
        canvas.setFont("Helvetica",7);canvas.setFillColor(TIJAN_GREY)
        canvas.drawString(M,8*mm,"Tijan AI — BIM & MEP Engineering Automation")
        canvas.drawRightString(PAGE_W-M,8*mm,f"Page {doc.page}")
        canvas.restoreState()
    return _cb

def _ts():
    return TableStyle([
        ('BACKGROUND',(0,0),(-1,0),TIJAN_GREEN),('TEXTCOLOR',(0,0),(-1,0),white),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[TIJAN_WHITE,TIJAN_LIGHT]),
        ('GRID',(0,0),(-1,-1),0.5,TIJAN_BORDER),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
    ])

def _fmt(v):
    if isinstance(v,(int,float)):
        if v>=1e9: return f"{v/1e9:.1f} B FCFA"
        if v>=1e6: return f"{v/1e6:.1f} M FCFA"
        return f"{v:,.0f} FCFA"
    return str(v)

def _disclaimer(S):
    return [Spacer(1,10*mm),HRFlowable(width="100%",thickness=0.5,color=TIJAN_BORDER,spaceAfter=3*mm),
            Paragraph("<b>Disclaimer:</b> This document has been generated automatically. "
                      "It must be reviewed by a qualified MEP engineer. "
                      "Tijan AI accepts no liability for use without professional verification.",S['SM'])]

def _cover(story,S,title,subtitle,p_,rm):
    def p(t,st='BD'): return Paragraph(str(t),S[st])
    story+=[Spacer(1,25*mm),p(title,'TT')]
    if subtitle: story.append(p(subtitle,'SM'))
    story+=[Spacer(1,3*mm),HRFlowable(width="60%",thickness=2,color=TIJAN_GREEN,spaceAfter=8*mm)]
    data=[
        [p('PARAMETER','TH'),p('VALUE','TH')],
        [p('Project'),p(p_.get('nom','Project'))],
        [p('Location'),p(f"{p_.get('ville','Dakar')}, {p_.get('pays','Senegal')}")],
        [p('Use'),p(p_.get('usage','residential').capitalize())],
        [p('Levels'),p(str(p_.get('nb_niveaux',4)))],
        [p('Built area'),p(f'{rm.surf_batie_m2:,.0f} m²')],
        [p('Units'),p(str(rm.nb_logements))],
        [p('Occupants'),p(str(rm.nb_personnes))],
    ]
    ct=Table(data,colWidths=[CW*0.30,CW*0.70],repeatRows=1);ct.setStyle(_ts())
    story+=[ct,PageBreak()]


# ════════════════════════════════════════════
# 1. MEP TECHNICAL NOTE
# ════════════════════════════════════════════
def generer_note_mep(rm, params_dict: dict) -> bytes:
    buf=io.BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,topMargin=22*mm,bottomMargin=18*mm,leftMargin=M,rightMargin=M)
    S=_S(); story=[]; p_=params_dict or {}
    cb=_hf("MEP Technical Note")
    def p(t,st='BD'): return Paragraph(str(t),S[st])

    _cover(story,S,"MEP TECHNICAL NOTE","Electrical · Plumbing · HVAC · Fire Safety · Lifts · Automation",p_,rm)

    e=rm.electrique; pl=rm.plomberie; cvc=rm.cvc; cf=rm.courants_faibles
    si=rm.securite_incendie; asc=rm.ascenseurs; auto=rm.automatisation

    # ── ELECTRICAL ──
    story.append(p("1. ELECTRICAL INSTALLATION (NF C 15-100)",'H1'))
    story.append(p(e.note_dimensionnement))
    elec_data=[
        [p('PARAMETER','TH'),p('VALUE','TH'),p('DETAIL','TH')],
        [p('Total power'),p(f'{e.puissance_totale_kva:.0f} kVA'),p(f'Lighting {e.puissance_eclairage_kw:.0f} kW + Sockets {e.puissance_prises_kw:.0f} kW')],
        [p('HVAC power'),p(f'{e.puissance_cvc_kw:.0f} kW'),p('')],
        [p('Lifts power'),p(f'{e.puissance_ascenseurs_kw:.0f} kW'),p('')],
        [p('Misc. power'),p(f'{e.puissance_divers_kw:.0f} kW'),p('Common areas + fire safety')],
        [p('Transformer'),p(f'{e.transfo_kva} kVA'),p('')],
        [p('Backup generator'),p(f'{e.groupe_electrogene_kva} kVA'),p('')],
        [p('Meters'),p(str(e.nb_compteurs)),p('')],
        [p('Riser section'),p(f'{e.section_colonne_mm2} mm²'),p('')],
        [p('Annual consumption'),p(f'{e.conso_annuelle_kwh:,.0f} kWh'),p(f'≈ {_fmt(e.facture_annuelle_fcfa)}/year')],
    ]
    te=Table(elec_data,colWidths=[CW*0.25,CW*0.25,CW*0.50],repeatRows=1);te.setStyle(_ts())
    story+=[te,Spacer(1,2*mm)]
    if e.marques_recommandees:
        story.append(p(f'Recommended brands: {", ".join(e.marques_recommandees)}','NT'))
    story.append(PageBreak())

    # ── PLUMBING ──
    story.append(p("2. PLUMBING (DTU 60.11 + EN 12056)",'H1'))
    story.append(p(pl.note_dimensionnement))
    plomb_data=[
        [p('PARAMETER','TH'),p('VALUE','TH'),p('DETAIL','TH')],
        [p('Daily demand'),p(f'{pl.besoin_total_m3_j:.1f} m³/day'),p(f'{pl.nb_personnes} occupants')],
        [p('Storage tank'),p(f'{pl.volume_citerne_m3:.0f} m³'),p('24h reserve')],
        [p('Booster pump'),p(f'{pl.debit_surpresseur_m3h:.1f} m³/h'),p('')],
        [p('Riser diameter'),p(f'Ø{pl.diam_colonne_montante_mm} mm'),p('')],
        [p('Solar water heaters'),p(str(pl.nb_chauffe_eau_solaire)),p('Energy savings')],
        [p('Dual-flush WC'),p(str(pl.nb_wc_double_chasse)),p('Water savings 3/6L')],
        [p('Eco faucets'),p(str(pl.nb_robinets_eco)),p('6 L/min aerator')],
        [p('Annual water'),p(f'{pl.conso_eau_annuelle_m3:,.0f} m³'),p(f'≈ {_fmt(pl.facture_eau_fcfa)}/year')],
    ]
    tp=Table(plomb_data,colWidths=[CW*0.25,CW*0.25,CW*0.50],repeatRows=1);tp.setStyle(_ts())
    story+=[tp,PageBreak()]

    # ── HVAC ──
    story.append(p("3. HVAC — AIR CONDITIONING & VENTILATION",'H1'))
    story.append(p(cvc.note_dimensionnement))
    cvc_data=[
        [p('PARAMETER','TH'),p('VALUE','TH'),p('DETAIL','TH')],
        [p('Cooling capacity'),p(f'{cvc.puissance_frigorifique_kw:.0f} kW'),p('')],
        [p('Living room splits'),p(str(cvc.nb_splits_sejour)),p('')],
        [p('Bedroom splits'),p(str(cvc.nb_splits_chambre)),p('')],
        [p('Cassette units'),p(str(cvc.nb_cassettes)),p('Common areas')],
        [p('VMC extract fans'),p(str(cvc.nb_vmc)),p(cvc.type_vmc)],
        [p('Annual consumption'),p(f'{cvc.conso_cvc_kwh_an:,.0f} kWh'),p('')],
    ]
    tc=Table(cvc_data,colWidths=[CW*0.25,CW*0.25,CW*0.50],repeatRows=1);tc.setStyle(_ts())
    story+=[tc,PageBreak()]

    # ── LOW CURRENT ──
    story.append(p("4. LOW-CURRENT SYSTEMS",'H1'))
    story.append(p(cf.note_dimensionnement))
    cf_data=[
        [p('PARAMETER','TH'),p('VALUE','TH')],
        [p('RJ45 sockets'),p(str(cf.nb_prises_rj45))],
        [p('Indoor cameras'),p(str(cf.nb_cameras_int))],
        [p('Outdoor cameras'),p(str(cf.nb_cameras_ext))],
        [p('Access control doors'),p(str(cf.nb_portes_controle_acces))],
        [p('Intercoms'),p(str(cf.nb_interphones))],
        [p('Server racks'),p(str(cf.baies_serveur))],
        [p('Audio/Video system'),p('Yes' if cf.systeme_audio_video else 'No')],
    ]
    tcf=Table(cf_data,colWidths=[CW*0.50,CW*0.50],repeatRows=1);tcf.setStyle(_ts())
    story.append(tcf)

    # ── FIRE SAFETY ──
    story.append(p("5. FIRE SAFETY",'H1'))
    story.append(p(si.note_dimensionnement))
    si_data=[
        [p('PARAMETER','TH'),p('VALUE','TH'),p('REMARK','TH')],
        [p('ERP category'),p(si.categorie_erp),p('')],
        [p('Smoke detectors'),p(str(si.nb_detecteurs_fumee)),p('')],
        [p('Manual call points'),p(str(si.nb_declencheurs_manuels)),p('')],
        [p('Sirens'),p(str(si.nb_sirenes)),p('')],
        [p('CO2 extinguishers'),p(str(si.nb_extincteurs_co2)),p('')],
        [p('Powder extinguishers'),p(str(si.nb_extincteurs_poudre)),p('')],
        [p('Fire hose cabinets'),p(f'{si.longueur_ria_ml:.0f} ml'),p('')],
        [p('Sprinkler heads'),p(str(si.nb_tetes_sprinkler)),p('Required' if si.sprinklers_requis else 'Not required')],
        [p('Alarm zones'),p(str(si.centrale_zones)),p('')],
        [p('Smoke extraction'),p('Required' if si.desenfumage_requis else 'Not required'),p('')],
    ]
    tsi=Table(si_data,colWidths=[CW*0.30,CW*0.25,CW*0.45],repeatRows=1);tsi.setStyle(_ts())
    story+=[tsi,PageBreak()]

    # ── LIFTS ──
    story.append(p("6. LIFTS & VERTICAL TRANSPORT",'H1'))
    story.append(p(asc.note_dimensionnement))
    asc_data=[
        [p('PARAMETER','TH'),p('VALUE','TH')],
        [p('Passenger lifts'),p(str(asc.nb_ascenseurs))],
        [p('Capacity'),p(f'{asc.capacite_kg} kg')],
        [p('Speed'),p(f'{asc.vitesse_ms} m/s')],
        [p('Goods lifts'),p(str(asc.nb_monte_charges))],
        [p('Escalators'),p(str(asc.nb_escalators))],
        [p('Total power'),p(f'{asc.puissance_totale_kw:.0f} kW')],
    ]
    ta=Table(asc_data,colWidths=[CW*0.50,CW*0.50],repeatRows=1);ta.setStyle(_ts())
    story.append(ta)
    if asc.note_impact_prix:
        story.append(p(f'Cost note: {asc.note_impact_prix}','NT'))

    # ── AUTOMATION ──
    story.append(p("7. BUILDING AUTOMATION (BMS)",'H1'))
    story.append(p(auto.note_dimensionnement))
    auto_data=[
        [p('PARAMETER','TH'),p('VALUE','TH')],
        [p('Automation level'),p(auto.niveau.capitalize())],
        [p('Protocol'),p(auto.protocole)],
        [p('Control points'),p(str(auto.nb_points_controle))],
        [p('Lighting control'),p('✓' if auto.gestion_eclairage else '—')],
        [p('HVAC control'),p('✓' if auto.gestion_cvc else '—')],
        [p('Access control'),p('✓' if auto.gestion_acces else '—')],
        [p('Energy monitoring'),p('✓' if auto.gestion_energie else '—')],
        [p('BMS required'),p('Yes' if auto.bms_requis else 'No')],
    ]
    tau=Table(auto_data,colWidths=[CW*0.50,CW*0.50],repeatRows=1);tau.setStyle(_ts())
    story.append(tau)

    story+=_disclaimer(S)
    doc.build(story,onFirstPage=cb,onLaterPages=cb)
    buf.seek(0);return buf.read()


# ════════════════════════════════════════════
# 2. EDGE REPORT
# ════════════════════════════════════════════
def generer_edge(rm, params_dict: dict) -> bytes:
    buf=io.BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,topMargin=22*mm,bottomMargin=18*mm,leftMargin=M,rightMargin=M)
    S=_S();story=[];p_=params_dict or {}
    cb=_hf("EDGE Certification Report")
    def p(t,st='BD'): return Paragraph(str(t),S[st])

    _cover(story,S,"EDGE CERTIFICATION REPORT","IFC / World Bank — Green Building Standard",p_,rm)

    e=rm.edge
    story.append(p("1. EDGE OVERVIEW",'H1'))
    story.append(p("EDGE (Excellence in Design for Greater Efficiencies) is the IFC/World Bank green building "
                   "certification. Minimum: 20% savings in energy, water, and embodied energy vs. local baseline."))

    story.append(p("2. PERFORMANCE SCORES",'H1'))
    cert="✓ CERTIFIABLE" if e.certifiable else "✗ NOT YET CERTIFIABLE"
    scores=[
        [p('PILLAR','TH'),p('BASELINE','TH'),p('PROJECT','TH'),p('SAVINGS','TH'),p('TARGET','TH')],
        [p('Energy'),p(f'{e.base_energie_kwh_m2_an:.0f} kWh/m²/yr'),p(f'{e.projet_energie_kwh_m2_an:.0f} kWh/m²/yr'),
         p(f'{e.economie_energie_pct:.1f}%'),p('≥ 20%')],
        [p('Water'),p(f'{e.base_eau_L_pers_j:.0f} L/pers/day'),p(f'{e.projet_eau_L_pers_j:.0f} L/pers/day'),
         p(f'{e.economie_eau_pct:.1f}%'),p('≥ 20%')],
        [p('Materials'),p(f'{e.base_ei_kwh_m2:.0f} kWh/m²'),p(f'{e.projet_ei_kwh_m2:.0f} kWh/m²'),
         p(f'{e.economie_materiaux_pct:.1f}%'),p('≥ 20%')],
    ]
    ts=Table(scores,colWidths=[CW*0.15,CW*0.22,CW*0.22,CW*0.18,CW*0.13],repeatRows=1);ts.setStyle(_ts())
    story+=[ts,Spacer(1,4*mm)]
    story.append(p(f'<b>Level: {e.niveau_certification} — {cert}</b>'))
    story.append(Spacer(1,4*mm))

    # Energy measures
    story.append(p("3. ENERGY MEASURES",'H1'))
    for m in e.mesures_energie:
        if isinstance(m,dict):
            story.append(p(f"• {m.get('mesure','')} — +{m.get('gain_pct',0):.1f}% — {m.get('statut','')}"
                          f"{' — '+_fmt(m['impact_prix']) if m.get('impact_prix') else ''}"))

    story.append(p("4. WATER MEASURES",'H1'))
    for m in e.mesures_eau:
        if isinstance(m,dict):
            story.append(p(f"• {m.get('mesure','')} — +{m.get('gain_pct',0):.1f}% — {m.get('statut','')}"
                          f"{' — '+_fmt(m['impact_prix']) if m.get('impact_prix') else ''}"))

    story.append(p("5. MATERIALS MEASURES",'H1'))
    for m in e.mesures_materiaux:
        if isinstance(m,dict):
            story.append(p(f"• {m.get('mesure','')} — +{m.get('gain_pct',0):.1f}% — {m.get('statut','')}"
                          f"{' — '+_fmt(m['impact_prix']) if m.get('impact_prix') else ''}"))

    if e.plan_action:
        story.append(p("6. ACTION PLAN — PATH TO CERTIFICATION",'H1'))
        for a in e.plan_action:
            if isinstance(a,dict):
                story.append(p(f"→ [{a.get('pilier','').upper()}] {a.get('action','')} — "
                              f"+{a.get('gain_pct',0):.1f}% — {_fmt(a.get('cout_fcfa',0))}"))

    story.append(p("7. COST AND ROI",'H1'))
    story.append(p(f'<b>Compliance cost:</b> {_fmt(e.cout_mise_conformite_fcfa)}<br/>'
                   f'<b>Payback period:</b> {e.roi_ans:.1f} years<br/>'
                   f'<b>Method:</b> {e.methode_calcul}'))
    story.append(Spacer(1,4*mm))
    story.append(p(e.note_generale,'BL'))

    story+=_disclaimer(S)
    doc.build(story,onFirstPage=cb,onLaterPages=cb)
    buf.seek(0);return buf.read()


# ════════════════════════════════════════════
# 3. EXECUTIVE REPORT
# ════════════════════════════════════════════
def generer_rapport_executif(rs, rm, params_dict: dict) -> bytes:
    buf=io.BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,topMargin=22*mm,bottomMargin=18*mm,leftMargin=M,rightMargin=M)
    S=_S();story=[];p_=params_dict or {}
    cb=_hf("Executive Summary Report")
    def p(t,st='BD'): return Paragraph(str(t),S[st])

    _cover(story,S,"EXECUTIVE SUMMARY REPORT","Owner / Investor Technical Brief",p_,rm)

    boq=rs.boq; bmep=rm.boq; e=rm.edge; ana=rs.analyse

    story.append(p("1. STRUCTURAL OVERVIEW",'H1'))
    story.append(p(f'<b>Concrete:</b> {rs.classe_beton} — <b>Steel:</b> {rs.classe_acier}<br/>'
                   f'<b>Total concrete:</b> {boq.beton_total_m3:.0f} m³ — <b>Total steel:</b> {boq.acier_kg:,.0f} kg<br/>'
                   f'<b>Structural cost (low):</b> {_fmt(boq.total_bas_fcfa)} — <b>(high):</b> {_fmt(boq.total_haut_fcfa)}'))

    story.append(p("2. MEP OVERVIEW",'H1'))
    story.append(p(f'<b>MEP cost (Basic):</b> {_fmt(bmep.total_basic_fcfa)}<br/>'
                   f'<b>MEP cost (High-End):</b> {_fmt(bmep.total_hend_fcfa)}<br/>'
                   f'<b>MEP cost (Luxury):</b> {_fmt(bmep.total_luxury_fcfa)}<br/>'
                   f'<b>Recommendation:</b> {bmep.recommandation}'))

    story.append(p("3. TOTAL PROJECT COST ESTIMATE",'H1'))
    total_bas=boq.total_bas_fcfa+bmep.total_basic_fcfa
    total_haut=boq.total_haut_fcfa+bmep.total_hend_fcfa
    cost_data=[
        [p('ITEM','TH'),p('LOW ESTIMATE','TH'),p('HIGH ESTIMATE','TH')],
        [p('Structure'),p(_fmt(boq.total_bas_fcfa),'TR'),p(_fmt(boq.total_haut_fcfa),'TR')],
        [p('MEP (Basic / High-End)'),p(_fmt(bmep.total_basic_fcfa),'TR'),p(_fmt(bmep.total_hend_fcfa),'TR')],
        [p('<b>TOTAL</b>'),p(f'<b>{_fmt(total_bas)}</b>','TR'),p(f'<b>{_fmt(total_haut)}</b>','TR')],
        [p('Cost / m² built'),p(f'{total_bas/max(rm.surf_batie_m2,1):,.0f} FCFA/m²','TR'),
         p(f'{total_haut/max(rm.surf_batie_m2,1):,.0f} FCFA/m²','TR')],
    ]
    tco=Table(cost_data,colWidths=[CW*0.40,CW*0.30,CW*0.30],repeatRows=1);tco.setStyle(_ts())
    story.append(tco)

    story.append(p("4. EDGE GREEN CERTIFICATION",'H1'))
    story.append(p(f'Energy: {e.economie_energie_pct:.0f}% | Water: {e.economie_eau_pct:.0f}% | '
                   f'Materials: {e.economie_materiaux_pct:.0f}%<br/>'
                   f'<b>Status:</b> {e.niveau_certification} — '
                   f'{"Certifiable" if e.certifiable else "Action plan required"}<br/>'
                   f'<b>Compliance cost:</b> {_fmt(e.cout_mise_conformite_fcfa)} — ROI: {e.roi_ans:.1f} years'))

    if ana.recommandations:
        story.append(p("5. KEY RECOMMENDATIONS",'H1'))
        for r in ana.recommandations:
            story.append(p(f'→ {r}'))

    if ana.alertes:
        story.append(p("6. ALERTS",'H1'))
        for a in ana.alertes:
            story.append(p(f'⚠ {a}','NT'))

    story+=_disclaimer(S)
    doc.build(story,onFirstPage=cb,onLaterPages=cb)
    buf.seek(0);return buf.read()
