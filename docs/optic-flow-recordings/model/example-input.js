/* Invented values. This example contains no recorded case. */
(function (root) {
  "use strict";
  const example = {
  "valid": true,
  "case_id": 50,
  "issue_s": 16.0,
  "camera_stats_rad": [
    [
      0.01,
      0.02
    ],
    [
      -0.01,
      0.024
    ],
    [
      0.02,
      0.033
    ],
    [
      -0.005,
      0.017
    ]
  ],
  "recent_spread_rad": 0.029073183520213264,
  "camera_first_s": [
    15.804,
    15.854,
    15.904,
    15.954
  ],
  "camera_last_s": [
    15.846,
    15.896,
    15.946,
    15.996
  ],
  "camera_closed_s": [
    15.849,
    15.899,
    15.949,
    16.0
  ],
  "command_codes": [
    1,
    1,
    -1,
    -1,
    1,
    -1,
    1,
    -1,
    1,
    1
  ],
  "earlier_command_codes": [
    -1,
    1,
    1,
    -1,
    1,
    1,
    -1,
    1,
    -1,
    -1
  ],
  "command_max_age_s": 0.02,
  "clock_tolerance_s": 1e-13,
  "command_sample_s": [
    10.992,
    11.992,
    12.992,
    13.992,
    14.992,
    15.492,
    15.792,
    15.892,
    15.942,
    15.992
  ],
  "command_closed_s": [
    10.995,
    11.995,
    12.995,
    13.995,
    14.995,
    15.495,
    15.795,
    15.895,
    15.945,
    15.995
  ],
  "earlier_command_sample_s": [
    4.994,
    5.994,
    6.994,
    7.994,
    8.994,
    9.494,
    9.794,
    9.894,
    9.944,
    9.994
  ],
  "earlier_command_closed_s": [
    4.997,
    5.997,
    6.997,
    7.997,
    8.997,
    9.497,
    9.797,
    9.897,
    9.947,
    9.997
  ]
};
  root.ZebrafishForecastExample = example;
  if (typeof module === "object" && module.exports) module.exports = example;
})(globalThis);
