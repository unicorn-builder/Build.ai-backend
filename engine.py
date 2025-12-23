import google.generativeai as genai
import os

def generer_note_technique(projet):
    # On configure l'IA
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"Agis en ingénieur. Pour un projet {projet.nom} en gamme {projet.gamme}, rédige une note de calcul courte pour les fondations et le choix du système CVC."
    response = model.generate_content(prompt)
    return response.text

def calculer_fondations(projet):
    poids_total = 0
    for etage in projet.etages:
        for mur in etage.murs:
            poids_total += (mur.longueur * mur.hauteur * mur.epaisseur) * 2500
    largeur = poids_total / (projet.sol.pression_admissible * 1000000)
    return round(largeur, 2)
