"""
gen_boq_mep_detail_en.py — English MEP Detailed BOQ (7 lots × 3 tiers)
Uses tijan_theme.py for identical design to FR version.
Signature: generer_boq_mep_detail(rm, params_dict) → bytes
"""
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, Spacer, PageBreak
from tijan_theme import *

def _devise_label():
    if _current_devise and _current_devise.get('devise') != 'XOF':
        return _current_devise.get('devise', 'FCFA')
    return 'FCFA'

LOT_EN = {
    "Électricité": "Electrical", "Electricité": "Electrical",
    "Plomberie": "Plumbing", "CVC / Climatisation": "HVAC", "CVC": "HVAC",
    "Climatisation": "HVAC", "Courants faibles": "Low Current",
    "Sécurité incendie": "Fire Safety", "Ascenseurs": "Lifts",
    "Automatisation": "Building Automation",
}


def generer_boq_mep_detail(rm, params: dict) -> bytes:
    buf = io.BytesIO()
    hf = HeaderFooter(rm.params.nom, 'MEP Bill of Quantities', lang='en')
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=ML, rightMargin=MR, topMargin=26*mm, bottomMargin=18*mm)
    story = _build(rm)
    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    return buf.getvalue()


def _build(rm):
    story = []
    d = rm.params
    bmep = rm.boq

    story.append(Spacer(1, 3*mm))
    story.append(p(d.nom, 'titre'))
    story.append(p(f'MEP Bill of Quantities — {d.ville}', 'sous_titre'))
    story.append(p('Three pricing tiers: Basic / High-End / Luxury. Indicative ±15%.', 'disc'))
    story.append(Spacer(1, 3*mm))

    # Project info
    story += section_title('1', 'PROJECT OVERVIEW')
    cw4 = [CW*0.28, CW*0.22, CW*0.28, CW*0.22]
    info = [
        [p('PARAMETER','th'), p('VALUE','th'), p('PARAMETER','th'), p('VALUE','th')],
        [p('Project','td_b'), p(d.nom), p('Location','td_b'), p(d.ville)],
        [p('Built area','td_b'), p(fmt_n(rm.surf_batie_m2,'','m²')), p('Units','td_b'), p(str(rm.nb_logements))],
        [p('Occupants','td_b'), p(str(rm.nb_personnes)), p('Currency','td_b'), p('FCFA (XOF)')],
    ]
    ti = Table(info, colWidths=cw4, repeatRows=1); ti.setStyle(table_style())
    story.append(ti)

    # ── SUMMARY TABLE ─────────────────────────────────────────
    story += section_title('2', 'SUMMARY BY LOT')
    cw_s = [CW*0.06, CW*0.28, CW*0.08, CW*0.08, CW*0.15, CW*0.15, CW*0.15]
    sum_rows = [[p(h,'th') for h in ['Lot','Description','Qty','Unit',f'Basic ({_devise_label()})','High-End','Luxury']]]
    for lot in bmep.lots:
        designation_en = LOT_EN.get(lot.designation, lot.designation)
        sum_rows.append([
            p(lot.lot), p(designation_en),
            p(fmt_n(lot.quantite),'td_r'), p(lot.unite),
            p(fmt_fcfa(lot.pu_basic_fcfa),'td_r'),
            p(fmt_fcfa(lot.pu_hend_fcfa),'td_r'),
            p(fmt_fcfa(lot.pu_luxury_fcfa),'td_r'),
        ])
    # Totals
    sum_rows.append([
        p('','td_b'), p('TOTAL EXCL. TAX','td_b'), p('','td_r'), p(''),
        p(fmt_fcfa(bmep.total_basic_fcfa),'td_g_r'),
        p(fmt_fcfa(bmep.total_hend_fcfa),'td_g_r'),
        p(fmt_fcfa(bmep.total_luxury_fcfa),'td_g_r'),
    ])
    tva_b = int(bmep.total_basic_fcfa*0.18)
    tva_h = int(bmep.total_hend_fcfa*0.18)
    tva_l = int(bmep.total_luxury_fcfa*0.18)
    sum_rows.append([
        p('','td_b'), p('VAT (18%)','td_b'), p('','td_r'), p(''),
        p(fmt_fcfa(tva_b),'td_r'), p(fmt_fcfa(tva_h),'td_r'), p(fmt_fcfa(tva_l),'td_r'),
    ])
    sum_rows.append([
        p('','td_b'), p('TOTAL INCL. TAX','td_b'), p('','td_r'), p(''),
        p(fmt_fcfa(bmep.total_basic_fcfa+tva_b),'td_g_r'),
        p(fmt_fcfa(bmep.total_hend_fcfa+tva_h),'td_g_r'),
        p(fmt_fcfa(bmep.total_luxury_fcfa+tva_l),'td_g_r'),
    ])

    ts_sum = Table(sum_rows, colWidths=cw_s, repeatRows=1)
    ts_s = table_style()
    total_row_style(ts_s)
    ts_sum.setStyle(ts_s)
    story.append(ts_sum)

    # Impact notes per lot
    story.append(Spacer(1, 3*mm))
    for lot in bmep.lots:
        if lot.note_impact:
            designation_en = LOT_EN.get(lot.designation, lot.designation)
            story.append(p(f'ℹ Lot {lot.lot} ({designation_en}): {lot.note_impact}', 'note'))

    # ── RATIOS ────────────────────────────────────────────────
    story += section_title('3', 'COST RATIOS AND RECOMMENDATION')
    story.append(p(f'Basic: {bmep.ratio_basic_m2:,} FCFA/m²  |  High-End: {bmep.ratio_hend_m2:,} FCFA/m²'.replace(',', ' '), 'body'))
    story.append(p(f'Recommendation: {bmep.recommandation}', 'td_g'))
    if bmep.note_choix:
        story.append(p(bmep.note_choix, 'body_j'))

    # Notes
    story.append(Spacer(1, 4*mm))
    story.append(p('1. Three tiers: Basic (standard), High-End (quality), Luxury (premium).', 'small'))
    story.append(p('2. Prices from validated local market data (Senegal, Côte d\'Ivoire, Morocco).', 'small'))
    story.append(p('3. Labour, testing, and commissioning included per lot.', 'small'))
    story.append(p('4. Owner selects tier per lot — mix-and-match supported.', 'small'))
    story.append(p('5. Prices valid at date of generation — subject to market fluctuation.', 'small'))

    return story
