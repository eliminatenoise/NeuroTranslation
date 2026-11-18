"""Draw the primary change in angle error with four-person resampling intervals."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def draw(source, output):
    data = json.loads(source.read_text(encoding="utf-8"))
    result = data["primary"]["primary"]
    assert result["people"] == 4 and result["rows"] == 20073
    labels = ["Both axes", "Flexion / extension", "Radial / ulnar"]
    keys = ["two_axis", "extension_deg", "radial_deviation_deg"]
    values = [result["two_axis_difference_deg"], *(result["axis_difference_deg"][k] for k in keys[1:])]
    intervals = [result["exploratory_bootstrap_95_percent_deg"][k] for k in keys]
    with plt.rc_context({"font.family":"DejaVu Sans","font.size":10,"text.color":"#19343c",
                         "axes.labelcolor":"#19343c","xtick.color":"#3f5359","ytick.color":"#19343c"}):
        fig, ax = plt.subplots(figsize=(8.4,4.1))
        fig.subplots_adjust(left=.235,right=.94,bottom=.29,top=.7)
        fig.text(.04,.91,"What did earlier forearm activity add?",size=17,weight="bold")
        fig.text(.04,.83,"Prespecified primary comparison · Change in wrist-angle RMSE with EMG.",size=10.5)
        ax.axvline(0,color="#46565a",lw=1)
        for i,(value,(lo,hi)) in enumerate(zip(values,intervals,strict=True)):
            y=2-i
            color = "#006779" if value < 0 else "#9c4021"
            ax.plot([lo,hi],[y,y],color=color,lw=2,solid_capstyle="butt")
            ax.plot([lo,hi],[y,y],marker="|",linestyle="none",color=color,ms=8)
            ax.scatter([value],[y],s=60,c=color,zorder=3)
            ax.annotate(f"{value:+.2f}°",(value,y),xytext=(0,9),textcoords="offset points",
                        fontsize=10,color=color,ha="center",va="bottom",weight="bold")
        ax.set(xlim=(-5,2),ylim=(-.5,2.6),yticks=[2,1,0],yticklabels=labels,xticks=range(-5,3))
        ax.spines[:].set_visible(False)
        ax.tick_params(length=0,pad=6)
        ax.set_axisbelow(True);ax.grid(axis="x",color="#d7dfdd",lw=.65)
        ax.set_xlabel("Change in error (°)     ·     Negative values indicate lower error",labelpad=6)
        fig.text(.04,.105,"Dots show differences on the same 20,073 target times. Lines show the 2.5th and 97.5th percentiles",size=9)
        fig.text(.04,.06,"from 20,000 paired resamples of four development participants. The intervals are exploratory.",size=9)
        fig.savefig(output,dpi=180,metadata={"Software":"Matplotlib"})
        plt.close(fig)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source",type=Path);parser.add_argument("output",type=Path)
    args=parser.parse_args()
    draw(args.source,args.output)
