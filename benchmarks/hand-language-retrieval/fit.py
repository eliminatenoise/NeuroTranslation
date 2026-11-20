"""Fit frozen text-to-hand retrieval models using only the selected HoloAssist training sessions."""
from collections import defaultdict
import argparse
import json
from pathlib import Path
import time

import numpy as np
import torch
import torch.nn.functional as F

from hand_data import read_role, STEPS
from kit_components import Retrieval, TextMap, cyclic_derangement, descriptors, digest, dump, words

POLICY = dict(seed=20261120, wrong_seed=40362, text_tokens=32, motion_steps=STEPS,
              vocabulary_cap=512, width=32, heads=4, epochs=30, ridge_penalty=2,
              temperature=.13, learning_rate=.002, weight_decay=.01)
CODE_FILES = ('fit.py','kit_components.py','hand_data.py','score.py','rank.py')
RULE_FILES = ('design.json','source-addendum.json','time-addendum.json')
REAL_SPLIT = '1be4ec20c77da82a73a14ecbea8f9097e4240ea44596ed80c1678ba076529cac'


def code_identity():
    base=Path(__file__).resolve().parent
    return {k:digest(base/k) for k in CODE_FILES + RULE_FILES}


def by_record(items):
    groups=defaultdict(list)
    for i,c in enumerate(items):
        groups[c.recording].append(i)
    return {r:np.asarray(indices,dtype=int) for r,indices in groups.items()}


def unpack(items):
    texts, owner, by_seg=[],[],[]
    for i,c in enumerate(items):
        by_seg.append(list(range(len(texts),len(texts)+len(c.captions))))
        texts.extend(c.captions)
        owner += [i]*len(c.captions)
    return texts,np.array(owner),by_seg


def normalized(a, mean, sd):
    return np.nan_to_num((a-mean)/sd, nan=0.,posinf=0.,neginf=0.).astype(np.float32)


def statistics(a, axes):
    a=np.asarray(a,dtype=np.float64)
    obs=np.isfinite(a)
    n=obs.sum(axis=axes,keepdims=True)
    mu=np.nansum(a,axis=axes,keepdims=True)/np.maximum(n,1)
    var=np.nansum((a-mu)**2,axis=axes,keepdims=True)/np.maximum(n,1)
    sigma=np.sqrt(var)
    return tuple(np.squeeze(v,axis=axes).astype(np.float32) for v in [mu,np.where(sigma>1e-6,sigma,1.)])


def control_values(clips):
    return {'duration':np.array([[np.log1p(c.duration)] for c in clips]),
            'context':np.array([[c.context] for c in clips]),
            'mask':np.array([np.isfinite(c.sequence).ravel() for c in clips],dtype=float)}


def with_bias(a):
    return np.column_stack((a,np.ones(len(a))))


def ridge(a,targets,weights):
    a=with_bias(a)
    pen=np.full(a.shape[1],POLICY['ridge_penalty'])
    pen[-1]=0.
    return np.linalg.solve(a.T@(weights[:,None]*a)+np.diag(pen),
                           a.T@(weights[:,None]*targets)).astype(np.float32)


def fit_attention(items, vocab, ids, by_seg, x, target, policy):
    torch.manual_seed(policy['seed'])
    model=Retrieval(len(vocab.idf),x.shape[-1],policy)
    opt=torch.optim.AdamW(model.parameters(),lr=policy['learning_rate'],weight_decay=policy['weight_decay'])
    groups=list(by_record(items).values())
    rng=np.random.default_rng(policy['seed'])
    text,_,_=unpack(items)
    canonical=[tuple(words(s)) for s in text]
    for _ in range(policy['epochs']):
        for g in rng.permutation(len(groups)):
            batch=groups[g]
            q=[rng.choice(by_seg[i]) for i in batch]
            pos=torch.tensor([[canonical[i]==canonical[j] for j in q] for i in q],dtype=torch.bool)
            logits=model.from_words(ids[q])@model.from_motion(x[target[batch]]).T/policy['temperature']
            # Marginalize over indistinguishable label groups in both directions.
            POS=logits.masked_fill(~pos,-torch.inf)
            loss=sum((logits.logsumexp(dim=d)-POS.logsumexp(dim=d)).mean() for d in (0,1))*.5
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
    return model.eval()


def fitted(items, dest, policy):
    dest.mkdir(parents=True,exist_ok=False)
    texts,owner,by_seg=unpack(items)
    vocab=TextMap.fit(items,policy)
    ids,bow=vocab.encode(texts)
    seq=np.stack([s.sequence for s in items])
    center,scale=statistics(seq,(0,1))
    x=torch.from_numpy(normalized(seq,center,scale))
    raw=descriptors(x).numpy()
    dmean,dsd=statistics(raw,0)
    y=normalized(raw,dmean,dsd)
    weight=1./np.bincount(owner)[owner]
    wrong=np.arange(len(items))
    for n,b in enumerate(by_record(items).values()):
        wrong[b]=b[cyclic_derangement(len(b),policy['wrong_seed']+n)]
    arrays={'center':center,'scale':scale,'desc_center':dmean,'desc_scale':dsd,'idf':vocab.idf,
            'ridge':ridge(bow.numpy(),y[owner],weight),'wrong_ridge':ridge(bow.numpy(),y[wrong[owner]],weight)}
    length=np.array([[np.log1p(len(words(s)))] for s in texts])
    mean,sd=statistics(length,0)
    arrays.update(length_center=mean,length_scale=sd,length=ridge(normalized(length,mean,sd),y[owner],weight))
    blocks=[]
    for name,values in control_values(items).items():
        mean,sd=statistics(values,0)
        v=normalized(values,mean,sd)
        arrays[name+'_center'],arrays[name+'_scale']=mean,sd
        arrays[name]=ridge(bow.numpy(),v[owner],weight)
        blocks.append(v/np.sqrt(v.shape[1]))
    arrays['joint_nuisance']=ridge(bow.numpy(),np.column_stack(blocks)[owner],weight)
    np.savez_compressed(dest/'linear.npz',**arrays)
    for name,perm in [('attention',np.arange(len(items))),('wrong_attention',wrong)]:
        model=fit_attention(items,vocab,ids,by_seg,x,perm,policy)
        np.savez_compressed(dest/(name+'.npz'),**{k:v.detach().numpy() for k,v in model.state_dict().items()})
    dump({'policy':policy,'vocabulary':vocab.vocab,'channels':x.shape[-1],
          'train':[s.key for s in items],'wrong_target':[items[i].key for i in wrong]},dest/'fit.json')


def write_gallery(items,dest):
    gallery=[s for s in items if s.recording==items[0].recording]
    np.savez_compressed(dest/'gallery.npz',sequence=np.stack([s.sequence for s in gallery]))
    dump({'role':'train','recording':items[0].recording,'segments':[{
        'key':s.key,'captions':s.captions,'start':s.start,'end':s.end,'duration':s.duration,
        'context':s.context,'cue':s.cue,'group':s.group} for s in gallery]},dest/'gallery.json')


def trust_fit(fit):
    seal=json.loads((fit/'seal.json').read_text())
    if seal['code']!=code_identity() or any(digest(fit/k)!=v for k,v in seal['weights'].items()):
        raise ValueError('Fitted artifacts, source code or study design differ from the sealed run')
    return seal


def define_args():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',required=True,type=Path)
    p.add_argument('--split',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--fixture',action='store_true',help='Only use an artificial manifest explicitly marked fixture')
    p.add_argument('--threads',type=int,choices=[1,2,4],default=2)
    return p


def check_split(args):
    manifest=json.loads(args.split.read_text())
    if args.fixture:
        if manifest.get('kind')!='artificial_fixture':
            raise ValueError('Fixture mode requires an explicit artificial manifest')
    elif digest(args.split)!=REAL_SPLIT:
        raise ValueError('Real corpus split changed after prospective review')


def main():
    a=define_args().parse_args()
    check_split(a)
    torch.set_num_threads(a.threads)
    torch.set_num_interop_threads(1)
    start=time.monotonic()
    training,ledger=read_role(a.data,a.split,'train')
    a.output.mkdir(parents=True,exist_ok=False)
    fit=a.output/'fit'
    dump(ledger,a.output/'training.json')
    fitted(training,fit,POLICY)
    write_gallery(training,a.output)
    seal={'split':digest(a.split),'training':digest(a.output/'training.json'),'code':code_identity(),
          'weights':{p.name:digest(p) for p in sorted(fit.iterdir())},
          'gallery':{k:digest(a.output/k) for k in ('gallery.npz','gallery.json')},
          'torch':str(torch.__version__),'numpy':np.__version__,'intraop':torch.get_num_threads(),
          'interop':torch.get_num_interop_threads(),'elapsed_seconds':time.monotonic()-start,
          'training_segments':len(training),'training_captions':sum(len(s.captions) for s in training)}
    dump(seal,fit/'seal.json')
    print(json.dumps(seal))


if __name__=='__main__':
    main()
