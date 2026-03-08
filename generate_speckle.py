"""
Tijan AI — Générateur Speckle 3D BIM
Utilise l'API GraphQL Speckle directement (pas de specklepy → pas de conflit pydantic).
"""

import os
import json
import math
import httpx
from typing import Dict, Any

SPECKLE_SERVER = os.getenv("SPECKLE_SERVER_URL", "https://app.speckle.systems")
SPECKLE_TOKEN  = os.getenv("SPECKLE_TOKEN", "")


def gql(query: str, variables: dict = None, token: str = None, server: str = None) -> dict:
    _token  = token  or SPECKLE_TOKEN
    _server = server or SPECKLE_SERVER
    resp = httpx.post(
        f"{_server}/graphql",
        json={"query": query, "variables": variables or {}},
        headers={"Authorization": f"Bearer {_token}", "Content-Type": "application/json"},
        timeout=30
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise Exception(f"GraphQL error: {data['errors']}")
    return data["data"]


def get_or_create_project(nom: str, token: str, server: str) -> str:
    # Chercher dans les projets existants
    data = gql("query { activeUser { projects { items { id name } } } }", token=token, server=server)
    for p in data["activeUser"]["projects"]["items"]:
        if p["name"] == "Tijan AI — Modeles Structurels":
            return p["id"]

    # Trouver le workspace ID
    data_ws = gql("query { activeUser { workspaces { items { id name slug } } } }", token=token, server=server)
    workspace_id = None
    for ws in data_ws["activeUser"]["workspaces"]["items"]:
        workspace_id = ws["id"]
        break  # prend le premier workspace

    # Créer le projet dans le workspace
    mutation = """
        mutation CreateProject($name: String!, $description: String, $workspaceId: String) {
            projectMutations { create(input: { name: $name, description: $description, workspaceId: $workspaceId }) { id } }
        }
    """
    data = gql(mutation, {
        "name": "Tijan AI — Modeles Structurels",
        "description": "Modeles BIM generes par Tijan AI Engine v2",
        "workspaceId": workspace_id
    }, token=token, server=server)
    return data["projectMutations"]["create"]["id"]



def get_or_create_model(project_id: str, model_name: str, token: str, server: str) -> str:
    data = gql("""
        query GetModels($projectId: String!) {
            project(id: $projectId) { models { items { id name } } }
        }
    """, {"projectId": project_id}, token=token, server=server)
    for m in data["project"]["models"]["items"]:
        if m["name"] == model_name:
            return m["id"]
    data = gql("""
        mutation CreateModel($projectId: String!, $name: String!) {
            modelMutations { create(input: { projectId: $projectId, name: $name }) { id } }
        }
    """, {"projectId": project_id, "name": model_name}, token=token, server=server)
    return data["modelMutations"]["create"]["id"]


def send_objects(project_id: str, objects: list, token: str, server: str) -> str:
    _token  = token  or SPECKLE_TOKEN
    _server = server or SPECKLE_SERVER
    lines = "\n".join(json.dumps(obj) for obj in objects)
    resp = httpx.post(
        f"{_server}/objects/{project_id}",
        content=lines.encode(),
        headers={"Authorization": f"Bearer {_token}", "Content-Type": "text/plain"},
        timeout=60
    )
    resp.raise_for_status()
    return objects[0]["id"]


def create_version(project_id: str, model_id: str, object_id: str, message: str, token: str, server: str) -> str:
    data = gql("""
        mutation CreateVersion($input: CreateVersionInput!) {
            versionMutations { create(input: $input) { id } }
        }
    """, {"input": {"projectId": project_id, "modelId": model_id, "objectId": object_id,
                    "message": message, "sourceApplication": "TijanAI"}},
        token=token, server=server)
    return data["versionMutations"]["create"]["id"]


def make_id(prefix: str, idx: int) -> str:
    return f"{prefix}_{idx:06d}"


def build_box_mesh(x, y, z, dx, dy, dz):
    x2, y2, z2 = x+dx, y+dy, z+dz
    verts = [x,y,z, x2,y,z, x2,y2,z, x,y2,z, x,y,z2, x2,y,z2, x2,y2,z2, x,y2,z2]
    faces = [4,0,1,2,3, 4,4,5,6,7, 4,0,1,5,4, 4,2,3,7,6, 4,0,3,7,4, 4,1,2,6,5]
    return {"speckle_type": "Objects.Geometry.Mesh", "vertices": verts, "faces": faces, "units": "m"}


def build_cylinder_mesh(cx, cy, z_bot, radius, height, segments=12):
    verts, faces = [], []
    for rz in [z_bot, z_bot+height]:
        for i in range(segments):
            a = 2*math.pi*i/segments
            verts += [cx+radius*math.cos(a), cy+radius*math.sin(a), rz]
    for i in range(segments):
        i2 = (i+1)%segments
        faces += [4, i, i2, i2+segments, i+segments]
    faces += [segments] + list(range(segments-1,-1,-1))
    faces += [segments] + list(range(segments, 2*segments))
    return {"speckle_type": "Objects.Geometry.Mesh", "vertices": verts, "faces": faces, "units": "m"}


def assembler_objets(resultats: Dict[str, Any], nom_projet: str) -> list:
    geo        = resultats.get("geometrie", {})
    nb_niv     = geo.get("nb_niveaux", 12)
    surface    = geo.get("surface_emprise_m2", 766)
    portee     = geo.get("portee_max_m", 6.0)
    h_etage    = geo.get("hauteur_etage_m", 3.0)
    ville      = resultats.get("localisation", {}).get("ville", "Afrique")
    elements   = resultats.get("elements_structurels", {})
    fondations = resultats.get("fondations", {})
    score_edge = resultats.get("score_edge", {})

    nb_trav = max(2, int(math.sqrt(surface) / portee))
    xs = [i*portee for i in range(nb_trav+1)]
    ys = [j*portee for j in range(nb_trav+1)]

    pot  = elements.get("poteaux", {})
    pout = elements.get("poutres", {})
    dall = elements.get("dalle", {})

    sb = pot.get("section_cm", {}).get("b", 30)/100
    sh = pot.get("section_cm", {}).get("h", 30)/100
    arm_p  = pot.get("armatures_long", "10HA20")
    pb = pout.get("section_cm", {}).get("b", 30)/100
    ph = pout.get("section_cm", {}).get("h", 55)/100
    arm_po = pout.get("armatures_long", "12HA16")
    etr    = pout.get("armatures_trans", "HA14/200")
    ep_d   = dall.get("epaisseur_cm", 22)/100
    fer_d  = dall.get("armatures", "HA12/150")

    fond_type = fondations.get("type", "pieux")
    d_pieu    = fondations.get("diametre_m", 0.8)
    l_pieu    = fondations.get("longueur_m", 12.0)

    all_objects, poteau_ids, poutre_ids, dalle_ids, pieu_ids = [], [], [], [], []
    c = [0]

    def nid(p):
        c[0] += 1
        return make_id(p, c[0])

    for n in range(nb_niv):
        z_bas  = n*h_etage
        z_haut = (n+1)*h_etage
        nom_n  = "RDC" if n==0 else f"N+{n}"
        sb_n = sh_n = max(0.25, sb-(0.05 if n >= nb_niv//2 else 0))
        arm_n = arm_p if n < nb_niv//2 else "8HA16"
        N_Ed = round((nb_niv-n)*surface*0.012, 1)
        taux = 2.1 if n < nb_niv//2 else 1.4

        for x in xs:
            for y in ys:
                oid = nid("col")
                all_objects.append({"id":oid,"speckle_type":"Objects.BuiltElements.Column",
                    "displayValue":[build_box_mesh(x-sb_n/2,y-sh_n/2,z_bas,sb_n,sh_n,h_etage)],
                    "Niveau":nom_n,"Section":f"{int(sb_n*100)}x{int(sh_n*100)}cm",
                    "Armatures":arm_n,"Beton":"C30/37 XS1","N_Ed_kN":N_Ed,"Taux_pct":taux,
                    "Norme":"EN 1992-1-1","Generateur":"Tijan AI"})
                poteau_ids.append(oid)

        for y in ys:
            for i in range(len(xs)-1):
                oid = nid("bm")
                x1,x2 = xs[i]+sb_n/2, xs[i+1]-sb_n/2
                all_objects.append({"id":oid,"speckle_type":"Objects.BuiltElements.Beam",
                    "displayValue":[build_box_mesh(x1,y-pb/2,z_haut-ph,x2-x1,pb,ph)],
                    "Niveau":nom_n,"Section":f"{int(pb*100)}x{int(ph*100)}cm",
                    "Armatures":arm_po,"Etriers":etr,"Norme":"EN 1992-1-1","Generateur":"Tijan AI"})
                poutre_ids.append(oid)

        for x in xs:
            for j in range(len(ys)-1):
                oid = nid("bm")
                y1,y2 = ys[j]+sh_n/2, ys[j+1]-sh_n/2
                all_objects.append({"id":oid,"speckle_type":"Objects.BuiltElements.Beam",
                    "displayValue":[build_box_mesh(x-pb/2,y1,z_haut-ph,pb,y2-y1,ph)],
                    "Niveau":nom_n,"Section":f"{int(pb*100)}x{int(ph*100)}cm",
                    "Armatures":arm_po,"Etriers":etr,"Norme":"EN 1992-1-1","Generateur":"Tijan AI"})
                poutre_ids.append(oid)

        if n > 0:
            oid = nid("floor")
            lx,ly = nb_trav*portee, nb_trav*portee
            all_objects.append({"id":oid,"speckle_type":"Objects.BuiltElements.Floor",
                "displayValue":[build_box_mesh(0,0,z_haut-ep_d,lx,ly,ep_d)],
                "Niveau":nom_n,"Epaisseur_cm":int(ep_d*100),"Ferraillage":fer_d,
                "Norme":"EN 1992-1-1","Generateur":"Tijan AI"})
            dalle_ids.append(oid)

    if "pieux" in fond_type.lower():
        charge = round(surface*nb_niv*0.012/(len(xs)*len(ys)),1)
        for x in xs:
            for y in ys:
                oid = nid("pile")
                all_objects.append({"id":oid,"speckle_type":"Objects.BuiltElements.Pile",
                    "displayValue":[build_cylinder_mesh(x,y,-l_pieu,d_pieu/2,l_pieu)],
                    "Diametre_m":d_pieu,"Longueur_m":l_pieu,"Charge_kN":charge,
                    "Type":"Pieu fore","Beton":"C25/30","Generateur":"Tijan AI"})
                pieu_ids.append(oid)

    root_id = make_id("root", 0)
    root = {"id":root_id,"speckle_type":"Base","name":nom_projet,"Ville":ville,
        "Niveaux":nb_niv,"Surface_m2":surface,"Norme":"EN 1992-1-1 / Eurocodes",
        "Beton":"C30/37 XS1",
        "Score_Edge_Energie":score_edge.get("energie",{}).get("total_pct",0),
        "Score_Edge_Eau":score_edge.get("eau",{}).get("total_pct",0),
        "Score_Edge_Materiaux":score_edge.get("materiaux",{}).get("total_pct",0),
        "Generateur":"Tijan AI Engine v2",
        "@poteaux":poteau_ids,"@poutres":poutre_ids,"@dalles":dalle_ids,"@pieux":pieu_ids}

    return [root] + all_objects


def envoyer_sur_speckle(resultats: Dict[str, Any], nom_projet: str,
                         token: str = None, server_url: str = None) -> Dict[str, str]:
    _token  = token      or SPECKLE_TOKEN
    _server = server_url or SPECKLE_SERVER
    if not _token:
        raise ValueError("SPECKLE_TOKEN manquant")

    project_id = get_or_create_project(nom_projet, _token, _server)
    model_id   = get_or_create_model(project_id, nom_projet, _token, _server)
    objects    = assembler_objets(resultats, nom_projet)
    object_id  = send_objects(project_id, objects, _token, _server)

    nb_niv = resultats.get("geometrie", {}).get("nb_niveaux", "?")
    ville  = resultats.get("localisation", {}).get("ville", "")
    create_version(project_id, model_id, object_id,
                   f"Tijan AI — {nom_projet} — R+{nb_niv} {ville}", _token, _server)

    url = f"{_server}/projects/{project_id}/models/{model_id}"
    nb_col  = sum(1 for o in objects if "Column" in o.get("speckle_type",""))
    nb_beam = sum(1 for o in objects if "Beam"   in o.get("speckle_type",""))
    nb_fl   = sum(1 for o in objects if "Floor"  in o.get("speckle_type",""))

    return {"url":url,"project_id":project_id,"model_id":model_id,"object_id":object_id,
            "message":f"Modèle BIM envoyé — {nb_col} poteaux, {nb_beam} poutres, {nb_fl} dalles",
            "nb_objets":len(objects)}
