/* Controlled vocabulary for the NeuroTranslate 0.0 compatibility policy (r1).
 * Pure data. Every list is closed: a value outside it is reported, never mapped
 * to the nearest match. Programme terms follow the shared glossary (revision 36,
 * sha256 40b98695...): four source groups (neural, myographic, measured motion,
 * physics-generated), myoception, NeuroTranslate 0.0 as an unvalidated development
 * model name, and NeuroSurge as the separate game-demo name. */

const freezeDeep = o => { Object.values(o).forEach(v => { if (v && typeof v === 'object') freezeDeep(v); }); return Object.freeze(o); };

/** What a stream represents. 'physiological_context' holds ECG, respiration and
 * similar signals that are useful context but are not neural recordings. */
export const MODALITIES = freezeDeep(['neural', 'myographic', 'motion', 'mechanics', 'physiological_context']);

/** How the values came to exist. 'derived' = computed from other data by a declared
 * pipeline (for example, video-estimated pose); 'inferred' = model output;
 * 'simulated' = produced by a physics/musculoskeletal or other simulator. */
export const ORIGINS = freezeDeep(['measured', 'derived', 'inferred', 'simulated', 'unknown']);

/** Whole-body neural scope: each division is reported separately per dataset. */
export const NEURAL_DIVISIONS = freezeDeep(['brain', 'spinal', 'peripheral', 'autonomic_visceral']);
export const NEURAL_DIRECTIONS = freezeDeep(['efferent', 'afferent', 'mixed']);

export const FRAME_KINDS = freezeDeep(['cartesian_3d', 'cartesian_2d', 'image_2d', 'joint_space', 'sensor_local', 'none']);
export const SPLITS = freezeDeep(['train', 'validation', 'test', 'heldout', 'unassigned', 'unknown']);
export const NEGATIVE_CONTROL_KINDS = freezeDeep(['shuffled', 'time_shifted', 'surrogate', 'sham', 'other']);
export const RIGHTS_STATUSES = freezeDeep(['declared_open', 'declared_restricted', 'unknown']);
export const REDISTRIBUTION = freezeDeep(['allowed', 'not_allowed', 'unknown']);
export const MISSING_ENCODINGS = freezeDeep(['none', 'null', 'mask']);
export const PURPOSES = freezeDeep(['inspection', 'display', 'training', 'evaluation', 'publication', 'clinical', 'causal_analysis']);
export const RESAMPLE_METHODS = freezeDeep(['linear', 'nearest', 'previous_sample_hold']);
/** Methods that read a sample later than the output time (non-causal). */
export const NON_CAUSAL_METHODS = freezeDeep(['linear', 'nearest']);

/** Evidence kinds. Admissible kinds only ever make a claim "declared"; a
 * verifier_record counts only when it matches a caller-supplied registry entry. */
export const ADMISSIBLE_EVIDENCE = freezeDeep(['self_attestation', 'header_field', 'verifier_record']);
/** Never evidence of same person, session or time. */
export const INADMISSIBLE_EVIDENCE = freezeDeep(['equal_identifiers', 'equal_labels', 'coincident_timestamps', 'shared_source_family', 'same_file', 'filename_pattern']);
export const REGISTRY_CLAIMS = freezeDeep(['sameSubject', 'sameSession', 'sameTime', 'clockMapping', 'frameTransform', 'derivation']);

const ALL = NEURAL_DIVISIONS;
const VOLT = ['voltage', 'arbitrary'];
/** measurement -> { modality, divisions (neural), dims (allowed unit dimensions),
 *  family, simulatedOnly, estimateOnly, other } */
export const MEASUREMENTS = freezeDeep({
  // neural
  spikes: { modality: 'neural', divisions: ALL, dims: ['count', 'event_rate', 'voltage', 'arbitrary'], eventRate: true },
  multiunit_threshold_crossings: { modality: 'neural', divisions: ALL, dims: ['count', 'event_rate', 'arbitrary'], eventRate: true },
  lfp: { modality: 'neural', divisions: ALL, dims: VOLT },
  calcium_imaging: { modality: 'neural', divisions: ALL, dims: ['fluorescence_ratio', 'dimensionless', 'arbitrary'] },
  eeg: { modality: 'neural', divisions: ['brain'], dims: VOLT },
  meg: { modality: 'neural', divisions: ['brain'], dims: ['magnetic_flux_density', 'arbitrary'] },
  ecog: { modality: 'neural', divisions: ['brain'], dims: VOLT },
  seeg: { modality: 'neural', divisions: ['brain'], dims: VOLT },
  esg_surface: { modality: 'neural', divisions: ['spinal'], dims: VOLT },
  intraspinal_electrophysiology: { modality: 'neural', divisions: ['spinal'], dims: ['voltage', 'count', 'event_rate', 'arbitrary'], eventRate: true },
  dorsal_root_ganglion: { modality: 'neural', divisions: ['peripheral'], dims: ['voltage', 'count', 'event_rate', 'fluorescence_ratio', 'arbitrary'], eventRate: true },
  eng_peripheral_nerve: { modality: 'neural', divisions: ['peripheral', 'autonomic_visceral'], dims: ['voltage', 'count', 'event_rate', 'arbitrary'], eventRate: true },
  microneurography: { modality: 'neural', divisions: ['peripheral', 'autonomic_visceral'], dims: ['voltage', 'count', 'event_rate', 'arbitrary'], eventRate: true },
  vagus_nerve: { modality: 'neural', divisions: ['autonomic_visceral'], dims: ['voltage', 'count', 'event_rate', 'arbitrary'], eventRate: true },
  enteric_nervous_system: { modality: 'neural', divisions: ['autonomic_visceral'], dims: ['voltage', 'count', 'event_rate', 'fluorescence_ratio', 'arbitrary'], eventRate: true },
  /** A simulated neural drive (for example NeuroSurge's gaze/WASD-selected cortical response field): a unitless display value, never a recording. */
  simulated_neural_drive: { modality: 'neural', divisions: ALL, dims: ['dimensionless', 'arbitrary'], simulatedOnly: true },
  other_neural: { modality: 'neural', divisions: ALL, dims: ['voltage', 'magnetic_flux_density', 'count', 'event_rate', 'frequency', 'fluorescence_ratio', 'dimensionless', 'arbitrary'], other: true },
  // myographic (muscle). EMG is muscle electrical activity, not a nerve recording.
  emg_surface: { modality: 'myographic', family: 'emg', dims: ['voltage', 'normalized_activation', 'arbitrary'] },
  emg_intramuscular: { modality: 'myographic', family: 'emg', dims: ['voltage', 'normalized_activation', 'arbitrary'] },
  emg_high_density: { modality: 'myographic', family: 'emg', dims: ['voltage', 'normalized_activation', 'arbitrary'] },
  mechanomyography: { modality: 'myographic', dims: ['acceleration', 'voltage', 'arbitrary'] },
  muscle_ultrasound: { modality: 'myographic', dims: ['length', 'angle', 'dimensionless', 'arbitrary'] },
  simulated_muscle_activation: { modality: 'myographic', simulatedOnly: true, dims: ['dimensionless', 'arbitrary'] },
  other_myographic: { modality: 'myographic', dims: ['voltage', 'normalized_activation', 'acceleration', 'length', 'angle', 'dimensionless', 'arbitrary'], other: true },
  // measured or simulated motion
  marker_mocap_3d: { modality: 'motion', dims: ['length'], cartesian: true },
  markerless_pose_3d: { modality: 'motion', dims: ['length'], cartesian: true, estimateOnly: true },
  video_pose_2d: { modality: 'motion', dims: ['image_length', 'dimensionless'], image: true, estimateOnly: true },
  imu: { modality: 'motion', dims: ['acceleration', 'angular_velocity', 'angle', 'dimensionless'] },
  glove_joint_angles: { modality: 'motion', dims: ['angle'], jointAngles: true },
  joint_angles: { modality: 'motion', dims: ['angle'], jointAngles: true },
  goniometer: { modality: 'motion', dims: ['angle'], jointAngles: true },
  simulated_kinematics: { modality: 'motion', simulatedOnly: true, dims: ['length', 'angle', 'velocity', 'angular_velocity'] },
  other_motion: { modality: 'motion', dims: ['length', 'image_length', 'angle', 'velocity', 'angular_velocity', 'acceleration', 'dimensionless'], other: true },
  // mechanics (forces, torques, contact)
  force_plate: { modality: 'mechanics', dims: ['force', 'torque', 'length'] },
  load_cell: { modality: 'mechanics', dims: ['force', 'torque'] },
  joint_torque_estimate: { modality: 'mechanics', estimateOnly: true, dims: ['torque'] },
  contact_pressure: { modality: 'mechanics', dims: ['pressure', 'force'] },
  tactile_array: { modality: 'mechanics', dims: ['pressure', 'force', 'arbitrary'] },
  simulated_contact_force: { modality: 'mechanics', simulatedOnly: true, dims: ['force'] },
  simulated_joint_torque: { modality: 'mechanics', simulatedOnly: true, dims: ['torque'] },
  other_mechanics: { modality: 'mechanics', dims: ['force', 'torque', 'pressure', 'length', 'dimensionless', 'arbitrary'], other: true },
  // physiological context: not neural recordings
  ecg: { modality: 'physiological_context', dims: VOLT },
  respiration: { modality: 'physiological_context', dims: ['length', 'pressure', 'dimensionless', 'arbitrary'] },
  blood_pressure: { modality: 'physiological_context', dims: ['pressure'] },
  skin_conductance: { modality: 'physiological_context', dims: ['conductance'] },
  other_context: { modality: 'physiological_context', dims: ['voltage', 'pressure', 'conductance', 'length', 'frequency', 'dimensionless', 'arbitrary'], other: true },
});

/** Unit table. Exact, case-sensitive spellings; no prefix parsing, no guessing.
 * dimension = quantity kind used for compatibility; si = SI base signature
 * (null when the unit has no physical scale). factor converts to the kind's base. */
const U = (dimension, si, factor) => ({ dimension, si, factor });
export const UNITS = freezeDeep({
  V: U('voltage', 'kg m2 s-3 A-1', 1), mV: U('voltage', 'kg m2 s-3 A-1', 1e-3),
  uV: U('voltage', 'kg m2 s-3 A-1', 1e-6), 'µV': U('voltage', 'kg m2 s-3 A-1', 1e-6), 'μV': U('voltage', 'kg m2 s-3 A-1', 1e-6),
  T: U('magnetic_flux_density', 'kg s-2 A-1', 1), fT: U('magnetic_flux_density', 'kg s-2 A-1', 1e-15),
  m: U('length', 'm', 1), cm: U('length', 'm', 1e-2), mm: U('length', 'm', 1e-3),
  px: U('image_length', 'px', 1),
  rad: U('angle', '1', 1), deg: U('angle', '1', Math.PI / 180),
  'rad/s': U('angular_velocity', 's-1', 1), 'deg/s': U('angular_velocity', 's-1', Math.PI / 180),
  'm/s': U('velocity', 'm s-1', 1), 'mm/s': U('velocity', 'm s-1', 1e-3),
  'm/s^2': U('acceleration', 'm s-2', 1),
  N: U('force', 'kg m s-2', 1), kN: U('force', 'kg m s-2', 1e3),
  'N*m': U('torque', 'kg m2 s-2', 1), 'N·m': U('torque', 'kg m2 s-2', 1), Nm: U('torque', 'kg m2 s-2', 1),
  Pa: U('pressure', 'kg m-1 s-2', 1), kPa: U('pressure', 'kg m-1 s-2', 1e3), mmHg: U('pressure', 'kg m-1 s-2', 133.322387415),
  S: U('conductance', 'kg-1 m-2 s3 A2', 1), uS: U('conductance', 'kg-1 m-2 s3 A2', 1e-6), 'µS': U('conductance', 'kg-1 m-2 s3 A2', 1e-6), 'μS': U('conductance', 'kg-1 m-2 s3 A2', 1e-6),
  s: U('time', 's', 1), ms: U('time', 's', 1e-3),
  Hz: U('frequency', 's-1', 1), 'spikes/s': U('event_rate', 's-1', 1),
  count: U('count', '1', 1), spikes: U('count', '1', 1),
  1: U('dimensionless', '1', 1), ratio: U('dimensionless', '1', 1), '%': U('dimensionless', '1', 0.01),
  '%MVC': U('normalized_activation', '1', 0.01),
  'dF/F': U('fluorescence_ratio', '1', 1),
  'a.u.': U('arbitrary', null, null), au: U('arbitrary', null, null), arb: U('arbitrary', null, null),
});
export const DIMENSIONS = freezeDeep([...new Set(Object.values(UNITS).map(u => u.dimension))].sort());

/** Spellings that name more than one unit. They are never resolved. */
export const AMBIGUOUS_UNITS = freezeDeep({
  g: 'gram (mass) or standard gravity (acceleration)',
  G: 'gauss, giga- or standard gravity',
  M: 'molar or the mega- prefix',
  u: 'micro- or the atomic mass unit',
  'deg C': 'temperature, not an angle',
  sec: 'second or angular arcsecond',
});

/** Clock units accepted for timestamps and intervals, as divisors to seconds
 * (value / divisor is correctly rounded; multiplying by 1e-3 is not). */
export const TIME_UNIT_DIVISORS = freezeDeep({ s: 1, ms: 1000 });

/** Pairs of quantity kinds that share SI base units and have a meaningful, owner-defined
 * relation (a rate definition, or an MVC normalisation reference). Every other same-SI pair
 * of different kinds is a dimension mismatch. */
export const ADJACENT_KINDS = freezeDeep([['event_rate', 'frequency'], ['dimensionless', 'normalized_activation']]);

/** How a simulator actuates the body. muscle_excitation drives a muscle model; schematic_rules gives a schematic
 * (display) muscle drive; joint-level actuation never produces muscle activation. */
export const SIMULATION_ACTUATIONS = freezeDeep(['muscle_excitation', 'schematic_rules', 'joint_pd_targets', 'joint_torque', 'kinematic_playback', 'other']);
/** Joint-level actuation: its output is never muscle activation. */
export const JOINT_LEVEL_ACTUATIONS = freezeDeep(['joint_pd_targets', 'joint_torque', 'kinematic_playback']);

/** Body side (for a neural stream: hemisphere). */
export const SIDES = freezeDeep(['left', 'right', 'bilateral', 'midline']);

/** Frame transform types. Rigid, rotation, translation and similarity transforms preserve handedness; a reflection
 * always changes it; affine, homography and other declared transforms may change it. */
export const TRANSFORM_TYPES = freezeDeep(['rigid', 'rotation', 'translation', 'reflection', 'similarity', 'affine', 'homography', 'other']);
export const HANDEDNESS_CHANGING_TRANSFORMS = freezeDeep(['reflection', 'affine', 'homography', 'other']);

/** Licence identifiers that grant rights to software, not to data. The lists cover common licences only; the rights owner decides the rest.
 * - Bare short ids are case-sensitive whole tokens, so the German word 'mit' or the dataset name 'MIT-BIH' is not a licence.
 * - Versioned SPDX-style ids are case-insensitive ('gpl-3.0', 'bsd-3-clause', 'mpl-2.0', 'python-2.0').
 * - A whole value that is just a short id is case-insensitive ('mit', 'isc', 'Apache').
 * - Full licence names are case-insensitive. */
export const SOFTWARE_LICENCE_SHORT_RE = /(^|[^A-Za-z0-9])(MIT(?![-_ ]?BIH)(?:-0)?|ISC|0BSD|BSD(?:[-_ ]?[0-9]+(?:[-_ ]?Clause)?)?|[AL]?GPL(?:[-_ ]?v?[0-9.]+)?|GNU|MPL(?:[-_ ]?[0-9.]+)?|EPL(?:[-_ ]?[0-9.]+)?|BSL(?:[-_ ]?[0-9.]+)?|CDDL(?:[-_ ]?[0-9.]+)?|EUPL(?:[-_ ]?[0-9.]+)?|MS-PL|WTFPL|PSF(?:[-_ ]?[0-9.]+)?|CNRI-Python)(?=[^A-Za-z0-9]|$)/u;
export const SOFTWARE_LICENCE_SPDX_RE = /(^|[^A-Za-z0-9])((?:[al]?gpl|mpl|epl|bsl|cddl|eupl|psf|python|apache|artistic)[-_ ]?v?[0-9][0-9.]*(?:[-_ ]?(?:only|or[-_ ]later)|\+)?|bsd[-_ ]?[0-9](?:[-_ ]?clause(?:[-_ ][a-z]+)?)?|mit-0|0bsd|ms-[pr]l|cnri-python|wtfpl|zlib|unlicense)(?=[^A-Za-z0-9]|$)/iu;
export const SOFTWARE_LICENCE_NAME_RE = /(^|[^A-Za-z0-9])(Apache[-_ ]Licen[cs]e|Artistic[-_ ]Licen[cs]e|Boost[-_ ]Software(?:[-_ ]Licen[cs]e)?|Zlib[-_ ]Licen[cs]e|MIT[-_ ]Licen[cs]e|ISC[-_ ]Licen[cs]e|BSD[-_ ]Licen[cs]e|Python[-_ ]Licen[cs]e|(?:Lesser |Library |Affero )?General Public Licen[cs]e|Mozilla Public Licen[cs]e|Eclipse Public Licen[cs]e|Python Software Foundation|Common Development and Distribution Licen[cs]e|European Union Public Licen[cs]e|Microsoft Public Licen[cs]e|Do What The F\S* You Want To Public Licen[cs]e)(?=[^A-Za-z0-9]|$)/iu;
const SOFTWARE_LICENCE_WHOLE = ['mit', 'isc', 'bsd', 'gpl', 'lgpl', 'agpl', 'gnu gpl', 'mpl', 'epl', 'bsl', 'cddl', 'eupl', 'psf', 'apache', 'boost', 'artistic', 'zlib', 'wtfpl', 'python'];
/** Does licence text name a software licence? */
export const namesSoftwareLicence = text => {
  if (typeof text !== 'string') return false;
  const whole = text.normalize('NFKC').toLowerCase().replace(/[^a-z0-9]+/gu, ' ').replace(/ (?:licen[cs]e|software licen[cs]e)$/u, '').trim();
  return SOFTWARE_LICENCE_WHOLE.includes(whole) || SOFTWARE_LICENCE_SHORT_RE.test(text) || SOFTWARE_LICENCE_SPDX_RE.test(text) || SOFTWARE_LICENCE_NAME_RE.test(text);
};
const LICENCE_PLACEHOLDER_RE = /^(?:no|none|nil|unknown|unspecified|undeclared|undefined|unclear|pending|missing|other|unlicen[cs]ed|tb[acd]|n ?a|n\/a|(?:no|none|not)(?: (?:yet|currently))? (?:specified|stated|declared|available|provided|given|applicable|known|set|defined|selected|chosen|confirmed|determined|decided|found)|to be (?:confirmed|determined|decided|announced|added|defined|specified)|see .*|\?+|-+)$/u;
/** Is licence text a placeholder rather than a licence ('Unknown license', 'No license provided', 'None specified', 'To be confirmed')? */
export const isLicencePlaceholder = text => {
  if (typeof text !== 'string') return true;
  const t = text.normalize('NFKC').toLowerCase().replace(/[^a-z0-9/?-]+/gu, ' ').replace(/(^| )(?:data|licen[cs]e[sd]?|licensing|terms)(?= |$)/gu, ' ').replace(/ +/gu, ' ').trim();
  return t === '' || UNKNOWN_WORDS.includes(t) || LICENCE_PLACEHOLDER_RE.test(t);
};

/** Unknown spellings treated as "not declared" for identifiers. */
export const UNKNOWN_WORDS = freezeDeep(['unknown', 'unspecified', 'n/a', 'na', '?', 'none', 'null', 'undefined', 'tbd', 'tba', 'not specified', 'not stated', 'not declared', 'not applicable', '']);

/** Descriptor fields that try to assert pairing inside one stream's metadata. They are
 * ignored: pairing is only ever proposed through a link, with evidence. */
export const PAIRING_FIELD_NAMES = freezeDeep(['paired', 'pairedWith', 'pairing', 'synchronized', 'synchronised', 'synchronizedWith', 'sameSubjectAs', 'sameSessionAs', 'alignedWith', 'syncedTo']);
