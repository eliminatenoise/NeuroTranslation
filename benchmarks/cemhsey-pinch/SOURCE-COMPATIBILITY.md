# An unused tail in the force record

The acquisition paper describes force recordings with 6,016 to 6,048 samples. During source checks, one original training member had 6,060. Its file integrity, variable names, real double types, one-row force matrix and paired 320-channel muscle matrix all checked out. The parser initially stopped because it treated the paper’s descriptive range as a mandatory file format. No model had been fitted or scored.

The [prespecified protocol](PROTOCOL.md) had already limited the evaluation to the first 6,000 force samples. The final target uses index 5,994, with index zero at the first released sample. The additional tail supplies no feature or target. We retain the paper’s range as a separate comparison flag. A discrepant but intact trial can enter numerical work only after review of its exact member identity, type, shape, source pairing, checksum and full fixed window. A shorter record lacking required support, a different instrument, an invalid field or a failed integrity check still suspends the relevant stage.

The roster, clock convention, 592 issue indices per trial, matched-repeat control, penalty, contrasts and outcome measures are unchanged. The longer stored tail supplies no estimate of the relative start times of the two devices. [Acquisition paper and data records](https://doi.org/10.1038/s41597-025-05733-y)
