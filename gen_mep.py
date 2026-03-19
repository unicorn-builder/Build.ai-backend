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

def generer_note_mep(rm, params: dict, lang: str = "fr") -> bytes:
    buf = io.BytesIO()
    hf = HeaderFooter(rm.params.nom, 'Note de calcul MEP')
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=ML, rightMargin=MR, topMargin=26*mm, bottomMargin=18*mm)
    doc.build(_build_note_mep(rm), onFirstPage=hf, onLaterPages=hf)
    buf = io.BytesIO()
    hf = HeaderFooter(rm.params.nom, 'BOQ MEP')
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=ML, rightMargin=MR, topMargin=26*mm, bottomMargin=18*mm)
    doc.build(_build_boq_mep(rm), onFirstPage=hf, onLaterPages=hf)
    buf = io.BytesIO()
    hf = HeaderFooter(rm.params.nom, 'Pré-évaluation EDGE')
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=ML, rightMargin=MR, topMargin=26*mm, bottomMargin=18*mm)
    doc.build(_build_edge(rm), onFirstPage=hf, onLaterPages=hf)
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
