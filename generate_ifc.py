"""
Tijan AI — Générateur IFC Structurel
Produit un fichier IFC 2x3 valide depuis les résultats du moteur Eurocodes.
Format ISO 16739 — ouvrable dans Revit, ArchiCAD, FreeCAD, Navisworks.
"""

import math
import uuid
import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


# ─────────────────────────────────────────────
# HELPERS IFC
# ─────────────────────────────────────────────

def new_guid() -> str:
    """Génère un GUID IFC valide (22 chars base64-like)."""
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$"
    raw = uuid.uuid4().int
    result = []
    for _ in range(22):
        result.append(chars[raw % 64])
        raw //= 64
    return "".join(result)


def ifc_timestamp() -> str:
    now = datetime.datetime.utcnow()
    return now.strftime("%Y-%m-%dT%H:%M:%S")


# ─────────────────────────────────────────────
# GÉNÉRATEUR IFC PRINCIPAL
# ─────────────────────────────────────────────

class GenerateurIFC:
    def __init__(self, resultats: Dict[str, Any], nom_projet: str = "Tijan AI Project"):
        self.resultats = resultats
        self.nom_projet = nom_projet
        self.lignes = []
        self._counter = 1
        self._ids = {}

    def _id(self, key: str) -> int:
        if key not in self._ids:
            self._ids[key] = self._counter
            self._counter += 1
        return self._ids[key]

    def _new_id(self) -> int:
        idx = self._counter
        self._counter += 1
        return idx

    def _add(self, line: str):
        self.lignes.append(line)

    def _ref(self, key: str) -> str:
        return f"#{self._id(key)}"

    # ── Extraction des données du moteur ──────

    def _extraire_params(self):
        r = self.resultats
        g = r.get("geometrie", {})
        self.nb_niveaux = g.get("nb_niveaux", r.get("nb_niveaux", 5))
        self.hauteur_etage = g.get("hauteur_etage_m", 3.0)
        self.surface = g.get("surface_emprise_m2", 500.0)
        self.portee = g.get("portee_max_m", 6.0)

        # Dimensions approximatives du bâtiment
        self.largeur = math.sqrt(self.surface * 0.6)
        self.longueur = self.surface / self.largeur

        # Trame de poteaux
        self.pas_x = self.portee
        self.pas_y = self.portee
        self.nb_poteaux_x = max(2, int(self.longueur / self.pas_x) + 1)
        self.nb_poteaux_y = max(2, int(self.largeur / self.pas_y) + 1)

        # Sections structurelles depuis les résultats
        res = r.get("resultats", r)
        poteaux = res.get("poteaux", {})
        section_str = poteaux.get("section_cm", "25x25") if isinstance(poteaux, dict) else "25x25"
        try:
            parts = str(section_str).replace("x", "x").split("x")
            self.poteau_b = float(parts[0]) / 100.0
            self.poteau_h = float(parts[1]) / 100.0
        except:
            self.poteau_b = 0.25
            self.poteau_h = 0.25

        poutres = res.get("poutres", {})
        if isinstance(poutres, dict):
            self.poutre_b = poutres.get("largeur_m", 0.30)
            self.poutre_h = poutres.get("hauteur_m", 0.55)
        else:
            self.poutre_b = 0.30
            self.poutre_h = 0.55

        dalles = res.get("dalle", res.get("dalles", {}))
        if isinstance(dalles, dict):
            self.dalle_ep = dalles.get("epaisseur_m", 0.22)
        else:
            self.dalle_ep = 0.22

        fond = res.get("fondations", {})
        if isinstance(fond, dict):
            self.fond_type = fond.get("type", "radier")
            self.fond_ep = fond.get("epaisseur_m", fond.get("epaisseur_radier_m", 0.80))
        else:
            self.fond_type = "radier"
            self.fond_ep = 0.80

        ville = r.get("localisation", {})
        if isinstance(ville, dict):
            self.ville = ville.get("ville", "Dakar")
        else:
            self.ville = "Dakar"

    # ── Sections IFC ──────────────────────────

    def _ecrire_header(self):
        ts = ifc_timestamp()
        self._add("ISO-10303-21;")
        self._add("HEADER;")
        self._add(f"FILE_DESCRIPTION(('Tijan AI - Note de Calcul Structurel IFC','Projet: {self.nom_projet}'),'2;1');")
        self._add(f"FILE_NAME('{self.nom_projet}.ifc','{ts}',('Tijan AI Engine v2'),('Tijan.ai'),'IFC2X3','','');")
        self._add("FILE_SCHEMA(('IFC2X3'));")
        self._add("ENDSEC;")
        self._add("DATA;")

    def _ecrire_footer(self):
        self._add("ENDSEC;")
        self._add("END-ISO-10303-21;")

    def _def(self, key: str, ifc_class: str, *args) -> int:
        idx = self._id(key)
        args_str = ",".join(str(a) for a in args)
        self._add(f"#{idx}={ifc_class}({args_str});")
        return idx

    def _defn(self, ifc_class: str, *args) -> int:
        idx = self._new_id()
        args_str = ",".join(str(a) for a in args)
        self._add(f"#{idx}={ifc_class}({args_str});")
        return idx

    def _ecrire_contexte(self):
        # Application
        self._def("app_dev", "IFCORGANIZATION", "$,'Tijan AI','Plateforme BIM Afrique',$,$")
        self._def("app", "IFCAPPLICATION",
                  self._ref("app_dev"), "'2.0'", "'Tijan AI Engine'", "'TIJAN_AI'")
        self._def("person", "IFCPERSON", "$,'Ingénieur','Tijan AI',$,$,$,$,$")
        self._def("org", "IFCORGANIZATION", "$,'Tijan AI',$,$,$")
        self._def("person_org", "IFCPERSONANDORGANIZATION",
                  self._ref("person"), self._ref("org"), "$")
        self._def("owner", "IFCOWNERHISTORY",
                  self._ref("person_org"), self._ref("app"), "$,.ADDED.,$,$,$,$,0")

        # Unités
        si_unit = self._defn("IFCSIUNIT", "*,.LENGTHUNIT.,$,.METRE.")
        area_unit = self._defn("IFCSIUNIT", "*,.AREAUNIT.,$,.SQUARE_METRE.")
        vol_unit = self._defn("IFCSIUNIT", "*,.VOLUMEUNIT.,$,.CUBIC_METRE.")
        unit_assign = self._defn("IFCUNITASSIGNMENT", f"({si_unit},{area_unit},{vol_unit})")
        self._ids["unit_assign"] = unit_assign

        # Contexte géométrique
        origin_3d = self._defn("IFCCARTESIANPOINT", "(0.,0.,0.)")
        z_axis = self._defn("IFCDIRECTION", "(0.,0.,1.)")
        x_axis = self._defn("IFCDIRECTION", "(1.,0.,0.)")
        axis2_3d = self._defn("IFCAXIS2PLACEMENT3D",
                              f"#{origin_3d}", f"#{z_axis}", f"#{x_axis}")
        origin_2d = self._defn("IFCCARTESIANPOINT", "(0.,0.)")
        axis2_2d = self._defn("IFCAXIS2PLACEMENT2D", f"#{origin_2d}", "$")
        geom_ctx = self._defn("IFCGEOMETRICREPRESENTATIONCONTEXT",
                              "'Plan'", "'Model'", "3", "1.E-5",
                              f"#{axis2_3d}", "$")
        self._ids["geom_ctx"] = geom_ctx

        # Projet
        proj = self._def("projet", "IFCPROJECT",
                         f"'{new_guid()}'", self._ref("owner"),
                         f"'{self.nom_projet}'", "$", "$", "$", "$",
                         f"(#{geom_ctx})", f"#{unit_assign}")

    def _placement(self, x: float, y: float, z: float) -> int:
        pt = self._defn("IFCCARTESIANPOINT", f"({x:.3f},{y:.3f},{z:.3f})")
        ax = self._defn("IFCAXIS2PLACEMENT3D", f"#{pt}", "$", "$")
        pl = self._defn("IFCLOCALPLACEMENT", "$", f"#{ax}")
        return pl

    def _placement_relatif(self, parent_pl: int, x: float, y: float, z: float) -> int:
        pt = self._defn("IFCCARTESIANPOINT", f"({x:.3f},{y:.3f},{z:.3f})")
        ax = self._defn("IFCAXIS2PLACEMENT3D", f"#{pt}", "$", "$")
        pl = self._defn("IFCLOCALPLACEMENT", f"#{parent_pl}", f"#{ax}")
        return pl

    def _profil_rect(self, b: float, h: float, nom: str) -> int:
        return self._defn("IFCRECTANGLEPROFILEDEF",
                          ".AREA.", f"'{nom}'", "$",
                          f"{b:.3f}", f"{h:.3f}")

    def _extrusion(self, profil_id: int, hauteur: float) -> int:
        dir_up = self._defn("IFCDIRECTION", "(0.,0.,1.)")
        return self._defn("IFCEXTRUDEDAREASOLID",
                          f"#{profil_id}", "$", f"#{dir_up}", f"{hauteur:.3f}")

    def _shape_rep(self, solid_id: int) -> int:
        return self._defn("IFCSHAPEREPRESENTATION",
                          f"#{self._ids['geom_ctx']}",
                          "'Body'", "'SweptSolid'",
                          f"(#{solid_id})")

    def _product_def_shape(self, shape_rep_id: int) -> int:
        return self._defn("IFCPRODUCTDEFINITIONSHAPE",
                          "$", "$", f"(#{shape_rep_id})")

    def _beton_materiau(self) -> int:
        key = "materiau_beton"
        if key not in self._ids:
            mat = self._defn("IFCMATERIAL", "'Béton C30/37 - Tijan AI'")
            self._ids[key] = mat
        return self._ids[key]

    def _ecrire_site_et_batiment(self):
        site_pl = self._placement(0, 0, 0)
        site = self._defn("IFCSITE",
                          f"'{new_guid()}'", self._ref("owner"),
                          f"'{self.ville}'", "$", "$",
                          f"#{site_pl}", "$", "$",
                          ".ELEMENT.", "$", "$", "$", "$", "$")
        self._ids["site"] = site

        bat_pl = self._placement_relatif(site_pl, 0, 0, 0)
        bat = self._defn("IFCBUILDING",
                         f"'{new_guid()}'", self._ref("owner"),
                         f"'{self.nom_projet}'", "$", "$",
                         f"#{bat_pl}", "$", "$",
                         ".ELEMENT.", "$", "$", "$")
        self._ids["batiment"] = bat

        # Relation site → bâtiment
        self._defn("IFCRELAGGREGATES",
                   f"'{new_guid()}'", self._ref("owner"),
                   "'Site contient bâtiment'", "$",
                   f"#{site}", f"(#{bat})")

        # Relation projet → site
        self._defn("IFCRELAGGREGATES",
                   f"'{new_guid()}'", self._ref("owner"),
                   "'Projet contient site'", "$",
                   self._ref("projet"), f"(#{site})")

    def _ecrire_niveaux(self) -> List[Dict]:
        niveaux = []
        bat_id = self._ids["batiment"]

        # Fondations (niveau -1)
        z_fond = -(self.fond_ep + 0.5)
        pl_fond = self._placement(0, 0, z_fond)
        storey_fond = self._defn("IFCBUILDINGSTOREY",
                                 f"'{new_guid()}'", self._ref("owner"),
                                 "'Fondations'", "$", "$",
                                 f"#{pl_fond}", "$", "$",
                                 ".ELEMENT.", f"{z_fond:.3f}")
        niveaux.append({"id": storey_fond, "z": z_fond, "nom": "Fondations", "pl": pl_fond})

        # Niveaux courants
        for i in range(self.nb_niveaux + 1):
            nom = "RDC" if i == 0 else f"Niveau {i}"
            z = i * self.hauteur_etage
            pl = self._placement(0, 0, z)
            storey = self._defn("IFCBUILDINGSTOREY",
                                f"'{new_guid()}'", self._ref("owner"),
                                f"'{nom}'", "$", "$",
                                f"#{pl}", "$", "$",
                                ".ELEMENT.", f"{z:.3f}")
            niveaux.append({"id": storey, "z": z, "nom": nom, "pl": pl})

        # Terrasse
        z_terr = self.nb_niveaux * self.hauteur_etage
        pl_terr = self._placement(0, 0, z_terr)
        storey_terr = self._defn("IFCBUILDINGSTOREY",
                                 f"'{new_guid()}'", self._ref("owner"),
                                 "'Terrasse'", "$", "$",
                                 f"#{pl_terr}", "$", "$",
                                 ".ELEMENT.", f"{z_terr:.3f}")
        niveaux.append({"id": storey_terr, "z": z_terr, "nom": "Terrasse", "pl": pl_terr})

        # Relation bâtiment → niveaux
        ids_str = ",".join(f"#{n['id']}" for n in niveaux)
        self._defn("IFCRELAGGREGATES",
                   f"'{new_guid()}'", self._ref("owner"),
                   "'Bâtiment contient niveaux'", "$",
                   f"#{bat_id}", f"({ids_str})")

        return niveaux

    def _ecrire_radier(self, niveaux: List[Dict]):
        """Radier général ou semelles selon le type de fondation."""
        z_fond = niveaux[0]["z"]
        pl_fond = niveaux[0]["pl"]
        fond_elements = []

        if self.fond_type in ["radier", "radier_general"]:
            # Un radier plein sur toute l'emprise
            prof = self._profil_rect(self.longueur, self.largeur, "Radier")
            solid = self._extrusion(prof, self.fond_ep)
            shape = self._shape_rep(solid)
            pds = self._product_def_shape(shape)
            pl = self._placement_relatif(pl_fond, self.longueur / 2, self.largeur / 2, 0)
            slab = self._defn("IFCSLAB",
                              f"'{new_guid()}'", self._ref("owner"),
                              "'Radier Général'", "$", "$",
                              f"#{pl}", f"#{pds}", "$", ".BASESLAB.")
            fond_elements.append(slab)

        else:
            # Pieux forés
            rayon = 0.40
            prof_pieu = self._defn("IFCCIRCLEPROFILEDEF",
                                   ".AREA.", "'Pieu_800'", "$", f"{rayon:.3f}")
            for ix in range(self.nb_poteaux_x):
                for iy in range(self.nb_poteaux_y):
                    x = ix * self.pas_x
                    y = iy * self.pas_y
                    solid = self._extrusion(prof_pieu, 10.0)
                    shape = self._shape_rep(solid)
                    pds = self._product_def_shape(shape)
                    pl = self._placement_relatif(pl_fond, x, y, -10.0)
                    pile = self._defn("IFCPILE",
                                     f"'{new_guid()}'", self._ref("owner"),
                                     f"'Pieu P{ix+1}{iy+1}'", "$", "$",
                                     f"#{pl}", f"#{pds}", "$", ".COHESION.")
                    fond_elements.append(pile)

        # Relation niveau fondations → éléments
        ids_str = ",".join(f"#{e}" for e in fond_elements)
        self._defn("IFCRELCONTAINEDINSPATIALSTRUCTURE",
                   f"'{new_guid()}'", self._ref("owner"),
                   "'Fondations'", "$",
                   f"({ids_str})", f"#{niveaux[0]['id']}")

    def _ecrire_poteaux(self, niveaux: List[Dict]):
        """Poteaux sur tous les niveaux."""
        for niveau in niveaux[1:-1]:  # Exclure fondations et terrasse
            elements = []
            z = niveau["z"]
            pl_niveau = niveau["pl"]
            nom_niv = niveau["nom"]

            for ix in range(self.nb_poteaux_x):
                for iy in range(self.nb_poteaux_y):
                    x = ix * self.pas_x
                    y = iy * self.pas_y
                    prof = self._profil_rect(self.poteau_b, self.poteau_h,
                                            f"Poteau_{int(self.poteau_b*100)}x{int(self.poteau_h*100)}")
                    solid = self._extrusion(prof, self.hauteur_etage)
                    shape = self._shape_rep(solid)
                    pds = self._product_def_shape(shape)
                    pl = self._placement_relatif(pl_niveau, x, y, 0)
                    col = self._defn("IFCCOLUMN",
                                     f"'{new_guid()}'", self._ref("owner"),
                                     f"'Poteau P{ix+1}{iy+1} - {nom_niv}'",
                                     "$", "$",
                                     f"#{pl}", f"#{pds}", "$")
                    elements.append(col)

            ids_str = ",".join(f"#{e}" for e in elements)
            self._defn("IFCRELCONTAINEDINSPATIALSTRUCTURE",
                       f"'{new_guid()}'", self._ref("owner"),
                       f"'Poteaux {nom_niv}'", "$",
                       f"({ids_str})", f"#{niveau['id']}")

    def _ecrire_poutres(self, niveaux: List[Dict]):
        """Poutres principales et secondaires sur chaque niveau."""
        for niveau in niveaux[1:-1]:
            elements = []
            pl_niveau = niveau["pl"]
            nom_niv = niveau["nom"]
            z_poutre = self.hauteur_etage - self.poutre_h

            # Poutres en X
            for iy in range(self.nb_poteaux_y):
                for ix in range(self.nb_poteaux_x - 1):
                    x1 = ix * self.pas_x
                    y = iy * self.pas_y
                    prof = self._profil_rect(self.poutre_b, self.poutre_h,
                                            f"Poutre_{int(self.poutre_b*100)}x{int(self.poutre_h*100)}")
                    solid = self._extrusion(prof, self.pas_x)
                    shape = self._shape_rep(solid)
                    pds = self._product_def_shape(shape)
                    pl = self._placement_relatif(pl_niveau, x1, y, z_poutre)
                    beam = self._defn("IFCBEAM",
                                     f"'{new_guid()}'", self._ref("owner"),
                                     f"'Poutre PX{ix+1}{iy+1} - {nom_niv}'",
                                     "$", "$",
                                     f"#{pl}", f"#{pds}", "$")
                    elements.append(beam)

            # Poutres en Y
            for ix in range(self.nb_poteaux_x):
                for iy in range(self.nb_poteaux_y - 1):
                    x = ix * self.pas_x
                    y1 = iy * self.pas_y
                    prof = self._profil_rect(self.poutre_b, self.poutre_h,
                                            f"Poutre_{int(self.poutre_b*100)}x{int(self.poutre_h*100)}")
                    solid = self._extrusion(prof, self.pas_y)
                    shape = self._shape_rep(solid)
                    pds = self._product_def_shape(shape)

                    # Rotation 90° pour Y
                    pt_rot = self._defn("IFCCARTESIANPOINT", f"({x:.3f},{y1:.3f},{z_poutre:.3f})")
                    dir_z = self._defn("IFCDIRECTION", "(0.,0.,1.)")
                    dir_y = self._defn("IFCDIRECTION", "(0.,1.,0.)")
                    ax_rot = self._defn("IFCAXIS2PLACEMENT3D",
                                       f"#{pt_rot}", f"#{dir_z}", f"#{dir_y}")
                    pl_rot = self._defn("IFCLOCALPLACEMENT", f"#{pl_niveau}", f"#{ax_rot}")

                    beam = self._defn("IFCBEAM",
                                     f"'{new_guid()}'", self._ref("owner"),
                                     f"'Poutre PY{ix+1}{iy+1} - {nom_niv}'",
                                     "$", "$",
                                     f"#{pl_rot}", f"#{pds}", "$")
                    elements.append(beam)

            if elements:
                ids_str = ",".join(f"#{e}" for e in elements)
                self._defn("IFCRELCONTAINEDINSPATIALSTRUCTURE",
                           f"'{new_guid()}'", self._ref("owner"),
                           f"'Poutres {nom_niv}'", "$",
                           f"({ids_str})", f"#{niveau['id']}")

    def _ecrire_dalles(self, niveaux: List[Dict]):
        """Dalles sur chaque niveau."""
        for niveau in niveaux[1:]:
            pl_niveau = niveau["pl"]
            nom_niv = niveau["nom"]
            z_dalle = self.hauteur_etage - self.dalle_ep

            prof = self._profil_rect(self.longueur, self.largeur, "Dalle_pleine")
            solid = self._extrusion(prof, self.dalle_ep)
            shape = self._shape_rep(solid)
            pds = self._product_def_shape(shape)
            pl = self._placement_relatif(pl_niveau,
                                         self.longueur / 2, self.largeur / 2, z_dalle)
            slab = self._defn("IFCSLAB",
                              f"'{new_guid()}'", self._ref("owner"),
                              f"'Dalle {nom_niv}'", "$", "$",
                              f"#{pl}", f"#{pds}", "$", ".FLOOR.")

            self._defn("IFCRELCONTAINEDINSPATIALSTRUCTURE",
                       f"'{new_guid()}'", self._ref("owner"),
                       f"'Dalle {nom_niv}'", "$",
                       f"(#{slab})", f"#{niveau['id']}")

    def _ecrire_proprietes(self):
        """Propriétés Tijan AI : béton, Eurocodes, Edge."""
        r = self.resultats
        res = r.get("resultats", r)
        mat = res.get("materiaux", res.get("materiau", {}))
        edge = r.get("score_edge", res.get("score_edge", {}))

        # Propriétés béton
        props_beton = []
        if isinstance(mat, dict):
            classe = mat.get("classe_beton", "C30/37")
            expo = mat.get("classe_exposition", "XS1")
            enrobage = mat.get("enrobage_mm", 40)
            for nom, val in [
                ("ClasseBéton", f"'{classe}'"),
                ("ClasseExposition", f"'{expo}'"),
                ("EnrobageMm", f"{enrobage}."),
                ("NormeCalcul", "'Eurocodes EN 1992-1-1'"),
                ("LogicielCalcul", "'Tijan AI Engine v2'"),
            ]:
                pid = self._defn("IFCPROPERTYSINGLEVALUE",
                                 f"'{nom}'", "$",
                                 f"IFCLABEL({val})", "$")
                props_beton.append(pid)

        # Propriétés Edge
        props_edge = []
        if isinstance(edge, dict):
            for pilier, data in edge.items():
                if isinstance(data, dict):
                    pct = data.get("total_pct", 0)
                    conforme = data.get("conforme", False)
                    pid = self._defn("IFCPROPERTYSINGLEVALUE",
                                     f"'Edge_{pilier}_pct'", "$",
                                     f"IFCREAL({pct}.)", "$")
                    props_edge.append(pid)
                    pid2 = self._defn("IFCPROPERTYSINGLEVALUE",
                                      f"'Edge_{pilier}_conforme'", "$",
                                      f"IFCBOOLEAN({'TRUE' if conforme else 'FALSE'})", "$")
                    props_edge.append(pid2)

        if props_beton:
            pset_b = self._defn("IFCPROPERTYSET",
                                f"'{new_guid()}'", self._ref("owner"),
                                "'Tijan_Béton_Eurocodes'", "$",
                                f"({','.join(f'#{p}' for p in props_beton)})")

        if props_edge:
            pset_e = self._defn("IFCPROPERTYSET",
                                f"'{new_guid()}'", self._ref("owner"),
                                "'Tijan_Score_EDGE'", "$",
                                f"({','.join(f'#{p}' for p in props_edge)})")

    # ── Point d'entrée ─────────────────────────

    def generer(self) -> str:
        self._extraire_params()
        self._ecrire_header()
        self._ecrire_contexte()
        self._ecrire_site_et_batiment()
        niveaux = self._ecrire_niveaux()
        self._ecrire_radier(niveaux)
        self._ecrire_poteaux(niveaux)
        self._ecrire_poutres(niveaux)
        self._ecrire_dalles(niveaux)
        self._ecrire_proprietes()
        self._ecrire_footer()
        return "\n".join(self.lignes)


# ─────────────────────────────────────────────
# FONCTION PRINCIPALE APPELÉE PAR main.py
# ─────────────────────────────────────────────

def generer_ifc(resultats: Dict[str, Any], nom_projet: str = "Tijan AI Project") -> str:
    """
    Entrée : dict résultats du moteur Eurocodes (sortie de /calculate)
    Sortie : contenu du fichier .ifc (string)
    """
    gen = GenerateurIFC(resultats, nom_projet)
    return gen.generer()


# ─────────────────────────────────────────────
# TEST LOCAL
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Simuler les résultats du moteur pour R+12 Dakar
    resultats_test = {
        "nom": "Tour Résidentielle Dakar R+12",
        "geometrie": {
            "surface_emprise_m2": 766,
            "nb_niveaux": 12,
            "hauteur_etage_m": 3.0,
            "portee_max_m": 6.0,
        },
        "localisation": {"ville": "Dakar", "distance_mer_km": 0.2},
        "resultats": {
            "materiaux": {
                "classe_beton": "C30/37",
                "classe_exposition": "XS1",
                "enrobage_mm": 40,
            },
            "poteaux": {"section_cm": "30x30"},
            "poutres": {"largeur_m": 0.30, "hauteur_m": 0.55},
            "dalle": {"epaisseur_m": 0.22},
            "fondations": {"type": "pieux", "epaisseur_m": 0.80},
        },
        "score_edge": {
            "energie": {"total_pct": 22, "conforme": True},
            "eau": {"total_pct": 21, "conforme": True},
            "materiaux": {"total_pct": 22, "conforme": True},
        },
    }

    contenu = generer_ifc(resultats_test, "Tour Dakar R+12")

    with open("/mnt/user-data/outputs/tijan_structure.ifc", "w") as f:
        f.write(contenu)

    lignes = contenu.split("\n")
    entites = [l for l in lignes if l.startswith("#")]
    colonnes = [l for l in entites if "IFCCOLUMN" in l]
    poutres = [l for l in entites if "IFCBEAM" in l]
    dalles = [l for l in entites if "IFCSLAB" in l]
    pieux = [l for l in entites if "IFCPILE" in l]

    print(f"✅ IFC généré : {len(lignes)} lignes, {len(entites)} entités")
    print(f"   Poteaux (IFCCOLUMN) : {len(colonnes)}")
    print(f"   Poutres (IFCBEAM)   : {len(poutres)}")
    print(f"   Dalles (IFCSLAB)    : {len(dalles)}")
    print(f"   Pieux (IFCPILE)     : {len(pieux)}")
    print(f"   Fichier : tijan_structure.ifc")
