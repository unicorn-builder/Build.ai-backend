"""
parse_plans.py v3.0 — Tijan AI
Parser de plans architecturaux : PDF vectoriels, scannés, images.
Stack : pymupdf (fitz) + Claude API (Haiku texte / Sonnet vision).
Multi-fichiers. Extraction maximale. Zéro formulaire utilisateur.
"""

import re
import json
import os
import base64
import tempfile
import gc
from pathlib import Path
from typing import Optional, List

import httpx
from fastapi import UploadFile, HTTPException

# ── CONSTANTES ────────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Seuil vectoriel : si une page a plus de 200 chars, le PDF est vectoriel
SEUIL_VECTORIEL = 200

# Résolution rendu image : 1.5x = bon compromis qualité/mémoire
RESOLUTION = 1.5

# Nb max de pages à envoyer en vision (pour éviter timeout)
MAX_PAGES_VISION = 4

# ── SYSTEM PROMPT CLAUDE ──────────────────────────────────────────────────────

SYSTEM_PROMPT = """Tu es un ingénieur structure senior spécialisé dans les projets africains (Sénégal, Côte d'Ivoire, Maroc, Nigeria).
Tu lis des plans architecturaux et en extrais tous les paramètres nécessaires au calcul structurel Eurocodes.
Réponds UNIQUEMENT en JSON valide, sans markdown, sans backticks, sans commentaires.

Format de réponse obligatoire :
{
  "projet": {
    "nom": "string",
    "reference": "string",
    "architecte": "string",
    "maitre_ouvrage": "string",
    "date": "string",
    "phase": "APS|APD|PRO|EXE"
  },
  "localisation": {
    "ville": "string (dakar|abidjan|casablanca|lagos|autre)",
    "pays": "string",
    "adresse": "string",
    "distance_mer_km": float,
    "zone_sismique": "string (Z1|Z2|Z3|Z4)"
  },
  "geometrie": {
    "nb_niveaux_total": integer,
    "nb_niveaux_habitables": integer,
    "description_niveaux": "string (ex: SS+RDC+R+7+Terrasse)",
    "surface_emprise_m2": float,
    "longueur_m": float,
    "largeur_m": float,
    "surface_totale_m2": float,
    "hauteur_totale_m": float,
    "hauteur_etage_m": float,
    "hauteur_rdc_m": float,
    "hauteur_ss_m": float
  },
  "trame_structurelle": {
    "portee_max_m": float,
    "portee_min_m": float,
    "portee_dominante_m": float,
    "nb_travees_x": integer,
    "nb_travees_y": integer,
    "nb_poteaux_estime": integer,
    "grille_reguliere": boolean,
    "description_trame": "string"
  },
  "usage": {
    "type_principal": "résidentiel|bureaux|commercial|mixte|industriel|hôtelier",
    "sous_type": "string (ex: appartements, villa, hôtel)",
    "nb_logements": integer,
    "charge_exploitation_knm2": float,
    "occupation_type": "A|B|C|D|E (EN1991)"
  },
  "enveloppe": {
    "type_facade": "string (maçonnerie|rideau|mixte)",
    "type_toiture": "terrasse|inclinée|mixte",
    "presence_balcons": boolean,
    "presence_loggias": boolean
  },
  "notes_parser": "string — observations importantes, ambiguïtés, éléments à vérifier",
  "confiance": "haute|moyenne|faible",
  "raison_confiance": "string"
}

Règles absolues :
1. Jamais null, jamais 0 sauf si vraiment zéro — donne une estimation d'ingénieur
2. confiance = haute si tu lis les valeurs directement sur le plan
3. confiance = moyenne si tu les déduis (cotations implicites, échelle, comptage)
4. confiance = faible si le document est illisible ou insuffisant
5. Pour Dakar : distance_mer_km ≈ 1.5, zone_sismique = Z2, charge_exp résidentiel = 1.5 kN/m²
6. Pour les portées : lis les cotations exactes. Si absentes, déduis de l'échelle du plan.
7. nb_poteaux_estime = (nb_travees_x + 1) × (nb_travees_y + 1) × nb_niveaux"""


# ── EXTRACTION PYMUPDF ────────────────────────────────────────────────────────

def extraire_contenu_pdf(pdf_bytes: bytes) -> dict:
    """
    Extrait texte + images depuis un PDF en mémoire.
    Retourne : est_vectoriel, texte_total, pages_images[]
    """
    import fitz  # lazy import — ne charge que si nécessaire

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages_texte = []
    pages_images = []
    total_chars = 0

    for i, page in enumerate(doc):
        # Extraction texte
        texte = page.get_text("text")
        total_chars += len(texte)
        pages_texte.append({"page": i + 1, "texte": texte})

        # Rendu image (toutes les pages pour vision)
        mat = fitz.Matrix(RESOLUTION, RESOLUTION)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("jpeg")
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        pages_images.append({
            "page": i + 1,
            "image_b64": img_b64,
            "width": pix.width,
            "height": pix.height
        })
        del pix  # libérer mémoire immédiatement

    doc.close()
    gc.collect()

    est_vectoriel = total_chars > (SEUIL_VECTORIEL * len(pages_texte))
    texte_total = "\n\n".join(
        f"=== PAGE {p['page']} ===\n{p['texte']}"
        for p in pages_texte
        if p['texte'].strip()
    )

    return {
        "est_vectoriel": est_vectoriel,
        "nb_pages": len(pages_texte),
        "texte_total": texte_total,
        "pages_images": pages_images,
        "total_chars": total_chars
    }


def convertir_image_en_extraction(img_bytes: bytes, filename: str) -> dict:
    """Pour les images (PNG/JPG) uploadées directement."""
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")
    ext = Path(filename).suffix.lower()
    media_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
    return {
        "est_vectoriel": False,
        "nb_pages": 1,
        "texte_total": "",
        "pages_images": [{"page": 1, "image_b64": img_b64, "media_type": media_type}],
        "total_chars": 0
    }


# ── APPELS CLAUDE API ─────────────────────────────────────────────────────────

def appeler_claude_texte(texte: str, contexte_additionnel: str = "") -> dict:
    """
    PDF vectoriel → Claude Haiku sur le texte extrait.
    Rapide (3-5s), peu coûteux.
    """
    prompt = f"""Voici le texte extrait d'un ou plusieurs plans architecturaux PDF.
Extrais tous les paramètres structurels avec précision maximale.

{f"Contexte additionnel : {contexte_additionnel}" if contexte_additionnel else ""}

TEXTE EXTRAIT :
{texte[:20000]}

Réponds en JSON uniquement."""

    response = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 2000,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=60.0
    )
    response.raise_for_status()
    raw = response.json()["content"][0]["text"].strip()
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)
    return json.loads(raw)


def appeler_claude_vision(pages_images: list, texte_complement: str = "") -> dict:
    """
    PDF scanné ou image → Claude Sonnet Vision sur les pages rendues.
    Analyse visuelle complète du plan.
    """
    # Sélectionner les meilleures pages (premières = plan masse/RDC, plus informatif)
    pages = pages_images[:MAX_PAGES_VISION]

    content = []
    for p in pages:
        media_type = p.get("media_type", "image/jpeg")
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": p["image_b64"]
            }
        })

    texte_prompt = f"Voici {len(pages)} page(s) de plans architecturaux."
    if texte_complement:
        texte_prompt += f"\n\nTexte partiel extrait (pour aide) :\n{texte_complement[:3000]}"
    texte_prompt += "\n\nExtrais tous les paramètres structurels. Réponds en JSON uniquement."

    content.append({"type": "text", "text": texte_prompt})

    response = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-sonnet-4-6",  # Sonnet pour vision — meilleur ratio qualité/coût
            "max_tokens": 2000,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": content}]
        },
        timeout=120.0
    )
    response.raise_for_status()
    raw = response.json()["content"][0]["text"].strip()
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)
    return json.loads(raw)


def appeler_claude_hybride(texte: str, pages_images: list) -> dict:
    """
    PDF semi-vectoriel (texte partiel + images) → Claude Sonnet avec les deux.
    Meilleure précision sur les plans partiellement extractibles.
    """
    pages = pages_images[:2]  # Max 2 images en mode hybride
    content = []

    for p in pages:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": p.get("media_type", "image/jpeg"),
                "data": p["image_b64"]
            }
        })

    content.append({
        "type": "text",
        "text": f"""Voici des plans architecturaux (image + texte extrait).
Le texte extrait complète ce que tu vois dans les images.

TEXTE EXTRAIT :
{texte[:8000]}

Combine les deux sources pour extraire les paramètres structurels.
Réponds en JSON uniquement."""
    })

    response = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 2000,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": content}]
        },
        timeout=120.0
    )
    response.raise_for_status()
    raw = response.json()["content"][0]["text"].strip()
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)
    return json.loads(raw)


# ── VALIDATION ET ENRICHISSEMENT ──────────────────────────────────────────────

PRESSIONS_SOL = {
    "dakar":       {"valeur": 0.15, "type": "Basalte côtier"},
    "abidjan":     {"valeur": 0.10, "type": "Sol latéritique"},
    "casablanca":  {"valeur": 0.18, "type": "Sol argileux compact"},
    "lagos":       {"valeur": 0.08, "type": "Sol argileux mou"},
    "accra":       {"valeur": 0.12, "type": "Sol latéritique"},
    "nairobi":     {"valeur": 0.14, "type": "Sol volcanique"},
    "default":     {"valeur": 0.12, "type": "Valeur conservative"},
}

EXPOSITION_MARINE = {
    "dakar": "XS1",      # Exposition marine < 2km
    "abidjan": "XS1",
    "lagos": "XS1",
    "casablanca": "XC3", # Moins exposé
    "default": "XC2",
}

CLASSES_BETON = {
    "XS1": "C30/37",  # Exposition marine
    "XS2": "C35/45",
    "XC2": "C25/30",
    "XC3": "C30/37",
    "default": "C30/37",
}


def valider_et_enrichir(donnees: dict, texte_brut: str = "") -> dict:
    """
    Valide toutes les données extraites.
    Enrichit avec les paramètres techniques dérivés (béton, acier, exposition).
    Ne laisse aucun champ vide.
    """
    geo = donnees.get("geometrie", {})
    loc = donnees.get("localisation", {})
    trame = donnees.get("trame_structurelle", {})
    usage = donnees.get("usage", {})
    projet = donnees.get("projet", {})

    # ── Géométrie ──
    if not geo.get("hauteur_etage_m") or geo["hauteur_etage_m"] < 2:
        geo["hauteur_etage_m"] = 3.0
    if not geo.get("hauteur_rdc_m"):
        geo["hauteur_rdc_m"] = geo["hauteur_etage_m"]
    if not geo.get("surface_emprise_m2") and geo.get("longueur_m") and geo.get("largeur_m"):
        geo["surface_emprise_m2"] = round(geo["longueur_m"] * geo["largeur_m"], 1)
    if not geo.get("surface_totale_m2") and geo.get("surface_emprise_m2"):
        nb = geo.get("nb_niveaux_total", 1)
        geo["surface_totale_m2"] = round(geo["surface_emprise_m2"] * nb * 0.85, 1)
    if not geo.get("hauteur_totale_m"):
        nb = geo.get("nb_niveaux_total", geo.get("nb_niveaux_habitables", 9))
        geo["hauteur_totale_m"] = round(nb * geo["hauteur_etage_m"], 1)

    # ── Trame ──
    if not trame.get("portee_dominante_m"):
        pmax = trame.get("portee_max_m", 6.0)
        pmin = trame.get("portee_min_m", 4.0)
        trame["portee_dominante_m"] = round((pmax + pmin) / 2, 1)
    if not trame.get("nb_poteaux_estime"):
        nx = trame.get("nb_travees_x", 11) + 1
        ny = trame.get("nb_travees_y", 10) + 1
        trame["nb_poteaux_estime"] = nx * ny

    # ── Localisation ──
    if not loc.get("ville"):
        for ville in ["dakar", "abidjan", "casablanca", "lagos", "accra", "nairobi"]:
            if ville in texte_brut.lower():
                loc["ville"] = ville
                break
        if not loc.get("ville"):
            loc["ville"] = "dakar"

    ville_key = loc.get("ville", "dakar").lower()

    if not loc.get("distance_mer_km"):
        loc["distance_mer_km"] = 1.5 if ville_key == "dakar" else 5.0

    if not loc.get("zone_sismique"):
        loc["zone_sismique"] = "Z2"

    # ── Usage ──
    if not usage.get("charge_exploitation_knm2"):
        charges = {"résidentiel": 1.5, "bureaux": 2.5, "commercial": 4.0, "hôtelier": 2.0}
        usage["charge_exploitation_knm2"] = charges.get(
            usage.get("type_principal", "résidentiel"), 1.5
        )
    if not usage.get("occupation_type"):
        types_occ = {"résidentiel": "A", "bureaux": "B", "commercial": "C"}
        usage["occupation_type"] = types_occ.get(usage.get("type_principal", "résidentiel"), "A")

    # ── Paramètres techniques dérivés (pour le moteur Eurocodes) ──
    classe_exp = EXPOSITION_MARINE.get(ville_key, EXPOSITION_MARINE["default"])
    classe_beton = CLASSES_BETON.get(classe_exp, "C30/37")
    sol_info = PRESSIONS_SOL.get(ville_key, PRESSIONS_SOL["default"])

    donnees["parametres_eurocodes"] = {
        "classe_exposition": classe_exp,
        "classe_beton": classe_beton,
        "classe_acier": "HA500B",
        "enrobage_mm": 30 if classe_exp.startswith("XS") else 25,
        "sol_pression_admissible_MPa": sol_info["valeur"],
        "sol_type": sol_info["type"],
        "sol_source": "valeur_typique_ville",
        "sol_note": "À confirmer avec rapport géotechnique",
        "categorie_seismique": "II",
        "coefficient_importance": 1.0,
    }

    donnees["geometrie"] = geo
    donnees["localisation"] = loc
    donnees["trame_structurelle"] = trame
    donnees["usage"] = usage
    donnees["projet"] = projet

    return donnees


def fusionner_extractions(extractions: list) -> dict:
    """
    Fusionne les données extraites de plusieurs fichiers.
    Priorité : le fichier avec le plus de chars (le plus informatif).
    Enrichit avec les données complémentaires des autres fichiers.
    """
    if len(extractions) == 1:
        return extractions[0]

    # Trier par richesse d'information (confiance haute > moyenne > faible)
    ordre = {"haute": 3, "moyenne": 2, "faible": 1}
    extractions_triees = sorted(
        extractions,
        key=lambda x: ordre.get(x.get("confiance", "faible"), 0),
        reverse=True
    )

    # Base = extraction la plus fiable
    base = extractions_triees[0]

    # Enrichir les champs manquants avec les autres extractions
    for autre in extractions_triees[1:]:
        for section in ["geometrie", "trame_structurelle", "localisation", "usage", "projet"]:
            if section in autre:
                if section not in base:
                    base[section] = autre[section]
                else:
                    for k, v in autre[section].items():
                        if not base[section].get(k) and v:
                            base[section][k] = v

    base["_sources_fusionnees"] = len(extractions)
    return base


# ── FONCTION PRINCIPALE ───────────────────────────────────────────────────────

async def parser_plans_architecturaux(
    fichiers: List[UploadFile],
    pression_sol_mpa: Optional[float] = None
) -> dict:
    """
    Endpoint principal : reçoit 1 à N fichiers (PDF ou images),
    extrait tous les paramètres structurels, retourne un dict complet.

    Routing intelligent :
    - PDF vectoriel (texte lisible) → Claude Haiku sur texte → rapide + précis
    - PDF semi-vectoriel (texte partiel) → Claude Sonnet hybride (texte + vision)
    - PDF scanné / image → Claude Sonnet Vision → analyse visuelle
    """
    if not ANTHROPIC_API_KEY:
        raise HTTPException(503, "ANTHROPIC_API_KEY manquante")

    if not fichiers:
        raise HTTPException(400, "Aucun fichier fourni")

    resultats = []

    for fichier in fichiers:
        contenu = await fichier.read()
        nom = fichier.filename or "fichier"
        ext = Path(nom).suffix.lower()

        try:
            if ext == ".pdf":
                extraction = extraire_contenu_pdf(contenu)
                nb_chars = extraction["total_chars"]
                nb_pages = extraction["nb_pages"]

                if extraction["est_vectoriel"]:
                    # Texte riche → Haiku (rapide)
                    donnees = appeler_claude_texte(extraction["texte_total"])
                elif nb_chars > 100:
                    # Texte partiel → hybride Sonnet
                    donnees = appeler_claude_hybride(
                        extraction["texte_total"],
                        extraction["pages_images"]
                    )
                else:
                    # Scan pur → Vision Sonnet
                    donnees = appeler_claude_vision(
                        extraction["pages_images"],
                        extraction["texte_total"]
                    )

            elif ext in [".png", ".jpg", ".jpeg"]:
                extraction = convertir_image_en_extraction(contenu, nom)
                donnees = appeler_claude_vision(extraction["pages_images"])

            else:
                continue  # Ignorer les formats non supportés

            # Validation + enrichissement
            donnees = valider_et_enrichir(donnees, extraction.get("texte_total", ""))
            donnees["_fichier_source"] = nom
            resultats.append(donnees)

        except json.JSONDecodeError as e:
            # Claude a retourné du JSON invalide — rare mais possible
            resultats.append({
                "confiance": "faible",
                "notes_parser": f"Erreur parsing JSON Claude: {str(e)}",
                "_fichier_source": nom,
                "_erreur": True
            })
        finally:
            gc.collect()

    if not resultats:
        raise HTTPException(422, "Aucun fichier traitable fourni (PDF, PNG ou JPG requis)")

    # Filtrer les erreurs si on a au moins un résultat valide
    resultats_valides = [r for r in resultats if not r.get("_erreur")]
    if not resultats_valides:
        raise HTTPException(422, "Impossible d'extraire les données des fichiers fournis")

    # Fusionner si plusieurs fichiers
    resultat_final = fusionner_extractions(resultats_valides)

    # Override sol si fourni manuellement
    if pression_sol_mpa:
        resultat_final["parametres_eurocodes"]["sol_pression_admissible_MPa"] = pression_sol_mpa
        resultat_final["parametres_eurocodes"]["sol_source"] = "fourni_par_utilisateur"
        resultat_final["parametres_eurocodes"].pop("sol_note", None)

    # Métadonnées finales
    resultat_final["_meta"] = {
        "nb_fichiers_traites": len(resultats_valides),
        "nb_fichiers_fournis": len(fichiers),
        "version_parser": "3.0-pymupdf-claude-multifichiers",
        "modeles_utilises": _detecter_modeles_utilises(resultats_valides)
    }

    return resultat_final


def _detecter_modeles_utilises(resultats: list) -> list:
    modeles = set()
    for r in resultats:
        conf = r.get("confiance", "")
        if conf == "haute":
            modeles.add("claude-haiku-4-5 (texte)")
        else:
            modeles.add("claude-sonnet-4-6 (vision)")
    return list(modeles)
