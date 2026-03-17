"""
gen_boq_mep_detail.py — BOQ MEP détaillé standalone
Tijan AI — données 100% issues du moteur engine_mep_v2
Niveau de détail : consultable pour appel d'offres
"""
import io, math
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Spacer, PageBreak
from tijan_theme import *


def generer_boq_mep_detail(rm, params: dict) -> bytes:
    buf = io.BytesIO()
    hf = HeaderFooter(rm.params.nom, 'BOQ MEP — Détaillé')
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=ML, rightMargin=MR, topMargin=26*mm, bottomMargin=18*mm)
    doc.build(_build(rm), onFirstPage=hf, onLaterPages=hf)
    return buf.getvalue()


def _row(lot, desig, qte, unite, pu_b, pu_h, pu_l, note='', bold=False):
    st = 'td_b' if bold else 'td'
    return [
        p(lot, st), p(desig, st),
        p(str(qte) if qte != '' else '—', 'td_r'),
        p(unite, st),
        p(fmt_n(pu_b) if pu_b else '—', 'td_r'),
        p(fmt_n(pu_h) if pu_h else '—', 'td_r'),
        p(fmt_n(pu_l) if pu_l else '—', 'td_r'),
        p(note, 'small'),
    ]

def _sous_total(desig, c_b, c_h, c_l):
    return [p(''), p(desig, 'td_b'), p(''), p(''),
            p(fmt_fcfa(c_b), 'td_g_r'), p(fmt_fcfa(c_h), 'td_g_r'), p(fmt_fcfa(c_l), 'td_g_r'), p('')]

def _build(rm):
    story = []
    d = rm.params
    el = rm.electrique
    pl = rm.plomberie
    cv = rm.cvc
    cf = rm.courants_faibles
    si = rm.securite_incendie
    asc = rm.ascenseurs
    auto = rm.automatisation
    surf = rm.surf_batie_m2

    # Tenter import prix
    try:
        from prix_marche import get_prix_mep
        px = get_prix_mep(d.ville)
    except:
        class _PX:
            transfo_160kva=22_000_000; transfo_250kva=32_000_000; transfo_400kva=48_000_000
            groupe_electrogene_100kva=18_000_000; groupe_electrogene_200kva=32_000_000
            groupe_electrogene_400kva=58_000_000; compteur_monophase=180_000
            compteur_triphase=280_000; canalisation_cuivre_ml=12_000
            luminaire_led_standard=35_000; luminaire_led_premium=85_000
            colonne_montante_ml=22_000; tuyau_pvc_dn50_ml=8_500
            tuyau_pvc_dn100_ml=14_000; tuyau_pvc_dn150_ml=22_000
            robinet_standard=45_000; robinet_eco=75_000
            wc_standard=85_000; wc_double_chasse=130_000
            cuve_eau_5000l=850_000; cuve_eau_10000l=1_500_000
            pompe_surpresseur_1kw=450_000; pompe_surpresseur_3kw=850_000
            chauffe_eau_electrique_100l=180_000; chauffe_eau_solaire_200l=2_100_000
            split_1cv=450_000; split_2cv=750_000; split_cassette_4cv=1_800_000
            vmc_simple_flux=320_000; vmc_double_flux=850_000
            ascenseur_630kg_r4_r6=28_000_000; ascenseur_630kg_r7_r10=38_000_000
            ascenseur_1000kg_r6_r10=45_000_000; ascenseur_1000kg_r11_plus=58_000_000
            monte_charge_500kg=22_000_000; cablage_rj45_ml=3_500
            prise_rj45=18_000; baie_serveur_12u=850_000
            camera_ip_interieure=180_000; camera_ip_exterieure=280_000
            systeme_controle_acces=350_000; interphone_video=220_000
            detecteur_fumee=45_000; declencheur_manuel=35_000; sirene_flash=55_000
            centrale_incendie_16zones=1_800_000; centrale_incendie_32zones=3_200_000
            extincteur_6kg_co2=85_000; extincteur_9kg_poudre=65_000
            ria_dn25_ml=45_000; sprinkler_tete=85_000; sprinkler_centrale=4_500_000
            domotique_logement=850_000; bms_systeme=12_000_000
            eclairage_detecteur_presence=95_000
        px = _PX()

    # Colonnes BOQ MEP
    CW_COLS = [CW*w for w in [0.05, 0.32, 0.06, 0.05, 0.12, 0.12, 0.12, 0.16]]
    HEADERS = [p(h,'th') for h in ['Lot','Désignation','Qté','Unité','Basic (FCFA)','High-End','Luxury','Marque / Réf.']]

    def make_table(rows):
        t = Table([HEADERS] + rows, colWidths=CW_COLS, repeatRows=1)
        t.setStyle(table_style())
        return t

    # En-tête
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(d.nom, S['titre']))
    story.append(Paragraph(f'BOQ MEP Détaillé — {d.ville} — R+{d.nb_niveaux-1} — {d.usage.value.capitalize()}', S['sous_titre']))
    story.append(Paragraph(
        f'Surface bâtie : {fmt_n(surf,0,"m²")} | {rm.nb_logements} logements | {rm.nb_personnes} personnes | '
        f'3 gammes : Basic / High-End / Luxury',
        S['body']))
    story.append(Paragraph(
        'Prix unitaires marché local 2026 — fournis posés — marge ±15%. '
        'Document utilisable pour consultation d\'entreprises.',
        S['note']))
    story.append(Spacer(1, 2*mm))

    totaux = {}

    # ══════════════════════════════════════════════════════════
    # LOT E — ÉLECTRICITÉ COURANTS FORTS
    # ══════════════════════════════════════════════════════════
    story += section_title('LOT E', 'ÉLECTRICITÉ COURANTS FORTS (NF C 15-100)')
    story.append(Paragraph(el.note_dimensionnement, S['note']))
    story.append(Spacer(1, 2*mm))

    # Sélection transformateur
    transfo_pu = {100: px.transfo_160kva, 160: px.transfo_160kva,
                   250: px.transfo_250kva, 400: px.transfo_400kva,
                   630: px.transfo_400kva, 1000: px.transfo_400kva*2}.get(el.transfo_kva, px.transfo_160kva)
    ge_pu = {60: px.groupe_electrogene_100kva, 100: px.groupe_electrogene_100kva,
              160: px.groupe_electrogene_200kva, 200: px.groupe_electrogene_200kva,
              250: px.groupe_electrogene_200kva, 400: px.groupe_electrogene_400kva}.get(el.groupe_electrogene_kva, px.groupe_electrogene_200kva)

    L_cable = int(surf * 2.5)  # ml câblage estimé
    nb_lum = int(surf / 12)    # 1 luminaire / 12m²

    rows_elec = [
        _row('E.1', f'Poste HTA/BT — transformateur {el.transfo_kva} kVA', 1, 'U',
             transfo_pu, int(transfo_pu*1.15), int(transfo_pu*1.40),
             'Schneider / ABB / Siemens'),
        _row('E.2', 'TGBT — tableau général basse tension', 1, 'U',
             3_500_000, 5_500_000, 8_000_000,
             'Schneider Prisma / ABB MNS'),
        _row('E.3', f'Groupe électrogène {el.groupe_electrogene_kva} kVA — insonorisé', 1, 'U',
             ge_pu, int(ge_pu*1.20), int(ge_pu*1.45),
             'FG Wilson / Caterpillar / Cummins'),
        _row('E.4', f'Compteurs — {el.nb_compteurs} unités',
             el.nb_compteurs, 'U', px.compteur_monophase, px.compteur_triphase, int(px.compteur_triphase*1.3),
             'SENELEC compatible'),
        _row('E.5', 'Colonne montante + tableaux divisionnaires',
             d.nb_niveaux, 'niv.', 1_200_000, 1_800_000, 2_500_000,
             f'Section {el.section_colonne_mm2} mm²'),
        _row('E.6', f'Câblage cuivre distribution — {L_cable} ml',
             L_cable, 'ml', px.canalisation_cuivre_ml, int(px.canalisation_cuivre_ml*1.3), int(px.canalisation_cuivre_ml*1.6),
             'Câbles NYM / H07RN'),
        _row('E.7', f'Luminaires LED — {nb_lum} unités',
             nb_lum, 'U', px.luminaire_led_standard, px.luminaire_led_premium, int(px.luminaire_led_premium*1.5),
             'Philips / Osram / Legrand'),
        _row('E.8', 'Prises de courant + interrupteurs',
             int(surf/8), 'U', 12_000, 22_000, 38_000,
             'Legrand Mosaic / Schneider Unica'),
        _row('E.9', 'Mise à la terre + parafoudres',
             1, 'forfait', 850_000, 1_200_000, 1_800_000,
             'Obligatoire NF C 15-100'),
    ]

    c_elec_b = (transfo_pu + 3_500_000 + ge_pu + el.nb_compteurs*px.compteur_monophase +
                d.nb_niveaux*1_200_000 + L_cable*px.canalisation_cuivre_ml +
                nb_lum*px.luminaire_led_standard + int(surf/8)*12_000 + 850_000)
    c_elec_h = int(c_elec_b * 1.35)
    c_elec_l = int(c_elec_b * 1.75)
    rows_elec.append(_sous_total('SOUS-TOTAL LOT E', c_elec_b, c_elec_h, c_elec_l))
    totaux['E'] = (c_elec_b, c_elec_h, c_elec_l)
    story.append(make_table(rows_elec))

    # ══════════════════════════════════════════════════════════
    # LOT P — PLOMBERIE SANITAIRE
    # ══════════════════════════════════════════════════════════
    story.append(PageBreak())
    story += section_title('LOT P', 'PLOMBERIE SANITAIRE (DTU 60.11)')
    story.append(Paragraph(pl.note_dimensionnement, S['note']))
    story.append(Spacer(1, 2*mm))

    # Citerne
    cuve_pu = px.cuve_eau_5000l if pl.volume_citerne_m3 <= 5 else px.cuve_eau_10000l
    nb_cuves = max(1, math.ceil(pl.volume_citerne_m3 / 10))
    # Surpresseur
    surp_pu = px.pompe_surpresseur_1kw if pl.debit_surpresseur_m3h <= 4 else px.pompe_surpresseur_3kw

    rows_plomb = [
        _row('P.1', f'Citerne polyéthylène {int(pl.volume_citerne_m3)} m³',
             nb_cuves, 'U', cuve_pu, int(cuve_pu*1.20), int(cuve_pu*1.50),
             f'Capacité totale {int(pl.volume_citerne_m3)} m³'),
        _row('P.2', f'Surpresseur {pl.debit_surpresseur_m3h} m³/h — avec variateur',
             1, 'U', surp_pu, int(surp_pu*1.30), int(surp_pu*1.70),
             'Grundfos / DAB / Ebara'),
        _row('P.3', f'Colonnes montantes eau froide DN{pl.diam_colonne_montante_mm}',
             int(d.nb_niveaux * d.hauteur_etage_m * 1.2), 'ml',
             px.colonne_montante_ml, int(px.colonne_montante_ml*1.2), int(px.colonne_montante_ml*1.5),
             'Acier galvanisé / PPR'),
        _row('P.4', 'Réseau EU/EV — PVC DN100/DN150',
             int(surf*0.15), 'ml', px.tuyau_pvc_dn100_ml, int(px.tuyau_pvc_dn100_ml*1.2), int(px.tuyau_pvc_dn100_ml*1.5),
             'Wavin / Georg Fischer'),
        _row('P.5', f'WC + chasse standard — {pl.nb_wc_double_chasse} u.',
             pl.nb_wc_double_chasse, 'U', px.wc_standard, px.wc_double_chasse, int(px.wc_double_chasse*1.8),
             'Basic: Standard | HE: 2 chasses | Lux: Geberit'),
        _row('P.6', f'Robinets mélangeurs — {pl.nb_robinets_eco} u.',
             pl.nb_robinets_eco, 'U', px.robinet_standard, px.robinet_eco, int(px.robinet_eco*2.5),
             'Basic: Local | HE: Grohe | Lux: Hansgrohe'),
        _row('P.7', 'Lavabos + douches + baignoires',
             pl.nb_logements, 'log.', 280_000, 520_000, 1_200_000,
             'Forfait sanitaires par logement'),
        _row('P.8', 'Chauffe-eau électrique 100L backup',
             pl.nb_logements, 'U', px.chauffe_eau_electrique_100l, int(px.chauffe_eau_electrique_100l*1.3), int(px.chauffe_eau_electrique_100l*1.6),
             'Atlantic / Thermor'),
    ]
    if pl.nb_chauffe_eau_solaire > 0:
        rows_plomb.append(_row('P.9', f'Chauffe-eau solaires CESI 200L — {pl.nb_chauffe_eau_solaire} u.',
             pl.nb_chauffe_eau_solaire, 'U', px.chauffe_eau_solaire_200l, int(px.chauffe_eau_solaire_200l*1.2), int(px.chauffe_eau_solaire_200l*1.5),
             'CESI = +6% EDGE énergie — ROI 5-7 ans'))

    c_pl_b = (nb_cuves*cuve_pu + surp_pu +
              int(d.nb_niveaux*d.hauteur_etage_m*1.2*px.colonne_montante_ml) +
              int(surf*0.15*px.tuyau_pvc_dn100_ml) +
              pl.nb_wc_double_chasse*px.wc_standard +
              pl.nb_robinets_eco*px.robinet_standard +
              pl.nb_logements*280_000 +
              pl.nb_logements*px.chauffe_eau_electrique_100l)
    if pl.nb_chauffe_eau_solaire > 0:
        c_pl_b += pl.nb_chauffe_eau_solaire * px.chauffe_eau_solaire_200l
    c_pl_h = int(c_pl_b * 1.40)
    c_pl_l = int(c_pl_b * 1.90)
    rows_plomb.append(_sous_total('SOUS-TOTAL LOT P', c_pl_b, c_pl_h, c_pl_l))
    totaux['P'] = (c_pl_b, c_pl_h, c_pl_l)
    story.append(make_table(rows_plomb))

    # ══════════════════════════════════════════════════════════
    # LOT C — CVC
    # ══════════════════════════════════════════════════════════
    story.append(PageBreak())
    story += section_title('LOT C', 'CLIMATISATION, VENTILATION ET CHAUFFAGE (EN 12831)')
    story.append(Paragraph(cv.note_dimensionnement, S['note']))
    story.append(Spacer(1, 2*mm))

    rows_cvc = []
    if cv.nb_splits_sejour > 0:
        rows_cvc += [
            _row('C.1', f'Splits muraux séjour 1CV — {cv.nb_splits_sejour} u.',
                 cv.nb_splits_sejour, 'U', px.split_1cv, int(px.split_1cv*1.35), int(px.split_1cv*1.80),
                 'Daikin / Mitsubishi / Carrier'),
            _row('C.2', f'Splits muraux chambre 1CV — {cv.nb_splits_chambre} u.',
                 cv.nb_splits_chambre, 'U', px.split_1cv, int(px.split_1cv*1.35), int(px.split_1cv*1.80),
                 'Basic: Standard | Lux: Inverter A+++'),
        ]
    if cv.nb_cassettes > 0:
        rows_cvc.append(_row('C.1', f'Cassettes plafond 4CV — {cv.nb_cassettes} u.',
             cv.nb_cassettes, 'U', px.split_cassette_4cv, int(px.split_cassette_4cv*1.30), int(px.split_cassette_4cv*1.70),
             'Daikin VRV / Mitsubishi City Multi'))

    vmc_pu = px.vmc_double_flux if cv.type_vmc == 'double_flux' else px.vmc_simple_flux
    rows_cvc += [
        _row('C.3', f'VMC {cv.type_vmc} — {cv.nb_vmc} u.',
             cv.nb_vmc, 'U', vmc_pu, int(vmc_pu*1.25), int(vmc_pu*1.60),
             'Atlantic / Aldes / Zehnder (double flux)'),
        _row('C.4', 'Réseau de gaines ventilation',
             int(surf*0.08), 'm²', 18_000, 25_000, 35_000,
             'Gaines acier galva + calorifuge'),
        _row('C.5', 'Grilles + bouches de ventilation',
             int(rm.nb_logements * 4), 'U', 15_000, 25_000, 45_000,
             'Aldes / Price'),
        _row('C.6', 'Régulation et thermostat par zone',
             int(surf/80), 'zone', 85_000, 150_000, 280_000,
             'Honeywell / Siemens / KNX'),
    ]

    nb_sp = cv.nb_splits_sejour + cv.nb_splits_chambre + cv.nb_cassettes
    c_cv_b = (nb_sp * px.split_1cv + cv.nb_vmc * vmc_pu +
              int(surf*0.08*18_000) + int(rm.nb_logements*4*15_000) + int(surf/80*85_000))
    c_cv_h = int(c_cv_b * 1.40)
    c_cv_l = int(c_cv_b * 1.90)
    rows_cvc.append(_sous_total('SOUS-TOTAL LOT C', c_cv_b, c_cv_h, c_cv_l))
    totaux['C'] = (c_cv_b, c_cv_h, c_cv_l)
    story.append(make_table(rows_cvc))

    # ══════════════════════════════════════════════════════════
    # LOT CF — COURANTS FAIBLES
    # ══════════════════════════════════════════════════════════
    story.append(PageBreak())
    story += section_title('LOT CF', 'COURANTS FAIBLES — RÉSEAU, VIDÉO, ACCÈS, INTERPHONIE')
    story.append(Paragraph(cf.note_dimensionnement, S['note']))
    story.append(Spacer(1, 2*mm))

    L_rj45 = int(cf.nb_prises_rj45 * 25)
    rows_cf = [
        _row('CF.1', f'Câblage réseau Cat6A — {L_rj45} ml',
             L_rj45, 'ml', px.cablage_rj45_ml, int(px.cablage_rj45_ml*1.3), int(px.cablage_rj45_ml*1.6),
             'Legrand / Nexans Cat6A'),
        _row('CF.2', f'Prises RJ45 double — {cf.nb_prises_rj45} u.',
             cf.nb_prises_rj45, 'U', px.prise_rj45, int(px.prise_rj45*1.4), int(px.prise_rj45*2.0),
             'Basic: Cat6 | HE: Cat6A | Lux: Cat7'),
        _row('CF.3', f'Baies serveur 12U — {cf.baies_serveur} u.',
             cf.baies_serveur, 'U', px.baie_serveur_12u, int(px.baie_serveur_12u*1.5), int(px.baie_serveur_12u*2.0),
             'APC / Legrand / Eaton'),
        _row('CF.4', f'Caméras IP intérieures — {cf.nb_cameras_int} u.',
             cf.nb_cameras_int, 'U', px.camera_ip_interieure, int(px.camera_ip_interieure*1.8), int(px.camera_ip_interieure*2.5),
             'Axis / Hikvision / Dahua'),
        _row('CF.5', f'Caméras IP extérieures — {cf.nb_cameras_ext} u.',
             cf.nb_cameras_ext, 'U', px.camera_ip_exterieure, int(px.camera_ip_exterieure*1.6), int(px.camera_ip_exterieure*2.2),
             'Axis P-series / Bosch'),
        _row('CF.6', f'Contrôle d\'accès — {cf.nb_portes_controle_acces} portes',
             cf.nb_portes_controle_acces, 'porte', px.systeme_controle_acces, int(px.systeme_controle_acces*1.5), int(px.systeme_controle_acces*2.5),
             'HID / Nedap / Siemens'),
        _row('CF.7', f'Interphones vidéo — {cf.nb_interphones} u.',
             cf.nb_interphones, 'U', px.interphone_video, int(px.interphone_video*1.5), int(px.interphone_video*2.5),
             'Legrand / BTicino / Aiphone'),
        _row('CF.8', 'NVR enregistreur vidéo + stockage',
             cf.baies_serveur, 'U', 850_000, 1_500_000, 3_000_000,
             '30 jours stockage — disques NAS'),
    ]
    if cf.systeme_audio_video:
        rows_cf.append(_row('CF.9', 'Système audio/vidéo collectif (halls, espaces communs)',
             1, 'forfait', 2_500_000, 5_000_000, 12_000_000,
             'Bose / Sonos / Crestron'))

    c_cf_b = (L_rj45*px.cablage_rj45_ml + cf.nb_prises_rj45*px.prise_rj45 +
              cf.baies_serveur*px.baie_serveur_12u +
              cf.nb_cameras_int*px.camera_ip_interieure +
              cf.nb_cameras_ext*px.camera_ip_exterieure +
              cf.nb_portes_controle_acces*px.systeme_controle_acces +
              cf.nb_interphones*px.interphone_video +
              cf.baies_serveur*850_000)
    c_cf_h = int(c_cf_b * 1.55)
    c_cf_l = int(c_cf_b * 2.20)
    rows_cf.append(_sous_total('SOUS-TOTAL LOT CF', c_cf_b, c_cf_h, c_cf_l))
    totaux['CF'] = (c_cf_b, c_cf_h, c_cf_l)
    story.append(make_table(rows_cf))

    # ══════════════════════════════════════════════════════════
    # LOT SI — SÉCURITÉ INCENDIE
    # ══════════════════════════════════════════════════════════
    story.append(PageBreak())
    story += section_title('LOT SI', 'SÉCURITÉ INCENDIE (IT 246 — France/Sénégal)')
    story.append(Paragraph(si.note_dimensionnement, S['note']))
    story.append(Spacer(1, 2*mm))

    centrale_pu = px.centrale_incendie_32zones if si.centrale_zones > 16 else px.centrale_incendie_16zones

    rows_si = [
        _row('SI.1', f'Centrale incendie adressable — {si.centrale_zones} zones',
             1, 'U', centrale_pu, int(centrale_pu*1.30), int(centrale_pu*1.70),
             'Schneider Esser / Siemens Cerberus / Tyco'),
        _row('SI.2', f'Détecteurs fumée optiques — {si.nb_detecteurs_fumee} u.',
             si.nb_detecteurs_fumee, 'U', px.detecteur_fumee, int(px.detecteur_fumee*1.3), int(px.detecteur_fumee*1.6),
             'Apollo / Siemens / Hochiki'),
        _row('SI.3', f'Déclencheurs manuels — {si.nb_declencheurs_manuels} u.',
             si.nb_declencheurs_manuels, 'U', px.declencheur_manuel, int(px.declencheur_manuel*1.2), int(px.declencheur_manuel*1.5),
             '1 par palier min.'),
        _row('SI.4', f'Sirènes + flashs — {si.nb_sirenes} u.',
             si.nb_sirenes, 'U', px.sirene_flash, int(px.sirene_flash*1.2), int(px.sirene_flash*1.5),
             '1 par niveau min.'),
        _row('SI.5', f'Extincteurs CO2 6kg — {si.nb_extincteurs_co2} u.',
             si.nb_extincteurs_co2, 'U', px.extincteur_6kg_co2, int(px.extincteur_6kg_co2*1.2), int(px.extincteur_6kg_co2*1.4),
             'Amerex / Firex / Sicli'),
        _row('SI.6', f'Extincteurs poudre 9kg — {si.nb_extincteurs_poudre} u.',
             si.nb_extincteurs_poudre, 'U', px.extincteur_9kg_poudre, int(px.extincteur_9kg_poudre*1.2), int(px.extincteur_9kg_poudre*1.4),
             'Locaux techniques + parkings'),
        _row('SI.7', f'RIA DN25 — {int(si.longueur_ria_ml)} ml',
             int(si.longueur_ria_ml), 'ml', px.ria_dn25_ml, int(px.ria_dn25_ml*1.2), int(px.ria_dn25_ml*1.4),
             f'Obligatoire {si.categorie_erp}'),
    ]
    if si.sprinklers_requis and si.nb_tetes_sprinkler > 0:
        rows_si += [
            _row('SI.8', f'Centrale sprinkler + réseau alimentation',
                 1, 'U', px.sprinkler_centrale, int(px.sprinkler_centrale*1.2), int(px.sprinkler_centrale*1.5),
                 '⚠ Obligatoire — poste significatif'),
            _row('SI.9', f'Têtes de sprinkler — {si.nb_tetes_sprinkler} u.',
                 si.nb_tetes_sprinkler, 'U', px.sprinkler_tete, int(px.sprinkler_tete*1.2), int(px.sprinkler_tete*1.4),
                 f'1 tête / 9m² — {si.nb_tetes_sprinkler} têtes'),
        ]
    if si.desenfumage_requis:
        c_desenfum = int(surf * 3500)
        rows_si.append(_row('SI.10', 'Désenfumage — volets motorisés + gaines',
             1, 'forfait', c_desenfum, int(c_desenfum*1.3), int(c_desenfum*1.6),
             '⚠ Obligatoire — vérifier IT 246'))

    c_si_b = (centrale_pu + si.nb_detecteurs_fumee*px.detecteur_fumee +
              si.nb_declencheurs_manuels*px.declencheur_manuel +
              si.nb_sirenes*px.sirene_flash +
              si.nb_extincteurs_co2*px.extincteur_6kg_co2 +
              si.nb_extincteurs_poudre*px.extincteur_9kg_poudre +
              int(si.longueur_ria_ml*px.ria_dn25_ml) +
              (si.nb_tetes_sprinkler*px.sprinkler_tete + px.sprinkler_centrale if si.sprinklers_requis else 0) +
              (int(surf*3500) if si.desenfumage_requis else 0))
    c_si_h = int(c_si_b * 1.30)
    c_si_l = int(c_si_b * 1.60)
    rows_si.append(_sous_total('SOUS-TOTAL LOT SI', c_si_b, c_si_h, c_si_l))
    totaux['SI'] = (c_si_b, c_si_h, c_si_l)
    story.append(make_table(rows_si))

    # ══════════════════════════════════════════════════════════
    # LOT ASC — ASCENSEURS
    # ══════════════════════════════════════════════════════════
    if asc.nb_ascenseurs > 0:
        story.append(PageBreak())
        story += section_title('LOT ASC', 'ASCENSEURS ET MONTE-CHARGES (EN 81-20/50)')
        story.append(Paragraph(f'{asc.note_dimensionnement} | {asc.note_impact_prix}', S['note']))
        story.append(Spacer(1, 2*mm))

        if asc.capacite_kg == 630 and d.nb_niveaux <= 6:
            asc_pu = px.ascenseur_630kg_r4_r6
        elif asc.capacite_kg == 630:
            asc_pu = px.ascenseur_630kg_r7_r10
        elif d.nb_niveaux <= 10:
            asc_pu = px.ascenseur_1000kg_r6_r10
        else:
            asc_pu = px.ascenseur_1000kg_r11_plus

        rows_asc = [
            _row('ASC.1', f'Ascenseur {asc.capacite_kg}kg {asc.vitesse_ms}m/s — {asc.nb_ascenseurs} u.',
                 asc.nb_ascenseurs, 'U', asc_pu, int(asc_pu*1.15), int(asc_pu*1.40),
                 'Otis / Schindler / Kone / Thyssen'),
            _row('ASC.2', 'Trémie béton armé + fosse ascenseur',
                 asc.nb_ascenseurs, 'U', 3_500_000, 4_200_000, 4_200_000,
                 'Inclus dans gros œuvre si prévu'),
            _row('ASC.3', 'Tableau électrique dédié ascenseurs',
                 asc.nb_ascenseurs, 'U', 850_000, 1_200_000, 1_500_000,
                 'Alimentation dédiée NF C 15-100'),
        ]
        if asc.nb_monte_charges > 0:
            rows_asc.append(_row('ASC.4', f'Monte-charge 500kg — {asc.nb_monte_charges} u.',
                 asc.nb_monte_charges, 'U', px.monte_charge_500kg, int(px.monte_charge_500kg*1.15), int(px.monte_charge_500kg*1.35),
                 'Service + cuisine hôtel'))

        c_asc_b = (asc.nb_ascenseurs * asc_pu + asc.nb_ascenseurs*3_500_000 +
                   asc.nb_ascenseurs*850_000 + asc.nb_monte_charges*px.monte_charge_500kg)
        c_asc_h = int(c_asc_b * 1.15)
        c_asc_l = int(c_asc_b * 1.40)
        rows_asc.append(_sous_total('SOUS-TOTAL LOT ASC', c_asc_b, c_asc_h, c_asc_l))
        totaux['ASC'] = (c_asc_b, c_asc_h, c_asc_l)
        story.append(make_table(rows_asc))

    # ══════════════════════════════════════════════════════════
    # LOT AUTO — AUTOMATISATION
    # ══════════════════════════════════════════════════════════
    story += section_title('LOT AUTO', f'AUTOMATISATION GTB — {auto.niveau.upper()} ({auto.protocole})')
    story.append(Paragraph(auto.note_dimensionnement, S['note']))
    story.append(Spacer(1, 2*mm))

    rows_auto = [
        _row('AUTO.1', f'Système GTB/BMS — {auto.protocole}',
             1, 'forfait',
             5_000_000 if auto.niveau == 'basic' else 12_000_000 if auto.niveau == 'standard' else px.bms_systeme,
             8_000_000 if auto.niveau == 'basic' else 18_000_000 if auto.niveau == 'standard' else int(px.bms_systeme*1.4),
             12_000_000 if auto.niveau == 'basic' else 28_000_000 if auto.niveau == 'standard' else int(px.bms_systeme*1.8),
             'Schneider EcoStruxure / Siemens Desigo / KNX'),
        _row('AUTO.2', f'Gestion éclairage — {auto.nb_points_controle} points',
             auto.nb_points_controle, 'pt', px.eclairage_detecteur_presence, int(px.eclairage_detecteur_presence*1.4), int(px.eclairage_detecteur_presence*2.0),
             'Détecteurs présence + variation'),
        _row('AUTO.3', 'Gestion CVC centralisée',
             1, 'forfait', 2_500_000, 4_500_000, 8_000_000,
             'Intégré BMS ou standalone'),
    ]
    if auto.gestion_energie:
        rows_auto.append(_row('AUTO.4', 'Comptage énergie + tableaux de bord',
             1, 'forfait', 3_500_000, 6_000_000, 10_000_000,
             'Schneider PowerLogic / ABB Ability'))
    if not auto.bms_requis:
        rows_auto.append(_row('AUTO.5', f'Domotique par logement — {rm.nb_logements} u.',
             rm.nb_logements, 'U', px.domotique_logement, int(px.domotique_logement*1.5), int(px.domotique_logement*2.5),
             'KNX / Legrand MyHome / Somfy'))

    c_auto_b_base = 5_000_000 if auto.niveau == 'basic' else (12_000_000 if auto.niveau == 'standard' else px.bms_systeme)
    c_auto_b = (c_auto_b_base + auto.nb_points_controle*px.eclairage_detecteur_presence +
                2_500_000 + (rm.nb_logements*px.domotique_logement if not auto.bms_requis else 0))
    c_auto_h = int(c_auto_b * 1.55)
    c_auto_l = int(c_auto_b * 2.20)
    rows_auto.append(_sous_total('SOUS-TOTAL LOT AUTO', c_auto_b, c_auto_h, c_auto_l))
    totaux['AUTO'] = (c_auto_b, c_auto_h, c_auto_l)
    story.append(make_table(rows_auto))

    # ══════════════════════════════════════════════════════════
    # RÉCAPITULATIF GÉNÉRAL MEP
    # ══════════════════════════════════════════════════════════
    story.append(PageBreak())
    story += section_title('RÉCAP', 'RÉCAPITULATIF GÉNÉRAL BOQ MEP')

    total_b = sum(v[0] for v in totaux.values())
    total_h = sum(v[1] for v in totaux.values())
    total_l = sum(v[2] for v in totaux.values())
    ratio_b = int(total_b / surf) if surf > 0 else 0
    ratio_h = int(total_h / surf) if surf > 0 else 0

    lot_labels = {
        'E': 'Électricité courants forts',
        'P': 'Plomberie sanitaire',
        'C': 'CVC — Climatisation + ventilation',
        'CF': 'Courants faibles',
        'SI': 'Sécurité incendie',
        'ASC': 'Ascenseurs et monte-charges',
        'AUTO': 'Automatisation GTB',
    }

    CW_RECAP = [CW*w for w in [0.06, 0.38, 0.16, 0.16, 0.16, 0.08]]
    recap_rows = [[p(h,'th') for h in ['Lot','Désignation','BASIC','HIGH-END','LUXURY','% TOTAL']]]
    for k, (cb, ch, cl) in totaux.items():
        recap_rows.append([
            p(k,'td_b'), p(lot_labels.get(k,'—')),
            p(fmt_fcfa(cb),'td_r'), p(fmt_fcfa(ch),'td_r'), p(fmt_fcfa(cl),'td_r'),
            p(f'{cb/total_b*100:.0f}%','td_r'),
        ])
    recap_rows.append([
        p('','td_b'), p('TOTAL MEP','td_b'),
        p(fmt_fcfa(total_b),'td_g_r'), p(fmt_fcfa(total_h),'td_g_r'), p(fmt_fcfa(total_l),'td_g_r'),
        p('100%','td_b'),
    ])
    recap_rows.append([
        p('','td_b'), p(f'Coût MEP / m² bâti ({fmt_n(surf,0)} m²)','td_b'),
        p(f'{ratio_b:,} FCFA/m²'.replace(',', ' '),'td_r'),
        p(f'{ratio_h:,} FCFA/m²'.replace(',', ' '),'td_r'),
        p('—','td_r'), p('','td_b'),
    ])

    tr = Table(recap_rows, colWidths=CW_RECAP, repeatRows=1)
    ts_r = table_style(zebra=False)
    ts_r.add('BACKGROUND', (0,-2), (-1,-1), VERT_LIGHT)
    ts_r.add('FONTNAME',   (0,-2), (-1,-1), 'Helvetica-Bold')
    ts_r.add('LINEABOVE',  (0,-2), (-1,-2), 1.5, VERT)
    tr.setStyle(ts_r)
    story.append(tr)

    # Note recommandation gamme
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(rm.boq.recommandation, S['note']))
    story.append(Paragraph(rm.boq.note_choix, S['small']))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        '* Ce BOQ est une estimation d\'avant-projet (±15%). '
        'Les quantités sont calculées depuis les bilans techniques MEP. '
        'Un métré définitif sur plans d\'exécution est requis avant appel d\'offres.',
        S['disc']))

    return story
