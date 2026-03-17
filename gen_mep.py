"""
gen_mep.py — Générateurs MEP, EDGE, BOQ MEP, Rapport exécutif
Tijan AI — données 100% issues du moteur engine_mep_v2
"""
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Table, Spacer,
                                  PageBreak, KeepTogether, HRFlowable)
from tijan_theme import *


# ══════════════════════════════════════════════════════════════
# NOTE DE CALCUL MEP
# ══════════════════════════════════════════════════════════════

def generer_note_mep(rm, params: dict) -> bytes:
    buf = io.BytesIO()
    hf = HeaderFooter(rm.params.nom, 'Note de calcul MEP')
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=ML, rightMargin=MR, topMargin=26*mm, bottomMargin=18*mm)
    doc.build(_build_note_mep(rm), onFirstPage=hf, onLaterPages=hf)
    return buf.getvalue()


def _build_note_mep(rm):
    story = []
    d = rm.params
    el = rm.electrique
    pl = rm.plomberie
    cv = rm.cvc
    cf = rm.courants_faibles
    si = rm.securite_incendie
    asc = rm.ascenseurs
    auto = rm.automatisation

    # En-tête
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(d.nom, S['titre']))
    story.append(Paragraph(f'{d.ville} — MEP — R+{d.nb_niveaux-1} ({d.usage.value.capitalize()})', S['sous_titre']))
    story.append(Paragraph(f'Surface bâtie : {fmt_n(rm.surf_batie_m2,0,"m²")} | {rm.nb_logements} logements / unités | {rm.nb_personnes} personnes', S['body']))
    story.append(Spacer(1, 2*mm))

    # ── ÉLECTRICITÉ ───────────────────────────────────────────
    story += section_title('1', 'BILAN ÉLECTRICITÉ (NF C 15-100)')
    story.append(Paragraph(el.note_dimensionnement, S['note']))
    story.append(Spacer(1, 2*mm))

    elec_data = [
        [p('PARAMÈTRE','th'), p('VALEUR','th'), p('PARAMÈTRE','th'), p('VALEUR','th')],
        [p('Puissance totale','td_b'), p(f'{el.puissance_totale_kva:.0f} kVA'), p('Transformateur','td_b'), p(f'{el.transfo_kva} kVA')],
        [p('Puissance éclairage','td_b'), p(f'{el.puissance_eclairage_kw:.1f} kW'), p('Groupe électrogène','td_b'), p(f'{el.groupe_electrogene_kva} kVA')],
        [p('Puissance CVC','td_b'), p(f'{el.puissance_cvc_kw:.1f} kW'), p('Nb compteurs','td_b'), p(str(el.nb_compteurs))],
        [p('Puissance ascenseurs','td_b'), p(f'{el.puissance_ascenseurs_kw:.1f} kW'), p('Section colonne','td_b'), p(f'{el.section_colonne_mm2} mm²')],
        [p('Conso annuelle','td_b'), p(f'{fmt_n(el.conso_annuelle_kwh,0)} kWh/an'), p('Facture annuelle','td_b'), p(fmt_fcfa(el.facture_annuelle_fcfa))],
    ]
    te = Table(elec_data, colWidths=[CW*0.25, CW*0.25, CW*0.25, CW*0.25], repeatRows=1)
    te.setStyle(table_style())
    story.append(te)
    story.append(Paragraph('Marques recommandées : ' + ' | '.join(el.marques_recommandees[:2]), S['small']))

    # ── PLOMBERIE ─────────────────────────────────────────────
    story += section_title('2', 'BILAN PLOMBERIE (DTU 60.11 — ONAS)')
    story.append(Paragraph(pl.note_dimensionnement, S['note']))
    story.append(Spacer(1, 2*mm))

    plomb_data = [
        [p('PARAMÈTRE','th'), p('VALEUR','th'), p('PARAMÈTRE','th'), p('VALEUR','th')],
        [p('Nb logements','td_b'), p(str(pl.nb_logements)), p('Nb personnes','td_b'), p(str(pl.nb_personnes))],
        [p('Besoin eau/jour','td_b'), p(f'{pl.besoin_total_m3_j:.2f} m³/j'), p('Volume citerne','td_b'), p(f'{int(pl.volume_citerne_m3)} m³')],
        [p('Débit surpresseur','td_b'), p(f'{pl.debit_surpresseur_m3h} m³/h'), p('Diam. colonne','td_b'), p(f'DN{pl.diam_colonne_montante_mm}')],
        [p('Nb CESI 200L','td_b'), p(str(pl.nb_chauffe_eau_solaire)), p('Nb WC 2 chasses','td_b'), p(str(pl.nb_wc_double_chasse))],
        [p('Conso eau/an','td_b'), p(f'{fmt_n(pl.conso_eau_annuelle_m3,0)} m³/an'), p('Facture eau/an','td_b'), p(fmt_fcfa(pl.facture_eau_fcfa))],
    ]
    tp = Table(plomb_data, colWidths=[CW*0.25]*4, repeatRows=1)
    tp.setStyle(table_style())
    story.append(tp)
    story.append(Paragraph('Marques recommandées : ' + ' | '.join(pl.marques_recommandees[:2]), S['small']))

    # ── CVC ───────────────────────────────────────────────────
    story.append(PageBreak())
    story += section_title('3', 'BILAN CVC (EN 12831 — ASHRAE 55)')
    story.append(Paragraph(cv.note_dimensionnement, S['note']))
    story.append(Spacer(1, 2*mm))

    cvc_data = [
        [p('PARAMÈTRE','th'), p('VALEUR','th'), p('PARAMÈTRE','th'), p('VALEUR','th')],
        [p('Puissance frigo','td_b'), p(f'{cv.puissance_frigorifique_kw:.0f} kW'), p('Type VMC','td_b'), p(cv.type_vmc)],
        [p('Splits séjour','td_b'), p(str(cv.nb_splits_sejour)), p('Splits chambre','td_b'), p(str(cv.nb_splits_chambre))],
        [p('Cassettes plafond','td_b'), p(str(cv.nb_cassettes)), p('Nb VMC','td_b'), p(str(cv.nb_vmc))],
        [p('Conso CVC/an','td_b'), p(f'{fmt_n(cv.conso_cvc_kwh_an,0)} kWh/an'), p('','td_b'), p('')],
    ]
    tc = Table(cvc_data, colWidths=[CW*0.25]*4, repeatRows=1)
    tc.setStyle(table_style())
    story.append(tc)

    # ── COURANTS FAIBLES ──────────────────────────────────────
    story += section_title('4', 'COURANTS FAIBLES')
    story.append(Paragraph(cf.note_dimensionnement, S['note']))
    story.append(Spacer(1, 2*mm))

    cf_data = [
        [p('PARAMÈTRE','th'), p('VALEUR','th'), p('PARAMÈTRE','th'), p('VALEUR','th')],
        [p('Prises RJ45','td_b'), p(str(cf.nb_prises_rj45)), p('Caméras intérieur','td_b'), p(str(cf.nb_cameras_int))],
        [p('Caméras extérieur','td_b'), p(str(cf.nb_cameras_ext)), p('Contrôle accès','td_b'), p(f'{cf.nb_portes_controle_acces} portes')],
        [p('Interphones vidéo','td_b'), p(str(cf.nb_interphones)), p('Baies serveur','td_b'), p(str(cf.baies_serveur))],
        [p('Audio/vidéo collectif','td_b'), p('Oui' if cf.systeme_audio_video else 'Non'), p('','td_b'), p('')],
    ]
    tcf = Table(cf_data, colWidths=[CW*0.25]*4, repeatRows=1)
    tcf.setStyle(table_style())
    story.append(tcf)

    # ── SÉCURITÉ INCENDIE ─────────────────────────────────────
    story.append(PageBreak())
    story += section_title('5', 'SÉCURITÉ INCENDIE (IT 246)')
    story.append(Paragraph(si.note_dimensionnement, S['note']))
    story.append(Spacer(1, 2*mm))

    si_data = [
        [p('PARAMÈTRE','th'), p('VALEUR','th'), p('PARAMÈTRE','th'), p('VALEUR','th')],
        [p('Catégorie ERP','td_b'), p(si.categorie_erp), p('Centrale incendie','td_b'), p(f'{si.centrale_zones} zones')],
        [p('Détecteurs fumée','td_b'), p(str(si.nb_detecteurs_fumee)), p('Déclencheurs manuel','td_b'), p(str(si.nb_declencheurs_manuels))],
        [p('Sirènes + flash','td_b'), p(str(si.nb_sirenes)), p('Ext. CO2 6kg','td_b'), p(str(si.nb_extincteurs_co2))],
        [p('RIA DN25','td_b'), p(f'{int(si.longueur_ria_ml)} ml'), p('Têtes sprinkler','td_b'), p(str(si.nb_tetes_sprinkler))],
        [p('Désenfumage','td_b'), p('Obligatoire' if si.desenfumage_requis else 'Non requis', 'td_o' if si.desenfumage_requis else 'td'), p('Sprinklers','td_b'), p('Obligatoires' if si.sprinklers_requis else 'Non requis', 'td_o' if si.sprinklers_requis else 'td')],
    ]
    tsi = Table(si_data, colWidths=[CW*0.25]*4, repeatRows=1)
    tsi.setStyle(table_style())
    story.append(tsi)

    # ── ASCENSEURS ────────────────────────────────────────────
    story += section_title('6', 'ASCENSEURS (EN 81-20/50)')
    story.append(Paragraph(asc.note_dimensionnement, S['note']))
    if asc.note_impact_prix:
        story.append(Paragraph(f'ℹ {asc.note_impact_prix}', S['note']))
    story.append(Spacer(1, 2*mm))

    if asc.nb_ascenseurs > 0:
        asc_data = [
            [p('PARAMÈTRE','th'), p('VALEUR','th'), p('PARAMÈTRE','th'), p('VALEUR','th')],
            [p('Nb ascenseurs','td_b'), p(str(asc.nb_ascenseurs)), p('Capacité','td_b'), p(f'{asc.capacite_kg} kg')],
            [p('Vitesse','td_b'), p(f'{asc.vitesse_ms} m/s'), p('Monte-charges','td_b'), p(str(asc.nb_monte_charges))],
            [p('Escalators','td_b'), p(str(asc.nb_escalators)), p('Puissance totale','td_b'), p(f'{asc.puissance_totale_kw:.1f} kW')],
        ]
        tasc = Table(asc_data, colWidths=[CW*0.25]*4, repeatRows=1)
        tasc.setStyle(table_style())
        story.append(tasc)
        story.append(Paragraph('Marques : ' + ' | '.join(asc.marques_recommandees[:3]), S['small']))
    else:
        story.append(Paragraph('Aucun ascenseur requis (R+2 et moins).', S['body']))

    # ── AUTOMATISATION ────────────────────────────────────────
    story += section_title('7', 'AUTOMATISATION ET GTB')
    story.append(Paragraph(auto.note_dimensionnement, S['note']))
    story.append(Spacer(1, 2*mm))

    auto_data = [
        [p('PARAMÈTRE','th'), p('VALEUR','th'), p('PARAMÈTRE','th'), p('VALEUR','th')],
        [p('Niveau','td_b'), p(auto.niveau), p('Protocole','td_b'), p(auto.protocole)],
        [p('Points de contrôle','td_b'), p(str(auto.nb_points_controle)), p('BMS requis','td_b'), p('Oui' if auto.bms_requis else 'Non')],
        [p('Gestion éclairage','td_b'), p('Oui'), p('Gestion CVC','td_b'), p('Oui')],
        [p('Gestion accès','td_b'), p('Oui' if auto.gestion_acces else 'Non'), p('Gestion énergie','td_b'), p('Oui' if auto.gestion_energie else 'Non')],
    ]
    tauto = Table(auto_data, colWidths=[CW*0.25]*4, repeatRows=1)
    tauto.setStyle(table_style())
    story.append(tauto)

    return story


# ══════════════════════════════════════════════════════════════
# BOQ MEP
# ══════════════════════════════════════════════════════════════

def generer_boq_mep(rm, params: dict) -> bytes:
    buf = io.BytesIO()
    hf = HeaderFooter(rm.params.nom, 'BOQ MEP')
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=ML, rightMargin=MR, topMargin=26*mm, bottomMargin=18*mm)
    doc.build(_build_boq_mep(rm), onFirstPage=hf, onLaterPages=hf)
    return buf.getvalue()


def _build_boq_mep(rm):
    story = []
    d = rm.params
    boq = rm.boq

    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(d.nom, S['titre']))
    story.append(Paragraph(f'BOQ MEP — {d.ville} — R+{d.nb_niveaux-1}', S['sous_titre']))
    story.append(Spacer(1, 2*mm))

    # Résumé
    story += section_title('1', 'SYNTHÈSE BOQ MEP')
    sum_data = [
        [p('GAMME','th'), p('MONTANT TOTAL','th'), p('COÛT / m² BÂTI','th'), p('DESCRIPTION','th')],
        [p('BASIC','td_b'), p(fmt_fcfa(boq.total_basic_fcfa),'td_g_r'), p(f'{boq.ratio_basic_m2:,} FCFA/m²'.replace(",", " "),'td_r'), p('Équipements standard — fonctionnel')],
        [p('HIGH-END','td_b'), p(fmt_fcfa(boq.total_hend_fcfa),'td_g_r'), p(f'{boq.ratio_hend_m2:,} FCFA/m²'.replace(",", " "),'td_r'), p('Équipements premium — confort élevé')],
        [p('LUXURY','td_b'), p(fmt_fcfa(boq.total_luxury_fcfa),'td_g_r'), p('—','td_r'), p('Équipements haut de gamme — standing maximum')],
    ]
    ts = Table(sum_data, colWidths=[CW*0.12, CW*0.20, CW*0.20, CW*0.48], repeatRows=1)
    tss = table_style(zebra=False)
    tss.add('BACKGROUND', (0,2), (-1,2), VERT_LIGHT)
    ts.setStyle(tss)
    story.append(ts)
    story.append(Paragraph(boq.recommandation, S['note']))
    story.append(Paragraph(boq.note_choix, S['small']))
    story.append(Spacer(1, 3*mm))

    # Détail par lot
    story += section_title('2', 'DÉTAIL PAR LOT')
    cw_b = [CW*w for w in [0.05, 0.35, 0.08, 0.17, 0.17, 0.18]]
    rows = [[p(h,'th') for h in ['Lot','Désignation','Unité','Montant basic','Montant high-end','Montant luxury']]]
    for lot in boq.lots:
        rows.append([
            p(lot.lot,'td_b'), p(lot.designation), p(lot.unite),
            p(fmt_fcfa(lot.pu_basic_fcfa),'td_r'),
            p(fmt_fcfa(lot.pu_hend_fcfa),'td_r'),
            p(fmt_fcfa(lot.pu_luxury_fcfa),'td_r'),
        ])
        if lot.note_impact:
            rows.append([p(''), p(f'   ℹ {lot.note_impact}', 'small'), p(''), p(''), p(''), p('')])

    rows.append([
        p('','td_b'), p('TOTAL MEP','td_b'), p(''),
        p(fmt_fcfa(boq.total_basic_fcfa),'td_g_r'),
        p(fmt_fcfa(boq.total_hend_fcfa),'td_g_r'),
        p(fmt_fcfa(boq.total_luxury_fcfa),'td_g_r'),
    ])

    tb = Table(rows, colWidths=cw_b, repeatRows=1)
    ts_b = table_style()
    total_row_style(ts_b)
    tb.setStyle(ts_b)
    story.append(tb)

    return story


# ══════════════════════════════════════════════════════════════
# RAPPORT EDGE
# ══════════════════════════════════════════════════════════════

def generer_edge(rm, params: dict) -> bytes:
    buf = io.BytesIO()
    hf = HeaderFooter(rm.params.nom, 'Pré-évaluation EDGE')
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=ML, rightMargin=MR, topMargin=26*mm, bottomMargin=18*mm)
    doc.build(_build_edge(rm), onFirstPage=hf, onLaterPages=hf)
    return buf.getvalue()


def _build_edge(rm):
    story = []
    d = rm.params
    e = rm.edge

    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(d.nom, S['titre']))
    story.append(Paragraph(f'Pré-évaluation EDGE — IFC EDGE Standard v3 — {d.ville}', S['sous_titre']))
    story.append(Spacer(1, 2*mm))

    # Verdict global
    verdict_color = VERT if e.certifiable else ORANGE
    verdict_txt = f'CERTIFIABLE — {e.niveau_certification}' if e.certifiable else f'NON CERTIFIABLE — {e.niveau_certification}'
    verd = Table([[Paragraph(f'RÉSULTAT : {verdict_txt}',
        ParagraphStyle('v', fontName='Helvetica-Bold', fontSize=11,
                       textColor=verdict_color))]], colWidths=[CW])
    verd.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1), VERT_LIGHT if e.certifiable else ORANGE_LT),
        ('BOX',(0,0),(-1,-1),1.5, verdict_color),
        ('TOPPADDING',(0,0),(-1,-1),8), ('BOTTOMPADDING',(0,0),(-1,-1),8),
        ('LEFTPADDING',(0,0),(-1,-1),12),
    ]))
    story.append(verd)
    story.append(Paragraph(e.note_generale, S['small']))
    story.append(Spacer(1, 3*mm))

    # Scores synthèse
    story += section_title('1', 'SYNTHÈSE DES SCORES EDGE')
    sc_data = [
        [p('PILIER','th'), p('SCORE PROJET','th'), p('SEUIL CIBLE','th'), p('STATUT','th')],
        [p('Énergie'), p(f'{e.economie_energie_pct}%','td_r'), p('20%','td_r'),
         p('✓ CONFORME' if e.economie_energie_pct>=20 else f'✗ DÉFICIT {20-e.economie_energie_pct:.1f}%',
           'ok' if e.economie_energie_pct>=20 else 'nok')],
        [p('Eau'), p(f'{e.economie_eau_pct}%','td_r'), p('20%','td_r'),
         p('✓ CONFORME' if e.economie_eau_pct>=20 else f'✗ DÉFICIT {20-e.economie_eau_pct:.1f}%',
           'ok' if e.economie_eau_pct>=20 else 'nok')],
        [p('Matériaux'), p(f'{e.economie_materiaux_pct}%','td_r'), p('20%','td_r'),
         p('✓ CONFORME' if e.economie_materiaux_pct>=20 else f'✗ DÉFICIT {20-e.economie_materiaux_pct:.1f}%',
           'ok' if e.economie_materiaux_pct>=20 else 'nok')],
    ]
    tsc = Table(sc_data, colWidths=[CW*0.30, CW*0.20, CW*0.20, CW*0.30], repeatRows=1)
    tsc.setStyle(table_style(zebra=False))
    story.append(tsc)
    story.append(Paragraph(f'Méthode : {e.methode_calcul}', S['small']))

    # Détail par pilier
    for pilier, titre, mesures, base, projet, unite in [
        ('ÉNERGIE',    'PILIER 1 — ÉNERGIE', e.mesures_energie,
         e.base_energie_kwh_m2_an, e.projet_energie_kwh_m2_an, 'kWh/m²/an'),
        ('EAU',        'PILIER 2 — EAU',     e.mesures_eau,
         e.base_eau_L_pers_j, e.projet_eau_L_pers_j, 'L/pers/j'),
        ('MATÉRIAUX',  'PILIER 3 — MATÉRIAUX', e.mesures_materiaux,
         e.base_ei_kwh_m2, e.projet_ei_kwh_m2, 'kWh/m²'),
    ]:
        story.append(PageBreak() if pilier != 'ÉNERGIE' else Spacer(1, 3*mm))
        story += section_title('', titre)
        story.append(Paragraph(
            f'Référence bâtiment standard : {base:.0f} {unite} | '
            f'Projet : {projet:.0f} {unite}',
            S['body']))
        story.append(Spacer(1, 2*mm))

        m_data = [[p('MESURE','th'), p('GAIN (%)','th'), p('STATUT','th'), p('IMPACT PRIX','th')]]
        for m in mesures:
            gain = m.get('gain_pct', 0)
            statut = m.get('statut', '—')
            est_integre = 'Intégré' in statut or 'standard' in statut
            m_data.append([
                p(m.get('mesure', '—')),
                p(f'+{gain}%', 'td_g_r' if est_integre else 'td_r'),
                p(statut, 'td_g' if est_integre else 'td_o' if 'spécifier' in statut.lower() else 'td'),
                p(m.get('impact_prix', '—'), 'small'),
            ])
        tm = Table(m_data, colWidths=[CW*0.32, CW*0.10, CW*0.28, CW*0.30], repeatRows=1)
        tm.setStyle(table_style())
        story.append(tm)

    # Plan d'action (si non certifiable)
    if not e.certifiable and e.plan_action:
        story.append(PageBreak())
        story += section_title('5', 'PLAN D\'ACTION — OPTIMISATION VERS CERTIFICATION')
        story.append(Paragraph(
            f'Coût total de mise en conformité estimé : {fmt_fcfa(e.cout_mise_conformite_fcfa)} | '
            f'ROI estimé : {e.roi_ans} ans',
            S['note']))
        story.append(Spacer(1, 2*mm))

        pa_data = [[p(h,'th') for h in ['PILIER','ACTION','GAIN (%)','COÛT','ROI','IMPACT']]]
        for action in e.plan_action:
            pa_data.append([
                p(action.get('pilier','—'), 'td_b'),
                p(action.get('action','—')),
                p(f'+{action.get("gain_pct",0):.1f}%', 'td_g_r'),
                p(fmt_fcfa(action.get('cout_fcfa',0)) if action.get('cout_fcfa',0) > 0 else '—','td_r'),
                p(f'{action.get("roi_ans",0):.1f} ans' if action.get('roi_ans',0)>0 else '—','td_r'),
                p(action.get('impact','—'), 'small'),
            ])
        tpa = Table(pa_data, colWidths=[CW*w for w in [0.10, 0.30, 0.09, 0.13, 0.09, 0.29]], repeatRows=1)
        tpa.setStyle(table_style())
        story.append(tpa)
        story.append(Paragraph(
            '⚠ Cette fonctionnalité "Optimiser vers EDGE" permet de simuler '
            'les modifications nécessaires et leur impact sur le coût du projet.',
            S['note']))

    return story


# ══════════════════════════════════════════════════════════════
# RAPPORT DE SYNTHÈSE EXÉCUTIF
# ══════════════════════════════════════════════════════════════

def generer_rapport_executif(rs, rm, params: dict) -> bytes:
    """
    Rapport 1-2 pages destiné au maître d'ouvrage non-technique.
    Synthèse tous corps d'état — coût global — EDGE.
    """
    buf = io.BytesIO()
    hf = HeaderFooter(rs.params.nom, 'Rapport de synthèse exécutif')
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=ML, rightMargin=MR, topMargin=26*mm, bottomMargin=18*mm)
    doc.build(_build_executif(rs, rm), onFirstPage=hf, onLaterPages=hf)
    return buf.getvalue()


def _build_executif(rs, rm):
    story = []
    d = rs.params
    boq_s = rs.boq
    boq_m = rm.boq
    e = rm.edge

    # En-tête
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(d.nom, S['titre']))
    story.append(Paragraph(f'{d.ville} — {d.usage.value.capitalize()} R+{d.nb_niveaux-1} — Rapport exécutif', S['sous_titre']))
    story.append(Paragraph(
        f'Ce document est destiné au maître d\'ouvrage. '
        f'Il présente les points clés du projet et l\'estimation budgétaire globale.',
        S['body_j']))
    story.append(Spacer(1, 3*mm))

    # ── FICHE PROJET ─────────────────────────────────────────
    story += section_title('1', 'FICHE PROJET')
    fiche = [
        [p('PARAMÈTRE','th'), p('VALEUR','th'), p('PARAMÈTRE','th'), p('VALEUR','th')],
        [p('Projet','td_b'), p(d.nom), p('Localisation','td_b'), p(d.ville)],
        [p('Usage','td_b'), p(d.usage.value.capitalize()), p('Hauteur','td_b'), p(f'R+{d.nb_niveaux-1} ({d.nb_niveaux} niveaux)')],
        [p('Surface bâtie','td_b'), p(f'{fmt_n(boq_s.surface_batie_m2,0)} m²'), p('Surface habitable','td_b'), p(f'{fmt_n(boq_s.surface_habitable_m2,0)} m²')],
        [p('Nb logements/unités','td_b'), p(str(rm.nb_logements)), p('Nb occupants estimé','td_b'), p(str(rm.nb_personnes))],
        [p('Béton','td_b'), p(rs.classe_beton), p('Fondations','td_b'), p(rs.fondation.type.value)],
        [p('Certification EDGE','td_b'), p(e.niveau_certification, 'td_g' if e.certifiable else 'td_o'), p('Conformité EC2','td_b'), p(rs.analyse.conformite_ec2, 'td_g' if rs.analyse.conformite_ec2=='Conforme' else 'td_o')],
    ]
    tf = Table(fiche, colWidths=[CW*0.25]*4, repeatRows=1)
    tf.setStyle(table_style())
    story.append(tf)

    # ── BUDGET GLOBAL ─────────────────────────────────────────
    story += section_title('2', 'ESTIMATION BUDGÉTAIRE GLOBALE')
    story.append(Paragraph(
        'Estimation ±15% — Prix unitaires marché local 2026. '
        'À affiner avec métrés définitifs et appels d\'offres.',
        S['note']))
    story.append(Spacer(1, 2*mm))

    total_global_bas  = boq_s.total_bas_fcfa + boq_m.total_basic_fcfa
    total_global_haut = boq_s.total_haut_fcfa + boq_m.total_hend_fcfa
    ratio_global_bas  = int(total_global_bas / boq_s.surface_batie_m2) if boq_s.surface_batie_m2 > 0 else 0

    budget_data = [
        [p('CORPS D\'ÉTAT','th'), p('MONTANT BAS','th'), p('MONTANT HAUT','th'), p('% TOTAL','th'), p('NOTE','th')],
        [p('Structure (gros œuvre)','td_b'), p(fmt_fcfa(boq_s.total_bas_fcfa),'td_r'), p(fmt_fcfa(boq_s.total_haut_fcfa),'td_r'),
         p(f'{boq_s.total_bas_fcfa/total_global_bas*100:.0f}%','td_r'), p('Béton + acier + fondations')],
        [p('MEP — Basic','td_b'), p(fmt_fcfa(boq_m.total_basic_fcfa),'td_r'), p(fmt_fcfa(boq_m.total_hend_fcfa),'td_r'),
         p(f'{boq_m.total_basic_fcfa/total_global_bas*100:.0f}%','td_r'), p('Élec, plomberie, CVC, ascenseurs, sécurité')],
        [p('TOTAL GROS ŒUVRE','td_b'), p(fmt_fcfa(total_global_bas),'td_g_r'), p(fmt_fcfa(total_global_haut),'td_g_r'),
         p('100%','td_r'), p('Hors finitions, VRD, honoraires')],
        [p('Finitions (estimation)','td_b'), p(fmt_fcfa(int(total_global_bas*0.35)),'td_r'), p(fmt_fcfa(int(total_global_haut*0.35)),'td_r'),
         p('~35%','td_r'), p('Carrelage, peinture, menuiseries, etc.')],
        [p('COÛT TOTAL ESTIMÉ','td_b'),
         p(fmt_fcfa(int(total_global_bas*1.35)),'td_g_r'),
         p(fmt_fcfa(int(total_global_haut*1.35)),'td_g_r'),
         p('—','td_r'), p(f'{ratio_global_bas:,} FCFA/m² (gros œuvre seul)'.replace(',', ' '))],
    ]
    tb = Table(budget_data, colWidths=[CW*0.28, CW*0.16, CW*0.16, CW*0.09, CW*0.31], repeatRows=1)
    ts_b = table_style()
    ts_b.add('BACKGROUND', (0,3), (-1,3), VERT_LIGHT)
    ts_b.add('FONTNAME', (0,3), (-1,3), 'Helvetica-Bold')
    ts_b.add('BACKGROUND', (0,5), (-1,5), VERT_LIGHT)
    ts_b.add('FONTNAME', (0,5), (-1,5), 'Helvetica-Bold')
    tb.setStyle(ts_b)
    story.append(tb)

    # ── EDGE ─────────────────────────────────────────────────
    story += section_title('3', 'PERFORMANCE ENVIRONNEMENTALE (EDGE IFC)')
    edge_data = [
        [p('PILIER','th'), p('SCORE','th'), p('SEUIL','th'), p('STATUT','th')],
        [p('Économie énergie'), p(f'{e.economie_energie_pct}%','td_r'), p('≥ 20%','td_r'),
         p('✓' if e.economie_energie_pct>=20 else '✗','ok' if e.economie_energie_pct>=20 else 'nok')],
        [p('Économie eau'), p(f'{e.economie_eau_pct}%','td_r'), p('≥ 20%','td_r'),
         p('✓' if e.economie_eau_pct>=20 else '✗','ok' if e.economie_eau_pct>=20 else 'nok')],
        [p('Économie matériaux'), p(f'{e.economie_materiaux_pct}%','td_r'), p('≥ 20%','td_r'),
         p('✓' if e.economie_materiaux_pct>=20 else '✗','ok' if e.economie_materiaux_pct>=20 else 'nok')],
        [p('VERDICT','td_b'), p(e.niveau_certification,'td_b'), p('3/3 piliers','td_b'),
         p('✓ CERTIFIABLE' if e.certifiable else '✗ NON CERTIFIABLE',
           'td_g' if e.certifiable else 'td_o')],
    ]
    te = Table(edge_data, colWidths=[CW*0.30, CW*0.20, CW*0.20, CW*0.30], repeatRows=1)
    ts_e = table_style(zebra=False)
    ts_e.add('BACKGROUND', (0,-1), (-1,-1), VERT_LIGHT)
    te.setStyle(ts_e)
    story.append(te)

    if not e.certifiable:
        story.append(Paragraph(
            f'ℹ Pour obtenir la certification EDGE Basique, des mesures complémentaires '
            f'sont nécessaires (coût estimé : {fmt_fcfa(e.cout_mise_conformite_fcfa)}). '
            f'Voir le rapport EDGE détaillé pour le plan d\'action complet.',
            S['note']))

    # ── POINTS CLÉS ──────────────────────────────────────────
    story += section_title('4', 'POINTS CLÉS ET RECOMMANDATIONS')
    all_points = (rs.analyse.points_forts + rs.analyse.alertes +
                  rs.analyse.recommandations[:3])
    for pt in all_points[:8]:
        style = 'note' if pt in rs.analyse.alertes else 'body'
        prefix = '⚠' if pt in rs.analyse.alertes else '•'
        story.append(Paragraph(f'{prefix} {pt}', S[style]))

    # Disclaimer
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width=CW, thickness=0.5, color=GRIS2))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        'Ce rapport est un document de pré-étude indicatif (±15%). '
        'Il ne remplace pas les études techniques d\'un bureau d\'études agréé, '
        'dont l\'intervention est légalement obligatoire avant tout démarrage des travaux.',
        S['disc']))

    return story
