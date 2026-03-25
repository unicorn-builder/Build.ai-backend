"""
generate_fiches_mep_v3.py — Fiches Techniques Equipements MEP
Tijan AI — Electricite, Plomberie, CVC, Domotique
Fournisseurs Dakar inclus
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm

import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_LOGO = next((c for c in [_os.path.join(_HERE,'tijan_logo_crop.png'),'/opt/render/project/src/tijan_logo_crop.png'] if _os.path.exists(c)), None)
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
from datetime import datetime
import io

NOIR=colors.HexColor("#111111"); GRIS=colors.HexColor("#888888")
GRIS_CLAIR=colors.HexColor("#E5E5E5"); FOND=colors.HexColor("#FAFAFA")
BLANC=colors.white; VERT=colors.HexColor("#43A956")

def gs():
    return {
        'brand': ParagraphStyle('b',fontSize=8,textColor=VERT,fontName='Helvetica-Bold',spaceAfter=2),
        'title': ParagraphStyle('t',fontSize=16,textColor=NOIR,fontName='Helvetica-Bold',spaceAfter=4),
        'sub':   ParagraphStyle('s',fontSize=9,textColor=GRIS,spaceAfter=8),
        'h2':    ParagraphStyle('h2',fontSize=11,textColor=VERT,fontName='Helvetica-Bold',spaceBefore=10,spaceAfter=5),
        'h3':    ParagraphStyle('h3',fontSize=9,textColor=NOIR,fontName='Helvetica-Bold',spaceBefore=6,spaceAfter=3),
        'fiche': ParagraphStyle('f',fontSize=8.5,textColor=VERT,fontName='Helvetica-Bold',spaceBefore=8,spaceAfter=4),
        'small': ParagraphStyle('sm',fontSize=7.5,textColor=GRIS,spaceAfter=2),
        'disc':  ParagraphStyle('d',fontSize=7,textColor=GRIS,spaceAfter=2),
    }

def hf(canvas,doc,nom,date_str):
    canvas.saveState(); w,h=A4
    canvas.setFillColor(VERT); canvas.setFont('Helvetica-Bold',8); canvas.drawString(15*mm,h-12*mm,"TIJAN AI")
    canvas.setFillColor(GRIS); canvas.setFont('Helvetica',7.5)
    canvas.drawString(15*mm,h-17*mm,f"{nom}  —  Fiches Techniques Equipements MEP & Automation")
    canvas.setStrokeColor(GRIS_CLAIR); canvas.line(15*mm,h-19*mm,w-15*mm,h-19*mm)
    canvas.line(15*mm,14*mm,w-15*mm,14*mm)
    canvas.setFont('Helvetica',7); canvas.setFillColor(GRIS)
    canvas.drawString(15*mm,10*mm,f"Tijan AI — {date_str} | Document d'assistance technique")
    canvas.drawRightString(w-15*mm,10*mm,f"Page {doc.page}"); canvas.restoreState()

def fiche(titre, specs, fournisseur, note=None):
    story = []
    story.append(Paragraph(titre, ParagraphStyle('ft',fontSize=9,textColor=VERT,fontName='Helvetica-Bold',spaceBefore=8,spaceAfter=3)))
    
    mid = len(specs)//2
    left = specs[:mid]; right = specs[mid:]
    rows = []
    for i in range(max(len(left),len(right))):
        l = left[i] if i < len(left) else ("","")
        r = right[i] if i < len(right) else ("","")
        rows.append([l[0], l[1], r[0], r[1]])
    
    t = Table(rows, colWidths=[45*mm,42*mm,45*mm,43*mm])
    t.setStyle(TableStyle([
        ('FONTSIZE',(0,0),(-1,-1),8),
        ('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('FONTNAME',(2,0),(2,-1),'Helvetica-Bold'),
        ('TEXTCOLOR',(0,0),(0,-1),VERT),('TEXTCOLOR',(2,0),(2,-1),VERT),
        ('GRID',(0,0),(-1,-1),0.3,GRIS_CLAIR),('ROWBACKGROUNDS',(0,0),(-1,-1),[BLANC,FOND]),
        ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
        ('LEFTPADDING',(0,0),(-1,-1),5),
    ]))
    story.append(t)
    story.append(Paragraph(f"Fournisseurs Dakar : {fournisseur}", 
        ParagraphStyle('f',fontSize=7,textColor=GRIS,spaceAfter=2,spaceBefore=2)))
    if note:
        story.append(Paragraph(f"Note : {note}",
            ParagraphStyle('n',fontSize=7,textColor=colors.HexColor("#B45309"),spaceAfter=3)))
    story.append(HRFlowable(width="100%",thickness=0.3,color=GRIS_CLAIR))
    return story

def generer_fiches_mep(resultats, buf, params_dict=None):
    params = {}
    if params_dict:
        params = vars(params_dict) if hasattr(params_dict,'__dict__') else params_dict

    date_str = datetime.now().strftime("%d/%m/%Y")
    nom = params.get('nom','Projet Tijan')
    nb_niveaux = params.get('nb_niveaux',5)
    surface_totale = params.get('surface_emprise_m2',500) * nb_niveaux
    nb_logements = max(1,int(surface_totale/120))
    P_total = max(200, int((nb_logements*8*0.65 + nb_logements*3*0.7 + 60 + 50)*1.2/100)*100)

    doc = SimpleDocTemplate(buf,pagesize=A4,rightMargin=15*mm,leftMargin=15*mm,
        topMargin=25*mm,bottomMargin=20*mm,title=f"Fiches MEP — {nom}",author="Tijan AI")
    def _hf(c,d): hf(c,d,nom,date_str)
    st = gs(); story = []

    # Page de garde
    story.append(Spacer(1,10*mm))
    story.append(Paragraph("TIJAN AI",st['brand']))
    story.append(Paragraph("FICHES TECHNIQUES EQUIPEMENTS MEP & AUTOMATION",st['title']))
    story.append(Paragraph("Electricite | Plomberie | CVC | Domotique — Fournisseurs Dakar",st['sub']))
    story.append(HRFlowable(width="100%",thickness=1.5,color=VERT))
    story.append(Spacer(1,6*mm))

    entete=[["Projet",nom],["Localisation",params.get('ville','Dakar').capitalize()+", Senegal"],
            ["Niveaux",f"R+{nb_niveaux-1}"],["Surface totale",f"{surface_totale:,} m²"],
            ["Logements",str(nb_logements)],["Date",date_str]]
    t=Table(entete,colWidths=[50*mm,125*mm])
    t.setStyle(TableStyle([('FONTSIZE',(0,0),(-1,-1),9),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),
        ('TEXTCOLOR',(0,0),(0,-1),VERT),('GRID',(0,0),(-1,-1),0.3,GRIS_CLAIR),
        ('BACKGROUND',(0,0),(-1,-1),FOND),('TOPPADDING',(0,0),(-1,-1),4),
        ('BOTTOMPADDING',(0,0),(-1,-1),4),('LEFTPADDING',(0,0),(-1,-1),8)]))
    story.append(t); story.append(PageBreak())

    # 1. EQUIPEMENTS ELECTRIQUES
    story.append(Paragraph("1. EQUIPEMENTS ELECTRIQUES",st['h2']))
    story.append(HRFlowable(width="100%",thickness=0.5,color=GRIS_CLAIR))

    story += fiche(f"EL-01 Transformateur HTA/BT {P_total} kVA",
        [("Puissance nominale",f"{P_total} kVA"),("Tension primaire","30 kV (HTA Senegal)"),
         ("Tension secondaire","380/220V — 50Hz"),("Couplage","Dyn11"),
         ("Pertes a vide","< 620 W"),("Pertes en charge","< 4 600 W"),
         ("Niveau d'isolement","36 kV"),("Liquide isolant","Huile minerale IEC 60296"),
         ("Dimensions (LxlxH)","1 850x900x1 700 mm"),("Poids total","2 450 kg"),
         ("IP","IP44 (exterieur)"),("Certifications","IEC 60076 | NF EN 50588 | CE")],
        "SENELEC agree | ABB Dakar | Schneider Electric SN")

    story += fiche(f"EL-02 Groupe Electrogene Secours {int(P_total*0.65/100)*100} kVA",
        [("Puissance de secours",f"{int(P_total*0.65/100)*100} kVA"),("Moteur diesel","6 cylindres en ligne"),
         ("Regime nominal","1 500 tr/min (50 Hz)"),("Niveau sonore","< 75 dB(A) a 7m"),
         ("Reservoir carburant","500 L (autonomie 24h)"),("Demarrage auto (AMF)","< 10 secondes"),
         ("Alternateur","Brushless — IP23"),("Dimensions","3 500x1 200x1 850 mm"),
         ("Poids","3 200 kg"),("Capotage","Insonorise IP23"),
         ("Certifications","ISO 8528 | IEC 60034 | CE")],
        "Aggreko Dakar | CFAO Energie | Cummins West Africa",
        "Prevoir local ventile avec bac de retention carburant 110% du volume reservoir.")

    story += fiche("EL-03 TGBT 4000A — Tableau General Basse Tension",
        [("Courant nominal","4 000 A"),("Tension assignee","400V / 50Hz"),
         ("Courant de court-circuit","50 kA (1s)"),("Nb de departs","22 modules"),
         ("Disjoncteur general","4P 4000A — declenchement electronique"),
         ("Jeu de barres","Cuivre 4x(5x80x10mm)"),
         ("Inverseur de source (ATS)","Automatique < 1s"),
         ("Dimensions","2 200x600x2 000 mm"),("Degre de protection","IP55 / IK10"),
         ("Matiere enveloppe","Tole acier galva RAL 7035"),
         ("Certifications","IEC 61439-1 | IEC 61439-2")],
        "Schneider Electric SN | Legrand Dakar | ABB Senegal")

    story.append(PageBreak())

    # 2. EQUIPEMENTS PLOMBERIE
    story.append(Paragraph("2. EQUIPEMENTS PLOMBERIE",st['h2']))
    story.append(HRFlowable(width="100%",thickness=0.5,color=GRIS_CLAIR))

    story += fiche("PL-01 Surpresseur Eau Domestique — 6 m³/h",
        [("Debit nominal","6 m³/h"),("Hauteur manometrique","70 mCE"),
         ("Puissance moteur","5.5 kW — 400V/50Hz"),("Type de pompe","Centrifuge multicellulaire verticale"),
         ("Nb de pompes","2 (1 + 1 secours) + vase expansion"),("Pression de service maxi","8 bar"),
         ("Regulation","Variateur de frequence integre"),("Pressostat","Demarrage auto 2 bar / Arret 4 bar"),
         ("Materiaux","Inox 316L — joints EPDM"),("Cuve expansion","60 L — membrane EPDM"),
         ("Dimensions groupe","800x500x1 200 mm"),("Certifications","ISO 9906 | EN 809 | CE | NF")],
        "Grundfos Dakar | Wilo Senegal | DAB Pumps West Africa")

    story += fiche("PL-02 Chauffe-eau solaire 200L avec appoint electrique",
        [("Volume ballon","200 L"),("Surface capteur","2 x 2.0 m² (plat selectif)"),
         ("Puissance thermique capteur","2 600 W/capteur"),("Appoint electrique","3 000 W — resistance blindee inox"),
         ("Temperature maximale","90°C (protection thermique)"),("Isolation ballon","Polyurethane 50mm"),
         ("Pression maxi service","8 bar"),("Rendement global","> 70% (conditions Dakar)"),
         ("Dimensions ballon","o520 x H 1 650 mm"),("Dimensions capteur","2 000x1 000x80 mm"),
         ("Fixation toiture","Structure alu 45°"),("Certifications","NF Solaire | Solar Keymark | CE")],
        "SENELEC Solaire | Tenesol Dakar | Solafrica SN",
        "Orienter les capteurs plein Sud avec inclinaison 15° (optimum latitude Dakar 14°N).")

    story.append(PageBreak())

    # 3. EQUIPEMENTS CVC
    story.append(Paragraph("3. EQUIPEMENTS CVC",st['h2']))
    story.append(HRFlowable(width="100%",thickness=0.5,color=GRIS_CLAIR))

    story += fiche("CV-01 Split Inverter Mural — Sejour 18 000 BTU/h",
        [("Puissance frigorifique","18 000 BTU/h (5.3 kW)"),("Puissance calorifique","20 000 BTU/h (5.9 kW)"),
         ("COP chauffage","4.0"),("EER refroidissement","3.6"),
         ("Classe energetique","A++ (refroidissement)"),("Fluide frigorigene","R32 — GWP 675"),
         ("Temperature ext. maxi","52°C (adapte Dakar)"),("Niveau sonore unite int.","< 35 dB(A)"),
         ("Alimentation","220V / 50Hz / 1Ph"),("Unité intérieure","1 060x295x230 mm"),
         ("Poids unité ext.","34 kg"),("Certifications","Eurovent | CE | CFC-free")],
        "LG Electronics SN | Daikin Dakar | Mitsubishi Electric WA | Samsung HVAC")

    story += fiche("CV-02 VMC Double Flux — 150 m³/h par logement",
        [("Debit nominal","150 m³/h (reglable 80-200 m³/h)"),("Efficacite enthalpique",">= 85%"),
         ("Puissance electrique","60 W (basse vitesse) / 120 W (haute)"),("Niveau sonore","< 28 dB(A) a 3m"),
         ("Filtration","Filtre G4 + filtre F7 (PM2.5)"),("Bypass ete","Automatique (T° ext < T° int)"),
         ("Regulation CO2","Sonde CO2 integree — modulation debit"),("Degivrage","Automatique"),
         ("Connexion BMS","Modbus RTU / 0-10V"),("Dimensions","600x480x250 mm"),
         ("Poids","22 kg"),("Certifications","NF Ventilation | CE | EN 13141-7")],
        "Aldes Dakar | Atlantic SN | Zehnder West Africa")

    story.append(PageBreak())

    # 4. DOMOTIQUE BMS
    story.append(Paragraph("4. EQUIPEMENTS DOMOTIQUE & BMS",st['h2']))
    story.append(HRFlowable(width="100%",thickness=0.5,color=GRIS_CLAIR))

    story += fiche("BM-01 Serveur BMS — Supervision Centralisee",
        [("Processeur","Intel Core i7 12eme gen — 3.6 GHz"),("Memoire RAM","32 GB DDR4 ECC"),
         ("Stockage","2 x 2 TB SSD NVMe (RAID 1)"),("OS","Linux Ubuntu Server 22.04 LTS"),
         ("Logiciel BMS","Niagara N4 / Siemens Desigo CC"),
         ("Protocoles supportes","BACnet/IP, KNX, Modbus, M-Bus, MQTT"),
         ("Connexions reseau","4 x GigE + 1 x 10GbE"),("Interfaces serie","4 x RS485, 2 x RS232"),
         ("Securite","VPN IPSec + pare-feu applicatif"),("Format","Rack 2U — 19"),
         ("Dimensions","482x88x500 mm"),("Certifications","IEC 62443 | ISO 27001 | CE")],
        "Siemens SN | Schneider EcoStruxure | Honeywell Building SN",
        "Prevoir contrat de maintenance annuel incluant mises a jour securite et sauvegarde distante.")

    story += fiche("BM-02 Interphone Video IP — Portier immeuble",
        [("Resolution camera","2 MP — 1080p Full HD"),("Vision nocturne","IR — 3 metres"),
         ("Angle de vision","140° horizontal"),("Audio","Bidirectionnel — annulation echo"),
         ("Protocole SIP","SIP 2.0 — compatible Asterisk"),
         ("App mobile","iOS 12+ / Android 8+ — notification push"),
         ("Deverrouillage","Code + badge NFC + app + reconnaissance faciale"),
         ("Alimentation","PoE 802.3af (15.4W)"),("Resistance","IK10 — IP65 — anti-vandalisme"),
         ("Dimensions facade","135x130x30 mm"),("Matiere","Aluminium anodise"),
         ("Certifications","CE | FCC | IP65 | IK10")],
        "2N Helios (Somfy SN) | Aiphone WA | Comelit Dakar")

    story.append(Spacer(1,6*mm))
    story.append(HRFlowable(width="100%",thickness=0.5,color=GRIS_CLAIR))
    story.append(Spacer(1,4*mm))
    story.append(Paragraph(
        "Fiches techniques a titre indicatif. Specifications definitives a valider par l'ingenieur fluides responsable. "
        "Prix et disponibilite a confirmer aupres des fournisseurs avant appel d'offres.",
        ParagraphStyle('disc',fontSize=7,textColor=GRIS)))

    doc.build(story,onFirstPage=_hf,onLaterPages=_hf)
