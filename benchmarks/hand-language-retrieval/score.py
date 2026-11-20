"""Score each eligible held-out recording as a separate gallery, after verifying its sealed training fit."""
from collections import defaultdict
import json
from pathlib import Path

import numpy as np
import torch

from fit import by_record, check_split, define_args, normalized, unpack
from hand_data import read_role
from kit_components import digest, dump, multi_scores, tied_scores, words
from rank import Scorer

METRICS=('recall1','recall5','mrr')


def audit(train,test,scorer):
    z=scorer.z
    orig=np.stack([s.sequence for s in train])
    train_x=normalized(orig,z['center'],z['scale']).astype(float)
    mask=np.isfinite(orig)
    docs={tuple(words(t)) for s in train for t in s.captions}
    bags={frozenset(t) for t in docs}
    out=[]
    for c in test:
        x=normalized(c.sequence,z['center'],z['scale']).astype(float)
        valid=np.isfinite(c.sequence)
        common=valid&mask
        count=common.sum((1,2))
        support=(count>=.75*valid.size)&(common.any(2).sum(1)>=2)
        dist=np.sqrt(np.where(common,(train_x-x)**2,0).sum((1,2))/np.maximum(count,1))
        same_mask=(mask==valid).all((1,2))
        exact=((train_x==x)|~common).all((1,2)) & same_mask
        near=(dist<=.01)&support
        txt=[]
        for desc in c.captions:
            ts=tuple(words(desc))
            bag=set(ts)
            sim=max(len(bag & b)/len(bag | b) for b in bags)
            txt.append({'text_exact':ts in docs,'max_jaccard':sim,'novel':ts not in docs and sim<.8})
        out.append({'key':c.key,'exact_geometry':[train[j].key for j in np.flatnonzero(exact)],
                    'near_geometry':[train[j].key for j in np.flatnonzero(near)],
                    'same_mask':int(same_mask.sum()),'coverage':float(valid.mean()),'queries':txt})
    return out


def group_mean(rows,method,domain):
    recs=defaultdict(dict)
    for row in rows:
        k=(row['group'],row['recording'])
        valid=[q['scores'][method][domain] for q in row['queries'] if domain in q['scores'][method]]
        if valid:
            recs[k][row['key']]=np.mean(valid,axis=0)
    families=defaultdict(list)
    for (g,r),v in recs.items():
        families[g].append(np.mean(list(v.values()),axis=0))
    return {g:np.mean(values,axis=0) for g,values in families.items()}


def assess(train,test,scorer,dest):
    dest.mkdir(exist_ok=False)
    copies=audit(train,test,scorer)
    copy_by={c['key']:c for c in copies}
    rows=[]
    gallery_sizes={}
    for rec,indices in by_record(test).items():
        clips=[test[i] for i in indices]
        query,owner,by_seg=unpack(clips)
        arrays=scorer.scores(query,clips)
        np.savez_compressed(dest/(rec+'.npz'),owner=owner,**arrays)
        gallery_sizes[rec]=len(clips)
        tokens=[tuple(words(s)) for s in query]
        alternatives=[{tuple(words(s)) for s in c.captions} for c in clips]
        compat=np.array([[t in choices for choices in alternatives] for t in tokens])
        values={}
        for method,scores in arrays.items():
            exact=tied_scores(scores,owner)
            lexical=multi_scores(scores,compat)
            values[method]=[]
            for j,t in enumerate(tokens):
                idx=owner[j]
                group=np.array([k for k,c in enumerate(clips) if c.cue==clips[idx].cue])
                dif=np.array([k for k in group if k==idx or t not in alternatives[k]],dtype=int)
                v={'exact':exact[j].tolist(),'any_same_text':lexical[j].tolist()}
                for name,pool in [('same_action',group),('same_action_other_sentence',dif)]:
                    if all(clips[idx].cue) and len(pool)>1:
                        true=np.array([np.flatnonzero(pool==idx)[0]])
                        v[name]=tied_scores(scores[j:j+1,pool],true)[0].tolist()
                values[method].append(v)
        for i,c in enumerate(clips):
            qq=[]
            for jj,j in enumerate(by_seg[i]):
                scores={m:v[j] for m,v in values.items()}
                for s in scores.values():
                    if copy_by[c.key]['queries'][jj]['novel']:
                        s['novel_text']=s['exact']
                ids,_=scorer.text.encode([query[j]])
                qq.append({'known_tokens':int((ids>=2).sum()),'unknown_tokens':int((ids==1).sum()),
                           'lexical_positives':int(compat[j].sum()),'scores':scores})
            rows.append({'key':c.key,'recording':rec,'group':c.group,'queries':qq})
    domains=['exact','any_same_text','same_action','same_action_other_sentence','novel_text']
    methods=list(arrays)
    metrics={}
    for domain in domains:
        sample=group_mean(rows,methods[0],domain)
        info={'families':sorted(sample),'queries':sum(domain in q['scores'][methods[0]] for r in rows for q in r['queries']),
              'models':{}}
        for m in methods:
            grouped=group_mean(rows,m,domain)
            if grouped:
                info['models'][m]={'family_macro':dict(zip(METRICS,np.mean(list(grouped.values()),0).tolist())),
                                    'by_family':{g:v.tolist() for g,v in sorted(grouped.items())}}
        metrics[domain]=info
    base=metrics['exact']['models']
    n=len(metrics['exact']['families'])
    choose=np.random.default_rng(98031).integers(n,size=(10000,n))
    comparisons={}
    duplicates=any(r['exact_geometry'] or r['near_geometry'] for r in copies)
    for name in ['ridge','attention']:
        others=[k for k in methods if k!=name and (name=='attention' or k!='attention')]
        pred=np.array(list(base[name]['by_family'].values()))
        cmp={}
        for m in others:
            diff=pred-np.array(list(base[m]['by_family'].values()))
            ci=np.quantile(diff[choose].mean(1),[.025,.975],axis=0)
            cmp[m]={'mean_difference':diff.mean(0).tolist(),'paired_lower':ci[0].tolist(),'paired_upper':ci[1].tolist(),
                    'by_family':dict(zip(metrics['exact']['families'],diff.tolist()))}
        comparisons[name]={'comparators':cmp,'passed':bool(n>=6 and not duplicates and all(
            min(c['paired_lower'][0],c['paired_lower'][2],c['mean_difference'][0],c['mean_difference'][2])>0 for c in cmp.values()))}
    dump(copies,dest/'copy-audit.json')
    dump(rows,dest/'query-metrics.json')
    result={'metrics':metrics,'comparisons':comparisons,'gallery_sizes':gallery_sizes,'assessment_segments':len(test),
            'r5_saturated_galleries':sum(v<=5 for v in gallery_sizes.values()),
            'any_cross_split_geometry_copy':duplicates,'fully_oov':sum(q['known_tokens']==0 for r in rows for q in r['queries']),
            'normalized_text_exact':sum(q['text_exact'] for c in copies for q in c['queries']),
            'normalized_text_jaccard_ge_08':sum(q['max_jaccard']>=.8 for c in copies for q in c['queries'])}
    dump(result,dest/'results.json')
    return result


def main():
    a=define_args().parse_args()
    check_split(a)
    torch.set_num_threads(a.threads)
    torch.set_num_interop_threads(1)
    fit=a.output/'fit'
    scorer=Scorer(fit)
    seal=scorer.seal
    if digest(a.split)!=seal['split'] or digest(a.output/'training.json')!=seal['training']:
        raise ValueError('Split or training manifest changed')
    if (a.output/'assessment').exists():
        raise FileExistsError('A sealed assessment exists or an interrupted assessment needs inspection')
    train,ledger=read_role(a.data,a.split,'train')
    if ledger!=json.loads((a.output/'training.json').read_text()):
        raise ValueError('Training payload or exclusions changed')
    test,ledger=read_role(a.data,a.split,'review')
    dest=a.output/'assessment'
    result=assess(train,test,scorer,dest)
    dump(ledger,dest/'sources.json')
    dump({'fit':digest(fit/'seal.json'),'outputs':{p.name:digest(p) for p in sorted(dest.iterdir())}},dest/'seal.json')
    print(json.dumps({'counts':result['gallery_sizes'],'exact':{m:v['family_macro'] for m,v in result['metrics']['exact']['models'].items()}}))


if __name__=='__main__':
    main()
