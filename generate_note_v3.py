"""
generate_note_v3.py — Wrapper note de calcul v3
Utilise le vrai generate_pdf.py via l'adaptateur engine_structural.py
"""
import os
import tempfile
from engine_structural import adapter_v3_vers_anciens


def generer_note(resultats_v3, buf, params_dict: dict = None):
    """
    Génère la note de calcul PDF complète (vrai generate_pdf.py)
    depuis les résultats du moteur v3.
    
    Args:
        resultats_v3: ResultatsCalcul du moteur v3
        buf: BytesIO buffer pour écrire le PDF
        params_dict: dict des paramètres projet (optionnel, utilise valeurs par défaut)
    """
    if params_dict is None:
        params_dict = {}

    # Adapter les types
    projet, note = adapter_v3_vers_anciens(params_dict, resultats_v3)

    # Générer dans un fichier temporaire puis lire dans le buffer
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp_path = tmp.name

    try:
        from generate_pdf import generer_pdf
        generer_pdf(
            resultat=note,
            projet=projet,
            output_path=tmp_path,
            ingenieur="À compléter par l'ingénieur responsable",
        )
        with open(tmp_path, "rb") as f:
            buf.write(f.read())
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
