"""Shared channel vocabularies (PROTOCOL.json representation.channel_identity.shared_vocabularies).

A channel gets a shared key when its name identifies the same anatomical landmark, muscle and side,
joint and axis, or force axis in another dataset; otherwise its key is None and it gets a learned
row per dataset (unnamed EMG channels, HD-EMG electrodes, technical cluster markers).
Keys are strings so that they can be counted and hashed:
  landmark:<side>_<landmark>       e.g. landmark:L_ASIS
  muscle:<side>_<muscle>           e.g. muscle:R_tibialis_anterior
  joint:<convention>:<coordinate>  e.g. joint:opensim:knee_angle_r (conventions are kept apart because
                                   their signs and zero angles differ)
  imu:<segment>:<quantity>:<axis>  e.g. imu:pelvis:free_acceleration:x
  force:<source>:<axis>            e.g. force:plate1:z (laboratory frame, vertical +Z, ground reaction)
"""

# Plug-in-Gait (Gait120, Van Criekinge) -> landmark
PIG = {
    "LASI": "L_ASIS", "RASI": "R_ASIS", "LPSI": "L_PSIS", "RPSI": "R_PSIS", "SACR": "sacrum",
    "LKNE": "L_lat_femoral_epicondyle", "RKNE": "R_lat_femoral_epicondyle",
    "LANK": "L_lat_malleolus", "RANK": "R_lat_malleolus",
    "LHEE": "L_calcaneus", "RHEE": "R_calcaneus", "LTOE": "L_2nd_metatarsal_head", "RTOE": "R_2nd_metatarsal_head",
    "LTHI": "L_thigh_wand", "RTHI": "R_thigh_wand", "LTIB": "L_shank_wand", "RTIB": "R_shank_wand",
    "C7": "C7", "T10": "T10", "CLAV": "jugular_notch", "STRN": "xiphoid", "RBAK": "R_scapula",
    "LSHO": "L_acromion", "RSHO": "R_acromion", "LELB": "L_lat_humeral_epicondyle",
    "RELB": "R_lat_humeral_epicondyle", "LWRA": "L_radial_styloid", "RWRA": "R_radial_styloid",
    "LWRB": "L_ulnar_styloid", "RWRB": "R_ulnar_styloid", "LFIN": "L_2nd_metacarpal_head",
    "RFIN": "R_2nd_metacarpal_head", "LFHD": "L_front_head", "RFHD": "R_front_head",
    "LBHD": "L_back_head", "RBHD": "R_back_head", "LUPA": "L_upper_arm_wand", "RUPA": "R_upper_arm_wand",
    "LFRM": "L_forearm_wand", "RFRM": "R_forearm_wand",
}

# ISB-style names (Schreiber-Moissenet, Izmir) -> landmark; side prefix L_/R_ kept
ISB = {
    "IAS": "ASIS", "IPS": "PSIS", "FTC": "greater_trochanter", "FLE": "lat_femoral_epicondyle",
    "FME": "med_femoral_epicondyle", "FAX": "fibula_head", "TTC": "tibial_tuberosity",
    "FAL": "lat_malleolus", "TAM": "med_malleolus", "FCC": "calcaneus", "FM1": "1st_metatarsal_head",
    "FM2": "2nd_metatarsal_head", "FM5": "5th_metatarsal_head", "SIA": "acromion",
    "SRS": "scapula_spine_root", "SAA": "acromial_angle", "SAE": "acromial_edge",
    "HLE": "lat_humeral_epicondyle", "HME": "med_humeral_epicondyle", "UOA": "olecranon",
    "RSP": "radial_styloid", "UHE": "ulnar_styloid", "USP": "ulnar_styloid", "HM2": "2nd_metacarpal_head",
    "HM5": "5th_metacarpal_head", "HUM": "humerus_cluster", "HEAD": "head",
    "TH1": "thigh_cluster_1", "TH2": "thigh_cluster_2", "TH3": "thigh_cluster_3", "TH4": "thigh_cluster_4",
    "SK1": "shank_cluster_1", "SK2": "shank_cluster_2", "SK3": "shank_cluster_3", "SK4": "shank_cluster_4",
}
ISB_MIDLINE = {"CV7": "C7", "TV10": "T10", "SXS": "jugular_notch", "SJN": "xiphoid", "SGL": "glabella"}

# Moreira -> landmark
MOREIRA = {
    "ASIS": "ASIS", "PSIS": "PSIS", "TROC": "greater_trochanter", "TH1": "thigh_cluster_1",
    "LK": "lat_femoral_epicondyle", "MK": "med_femoral_epicondyle", "SK1": "shank_cluster_1",
    "LA": "lat_malleolus", "MA": "med_malleolus", "FM1": "1st_metatarsal_head", "FM2": "2nd_metatarsal_head",
    "FM5": "5th_metatarsal_head",
}

# technical markers (wands, clusters) keep a dataset-specific row: their placement is not a landmark
TECHNICAL = ("wand", "cluster")

PELVIS = ["L_ASIS", "R_ASIS", "L_PSIS", "R_PSIS", "sacrum"]
FEET = ["L_calcaneus", "R_calcaneus", "L_2nd_metatarsal_head", "R_2nd_metatarsal_head",
        "L_lat_malleolus", "R_lat_malleolus", "L_1st_metatarsal_head", "R_1st_metatarsal_head",
        "L_5th_metatarsal_head", "R_5th_metatarsal_head"]


def landmark_key(native, scheme):
    """Return (landmark name, shared key or None) for a marker label."""
    lm = None
    if scheme == "pig":
        lm = PIG.get(native)
    elif scheme == "isb":
        if native in ISB_MIDLINE:
            lm = ISB_MIDLINE[native]
        elif len(native) > 2 and native[1] == "_" and native[0] in "LR":
            base = ISB.get(native[2:])
            lm = native[0] + "_" + base if base else None
    elif scheme == "moreira":
        if native[0] in "LR":
            base = MOREIRA.get(native[1:])
            lm = native[0] + "_" + base if base else None
    if lm is None:
        return None, None
    if any(t in lm for t in TECHNICAL):
        return lm, None
    return lm, "landmark:" + lm


MUSCLES = {
    "tibialis anterior": "tibialis_anterior", "soleus": "soleus", "soleus medialis": "soleus_medialis",
    "soleus lateralis": "soleus_lateralis", "gastrocnemius medialis": "gastrocnemius_medialis",
    "gastrocnemuis medialis": "gastrocnemius_medialis", "gastrocnemius medial head": "gastrocnemius_medialis",
    "gastrocnemius lateralis": "gastrocnemius_lateralis", "gastrocnemius lateral head": "gastrocnemius_lateralis",
    "vastus medialis": "vastus_medialis", "vastus lateralis": "vastus_lateralis",
    "rectus femoris": "rectus_femoris", "semitendinosus": "semitendinosus",
    "biceps femoris": "biceps_femoris", "gluteus maximus": "gluteus_maximus", "gluteus medius": "gluteus_medius",
    "peroneus longus": "peroneus_longus", "peroneus brevis": "peroneus_brevis",
    "erector spinae": "erector_spinae",
}
VC_ABBREV = {"ERS": "erector_spinae", "RF": "rectus_femoris", "VL": "vastus_lateralis", "TA": "tibialis_anterior",
             "GAS": "gastrocnemius", "ST": "semitendinosus", "BF": "biceps_femoris"}


def muscle_key(side, name):
    m = MUSCLES.get(name.strip().lower().replace("_", " "))
    if m is None or side not in ("L", "R"):
        return None
    return "muscle:%s_%s" % (side, m)
