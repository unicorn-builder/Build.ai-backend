"""
parse_plans.py — Extraction paramètres projet depuis PDF plans archi
Utilise pymupdf (fitz) + Claude API
"""
import os
import json
import re
import anthropic

def extraire_params_pdf(pdf_path: str) -> dict:
    """
    Extrait les paramètres structurels depuis un PDF de plans archi.
    Retourne un dict compatible ParamsProjet.
    """
    try:
        import fitz  # pymupdf
    except ImportError:
        return {"ok": False, "message": "pymupdf non installé"}

    # Extraction texte PDF
    try:
        doc = fitz.open(pdf_path)
        texte = ""
        for page in doc:
            texte += page.get_text()
        doc.close()
    except Exception as e:
        return {"ok": False, "message": f"Erreur lecture PDF : {e}"}

    if len(texte.strip()) < 50:
        return {"ok": False, "message": "PDF non vectoriel ou vide — texte non extractible"}

    # Limiter à 8000 chars pour l'API
    texte_tronque = texte[:8000]

    # Appel Claude API
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {"ok": False, "message": "ANTHROPIC_API_KEY non configurée"}

    try:
        client = anthropic.Anthropic(api_key=api_key)
        prompt = f"""Tu es un ingénieur structure expert. Analyse ce texte extrait de plans architecturaux et extrait les paramètres du projet.

TEXTE DES PLANS :
{texte_tronque}

Extrais ces paramètres et réponds UNIQUEMENT avec un JSON valide (pas de markdown, pas d'explication) :
{{
  "nom": "nom du projet ou bâtiment",
  "ville": "ville du projet",
  "nb_niveaux": nombre_entier_niveaux_total_incluant_rdc,
  "hauteur_etage_m": hauteur_en_metres_float,
  "surface_emprise_m2": surface_emprise_au_sol_m2_float,
  "portee_max_m": portee_maximale_entre_poteaux_m_float,
  "portee_min_m": portee_minimale_entre_poteaux_m_float,
  "nb_travees_x": nombre_entier_travees_direction_x,
  "nb_travees_y": nombre_entier_travees_direction_y,
  "classe_beton": "C25/30 ou C30/37 ou C35/45",
  "pression_sol_MPa": valeur_float
}}

Règles :
- Si une valeur n'est pas trouvée, utilise ces défauts : hauteur_etage=3.0, portee_max=6.0, portee_min=4.5, nb_travees_x=4, nb_travees_y=3, classe_beton=C30/37, pression_sol=0.15
- nb_niveaux inclut RDC + étages + éventuellement sous-sol
- surface_emprise = surface au sol du bâtiment (footprint), PAS la surface totale plancher
- Réponds uniquement avec le JSON, rien d'autre"""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = message.content[0].text.strip()
        # Nettoyer si markdown
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'^```\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)

        params = json.loads(raw)

        # Valider et compléter
        defaults = {
            "nom": "Projet",
            "ville": "Dakar",
            "nb_niveaux": 5,
            "hauteur_etage_m": 3.0,
            "surface_emprise_m2": 500.0,
            "portee_max_m": 6.0,
            "portee_min_m": 4.5,
            "nb_travees_x": 4,
            "nb_travees_y": 3,
            "classe_beton": "C30/37",
            "classe_acier": "HA500",
            "pression_sol_MPa": 0.15,
        }
        for k, v in defaults.items():
            if k not in params or params[k] is None:
                params[k] = v

        params["classe_acier"] = "HA500"
        params["ok"] = True
        params["source"] = "pdf_claude"
        return params

    except json.JSONDecodeError as e:
        return {"ok": False, "message": f"Réponse Claude non parsable : {e}"}
    except Exception as e:
        return {"ok": False, "message": f"Erreur Claude API : {e}"}
