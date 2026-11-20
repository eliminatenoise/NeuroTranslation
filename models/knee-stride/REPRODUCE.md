# Reproduce the two-knee forecast

The example needs Python and NumPy. Training also needs PyTorch. The reported run used CPU PyTorch 2.14.1+cpu and NumPy 2.5.3. Run the commands in this directory. On Windows, use your Python interpreter and set the three thread environment variables in your shell before training.

1. Download version 1.0.0 of the IMU archive from PhysioNet. The extractor verifies the archive SHA-256 against the published checksum and selects the admitted 0.5 m/s joint-angle files. It reads two technical header fields to check the acquisition context. The 51 files report 60 Hz. Six list HD processing and 45 list Live processing. Those labels describe vendor processing. The time at which each displayed angle would become available to a live system remains unknown. [IMU archive](https://physionet.org/files/multimodal-gait-dataset/1.0.0/Dataset/IMU_Data/IMU.tar.gz) · [Published checksums](https://physionet.org/files/multimodal-gait-dataset/1.0.0/SHA256SUMS.txt)

   ```sh
   python extract.py IMU.tar.gz trials
   ```

2. Fit to the 39 training participants. Use fresh filenames. The saved JSON contains both sets of fitted weights and all parameters for inference. The fit receipt identifies each admitted source member, each set of forecast cutoffs and the end-of-training checkpoint.

   ```sh
   OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 python fit.py trials reproduced-weights.json local-fit.json --threads 2
   ```

3. Apply that checkpoint to the previously studied 12 evaluation participants. The script checks all source hashes before reading the arrays. It computes errors for every person, including both knees separately, and the three paired comparisons. It also compares the direct prefix predictor with the faster evaluation implementation on 36 cutoffs and changes later observations to test future independence.

   ```sh
   OPENBLAS_NUM_THREADS=1 python evaluate.py trials reproduced-weights.json local-fit.json reproduced-results.json
   python predict.py example.json --weights reproduced-weights.json
   ```

The prefix listed in `example.json` is invented. Its two angle curves combine sinusoids and slow linear drift. The expected answer for the released checkpoint is in `example-prediction.json`. Numerical differences across math libraries are possible.

## Input and scoring details

Each admitted source member contains Xsens joint angles expressed using the ZXY convention. The input at frame *i* is 240 consecutive right/left knee samples ending at *i*. The target is the stored pair at *i* + 15. The original experiment required complete finite values across six joint channels from *i* − 24 through *i* + 15. We retain that same eligibility check so that the comparison uses the original cutoffs. The two knee channels alone supply predictor values. Eligibility for retrospective scoring requires a future label. Running a forecast requires only the prefix.

Stride matching searches periods of 45 through 180 frames. For each candidate, it sums squared right and left angle differences between the most recent 60 frames and their shifted counterparts. The shortest minimizing period wins. Copying the knee pair 15 frames after that earlier match gives the forecast.

Both learned models receive the same nine snapshots within the prefix. Each snapshot carries the current knees, the knees one estimated period earlier, the earlier knees shifted forward another 15 frames, three-frame angle changes for the current and earlier knees, and the estimated period. Ridge regression estimates one linear correction. The Transformer learns how much weight to give each snapshot for this particular history. Both add their correction to the same copied knee pair. The registered offsets, feature order, training objective, architecture, update count, random seeds and decision criteria are recorded in the protocol. [Protocol](protocol.json)

Each participant contributes one average absolute error per method. Their two knees and thousands of overlapping windows are repeated observations. The 95% intervals resample whole participants, preserving the three errors for each sampled person. Each reported interval describes one comparison on this reused cohort. Follow-up work needs an independent cohort and a test of live frame availability.
