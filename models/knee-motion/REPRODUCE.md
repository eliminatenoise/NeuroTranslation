# Reproduce the treadmill forecast

The example and released predictions need Python and NumPy. Fitting the weights also needs PyTorch. The reported fit used Python 3.13.15, NumPy 2.4.6 and PyTorch 2.14.1+cpu, two PyTorch CPU threads, a single inter-op thread and one OpenBLAS thread. Give the scripts fresh output paths.

1. Obtain the 1.0.0 `IMU.tar.gz` from the official PhysioNet release. It is 3,922,799,402 bytes. The extractor checks the archive SHA-256 against the published index and writes only the selected 0.5 m/s joint-angle CSVs. It prints the counts for two fields in the matching technical headers, frame rate and processing quality. Compare them with `technical-summary.json`. The archive and the extracted participant files stay on your machine. [Official archive](https://physionet.org/files/multimodal-gait-dataset/1.0.0/Dataset/IMU_Data/IMU.tar.gz) · [Published checksums](https://physionet.org/files/multimodal-gait-dataset/1.0.0/SHA256SUMS.txt)

2. Extract, fit and score. Run from this folder.

   ```sh
   python extract.py IMU.tar.gz trials
   python fit.py trials reproduced-weights.json local-training.json --threads 2
   python assess.py trials reproduced-weights.json local-training.json reproduced-results.json reproduced-sources.json local-test.json
   python prior_stride.py trials
   ```

   The last command uses the released weights and source hashes. To test your fit on the same cutoffs, append `--weights reproduced-weights.json --sources reproduced-sources.json`. The two local reports include participant-level quality checks. The public tables report aggregate errors.

3. Check the source members against `sources.json`, which records the selected archive paths, per-file hashes, split, row counts and eligible windows. The numerical fit and inference may vary slightly between math libraries. The released weights have SHA-256 `cd876eac2165d40b43386643de99178807dc384cc0915abcff3fe92750018efc`. The independently recomputed held-participant mean absolute error was 4.4669008192°.

## Windows and fitting

The split uses IDs 1–40 for training, including the format-development file S1, and IDs 41–52 for testing. The source lists the S24 recording as missing. IDs 53–59 and the other treadmill speeds were reserved. These ranges select the cohort by availability. They do not constitute a random sample of a wider population.

Each window requires 40 consecutive finite source frames from cutoff −24 through cutoff +15. All six angles come from the same file. The predictors read just five frames within the first 25, and the targets are both knees at +15. No missing values are filled. The check for complete targets determines which windows can be scored and supplies no future values to the predictor. None of the 51 included six-column traces was an exact duplicate. No 5×6 model input appeared verbatim in both partitions. Moving every angle after an interior cutoff in each test trial by 123° changed its target by 123° and every model forecast by 0°.

Both ridge fits predict the difference from the last known knee angles. They standardize each flattened feature using training participants with equal weight. The fitted intercept is the mean knee-angle change. A diagonal penalty of 0.001 is applied to the mean standardized covariance matrix.

The Transformer is a gait specialist trained from scratch. It embeds each snapshot in 24 dimensions, adds a learned position vector and mixes the five historical snapshots using four attention heads. A 48-unit feedforward layer and the last token produce two changes in knee angle. All five tokens precede the requested endpoint. AdamW takes 700 updates, with a learning rate of 0.002 and weight decay of 0.001. Each update draws 128 training people with replacement and one uniformly sampled eligible cutoff for each draw. The loss is mean squared error after expressing the change in units of 20°. The seed is 81037. The final checkpoint was fixed before testing.

The longer-history comparator searches integer stride periods from 45 through 180 frames. For each period it compares the last 60 bilateral knee samples with the 60 samples one candidate period earlier and sums squared differences. The shortest minimizing period wins. The forecast copies the stored pair at cutoff + 15 − period, still inside its history. Its four-second eligibility rule and its direct comparison with the Transformer are in `prior_stride.py`.

Uncertainty comes from 10,000 participant-level bootstrap resamples with seed 21301. The same resampled people contribute to both sides of a comparison. The intervals describe this held cohort, one speed and one acquisition system. Generalization to other speeds, environments, populations and independent physical measurements remains open.
