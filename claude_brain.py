"""
claude_brain.py — Cerveau intelligent Tijan AI
Intègre Claude API pour :
1. Analyse et commentaire des résultats structurels
2. Endpoint /refine — peaufinage d'outputs par prompt utilisateur
"""

import os
import json
import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_INGENIEUR = """Tu es un ingénieur structure senior spécialisé en béton armé (Eurocodes EC2/EC8), 
expert du marché de la construction en Afrique de l'Ouest (Sénégal, Côte d'Ivoire, Maroc, Nigeria).
Tu travailles pour Tijan AI, une plateforme d'automatisation BIM/structure/MEP.
Tes réponses sont toujours :
- Précises techniquement (normes EC2, EC8, BAEL si pertinent)
- Adaptées au marché sénégalais (prix FCFA, fournisseurs locaux, contraintes chantier)
- Concises et professionnelles — tu t'adresses à des ingénieurs et promoteurs
- En français
Tu ne génères JAMAIS de contenu hors du domaine ingénierie/construction."""


def analyser_resultats_calcul(params: dict, resultats: dict) -> dict:
    """
    Analyse les résultats du moteur Eurocodes et génère :
    - Un commentaire d'ingénieur
    - Des alertes si anomalies détectées
    - Des recommandations d'optimisation
    """
    prompt = f"""Analyse ces résultats de calcul structurel pour le projet {params.get('nom', 'sans nom')} :

PARAMÈTRES PROJET :
- Ville : {params.get('ville', 'Dakar')}
- Niveaux : {params.get('nb_niveaux', '?')} (R+{params.get('nb_niveaux', 1) - 1})
- Surface emprise : {params.get('surface_emprise_m2', '?')} m²
- Portée max : {params.get('portee_max_m', '?')} m
- Béton : {params.get('classe_beton', 'C30/37')}
- Acier : {params.get('classe_acier', 'HA500')}
- Pression sol : {params.get('pression_sol_MPa', '?')} MPa

RÉSULTATS MOTEUR :
Poteaux par niveau :
{json.dumps(resultats.get('poteaux', []), indent=2, ensure_ascii=False)}

Poutre type :
{json.dumps(resultats.get('poutre', {}), indent=2, ensure_ascii=False)}

Fondation :
{json.dumps(resultats.get('fondation', {}), indent=2, ensure_ascii=False)}

BOQ résumé :
{json.dumps(resultats.get('boq_resume', {}), indent=2, ensure_ascii=False)}

Génère une analyse structurée en JSON avec exactement ces champs :
{{
  "commentaire_global": "Appréciation générale du dimensionnement (2-3 phrases)",
  "alertes": ["liste d'alertes si anomalies (taux armature hors limites EC2, sections inhabituelles, ratio coût aberrant...)"],
  "points_forts": ["points positifs du dimensionnement"],
  "recommandations": ["suggestions d'optimisation concrètes"],
  "conformite_ec2": "Conforme / À vérifier / Non conforme",
  "note_ingenieur": "Appréciation synthétique en 1 phrase pour le rapport"
}}

Réponds UNIQUEMENT avec le JSON, sans markdown ni texte autour."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=SYSTEM_INGENIEUR,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()
    # Nettoyer si markdown présent
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        return {
            "commentaire_global": text[:500],
            "alertes": [],
            "points_forts": [],
            "recommandations": [],
            "conformite_ec2": "À vérifier",
            "note_ingenieur": "Analyse disponible."
        }


def raffiner_output(output_existant: dict, prompt_utilisateur: str, contexte_projet: dict) -> dict:
    """
    Permet à l'utilisateur de peaufiner un output via prompt naturel.
    Ex: "Augmente le ratio acier de 10%", "Adapte pour budget serré", etc.
    """
    prompt = f"""Un utilisateur de Tijan AI veut modifier un output structurel.

CONTEXTE PROJET :
{json.dumps(contexte_projet, indent=2, ensure_ascii=False)}

OUTPUT ACTUEL :
{json.dumps(output_existant, indent=2, ensure_ascii=False)}

DEMANDE UTILISATEUR :
"{prompt_utilisateur}"

Interprète la demande et génère un JSON avec :
{{
  "interpretation": "Ce que tu as compris de la demande",
  "modifications": {{
    "description": "Quelles modifications ont été appliquées",
    "parametres_ajustes": {{}},
    "impact_technique": "Impact sur la structure/coût",
    "impact_cout_fcfa": "Estimation de l'impact budgétaire"
  }},
  "output_modifie": {{...output avec les modifications appliquées...}},
  "avertissements": ["avertissements techniques si la modification sort des normes EC2"]
}}

Si la demande est techniquement impossible ou dangereuse, explique pourquoi dans "avertissements" et retourne l'output original.
Réponds UNIQUEMENT avec le JSON."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=SYSTEM_INGENIEUR,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    try:
        return {"ok": True, "resultat": json.loads(text)}
    except Exception:
        return {"ok": False, "message": "Erreur parsing réponse Claude", "brut": text[:500]}


def generer_synthese_projet(params: dict, resultats: dict) -> str:
    """
    Génère une synthèse narrative du projet pour le rapport PDF.
    """
    prompt = f"""Génère une synthèse narrative professionnelle (3-4 paragraphes) 
pour la note de calcul du projet {params.get('nom', 'sans nom')}.

Paramètres : {json.dumps(params, ensure_ascii=False)}
Résultats clés : béton {params.get('classe_beton')}, 
section RDC {resultats.get('poteaux', [{}])[0].get('section_mm', '?')}mm,
ratio coût {resultats.get('boq_resume', {}).get('ratio_FCFA_m2', '?')} FCFA/m².

La synthèse doit mentionner : contexte projet, partis structurels retenus, 
conformité Eurocodes, adéquation au marché sénégalais.
Ton professionnel, style rapport BET."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        system=SYSTEM_INGENIEUR,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text.strip()
