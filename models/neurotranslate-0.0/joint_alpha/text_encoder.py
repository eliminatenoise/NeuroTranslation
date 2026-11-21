"""Optional offline language frontend. It may propose an existing task, never a physiological value."""
import argparse
import json
from pathlib import Path
import re

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
EXAMPLES = {
    "human_leg_emg": ["What will the electrical activity in the lower-leg muscles be?",
        "Can you predict the EMG of the calf muscles?", "Estimate the leg muscle voltage during this balance trial."],
    "human_sacrum_path": ["Where will the pelvis marker move over the next instant?",
        "Forecast the motion of my hips in this balance exercise.", "Predict the next sacrum positions."],
    "macaque_cortex_to_motion": ["In the macaque reaching task, predict where the arm will move.",
        "Use the monkey's earlier cortical and motion data to forecast hand and handle movement.", "Estimate displacement during the monkey's reach."],
    "macaque_motion_to_cortex": ["Forecast the number of spikes recorded at each macaque brain electrode.",
        "How many cortical spikes occur after this reach?", "Predict the next cortical count from the previous movement and brain signals."],
    "rat_next_unit": ["Which recorded neuron will fire next?", "Rank the individual recorded units by the probability of the next spike.", "Predict the identity of the next active cell in a rat recording."],
    "optical_fluorescence": ["How bright will the brain's calcium indicator be?", "Predict the next fluorescence measurement in fish or worm neurons.",
        "Estimate the next GCaMP signal in the imaging data."],
    "landmark_motion": ["Where will these camera points be next?", "Forecast the next position of the landmarks in my video.",
        "Where will the tracked wrist go in a moment?"],
    "human_touch_afferent": ["Forecast how many spikes a fingertip sensory nerve will send.",
        "Predict the firing of a touch afferent during loading of the finger pad.",
        "How many tactile nerve spikes come after the plate slides?"],
    "unsupported": ["I want a medical diagnosis.", "What is the weather tomorrow?", "Write poetry about a birthday.",
        "Tell me the force in newtons inside an individual tendon.", "Operate a stimulator or make my physical hand move.",
        "How much tension is each muscle producing?"]
}

class OutcomeEncoder:
    def __init__(self, directory, threads=2):
        import torch
        from transformers import AutoModel, AutoTokenizer
        self.torch=torch
        torch.set_num_threads(threads)
        path=Path(directory).expanduser().resolve(strict=True)
        if not path.is_dir():raise ValueError("Supply a local encoder folder.")
        self.tokenizer=AutoTokenizer.from_pretrained(path,local_files_only=True,trust_remote_code=False)
        self.model=AutoModel.from_pretrained(path,local_files_only=True,trust_remote_code=False,use_safetensors=True).eval()
        self.names=list(EXAMPLES)
        self.centres=self.embed([v for key in self.names for v in EXAMPLES[key]])
        self.labels=[key for key in self.names for _ in EXAMPLES[key]]

    def embed(self, texts):
        z=self.tokenizer(texts,padding=True,truncation=True,max_length=128,return_tensors="pt")
        with self.torch.inference_mode():
            vec=self.model(**z).last_hidden_state
            mask=z.attention_mask.unsqueeze(-1)
            return self.torch.nn.functional.normalize((vec*mask).sum(1)/mask.sum(1).clamp(min=1),dim=1)

    def propose(self, text):
        if not isinstance(text,str) or not text.strip() or len(text)>1000:
            return {"kind":"unsupported","message":"Supply one short description of a measured outcome."}
        if re.search(r"\b(force|torque|tension|newtons?|stimulat\w*|voltages? to apply)\b",text,re.I):
            return {"kind":"unsupported","message":"No direct force or physical-actuation forecast is available."}
        v=self.embed([text]);similarity=(v@self.centres.T)[0].tolist()
        ranked=sorted(((max(s for s,k in zip(similarity,self.labels,strict=True) if k==name),name) for name in self.names),reverse=True)
        best,task=ranked[0]
        if task=="unsupported" or best<0.48 or best-ranked[1][0]<0.045:
            return {"kind":"unsupported","message":"No single supported outcome is clear. Choose from the visible tasks."}
        return {"kind":"forecast","task":task}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model-dir",required=True,type=Path);p.add_argument("description")
    a=p.parse_args();print(json.dumps(OutcomeEncoder(a.model_dir).propose(a.description)))
