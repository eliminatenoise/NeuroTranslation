"""Compare trial-level muscle and knee-angle periodicities. Each signal keeps its own clock."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

HERE=Path(__file__).resolve().parent
INDEX_SHA="d2e302605b86e264bb7b0d710c7e19214cd5bf487d2f1c70170f9fae4961c147"
FIT_SHA="57e989090a461f3f4903c8ebc9d05bc6cf22bd60c6e731b007ade0f4d8110ac9"
FREEZE_SHA="67b33f3a79fb013cb71f7a59e1dca0fd34a4b2bbafbfe1437b719df4c584b34c"
FREQUENCIES=np.arange(180,601)/400.0

def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()

def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')

def dominant(t,signal):
    if not np.isfinite(t).all() or not np.isfinite(signal).all() or np.any(np.diff(t)<=0):
        raise ValueError('Invalid native time or amplitude')
    relative=t-t[0]
    if relative[-1]<45:
        raise ValueError('Less than 45 seconds of observations')
    window=(relative>=5)&(relative<45)
    count=int(window.sum())
    if count<(500 if signal.shape[1]==12 else 2000):
        raise ValueError('Too few rows in the fixed interval')
    times=relative[window]-5
    values=signal[window]
    tapered=(values-values.mean(axis=0))*(.5-.5*np.cos(2*np.pi*times/40))[:,None]
    # Evaluate the same frequency grid at actual time labels for either instrument.
    fourier=np.exp((-2j*np.pi)*FREQUENCIES[:,None]*times[None,:])@tapered
    power=np.abs(fourier)**2
    totals=power.sum(axis=0)
    if np.any(totals<=0): raise ValueError('Constant channel')
    spectrum=(power/totals).mean(axis=1)
    k=int(np.argmax(spectrum))
    return float(FREQUENCIES[k]*60), count

def read_pair(cache,index,person):
    emg_rel=f'Dataset/EMG_Data/EMG_S{person}_0.5.csv'
    if emg_rel not in index:raise FileNotFoundError('No EMG file in source index')
    knee_file=cache/'imu-members'/f'IMU_S{person}_0.5'/'Joint_Angles_ZXY.csv'
    expected=json.loads((HERE/'sources.json').read_bytes())['members'].get(str(person))
    if expected is None:
        if person==24:raise FileNotFoundError('No verified angle export for this selection')
        raise RuntimeError('Unlisted source identity')
    if not knee_file.is_file() or sha(knee_file)!=expected['knee_sha256']:
        raise RuntimeError('Missing or changed angle file for S'+str(person))
    tech=cache/'imu-members'/expected['technical_member']
    if not tech.is_file() or sha(tech)!=expected['technical_sha256']:
        raise RuntimeError('Missing or changed IMU technical file for S'+str(person))
    with tech.open(encoding='utf-8-sig',newline='') as stream:
        hz=[r[1] for r in csv.reader(stream) if len(r)==2 and r[0]=='Frame Rate']
    if len(hz)!=1 or float(hz[0])!=60:raise RuntimeError('Unsupported source frame rate')
    emg_file=cache/emg_rel
    if not emg_file.is_file():raise RuntimeError('Fetch listed original before running: '+emg_rel)
    if sha(emg_file)!=index[emg_rel]:raise RuntimeError('Wrong source hash for '+emg_rel)
    with emg_file.open(encoding='utf-8-sig',newline='') as f:columns=next(csv.reader(f))
    if len(columns)!=13 or columns[0].strip()!='X [s]' or not all('MAV [Volts]' in n for n in columns[1:]):
        raise ValueError('Unexpected muscle columns')
    emg=np.loadtxt(emg_file,delimiter=',',skiprows=1,encoding='utf-8-sig')
    if np.max(np.diff(emg[:,0]))>.110:raise ValueError('Muscle time label gap exceeds 110 ms')
    with knee_file.open(encoding='utf-8-sig',newline='') as f:cols=next(csv.reader(f))
    variables=['Frame','Right Knee Flexion/Extension','Left Knee Flexion/Extension']
    angles=np.loadtxt(knee_file,delimiter=',',skiprows=1,usecols=[cols.index(k) for k in variables],encoding='utf-8-sig')
    if not np.all(np.diff(angles[:,0])==1):raise ValueError('Discontinuous angle frame numbers')
    emg_rate,emg_rows=dominant(emg[:,0],emg[:,1:])
    knee_rate,knee_rows=dominant(angles[:,0]/60,angles[:,1:])
    return {'person':person,'emg_cycles_min':emg_rate,'angle_cycles_min':knee_rate,'emg_rows':emg_rows,'angle_rows':knee_rows,
            'emg_sha256':sha(emg_file),'angles_sha256':sha(knee_file)}

def selected(cache,index,ids,seen):
    rows=[];excluded=[]
    for person in ids:
        try:r=read_pair(cache,index,person)
        except (FileNotFoundError,ValueError) as e:
            excluded.append({'person':person,'reason':str(e)});continue
        if r['emg_sha256'] in seen or r['angles_sha256'] in seen:
            excluded.append({'person':person,'reason':'Repeated source bytes'});continue
        seen.update((r['emg_sha256'],r['angles_sha256']));rows.append(r)
    return rows,excluded

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('mode',choices=['fit','score'])
    ap.add_argument('--cache',type=Path,required=True,help='Verified PhysioNet source and extracted IMU directory')
    ap.add_argument('--index',type=Path,required=True,help='Original v1.0.0 SHA256SUMS.txt')
    ap.add_argument('--output',type=Path,default=Path('rebuilt'))
    a=ap.parse_args()
    if sha(a.index)!=INDEX_SHA or sha(HERE/'protocol.json')!=FREEZE_SHA:raise ValueError('Source or study specification changed')
    index={name:pin for pin,name in (line.split(maxsplit=1) for line in a.index.read_text().splitlines())}
    training=a.output/'fit.json'
    if a.mode=='fit':
        rows,excluded=selected(a.cache,index,range(1,41),set())
        if len(rows)<2:raise ValueError('Too few training recordings')
        x=np.array([r['emg_cycles_min'] for r in rows]);y=np.array([r['angle_cycles_min'] for r in rows])
        coef=np.linalg.lstsq(np.column_stack((np.ones_like(x),x)),y,rcond=None)[0]
        save(training,{'protocol_sha256':FREEZE_SHA,'median_reference':float(np.median(y)),'intercept':float(coef[0]),'slope':float(coef[1]),'training':rows,'excluded':excluded});return
    published=HERE/'fit.json'
    if sha(published)!=FIT_SHA:raise ValueError('Published training artifact changed')
    if not training.exists():training=published
    fit=json.loads(training.read_bytes())
    reference=json.loads(published.read_bytes())
    for key,value in reference.items():
        if key in ('slope','intercept'):
            if not np.isclose(fit[key],value,rtol=0,atol=1e-10):raise ValueError('Rebuilt affine coefficients disagree')
        elif fit.get(key)!=value:raise ValueError('Rebuilt training inputs disagree: '+key)
    if fit['protocol_sha256']!=FREEZE_SHA:raise ValueError('Training specification changed')
    seen={r[k] for r in fit['training'] for k in ('emg_sha256','angles_sha256')}
    rows,excluded=selected(a.cache,index,range(41,53),seen)
    if len(rows)<3:raise ValueError('Too few test recordings')
    x=np.array([r['emg_cycles_min'] for r in rows]);y=np.array([r['angle_cycles_min'] for r in rows])
    preds={'matched_emg':x,'training_median':np.full_like(y,fit['median_reference']),
          'affine_emg':fit['intercept']+fit['slope']*x,'wrong_person':np.roll(x,-1)}
    for i,row in enumerate(rows):
        row['wrong_person_source']=rows[(i+1)%len(rows)]['person']
        row['estimate_cycles_min']={k:float(vals[i]) for k,vals in preds.items()}
        row['absolute_error_cycles_min']={k:round(abs(float(vals[i])-float(y[i])),10) for k,vals in preds.items()}
        row['matched_minus_control_error']={key:round(row['absolute_error_cycles_min']['matched_emg']-row['absolute_error_cycles_min'][key],10) for key in ('training_median','wrong_person')}
    scores={k:{'mae':float(np.abs(v-y).mean()),'bias':float((v-y).mean())} for k,v in preds.items()}
    comparisons={}
    for key in ('training_median','wrong_person'):
        # Frequency bins are exactly 0.15 cycles/min apart. Treat equal bin distances as ties.
        diff=np.round(np.abs(x-y)-np.abs(preds[key]-y),10)
        without=(diff.sum()-diff)/(len(diff)-1)
        comparisons[key]={'mae_difference':float(diff.mean()),'people_with_lower_error':int((diff<0).sum()),'ties':int((diff==0).sum()),
                          'leave_one_out_mean_difference_range':[float(without.min()),float(without.max())]}
    met=all(v['mae_difference']<0 and v['people_with_lower_error']>len(rows)/2 for v in comparisons.values())
    save(a.output/'results.json',{'protocol_sha256':FREEZE_SHA,'fit_sha256':sha(training),'units':'unilateral cycles per minute',
         'included_people':len(rows),'excluded':excluded,'people':rows,'scores':scores,'paired':comparisons,'criterion_met':met})
if __name__=='__main__':main()
