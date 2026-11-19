"use strict";

// Eight invented trials, separate from the on-screen example.
globalThis.CEMHSEY_ARRAY_PROFILE = {
  "format": "cemhsey-pinch-interval-profile-v1",
  "reader_fit_sha256": "4022896bfbe47f2675a0728a7b7e99bc930fd37898e19f14e119f441c9f588ef",
  "protocol_sha256": "44bc615272587c66b90a10be4208168501539d0ab3eb10a929040a80a3848082",
  "timing_mode": "nominal_release_index",
  "profile_origin": "invented_signals",
  "nominal_coverage": 0.9,
  "pooled_count": 4736,
  "phase_counts": {
    "initial_rest": 752,
    "ramp_up": 800,
    "hold": 1600,
    "release": 800,
    "final_rest": 784
  },
  "half_widths": {
    "persistence": {
      "pooled": 0.010009483978434486,
      "by_issue_phase": {
        "initial_rest": 0.00425683333131768,
        "ramp_up": 0.013605347177242488,
        "hold": 0.005336018995519887,
        "release": 0.013824867899710908,
        "final_rest": 0.004208087071933651
      }
    },
    "history_phase": {
      "pooled": 0.010112566890671582,
      "by_issue_phase": {
        "initial_rest": 0.007595270596475721,
        "ramp_up": 0.00858145395256038,
        "hold": 0.00783287135579297,
        "release": 0.016868238736911678,
        "final_rest": 0.007554888009240898
      }
    },
    "history_phase_paired_grid": {
      "pooled": 0.050092213677228825,
      "by_issue_phase": {
        "initial_rest": 0.007858419153423463,
        "ramp_up": 0.04941784563367779,
        "hold": 0.05075758040759604,
        "release": 0.05665895087203543,
        "final_rest": 0.007531575788359248
      }
    }
  }
};
