# Bridge API

`toPolicyDescriptor(stream, dataset, options = {})` returns:

| Field | Meaning |
|---|---|
| `status` | `mapped` or `input_rejected`; this is a mapping result, not policy or scientific acceptance |
| `descriptor` | Policy descriptor v1, or null after any fatal mapping error |
| `identityMap` | Exact original dataset/stream IDs and their encoded policy IDs |
| `declarationOrigins` | Source field and basis for each mapped field |
| `appliedBindings` | Explicit caller measurement bindings, including original value and provenance |
| `diagnostics` | Mapping codes, severity, paths and explanations |
| `policyValidation` | The frozen policy core's complete single-descriptor validation result |
| `mappingFingerprint` | SHA-256 identifying the identity map, descriptor, bindings and diagnostics; it proves no authenticity |

`toPolicyEnvelope(packets)` accepts 1–64 already parsed and validated packet-v1 objects, with at most 64 selected streams and 50,000 total samples. It returns `policyInput: {descriptors, links: []}` plus `identityMap`, `streamResults`, diagnostics and fixed no-pairing/no-inference flags. Any fatal mapping error blocks the whole envelope. There is no partial-success policy input and no automatic pairing, even when subjects, sessions, URLs and clocks match. Explicit pairing or unpaired display proposals belong to the caller and the policy's own link/evidence API.

The companion remains responsible for packet parsing, its 5 MiB input limit and full packet validation. This bridge is a projection of that accepted format. It adds target-limit, identity, sample-shape and declaration-conflict checks; it does not replace the companion validator. It copies finite scalar sample arrays for counting without modifying the source arrays. No masking, sentinel repair, resampling or unit conversion occurs here.

## Packet fields

| Source | Descriptor | Mapping rule |
|---|---|---|
| Complete `dataset.id` and `stream.id` | Encoded `dataset.id` and `streamId` | Full SHA-256 of domain-separated canonical JSON tuples; no delimiter joining, Unicode normalization or truncation |
| `modality` | `modality` | `neural` → `neural`; `muscle` → `myographic`; `displacement` → `motion`; `mechanics` → `mechanics` |
| Neural `region` | `neural.division` | `brain`, `spinal`, `peripheral` retain their names; `autonomic` and `visceral` → `autonomic_visceral`; unknown regions stay absent |
| `measurement` | `measurement` | Exact declaration; missing or uncontrolled measurements remain missing or invalid; labels, units and `signalType` supply no substitute |
| `origin` | `origin` | Exact stream declaration; `dataset.origin` never overrides it |
| `unit` | `quantity.unit` | Exact string, including case and whitespace |
| `frame` | `frame.id` | Free-text identity only; no frame kind or handedness follows from its name |
| `dataset.timebase`, `rateHz` | `clock.domain`, `clock.rateHz` | Declared values only; `clock.unit: s` follows the packet-v1 timestamp contract |
| First/last source timestamp | `interval.start`, `interval.end` | Observed endpoints; uncertainty remains unknown |
| `subjectId`, `organism`, `recordingId` | Subject ID/species and session ID | Exact declarations; no namespace, taxon or cross-dataset identity is supplied |
| `dataset.license` | `rights.dataLicence` | Exact declaration; neither openness nor redistribution is derived from its wording |
| `dataset.split` | `role.split` | `held_out` → `heldout`, `unspecified` → `unknown`; other policy split spellings pass exactly; `fixture` stays unmapped |
| Scalar nullable `values` | `channels.count: 1`, null encoding and missing count | Structural facts from packet v1; channel names/order and temporal gaps stay undeclared |
| `t`, `values` | `observations` | The whole `summarizeObservations(t, values)` result, including timestamp-quality flags |

Each original identity accepts the packet limit of 2,000 characters. Policy IDs use the complete 64-hex digest, within the 128-character policy-ID limit. The sidecar preserves the exact original strings. The envelope rejects duplicate original identities, conflicting dataset declarations, and observed digest collisions for dataset or stream IDs. SHA-256 provides collision resistance, not a mathematical guarantee of injectivity; a detected collision blocks mapping rather than collapsing records.

Other metadata passes through the policy core's 512-character string, object, array and depth limits. Overlimit metadata blocks mapping with explicit diagnostics. Nothing is silently shortened. Even source metadata used only for display is checked conservatively; a companion-valid packet can therefore require a target-metadata correction before this bridge maps it.

## Richer native declarations

Packet v1 preserves extra metadata. This bridge recognizes an explicit `policyMetadata` object on the dataset or stream. The name marks the source's richer declarations; a declaration is still self-attested. No metadata object is created merely to make a descriptor pass.

| Location | Supported fields |
|---|---|
| `dataset.policyMetadata` | `sourceId`, `sourceFamily`, `subject`, `session`, `rights`, `role.negativeControl` |
| `stream.policyMetadata` | `measurement`, `side`, `neural`, `provenance`, `quantity`, `frame`, `clock`, `interval`, `subject`, `session`, `rights`, `role.negativeControl`, `missingness`, `channels` |

Structured fields use the frozen policy's documented schema. Source metadata can explicitly declare frame kind/handedness, identity namespaces, source identity, taxon, clock uncertainty/drift/sync time, interval uncertainty, rights status/redistribution, generator, lineage, gaps or channel order. Only the declared fields are copied. Missing fields receive no defaults. Unsupported fields or conflicting declarations block mapping; the original split, unit, frame, clock and origin cannot be silently replaced. `role.split` inside `policyMetadata` is deliberately unsupported: the packet's dataset split owns that field.

Lineage references (`derivedFrom`, `generator.sourceMotion`, negative-control `of`) must already be explicit policy stream IDs obtained from the identity map. They are copied exactly. The bridge never interprets a raw label as a source, searches for matching strings, or constructs lineage from a filename. The policy's full `evaluate` call remains necessary for cross-descriptor lineage checks. Single-descriptor validation cannot perform those checks.

## Caller measurement binding

The optional single-stream call accepts:

```js
const mapping = toPolicyDescriptor(stream, dataset, {
  measurementBinding: {
    value: controlledMeasurement,
    provenance: { source: declarationSource, ref: declarationReference }
  }
});
```

`value` must exactly name a controlled measurement. `provenance.source` and `provenance.ref` must be non-placeholder strings within the policy limits. The caller supplies those facts; the bridge does not verify their source. The binding can resolve a missing or uncontrolled measurement, but cannot replace a different controlled native measurement. Its native value, provenance and `explicit_caller_binding` origin remain in the returned record. Keep that record with the descriptor; discarding it would hide the distinction from native declarations. The envelope API applies no bindings automatically.

## Verification scope

The portable metadata tests exercise constructed packets through the installed modules. The browser view reports file declarations and missing details. Neither proves recording identity, synchronization, data rights, whole-body neural coverage, calibrated mechanics or a validated translation model. Those require independent source and measurement evidence.
