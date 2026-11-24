globalThis.WalkingBlendCoefficients = {
  "compact": {
    "schema_version": 1,
    "model": "compact",
    "source_forecaster": {
      "walking_checkpoint_payload_sha256": "057c8541b14b2dc74abff896cf1ff45e804d7c71a3b876564f070525119726ac"
    },
    "learned_fraction": {
      "heel_mm": 0.03,
      "impulse_ns": 0.58,
      "new_load_probability": 1.0
    },
    "formula": "physical + weight * (learned - physical)",
    "foot_order": [
      "left",
      "right"
    ],
    "heel_positive_coordinates": [
      "leftward",
      "backward",
      "upward"
    ],
    "units": [
      "millimetres",
      "newton-seconds",
      "probability"
    ],
    "decision_sha256": "acac85829d7a2359db80a974bdbb73b36668172ed6c088d49cc69706f17c7fc2"
  },
  "research": {
    "schema_version": 1,
    "model": "research",
    "source_forecaster": {
      "complete_walking_joint_manifest_sha256": "aff71dd2ae535411fa1326f9067a2922f2c90eb9739196af479230a75ad3076c",
      "dense_payload_sha256": "0f584f4cc05ddf6f43d8a1b3790e203a99b1c1e61a1e0d2138c1f413b3bc4687",
      "requires": "Matching frozen dense continuation, expert bank and parent; use its completed walking outputs."
    },
    "learned_fraction": {
      "heel_mm": 0.15,
      "impulse_ns": 0.32,
      "new_load_probability": 1.0
    },
    "formula": "physical + weight * (learned - physical)",
    "foot_order": [
      "left",
      "right"
    ],
    "heel_positive_coordinates": [
      "leftward",
      "backward",
      "upward"
    ],
    "units": [
      "millimetres",
      "newton-seconds",
      "probability"
    ],
    "decision_sha256": "acac85829d7a2359db80a974bdbb73b36668172ed6c088d49cc69706f17c7fc2"
  }
};
