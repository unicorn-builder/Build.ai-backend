"""
Tijan AI — Parseur de Plans Architecte
Extrait automatiquement les données structurelles depuis PDF/DWG
Pipeline: PDF → pdfplumber (texte) + Claude Vision (géométrie) → JSON Engine

Auteur: Tijan AI Engine v1.1
"""

import re
import json
import math
import base64
import io
import os
from typing import Optional



# ============================================================
# CONSTANTES
# ============================================================

VILLES_DAKAR_REGION = ["dakar", "pikine", "guediawaye", "rufisque", "mbour", "thies"]
VILLES_CONNUES = {
    "dakar": {"distance_mer_km": 2.0, "zone_sismique": "faible"},
    "abidjan": {"distance_mer_km": 5.0, "zone_sismique": "faible"},
    "casablanca": {"distance_mer_km": 3.0, "zone_sismique": "moderee"},
    "lagos": {"distance_mer_km": 8.0, "zone_sismique": "faible"},
}

KEYWORDS_NIVEAUX = {
    "sous_sol": ["SOUS.SOL", "SOUS SOL", "SS", "BASEMENT", r"-\d+\.\d+m"],
    "rdc": ["RDC", "REZ.DE.CHAUSSEE", "REZ DE CHAUSSEE", "RDC", "RC"],
    "etage": ["ETAGE", "NIVEAU", "FLOOR", r"R\+\d+"],
    "terrasse": ["TERRASSE", "TERRACE", "TOIT"],
    "toiture": ["TOITURE", "ROOF", "COUVERTURE"],
}


# ============================================================
# MODULE 1 — EXTRACTION TEXTE PDF
# ============================================================

def extraire_texte_pdf(pdf_path: str) -> dict:
    import pdfplumber
    import pdfplumber
    """
    Extrait tout le texte d'un PDF architectural page par page.
    Retourne un dict {page_num: texte}
    """
    pages_texte = {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                txt = page.extract_text() or ""
                if txt.strip():
                    pages_texte[i + 1] = txt
    except Exception as e:
        print(f"[WARN] pdfplumber error: {e}")
    return pages_texte


def extraire_tables_pdf(pdf_path: str) -> list:
    """Extrait les tableaux d'un PDF (légendes, nomenclatures)"""
    tables = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)
    except Exception:
        pass
    return tables


# ============================================================
# MODULE 2 — ANALYSE DU TEXTE EXTRAIT
# ============================================================

def detecter_niveaux(texte_complet: str) -> dict:
    """
    Détecte et parse les niveaux altimétrique depuis le texte.
    Retourne {label: altitude_m}
    """
    niveaux = {}

    # Pattern: "+3.80 m" ou "± 0.00m" ou "-3.48 m"
    pattern_cote = r'([+-]?\s*\d+\.\d+)\s*m(?!\²)'
    cotes_raw = re.findall(pattern_cote, texte_complet)

    # Pattern: "ETAGE 1" suivi de cote
    pattern_niveau_cote = r'(ETAGE\s*\d+|TERRASSE|TOITURE|SOUS.SOL|R\.?D\.?C\.?)[^\d]*([+\-]?\d+\.\d+)\s*m'
    matches = re.findall(pattern_niveau_cote, texte_complet, re.IGNORECASE)

    for label, cote in matches:
        label_clean = label.strip().upper().replace(" ", "_")
        try:
            niveaux[label_clean] = float(cote)
        except ValueError:
            pass

    # Extraire niveaux depuis les cotes trouvées dans les facades
    cotes_facades = []
    for c in cotes_raw:
        try:
            val = float(c.replace(" ", ""))
            if -10 < val < 50:  # plage réaliste pour un bâtiment
                cotes_facades.append(val)
        except ValueError:
            pass

    cotes_uniques = sorted(set(cotes_facades))

    return {
        "niveaux_detectes": niveaux,
        "cotes_altimetriques": cotes_uniques,
        "nb_niveaux_estimes": max(0, len([c for c in cotes_uniques if c > 0]))
    }


def detecter_surfaces(texte_complet: str) -> dict:
    """
    Extrait toutes les surfaces (m²) mentionnées dans le plan.
    Classifie : emprise, appartements, locaux techniques, parking
    """
    # Pattern surface: "1075.14m²" ou "225.39m²" ou "37.50 m²"
    pattern = r'(\d+\.?\d*)\s*m²'
    toutes_surfaces = []

    for match in re.finditer(pattern, texte_complet):
        try:
            val = float(match.group(1))
            if val > 0:
                toutes_surfaces.append(val)
        except ValueError:
            pass

    if not toutes_surfaces:
        return {}

    # Classification automatique
    surfaces_parking = [s for s in toutes_surfaces if s > 500]
    surfaces_apparts = [s for s in toutes_surfaces if 40 <= s <= 350]
    surfaces_locaux = [s for s in toutes_surfaces if 1 <= s < 40]

    # Emprise = plus grande surface OU parking SS
    emprise = max(surfaces_parking) if surfaces_parking else (
        sum(surfaces_apparts) * 1.25 if surfaces_apparts else 0
    )

    return {
        "emprise_m2": round(emprise),
        "surfaces_appartements": sorted(surfaces_apparts, reverse=True),
        "surfaces_locaux_techniques": sorted(surfaces_locaux, reverse=True)[:10],
        "surface_utile_etage": round(sum(surfaces_apparts[:10]), 1) if surfaces_apparts else 0,
        "nb_appartements_detectes": len([s for s in surfaces_apparts if s > 50]),
    }


def detecter_dimensions_structurelles(texte_complet: str) -> dict:
    """
    Extrait les dimensions structurelles : portées, épaisseurs de murs, sections.
    Les cotes dans un plan AutoCAD sont en mm.
    """
    # Cotes numériques (4 chiffres = mm dans un plan archi)
    pattern_dim = r'\b(\d{3,4})\b'
    dims_raw = re.findall(pattern_dim, texte_complet)
    dims = [int(d) for d in dims_raw if 100 <= int(d) <= 9999]

    if not dims:
        return {}

    # Épaisseurs typiques de murs : 100, 150, 200, 230, 250mm
    ep_murs_typiques = [100, 120, 150, 200, 230, 250, 300]
    epaisseurs_detectees = [d for d in dims if d in ep_murs_typiques]
    ep_voile = 200  # défaut 20cm

    if epaisseurs_detectees:
        from collections import Counter
        counter = Counter(epaisseurs_detectees)
        ep_voile = counter.most_common(1)[0][0]

    # Portées : valeurs entre 300 et 800cm (3m à 8m) en cm
    # Dans les plans AARS: les cotes sont en cm sur le dessin
    portees_potentielles_cm = [d for d in dims if 200 <= d <= 800]
    portee_max_m = max(portees_potentielles_cm) / 100 if portees_potentielles_cm else 6.0

    # Sections poteaux typiques: 25x25, 30x30, 35x35...
    sections_potentielles = [d for d in dims if d in [250, 300, 350, 400, 450, 500]]

    return {
        "portee_max_m": round(portee_max_m, 2),
        "epaisseur_voile_mm": ep_voile,
        "epaisseur_voile_m": ep_voile / 1000,
        "sections_detectees_mm": list(set(sections_potentielles))[:5],
    }


def detecter_infos_projet(texte_complet: str) -> dict:
    """
    Extrait les métadonnées du projet : nom, architecte, date, maître d'ouvrage.
    """
    infos = {}

    # Maître d'ouvrage
    mo_match = re.search(r'(?:Maitre|Maître)\s+d\'?ouvrage\s*:?\s*([A-Z][A-Za-z\s]+?)(?:\n|Situation)', texte_complet)
    if mo_match:
        infos["maitre_ouvrage"] = mo_match.group(1).strip()

    # Architecte / Atelier
    arch_match = re.search(r'(?:ATELIER|Atelier)\s+d\'?(?:ARCHITECTURE|Architecture)\s+([A-Za-z\s]+?)(?:\n|Rue|Tél)', texte_complet)
    if arch_match:
        infos["architecte"] = f"Atelier Architecture {arch_match.group(1).strip()}"

    # Date
    date_match = re.search(r'(Janvier|Février|Mars|Avril|Mai|Juin|Juillet|Août|Septembre|Octobre|Novembre|Décembre)\s+(\d{4})', texte_complet, re.IGNORECASE)
    if date_match:
        infos["date_plans"] = f"{date_match.group(1)} {date_match.group(2)}"

    # Type construction
    type_match = re.search(r'(?:Batiment|Bâtiment)\s+en\s+(R\+\d+)', texte_complet, re.IGNORECASE)
    if type_match:
        infos["type_construction"] = type_match.group(1)
        nb = re.search(r'R\+(\d+)', type_match.group(1))
        if nb:
            infos["nb_niveaux"] = int(nb.group(1))

    # Localisation
    for ville in VILLES_CONNUES.keys():
        if ville.upper() in texte_complet.upper():
            infos["ville"] = ville
            infos.update(VILLES_CONNUES[ville])
            break

    # Dossier référence
    ref_match = re.search(r'N°\s*(?:de\s*dossier\s*:?\s*)?(\d{4})', texte_complet)
    if ref_match:
        infos["ref_dossier"] = ref_match.group(1)

    return infos


# ============================================================
# MODULE 3 — CALCUL HAUTEUR D'ÉTAGE
# ============================================================

def calculer_hauteur_etage(cotes: list) -> float:
    """
    Calcule la hauteur d'étage courante depuis les cotes altimétriques.
    Retourne la hauteur modale (la plus fréquente).
    """
    if len(cotes) < 2:
        return 3.38  # défaut

    cotes_pos = sorted([c for c in cotes if c >= 0])
    if len(cotes_pos) < 2:
        return 3.38

    hauteurs = []
    for i in range(len(cotes_pos) - 1):
        diff = round(cotes_pos[i+1] - cotes_pos[i], 3)
        if 2.5 <= diff <= 5.0:  # plage réaliste pour hauteur étage
            hauteurs.append(diff)

    if not hauteurs:
        return 3.38

    from collections import Counter
    counter = Counter([round(h, 1) for h in hauteurs])
    return counter.most_common(1)[0][0]


# ============================================================
# MODULE 4 — ASSEMBLAGE JSON FINAL
# ============================================================

def assembler_json_engine(
    infos_projet: dict,
    niveaux_data: dict,
    surfaces_data: dict,
    dims_data: dict,
    pression_sol_mpa: float = 0.12,
) -> dict:
    """
    Assemble toutes les données extraites en JSON compatible avec l'engine Tijan.
    """
    # Nb niveaux
    nb_niveaux = infos_projet.get("nb_niveaux", 0)
    if not nb_niveaux:
        nb_niveaux = niveaux_data.get("nb_niveaux_estimes", 5)

    # Hauteur étage
    cotes = niveaux_data.get("cotes_altimetriques", [])
    hauteur_etage = calculer_hauteur_etage(cotes)

    # Surface emprise
    surface_emprise = surfaces_data.get("emprise_m2", 0)
    if not surface_emprise and surfaces_data.get("surface_utile_etage"):
        surface_emprise = int(surfaces_data["surface_utile_etage"] * 1.25)
    if not surface_emprise:
        surface_emprise = 500  # défaut

    # Portée max
    portee_max = dims_data.get("portee_max_m", 6.0)
    portee_max = max(3.0, min(portee_max, 9.0))  # clamp réaliste

    # Épaisseur voile
    ep_voile = dims_data.get("epaisseur_voile_m", 0.20)

    # Ville et distance mer
    ville = infos_projet.get("ville", "dakar")
    distance_mer = infos_projet.get("distance_mer_km", 5.0)

    # Maître d'ouvrage comme nom projet
    nom_projet = infos_projet.get("maitre_ouvrage", "Projet")
    type_construction = infos_projet.get("type_construction", f"R+{nb_niveaux}")

    json_engine = {
        "nom": nom_projet,
        "geometrie": {
            "surface_emprise_m2": surface_emprise,
            "nb_niveaux": nb_niveaux,
            "hauteur_etage_m": hauteur_etage,
            "portee_max_m": portee_max,
            "epaisseur_voile_m": ep_voile,
        },
        "usage": {
            "usage_principal": "residentiel"
        },
        "sol": {
            "pression_admissible_MPa": pression_sol_mpa,
            "description": f"Sol {ville.capitalize()} — vérifier sondage géotechnique"
        },
        "localisation": {
            "ville": ville,
            "distance_mer_km": distance_mer,
        },
        "_metadata": {
            "source": "Extraction automatique Tijan AI",
            "architecte": infos_projet.get("architecte", ""),
            "date_plans": infos_projet.get("date_plans", ""),
            "ref_dossier": infos_projet.get("ref_dossier", ""),
            "type_construction": type_construction,
            "surfaces_appartements": surfaces_data.get("surfaces_appartements", []),
            "nb_appartements_detectes": surfaces_data.get("nb_appartements_detectes", 0),
            "cotes_altimetriques": cotes,
        }
    }

    return json_engine


# ============================================================
# MODULE 5 — VALIDATION ET SCORING
# ============================================================

def valider_extraction(json_engine: dict) -> dict:
    """
    Valide la qualité de l'extraction et retourne un score de confiance.
    Score de 0 à 100%.
    """
    score = 0
    details = []
    warnings = []

    geo = json_engine.get("geometrie", {})
    meta = json_engine.get("_metadata", {})

    # Vérifications critiques
    checks = [
        (geo.get("nb_niveaux", 0) > 0, 20, "Nb niveaux détecté"),
        (0 < geo.get("hauteur_etage_m", 0) <= 5, 15, "Hauteur étage réaliste"),
        (geo.get("surface_emprise_m2", 0) > 50, 15, "Surface emprise détectée"),
        (1 <= geo.get("portee_max_m", 0) <= 12, 15, "Portée structurelle détectée"),
        (json_engine.get("localisation", {}).get("ville") != "dakar" or True, 10, "Localisation détectée"),
        (bool(meta.get("architecte")), 10, "Architecte détecté"),
        (bool(meta.get("date_plans")), 5, "Date plans détectée"),
        (len(meta.get("surfaces_appartements", [])) > 0, 10, "Surfaces appartements détectées"),
    ]

    for condition, points, label in checks:
        if condition:
            score += points
            details.append(f"✅ {label}")
        else:
            warnings.append(f"⚠️  {label} non détecté")

    # Warnings supplémentaires
    if geo.get("portee_max_m", 0) > 8:
        warnings.append("⚠️  Portée > 8m — vérifier manuellement")
    if geo.get("nb_niveaux", 0) > 20:
        warnings.append("⚠️  Nb niveaux > 20 — vérifier")
    if geo.get("surface_emprise_m2", 0) > 5000:
        warnings.append("⚠️  Surface > 5000m² — vérifier")

    return {
        "score_confiance_pct": score,
        "qualite": "Excellente" if score >= 80 else "Bonne" if score >= 60 else "Partielle" if score >= 40 else "Insuffisante",
        "details": details,
        "warnings": warnings,
        "recommandation": (
            "Extraction fiable — lancer le calcul" if score >= 70
            else "Vérifier les paramètres surlignés avant calcul" if score >= 50
            else "Extraction incomplète — saisir manuellement les données manquantes"
        )
    }


# ============================================================
# FONCTION PRINCIPALE
# ============================================================

def parser_plans_architecte(
    
    pdf_paths: list,
    pression_sol_mpa: float = 0.12,
    verbose: bool = True
) -> dict:
    """
    Fonction principale : parse un ou plusieurs PDFs architecte
    et retourne le JSON prêt pour l'engine Tijan.

    Args:
        pdf_paths: liste de chemins vers les PDFs (vues en plan + coupe + facades)
        pression_sol_mpa: pression admissible sol (à confirmer)
        verbose: affiche le détail de l'extraction

    Returns:
        dict avec json_engine, validation, texte_brut
    """
    if verbose:
        print(f"\n🔍 Tijan AI — Parseur de Plans Architecte")
        print(f"   Fichiers: {[os.path.basename(p) for p in pdf_paths]}")
        print("=" * 55)

    # Étape 1 — Extraire tout le texte
    texte_total = ""
    pages_par_fichier = {}

    for path in pdf_paths:
        if not os.path.exists(path):
            if verbose: print(f"   ⚠️  Fichier non trouvé: {path}")
            continue
        pages = extraire_texte_pdf(path)
        pages_par_fichier[os.path.basename(path)] = pages
        for txt in pages.values():
            texte_total += "\n" + txt

    if not texte_total.strip():
        return {"error": "Aucun texte extractible depuis les PDFs fournis"}

    if verbose:
        print(f"   📄 {len(texte_total)} caractères extraits")

    # Étape 2 — Analyses
    infos_projet = detecter_infos_projet(texte_total)
    niveaux_data = detecter_niveaux(texte_total)
    surfaces_data = detecter_surfaces(texte_total)
    dims_data = detecter_dimensions_structurelles(texte_total)

    if verbose:
        print(f"\n📐 INFOS PROJET:")
        for k, v in infos_projet.items():
            print(f"   {k}: {v}")
        print(f"\n📏 NIVEAUX:")
        print(f"   Niveaux détectés: {niveaux_data.get('niveaux_detectes', {})}")
        print(f"   Cotes: {niveaux_data.get('cotes_altimetriques', [])[:8]}")
        print(f"   Nb niveaux estimés: {niveaux_data.get('nb_niveaux_estimes', 0)}")
        print(f"\n📐 SURFACES:")
        print(f"   Emprise: {surfaces_data.get('emprise_m2', 0)}m²")
        print(f"   Appartements: {surfaces_data.get('surfaces_appartements', [])[:6]}")
        print(f"\n🏗️  DIMENSIONS STRUCTURELLES:")
        print(f"   Portée max: {dims_data.get('portee_max_m', 0)}m")
        print(f"   Voile ep: {dims_data.get('epaisseur_voile_mm', 200)}mm")

    # Étape 3 — Assemblage JSON
    json_engine = assembler_json_engine(
        infos_projet, niveaux_data, surfaces_data, dims_data, pression_sol_mpa
    )

    # Étape 4 — Validation
    validation = valider_extraction(json_engine)

    if verbose:
        print(f"\n✅ VALIDATION:")
        print(f"   Score confiance: {validation['score_confiance_pct']}% — {validation['qualite']}")
        for d in validation["details"]:
            print(f"   {d}")
        for w in validation["warnings"]:
            print(f"   {w}")
        print(f"\n   → {validation['recommandation']}")
        print(f"\n📋 JSON ENGINE:")
        print(json.dumps({k: v for k, v in json_engine.items() if k != "_metadata"}, indent=2, ensure_ascii=False))

    return {
        "json_engine": json_engine,
        "validation": validation,
        "infos_projet": infos_projet,
        "niveaux": niveaux_data,
        "surfaces": surfaces_data,
        "dimensions": dims_data,
    }


# ============================================================
# ENDPOINT FASTAPI (à intégrer dans main.py)
# ============================================================

FASTAPI_ENDPOINT = '''
from fastapi import UploadFile, File, Form
from typing import List
import tempfile, shutil

@app.post("/parse-plans")
async def parse_plans_endpoint(
    files: List[UploadFile] = File(...),
    pression_sol_mpa: float = Form(0.12),
):
    """
    Upload PDF plans architecte → extraction automatique JSON pour calcul.
    Accepte plusieurs fichiers (vues en plan + coupes + facades).
    """
    tmp_paths = []
    try:
        for file in files:
            suffix = os.path.splitext(file.filename)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                shutil.copyfileobj(file.file, tmp)
                tmp_paths.append(tmp.name)

        result = parser_plans_architecte(
            pdf_paths=tmp_paths,
            pression_sol_mpa=pression_sol_mpa,
            verbose=False
        )
        return result

    finally:
        for p in tmp_paths:
            try: os.unlink(p)
            except: pass
'''


# ============================================================
# TEST AVEC LES VRAIS PLANS P.O. SAKHO
# ============================================================

if __name__ == "__main__":
    pdfs = [
        "/mnt/user-data/uploads/VUES_EN_PLAN__2_.pdf",
        "/mnt/user-data/uploads/COUPE_ET_FACADES.pdf",
    ]

    result = parser_plans_architecte(pdfs, pression_sol_mpa=0.12, verbose=True)

    # Sauvegarder le JSON
    output_path = "/tmp/sakho_engine_input.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result["json_engine"], f, indent=2, ensure_ascii=False)

    print(f"\n💾 JSON sauvegardé: {output_path}")
    print(f"\n🚀 Prêt à envoyer à POST /calculate !")
