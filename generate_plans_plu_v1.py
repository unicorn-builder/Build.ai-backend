"""
generate_plans_plu_v1.py — Tijan AI — Plans PLU Sakho R+8
"""
import math
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdfcanvas

A3L = landscape(A3)
NOIR   = colors.HexColor("#111111")
GRIS1  = colors.HexColor("#333333")
GRIS2  = colors.HexColor("#555555")
GRIS3  = colors.HexColor("#888888")
GRIS4  = colors.HexColor("#CCCCCC")
GRIS5  = colors.HexColor("#E8E8E8")
BLANC  = colors.HexColor("#FFFFFF")
VERT   = colors.HexColor("#43A956")
VERT_P = colors.HexColor("#E8F5E9")
EU_COL  = colors.HexColor("#1565C0")
EV_COL  = colors.HexColor("#2E7D32")
EF_COL  = colors.HexColor("#00838F")
ECS_COL = colors.HexColor("#E65100")

AXES_X_MM = [0, 5050, 8360, 11620, 14930, 18270, 21580, 24890, 29940, 34990]
AXES_Y_MM = [0, 5051, 10102]
LABELS_X  = ["1","2","3","4","5","6","7","8","9","10"]
LABELS_Y  = ["A","B","C"]

NIVEAUX = [
    ("SS",  "SOUS-SOL",        -3.20, False),
    ("RDC", "REZ-DE-CHAUSSEE",  0.00, False),
    ("R1",  "ETAGE 1",          3.70, True),
    ("R2",  "ETAGE 2",          7.40, True),
    ("R3",  "ETAGE 3",         11.10, True),
    ("R4",  "ETAGE 4",         14.80, True),
    ("R5",  "ETAGE 5",         18.50, True),
    ("R6",  "ETAGE 6",         22.20, True),
    ("R7",  "ETAGE 7",         25.90, True),
    ("R8",  "ETAGE 8",         29.60, False),
    ("TER", "TERRASSE",        33.30, False),
]

def reseau_color(r):
    return {"EU":EU_COL,"EV":EV_COL,"EF":EF_COL,"ECS":ECS_COL}.get(r, GRIS3)

def get_equips(code, cote):
    base = [
        (4,1,"EU","chute","CC-EU1",cote),
        (5,1,"EU","chute","CC-EU2",cote),
        (4,1,"EV","chute","CC-EV1",cote),
        (4,1,"EF","montante","CM-EF1",cote),
        (5,1,"ECS","montante","CM-ECS1",cote),
    ]
    if code == "SS":
        return base + [
            (7,1,"EF","bac","BACHE",cote),
            (7,1,"EU","regard","RG-BACHE",cote),
            (3,2,"EU","siphon","VEST-EU",cote-0.08),
            (3,2,"EV","wc","VEST-WC",cote),
            (3,2,"EF","lavabo","VEST-EF",cote),
            (5,2,"EF","bac","PISC-EF",cote),
        ]
    elif code == "TER":
        return [
            (2,1,"EV","regard","EP-1",cote),
            (4,1,"EV","regard","EP-2",cote),
            (6,1,"EV","regard","EP-3",cote),
            (8,1,"EV","regard","EP-4",cote),
            (5,0,"ECS","bac","CESI-1",cote),
            (6,0,"ECS","bac","CESI-2",cote),
            (4,1,"EU","chute","CC-EU1",cote),
        ]
    elif code == "RDC":
        return base + [
            (2,1,"EU","siphon","WC-H",cote-0.05),
            (2,1,"EV","wc","WC-H2",cote),
            (3,1,"EU","siphon","WC-F",cote-0.05),
            (3,1,"EV","wc","WC-F2",cote),
            (6,0,"EU","evier","REST-EV",cote-0.05),
            (6,0,"EF","lavabo","REST-EF",cote),
            (6,0,"ECS","bac","REST-ECS",cote),
            (1,0,"EU","siphon","APT-SDB",cote-0.08),
            (1,0,"EV","wc","APT-WC",cote),
        ]
    else:
        return base + [
            (1,0,"EU","siphon","A-SDB1",cote-0.08),
            (1,0,"EV","wc","A-WC1",cote),
            (1,0,"EF","lavabo","A-LV1",cote),
            (1,0,"ECS","douche","A-DCH1",cote),
            (2,0,"EU","siphon","A-SDB2",cote-0.08),
            (2,0,"EV","wc","A-WC2",cote),
            (2,0,"EF","lavabo","A-LV2",cote),
            (1,1,"EU","evier","A-EV1",cote-0.05),
            (1,1,"EF","lavabo","A-EF1",cote),
            (1,1,"ECS","bac","A-BAC1",cote),
            (7,0,"EU","siphon","B-SDB1",cote-0.08),
            (7,0,"EV","wc","B-WC1",cote),
            (7,0,"EF","lavabo","B-LV1",cote),
            (7,0,"ECS","douche","B-DCH1",cote),
            (8,0,"EU","evier","B-EV1",cote-0.05),
            (8,0,"EF","lavabo","B-EF1",cote),
            (5,2,"EU","siphon","C-SDB1",cote-0.08),
            (5,2,"EV","wc","C-WC1",cote),
            (5,2,"EF","lavabo","C-LV1",cote),
            (5,2,"ECS","douche","C-DCH1",cote),
            (3,2,"EU","siphon","D-SDB1",cote-0.08),
            (3,2,"EV","wc","D-WC1",cote),
            (3,2,"EF","lavabo","D-LV1",cote),
            (6,2,"EU","siphon","E-SDB1",cote-0.08),
            (6,2,"EV","wc","E-WC1",cote),
            (6,2,"EF","lavabo","E-LV1",cote),
        ]

def draw_sym(c, x, y, reseau, sym, r=3.5):
    col = reseau_color(reseau)
    c.setStrokeColor(col); c.setFillColor(col); c.setLineWidth(0.6)
    if sym == "chute":
        c.circle(x, y, r+1.5, fill=0, stroke=1)
        c.circle(x, y, r-0.5, fill=1, stroke=0)
    elif sym == "siphon":
        c.circle(x, y, r, fill=0, stroke=1)
        c.line(x-r+1,y,x+r-1,y); c.line(x,y-r+1,x,y+r-1)
    elif sym == "wc":
        c.roundRect(x-r, y-r*0.7, r*2, r*1.4, r*0.3, fill=1, stroke=0)
    elif sym == "lavabo":
        c.setFillColor(BLANC)
        p = c.beginPath(); p.arc(x-r,y-r,x+r,y+r,0,180); p.close()
        c.drawPath(p, fill=1, stroke=1)
    elif sym == "evier":
        c.setFillColor(BLANC); c.rect(x-r,y-r*0.6,r*2,r*1.2,fill=1,stroke=1)
        c.setStrokeColor(col); c.line(x,y-r*0.5,x,y+r*0.5)
    elif sym == "douche":
        c.setDash(2,1); c.setFillColor(BLANC)
        c.rect(x-r,y-r,r*2,r*2,fill=1,stroke=1); c.setDash()
        c.circle(x,y,1,fill=1,stroke=0)
    elif sym == "bac":
        c.setFillColor(colors.Color(col.red,col.green,col.blue,0.3))
        c.rect(x-r,y-r*0.7,r*2,r*1.4,fill=1,stroke=1)
    elif sym == "regard":
        c.setFillColor(BLANC); c.rect(x-r,y-r,r*2,r*2,fill=1,stroke=1)
        c.line(x-r,y-r,x+r,y+r); c.line(x+r,y-r,x-r,y+r)
    elif sym == "montante":
        c.setFillColor(col)
        p = c.beginPath()
        p.moveTo(x,y+r+1); p.lineTo(x-r,y-r+1); p.lineTo(x+r,y-r+1); p.close()
        c.drawPath(p, fill=1, stroke=0)

def draw_grille(c, ox, oy, sc):
    xs = [ox + ax*sc for ax in AXES_X_MM]
    ys = [oy + ay*sc for ay in AXES_Y_MM]
    gw = xs[-1]-xs[0]; gh = ys[-1]-ys[0]
    # hachures
    c.saveState(); c.setStrokeColor(GRIS5); c.setLineWidth(0.15)
    step = 8
    n_steps = int((gw+gh)/step)+1
    for i in range(n_steps):
        d = i*step
        x1=xs[0]+max(d-gh,0); y1=ys[0]+min(d,gh)
        x2=xs[0]+min(d,gw);   y2=ys[-1]-max(0,d-gw)
        c.line(x1,y1,x2,y2)
    c.restoreState()
    # grille
    c.setStrokeColor(GRIS4); c.setLineWidth(0.3)
    for x in xs: c.line(x, ys[0]-10, x, ys[-1]+10)
    for y in ys: c.line(xs[0]-10, y, xs[-1]+10, y)
    # murs
    mur = max(0.23*sc, 1.5)
    c.setFillColor(GRIS4); c.setStrokeColor(GRIS3); c.setLineWidth(0.2)
    c.rect(xs[0]-mur/2, ys[0]-mur/2, gw+mur, mur, fill=1, stroke=0)
    c.rect(xs[0]-mur/2, ys[-1]-mur/2, gw+mur, mur, fill=1, stroke=0)
    c.rect(xs[0]-mur/2, ys[0], mur, gh, fill=1, stroke=0)
    c.rect(xs[-1]-mur/2, ys[0], mur, gh, fill=1, stroke=0)
    c.rect(xs[4]-mur/2, ys[0], mur, gh, fill=1, stroke=0)
    c.rect(xs[5]-mur/2, ys[0], mur, gh, fill=1, stroke=0)
    c.rect(xs[0], ys[1]-mur/2, gw, mur, fill=1, stroke=0)
    # poteaux
    pot = max(0.25*sc, 2.5)
    c.setFillColor(GRIS2)
    for x in xs:
        for y in ys:
            c.rect(x-pot/2,y-pot/2,pot,pot,fill=1,stroke=0)
    # bulles axe
    r_ax = 4
    c.setFont("Helvetica-Bold", 5)
    for i,x in enumerate(xs):
        c.setFillColor(BLANC); c.setStrokeColor(NOIR); c.setLineWidth(0.4)
        c.circle(x, ys[0]-15, r_ax, fill=1, stroke=1)
        c.setFillColor(NOIR); c.drawCentredString(x, ys[0]-17, LABELS_X[i])
    for j,y in enumerate(ys):
        c.setFillColor(BLANC); c.setStrokeColor(NOIR); c.setLineWidth(0.4)
        c.circle(xs[-1]+15, y, r_ax, fill=1, stroke=1)
        c.setFillColor(NOIR); c.drawCentredString(xs[-1]+15, y-2, LABELS_Y[j])
    # cotations
    c.setFillColor(GRIS2); c.setFont("Helvetica", 4.5)
    c.setStrokeColor(GRIS3); c.setLineWidth(0.2)
    cy_cot = ys[-1]+18
    for i in range(len(xs)-1):
        x1,x2 = xs[i],xs[i+1]
        dim = (AXES_X_MM[i+1]-AXES_X_MM[i])/10
        c.line(x1,cy_cot,x2,cy_cot)
        c.line(x1,cy_cot-2,x1,cy_cot+2); c.line(x2,cy_cot-2,x2,cy_cot+2)
        c.drawCentredString((x1+x2)/2, cy_cot+2, f"{dim:.0f}")
    return xs, ys

def draw_canalisations(c, xs, ys, equips, reseau):
    col = reseau_color(reseau)
    chutes = [eq for eq in equips if eq[2]==reseau and eq[3] in ("chute","montante") and "CC" in eq[4]]
    if not chutes: return
    cc = chutes[0]
    cc_x = xs[min(cc[0],len(xs)-1)]
    cc_y = ys[min(cc[1],len(ys)-1)]
    lw = {"EU":1.4,"EV":1.2,"EF":0.9,"ECS":0.9}.get(reseau,1.0)
    c.setStrokeColor(col); c.setLineWidth(lw)
    for eq in equips:
        if eq[2]!=reseau: continue
        if eq[3] in ("chute","montante") and "CC" in eq[4]: continue
        ex = xs[min(eq[0],len(xs)-1)]
        ey = ys[min(eq[1],len(ys)-1)]
        if abs(ex-cc_x)>3 or abs(ey-cc_y)>3:
            c.line(ex,ey,cc_x,ey); c.line(cc_x,ey,cc_x,cc_y)

def cartouche(c, w, h, niv_label, pg, total):
    cw=130*mm; ch=28*mm; cx=w-cw-5*mm; cy=5*mm
    c.setFillColor(BLANC); c.setStrokeColor(NOIR); c.setLineWidth(0.5)
    c.rect(cx,cy,cw,ch,fill=1,stroke=1)
    c.setFillColor(VERT); c.rect(cx,cy+ch-8*mm,cw,8*mm,fill=1,stroke=0)
    c.setFillColor(BLANC); c.setFont("Helvetica-Bold",8)
    c.drawCentredString(cx+cw/2, cy+ch-5*mm, f"PLAN PLU — {niv_label}")
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold",6.5)
    c.drawString(cx+3*mm, cy+ch-14*mm, "Projet :")
    c.setFont("Helvetica",6.5)
    c.drawString(cx+22*mm, cy+ch-14*mm, "Residence Papa Oumar Sakho — R+8 — Dakar")
    c.setFont("Helvetica-Bold",6.5); c.drawString(cx+3*mm, cy+ch-19*mm, "BET :")
    c.setFont("Helvetica",6.5); c.drawString(cx+22*mm, cy+ch-19*mm, "Tijan AI — Ingenierie MEP")
    c.setFont("Helvetica",6)
    c.drawString(cx+3*mm, cy+3*mm, "Echelle : 1/200   |   Format : A3")
    c.drawString(cx+65*mm, cy+3*mm, f"PLU-{pg:02d}/{total:02d}")
    c.drawString(cx+100*mm, cy+3*mm, "Mars 2026")
    c.setFillColor(VERT); c.setFont("Helvetica-Bold",9)
    c.drawString(cx+3*mm, cy+10*mm, "tijan")
    c.setFillColor(NOIR); c.drawString(cx+19*mm, cy+10*mm, "AI")

def border(c, w, h):
    c.setStrokeColor(NOIR); c.setLineWidth(0.5)
    c.rect(5*mm,5*mm,w-10*mm,h-10*mm)
    c.setLineWidth(0.2); c.rect(6.5*mm,6.5*mm,w-13*mm,h-13*mm)

def pl_plu(c, code, label, cote, courant, pg, total):
    w,h = A3L; c.setPageSize(A3L); border(c,w,h)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold",12)
    c.drawString(12*mm, h-15*mm, f"PLAN PLU — {label}")
    c.setFont("Helvetica",6.5); c.setFillColor(GRIS2)
    c.drawString(12*mm, h-21*mm,
        f"Residence Papa Oumar Sakho R+8 — Dakar   |   Cote : {cote:+.2f} m NGF")
    c.setFillColor(VERT); c.setFont("Helvetica-Bold",7)
    c.drawString(12*mm, h-27*mm,
        "EU — Eaux Usees  |  EV — Eaux Vannes  |  EF — Eau Froide  |  ECS — Eau Chaude Sanitaire")

    px=10*mm; py=40*mm; pw=245*mm; ph=185*mm
    sc_x=(pw-30*mm)/AXES_X_MM[-1]; sc_y=(ph-25*mm)/AXES_Y_MM[-1]
    sc=min(sc_x,sc_y)
    agw=AXES_X_MM[-1]*sc; agh=AXES_Y_MM[-1]*sc
    ox=px+15*mm+(pw-30*mm-agw)/2
    oy=py+12*mm+(ph-25*mm-agh)/2
    c.setFillColor(BLANC); c.setStrokeColor(GRIS4); c.setLineWidth(0.3)
    c.rect(px,py,pw,ph,fill=1,stroke=1)
    xs,ys=draw_grille(c,ox,oy,sc)

    equips=get_equips(code,cote)
    for reseau in ["EU","EV","EF","ECS"]:
        draw_canalisations(c,xs,ys,equips,reseau)

    offsets={"EU":(0,0),"EV":(6,0),"EF":(0,6),"ECS":(6,6)}
    compteur={}
    for eq in equips:
        ax_x,ax_y,reseau,sym,lbl,ct = eq
        ex=xs[min(ax_x,len(xs)-1)]; ey=ys[min(ax_y,len(ys)-1)]
        dx,dy=offsets.get(reseau,(0,0)); ex+=dx; ey+=dy
        draw_sym(c,ex,ey,reseau,sym)
        n=compteur.get(reseau,1)
        col=reseau_color(reseau)
        c.setFillColor(BLANC); c.setStrokeColor(col); c.setLineWidth(0.4)
        c.circle(ex+5,ey+5,3.2,fill=1,stroke=1)
        c.setFillColor(col); c.setFont("Helvetica-Bold",4)
        c.drawCentredString(ex+5,ey+3.5,str(n))
        compteur[reseau]=n+1
        c.setFillColor(GRIS3); c.setFont("Helvetica",3.8)
        c.drawString(ex+9,ey-1,f"{ct:+.2f}")

    # Legende
    lx=px+pw+8*mm; lw_leg=44*mm
    c.setFillColor(BLANC); c.setStrokeColor(GRIS4); c.setLineWidth(0.3)
    c.rect(lx,py,lw_leg,h-py-38*mm,fill=1,stroke=1)
    c.setFillColor(VERT); c.rect(lx,h-38*mm,lw_leg,7*mm,fill=1,stroke=0)
    c.setFillColor(BLANC); c.setFont("Helvetica-Bold",7)
    c.drawCentredString(lx+lw_leg/2, h-35*mm, "LEGENDE")
    reseaux=[("EU","Eaux Usees",EU_COL),("EV","Eaux Vannes",EV_COL),
             ("EF","Eau Froide",EF_COL),("ECS","Eau Chaude San.",ECS_COL)]
    y_l=h-50*mm
    c.setFont("Helvetica-Bold",6); c.setFillColor(GRIS1)
    c.drawString(lx+3*mm,y_l+4*mm,"RESEAUX")
    for code_r,nom_r,col_r in reseaux:
        y_l-=8*mm
        c.setStrokeColor(col_r); c.setLineWidth(2)
        c.line(lx+3*mm,y_l+2,lx+12*mm,y_l+2)
        c.setFillColor(col_r); c.setFont("Helvetica-Bold",5.5)
        c.drawString(lx+14*mm,y_l,code_r)
        c.setFillColor(GRIS2); c.setFont("Helvetica",5)
        c.drawString(lx+14*mm,y_l-5,nom_r)
    y_l-=14*mm
    c.setFont("Helvetica-Bold",6); c.setFillColor(GRIS1)
    c.drawString(lx+3*mm,y_l,"SYMBOLES")
    syms=[("chute","Colonne de chute",EU_COL),("siphon","Siphon de sol",EU_COL),
          ("wc","WC / Cuvette",EV_COL),("lavabo","Lavabo",EF_COL),
          ("evier","Evier",EF_COL),("douche","Douche",EF_COL),
          ("regard","Regard de visite",EU_COL),("montante","Col. montante",EF_COL)]
    for sym_t,nom_s,col_s in syms:
        y_l-=9*mm
        if y_l<py+55*mm: break
        draw_sym(c,lx+7*mm,y_l+2,col_s,sym_t,r=3)
        c.setFillColor(GRIS2); c.setFont("Helvetica",5)
        c.drawString(lx+14*mm,y_l,nom_s)

    cartouche(c,w,h,label,pg,total)
    c.showPage()

def generer_plans_plu(output_path, params=None):
    c=pdfcanvas.Canvas(output_path,pagesize=A3L)
    c.setTitle("Dossier PLU — Sakho R+8"); c.setAuthor("Tijan AI")
    total=len(NIVEAUX)
    for pg,(code,label,cote,courant) in enumerate(NIVEAUX,start=1):
        pl_plu(c,code,label,cote,courant,pg,total)
    c.save(); return output_path
