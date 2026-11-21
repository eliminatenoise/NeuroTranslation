"use strict";
globalThis.WristScores = {
  "summary": [
    "The research models fitted 60 earlier right-wrist events on day three. The test used 58 preselected events on day four of the same participant’s recording. Each row below compares a predicted wrist position with the position estimated from the video. Lower error in pixels is better.",
    "Adding voltage to pose reduced right-wrist mean error at both horizons in all three fits. Giving the model voltage from a different event sometimes did just as well or better. Neither wrist passed the test of a consistent benefit from the matching voltage."
  ],
  "tables": [
    {
      "title": "Mean endpoint error in pixels",
      "columns": [
        "Forecast (learned models use seed 17)",
        "Right +8",
        "Right +15",
        "Left +8",
        "Left +15"
      ],
      "rows": [
        [
          "Velocity + learned correction, pose and voltage",
          "29.68 (58)",
          "48.83 (58)",
          "46.43 (58)",
          "53.12 (58)"
        ],
        [
          "Velocity + learned correction, pose only",
          "30.03 (58)",
          "49.99 (58)",
          "46.46 (58)",
          "53.13 (58)"
        ],
        [
          "Direct model, pose and voltage",
          "89.90 (58)",
          "130.16 (58)",
          "98.59 (58)",
          "115.64 (58)"
        ],
        [
          "Still wrist + learned correction, pose and voltage",
          "29.67 (58)",
          "48.93 (58)",
          "46.43 (58)",
          "53.12 (58)"
        ],
        [
          "Fitted velocity prior",
          "31.02 (58)",
          "50.31 (58)",
          "45.59 (58)",
          "51.79 (58)"
        ],
        [
          "Constant velocity",
          "30.92 (58)",
          "50.88 (58)",
          "53.69 (58)",
          "67.68 (58)"
        ],
        [
          "Still wrist",
          "31.02 (58)",
          "50.36 (58)",
          "45.59 (58)",
          "51.79 (58)"
        ],
        [
          "Linear correction to fitted velocity, pose and voltage",
          "30.54 (58)",
          "49.39 (58)",
          "46.55 (58)",
          "53.38 (58)"
        ],
        [
          "Weighted motion of arm segments",
          "32.02 (58)",
          "57.56 (58)",
          "47.28 (58)",
          "61.23 (58)"
        ]
      ],
      "description": "The number in parentheses counts scored events for each wrist and horizon."
    },
    {
      "title": "How much did the matching voltage change the error?",
      "columns": [
        "Fit vs comparison",
        "Right +8",
        "Right +15",
        "Left +8",
        "Left +15"
      ],
      "rows": [
        [
          "17 vs pose alone",
          "-0.359 (57)",
          "-1.19 (57)",
          "-0.0301 (57)",
          "-0.0118 (57)"
        ],
        [
          "17 vs earlier event’s voltage",
          "+0.0316 (57)",
          "-0.68 (57)",
          "+0.0957 (57)",
          "-0.146 (57)"
        ],
        [
          "37 vs pose alone",
          "-0.656 (57)",
          "-8.1e-05 (57)",
          "+0.28 (57)",
          "-0.0043 (57)"
        ],
        [
          "37 vs earlier event’s voltage",
          "-0.128 (57)",
          "+0.659 (57)",
          "-0.0143 (57)",
          "+0.113 (57)"
        ],
        [
          "73 vs pose alone",
          "-1.1 (57)",
          "-0.0301 (57)",
          "+0.283 (57)",
          "+0.239 (57)"
        ],
        [
          "73 vs earlier event’s voltage",
          "-0.079 (57)",
          "+0.314 (57)",
          "-0.151 (57)",
          "-0.113 (57)"
        ]
      ],
      "description": "Each entry is the mean paired difference in pixels (matching voltage minus comparison), followed by the matched event count. Negative means matching voltage helped. For the wrong-time comparison, voltage came from the latest eligible earlier event in a different two-minute block. Both comparisons use the same events."
    }
  ],
  "notes": [
    "The three fits differ by their initial random weights. They share one training day and one test day. The camera measures projected motion in pixels. These results do not establish the same relationship in another participant, a real-time detector of movement onset or a causal effect of cortical activity."
  ]
};
