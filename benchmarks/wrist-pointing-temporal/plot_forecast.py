"""Draw the measured error at each movement phase from a frozen WristMotion development report."""
import argparse
from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

def plot(result_path, dest):
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result["edition"] != "wrist-motion-v3-cue-locked-temporal-forecast-r1" or result["nominal_forecast_horizon_samples"] != 128 or result["sample_rate_hz"] != 512:
        raise ValueError("Expected the frozen 250 ms WristMotion development comparison")
    phase = result["by_offset_ticks_participant_balanced"]
    ticks = [384,512,640,768,896,1024]
    if sorted(map(int,phase)) != ticks:
        raise ValueError("All six original time offsets are required")
    time_ms = [t*1000/512 for t in ticks]
    methods = [
        ("persistence", "Last angle", "#526774", ":", "s"),
        ("motion_temporal", "Wrist history", "#17577b", "-", "o"),
        ("combined_temporal", "Wrist history + EEG", "#a14313", "--", "^"),
    ]
    overall = result["participant_balanced"]
    trial_rows = overall["motion_temporal"]["rows"]
    if trial_rows % len(ticks):
        raise ValueError("Expected whole-trial development support")
    axes = [
        ("extension", "Flexion–extension", "#006f66", "o", "-"),
        ("radial_deviation", "Radial–ulnar deviation", "#75548b", "^", "--"),
    ]
    with plt.rc_context({"font.family":"DejaVu Sans","font.size":10,"axes.labelcolor":"#24323b","text.color":"#1c2b34","axes.spines.top":False,"axes.spines.right":False,"axes.spines.left":False,"axes.spines.bottom":False,"savefig.facecolor":"white"}):
        fig, (upper,lower) = plt.subplots(2,1,figsize=(8.7,7.5),sharex=True,gridspec_kw={"height_ratios":[1.2,1]})
        fig.subplots_adjust(left=.11,right=.97,top=.77,bottom=.16,hspace=.40)
        fig.text(.09,.951,"Forecasting wrist angle in a pointing task",fontsize=21,fontweight="bold",va="top")
        fig.text(.09,.892,f"3 development participants   ·   {trial_rows//6:,} trials   ·   two measured wrist axes",fontsize=11)
        for key,label,color,style,marker in methods:
            group = [phase[str(t)][key]["rmse_deg"] for t in ticks]
            upper.plot(time_ms,group,label=label,color=color,ls=style,marker=marker,ms=6,lw=2)
        upper.set_ylim(bottom=0); upper.set_ylabel("RMSE (degrees)")
        upper.set_title("Error at each target time",loc="left",fontweight="bold",fontsize=12,pad=10)
        upper.legend(loc="lower left",bbox_to_anchor=(0,1.15),ncol=3,frameon=False,fontsize=9,borderaxespad=0)
        for axis,label,color,marker,style in axes:
            diff=[phase[str(t)]["combined_temporal"]["axes"][axis]["rmse_deg"]-
                  phase[str(t)]["motion_temporal"]["axes"][axis]["rmse_deg"] for t in ticks]
            lower.plot(time_ms,diff,label=label,color=color,ls=style,marker=marker,ms=5.5,lw=1.8)
        lower.axhline(0,lw=.85,color="#293e49",zorder=0)
        lower.set_title("Change in model error when EEG is added",loc="left",fontweight="bold",fontsize=12,pad=22)
        lower.legend(loc="lower left",bbox_to_anchor=(0,1.0),ncol=3,frameon=False,fontsize=9,borderaxespad=0)
        lower.set_ylabel("Change in RMSE (degrees)"); lower.set_xlabel("Time since the single-target cue (ms)",labelpad=8)
        lower.set_xticks(time_ms,[str(int(t)) for t in time_ms])
        for ax in (upper,lower):
            ax.grid(axis="y",color="#d7dfe3",lw=.65);ax.tick_params(length=0,pad=6);ax.yaxis.set_major_locator(MaxNLocator(nbins=5))
        fig.text(.09,.055,"Each forecast uses inputs ending 250 ms earlier on the stored clock. A value below zero in the lower",fontsize=9)
        fig.text(.09,.033,"panel means EEG reduced error on that axis. Data from EEG-EMG-WristMotion v3.",fontsize=9)
        fig.savefig(dest,dpi=200,metadata={"Software":"Matplotlib"});plt.close(fig)

if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("results",type=Path);cli.add_argument("output",type=Path)
    args=cli.parse_args();plot(args.results,args.output)
