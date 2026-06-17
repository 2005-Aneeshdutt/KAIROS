import json, os, tempfile
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import pandas as pd
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

ROOT = Path(r"c:/Users/anees/OneDrive/Desktop/epsilon")
ART = ROOT / "ml" / "artifacts"
ASSETS = Path(tempfile.mkdtemp(prefix="deck_"))

BG      = "#0F172A"; PANEL = "#1E293B"; TEXT = "#E2E8F0"; MUTED = "#94A3B8"
ACCENT  = "#E6007E"
BLUE="#3B82F6"; GREEN="#22C55E"; AMBER="#F59E0B"; RED="#EF4444"
def H(x): return RGBColor.from_string(x.lstrip("#"))

plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": TEXT,
                     "axes.edgecolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED})

def save(fig, name):
    p = ASSETS / name
    fig.savefig(p, dpi=200, facecolor=BG, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig); return str(p)

def chart_buckets():
    fig, ax = plt.subplots(figsize=(6.6, 4.4)); fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
    cells = [((0,1),GREEN,"Sure Things","buys anyway → SAVE $"),
             ((1,1),BLUE,"Persuadables","spend changes outcome → TARGET"),
             ((0,0),AMBER,"Sleeping Dogs","contact backfires → SUPPRESS"),
             ((1,0),RED,"Lost Causes","won't act → SKIP")]
    for (cx,cy),col,t,s in cells:
        ax.add_patch(FancyBboxPatch((cx+0.04,cy+0.04),0.92,0.92,
            boxstyle="round,pad=0.0,rounding_size=0.04", fc=col, ec="none", alpha=0.92))
        ax.text(cx+0.5,cy+0.62,t,ha="center",color="white",fontsize=14,fontweight="bold")
        ax.text(cx+0.5,cy+0.40,s,ha="center",color="white",fontsize=8.5,alpha=0.95)
    ax.set_xlim(0,2); ax.set_ylim(0,2); ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.text(1,2.12,"Buys WITHOUT marketing  →",ha="center",color=MUTED,fontsize=9)
    ax.text(-0.1,1,"Buys WITH marketing  →",va="center",rotation=90,color=MUTED,fontsize=9)
    return save(fig,"buckets.png")

def chart_rct():
    df = pd.read_parquet(ART/"scores.parquet")
    order=["Persuadable","Sure Thing","Sleeping Dog","Lost Cause"]
    tr=[]; cr=[]
    for b in order:
        g=df[df.bucket==b]
        tr.append(100*g[g.treatment==1].conversion.mean())
        cr.append(100*g[g.treatment==0].conversion.mean())
    import numpy as np
    x=np.arange(len(order)); w=0.36
    fig,ax=plt.subplots(figsize=(7.6,4.2)); fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
    ax.bar(x-w/2,cr,w,label="Control (not contacted)",color=MUTED)
    ax.bar(x+w/2,tr,w,label="Contacted",color=ACCENT)
    for i in range(len(order)):
        ax.text(i-w/2,cr[i]+0.04,f"{cr[i]:.2f}%",ha="center",color=TEXT,fontsize=8)
        ax.text(i+w/2,tr[i]+0.04,f"{tr[i]:.2f}%",ha="center",color=TEXT,fontsize=8)
    ax.annotate("contact LOWERS\nconversion",xy=(2+w/2+0.09,0.42),xytext=(2.62,2.05),
        color=AMBER,fontsize=9,fontweight="bold",ha="center",
        arrowprops=dict(arrowstyle="->",color=AMBER,lw=1.6,
                        connectionstyle="arc3,rad=-0.15"))
    ax.set_xticks(x); ax.set_xticklabels(order,color=TEXT,fontsize=10)
    ax.set_ylabel("Conversion rate",color=MUTED); ax.set_ylim(0,3.0)
    for sp in ["top","right"]: ax.spines[sp].set_visible(False)
    ax.legend(facecolor=PANEL,edgecolor="none",labelcolor=TEXT,fontsize=9,loc="upper right")
    ax.set_title("Hillstrom RCT · 64,000 customers · treated vs. held-out control",
                 color=MUTED,fontsize=9,loc="left")
    return save(fig,"rct.png")

def chart_qini():
    q=json.load(open(ART/"qini.json"))
    fig,ax=plt.subplots(figsize=(5.6,4.2)); fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
    ax.plot(q["x"],q["y"],color=ACCENT,lw=2.4,label="Conductor (uplift)")
    ax.plot([0,1],[0,1],color=MUTED,lw=1.4,ls="--",label="Random targeting")
    ax.fill_between(q["x"],q["y"],[xx for xx in q["x"]],color=ACCENT,alpha=0.12)
    ax.set_xlim(0,1); ax.set_ylim(0,1.05)
    ax.set_xlabel("Customers targeted (by predicted uplift)",color=MUTED,fontsize=9)
    ax.set_ylabel("Incremental responders captured",color=MUTED,fontsize=9)
    for sp in ["top","right"]: ax.spines[sp].set_visible(False)
    ax.legend(facecolor=PANEL,edgecolor="none",labelcolor=TEXT,fontsize=9,loc="lower right")
    ax.text(0.04,0.92,f"AUUC +{q['auuc']:.3f}",color=ACCENT,fontsize=13,fontweight="bold")
    return save(fig,"qini.png")

def chart_twoworld():
    import numpy as np
    cats=["Messages sent","Budget spent ($)","Annoyance risk (%)"]
    without=[5,19,45]; with_=[1,13.84,4]
    x=np.arange(len(cats)); w=0.36
    fig,ax=plt.subplots(figsize=(6.8,4.0)); fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
    ax.bar(x-w/2,without,w,label="Without Conductor",color=RED,alpha=0.85)
    ax.bar(x+w/2,with_,w,label="With Conductor",color=GREEN,alpha=0.9)
    for i,(a,b) in enumerate(zip(without,with_)):
        ax.text(i-w/2,a+0.6,f"{a}",ha="center",color=TEXT,fontsize=9)
        ax.text(i+w/2,b+0.6,f"{b}",ha="center",color=TEXT,fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(cats,color=TEXT,fontsize=9.5)
    ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.legend(facecolor=PANEL,edgecolor="none",labelcolor=TEXT,fontsize=9,loc="upper right")
    ax.set_title("Same shopper · one perfectly-timed touch vs. five blasts",color=MUTED,fontsize=9,loc="left")
    return save(fig,"twoworld.png")

def chart_arch():
    fig,ax=plt.subplots(figsize=(11.5,2.3)); fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
    steps=[("Identity","stitch cross-device"),("Causal","uplift / CATE"),
           ("Orchestrate","channel + timing"),("Optimize","budget knapsack"),
           ("Generate","Claude message"),("Measure","Qini · real RCT")]
    n=len(steps); bw=1.55; gap=0.36; x=0
    centers=[]
    for i,(t,s) in enumerate(steps):
        col=ACCENT if i in (1,5) else PANEL
        ax.add_patch(FancyBboxPatch((x,0.6),bw,0.95,boxstyle="round,pad=0.02,rounding_size=0.08",
            fc=col,ec=MUTED,lw=0.8))
        ax.text(x+bw/2,1.22,t,ha="center",color="white",fontsize=11,fontweight="bold")
        ax.text(x+bw/2,0.9,s,ha="center",color=TEXT if col==ACCENT else MUTED,fontsize=8)
        centers.append(x+bw/2)
        if i<n-1:
            ax.add_patch(FancyArrowPatch((x+bw,1.07),(x+bw+gap,1.07),arrowstyle="-|>",
                mutation_scale=14,color=MUTED,lw=1.4))
        x+=bw+gap
    ax.add_patch(FancyArrowPatch((centers[-1],0.55),(centers[0],0.55),
        connectionstyle="arc3,rad=0.25",arrowstyle="-|>",mutation_scale=14,color=ACCENT,lw=1.4))
    ax.text((centers[0]+centers[-1])/2,-0.15,"closed feedback loop",ha="center",color=ACCENT,fontsize=9)
    ax.set_xlim(-0.2,x); ax.set_ylim(-0.4,1.8); ax.axis("off")
    return save(fig,"arch.png")

imgs = {"buckets":chart_buckets(),"rct":chart_rct(),"qini":chart_qini(),
        "twoworld":chart_twoworld(),"arch":chart_arch()}
print("charts done")

prs=Presentation(); prs.slide_width=Inches(13.333); prs.slide_height=Inches(7.5)
SW,SH=prs.slide_width,prs.slide_height
BLANK=prs.slide_layouts[6]
FONT="Segoe UI"

def slide():
    s=prs.slides.add_slide(BLANK)
    r=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,0,0,SW,SH)
    r.fill.solid(); r.fill.fore_color.rgb=H(BG); r.line.fill.background()
    r.shadow.inherit=False
    s.shapes._spTree.remove(r._element); s.shapes._spTree.insert(2,r._element)
    return s

def txt(s,l,t,w,h,text,size,color=TEXT,bold=False,align=PP_ALIGN.LEFT,font=FONT,anchor=MSO_ANCHOR.TOP):
    tb=s.shapes.add_textbox(l,t,w,h); tf=tb.text_frame; tf.word_wrap=True; tf.vertical_anchor=anchor
    p=tf.paragraphs[0]; p.alignment=align
    run=p.add_run(); run.text=text
    f=run.font; f.size=Pt(size); f.bold=bold; f.name=font; f.color.rgb=H(color)
    return tb

def accent_bar(s,l=Inches(0.7),t=Inches(0.62),w=Inches(0.13),h=Inches(0.55)):
    r=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,l,t,w,h)
    r.fill.solid(); r.fill.fore_color.rgb=H(ACCENT); r.line.fill.background(); r.shadow.inherit=False
    return r

def heading(s,title,kicker=None):
    accent_bar(s)
    if kicker: txt(s,Inches(0.95),Inches(0.5),Inches(11),Inches(0.3),kicker.upper(),12,ACCENT,bold=True)
    txt(s,Inches(0.95),Inches(0.78),Inches(11.6),Inches(0.9),title,30,TEXT,bold=True)

def bullets(s,items,l=Inches(0.95),t=Inches(2.0),w=Inches(6.0),size=16,gap=True):
    tb=s.shapes.add_textbox(l,t,w,Inches(4.5)); tf=tb.text_frame; tf.word_wrap=True
    for i,it in enumerate(items):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph()
        p.space_after=Pt(14 if gap else 6)
        r1=p.add_run(); r1.text="▪  "; r1.font.color.rgb=H(ACCENT); r1.font.size=Pt(size); r1.font.bold=True; r1.font.name=FONT
        r2=p.add_run(); r2.text=it; r2.font.color.rgb=H(TEXT); r2.font.size=Pt(size); r2.font.name=FONT
    return tb

def footer(s,n):
    txt(s,Inches(0.7),Inches(7.05),Inches(6),Inches(0.3),"Epsilon Conductor",10,MUTED)
    txt(s,Inches(11.5),Inches(7.05),Inches(1.2),Inches(0.3),str(n),10,MUTED,align=PP_ALIGN.RIGHT)

def pic(s,path,l,t,w):
    return s.shapes.add_picture(path,l,t,width=w)

def placeholder(s,l,t,w,h,label):
    r=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,l,t,w,h)
    r.fill.solid(); r.fill.fore_color.rgb=H(PANEL); r.line.color.rgb=H(MUTED); r.line.width=Pt(0.75); r.shadow.inherit=False
    tf=r.text_frame; tf.word_wrap=True; p=tf.paragraphs[0]; p.alignment=PP_ALIGN.CENTER
    run=p.add_run(); run.text="🖼  "+label; run.font.color.rgb=H(MUTED); run.font.size=Pt(12); run.font.name=FONT
    return r

s=slide()
accent_bar(s,Inches(0.7),Inches(2.6),Inches(0.18),Inches(2.0))
txt(s,Inches(1.05),Inches(2.5),Inches(11),Inches(1.2),"Epsilon Conductor",54,TEXT,bold=True)
txt(s,Inches(1.08),Inches(3.7),Inches(10.8),Inches(0.7),
    "Causal marketing decisioning — spend only where it changes the outcome.",20,MUTED)
txt(s,Inches(1.08),Inches(4.5),Inches(10.8),Inches(0.5),
    "We don't predict who will buy. We prove whose decision marketing actually changed.",15,ACCENT)
txt(s,Inches(1.05),Inches(6.5),Inches(11),Inches(0.4),"Epsilon Hackathon  ·  Theme 02: seamless journeys, clear measures of success",12,MUTED)

s=slide(); heading(s,"Most marketing pays for sales it already had","The problem")
bullets(s,[
 "Conventional targeting ranks customers by propensity — who is likely to buy.",
 "But most high-propensity buyers would have bought anyway — the discount is wasted margin.",
 "Worse: some customers convert LESS when contacted — and nobody measures it.",
 "No system answers the only question that matters: where does spend change the decision?"
], t=Inches(2.1), w=Inches(11.4))
footer(s,2)

s=slide(); heading(s,"Four buckets, one question","The insight")
pic(s,imgs["buckets"],Inches(6.6),Inches(1.9),Inches(6.2))
bullets(s,[
 "Persuadables — spend here.",
 "Sure Things — buy anyway, save the budget.",
 "Sleeping Dogs — contact backfires, stay silent.",
 "Lost Causes — won't act, skip.",
], t=Inches(2.4), w=Inches(5.4))
txt(s,Inches(0.95),Inches(5.6),Inches(5.4),Inches(1),
    "Only the Persuadables are worth a dollar — typically a small slice of the base.",14,MUTED)
footer(s,3)

s=slide(); heading(s,"A closed decisioning loop","How it works")
pic(s,imgs["arch"],Inches(0.8),Inches(2.4),Inches(11.7))
txt(s,Inches(0.95),Inches(5.2),Inches(11.4),Inches(1),
    "Identity → causal uplift → channel orchestration → budget allocation → generative message → causal measurement — feeding back into the next decision.",15,MUTED)
footer(s,4)

s=slide(); heading(s,"We model uplift, not propensity","The causal engine")
pic(s,imgs["qini"],Inches(7.0),Inches(2.0),Inches(5.6))
bullets(s,[
 "EconML X-Learner estimates each customer's incremental effect (CATE).",
 "Trained on the Hillstrom RCT — 64,000 real, randomized customers.",
 "Validated with Qini / AUUC — the right metric for incrementality, not accuracy.",
 "Negative-uplift customers fall out automatically as Sleeping Dogs.",
], t=Inches(2.1), w=Inches(5.9))
footer(s,5)

s=slide(); heading(s,"Live, per-shopper decisioning","The product")
bullets(s,[
 "S-Learner scores live behaviour (9 signals) in real time.",
 "Per-product intent across the whole consideration set.",
 "Cross-device identity — cart & points follow the shopper.",
 "Next-best-action: right channel, right time — or deliberate silence.",
], t=Inches(2.1), w=Inches(5.7))
placeholder(s,Inches(6.9),Inches(2.0),Inches(5.7),Inches(4.2),"Paste screenshot: Console — live shopper view\n(/console · two-world economics + per-product cards)")
footer(s,6)

s=slide(); heading(s,"Restraint, measured in dollars","Economics")
pic(s,imgs["twoworld"],Inches(6.7),Inches(2.0),Inches(6.0))
bullets(s,[
 "Revenue GENERATED — incremental sales from Persuadables.",
 "Budget SAVED — not discounting Sure Things who pay full price.",
 "Revenue PROTECTED — not annoying Sleeping Dogs.",
 "Minimum Effective Dose — the smallest discount that still converts.",
], t=Inches(2.1), w=Inches(5.6))
footer(s,7)

s=slide(); heading(s,"Proof on a real experiment — measured, not modelled","The proof")
pic(s,imgs["rct"],Inches(5.6),Inches(1.85),Inches(7.2))
bullets(s,[
 "Persuadables convert ~2.5× higher when contacted.",
 "Sure Things barely move — discounting them is waste.",
 "Sleeping Dogs: contact CUT conversion by 1.83 points.",
], t=Inches(2.2), w=Inches(4.9), size=15)
txt(s,Inches(0.95),Inches(5.4),Inches(4.7),Inches(1.5),
    "That is the spend every propensity model makes blind — and we can prove it on a real RCT.",14,ACCENT)
footer(s,8)

s=slide(); heading(s,"What's actually new","Differentiation")
rows=[("","Conventional martech","Epsilon Conductor"),
 ("Target signal","Propensity — who'll buy","Uplift / CATE — whose mind we change"),
 ("Live scoring","Rules or stale score","S-Learner on live behaviour"),
 ("Channel","Same blast","Thompson bandit + timing policy"),
 ("Budget","Top-N by score","0/1 knapsack, marginal-ROI knee"),
 ("Discount","Blanket 20%","Minimum effective dose"),
 ("Success metric","Clicks / conversions","Qini + real RCT proof"),
 ("Restraint","Not modelled","Generated · Saved · Protected ($)")]
tbl=s.shapes.add_table(len(rows),3,Inches(0.95),Inches(1.95),Inches(11.4),Inches(4.6)).table
tbl.columns[0].width=Inches(2.6); tbl.columns[1].width=Inches(4.2); tbl.columns[2].width=Inches(4.6)
for ri,row in enumerate(rows):
    for ci,val in enumerate(row):
        c=tbl.cell(ri,ci); c.fill.solid()
        c.fill.fore_color.rgb=H(ACCENT) if ri==0 else (H("#172033") if ri%2 else H(PANEL))
        tfc=c.text_frame; tfc.word_wrap=True; p=tfc.paragraphs[0]
        run=p.add_run(); run.text=val
        run.font.size=Pt(12 if ri else 12.5); run.font.name=FONT
        run.font.bold = (ri==0 or ci==2)
        run.font.color.rgb=H("#FFFFFF") if ri==0 else (H(TEXT) if ci==2 else H(MUTED))
footer(s,9)

s=slide(); heading(s,"Built on Epsilon's own playbook","We did the homework")
bullets(s,[
 "Dell “Unfrozen”: split dormant customers into Nappers & Dormants — and chose to let some go.",
 "That restraint drove ~6% more revenue and ~8% higher margin. Letting go IS the thesis.",
 "Walgreens: a decade of per-person, cross-channel journeys.",
 "Conductor is the causal layer on top of CORE ID + PeopleCloud — every touch made provably worth it.",
], t=Inches(2.1), w=Inches(11.4))
footer(s,10)

s=slide(); heading(s,"Technology","Under the hood")
stack=[("Causal ML","EconML X-Learner · S-Learner · scikit-learn"),
 ("Orchestration","Thompson-sampling contextual bandit"),
 ("Optimization","PuLP 0/1 knapsack · marginal-ROI knee"),
 ("Data / proof","Hillstrom RCT · Qini / AUUC"),
 ("Backend","FastAPI · real-time SSE"),
 ("Frontend","Next.js · Recharts"),
 ("Generative","Claude — per-decision explanations")]
tb=s.shapes.add_textbox(Inches(0.95),Inches(2.0),Inches(11.4),Inches(4.5)); tf=tb.text_frame; tf.word_wrap=True
for i,(k,v) in enumerate(stack):
    p=tf.paragraphs[0] if i==0 else tf.add_paragraph(); p.space_after=Pt(12)
    a=p.add_run(); a.text=f"{k}   "; a.font.bold=True; a.font.size=Pt(16); a.font.color.rgb=H(ACCENT); a.font.name=FONT
    b=p.add_run(); b.text=v; b.font.size=Pt(16); b.font.color.rgb=H(TEXT); b.font.name=FONT
footer(s,11)

s=slide()
accent_bar(s,Inches(0.7),Inches(2.7),Inches(0.18),Inches(1.7))
txt(s,Inches(1.05),Inches(2.7),Inches(11),Inches(1.2),"We don't just market smarter.",40,TEXT,bold=True)
txt(s,Inches(1.05),Inches(3.7),Inches(11),Inches(1.2),"We prove it.",40,ACCENT,bold=True)
txt(s,Inches(1.08),Inches(5.2),Inches(11),Inches(0.6),
    "Seamless across every channel and device · every decision explainable · every dollar tied to a measured outcome.",15,MUTED)
txt(s,Inches(1.05),Inches(6.6),Inches(11),Inches(0.4),"Thank you.",16,TEXT,bold=True)

out=ROOT/"docs"/"Epsilon_Conductor.pptx"
prs.save(str(out))
print("SAVED:", out, "slides:", len(prs.slides._sldIdLst))
