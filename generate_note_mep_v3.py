"""
generate_note_mep_v3.py — Note de calcul MEP & Automation
Tijan AI — Électricité, Plomberie, CVC, Domotique
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
from datetime import datetime
import math

NOIR = colors.HexColor("#111111")
GRIS = colors.HexColor("#888888")
GRIS_CLAIR = colors.HexColor("#E5E5E5")
FOND = colors.HexColor("#FAFAFA")
BLANC = colors.white
VERT = colors.HexColor("#43A956")

def get_styles():
    return {
        'brand':   ParagraphStyle('brand', fontSize=8, textColor=VERT, fontName='Helvetica-Bold', spaceAfter=2),
        'title':   ParagraphStyle('title', fontSize=16, textColor=NOIR, fontName='Helvetica-Bold', spaceAfter=4),
        'subtitle':ParagraphStyle('sub', fontSize=9, textColor=GRIS, spaceAfter=8),
        'h2':      ParagraphStyle('h2', fontSize=11, textColor=VERT, fontName='Helvetica-Bold', spaceBefore=10, spaceAfter=5),
        'h3':      ParagraphStyle('h3', fontSize=9, textColor=NOIR, fontName='Helvetica-Bold', spaceBefore=6, spaceAfter=3),
        'normal':  ParagraphStyle('n', fontSize=9, textColor=NOIR, spaceAfter=3, leading=13),
        'small':   ParagraphStyle('s', fontSize=7.5, textColor=GRIS, spaceAfter=2),
        'disc':    ParagraphStyle('d', fontSize=7, textColor=GRIS, spaceAfter=2),
    }

def hf(canvas, doc, nom, date_str):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(VERT); canvas.setFont('Helvetica-Bold', 8)
    canvas.drawString(15*mm, h-12*mm, "TIJAN AI")
    canvas.setFillColor(GRIS); canvas.setFont('Helvetica', 7.5)
    canvas.drawString(15*mm, h-17*mm, f"{nom}  —  Note de Calcul MEP & Automation")
    canvas.setStrokeColor(GRIS_CLAIR)
    canvas.line(15*mm, h-19*mm, w-15*mm, h-19*mm)
    canvas.line(15*mm, 14*mm, w-15*mm, 14*mm)
    canvas.setFont('Helvetica', 7); canvas.setFillColor(GRIS)
    canvas.drawString(15*mm, 10*mm, f"Tijan AI — {date_str} | Document d'assistance technique")
    canvas.drawRightString(w-15*mm, 10*mm, f"Page {doc.page}")
    canvas.restoreState()

def calc_table(data, col_widths):
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), VERT),
        ('TEXTCOLOR', (0,0), (-1,0), BLANC),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('GRID', (0,0), (-1,-1), 0.3, GRIS_CLAIR),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [BLANC, FOND]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 7),
    ]))
    return t

def generer_note_mep(resultats, buf, params_dict=None):
    params = {}
    if params_dict:
        params = vars(params_dict) if hasattr(params_dict, '__dict__') else params_dict

    date_str = datetime.now().strftime("%d/%m/%Y")
    nom = params.get('nom', 'Projet Tijan')
    ville = params.get('ville', 'Dakar').capitalize()
    nb_niveaux = params.get('nb_niveaux', 5)
    surface_emprise = params.get('surface_emprise_m2', 500)
    surface_totale = surface_emprise * nb_niveaux
    nb_logements = max(1, int(surface_totale / 120))

    # Calculs MEP
    P_logements = nb_logements * 8 * 0.65
    P_clim = nb_logements * 3 * 0.70
    P_ascenseurs = 2 * 15 * 0.80
    P_pompes = 3 * 7 * 0.70
    P_eclairage = surface_totale * 0.008
    P_ventilation = 30 * 0.80
    P_reserve = (P_logements + P_clim + P_ascenseurs + P_pompes + P_eclairage + P_ventilation) * 0.10
    P_total = P_logements + P_clim + P_ascenseurs + P_pompes + P_eclairage + P_ventilation + P_reserve

    Q_logements = nb_logements * 4 * 150
    Q_incendie = 4800
    Q_communs = 2000
    Q_reserve = (Q_logements + Q_incendie + Q_communs) * 0.15
    Q_total = Q_logements + Q_incendie + Q_communs + Q_reserve

    P_frig = surface_totale * 0.05
    P_frig_installed = P_frig * 1.22

    doc = SimpleDocTemplate(buf, pagesize=A4,
        rightMargin=15*mm, leftMargin=15*mm, topMargin=25*mm, bottomMargin=20*mm,
        title=f"Note MEP — {nom}", author="Tijan AI")

    def _hf(c, d): hf(c, d, nom, date_str)
    styles = get_styles()
    story = []

    # Page de garde
    story.append(Spacer(1, 10*mm))
    story.append(Paragraph("TIJAN AI", styles['brand']))
    story.append(Paragraph("NOTE DE CALCUL MEP & AUTOMATION", styles['title']))
    story.append(Paragraph("Electricite Generale | Plomberie | CVC | Domotique / BMS", styles['subtitle']))
    story.append(HRFlowable(width="100%", thickness=1.5, color=VERT))
    story.append(Spacer(1, 6*mm))

    entete = [
        ["Projet", nom], ["Localisation", f"{ville}, Senegal"],
        ["Description", f"R+{nb_niveaux-1} — {nb_niveaux} niveaux"],
        ["Surface totale", f"{surface_totale:,} m²"],
        ["Logements estimes", str(nb_logements)],
        ["Date", date_str],
    ]
    t = Table(entete, colWidths=[50*mm, 125*mm])
    t.setStyle(TableStyle([('FONTSIZE',(0,0),(-1,-1),9),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),
        ('TEXTCOLOR',(0,0),(0,-1),VERT),('GRID',(0,0),(-1,-1),0.3,GRIS_CLAIR),
        ('BACKGROUND',(0,0),(-1,-1),FOND),('TOPPADDING',(0,0),(-1,-1),4),
        ('BOTTOMPADDING',(0,0),(-1,-1),4),('LEFTPADDING',(0,0),(-1,-1),8)]))
    story.append(t)
    story.append(PageBreak())

    # 1. ELECTRICITE
    story.append(Paragraph("1. ELECTRICITE GENERALE", styles['h2']))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_CLAIR))
    story.append(Paragraph("1.1 Bilan de puissance", styles['h3']))

    elec_data = [
        ["Usage", "Puissance unitaire", "Nb", "Foisonnement", "Puissance appelee (kVA)"],
        ["Logements (eclairage + prises)", "8 kVA", str(nb_logements), "0.65", f"{P_logements:.0f}"],
        ["Climatisation logements", "3 kVA/logt", str(nb_logements), "0.70", f"{P_clim:.0f}"],
        ["Ascenseurs (2 x 15 kW)", "15 kW", "2", "0.80", f"{P_ascenseurs:.0f}"],
        ["Pompes (eau, incendie)", "7 kW", "3", "0.70", f"{P_pompes:.0f}"],
        ["Eclairage communs + parking", f"{surface_totale*0.008:.0f} kW", "1", "1.00", f"{P_eclairage:.0f}"],
        ["Ventilation CVC centralisee", "30 kW", "1", "0.80", f"{P_ventilation:.0f}"],
        ["Reserve (10%)", "—", "—", "—", f"{P_reserve:.0f}"],
        ["TOTAL PUISSANCE SOUSCRITE", "", "", "", f"{P_total:.0f}"],
    ]
    t_elec = calc_table(elec_data, [55*mm, 30*mm, 15*mm, 25*mm, 35*mm])
    t_elec.setStyle(TableStyle([
        
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F0FAF1')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
    ]))
    story.append(t_elec)
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph("1.2 Architecture electrique", styles['h3']))
    archi_elec = [
        ["Composant", "Caracteristiques", "Localisation"],
        ["Transformateur SENELEC", f"{int(P_total*1.2/100)*100} kVA — HTA/BT — 30kV/380V", "Local technique SS"],
        ["TGBT principal", f"{int(P_total*2.5):.0f}A — modules — IP55", "Local technique SS"],
        ["Groupe electrogene secours", f"{int(P_total*0.7/100)*100} kVA — Insonorise", "Local technique SS"],
        ["Tableaux divisionnaires (TD)", f"1 par niveau — {nb_niveaux} niveaux", "Gaine technique/palier"],
        ["Tableaux logements (TL)", f"1 par logement — {nb_logements} logements", "Entree logement"],
        ["Cablage principal", f"Cables U1000 R2V — section 3x185mm²", "Gaine technique verticale"],
        ["Eclairage securite (BAES)", "8 lm/m² — autonomie 1h", "Couloirs + cages"],
        ["Paratonnerre", "Systeme ESE — rayon 70m", "Toiture"],
    ]
    story.append(calc_table(archi_elec, [55*mm, 80*mm, 40*mm]))
    story.append(PageBreak())

    # 2. PLOMBERIE
    story.append(Paragraph("2. PLOMBERIE SANITAIRE", styles['h2']))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_CLAIR))
    story.append(Paragraph("2.1 Bilan des besoins en eau", styles['h3']))
    story.append(Paragraph(
        f"Selon NF EN 806 et normes ONAS. Dotation retenue : 150 L/hab/jour (milieu urbain dakarois).",
        styles['small']))
    story.append(Spacer(1, 2*mm))

    eau_data = [
        ["Poste", "Debit (L/j)", "Calcul"],
        [f"Logements ({nb_logements} x 4 pers. x 150 L)", f"{Q_logements:,}", f"{nb_logements} x 4 x 150"],
        ["Besoins incendie (RIA + sprinklers)", f"{Q_incendie:,}", "Reserve 4h x 1200 L/h"],
        ["Nettoyage communs + espaces verts", f"{Q_communs:,}", "Forfait"],
        ["Reserve (15%)", f"{Q_reserve:,.0f}", "—"],
        ["BESOIN JOURNALIER TOTAL", f"{Q_total:,.0f} L/j ≈ {Q_total/1000:.0f} m³/j", "—"],
    ]
    t_eau = calc_table(eau_data, [80*mm, 40*mm, 55*mm])
    t_eau.setStyle(TableStyle([
        
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F0FAF1')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
    ]))
    story.append(t_eau)
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph("2.2 Architecture reseau plomberie", styles['h3']))
    plomb_data = [
        ["Equipement", "Dimensions / Capacite", "Localisation"],
        ["Citerne enterree eau de ville", f"{int(Q_total/1000)*2} m³ — beton etanche", "Sous-sol"],
        ["Bache incendie dediee", "12 m³ — acier inox", "Sous-sol"],
        ["Surpresseur eau domestique", "Q=6 m³/h — HMT 70m — 5.5 kW", "Local technique SS"],
        ["Pompe incendie principale", "Q=1200 L/h — HMT 50m — 15 kW", "Local technique SS"],
        ["Colonnes montantes EF", "DN63 acier galva — 2 colonnes", "Gaine technique"],
        ["Colonnes montantes ECS", "DN40 cuivre calorifuge", "Gaine technique"],
        [f"Chauffe-eau solaires", f"{nb_logements} x 200L — collecteurs toiture", "Toiture + gaines"],
        ["Reseau EU/EV", "PVC serie 51 — DN100 a DN150", "Gaines/Faux plafond"],
        ["RIA (Robinets Incendie Armes)", f"DN40 — 1 par palier — {nb_niveaux} niveaux", "Paliers"],
    ]
    story.append(calc_table(plomb_data, [65*mm, 65*mm, 45*mm]))
    story.append(PageBreak())

    # 3. CVC
    story.append(Paragraph("3. CLIMATISATION, VENTILATION & CHAUFFAGE (CVC)", styles['h2']))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_CLAIR))
    story.append(Paragraph("3.1 Bilan thermique", styles['h3']))
    story.append(Paragraph(
        f"Calcul selon RT Senegal et donnees meteo Dakar (zone 1 — Climat sahelien cotier). "
        f"T ext base = 35°C, T int souhaitee = 24°C.",
        styles['small']))
    story.append(Spacer(1, 2*mm))

    cvc_data = [
        ["Source de chaleur", "Puissance (W/m²)", "Surface (m²)", "Puissance totale (W)"],
        ["Apports solaires (facades E+O)", "65", f"{surface_totale*0.35:.0f}", f"{surface_totale*0.35*65:.0f}"],
        ["Apports internes (occupants)", "6", f"{surface_totale:.0f}", f"{surface_totale*6:.0f}"],
        ["Apports equipements", "8", f"{surface_totale:.0f}", f"{surface_totale*8:.0f}"],
        ["Renouvellement d'air (35°C ext)", "12", f"{surface_totale:.0f}", f"{surface_totale*12:.0f}"],
        ["PUISSANCE TOTALE A EXTRAIRE", "", "", f"{P_frig*1000:.0f} W ≈ {P_frig:.0f} kW"],
        ["PUISSANCE FRIGORIFIQUE INSTALLEE", "", "", f"{P_frig_installed:.0f} kW (+22% marge)"],
    ]
    t_cvc = calc_table(cvc_data, [65*mm, 25*mm, 25*mm, 45*mm])
    t_cvc.setStyle(TableStyle([
        
        ('BACKGROUND', (0,-2), (-1,-1), colors.HexColor('#F0FAF1')),
        ('FONTNAME', (0,-2), (-1,-1), 'Helvetica-Bold'),
    ]))
    story.append(t_cvc)
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph("3.2 Architecture CVC", styles['h3']))
    archi_cvc = [
        ["Systeme", "Caracteristiques", "Zone desservie"],
        ["Split-system inverter logements", f"1x12 000 BTU/h sejour + 1x9 000 BTU/h chambre", "Logements"],
        ["CTA (Centrale Traitement Air)", "Q=8 000 m³/h — recup. enthalpique", "Communs/couloirs"],
        ["VMC double flux", "Q=150 m³/h/logt — eta=85%", "Logements"],
        ["Extracteurs parking sous-sol", "Q=12 000 m³/h — 4 extracteurs", "Sous-sol"],
        ["Desenfumage cage escalier", "Q=15 000 m³/h — 2 ventilateurs", "Cages escalier"],
        ["Reseau gaines CTA", "Gaines galva isolees — 200x150mm a 500x300mm", "Faux plafond"],
    ]
    story.append(calc_table(archi_cvc, [55*mm, 75*mm, 45*mm]))
    story.append(PageBreak())

    # 4. DOMOTIQUE BMS
    story.append(Paragraph("4. DOMOTIQUE & BUILDING AUTOMATION (BMS)", styles['h2']))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_CLAIR))
    story.append(Paragraph("4.1 Perimetre du systeme BMS", styles['h3']))

    bms_data = [
        ["Module BMS", "Fonctions", "Protocole"],
        ["Gestion eclairage communs", "Detection presence + variation + scenarios", "KNX/DALI"],
        ["Gestion eclairage logements", "On/off + gradation + scenarios ambiance", "KNX"],
        ["Gestion climatisation logements", "Programmation horaire + presence + setpoint", "KNX/Modbus"],
        ["Comptage energetique", "Compteur logement + compteur general", "M-Bus"],
        ["Controle acces immeuble", "Interphone video IP + badge NFC + app", "TCP/IP"],
        ["Videosurveillance (CCTV)", "16 cameras 4K + NVR 8TB + acces mobile", "ONVIF/TCP"],
        ["Gestion ascenseurs", "Supervision etat + appel + maintenance", "BACnet"],
        ["Supervision pompes/groupes", "Demarrage auto + alarmes + consommation", "BACnet/IP"],
        ["Detection incendie (SSI)", "SSI categorie A + alarme sonore/visuelle", "Analogique"],
        ["Tableau de bord energie", "Dashboard web — consomm. temps reel", "TCP/IP"],
        ["Application residents", "Controle logement + interphone + consomm.", "API REST"],
    ]
    story.append(calc_table(bms_data, [60*mm, 75*mm, 40*mm]))
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph("4.2 Infrastructure reseau batiment", styles['h3']))
    reseau_data = [
        ["Equipement reseau", "Specifications", "Localisation"],
        ["Switch coeur de reseau", "48 ports GigE PoE+ — manageable", "Local tech. SS"],
        ["Switchs d'etage", f"24 ports GigE PoE — 1 par niveau", "Gaine technique"],
        ["Cablage cuivre", "Cat. 6A U/FTP — 1 prise RJ45/piece", "Logements"],
        ["Cablage backbone", "Fibre optique OS2 — 12 brins", "Gaine technique"],
        ["Point d'acces WiFi", f"WiFi 6 (802.11ax) — 1 par palier + 1/logt", "Plafond"],
        ["Routeur/Firewall", "Entreprise — VPN — VLAN — QoS", "Local tech. SS"],
        ["Onduleur reseau (UPS)", "3 kVA — autonomie 30 min", "Local tech. SS"],
        ["Serveur BMS", "Rack 2U — i7/32GB/2TB SSD — Linux", "Local tech. SS"],
    ]
    story.append(calc_table(reseau_data, [60*mm, 80*mm, 35*mm]))
    story.append(Spacer(1, 6*mm))

    # Récap bilan MEP
    story.append(Paragraph("BILAN MEP — RECAPITULATIF", styles['h2']))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_CLAIR))
    bilan_data = [
        ["Lot MEP", "Valeur cle", "Unite"],
        ["Puissance electrique souscrite", f"{P_total:.0f}", "kVA"],
        ["Transformateur", f"{int(P_total*1.2/100)*100}", "kVA"],
        ["Groupe electrogene secours", f"{int(P_total*0.7/100)*100}", "kVA"],
        ["Besoin journalier eau", f"{Q_total/1000:.0f}", "m³/j"],
        ["Puissance frigorifique installee", f"{P_frig_installed:.0f}", "kW"],
        ["Nombre de logements", str(nb_logements), "unites"],
        ["Surface totale desservie", f"{surface_totale:,}", "m²"],
        ["Critere EDGE energie", ">= 20%", "reduction vs reference"],
        ["Critere EDGE eau", ">= 20%", "reduction vs reference"],
    ]
    story.append(calc_table(bilan_data, [80*mm, 50*mm, 45*mm]))
    story.append(Spacer(1, 5*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_CLAIR))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(
        "Note de calcul MEP generee par Tijan AI sur la base des parametres fournis. "
        "A verifier et completer par un ingenieur fluides agree avant execution.",
        styles['disc']))

    doc.build(story, onFirstPage=_hf, onLaterPages=_hf)
