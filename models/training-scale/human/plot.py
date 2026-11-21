"""Plot frozen mean errors against the number of training people."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


def plot(results, output):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig, axes = plt.subplots(2,2,figsize=(10.8,7.4),sharex=True,sharey='row')
    sizes = [3,6,12,18]
    colors = {8:'#396BB0',16:'#AD501D',32:'#287769'}
    for col,(regime,limit) in enumerate((('all','all'),('matched432','432'))):
        for row in (0,1):
            ax=axes[row,col]
            for name,linestyle in (('paired','-'),('early','--')):
                for width,color in colors.items():
                    errors = [results['levels'][f'{regime}-{n}-{limit}']['models'][f'{name}_w{width}']['mean'][row] for n in sizes]
                    ax.plot(sizes,errors,marker='o' if name=='paired' else 's',markersize=4.5,
                            color=color,linestyle=linestyle,lw=1.7,zorder=3)
            ax.axhline(results['baselines']['velocity32']['both'][row],color='0.3',linestyle=':',lw=1.6,zorder=2)
            ax.grid(axis='y',lw=.5,color='#D8DCE0',zorder=0)
            ax.set_xticks(sizes)
            if row==1:
                ax.set_xlabel('Training people')
        axes[0,col].set_title('All eligible rotations' if col==0 else '432 rotations at every size',fontweight='bold',pad=12)
    axes[0,0].set_ylabel('Muscle error (µV)')
    axes[1,0].set_ylabel('Marker path error (mm)')
    handles = [Line2D([],[],color=c,lw=3,label=f'Width {w}') for w,c in colors.items()]
    handles += [Line2D([],[],color='#34393C',marker='o',lw=1.7,label='Paired'),
                Line2D([],[],color='#34393C',marker='s',linestyle='--',lw=1.7,label='Mixed early'),
                Line2D([],[],color='#34393C',linestyle=':',lw=1.6,label='Simple forecast')]
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.015),ncol=6,frameon=False,fontsize=10)
    fig.subplots_adjust(left=.10,right=.98,bottom=.16,top=.91,wspace=.15,hspace=.16)
    fig.savefig(output,dpi=160,facecolor='white',bbox_inches='tight',pad_inches=.22)
    plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('results',type=Path);p.add_argument('output',type=Path)
    args=p.parse_args();plot(json.loads(args.results.read_text()),args.output)
