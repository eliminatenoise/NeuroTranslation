"""Score a new human description against a gallery using fixed training weights."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from hand_data import Segment
from fit import control_values, normalized, trust_fit, with_bias
from kit_components import Retrieval, TextMap, descriptors, digest, words


def unit(a):
    return a / np.maximum(np.linalg.norm(a,axis=1,keepdims=True),1e-12)


class Scorer:
    def __init__(self, fit):
        self.seal=trust_fit(fit)
        self.meta=json.loads((fit/'fit.json').read_text())
        with np.load(fit/'linear.npz',allow_pickle=False) as z:
            self.z={k:z[k] for k in z.files}
        self.text=TextMap(self.meta['vocabulary'],self.z['idf'],self.meta['policy']['text_tokens'])
        self.networks={}
        for name in ('attention','wrong_attention'):
            model=Retrieval(len(self.text.idf),self.meta['channels'],self.meta['policy'])
            with np.load(fit/(name+'.npz'),allow_pickle=False) as z:
                model.load_state_dict({k:torch.from_numpy(z[k].copy()) for k in z.files})
            self.networks[name]=model.eval()

    @torch.no_grad()
    def scores(self, query, clips):
        z=self.z
        ids,bow=self.text.encode(query)
        design=with_bias(bow.numpy())
        x=torch.from_numpy(normalized(np.stack([s.sequence for s in clips]),z['center'],z['scale']))
        y=normalized(descriptors(x).numpy(),z['desc_center'],z['desc_scale'])
        result={'chance':np.zeros((len(query),len(clips)))}
        for name in ('ridge','wrong_ridge'):
            result[name]=unit(design@z[name]) @ unit(y).T
        length=np.array([[np.log1p(len(words(s)))] for s in query])
        a=with_bias(normalized(length,z['length_center'],z['length_scale']))
        result['length']=unit(a@z['length']) @ unit(y).T
        blocks=[]
        for name,val in control_values(clips).items():
            b=normalized(val,z[name+'_center'],z[name+'_scale'])
            result[name]=-np.mean((design@z[name])[:,None,:]**2+ b[None,:,:]**2
                                 -2*(design@z[name])[:,None,:]*b[None,:,:],axis=-1)
            blocks.append(b/np.sqrt(b.shape[1]))
        b=np.column_stack(blocks)
        result['joint_nuisance']=-np.mean(((design@z['joint_nuisance'])[:,None,:]-b[None,:,:])**2,axis=-1)
        for name,model in self.networks.items():
            result[name]=(model.from_words(ids)@model.from_motion(x).T).numpy()
        if any(not np.isfinite(v).all() for v in result.values()):
            raise ValueError('Nonfinite candidate score')
        return result

    def gallery(self,path):
        for k,sha in self.seal['gallery'].items():
            if digest(path/k)!=sha:
                raise ValueError('Example gallery changed')
        meta=json.loads((path/'gallery.json').read_text())
        with np.load(path/'gallery.npz',allow_pickle=False) as z:
            seq=z['sequence']
        return [Segment(r['key'],meta['recording'],r['group'],r['captions'],x,r['duration'],
                        r['context'],tuple(r['cue']),r['start'],r['end']) for r,x in zip(meta['segments'],seq,strict=True)]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('sentence')
    p.add_argument('--bundle',type=Path,default=Path(__file__).resolve().parent/'bundle')
    p.add_argument('--method',choices=['ridge','attention'],default='ridge')
    args=p.parse_args()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    scorer=Scorer(args.bundle/'fit')
    clips=scorer.gallery(args.bundle)
    scores=scorer.scores([args.sentence],clips)[args.method][0]
    ids,_=scorer.text.encode([args.sentence])
    print(json.dumps({'method':args.method,'known_words':int((ids>=2).sum()),'unknown_words':int((ids==1).sum()),
                      'recording':clips[0].recording,'fit_partition':'training example',
                      'matches':[{'key':clips[i].key,'rank_shared_if_tied':1+int((scores>scores[i]).sum()),
                                  'score':float(scores[i]),'start':clips[i].start,'end':clips[i].end,
                                  'reference_description':clips[i].captions} for i in np.argsort(-scores,kind='stable')]},indent=2))


if __name__=='__main__':
    main()
