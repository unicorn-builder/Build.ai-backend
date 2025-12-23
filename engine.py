def calculer_fondations(projet):
    poids_total = 0
    for etage in projet.etages:
        for mur in etage.murs:
            # Volume x Densité béton (2500kg/m3)
            poids_total += (mur.longueur * mur.hauteur * mur.epaisseur) * 2500
    
    # Largeur semelle = Poids / Pression sol
    largeur = poids_total / (projet.sol.pression_admissible * 1000000)
    return round(largeur, 2)

def estimer_boq(projet):
    tarifs = {
        "Basic": {"m3_beton": 150, "point_elec": 50},
        "High-end": {"m3_beton": 250, "point_elec": 150},
        "Luxury": {"m3_beton": 500, "point_elec": 450}
    }
    t = tarifs.get(projet.gamme, tarifs["Basic"])
    # Logique simplifiée de calcul de coût ici...
    return {"total_estime": "Calculé selon gamme " + projet.gamme}
