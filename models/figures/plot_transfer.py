"""Draw the two-domain forecast comparison from the public aggregate summary."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

def draw(summary, output):
    document=json.loads(summary.read_bytes())
    domains=document['domains']
    colors={'wrist':'#256982','rat':'#af6033'}
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10.5,'pdf.fonttype':42,'axes.spines.top':False,
                         'axes.spines.right':False,'axes.spines.left':False,'axes.spines.bottom':False,
                         'xtick.color':'#34464d','ytick.color':'#25373e','text.color':'#142a33','axes.labelcolor':'#34464d'})
    fig=plt.figure(figsize=(10.35,5.15),facecolor='white')
    a,b=fig.subplots(1,2,gridspec_kw={'width_ratios':[1.38,1]})
    fig.subplots_adjust(left=.23,right=.965,bottom=.26,top=.72,wspace=.48)
    fig.text(.045,.935,'One movement model, two tracking tasks',fontsize=19,fontweight='bold')
    fig.text(.045,.864,'Quarter-second displacement forecasts for a human wrist and a rat crossing a track',fontsize=12)
    for y,(key,label) in enumerate([('joint_27181','Shared attention model'),('solo32_27181','Single task, equal exposure'),
                                    ('solo64_27181','Single task, equal updates'),('ridge','Best linear baseline')]):
        for domain,offset in [('wrist',.14),('rat',-.14)]:
            scores=domains[domain]['macro_mae_cm']
            value=min(scores['ridge_cm'],scores['ridge_log']) if key=='ridge' else scores[key]
            height=3-y+offset
            a.barh(height,value,height=.22,color=colors[domain],zorder=2)
            a.text(value+.045,height,f'{value:.2f}',va='center',fontsize=9.5)
    a.set_yticks([3,2,1,0],['Shared attention model','Single task, equal exposure','Single task, equal updates','Best linear baseline'])
    a.set_xlim(0,2.22);a.set_ylim(-.42,3.42);a.xaxis.set_major_locator(MultipleLocator(.5))
    a.set_title('Mean absolute error',loc='left',fontsize=12.5,fontweight='bold',pad=12)
    a.set_xlabel('Centimetres · smaller is better',labelpad=7);a.grid(axis='x',alpha=.2,zorder=0)
    b.axvline(0,color='#566970',lw=1,ls='--');b.set_ylim(-.5,1.5)
    for idx,domain in [(1,'wrist'),(0,'rat')]:
        pair=domains[domain]['paired_joint_minus_comparator_cm']['solo32_27181'];e=pair['mean'];lo,hi=pair['percentile_95']
        b.errorbar(e,idx,xerr=[[e-lo],[hi-e]],color=colors[domain],fmt='o',capsize=4,markersize=7,lw=2)
        b.text((lo+hi)/2,idx+.21,f'{e:+.3f} cm',ha='center',fontsize=10)
    b.set_yticks([1,0],['Wrist','Rat']);b.set_xlim(-.16,.046);b.xaxis.set_major_locator(MultipleLocator(.05))
    b.set_title('Shared minus single task',loc='left',fontsize=12.5,fontweight='bold',pad=12)
    b.set_xlabel('Difference in error, cm',labelpad=7);b.grid(axis='x',alpha=.16)
    for ax in (a,b):ax.tick_params(axis='y',length=0,pad=5);ax.tick_params(axis='x',length=3)
    fig.text(.047,.157,'●  Wrist',color=colors['wrist'],fontweight='bold');fig.text(.14,.157,'●  Rat',color=colors['rat'],fontweight='bold')
    fig.text(.045,.095,'Left: each of six wrist acquisition groups or nine rat trips has equal weight within its task.',fontsize=9.7)
    fig.text(.045,.044,'Right: paired differences with equal training exposure. Both descriptive 95% group-resampling intervals include zero.',fontsize=9.7)
    output.mkdir(parents=True,exist_ok=True)
    for ext in ['png','pdf']:
        fig.savefig(output/('transfer-comparison.'+ext),dpi=180,metadata={'Creator':'NeuroTranslation'})
    plt.close(fig)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('summary',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();draw(a.summary,a.output)
