"""
Tijan AI — Générateur Speckle 3D BIM
Liste plate d'objets + referencedId — viewer compatible
"""
import os, json, math, hashlib, httpx
from typing import Dict, Any

SPECKLE_SERVER = os.getenv("SPECKLE_SERVER_URL", "https://app.speckle.systems")
SPECKLE_TOKEN  = os.getenv("SPECKLE_TOKEN", "")
PROJECT_ID     = "4cc31da4b3"

def md5(data: dict) -> str:
    content = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return hashlib.md5(content.encode()).hexdigest()

def gql(query, variables=None, token=None, server=None):
    _token  = token  or SPECKLE_TOKEN
    _server = server or SPECKLE_SERVER
    resp = httpx.post(f"{_server}/graphql",
        json={"query": query, "variables": variables or {}},
        headers={"Authorization": f"Bearer {_token}", "Content-Type": "application/json"},
        timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise Exception(f"GraphQL error: {data['errors']}")
    return data["data"]

def get_or_create_model(project_id, model_name, token, server):
    try:
        data = gql("query($p:String!){project(id:$p){models{items{id name}}}}",
                   {"p": project_id}, token=token, server=server)
        for m in data["project"]["models"]["items"]:
            if m["name"].lower() == model_name.lower():
                return m["id"]
    except Exception:
        pass
    try:
        data = gql("mutation($i:CreateModelInput!){modelMutations{create(input:$i){id}}}",
                   {"i": {"projectId": project_id, "name": model_name}}, token=token, server=server)
        return data["modelMutations"]["create"]["id"]
    except Exception as e:
        if "already exists" in str(e):
            data = gql("query($p:String!){project(id:$p){models{items{id name}}}}",
                       {"p": project_id}, token=token, server=server)
            for m in data["project"]["models"]["items"]:
                if m["name"].lower() == model_name.lower():
                    return m["id"]
        raise

def send_objects(project_id, objects, token, server):
    _token  = token  or SPECKLE_TOKEN
    _server = server or SPECKLE_SERVER
    # Envoyer en batches de 100 pour éviter les timeouts
    batch_size = 100
    for i in range(0, len(objects), batch_size):
        batch = objects[i:i+batch_size]
        data = json.dumps(batch).encode("utf-8")
        resp = httpx.post(f"{_server}/objects/{project_id}",
            files={f"batch{i}": (f"batch{i}.json", data, "application/json")},
            headers={"Authorization": f"Bearer {_token}"},
            timeout=120)
        resp.raise_for_status()
    return objects[0]["id"]

def create_version(project_id, model_id, object_id, message, token, server):
    data = gql("""mutation($i:CreateVersionInput!){versionMutations{create(input:$i){id}}}""",
        {"i": {"projectId": project_id, "modelId": model_id, "objectId": object_id,
               "message": message, "sourceApplication": "TijanAI"}},
        token=token, server=server)
    return data["versionMutations"]["create"]["id"]

def box(x, y, z, dx, dy, dz, counter):
    """Mesh simple 8 sommets — format plat Speckle."""
    x2,y2,z2 = x+dx, y+dy, z+dz
    verts = [x,y,z, x2,y,z, x2,y2,z, x,y2,z, x,y,z2, x2,y,z2, x2,y2,z2, x,y2,z2]
    faces = [4,0,1,2,3, 4,7,6,5,4, 4,0,4,5,1, 4,1,5,6,2, 4,2,6,7,3, 4,3,7,4,0]
    obj = {"speckle_type":"Objects.Geometry.Mesh",
           "vertices":verts,"faces":faces,"units":"m","_c":counter}
    oid = md5(obj)
    obj.pop("_c")
    obj["id"] = oid
    return obj

def assembler_objets(resultats: Dict[str, Any], nom_projet: str):
    geo     = resultats.get("geometrie", {})
    nb_niv  = geo.get("nb_niveaux", 12)
    surface = geo.get("surface_emprise_m2", 766)
    portee  = geo.get("portee_max_m", 6.0)
    h_et    = geo.get("hauteur_etage_m", 3.0)
    ville   = resultats.get("localisation", {}).get("ville", "Afrique")
    elts    = resultats.get("elements_structurels", {})
    fond    = resultats.get("fondations", {})
    edge    = resultats.get("score_edge", {})

    nb_trav = max(2, int(math.sqrt(surface) / portee))
    xs = [i * portee for i in range(nb_trav + 1)]
    ys = [j * portee for j in range(nb_trav + 1)]

    sb = elts.get("poteaux",{}).get("section_cm",{}).get("b",30)/100
    sh = elts.get("poteaux",{}).get("section_cm",{}).get("h",30)/100
    pb = elts.get("poutres",{}).get("section_cm",{}).get("b",30)/100
    ph = elts.get("poutres",{}).get("section_cm",{}).get("h",55)/100
    ep = elts.get("dalle",{}).get("epaisseur_cm",22)/100
    dp = fond.get("diametre_m", 0.8)
    lp = fond.get("longueur_m", 12.0)

    all_objects = []  # liste plate
    c = [0]

    def mk(speckle_type, props, bx):
        c[0] += 1
        mesh = box(*bx, c[0])
        all_objects.append(mesh)
        obj = {"speckle_type": speckle_type,
               "displayValue": [{"referencedId": mesh["id"], "speckle_type": "reference"}],
               **props, "_c": c[0]}
        oid = md5(obj)
        obj.pop("_c")
        obj["id"] = oid
        all_objects.append(obj)
        return oid

    poteau_refs, poutre_refs, dalle_refs, pieu_refs = [], [], [], []

    for n in range(nb_niv):
        z0 = n * h_et
        z1 = (n + 1) * h_et
        nom_n = "RDC" if n == 0 else f"N+{n}"
        sb_n = max(0.25, sb - (0.05 if n >= nb_niv // 2 else 0))

        for x in xs:
            for y in ys:
                oid = mk("Objects.BuiltElements.Column",
                    {"Niveau": nom_n, "Section": f"{int(sb_n*100)}x{int(sb_n*100)}cm",
                     "Armatures": elts.get("poteaux",{}).get("armatures_long","10HA20"),
                     "Beton": "C30/37 XS1", "Norme": "EN 1992-1-1"},
                    (x-sb_n/2, y-sb_n/2, z0, sb_n, sb_n, h_et))
                poteau_refs.append({"referencedId": oid, "speckle_type": "reference"})

        for y in ys:
            for i in range(len(xs)-1):
                x1, x2 = xs[i]+sb_n/2, xs[i+1]-sb_n/2
                oid = mk("Objects.BuiltElements.Beam",
                    {"Niveau": nom_n, "Section": f"{int(pb*100)}x{int(ph*100)}cm",
                     "Armatures": elts.get("poutres",{}).get("armatures_long","12HA16"),
                     "Norme": "EN 1992-1-1"},
                    (x1, y-pb/2, z1-ph, x2-x1, pb, ph))
                poutre_refs.append({"referencedId": oid, "speckle_type": "reference"})

        for x in xs:
            for j in range(len(ys)-1):
                y1, y2 = ys[j]+sh/2, ys[j+1]-sh/2
                oid = mk("Objects.BuiltElements.Beam",
                    {"Niveau": nom_n, "Section": f"{int(pb*100)}x{int(ph*100)}cm",
                     "Armatures": elts.get("poutres",{}).get("armatures_long","12HA16"),
                     "Norme": "EN 1992-1-1"},
                    (x-pb/2, y1, z1-ph, pb, y2-y1, ph))
                poutre_refs.append({"referencedId": oid, "speckle_type": "reference"})

        if n > 0:
            lx = ly = nb_trav * portee
            oid = mk("Objects.BuiltElements.Floor",
                {"Niveau": nom_n, "Epaisseur_cm": int(ep*100),
                 "Ferraillage": elts.get("dalle",{}).get("armatures","HA12/150"),
                 "Norme": "EN 1992-1-1"},
                (0, 0, z1-ep, lx, ly, ep))
            dalle_refs.append({"referencedId": oid, "speckle_type": "reference"})

    if "pieux" in fond.get("type","").lower():
        for x in xs:
            for y in ys:
                oid = mk("Objects.BuiltElements.Pile",
                    {"Diametre_m": dp, "Longueur_m": lp, "Type": "Pieu fore", "Beton": "C25/30"},
                    (x-dp/2, y-dp/2, -lp, dp, dp, lp))
                pieu_refs.append({"referencedId": oid, "speckle_type": "reference"})

    root = {"speckle_type": "Base", "name": nom_projet, "Ville": ville,
            "Niveaux": nb_niv, "Surface_m2": surface, "Norme": "EN 1992-1-1 / Eurocodes",
            "Beton": "C30/37 XS1",
            "Score_Edge_Energie": edge.get("energie",{}).get("total_pct",0),
            "Score_Edge_Eau":     edge.get("eau",{}).get("total_pct",0),
            "Score_Edge_Materiaux": edge.get("materiaux",{}).get("total_pct",0),
            "Generateur": "Tijan AI Engine v2",
            "totalChildrenCount": len(all_objects),
            "@poteaux": poteau_refs,
            "@poutres": poutre_refs,
            "@dalles":  dalle_refs,
            "@pieux":   pieu_refs}
    root["id"] = md5({"name": nom_projet, "nb_niv": nb_niv, "surface": surface})
    return [root] + all_objects

def envoyer_sur_speckle(resultats, nom_projet, token=None, server_url=None):
    _token  = token      or SPECKLE_TOKEN
    _server = server_url or SPECKLE_SERVER
    if not _token:
        raise ValueError("SPECKLE_TOKEN manquant")

    project_id = PROJECT_ID
    model_id   = get_or_create_model(project_id, nom_projet, _token, _server)
    objects    = assembler_objets(resultats, nom_projet)
    object_id  = send_objects(project_id, objects, _token, _server)

    nb_niv = resultats.get("geometrie",{}).get("nb_niveaux","?")
    ville  = resultats.get("localisation",{}).get("ville","")
    create_version(project_id, model_id, object_id,
                   f"Tijan AI — {nom_projet} — R+{nb_niv} {ville}", _token, _server)

    url = f"{_server}/projects/{project_id}/models/{model_id}"
    nb_col  = sum(1 for o in objects if "Column" in o.get("speckle_type",""))
    nb_beam = sum(1 for o in objects if "Beam"   in o.get("speckle_type",""))
    nb_fl   = sum(1 for o in objects if "Floor"  in o.get("speckle_type",""))

    return {"url": url, "project_id": project_id, "model_id": model_id,
            "object_id": object_id,
            "message": f"Modele BIM envoye — {nb_col} poteaux, {nb_beam} poutres, {nb_fl} dalles",
            "nb_objets": len(objects)}
