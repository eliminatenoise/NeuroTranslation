"""Rebuild the two figures from the published aggregate data. Requires Matplotlib."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

HERE = Path(__file__).resolve().parent


def draw():
    data = json.loads((HERE/'evidence.json').read_bytes())
    ink,teal,rust,purple = '#233b3c','#126861','#ad4f29','#685684'
    plt.rcParams.update({'font.family':'Liberation Sans','font.size':9.5,'text.color':ink,'axes.labelcolor':ink,'xtick.color':ink,'ytick.color':ink,'axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,'axes.spines.bottom':False,'svg.fonttype':'none','svg.hashsalt':'movement-forecast-supplement-v1'})
    times=list(range(50,601,50))
    fig,ax=plt.subplots(figsize=(7.35,2.64));fig.subplots_adjust(left=.09,right=.96,top=.83,bottom=.23)
    for name,label,color,style in [('ridge','Linear model',purple,':'),('retrieval','Recorded stride match',rust,'--'),('history-only','Movement alone','#798581','-.'),('conditional','Movement and word',teal,'-')]:
        values=data['stride']['overall'][name]['bodyCurveMm']
        ax.plot(times,values,label=label,color=color,ls=style,lw=2.1 if name=='conditional' else 1.65)
    ax.set(xlim=(40,610),ylim=(0,max(max(data['stride']['overall'][k]['bodyCurveMm']) for k in ['ridge','retrieval','history-only','conditional'])*1.06),xlabel='Time after the last observed pose (ms)',ylabel='Body-marker error (mm)')
    ax.set_xticks([50,150,250,350,450,550,600])
    ax.grid(axis='y',color='#dce3de');ax.legend(loc='lower left',bbox_to_anchor=(-.025,1.02),ncol=4,frameon=False,fontsize=8,columnspacing=1.1,handlelength=2.2)
    fig.savefig(HERE/'stride-curves.svg',metadata={'Date':None});plt.close(fig)

    fig,ax=plt.subplots(figsize=(7.35,2.4));fig.subplots_adjust(left=.095,right=.94,top=.79,bottom=.24)
    for i,r in enumerate(data['track']['rat']):
        a=r['motion_minus_combined'];b=r['earlier_minus_combined']
        ax.plot([a,b],[i,i],color='#b5c1bf',lw=1.7)
        ax.scatter([a],[i],color=teal,marker='o',s=43,zorder=3,label='Gain over movement alone' if i==0 else None)
        ax.scatter([b],[i],color=rust,marker='D',s=32,zorder=4,label='Gain over earlier-trip firing' if i==0 else None)
    ax.set_xlim(-.075,.125);ax.set_ylim(2.48,-.48)
    ax.set_yticks([0,1,2],[r['rat'] for r in data['track']['rat']])
    ax.set_xlabel('Decrease in error with correctly timed firing (cm)')
    ax.xaxis.set_major_locator(MultipleLocator(.025));ax.grid(axis='x',color='#dce3de')
    ax.axvline(0,c=ink,lw=1);ax.legend(loc='lower left',bbox_to_anchor=(-.02,1.03),ncol=2,frameon=False)
    fig.savefig(HERE/'rat-comparisons.svg',metadata={'Date':None});plt.close(fig)

if __name__=='__main__':draw()
