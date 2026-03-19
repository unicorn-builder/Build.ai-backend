"""
gen_boq_structure.py — BOQ Structure détaillé standalone
Tijan AI — données 100% issues du moteur engine_structure_v2
Niveau de détail : consultable pour appel d'offres
"""
import io, math
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Table,
                                  Spacer, PageBreak, KeepTogether)
from tijan_theme import *


def generer_boq_structure(rs, params: dict, lang: str = "fr") -> bytes:
    buf = io.BytesIO()
    hf = HeaderFooter(rs.params.nom, 'BOQ Structure — Détaillé')
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=ML, rightMargin=MR, topMargin=26*mm, bottomMargin=18*mm)
    doc.build(_build(rs), onFirstPage=hf, onLaterPages=hf)
    return buf.getvalue()


def _row(lot, desig, qte, unite, pu, montant, note='', bold=False):
    st = 'td_b' if bold else 'td'
    st_r = 'td_b_r' if bold else 'td_r'
    st_g = 'td_g_r' if bold else 'td_r'
    return [p(lot, st), p(desig, st), p(str(qte) if qte != '' else '—', st_r),
            p(unite, st), p(fmt_n(pu) if pu else '—', st_r),
            p(fmt_fcfa(montant) if montant else '—', st_g),
            p(note, 'small')]

def _sous_total(desig, montant):
    return [p(''), p(desig, 'td_b'), p(''), p(''), p(''),
            p(fmt_fcfa(montant), 'td_g_r'), p('')]

def _build(rs):
    story = []
    d = rs.params
    boq = rs.boq
    poteaux = rs.poteaux
    poutre = rs.poutre_principale
    dalle = rs.dalle
    fond = rs.fondation
    cl = rs.cloisons

    # Tenter import prix
    try:
        from prix_marche import get_prix_structure
        px = get_prix_structure(d.ville)
    except:
        class _PX:
            beton_c2530_m3=170000; beton_c3037_m3=185000; beton_c3545_m3=210000
            acier_ha400_kg=750; acier_ha500_kg=810; coffrage_bois_m2=18000
            coffrage_metal_m2=25000; terr_mecanique_m3=8500; terr_manuel_m3=5000
            remblai_m3=6500; pieu_fore_d600_ml=220000; pieu_fore_d800_ml=285000
            pieu_fore_d1000_ml=360000; semelle_filante_ml=85000; radier_m2=95000
            agglo_creux_10_m2=18000; agglo_creux_15_m2=24000; agglo_creux_20_m2=30000
            agglo_plein_25_m2=38000; ba13_simple_m2=28000; ba13_double_m2=42000
            etanch_sbs_m2=18500; etanch_pvc_m2=22000; etanch_liquide_m2=12000
            mo_chef_chantier_j=35000; mo_macon_j=18000; mo_ferrailleur_j=20000
            mo_manœuvre_j=8000
        px = _PX()

    # Sélection prix béton selon classe
    prix_beton = {
        'C25/30': px.beton_c2530_m3, 'C30/37': px.beton_c3037_m3,
        'C35/45': px.beton_c3545_m3, 'C40/50': getattr(px,'beton_c4050_m3', 240000),
    }.get(rs.classe_beton, px.beton_c3037_m3)

    prix_acier = px.acier_ha400_kg if rs.classe_acier == 'HA400' else px.acier_ha500_kg

    nb_pot = (d.nb_travees_x + 1) * (d.nb_travees_y + 1)
    ep_dalle_m = dalle.epaisseur_mm / 1000
    surf_batie = boq.surface_batie_m2

    # ── EN-TÊTE ───────────────────────────────────────────────
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(d.nom, S['titre']))
    story.append(Paragraph(
        f'Bordereau des Quantités et des Prix — Structure — {d.ville} {rs.params.pays}',
        S['sous_titre']))
    story.append(Paragraph(
        f'R+{d.nb_niveaux-1} — {d.usage.value.capitalize()} — '
        f'Surface bâtie : {fmt_n(surf_batie,0,"m²")} — '
        f'Béton {rs.classe_beton} — Acier {rs.classe_acier}',
        S['body']))
    story.append(Paragraph(
        'Prix unitaires marché local 2026 (fournis-posés). Marge ±15%. '
        'Document utilisable pour consultation d\'entreprises.',
        S['note']))
    story.append(Spacer(1, 3*mm))

    # Colonnes BOQ
    CW_COLS = [CW*w for w in [0.05, 0.36, 0.07, 0.06, 0.12, 0.14, 0.20]]
    HEADERS = [p(h,'th') for h in ['Lot','Désignation','Qté','Unité','P.U. (FCFA)','Montant (FCFA)','Observations']]

    def make_table(rows):
        t = Table([HEADERS] + rows, colWidths=CW_COLS, repeatRows=1)
        ts = table_style()
        t.setStyle(ts)
        return t

    # ══════════════════════════════════════════════════════════
    # LOT 1 — INSTALLATION DE CHANTIER
    # ══════════════════════════════════════════════════════════
    story += section_title('LOT 1', 'INSTALLATION ET ORGANISATION DE CHANTIER')
    inst_forfait = int(surf_batie * 2500)
    rows_inst = [
        _row('1.1', 'Clôture de chantier (palissade bois ou tôle)', int(4*math.sqrt(d.surface_emprise_m2)), 'ml', 15000, int(4*math.sqrt(d.surface_emprise_m2)*15000)),
        _row('1.2', 'Base vie chantier (bureau, vestiaires, sanitaires)', 1, 'forfait', 0, int(surf_batie*800), 'Modulaires démontables'),
        _row('1.3', 'Branchements provisoires eau + électricité', 1, 'forfait', 0, int(surf_batie*500)),
        _row('1.4', 'Signalétique sécurité + EPI chantier', 1, 'forfait', 0, int(surf_batie*300)),
        _row('1.5', 'Repli et nettoyage fin de chantier', 1, 'forfait', 0, int(surf_batie*600)),
        _sous_total('SOUS-TOTAL LOT 1', inst_forfait),
    ]
    story.append(make_table(rows_inst))

    # ══════════════════════════════════════════════════════════
    # LOT 2 — TERRASSEMENT
    # ══════════════════════════════════════════════════════════
    story.append(PageBreak())
    story += section_title('LOT 2', 'TERRASSEMENT GÉNÉRAL')
    V_decap = d.surface_emprise_m2 * 0.30
    V_fouilles = d.surface_emprise_m2 * (fond.profondeur_m + 0.50)
    V_remblai  = V_fouilles * 0.30
    V_evacu    = V_fouilles * 0.70
    c_terr = int(V_decap*px.terr_mecanique_m3 + V_fouilles*px.terr_mecanique_m3 +
                  V_remblai*px.remblai_m3 + V_evacu*5000)
    rows_terr = [
        _row('2.1', 'Décapage terre végétale e=30cm', int(V_decap), 'm³', px.terr_mecanique_m3, int(V_decap*px.terr_mecanique_m3)),
        _row('2.2', 'Fouilles générales mécaniques', int(V_fouilles), 'm³', px.terr_mecanique_m3, int(V_fouilles*px.terr_mecanique_m3), 'Engins mécaniques'),
        _row('2.3', 'Fouilles manuelles en fond de fouille', int(V_fouilles*0.10), 'm³', px.terr_manuel_m3, int(V_fouilles*0.10*px.terr_manuel_m3), 'Finitions manuelles'),
        _row('2.4', 'Remblai compacté (matériaux sélectionnés)', int(V_remblai), 'm³', px.remblai_m3, int(V_remblai*px.remblai_m3)),
        _row('2.5', 'Évacuation terres excédentaires', int(V_evacu), 'm³', 5000, int(V_evacu*5000), 'Transport + décharge agréée'),
        _row('2.6', 'Lit de sable sous dallage e=10cm', int(d.surface_emprise_m2*0.10), 'm³', 12000, int(d.surface_emprise_m2*0.10*12000)),
        _sous_total('SOUS-TOTAL LOT 2', c_terr),
    ]
    story.append(make_table(rows_terr))

    # ══════════════════════════════════════════════════════════
    # LOT 3 — FONDATIONS
    # ══════════════════════════════════════════════════════════
    story += section_title('LOT 3', 'FONDATIONS')
    story.append(Paragraph(
        f'Type : {fond.type.value} — Sol admissible : {d.pression_sol_MPa} MPa — '
        f'Justification : {fond.justification}', S['note']))
    story.append(Spacer(1, 2*mm))

    rows_fond = []
    c_fond = 0

    if fond.nb_pieux > 0:
        prix_pieu = {600: px.pieu_fore_d600_ml, 800: px.pieu_fore_d800_ml,
                     1000: px.pieu_fore_d1000_ml}.get(fond.diam_pieu_mm, px.pieu_fore_d800_ml)
        V_fond_beton = fond.nb_pieux * math.pi*(fond.diam_pieu_mm/1000/2)**2 * fond.longueur_pieu_m
        kg_fond_acier = fond.nb_pieux * fond.As_cm2/10000 * 7850 * fond.longueur_pieu_m
        c_pieux = int(fond.nb_pieux * fond.longueur_pieu_m * prix_pieu)
        c_longr = int(nb_pot * 6 * 85000)  # longrines
        c_fond  = c_pieux + c_longr
        rows_fond = [
            _row('3.1', f'Pieux forés béton armé Ø{fond.diam_pieu_mm}mm — L={fond.longueur_pieu_m}m', int(fond.nb_pieux * fond.longueur_pieu_m), 'ml', prix_pieu, c_pieux, f'{fond.nb_pieux} pieux × {fond.longueur_pieu_m}m'),
            _row('3.2', f'Armatures pieux HA500B — cage Ø{fond.diam_pieu_mm}mm', int(kg_fond_acier), 'kg', prix_acier, int(kg_fond_acier*prix_acier), f'As={fond.As_cm2}cm² par pieu'),
            _row('3.3', f'Béton de propreté e=10cm sous longrines', int(nb_pot*0.5*0.5*0.10), 'm³', 120000, int(nb_pot*0.5*0.5*0.10*120000)),
            _row('3.4', f'Longrines béton armé {rs.classe_beton} — section 30×50cm', int(nb_pot * 6), 'ml', 85000, c_longr, 'Liaisons entre pieux'),
            _row('3.5', 'Tête de pieux + chapiteaux béton armé', nb_pot, 'U', 120000, int(nb_pot*120000), 'Connexion pieux-structure'),
            _sous_total('SOUS-TOTAL LOT 3', c_fond),
        ]
        story.append(Paragraph(
            f'ℹ Les fondations représentent {c_fond/boq.total_bas_fcfa*100:.0f}% du budget structure — '
            f'poste critique nécessitant une étude géotechnique préalable.',
            S['note']))
    elif fond.beton_semelle_m3 > 0:
        c_fond = int(fond.beton_semelle_m3 * prix_beton * 1.6)
        rows_fond = [
            _row('3.1', 'Béton de propreté e=10cm', int(d.surface_emprise_m2*0.10), 'm³', 120000, int(d.surface_emprise_m2*0.10*120000)),
            _row('3.2', f'Semelles béton armé {rs.classe_beton}', int(fond.beton_semelle_m3*0.6), 'm³', prix_beton, int(fond.beton_semelle_m3*0.6*prix_beton)),
            _row('3.3', f'Armatures semelles {rs.classe_acier}', int(fond.beton_semelle_m3*100), 'kg', prix_acier, int(fond.beton_semelle_m3*100*prix_acier)),
            _row('3.4', 'Coffrage semelles perdues', int(fond.beton_semelle_m3*2), 'm²', px.coffrage_bois_m2, int(fond.beton_semelle_m3*2*px.coffrage_bois_m2)),
            _sous_total('SOUS-TOTAL LOT 3', c_fond),
        ]

    story.append(make_table(rows_fond))

    # ══════════════════════════════════════════════════════════
    # LOT 4 — STRUCTURE BÉTON ARMÉ
    # ══════════════════════════════════════════════════════════
    story.append(PageBreak())
    story += section_title('LOT 4', f'STRUCTURE BÉTON ARMÉ — {rs.classe_beton} / {rs.classe_acier}')

    # 4.1 Poteaux niveau par niveau
    story.append(Paragraph('4.1 — Poteaux', S['h2']))
    rows_pot = [HEADERS]
    c_pot_total = 0
    for i, pt in enumerate(poteaux):
        b = pt.section_mm / 1000
        V_niv = b**2 * d.hauteur_etage_m * nb_pot
        As_niv = pt.nb_barres * math.pi * pt.diametre_mm**2 / 400 * nb_pot * d.hauteur_etage_m * 7850 / 10000
        c_beton_niv = int(V_niv * prix_beton)
        c_acier_niv = int(As_niv * prix_acier)
        c_coff_niv  = int(4 * b * d.hauteur_etage_m * nb_pot * px.coffrage_bois_m2)
        c_pot_niv   = c_beton_niv + c_acier_niv + c_coff_niv
        c_pot_total += c_pot_niv
        rows_pot.append([
            p(f'4.1.{i+1}'),
            p(f'Poteaux {pt.niveau} — {pt.section_mm}×{pt.section_mm}mm — {pt.nb_barres}HA{pt.diametre_mm}'),
            p(f'{nb_pot}', 'td_r'), p('U'),
            p(fmt_n(c_pot_niv//nb_pot), 'td_r'),
            p(fmt_fcfa(c_pot_niv), 'td_r'),
            p(f'NEd={pt.NEd_kN:.0f}kN | ρ={pt.taux_armature_pct:.1f}%', 'small'),
        ])
    rows_pot.append(_sous_total('Sous-total poteaux', c_pot_total))

    t_pot = Table(rows_pot, colWidths=CW_COLS, repeatRows=1)
    t_pot.setStyle(table_style())
    story.append(t_pot)

    # 4.2 Poutres
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph('4.2 — Poutres', S['h2']))
    b_p = poutre.b_mm/1000; h_p = poutre.h_mm/1000
    L_px = d.nb_travees_x * d.portee_max_m * (d.nb_travees_y+1) * d.nb_niveaux
    L_py = d.nb_travees_y * d.portee_min_m * (d.nb_travees_x+1) * d.nb_niveaux
    V_pout = (L_px + L_py) * b_p * (h_p - ep_dalle_m)
    kg_pout = V_pout * 100
    c_pout_beton = int(V_pout * prix_beton)
    c_pout_acier = int(kg_pout * prix_acier)
    c_pout_coff  = int((L_px+L_py) * (b_p + 2*(h_p-ep_dalle_m)) * px.coffrage_bois_m2 * 0.6)
    c_pout_total = c_pout_beton + c_pout_acier + c_pout_coff
    rows_pout = [
        HEADERS,
        _row('4.2.1', f'Poutres principales {poutre.b_mm}×{poutre.h_mm}mm — portée max {d.portee_max_m}m', int(L_px), 'ml', int(c_pout_beton//(L_px+1)), int(c_pout_beton*L_px/(L_px+L_py)), f'As inf={poutre.As_inf_cm2}cm² / As sup={poutre.As_sup_cm2}cm²'),
        _row('4.2.2', f'Poutres secondaires {poutre.b_mm}×{poutre.h_mm}mm — portée min {d.portee_min_m}m', int(L_py), 'ml', int(c_pout_beton//(L_py+1)), int(c_pout_beton*L_py/(L_px+L_py))),
        _row('4.2.3', f'Armatures poutres {rs.classe_acier} (façonnées + posées)', int(kg_pout), 'kg', prix_acier, c_pout_acier, f'Étriers HA{poutre.etrier_diam_mm} e={poutre.etrier_esp_mm}mm'),
        _row('4.2.4', 'Coffrage poutres (bois + étais)', int((L_px+L_py)*(b_p+2*(h_p-ep_dalle_m))*0.6), 'm²', px.coffrage_bois_m2, c_pout_coff),
        _sous_total('Sous-total poutres', c_pout_total),
    ]
    t_pout = Table(rows_pout, colWidths=CW_COLS, repeatRows=1)
    t_pout.setStyle(table_style())
    story.append(t_pout)

    # 4.3 Dalles
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph('4.3 — Dalles', S['h2']))
    V_dalles = surf_batie * ep_dalle_m * 0.85
    kg_dalles = V_dalles * 80
    c_dalle_beton = int(V_dalles * prix_beton)
    c_dalle_acier = int(kg_dalles * prix_acier)
    c_dalle_coff  = int(surf_batie * 0.85 * px.coffrage_bois_m2)
    c_dalle_total = c_dalle_beton + c_dalle_acier + c_dalle_coff
    rows_dalles = [
        HEADERS,
        _row('4.3.1', f'Béton dalles {rs.classe_beton} BPE e={dalle.epaisseur_mm}mm', int(V_dalles), 'm³', prix_beton, c_dalle_beton, f'As_x={dalle.As_x_cm2_ml}cm²/ml / As_y={dalle.As_y_cm2_ml}cm²/ml'),
        _row('4.3.2', f'Armatures dalles {rs.classe_acier} — HA10 deux sens', int(kg_dalles), 'kg', prix_acier, c_dalle_acier, 'Treillis soudé + renforts'),
        _row('4.3.3', 'Coffrage dalles (banches métalliques)', int(surf_batie*0.85), 'm²', px.coffrage_bois_m2, c_dalle_coff),
        _row('4.3.4', 'Étaiement provisoire (échafaudages)', int(surf_batie*0.85), 'm²', 3500, int(surf_batie*0.85*3500), 'Location + main d\'œuvre'),
        _row('4.3.5', 'Réservations trémies (gaines, escaliers)', 1, 'forfait', 0, int(surf_batie*500), 'Estimation 0.5% SHOB'),
        _sous_total('Sous-total dalles', c_dalle_total),
    ]
    t_dalles = Table(rows_dalles, colWidths=CW_COLS, repeatRows=1)
    t_dalles.setStyle(table_style())
    story.append(t_dalles)

    # 4.4 Escaliers
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph('4.4 — Escaliers', S['h2']))
    nb_esc = max(1, int(surf_batie/1500))
    c_esc = int(nb_esc * d.nb_niveaux * 450000)
    rows_esc = [
        HEADERS,
        _row('4.4.1', f'Escaliers béton armé {rs.classe_beton} — volée + paliers', nb_esc * d.nb_niveaux, 'volée', 450000, c_esc, f'{nb_esc} cage(s) × {d.nb_niveaux} niveaux'),
        _row('4.4.2', 'Garde-corps béton/métal escaliers', nb_esc * d.nb_niveaux * 3, 'ml', 45000, int(nb_esc*d.nb_niveaux*3*45000)),
        _sous_total('Sous-total escaliers', c_esc + int(nb_esc*d.nb_niveaux*3*45000)),
    ]
    t_esc = Table(rows_esc, colWidths=CW_COLS, repeatRows=1)
    t_esc.setStyle(table_style())
    story.append(t_esc)

    # ══════════════════════════════════════════════════════════
    # LOT 5 — MAÇONNERIE ET CLOISONS
    # ══════════════════════════════════════════════════════════
    story.append(PageBreak())
    story += section_title('LOT 5', 'MAÇONNERIE, CLOISONS ET ENDUITS')
    cl = rs.cloisons
    opt_rec = next((o for o in cl.options if o.type == cl.option_recommandee), cl.options[0])

    rows_maco = [HEADERS]
    c_maco_total = 0

    # Façades extérieures
    surf_facades = 4 * math.sqrt(d.surface_emprise_m2) * d.nb_niveaux * d.hauteur_etage_m * 0.70
    c_fac = int(surf_facades * px.agglo_plein_25_m2)
    rows_maco.append(_row('5.1', 'Maçonnerie façades extérieures — agglos pleins 25cm',
        int(surf_facades), 'm²', px.agglo_plein_25_m2, c_fac, 'Murs périphériques enduits 2 faces'))
    c_maco_total += c_fac

    # Cloisons séparatives
    c_sep = int(cl.surface_separative_m2 * opt_rec.prix_fcfa_m2)
    rows_maco.append(_row('5.2', f'Cloisons séparatives — {opt_rec.materiau[:40]}',
        int(cl.surface_separative_m2), 'm²', int(opt_rec.prix_fcfa_m2), c_sep,
        f'Option recommandée — {opt_rec.usage_recommande[:35]}'))
    c_maco_total += c_sep

    # Cloisons légères intérieures
    prix_leger = px.ba13_simple_m2
    c_leg = int(cl.surface_legere_m2 * prix_leger)
    rows_maco.append(_row('5.3', 'Cloisons légères intérieures — BA13 simple rail',
        int(cl.surface_legere_m2), 'm²', prix_leger, c_leg, 'Cloisons intérieures non séparatives'))
    c_maco_total += c_leg

    # Gaines techniques
    c_gaines = int(cl.surface_gaines_m2 * px.beton_c3037_m3 * 0.20)
    rows_maco.append(_row('5.4', 'Gaines techniques — béton armé coulé 20cm',
        int(cl.surface_gaines_m2), 'm²', int(px.beton_c3037_m3 * 0.20), c_gaines,
        'Gaines ascenseurs + colonnes montantes'))
    c_maco_total += c_gaines

    # Enduits
    surf_enduit = (surf_facades + cl.surface_separative_m2) * 2
    c_end = int(surf_enduit * 8500)
    rows_maco.append(_row('5.5', 'Enduits ciment + plâtre intérieur/extérieur',
        int(surf_enduit), 'm²', 8500, c_end, 'Finitions surfaces maçonnées'))
    c_maco_total += c_end

    # Acrotères
    perim = 4 * math.sqrt(d.surface_emprise_m2)
    c_acrot = int(perim * 35000)
    rows_maco.append(_row('5.6', 'Acrotères béton armé h=60cm en toiture',
        int(perim), 'ml', 35000, c_acrot))
    c_maco_total += c_acrot

    rows_maco.append(_sous_total('SOUS-TOTAL LOT 5', c_maco_total))

    # Note options cloisons
    story.append(Paragraph(
        'ℹ Plusieurs options de cloisons disponibles selon budget et usage. '
        'Voir note de calcul structure pour détail comparatif.',
        S['note']))
    t_maco = Table(rows_maco, colWidths=CW_COLS, repeatRows=1)
    t_maco.setStyle(table_style())
    story.append(t_maco)

    # ══════════════════════════════════════════════════════════
    # LOT 6 — ÉTANCHÉITÉ ET ISOLATION
    # ══════════════════════════════════════════════════════════
    story += section_title('LOT 6', 'ÉTANCHÉITÉ ET ISOLATION')
    surf_etanch = d.surface_emprise_m2
    c_sbs  = int(surf_etanch * px.etanch_sbs_m2)
    c_prot = int(surf_etanch * 5000)
    c_dallettes = int(surf_etanch * 8000)
    c_ss_sol = int(d.surface_emprise_m2 * 0.30 * px.etanch_pvc_m2) if d.avec_sous_sol else 0
    c_salles = int(surf_batie * 0.08 * px.etanch_liquide_m2)
    c_etanch_total = c_sbs + c_prot + c_dallettes + c_ss_sol + c_salles

    rows_etanch = [
        HEADERS,
        _row('6.1', 'Étanchéité toiture-terrasse SBS bicouche (primaire + 2 couches)', int(surf_etanch), 'm²', px.etanch_sbs_m2, c_sbs, 'Soudage à la flamme — DTU 43.1'),
        _row('6.2', 'Protection étanchéité — chape de protection e=5cm', int(surf_etanch), 'm²', 5000, c_prot),
        _row('6.3', 'Dallettes béton sur plots (toiture accessible)', int(surf_etanch*0.40), 'm²', 8000, int(surf_etanch*0.40*8000), '40% toiture accessible'),
        _row('6.4', 'Étanchéité salles de bains + locaux humides', int(surf_batie*0.08), 'm²', px.etanch_liquide_m2, c_salles, 'Résine monocomposant'),
    ]
    if d.avec_sous_sol:
        rows_etanch.append(_row('6.5', 'Étanchéité sous-sol (membrane PVC)', int(d.surface_emprise_m2), 'm²', px.etanch_pvc_m2, c_ss_sol, 'Cuvelage intérieur'))
    rows_etanch.append(_sous_total('SOUS-TOTAL LOT 6', c_etanch_total))

    t_etanch = Table(rows_etanch, colWidths=CW_COLS, repeatRows=1)
    t_etanch.setStyle(table_style())
    story.append(t_etanch)

    # ══════════════════════════════════════════════════════════
    # LOT 7 — DIVERS ET IMPRÉVUS
    # ══════════════════════════════════════════════════════════
    story += section_title('LOT 7', 'DIVERS, IMPRÉVUS ET HONORAIRES TECHNIQUES')
    sous_tot_travaux = (inst_forfait + c_terr + c_fond + c_pot_total +
                        c_pout_total + c_dalle_total + c_maco_total + c_etanch_total)
    c_impr  = int(sous_tot_travaux * 0.05)
    c_bet   = int(sous_tot_travaux * 0.04)
    c_ctrl  = int(sous_tot_travaux * 0.015)

    rows_div = [
        HEADERS,
        _row('7.1', 'Joints de dilatation (tous niveaux)', int(surf_batie/500), 'U', 850000, int(surf_batie/500*850000), '1 joint / 500m² environ'),
        _row('7.2', 'Réservations et scellements divers', 1, 'forfait', 0, int(surf_batie*800), 'Gaines électriques, plomberie'),
        _row('7.3', 'Imprévus chantier (5% travaux)', 1, 'forfait', 0, c_impr, 'Aléas et adaptations'),
        _row('7.4', 'Honoraires BET structure (4% travaux)', 1, 'forfait', 0, c_bet, 'Plans d\'exécution + suivi'),
        _row('7.5', 'Contrôle technique (1.5% travaux)', 1, 'forfait', 0, c_ctrl, 'Organisme agréé obligatoire'),
        _sous_total('SOUS-TOTAL LOT 7', c_impr + c_bet + c_ctrl + int(surf_batie*800) + int(surf_batie/500*850000)),
    ]
    c_div_total = c_impr + c_bet + c_ctrl + int(surf_batie*800) + int(surf_batie/500*850000)

    t_div = Table(rows_div, colWidths=CW_COLS, repeatRows=1)
    t_div.setStyle(table_style())
    story.append(t_div)

    # ══════════════════════════════════════════════════════════
    # RÉCAPITULATIF GÉNÉRAL
    # ══════════════════════════════════════════════════════════
    story.append(PageBreak())
    story += section_title('RÉCAP', 'RÉCAPITULATIF GÉNÉRAL')

    total_ht  = (inst_forfait + c_terr + c_fond + c_pot_total +
                 c_pout_total + c_dalle_total + c_maco_total +
                 c_etanch_total + c_div_total)
    total_bas = int(total_ht * 0.95)
    total_haut = int(total_ht * 1.15)

    recap_rows = [
        [p('LOT','th'), p('DÉSIGNATION','th_l'), p('MONTANT (FCFA)','th'), p('% TOTAL','th')],
        [p('1','td_b'), p('Installation de chantier'), p(fmt_fcfa(inst_forfait),'td_r'), p(f'{inst_forfait/total_ht*100:.1f}%','td_r')],
        [p('2','td_b'), p('Terrassement'), p(fmt_fcfa(c_terr),'td_r'), p(f'{c_terr/total_ht*100:.1f}%','td_r')],
        [p('3','td_b'), p('Fondations'), p(fmt_fcfa(c_fond),'td_r'), p(f'{c_fond/total_ht*100:.1f}%','td_r')],
        [p('4','td_b'), p('Structure béton armé (poteaux + poutres + dalles + escaliers)'), p(fmt_fcfa(c_pot_total+c_pout_total+c_dalle_total),'td_r'), p(f'{(c_pot_total+c_pout_total+c_dalle_total)/total_ht*100:.1f}%','td_r')],
        [p('5','td_b'), p('Maçonnerie et cloisons'), p(fmt_fcfa(c_maco_total),'td_r'), p(f'{c_maco_total/total_ht*100:.1f}%','td_r')],
        [p('6','td_b'), p('Étanchéité et isolation'), p(fmt_fcfa(c_etanch_total),'td_r'), p(f'{c_etanch_total/total_ht*100:.1f}%','td_r')],
        [p('7','td_b'), p('Divers + honoraires techniques'), p(fmt_fcfa(c_div_total),'td_r'), p(f'{c_div_total/total_ht*100:.1f}%','td_r')],
    ]
    recap_rows.append([p('','td_b'), p('TOTAL ESTIMATIF HT','td_b'), p(fmt_fcfa(total_ht),'td_g_r'), p('100%','td_b')])
    recap_rows.append([p('','td_b'), p('FOURCHETTE BASSE (-5%)','td_b'), p(fmt_fcfa(total_bas),'td_g_r'), p('','td_b')])
    recap_rows.append([p('','td_b'), p('FOURCHETTE HAUTE (+15%)','td_b'), p(fmt_fcfa(total_haut),'td_g_r'), p('','td_b')])

    tr = Table(recap_rows, colWidths=[CW*0.07, CW*0.50, CW*0.25, CW*0.18], repeatRows=1)
    ts_r = table_style(zebra=False)
    ts_r.add('BACKGROUND', (0,-3), (-1,-1), VERT_LIGHT)
    ts_r.add('FONTNAME',   (0,-3), (-1,-1), 'Helvetica-Bold')
    ts_r.add('LINEABOVE',  (0,-3), (-1,-3), 1.5, VERT)
    tr.setStyle(ts_r)
    story.append(tr)

    # Ratios
    story.append(Spacer(1, 3*mm))
    rat_data = [
        [p('INDICATEUR','th'), p('VALEUR','th'), p('RÉFÉRENCE MARCHÉ','th')],
        [p('Surface bâtie totale','td_b'), p(f'{fmt_n(surf_batie,0)} m²'), p(f'Emprise {int(d.surface_emprise_m2)} m² × {d.nb_niveaux} niveaux')],
        [p('Coût total / m² bâti','td_b'), p(f'{int(total_ht/surf_batie):,} FCFA/m²'.replace(',', ' ')), p('Résidentiel Dakar : 80 000–160 000 FCFA/m²')],
        [p('Coût béton armé / m² bâti','td_b'), p(f'{int((c_pot_total+c_pout_total+c_dalle_total)/surf_batie):,} FCFA/m²'.replace(',', ' ')), p('Ratio béton + acier + coffrage')],
        [p('Fondations / total structure','td_b'), p(f'{c_fond/total_ht*100:.1f}%'), p('Normal : 15–25% (fondations profondes)')],
        [p('Ratio acier','td_b'), p(f'{int(boq.acier_kg/surf_batie)} kg/m²'), p('Référence EDGE : 40 kg/m²')],
    ]
    tr2 = Table(rat_data, colWidths=[CW*0.35, CW*0.25, CW*0.40], repeatRows=1)
    tr2.setStyle(table_style())
    story.append(tr2)

    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(
        '* Ce BOQ est une estimation d\'avant-projet (±15%). Les quantités sont calculées depuis le '
        'dimensionnement EC2/EC8 et les ratios validés pour le marché local. '
        'Un métré définitif sur plans d\'exécution est requis avant appel d\'offres.',
        S['disc']))

    return story
