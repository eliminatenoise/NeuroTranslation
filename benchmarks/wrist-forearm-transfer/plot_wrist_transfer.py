"""Compare forecast-time input conditions within one frozen wrist correction study."""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator


def draw(source, output):
    data = json.loads(source.read_text(encoding="utf-8"))
    scores = data["participant_balanced"]
    assert data["development_support"]["common_trials"] == 960
    assert data["development_support"]["participants"] == 3
    axes = [None, "extension", "radial_deviation"]

    def rmse(method, axis):
        score = scores[method]
        return (score if axis is None else score["axes"][axis])["rmse_deg"]

    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 10, "text.color":"#182e36",
                         "axes.labelcolor":"#182e36", "xtick.color":"#344e57", "ytick.color":"#182e36"}):
        fig, ax = plt.subplots(figsize=(8.7, 4.15))
        fig.subplots_adjust(left=.23, right=.94, bottom=.27, top=.72)
        fig.text(.045,.929,"Forearm signals and wrist-forecast error",weight="bold",fontsize=17)
        fig.text(.045,.857,"Change from the motion-only correction, in degrees of root mean square error.",fontsize=10.5)
        colors = ["#00677d", "#aa4c29"]
        conditions = [("motion_emg_correction", "Same-trial EMG", "o"), ("rotated_emg_correction", "Next-trial EMG", "s")]
        for index, (method, label, marker) in enumerate(conditions):
            for row, axis in enumerate(axes):
                y = 2-row + (.16 if index == 0 else -.16)
                diff = rmse(method,axis)-rmse("motion_correction",axis)
                ax.hlines(y,0,diff,color=colors[index],linewidth=1.2)
                ax.scatter(diff,y,s=48,marker=marker,edgecolor=colors[index],facecolor=colors[index] if index==0 else "white",
                           zorder=3,label=label if row==0 else None)
                ax.annotate(f"{diff:+.3f}°",(diff,y),xytext=(-7 if diff<0 else 7,0),
                            textcoords="offset points",ha="right" if diff<0 else "left",va="center",color=colors[index])
        ax.set(xlim=(-.25,.41),ylim=(-.55,2.55),yticks=[2,1,0],yticklabels=["Both axes","Flexion / extension","Radial / ulnar"])
        ax.axvline(0,color="#495c63",lw=1)
        ax.xaxis.set_major_locator(MultipleLocator(.1))
        ax.grid(axis="x",color="#d8e0dd",lw=.7)
        ax.set_axisbelow(True)
        ax.tick_params(length=0,pad=6)
        ax.spines[:].set_visible(False)
        ax.set_xlabel("Change in error (°)     ·     Negative values indicate lower error",labelpad=7)
        ax.legend(loc="lower left",bbox_to_anchor=(-.01,1.02),ncol=2,frameon=False,borderaxespad=0,handletextpad=.3)
        fig.text(.045,.085,"960 pointing trials, three previously evaluated development participants. Prediction inputs end 250 ms",fontsize=9)
        fig.text(.045,.038,"before the target on the stored clock. The six reserved test participants remain unevaluated.",fontsize=9)
        fig.savefig(output,dpi=180,metadata={"Software":"Matplotlib"})
        plt.close(fig)


if __name__ == "__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("source",type=Path)
    cli.add_argument("output",type=Path)
    args=cli.parse_args()
    draw(args.source,args.output)
