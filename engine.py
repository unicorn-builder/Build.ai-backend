import os
import google.generativeai as genai
from supabase import create_client

# Configuration de Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# Configuration de Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

def calculer_fondations(projet):
    poids_total = 0
    for etage in projet.etages:
        for mur in etage.murs:
            poids_total += (mur.longueur * mur.hauteur * mur.epaisseur) * 2500
    largeur = poids_total / (projet.sol.pression_admissible * 1000000)
    return round(largeur, 2)

def recuperer_boq_supabase(gamme):
    # On va chercher les vrais équipements dans ta table catalogue
    response = supabase.table("catalogue").select("*").eq("gamme", gamme).execute()
    return response.data

def generer_synthese_ia(projet, fondations, boq):
    prompt = f"""
    Agis en ingénieur civil expert. 
    Projet : {projet.nom}
    Gamme : {projet.gamme}
    Résultat structure : Semelle de {fondations}m de large.
    Équipements prévus : {boq}
    
    Rédige une courte synthèse technique (3 paragraphes) expliquant la robustesse de la structure et la qualité des équipements choisis.
    """
    response = model.generate_content(prompt)
    return response.text
