"""
Tijan AI — Générateur Speckle 3D BIM
Envoie le modèle structurel sur Speckle et retourne une URL de visualisation.

Dépendances : specklepy>=2.17
"""

import os
from typing import Dict, Any

from specklepy.api.client import SpeckleClient
from specklepy.api.credentials import get_default_account, Account
from specklepy.transports.server import ServerTransport
from specklepy.api import operations
from specklepy.objects import Base
from specklepy.objects.geometry import (
    Box, Point, Vector, Interval, Plane,
    Line, Mesh
)
from specklepy.objects.other import RenderMaterial

# ── Constantes ────────────────────────────────────────────────────────────────
SPECKLE_SERVER = os.getenv("SPECKLE_SERVER_URL", "https://app.speckle.systems")
SPECKLE_TOKEN  = os.getenv("SPECKLE_TOKEN", "")
PROJECT_NAME   = "Tijan AI — Modèles Structurels"


# ── Matériaux visuels ─────────────────────────────────────────────────────────
def mat_beton() -> RenderMaterial:
    m = RenderMaterial()
    m.name = "Béton C30/37"
    m.diffuse = 0xFF8B9496   # gris béton ARGB
    m.opacity = 1.0
    return m

def mat_acier() -> RenderMaterial:
    m = RenderMaterial()
    m.name = "Acier HA"
    m.diffuse = 0xFFFF6600   # orange armature
    m.opacity = 1.0
    return m

def mat_dalle() -> RenderMaterial:
    m = RenderMaterial()
    m.name = "Dalle BA"
    m.diffuse = 0xFFB0BEC5
    m.opacity = 0.85
    return m

def mat_pieu() -> RenderMaterial:
    m = RenderMaterial()
    m.name = "Pieu foré"
    m.diffuse = 0xFF795548
    m.opacity = 1.0
    return m


# ── Géométrie utilitaire ──────────────────────────────────────────────────────
def make_box(x: float, y: float, z: float,
             dx: float, dy: float, dz: float) -> Box:
    """Crée un Box à partir d'un coin origine et de dimensions."""
    origin = Point(x=x + dx/2, y=y + dy/2, z=z + dz/2)
    plane = Plane(
        origin=origin,
        normal=Vector(x=0, y=0, z=1),
        xdir=Vector(x=1, y=0, z=0),
        ydir=Vector(x=0, y=1, z=0)
    )
    box = Box(
        basePlane=plane,
        xSize=Interval(start=-dx/2, end=dx/2),
        ySize=Interval(start=-dy/2, end=dy/2),
        zSize=Interval(start=-dz/2, end=dz/2),
        units="m"
    )
    return box


def make_cylinder_mesh(cx: float, cy: float, z_bot: float,
                       radius: float, height: float,
                       segments: int = 16) -> Mesh:
    """Cylindre approximé en mesh (pour pieux)."""
    import math
    vertices = []
    faces = []

    # Anneaux bas et haut
    for ring in [z_bot, z_bot + height]:
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            vertices += [cx + radius * math.cos(angle),
                         cy + radius * math.sin(angle),
                         ring]

    # Faces latérales
    for i in range(segments):
        i_next = (i + 1) % segments
        b0, b1 = i, i_next
        t0, t1 = i + segments, i_next + segments
        faces += [4, b0, b1, t1, t0]

    # Bouchons
    # Bas
    faces += [segments] + list(range(segments - 1, -1, -1))
    # Haut
    faces += [segments] + list(range(segments, 2 * segments))

    m = Mesh(vertices=vertices, faces=faces, units="m")
    return m


# ── Constructeurs d'objets Speckle ────────────────────────────────────────────

def build_poteau(x: float, y: float, z_bas: float,
                 section_b: float, section_h: float,
                 hauteur: float, niveau: str,
                 armatures: str, beton: str,
                 N_Ed: float, taux: float) -> Base:
    obj = Base(speckle_type="Objects.BuiltElements.Column")
    obj["displayValue"] = [make_box(
        x - section_b/2, y - section_h/2, z_bas,
        section_b, section_h, hauteur
    )]
    obj["renderMaterial"] = mat_beton()
    # Propriétés BIM cliquables
    obj["Niveau"]          = niveau
    obj["Section"]         = f"{int(section_b*100)}×{int(section_h*100)} cm"
    obj["Armatures"]       = armatures
    obj["Béton"]           = beton
    obj["N_Ed_kN"]         = round(N_Ed, 1)
    obj["Taux_armature_%"] = round(taux, 2)
    obj["Norme"]           = "EN 1992-1-1"
    obj["Générateur"]      = "Tijan AI Engine v2"
    obj.units = "m"
    return obj


def build_poutre(x1: float, y1: float, x2: float, y2: float,
                 z: float, largeur: float, hauteur: float,
                 armatures: str, etriers: str,
                 V_Ed: float, M_Ed: float) -> Base:
    dx = x2 - x1
    dy = y2 - y1
    longueur = (dx**2 + dy**2) ** 0.5

    obj = Base(speckle_type="Objects.BuiltElements.Beam")
    obj["displayValue"] = [make_box(
        min(x1, x2), min(y1, y2) - largeur/2, z - hauteur,
        longueur if dx != 0 else largeur,
        largeur if dx != 0 else longueur,
        hauteur
    )]
    obj["renderMaterial"] = mat_beton()
    obj["Section"]    = f"{int(largeur*100)}×{int(hauteur*100)} cm"
    obj["Armatures"]  = armatures
    obj["Étriers"]    = etriers
    obj["V_Ed_kN"]    = round(V_Ed, 1)
    obj["M_Ed_kNm"]   = round(M_Ed, 1)
    obj["Norme"]      = "EN 1992-1-1"
    obj["Générateur"] = "Tijan AI Engine v2"
    obj.units = "m"
    return obj


def build_dalle(x: float, y: float, z: float,
                largeur_x: float, largeur_y: float,
                epaisseur: float, niveau: str,
                ferraillage: str) -> Base:
    obj = Base(speckle_type="Objects.BuiltElements.Floor")
    obj["displayValue"] = [make_box(x, y, z - epaisseur,
                                     largeur_x, largeur_y, epaisseur)]
    obj["renderMaterial"] = mat_dalle()
    obj["Niveau"]      = niveau
    obj["Épaisseur"]   = f"{int(epaisseur*100)} cm"
    obj["Ferraillage"] = ferraillage
    obj["Norme"]       = "EN 1992-1-1"
    obj["Générateur"]  = "Tijan AI Engine v2"
    obj.units = "m"
    return obj


def build_pieu(cx: float, cy: float, z_tete: float,
               diametre: float, longueur: float,
               charge_kN: float) -> Base:
    obj = Base(speckle_type="Objects.BuiltElements.Pile")
    obj["displayValue"] = [make_cylinder_mesh(
        cx, cy, z_tete - longueur, diametre/2, longueur
    )]
    obj["renderMaterial"] = mat_pieu()
    obj["Diamètre_m"]  = diametre
    obj["Longueur_m"]  = longueur
    obj["Charge_kN"]   = round(charge_kN, 1)
    obj["Type"]        = "Pieu foré béton"
    obj["Béton"]       = "C25/30"
    obj["Générateur"]  = "Tijan AI Engine v2"
    obj.units = "m"
    return obj


# ── Assemblage du modèle complet ──────────────────────────────────────────────

def assembler_modele(resultats: Dict[str, Any], nom_projet: str) -> Base:
    """
    Construit l'arbre d'objets Speckle depuis les résultats du moteur Tijan.
    """
    geo = resultats.get("geometrie", {})
    nb_niveaux   = geo.get("nb_niveaux", 12)
    surface      = geo.get("surface_emprise_m2", 766)
    portee       = geo.get("portee_max_m", 6.0)
    h_etage      = geo.get("hauteur_etage_m", 3.0)
    localisation = resultats.get("localisation", {}).get("ville", "Afrique")

    elements     = resultats.get("elements_structurels", {})
    fondations   = resultats.get("fondations", {})
    score_edge   = resultats.get("score_edge", {})

    # Dimensions grille
    import math
    cote = math.sqrt(surface)
    nb_travees = max(2, int(cote / portee))
    lx = nb_travees * portee
    ly = nb_travees * portee

    # Sections depuis résultats moteur
    pot_data  = elements.get("poteaux", {})
    pout_data = elements.get("poutres", {})
    dall_data = elements.get("dalle", {})

    # Valeurs par défaut robustes
    section_b    = pot_data.get("section_cm", {}).get("b", 30) / 100
    section_h    = pot_data.get("section_cm", {}).get("h", 30) / 100
    armatures_p  = pot_data.get("armatures_long", "10HA20")
    poutre_b     = pout_data.get("section_cm", {}).get("b", 30) / 100
    poutre_h     = pout_data.get("section_cm", {}).get("h", 55) / 100
    armatures_po = pout_data.get("armatures_long", "12HA16")
    etriers      = pout_data.get("armatures_trans", "HA14/200")
    ep_dalle     = dall_data.get("epaisseur_cm", 22) / 100
    ferr_dalle   = dall_data.get("armatures", "HA12/150")

    # Fondations
    fond_type  = fondations.get("type", "pieux")
    d_pieu     = fondations.get("diametre_m", 0.8)
    l_pieu     = fondations.get("longueur_m", 12.0)

    # Racine du modèle
    modele = Base()
    modele["name"]        = nom_projet
    modele["Ville"]       = localisation
    modele["Niveaux"]     = nb_niveaux
    modele["Surface_m2"]  = surface
    modele["Norme"]       = "EN 1992-1-1 / Eurocodes"
    modele["Béton"]       = "C30/37 — XS1"
    modele["Score_Edge_Energie"]   = score_edge.get("energie", {}).get("total_pct", 0)
    modele["Score_Edge_Eau"]       = score_edge.get("eau", {}).get("total_pct", 0)
    modele["Score_Edge_Materiaux"] = score_edge.get("materiaux", {}).get("total_pct", 0)
    modele["Générateur"]  = "Tijan AI Engine v2"

    poteaux = []
    poutres = []
    dalles  = []
    pieux   = []

    xs = [i * portee for i in range(nb_travees + 1)]
    ys = [j * portee for j in range(nb_travees + 1)]

    # Facteur section : niveaux inférieurs plus costauds
    def get_section(niveau_idx):
        if niveau_idx < nb_niveaux // 2:
            return section_b, section_h, armatures_p
        else:
            b2 = max(0.25, section_b - 0.05)
            return b2, b2, "8HA16"

    # Poteaux et poutres niveau par niveau
    for n in range(nb_niveaux):
        z_bas = n * h_etage
        z_haut = (n + 1) * h_etage
        nom_niveau = "RDC" if n == 0 else f"N+{n}"
        sb, sh, arm_p = get_section(n)

        N_Ed_approx = (nb_niveaux - n) * surface * 0.012  # kN estimé
        taux_approx = 2.1 if n < nb_niveaux // 2 else 1.4

        # Poteaux
        for x in xs:
            for y in ys:
                poteaux.append(build_poteau(
                    x, y, z_bas, sb, sh, h_etage,
                    nom_niveau, arm_p, "C30/37",
                    N_Ed_approx, taux_approx
                ))

        # Poutres en X
        for y in ys:
            for i in range(len(xs) - 1):
                V_Ed = N_Ed_approx * 0.08
                M_Ed = V_Ed * portee / 4
                poutres.append(build_poutre(
                    xs[i], y, xs[i+1], y, z_haut,
                    poutre_b, poutre_h,
                    armatures_po, etriers, V_Ed, M_Ed
                ))

        # Poutres en Y
        for x in xs:
            for j in range(len(ys) - 1):
                V_Ed = N_Ed_approx * 0.08
                M_Ed = V_Ed * portee / 4
                poutres.append(build_poutre(
                    x, ys[j], x, ys[j+1], z_haut,
                    poutre_b, poutre_h,
                    armatures_po, etriers, V_Ed, M_Ed
                ))

        # Dalle
        if n > 0:
            dalles.append(build_dalle(
                0, 0, z_haut,
                lx, ly, ep_dalle,
                nom_niveau, ferr_dalle
            ))

    # Pieux sous chaque poteau (si fondations pieux)
    if "pieux" in fond_type.lower():
        charge_pieu = surface * nb_niveaux * 0.012 / (len(xs) * len(ys))
        for x in xs:
            for y in ys:
                pieux.append(build_pieu(
                    x, y, 0.0, d_pieu, l_pieu, charge_pieu
                ))

    modele["@poteaux"] = poteaux
    modele["@poutres"] = poutres
    modele["@dalles"]  = dalles
    modele["@pieux"]   = pieux

    return modele


# ── Envoi sur Speckle ─────────────────────────────────────────────────────────

def envoyer_sur_speckle(resultats: Dict[str, Any],
                         nom_projet: str,
                         token: str = None,
                         server_url: str = None) -> Dict[str, str]:
    """
    Envoie le modèle sur Speckle et retourne l'URL de visualisation.

    Returns:
        {
            "url": "https://app.speckle.systems/projects/.../models/...",
            "project_id": "...",
            "model_id": "...",
            "object_id": "..."
        }
    """
    _token  = token      or SPECKLE_TOKEN
    _server = server_url or SPECKLE_SERVER

    if not _token:
        raise ValueError("SPECKLE_TOKEN manquant — configurez la variable d'environnement")

    # Connexion
    client = SpeckleClient(host=_server)
    client.authenticate_with_token(_token)

    # Trouver ou créer le projet Tijan
    projects = client.project.get_all()
    project_id = None
    for p in (projects or []):
        if p.name == PROJECT_NAME:
            project_id = p.id
            break

    if not project_id:
        project = client.project.create(name=PROJECT_NAME,
                                         description="Modèles BIM générés par Tijan AI")
        project_id = project.id

    # Créer un model (branche) pour ce projet
    model_name = nom_projet
    models = client.model.get_models(project_id=project_id)
    model_id = None
    for m in (models.items if models else []):
        if m.name == model_name:
            model_id = m.id
            break

    if not model_id:
        model = client.model.create(name=model_name, project_id=project_id)
        model_id = model.id

    # Construire et envoyer le modèle
    modele = assembler_modele(resultats, nom_projet)

    transport = ServerTransport(client=client, stream_id=project_id)
    object_id = operations.send(base=modele, transports=[transport])

    # Créer une version (commit)
    client.version.create(
        object_id=object_id,
        project_id=project_id,
        model_id=model_id,
        message=f"Tijan AI — {nom_projet} — {resultats.get('geometrie', {}).get('nb_niveaux', '?')} niveaux"
    )

    url = f"{_server}/projects/{project_id}/models/{model_id}"

    return {
        "url": url,
        "project_id": project_id,
        "model_id": model_id,
        "object_id": object_id,
        "message": f"Modèle BIM envoyé avec succès — {len(modele['@poteaux'])} poteaux, {len(modele['@poutres'])} poutres, {len(modele['@dalles'])} dalles"
    }
