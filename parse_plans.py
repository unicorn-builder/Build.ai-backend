import os, re, json, base64, logging, pathlib
logger = logging.getLogger("tijan")
CLAUDE_MODEL = "claude-sonnet-4-20250514"
MAX_TEXT = 8000
MIN_TEXT_LEN = 80
DEFAULTS = {"nb_niveaux":5,"hauteur_etage_m":3.0,"surface_emprise_m2":500.0,"portee_max_m":6.0,"portee_min_m":4.5,"nb_travees_x":4,"nb_travees_y":3,"classe_beton":"C30/37","classe_acier":"HA500","pression_sol_MPa":0.15}
PROMPT = """Tu es un ingenieur structure expert. Analyse ce contenu extrait de plans architecturaux. Reponds UNIQUEMENT avec un JSON valide sans markdown:\n{"nom":"nom du projet","ville":"ville","nb_niveaux":entier,"hauteur_etage_m":float,"surface_emprise_m2":float,"portee_max_m":float,"portee_min_m":float,"nb_travees_x":entier,"nb_travees_y":entier,"classe_beton":"C30/37","pression_sol_MPa":float}\nSi valeur absente mets null."""

def _client():
    import anthropic
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key: raise RuntimeError("ANTHROPIC_API_KEY manquante")
    return anthropic.Anthropic(api_key=key)

def _defaults(p):
    for k,v in DEFAULTS.items():
        if k not in p or p[k] is None: p[k]=v
    p.setdefault("classe_acier","HA500")
    return p

def _clean(raw):
    raw=raw.strip()
    raw=re.sub(r'^```json\s*','',raw)
    raw=re.sub(r'^```\s*','',raw)
    raw=re.sub(r'\s*```$','',raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from Claude: {raw[:200]}") from e

def _claude_text(texte, client):
    msg=client.messages.create(model=CLAUDE_MODEL,max_tokens=600,messages=[{"role":"user","content":f"{PROMPT}\n\nCONTENU:\n{texte[:MAX_TEXT]}"}])
    return _clean(msg.content[0].text)

def _claude_vision(img_b64, client):
    msg=client.messages.create(model=CLAUDE_MODEL,max_tokens=600,messages=[{"role":"user","content":[{"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":img_b64}},{"type":"text","text":f"{PROMPT}\n\nAnalyse ce plan architectural."}]}])
    return _clean(msg.content[0].text)

def _parse_pdf(path, client):
    try:
        import fitz
    except ImportError:
        return {"ok":False,"message":"pymupdf non installe"}
    try:
        doc=fitz.open(path)
    except Exception as e:
        return {"ok":False,"message":f"PDF illisible: {e}"}
    try:
        if len(doc)==0:
            return {"ok":False,"message":"PDF vide"}
        texte="".join(page.get_text() for page in doc).strip()
        if len(texte)>=MIN_TEXT_LEN:
            try:
                p=_claude_text(texte,client)
                p=_defaults(p); p["ok"]=True; p["source"]="pdf_vectoriel"
                # Extract geometry for plan generation
                p["dwg_geometry"] = _extract_pdf_geometry(path)
                return p
            except Exception as e:
                return {"ok":False,"message":f"Claude PDF: {e}"}
        try:
            mat=fitz.Matrix(120/72,120/72)
            pix=doc[0].get_pixmap(matrix=mat,alpha=False)
            img_bytes=pix.tobytes("jpeg")
            if len(img_bytes)>3500000:
                doc2=None
                try:
                    doc2=fitz.open(path); mat=fitz.Matrix(90/72,90/72)
                    pix=doc2[0].get_pixmap(matrix=mat,alpha=False); img_bytes=pix.tobytes("jpeg")
                finally:
                    if doc2:
                        doc2.close()
            img_b64=base64.standard_b64encode(img_bytes).decode()
            p=_claude_vision(img_b64,client)
            p=_defaults(p); p["ok"]=True; p["source"]="pdf_scanne_vision"
            # Extract geometry for plan generation
            p["dwg_geometry"] = _extract_pdf_geometry(path)
            return p
        except Exception as e:
            return {"ok":False,"message":f"PDF scanne: {e}"}
    finally:
        doc.close()


def _extract_pdf_geometry(path):
    """Try to extract vector geometry from PDF for plan background."""
    try:
        from extract_pdf_geometry import extract_geometry_from_pdf
        geom = extract_geometry_from_pdf(path, max_pages=5)
        if geom:
            logger.info(f"PDF geometry extracted successfully")
        return geom
    except Exception as e:
        logger.warning(f"PDF geometry extraction failed: {e}")
        return None

def _extract_ezdxf(doc, client, label):
    msp=doc.modelspace()
    textes=[]; dims=[]; xmin=xmax=ymin=ymax=None; n=0
    for ent in msp:
        t=ent.dxftype(); n+=1
        if t in("TEXT","ATTDEF","ATTRIB"):
            try:
                v=ent.dxf.text.strip()
                if v and len(v)<300: textes.append(v)
            except: pass
        elif t=="MTEXT":
            try:
                v=ent.plain_mtext().strip()
                if v and len(v)<500: textes.append(v)
            except: pass
        elif t=="DIMENSION":
            try:
                val=ent.dxf.actual_measurement
                if val and 0.01<abs(val)<200000: dims.append(round(abs(val),2))
            except: pass
        elif t in("LINE","LWPOLYLINE","POLYLINE"):
            try:
                bb=ent.get_bounding_box()
                if bb:
                    xmin=bb.extmin.x if xmin is None else min(xmin,bb.extmin.x)
                    xmax=bb.extmax.x if xmax is None else max(xmax,bb.extmax.x)
                    ymin=bb.extmin.y if ymin is None else min(ymin,bb.extmin.y)
                    ymax=bb.extmax.y if ymax is None else max(ymax,bb.extmax.y)
            except: pass
    geo=""
    if xmin is not None:
        dx=abs(xmax-xmin); dy=abs(ymax-ymin)
        if max(dx,dy)>500: dx_m=round(dx/1000,2); dy_m=round(dy/1000,2)
        else: dx_m=round(dx,2); dy_m=round(dy,2)
        geo=f"Etendue: {dx_m}m x {dy_m}m | Surface estimee: {round(dx_m*dy_m,1)} m2"
    contenu="\n".join(list(dict.fromkeys(textes))[:100])
    if geo: contenu+=f"\n{geo}"
    if dims: contenu+=f"\nDimensions: {sorted(set(dims))[:40]}"
    contenu+=f"\nEntites: {n}"
    if len(contenu.strip())<15:
        return {"ok":False,"message":"Fichier lu mais sans annotations suffisantes","source":label+"_vide"}
    try:
        p=_claude_text(contenu,client)
        p=_defaults(p); p["ok"]=True; p["source"]=label
        return p
    except Exception as e:
        return {"ok":False,"message":f"Claude {label}: {e}"}

def _parse_dwg(path, client):
    try:
        from ezdxf.recover import readfile
        doc,_=readfile(path)
        return _extract_ezdxf(doc,client,"dwg_ezdxf")
    except Exception as e:
        return {"ok":False,"message":f"DWG non lu: {e}. Exportez en PDF depuis AutoCAD pour une extraction optimale."}

def _parse_dxf(path, client):
    try:
        import ezdxf
        doc=ezdxf.readfile(path)
        return _extract_ezdxf(doc,client,"dxf_ezdxf")
    except Exception as e:
        return {"ok":False,"message":f"DXF non lu: {e}"}

def extraire_params(fichier_path):
    ext=pathlib.Path(fichier_path).suffix.lower()
    try: c=_client()
    except RuntimeError as e: return {"ok":False,"message":str(e)}
    try:
        if ext==".pdf": return _parse_pdf(fichier_path,c)
        elif ext==".dwg": return _parse_dwg(fichier_path,c)
        elif ext==".dxf": return _parse_dxf(fichier_path,c)
        else: return {"ok":False,"message":f"Format '{ext}' non supporte. Acceptes: PDF, DWG, DXF."}
    except Exception as e:
        return {"ok":False,"message":f"Erreur: {e}"}

def extraire_params_pdf(path): return extraire_params(path)
