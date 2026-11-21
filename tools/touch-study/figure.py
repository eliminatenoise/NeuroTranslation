"""Draw each independent person's change after replacing earlier plate forces."""
import json
from pathlib import Path

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
study=json.loads((REPO/'models/neurotranslate-0.0/joint_alpha/touch/study.json').read_bytes())
paired=next(x['per_person'] for x in study['held']['nll_differences']
            if (x['first'],x['second'])==('joint_true','joint_previous'))
with mpl.rc_context({"font.family":"Liberation Sans","svg.fonttype":"path","svg.hashsalt":"touch-study-figure-v1"}):
    fig,ax=plt.subplots(figsize=(7.3,2.45),layout="constrained")
    values=list(paired.values())
    extent=max(max(abs(x) for x in values),1e-8)
    ax.set_xlim(-1.38*extent,1.38*extent)
    ax.set_ylim(-.65,len(values)-.35)
    ax.set_yticks(range(len(values)),list(paired))
    for i,v in enumerate(values):
        color="#216557" if v<=0 else "#a34d26"
        ax.hlines(i,0,v,color=color,lw=2)
        ax.plot(v,i,'o',color=color,markersize=7)
        ax.annotate(f"{v:+.6f}",(v,i),xytext=(0,9),textcoords="offset points",ha="center",fontsize=9)
    ax.invert_yaxis()
    ax.axvline(0,color="#515f62",lw=1)
    ax.grid(axis="x",color="#d7dddd",lw=.6)
    ax.set_axisbelow(True)
    ax.spines[['top','right','left']].set_visible(False)
    ax.tick_params(axis='y',length=0)
    ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
    ax.set_xlabel("Change in forecast loss (nats per 20 ms interval)")
    fig.savefig(REPO/'docs/touch-feedback/force-timing.svg',metadata={'Date':None,'Title':'Forecast loss with actual force minus loss with earlier-repeat force'})
    plt.close(fig)
    svg = REPO/"docs/touch-feedback/force-timing.svg"
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines())+"\n")
