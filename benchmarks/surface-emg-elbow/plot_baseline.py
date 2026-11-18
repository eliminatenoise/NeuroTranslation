"""Plot aggregate elbow-angle errors from the frozen two-participant pilot."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metrics", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = json.loads(args.metrics.read_bytes())
    methods = ["ridge", "training_mean", "onset_only"]
    labels = ["Surface EMG ridge", "Training mean", "Time from onset"]
    panels = [
        ("HS01 · training fit", "Left dominant arm", result["reference_in_sample"]),
        ("HS02 · development", "Right dominant arm", result["development_held_out_subject"]),
    ]
    plt.rcParams.update({"font.family":"sans-serif","font.sans-serif":["Noto Sans","DejaVu Sans"],
                         "axes.spines.top":False,"axes.spines.right":False,"axes.spines.left":False,
                         "axes.edgecolor":"#b7c2c4","text.color":"#1c3135",
                         "xtick.color":"#50646a","ytick.color":"#1c3135","font.size":10})
    fig, axes = plt.subplots(1, 2, sharey=True, figsize=(8.9, 3.7))
    fig.subplots_adjust(left=.205,right=.975,top=.655,bottom=.225,wspace=.15)
    fig.text(.035,.94,"Predicting elbow angle during hand-to-mouth movement",
             fontsize=17,weight="bold",va="top")
    limit = max(panel["pooled_errors"][m]["rmse"] for _,_,panel in panels for m in methods)
    upper = 10 * (int(limit // 10) + 2)
    for ax, (title, side, panel) in zip(axes, panels):
        pooled = panel["pooled_errors"]
        ax.text(0,1.24,title,fontsize=12,weight="bold",transform=ax.transAxes)
        ax.text(0,1.09,f"{side} · {pooled['rows']:,} frames",fontsize=9,color="#475e63",transform=ax.transAxes)
        ax.set(xlim=(0,upper),ylim=(2.5,-.5),xticks=range(0,upper+1,20),yticks=range(3))
        ax.set_axisbelow(True)
        ax.grid(axis="x",color="#e2e8e8",linewidth=.7)
        ax.tick_params(axis="y",length=0,pad=8)
        ax.tick_params(axis="x",length=3,labelsize=9)
        for i,m in enumerate(methods):
            error=pooled[m]["rmse"]
            ax.barh(i,error,height=.48,color="#197779" if i==0 else "#aebdc0",zorder=2)
            ax.text(error+1,i,f"{error:.1f}°",va="center",fontsize=10,weight="bold")
    axes[0].set_yticklabels(labels)
    fig.text(.205,.101,"Root mean squared error (degrees)",fontsize=10)
    fig.text(.035,.025,"Five repetitions per participant. Data from Lucchetti et al. (2025).",fontsize=9,color="#475e63")
    fig.savefig(args.output,dpi=180,facecolor="white")
    plt.close(fig)

if __name__ == "__main__":
    main()
