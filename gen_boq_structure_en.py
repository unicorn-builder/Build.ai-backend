"""
gen_boq_structure_en.py — English Structural BOQ
Uses tijan_theme.py for identical design to FR version.
Signature: generer_boq_structure(rs, params_dict) → bytes
"""
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, Spacer, PageBreak
from tijan_theme import *



def generer_boq_structure(rs, params: dict) -> bytes:
    buf = io.BytesIO()
    hf = HeaderFooter(rs.params.nom, 'Structural Bill of Quantities', lang='en')
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=ML, rightMargin=MR, topMargin=26*mm, bottomMargin=18*mm)
    story = _build(rs)
    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    return buf.getvalue()


def _build(rs):
    story = []
    d = rs.params
    boq = rs.boq

    story.append(Spacer(1, 3*mm))
    story.append(p(d.nom, 'titre'))
    story.append(p(f'Structural Bill of Quantities — {d.ville}', 'sous_titre'))
    story.append(p('Indicative quantities ±15% — Must be confirmed by the contractor.', 'disc'))
    story.append(Spacer(1, 3*mm))

    # ── BOQ TABLE ─────────────────────────────────────────────
    story += section_title('1', 'BILL OF QUANTITIES AND PRICES — STRUCTURE')
    story.append(p(f'Unit prices based on {d.ville} 2026 market (supply and install). Margin ±15%.', 'small'))
    story.append(Spacer(1, 2*mm))

    cw_b = [CW*w for w in [0.05, 0.37, 0.09, 0.07, 0.13, 0.14, 0.15]]
    boq_rows = [[p(h,'th') for h in ['Lot','Description','Qty','Unit',f"U.P. ({devise_label()})",'Low est.','High est.']]]

    lots_data = [
        ('1', 'Earthworks — clearing + mechanical excavation',
         fmt_n(boq.terrassement_m3), 'm³', fmt_n(8500),
         fmt_fcfa(boq.cout_terr_fcfa), fmt_fcfa(int(boq.cout_terr_fcfa*1.10))),
        ('2', 'Foundations — piles/footings/raft RC',
         '—', 'lump sum', '—',
         fmt_fcfa(boq.cout_fond_fcfa), fmt_fcfa(int(boq.cout_fond_fcfa*1.20))),
        ('3a', f'Concrete {rs.classe_beton} RMC — structure ({fmt_n(boq.beton_structure_m3,0)} m³)',
         fmt_n(boq.beton_structure_m3,0), 'm³', '185 000',
         fmt_fcfa(boq.cout_beton_fcfa), fmt_fcfa(int(boq.cout_beton_fcfa*1.10))),
        ('3b', f'Steel {rs.classe_acier} supply+fix ({fmt_n(boq.acier_kg,0)} kg)',
         fmt_n(boq.acier_kg,0), 'kg', '810',
         fmt_fcfa(boq.cout_acier_fcfa), fmt_fcfa(int(boq.cout_acier_fcfa*1.10))),
        ('3c', f'Formwork all faces ({fmt_n(boq.coffrage_m2,0)} m²)',
         fmt_n(boq.coffrage_m2,0), 'm²', '18 000',
         fmt_fcfa(boq.cout_coffrage_fcfa), fmt_fcfa(int(boq.cout_coffrage_fcfa*1.10))),
        ('4', 'Masonry — 15cm blocks plastered both sides',
         fmt_n(boq.maconnerie_m2,0), 'm²', '24 000',
         fmt_fcfa(boq.cout_maco_fcfa), fmt_fcfa(int(boq.cout_maco_fcfa*1.15))),
        ('5', f'Roof waterproofing ({fmt_n(boq.etancheite_m2,0)} m²)',
         fmt_n(boq.etancheite_m2,0), 'm²', '18 500',
         fmt_fcfa(boq.cout_etanch_fcfa), fmt_fcfa(int(boq.cout_etanch_fcfa*1.10))),
        ('6', 'Miscellaneous — joints, parapets, openings',
         '—', 'lump sum', '—',
         fmt_fcfa(boq.cout_divers_fcfa), fmt_fcfa(int(boq.cout_divers_fcfa*1.10))),
    ]
    for lot in lots_data:
        boq_rows.append([p(lot[0]), p(lot[1]), p(lot[2],'td_r'), p(lot[3]),
                          p(lot[4],'td_r'), p(lot[5],'td_r'), p(lot[6],'td_r')])
    boq_rows.append([
        p('','td_b'), p('TOTAL STRUCTURE','td_b'), p('','td_r'), p(''), p('','td_r'),
        p(fmt_fcfa(boq.total_bas_fcfa),'td_g_r'), p(fmt_fcfa(boq.total_haut_fcfa),'td_g_r'),
    ])
    tboq = Table(boq_rows, colWidths=cw_b, repeatRows=1)
    ts_boq = table_style()
    total_row_style(ts_boq)
    tboq.setStyle(ts_boq)
    story.append(tboq)

    # ── RATIOS ────────────────────────────────────────────────
    story.append(Spacer(1, 3*mm))
    story += section_title('2', 'COST RATIOS')
    rat_data = [
        [p(h,'th') for h in ['INDICATOR','LOW VALUE','HIGH VALUE','NOTE']],
        [p('Total built area','td_b'), p(fmt_n(boq.surface_batie_m2,'','m²')), p('—'),
         p(f'Footprint {int(d.surface_emprise_m2)} m² × {d.nb_niveaux} levels', 'small')],
        [p('Cost / m² built','td_b'), p(f'{boq.ratio_fcfa_m2_bati:,} FCFA/m²'.replace(',', ' '),'td_r'),
         p(f'{int(boq.ratio_fcfa_m2_bati*1.15):,} FCFA/m²'.replace(',', ' '),'td_r'),
         p('Structure only — excl. MEP, finishes, ext. works', 'small')],
        [p('Cost / m² habitable','td_b'), p(f'{boq.ratio_fcfa_m2_habitable:,} FCFA/m²'.replace(',', ' '),'td_r'),
         p(f'{int(boq.ratio_fcfa_m2_habitable*1.15):,} FCFA/m²'.replace(',', ' '),'td_r'),
         p('Habitable area ≈ 78% of built area', 'small')],
        [p('TOTAL STRUCTURAL COST','td_b'),
         p(fmt_fcfa(boq.total_bas_fcfa),'td_g_r'), p(fmt_fcfa(boq.total_haut_fcfa),'td_g_r'),
         p('Estimate ±15%', 'small')],
    ]
    tr = Table(rat_data, colWidths=[CW*0.32, CW*0.20, CW*0.20, CW*0.28], repeatRows=1)
    ts_r = table_style()
    total_row_style(ts_r)
    tr.setStyle(ts_r)
    story.append(tr)

    # Notes
    story.append(Spacer(1, 4*mm))
    story.append(p('1. Steel: Fabrimetal Sénégal (Sébikotane), 480–600 FCFA/kg.', 'small'))
    story.append(p('2. Concrete: ready-mix C30/37, CIMAF/SOCOCIM, 185,000 FCFA/m³ delivered.', 'small'))
    story.append(p('3. Low/High estimates reflect market price range.', 'small'))
    story.append(p('4. Prices valid at date of generation — subject to market fluctuation.', 'small'))

    return story
