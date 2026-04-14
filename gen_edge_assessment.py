"""
gen_edge_assessment.py — EDGE Assessment PDF (format officiel IFC EDGE v3.0.0)
Tijan AI — produit un rapport calqué sur le layout de la plateforme app.edgebuildings.com

Données 100% issues du moteur engine_mep_v2 (rm.edge) + baselines pays + géométrie.
Aucun appel externe à la plateforme EDGE — calculs locaux indépendants.
"""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Table, TableStyle,
                                Spacer, PageBreak, HRFlowable)
from reportlab.lib.styles import ParagraphStyle
from tijan_theme import (BLEU, VERT, VERT_LIGHT, ORANGE, ORANGE_LT,
                         GRIS1, GRIS2, GRIS3,
                         ML, MR, CW, W, S, HeaderFooter, p, fmt_n, fmt_fcfa,
                         section_title, table_style, _current_lang)

# Alias EDGE/IFC navy = bleu Tijan
NAVY = BLEU

# Translation helper
def _t(fr_text, en_text):
    """Return FR or EN text based on current PDF language"""
    return en_text if _current_lang == 'en' else fr_text


# ══════════════════════════════════════════════════════════════
# TABLES DE RÉFÉRENCE EDGE v3.0.0
# ══════════════════════════════════════════════════════════════

# Climate data par ville (ASHRAE zone + temps mensuels max/min °C + lat + rainfall + elevation)
# Sources: Meteonorm, EDGE defaults IFC
CLIMAT_EDGE = {
    "dakar": {
        "ashrae": "2B", "lat": 14.7, "elev": 40, "rainfall": 644,
        "tmax": [30.3, 31.4, 31.4, 28.7, 29.6, 31.2, 32.6, 31.8, 32.9, 32.9, 34.6, 32.8],
        "tmin": [15.9, 15.9, 16.6, 17.1, 18.9, 21.2, 23.0, 23.1, 22.8, 22.9, 21.1, 18.1],
    },
    "abidjan": {
        "ashrae": "1A", "lat": 5.3, "elev": 18, "rainfall": 1847,
        "tmax": [31, 32, 32, 32, 31, 29, 28, 28, 28, 30, 31, 31],
        "tmin": [23, 24, 24, 24, 24, 23, 22, 22, 22, 23, 24, 24],
    },
    "casablanca": {
        "ashrae": "3B", "lat": 33.6, "elev": 27, "rainfall": 400,
        "tmax": [17, 18, 19, 20, 22, 24, 26, 27, 26, 24, 20, 18],
        "tmin": [8, 9, 10, 12, 15, 17, 19, 20, 18, 15, 12, 9],
    },
    "lagos": {
        "ashrae": "1A", "lat": 6.5, "elev": 41, "rainfall": 1532,
        "tmax": [33, 33, 33, 33, 32, 30, 28, 29, 30, 31, 33, 33],
        "tmin": [23, 24, 24, 24, 24, 23, 23, 23, 23, 23, 24, 24],
    },
    "accra": {
        "ashrae": "1A", "lat": 5.6, "elev": 61, "rainfall": 730,
        "tmax": [31, 31, 31, 31, 31, 29, 27, 27, 28, 30, 31, 31],
        "tmin": [23, 24, 24, 24, 24, 23, 23, 22, 23, 23, 24, 23],
    },
}

# Fuel costs + CO2 factors par pays (XOF per unit, kgCO2/kWh)
FUEL_DATA = {
    "Senegal": {
        "elec_xof_kwh": 108.5, "diesel_xof_lt": 356.95, "gaz_xof_kg": 338.04,
        "lpg_xof_kg": 338.04, "coal_xof_kg": 49.0, "fueloil_xof_lt": 184.7,
        "water_xof_kl": 586.85, "xof_usd": 605.0,
        "co2_elec": 0.66, "co2_diesel": 0.25, "co2_gaz": 0.18,
        "co2_lpg": 0.24, "co2_coal": 0.32, "co2_fueloil": 0.25,
    },
    "Cote d'Ivoire": {
        "elec_xof_kwh": 95.0, "diesel_xof_lt": 615.0, "gaz_xof_kg": 320.0,
        "lpg_xof_kg": 320.0, "coal_xof_kg": 49.0, "fueloil_xof_lt": 180.0,
        "water_xof_kl": 420.0, "xof_usd": 605.0,
        "co2_elec": 0.52, "co2_diesel": 0.25, "co2_gaz": 0.18,
        "co2_lpg": 0.24, "co2_coal": 0.32, "co2_fueloil": 0.25,
    },
    "Morocco": {
        "elec_xof_kwh": 78.0, "diesel_xof_lt": 650.0, "gaz_xof_kg": 250.0,
        "lpg_xof_kg": 250.0, "coal_xof_kg": 49.0, "fueloil_xof_lt": 180.0,
        "water_xof_kl": 420.0, "xof_usd": 605.0,
        "co2_elec": 0.71, "co2_diesel": 0.25, "co2_gaz": 0.18,
        "co2_lpg": 0.24, "co2_coal": 0.32, "co2_fueloil": 0.25,
    },
    "Nigeria": {
        "elec_xof_kwh": 50.0, "diesel_xof_lt": 450.0, "gaz_xof_kg": 200.0,
        "lpg_xof_kg": 200.0, "coal_xof_kg": 49.0, "fueloil_xof_lt": 170.0,
        "water_xof_kl": 300.0, "xof_usd": 605.0,
        "co2_elec": 0.43, "co2_diesel": 0.25, "co2_gaz": 0.18,
        "co2_lpg": 0.24, "co2_coal": 0.32, "co2_fueloil": 0.25,
    },
    "Ghana": {
        "elec_xof_kwh": 85.0, "diesel_xof_lt": 500.0, "gaz_xof_kg": 220.0,
        "lpg_xof_kg": 220.0, "coal_xof_kg": 49.0, "fueloil_xof_lt": 175.0,
        "water_xof_kl": 500.0, "xof_usd": 605.0,
        "co2_elec": 0.45, "co2_diesel": 0.25, "co2_gaz": 0.18,
        "co2_lpg": 0.24, "co2_coal": 0.32, "co2_fueloil": 0.25,
    },
}

MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


# ══════════════════════════════════════════════════════════════
# HEADER / FOOTER EDGE-STYLE
# ══════════════════════════════════════════════════════════════

class EdgeHeaderFooter:
    """Header EDGE v3.0.0: 'EDGE Assessment: v3.0.0' + 3 savings en haut à droite."""
    def __init__(self, project_name, subproject_name, savings_e, savings_w, savings_m):
        self.pn = project_name
        self.sp = subproject_name
        self.se = savings_e
        self.sw = savings_w
        self.sm = savings_m

    def __call__(self, canvas, doc):
        canvas.saveState()
        # Bandeau supérieur
        canvas.setFont('Helvetica-Bold', 14)
        canvas.setFillColor(NAVY)
        canvas.drawString(ML, A4[1] - 15*mm, "EDGE")
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(GRIS3)
        canvas.drawString(ML + 18*mm, A4[1] - 14*mm, "IFC — International Finance Corporation")
        canvas.drawString(ML + 18*mm, A4[1] - 17*mm, "Creating Markets, Creating Opportunities")
        # Titre à droite
        canvas.setFont('Helvetica-Bold', 12)
        canvas.setFillColor(NAVY)
        canvas.drawRightString(A4[0] - MR, A4[1] - 13*mm, "Apartments")
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawRightString(A4[0] - MR, A4[1] - 17*mm, "EDGE Assessment: v3.0.0")
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(GRIS3)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        canvas.drawRightString(A4[0] - MR, A4[1] - 20*mm, f"Downloaded date & time: {now}")
        # Trois savings
        e_color = colors.HexColor('#43A956') if self.se >= 20 else NAVY
        w_color = colors.HexColor('#43A956') if self.sw >= 20 else NAVY
        m_color = colors.HexColor('#43A956') if self.sm >= 20 else NAVY
        x = A4[0] - MR - 48*mm
        y = A4[1] - 25*mm
        canvas.setFont('Helvetica-Bold', 10)
        canvas.setFillColor(e_color)
        canvas.drawString(x, y, f"{self.se:.2f}%")
        canvas.setFillColor(GRIS3)
        canvas.drawString(x + 16*mm, y, "|")
        canvas.setFillColor(w_color)
        canvas.drawString(x + 19*mm, y, f"{self.sw:.2f}%")
        canvas.setFillColor(GRIS3)
        canvas.drawString(x + 35*mm, y, "|")
        canvas.setFillColor(m_color)
        canvas.drawString(x + 38*mm, y, f"{self.sm:.2f}%")
        # Project name à gauche
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(NAVY)
        canvas.drawString(ML, A4[1] - 23*mm, f"Project Name: {self.pn}")
        canvas.drawString(ML, A4[1] - 26*mm, f"Subproject Name: {self.sp}")
        # Footer
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(GRIS3)
        canvas.drawString(ML, 12*mm, "Created By: Tijan AI")
        canvas.drawString(ML, 9*mm, "Downloaded By: Tijan AI")
        canvas.drawCentredString(A4[0]/2, 12*mm,
                                 f"File Number: TJN{datetime.now().strftime('%y%m%d%H%M%S')}")
        canvas.drawCentredString(A4[0]/2, 9*mm,
                                 "Powered by Tijan AI — tijan.ai")
        canvas.drawRightString(A4[0] - MR, 12*mm, f"{doc.page:02d}")
        canvas.restoreState()


# ══════════════════════════════════════════════════════════════
# SECTION BUILDERS
# ══════════════════════════════════════════════════════════════

def _kv_row(label, value):
    """2-column label/value row used throughout EDGE PDF."""
    return [p(label, 'small'), p(str(value) if value is not None else '—', 'body')]


def _section_header(story, title):
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(f'<b>{title}</b>', S['sous_titre']))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS2, spaceAfter=2*mm))


def _project_details(story, rm, params, total_area):
    _section_header(story, "Project Details")
    nom = params.get('nom', rm.params.nom)
    ville = params.get('ville', rm.params.ville)
    pays = params.get('pays', 'Senegal')
    data = [
        [p("Project Name", 'small'), p(f"<b>{nom}</b>", 'body'),
         p("Address Line 1", 'small'), p(params.get('adresse', '—'), 'body')],
        [p("Number of Distinct Buildings", 'small'), p("1", 'body'),
         p("City", 'small'), p(ville, 'body')],
        [p("Number of EDGE Subproject(s)", 'small'), p("1", 'body'),
         p("Country", 'small'), p(pays, 'body')],
        [p("Total Project Floor Area (m²)", 'small'),
         p(f"<b>{fmt_n(total_area, 2)}</b>", 'body'),
         p("Project Number", 'small'),
         p(f"TJN{datetime.now().strftime('%y%m%d%H%M')}", 'body')],
        [p("Do you intend to certify?", 'small'), p("Yes", 'body'),
         p("Certification Stage", 'small'), p("Preliminary", 'body')],
    ]
    t = Table(data, colWidths=[CW*0.22, CW*0.28, CW*0.22, CW*0.28])
    t.setStyle(table_style(zebra=False))
    story.append(t)


def _subproject_details(story, rm, params):
    _section_header(story, "Subproject Details")
    nom = params.get('nom', rm.params.nom)
    ville = params.get('ville', rm.params.ville)
    pays = params.get('pays', 'Senegal')
    data = [
        [p("Subproject Name", 'small'), p(f"<b>{nom}</b>", 'body'),
         p("Building Name", 'small'), p(nom, 'body')],
        [p("Subproject Multiplier", 'small'), p("1", 'body'),
         p("Subproject Type", 'small'), p("New Building", 'body')],
        [p("Status", 'small'), p("Self-Review", 'body'),
         p("City", 'small'), p(ville, 'body')],
        [p("Primary Building Type", 'small'), p("Apartments", 'body'),
         p("Country", 'small'), p(pays, 'body')],
    ]
    t = Table(data, colWidths=[CW*0.22, CW*0.28, CW*0.22, CW*0.28])
    t.setStyle(table_style(zebra=False))
    story.append(t)


def _typologies_table(story, rm, params):
    """Multiple Typologies — utilise params['typologies'] si fourni, sinon type moyen."""
    _section_header(story, "Multiple Typologies")
    typos = params.get('typologies') or []
    nb_log = rm.nb_logements or 1
    total_area = rm.surf_batie_m2

    if not typos:
        # Fallback: un seul type moyen dérivé de la surface
        avg = total_area / nb_log if nb_log else 80
        typos = [{
            'name': 'Type Moyen', 'bedrooms': 3, 'area': round(avg, 1),
            'units': nb_log, 'occupancy': 4,
            'bedroom_m2': round(avg*0.35, 1), 'kitchen_m2': round(avg*0.10, 1),
            'dining_m2': round(avg*0.08, 1), 'living_m2': round(avg*0.15, 1),
            'toilet_m2': round(avg*0.08, 1), 'utility_m2': round(avg*0.04, 1),
            'balcony_m2': round(avg*0.08, 1), 'parking_m2': 12.5,
            'corridor_m2': round(avg*0.12, 1),
        }]

    # Page 1: dimensions principales
    hdr = [p(x, 'th') for x in
           ['#', 'Name', 'Bedrooms', 'Area (m²/U)', 'Similar Units',
            'Occupancy', 'Bedroom (m²)', 'Kitchen (m²)', 'Dining (m²)']]
    rows = [hdr]
    for i, t in enumerate(typos, 1):
        rows.append([p(str(i), 'td'), p(t.get('name', '—'), 'td'),
                     p(str(t.get('bedrooms', 0)), 'td'),
                     p(fmt_n(t.get('area', 0), 1), 'td'),
                     p(str(t.get('units', 0)), 'td'),
                     p(str(t.get('occupancy', 0)), 'td'),
                     p(fmt_n(t.get('bedroom_m2', 0), 1), 'td'),
                     p(fmt_n(t.get('kitchen_m2', 0), 1), 'td'),
                     p(fmt_n(t.get('dining_m2', 0), 1), 'td')])
    t1 = Table(rows, colWidths=[CW*0.05, CW*0.17] + [CW*0.11]*7, repeatRows=1)
    t1.setStyle(table_style())
    story.append(t1)

    # Page 2: autres pièces
    story.append(Spacer(1, 2*mm))
    hdr2 = [p(x, 'th') for x in
            ['#', 'Name', 'Living (m²/U)', 'Toilet (m²/U)', 'Utility (m²/U)',
             'Balcony (m²/U)', 'Parking (m²/U)', 'Corridor (m²/U)']]
    rows2 = [hdr2]
    for i, t in enumerate(typos, 1):
        rows2.append([p(str(i), 'td'), p(t.get('name', '—'), 'td'),
                      p(fmt_n(t.get('living_m2', 0), 1), 'td'),
                      p(fmt_n(t.get('toilet_m2', 0), 1), 'td'),
                      p(fmt_n(t.get('utility_m2', 0), 1), 'td'),
                      p(fmt_n(t.get('balcony_m2', 0), 1), 'td'),
                      p(fmt_n(t.get('parking_m2', 0), 1), 'td'),
                      p(fmt_n(t.get('corridor_m2', 0), 1), 'td')])
    t2 = Table(rows2, colWidths=[CW*0.05, CW*0.17] + [CW*0.13]*6, repeatRows=1)
    t2.setStyle(table_style())
    story.append(t2)


def _building_data(story, rm, params):
    _section_header(story, "Building Data")
    nb_log = rm.nb_logements or 0
    nb_niv = rm.params.nb_niveaux
    h_etage = getattr(rm.params, 'hauteur_etage_m', 3.0)
    roof = params.get('roof_area_m2', rm.params.surface_emprise_m2)
    cost = params.get('cost_construction_xof_m2', 380_000)
    sale = params.get('sale_value_xof_m2', 650_000)
    data = [
        [p("Total No. of Apartments", 'small'), p(f"<b>{nb_log}</b>", 'body'),
         p("Cost of Construction (XOF/m²)", 'small'), p(fmt_n(cost, 0), 'body')],
        [p("No. of Floors Above Grade", 'small'), p(str(nb_niv), 'body'),
         p("Estimated Sale Value (XOF/m²)", 'small'), p(fmt_n(sale, 0), 'body')],
        [p("No. of Floors Below Grade", 'small'),
         p(str(params.get('nb_sous_sols', 0)), 'body'),
         p("Floor-to-Floor Height (m)", 'small'), p(f"{h_etage:.2f}", 'body')],
        [p("Aggregate Roof Area (m²)", 'small'), p(fmt_n(roof, 1), 'body'),
         p("", 'small'), p("", 'body')],
    ]
    t = Table(data, colWidths=[CW*0.25, CW*0.25, CW*0.25, CW*0.25])
    t.setStyle(table_style(zebra=False))
    story.append(t)


def _area_and_loads(story, rm, params, total_area):
    _section_header(story, "Area and Loads Breakdown")
    ext_light = params.get('area_ext_light_m2', round(total_area*0.10, 0))
    ext_park = params.get('area_ext_park_m2', round(total_area*0.03, 0))
    data = [
        [p("Gross Internal Area (m²)", 'small'),
         p(f"<b>{fmt_n(total_area, 1)}</b>", 'body')],
        [p("Area with Exterior Lighting (m²)", 'small'), p(fmt_n(ext_light, 0), 'body')],
        [p("External Car Parking Area (m²)", 'small'), p(fmt_n(ext_park, 0), 'body')],
    ]
    t = Table(data, colWidths=[CW*0.50, CW*0.50])
    t.setStyle(table_style(zebra=False))
    story.append(t)

    # Water End Uses
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("<b>Water End Uses</b>", S['body']))
    water = {
        'irrigated_m2': params.get('irrigated_area_m2', 0),
        'pool_m2': params.get('pool_m2', 0),
        'car_wash': 'Yes' if params.get('car_wash', False) else 'No',
        'washing_clothes': 'Yes' if params.get('washing_clothes', True) else 'No',
        'process_water': 'Yes' if params.get('process_water', False) else 'No',
        'dishwasher': 'Yes' if params.get('dishwasher', False) else 'No',
        'pre_rinse': 'Yes' if params.get('pre_rinse', False) else 'No',
    }
    data2 = [
        [p("Irrigated Area (m²)", 'small'), p(fmt_n(water['irrigated_m2'], 0), 'body'),
         p("Swimming Pool (m²)", 'small'), p(fmt_n(water['pool_m2'], 0), 'body')],
        [p("Car Washing", 'small'), p(water['car_wash'], 'body'),
         p("Washing Clothes", 'small'), p(water['washing_clothes'], 'body')],
        [p("Process Water", 'small'), p(water['process_water'], 'body'),
         p("Dishwasher", 'small'), p(water['dishwasher'], 'body')],
        [p("Pre-Rinse Spray Valve", 'small'), p(water['pre_rinse'], 'body'),
         p("", 'small'), p("", 'body')],
    ]
    t2 = Table(data2, colWidths=[CW*0.22, CW*0.28, CW*0.22, CW*0.28])
    t2.setStyle(table_style(zebra=False))
    story.append(t2)


def _building_dimensions(story, rm, params):
    _section_header(story, "Building Dimensions")
    # 8 orientations (default EDGE = 12.5 m par côté)
    orients = params.get('orientations') or {
        'N':  {'len': 12.5, 'exposed_pct': 25},
        'NE': {'len': 12.5, 'exposed_pct': 0},
        'E':  {'len': 12.5, 'exposed_pct': 25},
        'SE': {'len': 12.5, 'exposed_pct': 0},
        'S':  {'len': 12.5, 'exposed_pct': 25},
        'SW': {'len': 12.5, 'exposed_pct': 0},
        'W':  {'len': 12.5, 'exposed_pct': 25},
        'NW': {'len': 12.5, 'exposed_pct': 0},
    }
    names = {'N': 'North', 'NE': 'North East', 'E': 'East', 'SE': 'South East',
             'S': 'South', 'SW': 'South West', 'W': 'West', 'NW': 'North West'}
    hdr = [p("Orientation", 'th'), p("Length (m)", 'th'),
           p("Façade Area Exposed to Outside Air (%)", 'th')]
    rows = [hdr]
    for k in ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']:
        o = orients[k]
        rows.append([p(names[k], 'td'), p(fmt_n(o['len'], 1), 'td'),
                     p(f"{o['exposed_pct']:.0f}", 'td')])
    t = Table(rows, colWidths=[CW*0.30, CW*0.30, CW*0.40], repeatRows=1)
    t.setStyle(table_style())
    story.append(t)


def _hvac_system(story, rm, params):
    _section_header(story, "Building HVAC System")
    has_ac = "Yes" if rm.cvc.nb_splits_sejour + rm.cvc.nb_splits_chambre > 0 else "No"
    data = [
        [p("Select Input Type", 'small'), p("Simplified Inputs", 'body'),
         p("District Cooling/Heating?", 'small'), p("None", 'body')],
        [p("Include AC system?", 'small'), p(has_ac, 'body'),
         p("Applicable Baseline", 'small'), p("EDGE", 'body')],
        [p("Include Space Heating?", 'small'), p("No", 'body'),
         p("", 'small'), p("", 'body')],
    ]
    t = Table(data, colWidths=[CW*0.25, CW*0.25, CW*0.25, CW*0.25])
    t.setStyle(table_style(zebra=False))
    story.append(t)


def _fuel_and_costs(story, rm, params):
    _section_header(story, "Fuel Usage")
    pays = params.get('pays', 'Senegal')
    f = FUEL_DATA.get(pays, FUEL_DATA['Senegal'])
    data = [
        [p("Hot Water", 'small'), p("Electricity", 'body'),
         p("Electricity (XOF/kWh)", 'small'), p(fmt_n(f['elec_xof_kwh'], 2), 'body')],
        [p("Space Heating", 'small'), p("Electricity", 'body'),
         p("Diesel (XOF/Lt)", 'small'), p(fmt_n(f['diesel_xof_lt'], 2), 'body')],
        [p("Generator", 'small'), p("Diesel", 'body'),
         p("Natural Gas (XOF/kg)", 'small'), p(fmt_n(f['gaz_xof_kg'], 2), 'body')],
        [p("% Gen. Using Diesel", 'small'), p("1.00%", 'body'),
         p("LPG (XOF/kg)", 'small'), p(fmt_n(f['lpg_xof_kg'], 2), 'body')],
        [p("Fuel Used for Cooking", 'small'), p("Electricity", 'body'),
         p("Water (XOF/KL)", 'small'), p(fmt_n(f['water_xof_kl'], 2), 'body')],
        [p("", 'small'), p("", 'body'),
         p("Conversion from USD (XOF/USD)", 'small'), p(fmt_n(f['xof_usd'], 0), 'body')],
    ]
    t = Table(data, colWidths=[CW*0.22, CW*0.28, CW*0.25, CW*0.25])
    t.setStyle(table_style(zebra=False))
    story.append(t)

    # CO2 emission factors
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("<b>CO₂ Emissions Factor (kgCO₂/kWh)</b>", S['body']))
    co2 = [
        [p("Electricity", 'small'), p(f"{f['co2_elec']:.2f}", 'body'),
         p("LPG", 'small'), p(f"{f['co2_lpg']:.2f}", 'body')],
        [p("Diesel", 'small'), p(f"{f['co2_diesel']:.2f}", 'body'),
         p("Coal", 'small'), p(f"{f['co2_coal']:.2f}", 'body')],
        [p("Natural Gas", 'small'), p(f"{f['co2_gaz']:.2f}", 'body'),
         p("Fuel Oil", 'small'), p(f"{f['co2_fueloil']:.2f}", 'body')],
    ]
    tc = Table(co2, colWidths=[CW*0.22, CW*0.28, CW*0.22, CW*0.28])
    tc.setStyle(table_style(zebra=False))
    story.append(tc)


def _climate_data(story, rm, params):
    _section_header(story, "Climate Data")
    ville = params.get('ville', rm.params.ville).lower().strip()
    c = CLIMAT_EDGE.get(ville, CLIMAT_EDGE['dakar'])
    data = [
        [p("Elevation (m)", 'small'), p(str(c['elev']), 'body'),
         p("Latitude (degrees)", 'small'), p(f"{c['lat']:.1f}", 'body')],
        [p("Rainfall (mm/year)", 'small'), p(str(c['rainfall']), 'body'),
         p("ASHRAE Climate Zone", 'small'), p(c['ashrae'], 'body')],
    ]
    t = Table(data, colWidths=[CW*0.25, CW*0.25, CW*0.25, CW*0.25])
    t.setStyle(table_style(zebra=False))
    story.append(t)

    # Temperatures mensuelles
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("<b>Temperature (°C) — Monthly Max / Min</b>", S['body']))
    hdr = [p("Month", 'th')] + [p(m, 'th') for m in MONTHS]
    row_max = [p("Max", 'td_b')] + [p(f"{v:.1f}", 'td') for v in c['tmax']]
    row_min = [p("Min", 'td_b')] + [p(f"{v:.1f}", 'td') for v in c['tmin']]
    t2 = Table([hdr, row_max, row_min],
               colWidths=[CW*0.10] + [CW*0.075]*12, repeatRows=1)
    t2.setStyle(table_style())
    story.append(t2)


def _edge_savings_summary(story, rm):
    """Page finale: résumé 3 piliers + mesures clés."""
    story.append(PageBreak())
    _section_header(story, "EDGE Savings Summary")
    e = rm.edge
    data = [
        [p(_t("Pilier", "Pillar"), 'th'), p("Baseline", 'th'),
         p(_t("Projet", "Project"), 'th'), p(_t("Économie", "Savings"), 'th'), p(_t("Statut", "Status"), 'th')],
        [p("Energy", 'td_b'),
         p(f"{e.base_energie_kwh_m2_an:.1f} kWh/m²/yr", 'td'),
         p(f"{e.projet_energie_kwh_m2_an:.1f} kWh/m²/yr", 'td'),
         p(f"<b>{e.economie_energie_pct:.2f}%</b>", 'td'),
         p("✓ Pass" if e.economie_energie_pct >= 20 else "⚠ Below", 'td')],
        [p("Water", 'td_b'),
         p(f"{e.base_eau_L_pers_j:.1f} L/pers/j", 'td'),
         p(f"{e.projet_eau_L_pers_j:.1f} L/pers/j", 'td'),
         p(f"<b>{e.economie_eau_pct:.2f}%</b>", 'td'),
         p("✓ Pass" if e.economie_eau_pct >= 20 else "⚠ Below", 'td')],
        [p("Materials", 'td_b'),
         p(f"{e.base_ei_kwh_m2:.0f} kWh/m²", 'td'),
         p(f"{e.projet_ei_kwh_m2:.0f} kWh/m²", 'td'),
         p(f"<b>{e.economie_materiaux_pct:.2f}%</b>", 'td'),
         p("✓ Pass" if e.economie_materiaux_pct >= 20 else "⚠ Below", 'td')],
    ]
    t = Table(data, colWidths=[CW*0.15, CW*0.22, CW*0.22, CW*0.18, CW*0.23],
              repeatRows=1)
    t.setStyle(table_style())
    story.append(t)

    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(f"<b>Certification:</b> {e.niveau_certification}", S['body']))
    methodology_text = _t(
        "Méthodologie: IFC EDGE v3 — calculs Tijan AI (locaux, indépendants de la plateforme EDGE).",
        "Methodology: IFC EDGE v3 — Tijan AI calculations (local, independent from EDGE platform)."
    )
    story.append(Paragraph(methodology_text, S['small']))


# ══════════════════════════════════════════════════════════════
# SECTIONS FUSIONNÉES DEPUIS gen_mep.generer_edge (Conformité EDGE)
# ══════════════════════════════════════════════════════════════

def _verdict_banner(story, rm):
    """Bandeau coloré CERTIFIABLE / NON CERTIFIABLE en tête de rapport."""
    e = rm.edge
    verdict_color = VERT if e.certifiable else ORANGE
    bg_color = VERT_LIGHT if e.certifiable else ORANGE_LT
    verdict_txt = (f'CERTIFIABLE — {e.niveau_certification}' if e.certifiable
                   else f'NON CERTIFIABLE — {e.niveau_certification}')
    style = ParagraphStyle('v', fontName='Helvetica-Bold', fontSize=11,
                           textColor=verdict_color)
    verd = Table([[Paragraph(f'RÉSULTAT : {verdict_txt}', style)]],
                 colWidths=[CW])
    verd.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_color),
        ('BOX', (0, 0), (-1, -1), 1.5, verdict_color),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(verd)
    if getattr(e, 'note_generale', None):
        story.append(Paragraph(e.note_generale, S['small']))
    story.append(Spacer(1, 3*mm))


def _scores_synthesis(story, rm):
    """Tableau synthèse des 3 piliers avec statut CONFORME / DÉFICIT."""
    e = rm.edge
    story += section_title('A', 'SYNTHÈSE DES SCORES EDGE')
    rows = [[p('PILIER', 'th'), p('SCORE PROJET', 'th'),
             p('SEUIL CIBLE', 'th'), p('STATUT', 'th')]]
    for label, val in [('Énergie', e.economie_energie_pct),
                       ('Eau', e.economie_eau_pct),
                       ('Matériaux', e.economie_materiaux_pct)]:
        ok = val >= 20
        statut = ('✓ CONFORME' if ok
                  else f'✗ DÉFICIT {20 - val:.1f}%')
        rows.append([
            p(label),
            p(f'{val:.1f}%', 'td_r'),
            p('20%', 'td_r'),
            p(statut, 'ok' if ok else 'nok'),
        ])
    t = Table(rows, colWidths=[CW*0.30, CW*0.20, CW*0.20, CW*0.30],
              repeatRows=1)
    t.setStyle(table_style(zebra=False))
    story.append(t)
    if getattr(e, 'methode_calcul', None):
        story.append(Paragraph(f'Méthode : {e.methode_calcul}', S['small']))
    story.append(Spacer(1, 3*mm))


def _measures_detail(story, rm):
    """Détail mesures par pilier avec gain %, statut, impact prix."""
    e = rm.edge
    piliers = [
        (_t('ÉNERGIE', 'ENERGY'),    _t('PILIER 1 — ÉNERGIE', 'PILLAR 1 — ENERGY'),
         getattr(e, 'mesures_energie', []),
         e.base_energie_kwh_m2_an, e.projet_energie_kwh_m2_an, 'kWh/m²/an'),
        (_t('EAU', 'WATER'),        _t('PILIER 2 — EAU', 'PILLAR 2 — WATER'),
         getattr(e, 'mesures_eau', []),
         e.base_eau_L_pers_j, e.projet_eau_L_pers_j, 'L/pers/j'),
        (_t('MATÉRIAUX', 'MATERIALS'),  _t('PILIER 3 — MATÉRIAUX', 'PILLAR 3 — MATERIALS'),
         getattr(e, 'mesures_materiaux', []),
         e.base_ei_kwh_m2, e.projet_ei_kwh_m2, 'kWh/m²'),
    ]
    for i, (key, titre, mesures, base, projet, unite) in enumerate(piliers):
        if i == 0:
            story.append(PageBreak())
        else:
            story.append(Spacer(1, 4*mm))
        story += section_title('', titre)
        baseline_label = _t("Référence bâtiment standard :", "Reference standard building:")
        project_label = _t("Projet :", "Project:")
        story.append(Paragraph(
            f'{baseline_label} {base:.0f} {unite} | '
            f'{project_label} {projet:.0f} {unite}',
            S['body']))
        story.append(Spacer(1, 2*mm))
        if not mesures:
            no_measures = _t('— Aucune mesure détaillée —', '— No detailed measures —')
            story.append(Paragraph(no_measures, S['small']))
            continue
        headers = [_t('MESURE', 'MEASURE'), _t('GAIN (%)', 'GAIN (%)'), _t('STATUT', 'STATUS'), _t('IMPACT PRIX', 'COST IMPACT')]
        m_data = [[p(h, 'th') for h in headers]]
        for m in mesures:
            gain = m.get('gain_pct', 0)
            statut = m.get('statut', '—')
            integre_fr = 'Intégré' in statut or 'standard' in statut
            integre_en = 'Integrated' in statut or 'standard' in statut
            est_integre = integre_en if _current_lang == 'en' else integre_fr
            m_data.append([
                p(m.get('mesure', '—')),
                p(f'+{gain}%', 'td_g_r' if est_integre else 'td_r'),
                p(statut,
                  'td_g' if est_integre
                  else 'td_o' if 'spécifier' in statut.lower()
                  else 'td'),
                p(m.get('impact_prix', '—'), 'small'),
            ])
        tm = Table(m_data, colWidths=[CW*0.32, CW*0.10, CW*0.28, CW*0.30],
                   repeatRows=1)
        tm.setStyle(table_style())
        story.append(tm)


def _plan_action(story, rm):
    """Action plan for optimization towards certification (if not certifiable)."""
    e = rm.edge
    if getattr(e, 'certifiable', True) or not getattr(e, 'plan_action', None):
        return
    story.append(PageBreak())
    plan_title = _t("PLAN D'ACTION — OPTIMISATION VERS CERTIFICATION", "ACTION PLAN — OPTIMIZATION FOR CERTIFICATION")
    story += section_title('B', plan_title)
    cost_label = _t('Coût total de mise en conformité estimé :', 'Estimated total compliance cost:')
    roi_label = _t('ROI estimé :', 'Estimated ROI:')
    story.append(Paragraph(
        f'{cost_label} '
        f'{fmt_fcfa(getattr(e, "cout_mise_conformite_fcfa", 0))} | '
        f'{roi_label} {getattr(e, "roi_ans", 0)} {_t("ans", "years")}',
        S['note']))
    story.append(Spacer(1, 2*mm))
    headers = [_t('PILIER', 'PILLAR'), _t('ACTION', 'ACTION'), _t('GAIN (%)', 'GAIN (%)'),
               _t('COÛT', 'COST'), _t('ROI', 'ROI'), _t('IMPACT', 'IMPACT')]
    pa_data = [[p(h, 'th') for h in headers]]
    for action in e.plan_action:
        cout = action.get('cout_fcfa', 0)
        roi = action.get('roi_ans', 0)
        pa_data.append([
            p(action.get('pilier', '—'), 'td_b'),
            p(action.get('action', '—')),
            p(f'+{action.get("gain_pct", 0):.1f}%', 'td_g_r'),
            p(fmt_fcfa(cout) if cout > 0 else '—', 'td_r'),
            p(f'{roi:.1f} ans' if roi > 0 else '—', 'td_r'),
            p(action.get('impact', '—'), 'small'),
        ])
    tpa = Table(pa_data,
                colWidths=[CW*w for w in [0.10, 0.30, 0.09, 0.13, 0.09, 0.29]],
                repeatRows=1)
    tpa.setStyle(table_style())
    story.append(tpa)
    story.append(Paragraph(
        '⚠ Simulation des modifications nécessaires et de leur impact '
        'sur le coût du projet pour atteindre la certification EDGE.',
        S['note']))


# ══════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════

def generer_edge_assessment(rm, params: dict) -> bytes:
    """
    Produit un PDF EDGE Assessment v3.0.0 officiel-like depuis rm (ResultatsMEP)
    + params (dict avec overrides optionnels: typologies, orientations, water end uses...).
    """
    buf = io.BytesIO()
    nom = params.get('nom', rm.params.nom)
    subproject_name = f"{nom} — {params.get('ville', rm.params.ville)}"
    hf = EdgeHeaderFooter(
        project_name=nom,
        subproject_name=subproject_name,
        savings_e=rm.edge.economie_energie_pct,
        savings_w=rm.edge.economie_eau_pct,
        savings_m=rm.edge.economie_materiaux_pct,
    )
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=ML, rightMargin=MR,
                            topMargin=32*mm, bottomMargin=18*mm)
    story = []
    total_area = rm.surf_batie_m2

    _verdict_banner(story, rm)
    _scores_synthesis(story, rm)
    _project_details(story, rm, params, total_area)
    _subproject_details(story, rm, params)
    story.append(PageBreak())
    _typologies_table(story, rm, params)
    story.append(PageBreak())
    _building_data(story, rm, params)
    _area_and_loads(story, rm, params, total_area)
    story.append(PageBreak())
    _building_dimensions(story, rm, params)
    _hvac_system(story, rm, params)
    story.append(PageBreak())
    _fuel_and_costs(story, rm, params)
    _climate_data(story, rm, params)
    _edge_savings_summary(story, rm)
    _measures_detail(story, rm)
    _plan_action(story, rm)

    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    return buf.getvalue()
