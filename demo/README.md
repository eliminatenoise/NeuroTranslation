# NeuroTranslate 0.0

Put compatible neural, muscle, displacement and mechanics recordings on a shared timeline. Each stream keeps its units, origin and source. Files stay in the browser; this application has no recording-upload endpoint.

This companion imports JSON and CSV, checks their structure, displays the original samples, and aligns declared paired recordings. It does not execute a trained translation model. The bundled example contains invented numbers, clearly labelled throughout the interface. It demonstrates the software rather than a biological relationship. [NeuroSurge](https://github.com/eliminatenoise/NeuroSurge), the separate arm-and-brain game, is still being developed.

Run `npm test` for the constructed-data and build checks, then `npm run build`. The build creates a stable `index.html`, versioned dependencies and a manifest in `dist`, replacing the previous output. Serve that directory over HTTP. No application dependencies or numerical frameworks are required.

## Import

Download the JSON example from the application for a complete packet. It contains `schemaVersion: 1`, one `dataset` object and a `streams` array. Dataset metadata includes ID, name, organism, subject, recording, task, clock (`timebase`), source URL, licence and partition (`split`). Each stream declares its ID, modality, label, unit, origin, timestamps in seconds and values. Values may be `null` where observations are missing.

The four modality values are `neural`, `muscle`, `displacement` and `mechanics`. Neural streams can declare `brain`, `spinal`, `peripheral`, `autonomic` or `visceral` as their region. A region label describes the supplied stream; it does not establish coverage elsewhere. EMG belongs to the muscle category.

A CSV file uses `time,value` columns. Enter its metadata in the import form and choose the signal type and origin explicitly. Leave the neural region unspecified when it is unknown. Unknown organism or identity fields permit inspection but prevent alignment. Import checks cannot verify the truth of supplied metadata or grant data rights.

Project-owned code is released under [CC0-1.0](LICENSE). Dataset and anatomical assets retain their own rights; see [RIGHTS.md](RIGHTS.md).

## Alignment

Recordings must declare the same organism, subject, recording and clock. Different data partitions remain separate. An unknown partition is not proof of an independent test set. Neural, muscle and movement signals from unrelated subjects are not synchronized merely because their tasks resemble one another.

Choose a sampling step, a maximum permitted gap and nearest-sample or linear interpolation. The result covers only the common time interval. Missing samples and gaps beyond the selected limit stay missing; values are not extrapolated. Units and coordinate frames are retained without conversion. Chart bins retain extrema and break at missing data; exports contain the aligned values and original packets.

File and combined-packet limits are 5 MiB, with at most 64 selected streams, 50,000 input samples, 5,000 aligned time points and 500,000 aligned values. These bounds protect browser responsiveness; they do not define a scientific sampling requirement. Metadata warnings remain visible when source rights, partitions or coordinate frames are unknown.

## Metadata checks

Open **Metadata checks** beside the signal explorer to inspect each stream's declared measurement, units, clock, identity and provenance. Missing or conflicting details remain visible. The generic invented example deliberately lacks measurement and generator details; plotting its numbers does not make those declarations complete.

The report keeps exact source IDs beside their encoded internal IDs, plus the origin of each mapped field. A generic EMG label never becomes a surface or intramuscular recording by guesswork. A licence string grants no permission, and matching subjects or clock names creates no biological pairing. Alignment continues to follow the separately declared common clock; it does not establish acquisition synchronization.

Export the metadata report independently, or retain it with an aligned-data export. Both include the original packets, mapping diagnostics and declaration checks. Metadata fingerprints identify the supplied declarations; they do not authenticate a recording or certify its sample values. No recording contents leave the browser through this feature. [Metadata format and API](docs/METADATA.md) describes optional richer declarations.

## What remains

The whole-body ambition includes brain, spinal, peripheral and relevant autonomic or visceral activity. The catalogue currently establishes separate, limited source examples. It does not establish one dataset covering all those regions, paired with all muscle, movement and mechanics observations.

A functioning learned translation needs separately qualified adapters and a validated model, with measured error, uncertainty, held-out comparisons and failure reporting. Those are still pending. Dataset reference cards link to existing sources; no recordings or third-party model assets are bundled here. This interface does not supply stimulation, clinical decisions or biological validation.
