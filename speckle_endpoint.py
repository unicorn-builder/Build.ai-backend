# ── À AJOUTER dans main.py ───────────────────────────────────────────────────
# 1. Import en haut du fichier (avec les autres imports) :
#    from generate_speckle import envoyer_sur_speckle
#
# 2. Endpoint à ajouter après /generate-ifc :

class SpeckleRequest(BaseModel):
    resultats: dict
    nom_projet: str = "Projet Tijan AI"
    token: str = None          # optionnel : override du token serveur
    server_url: str = None     # optionnel : override du serveur

@app.post("/generate-speckle")
async def generate_speckle_endpoint(req: SpeckleRequest):
    """
    Envoie le modèle 3D BIM sur Speckle et retourne une URL de visualisation.
    Input  : résultats du /calculate + nom du projet
    Output : URL Speckle navigable en ligne (partager avec ingénieur/client)
    """
    try:
        result = envoyer_sur_speckle(
            resultats=req.resultats,
            nom_projet=req.nom_projet,
            token=req.token,
            server_url=req.server_url
        )
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
