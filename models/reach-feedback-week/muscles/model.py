"""Infer modelled muscle–tendon changes from a past arm history or proposed arm paths."""
import numpy as np

def position_terms(pose):
    anchor=pose[:,-1]
    relative=pose-anchor[:,None]
    return anchor,relative.reshape(len(pose),4,5,8).mean(axis=2)

def design_displacement(anchor,delta,weights):
    pose=(anchor-weights["anchor_mean"])/weights["anchor_sd"]
    dx=delta/weights["motion_rms"]
    interaction=(dx[:,:,:,None]*pose[:,None,None,:]).reshape(len(dx),10,64)
    return np.concatenate((dx,interaction),axis=-1)

def infer_path(pose,delta,weights):
    """Return N × 10 × 39 changes in metres from the final history sample."""
    anchor=pose[:,-1]
    return design_displacement(anchor,delta,weights)@weights["geometry"]

def direct_x(pose,cue):
    anchor,means=position_terms(pose)
    return np.concatenate((anchor,means.reshape(len(pose),32),cue[:,-1]),axis=-1)

def infer_direct(pose,cue,weights):
    values=(direct_x(pose,cue)-weights["direct_mean"])/weights["direct_sd"]
    return (values@weights["direct_coef"]+weights["direct_bias"]).reshape(-1,10,39)
