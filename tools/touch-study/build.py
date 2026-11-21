"""Build the touch study article from verified aggregate scores and the shipped checkpoint."""
import argparse
from html import escape
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MODEL = REPO / "models/neurotranslate-0.0/joint_alpha"
TOUCH = MODEL/"touch"
OUT = REPO / "docs/touch-feedback"

METHODS = {
    "joint_true":"Eight-task model · recorded force",
    "joint_previous":"Eight-task model · previous slide’s force",
    "touch_only_true":"Touch-only model · recorded force",
    "touch_only_previous":"Touch-only model · previous slide’s force",
    "with_true_force":"Simple model · recorded force",
    "with_previous_repeat_force":"Simple model · previous slide’s force",
    "phase_and_spikes":"Simple model · time and earlier spikes",
    "training_rate":"Average training rate",
}
SOURCE="https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/neurotranslate-0.0/joint_alpha/touch"
DOWNLOAD="https://github.com/eliminatenoise/NeuroTranslation/raw/refs/heads/main/models/neurotranslate-0.0.zip"
PAPER="https://pmc.ncbi.nlm.nih.gov/articles/PMC8169108/"
DATA="https://zenodo.org/records/4818439"

def table(caption, headers, rows):
    h="".join(f'<th scope="col">{escape(str(v))}</th>' for v in headers)
    def row(values):
        return '<tr><th scope="row">'+escape(str(values[0]))+'</th>'+''.join('<td>'+escape(str(v))+'</td>' for v in values[1:])+'</tr>'
    return f'<div class="scroll" tabindex="0" role="region" aria-label="{escape(caption)}"><table><caption>{escape(caption)}</caption><thead><tr>{h}</tr></thead><tbody>'+''.join(row(x) for x in rows)+'</tbody></table></div>'

def render():
    study=json.loads((TOUCH/'study.json').read_bytes())
    held=study["held"]
    people=held['individuals']
    assert held['invalid_targets'] == 1
    ranking=sorted(held['equal_person'], key=lambda k:held['equal_person'][k]['poisson_nll'])
    best=ranking[0]
    totals=sum(p['observed_spikes'] for p in people)
    valid=sum(p['valid_targets'] for p in people)
    paired=next(x for x in held['nll_differences'] if (x['first'],x['second'])==('joint_true','joint_previous'))
    lower=sum(x<0 for x in paired['per_person'].values())
    lo,hi=paired['person_bootstrap_95pct']
    title='What a fingertip nerve sends as glass slides'
    lead=f'The experiment recorded {totals:,} spikes in {valid:,} test intervals across three people. Giving the shared model the force from the actual slide improved its forecast for {lower} of them compared with giving it the force from the previous slide.'
    scores=table('Average loss for each person and across people', ['Forecast',*[p['person'] for p in people],'Equal-person mean'],[
        [METHODS[key],*[f"{p['methods'][key]['poisson_nll']:.5f}" for p in people],f"{held['equal_person'][key]['poisson_nll']:.5f}"] for key in ranking if key in METHODS])
    counts=table('Counts over the included test intervals',['Person','Intervals','Recorded spikes','Eight-task expected total','Touch-only expected total'],[
        [p['person'],f"{p['valid_targets']:,}",f"{p['observed_spikes']:,}",f"{p['methods']['joint_true']['expected_spikes']:,.1f}",f"{p['methods']['touch_only_true']['expected_spikes']:,.1f}"] for p in people])
    old=study['old_tasks']
    original=table('Earlier task scores on the same inputs, in each task’s own units',['Task and assessment','Unit','Seven tasks','Eight tasks'],[
        [x['name'],x['unit'],f"{x['prior']:.5g}",f"{x['candidate']:.5g}"] for x in old])
    nbetter=sum(x['candidate']<x['prior'] for x in old)
    retro=f"The eight-task fit had lower error on {nbetter} of the {len(old)} previous assessments. A loss is measured within its own task and recording. A millimetre of hand error and a missed nerve spike have different meanings."
    fit=study['fit']
    leads=f"<p>The lowest equal-person loss was <strong>{held['equal_person'][best]['poisson_nll']:.5f}</strong> for {escape(METHODS[best].lower())}. The eight-task model scored <strong>{held['equal_person']['joint_true']['poisson_nll']:.5f}</strong> with the recorded force. Each person contributes one third of the mean, even when their recordings supply different numbers of windows.</p>"
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} · NeuroTranslate</title><style>{(HERE/'study.css').read_text()}</style></head><body><main>
<section class="sheet"><header><p class="overline">NeuroTranslation · Research report</p><h1>{title}</h1>
<p class="lead">A glass plate slides under a finger. How much can its motion tell us about the next signal that travels up the arm?</p></header>
<p>{lead}</p>{leads}
<figure><img src="force-timing.svg" alt="Actual minus previous-slide loss by person. {escape(', '.join(p+' '+format(value,'+.5f') for p,value in paired['per_person'].items()))}."><figcaption>Each dot is one person. Left of zero, the recorded force gave the model a better forecast. Right of zero, force from the previous slide gave it a better forecast.</figcaption></figure>
<p>The authors of the original experiment measured three forces on the plate and recorded brief electrical events, called spikes, from one sensory nerve fibre at a time. Their camera also showed the skin changing shape. Our forecast uses the force and the earlier spikes. The two optical files we audited contain 220 processed slices from recordings with 310 camera frames. The available files did not establish which camera frame went with each saved slice. <a href="{PAPER}">Original experiment</a> · <a href="{DATA}">Data archive</a></p>
<h2>Try it on your computer</h2><p><a class="download" href="{DOWNLOAD}">Download the model and demo</a> · <a href="https://eliminatenoise.github.io/NeuroTranslation/touch-feedback/fingertip-touch.pdf">Read the PDF</a></p>
<p>Extract the ZIP, install Python 3.10 or later and NumPy, then open <strong>Touch study</strong> for your operating system. In the Command box, type “How many spikes will the touch nerve send?” Change a sideways force reading, run the forecast and compare the expected counts. The starting example is invented. <a href="https://eliminatenoise.github.io/Interoceptomics/fingertip-touch/">Explore the fingertip in 3D</a>. The same eight-task model can also run the seven earlier forecasts. <a href="https://eliminatenoise.github.io/NeuroTranslation/joint-alpha/">Installation guide</a></p>
<p>The model predicts an average count over a short interval. A value of 0.2 means one spike per five such intervals on average. It cannot identify exactly which interval contains the spike from that number alone.</p></section>
<section class="sheet"><h2>Can the model tell one slide from another?</h2>
<p>Each trial repeated a movement of the plate. Force from the previous slide can therefore carry clues about when loading begins. We kept the active nerve’s earlier spikes and elapsed time fixed and substituted the previous slide’s forces. We matched the material and direction and used the same eligible windows for each forecast. We also fitted a simple statistical model with and without those forces.</p>
{scores}
<p>The score is Poisson negative log likelihood, in nats per 20 ms interval. It penalizes assigning a low expected count where spikes occur and a high count where none occur. Lower is better. Here the average change for actual versus previous-slide force in the eight-task model was <strong>{paired['mean']:+.5f}</strong>. Resampling the three people gave a descriptive 95% interval of {lo:+.6f} to {hi:+.6f}, which crosses zero. Three people give limited evidence about a fourth.</p>
{counts}
<p>A count total tests whether a model predicts too many or too few spikes overall. Two forecasts can give similar totals and still disagree on when the spikes happen. The <a href="{SOURCE}/study.json">result tables</a> also give errors by receptor class, surface and direction within each person.</p></section>
<section class="sheet"><h2>What changed in the shared model?</h2>
<p>One set of <strong>{fit['shared_parameters']:,}</strong> parameters learns from eight tasks. Small input and output layers give each instrument its own channel order and units. Together these make <strong>{fit['parameters']:,}</strong> trainable parameters. The saved eight-task checkpoint occupies <strong>{fit['checkpoint_bytes']:,} bytes</strong>.</p>
<p>Every update used 32 examples from each task. For touch, we first sampled a person, then a window within that person. The seven earlier tasks kept their original initialization, example draws and number of updates. The eight-task training run saw more examples in total because it also saw touch. The simpler regressions gave each training window equal weight. A separate model trained on touch alone saw the same touch examples and began with the same shared and touch weights.</p>
{original}<p>{retro}</p><p>{escape(study['decision'])}</p></section>
<section class="sheet"><h2>What went into each forecast?</h2>
<p>We traced 35 deposited recording files to 27 sensory fibres in 13 people. Seven people supplied training data and two more supplied development checks. We froze the model before comparing its predictions with recordings from three other people. One person remains in reserve. Files from the same person stayed together.</p>
<p>The history ends at time <em>t</em>. Each of ten consecutive 20 ms rows contains the three average force readings in newtons, the number of recorded spikes and elapsed trial time. The target is the number of spikes between 20 and 40 ms after <em>t</em>, counting the right edge. To make the next forecast the model can see spikes that have since happened. Saved predictions were fixed before the future spike counts were scored.</p>
<p>The source marked invalid trials. The comparison takes adjacent fully valid trials on the same surface moving in the same direction. It requires finite source readings and checks target availability separately. Of {held['source_trial_slots']:,} held trial slots, {held['matched_trials']:,} supplied matched repetitions. One forecast had a missing future spike sample and could not be scored. The training set supplied {fit['training_rows']:,} eligible touch windows.</p>
<h3>Reproduce the comparison</h3><p>Run <code>python predict.py --touch --example human_touch_afferent</code> inside the extracted model folder. The checkpoint fingerprint lets you check which weights made a forecast. The <a href="{SOURCE}">training and evaluation files</a> include the frozen group assignments, data instructions, matched simpler models and results. Recorded nerve and force histories are available from the original authors.</p>
<p>Delhaye BP, Jarocka E, Barrea A, Thonnard J-L, Edin BB and Lefèvre P (2021). High-resolution imaging of skin deformation shows that afferents from human fingertips signal slip onset. <em>eLife</em> 10:e64679. <a href="{PAPER}">Study</a> · <a href="{DATA}">Zenodo data release, CC BY 4.0</a>. This analysis derives trial windows, fits models and compares their predictions.</p>
</section></main></body></html>'''

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    page=render()
    f=OUT/'index.html'
    if args.check:
        if f.read_text()!=page:raise SystemExit('Rebuild touch-feedback/index.html.')
    else:
        OUT.mkdir(exist_ok=True);f.write_text(page)
