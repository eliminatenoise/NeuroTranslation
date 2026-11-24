window.handPositionStudy = {
  "study": "NeuroTranslate hand position with recent motion",
  "version": "2026-11-25",
  "dataset": {
    "name": "Neural population dynamics during reaching",
    "dandiset": "000070/0.261122.2046",
    "doi": "10.48324/dandi.000070/0.261122.2046",
    "license": "CC-BY-4.0",
    "subject": "Nitschke",
    "sources": {
      "2010-08-12": {
        "asset": "bceb8ef2-13b0-42b1-9d18-086876f603e1",
        "filename": "sub-Nitschke_ses-20100812_behavior+ecephys.nwb",
        "sha256": "352c789633f756e875e8567e1df4424ae2f3cfe7f6ecf22e2571d0c2a6c3069c",
        "bytes": 6850368077,
        "url": "https://api.dandiarchive.org/api/assets/bceb8ef2-13b0-42b1-9d18-086876f603e1/download/"
      },
      "2010-08-19": {
        "asset": "4fad0016-9d12-48df-8cbc-beb198d78528",
        "filename": "sub-Nitschke_ses-20100819_behavior+ecephys.nwb",
        "sha256": "b2fcd53533c9214d6907e6c999a5b0e18cab051ee5be67aadf573bd9bccf179d",
        "bytes": 5943965810,
        "url": "https://api.dandiarchive.org/api/assets/4fad0016-9d12-48df-8cbc-beb198d78528/download/"
      },
      "2010-09-10": {
        "asset": "fd725c07-6804-4954-a6c4-e03af015a057",
        "filename": "sub-Nitschke_ses-20100910_behavior+ecephys.nwb",
        "sha256": "1a54f6d8405dfca5e08f1f0951b745c32a5b202a987d2acbb9f4c3601ff1dc69",
        "bytes": 5922264602,
        "url": "https://api.dandiarchive.org/api/assets/fd725c07-6804-4954-a6c4-e03af015a057/download/"
      }
    }
  },
  "scope": "Three previously evaluated planar-reaching recordings from one animal.",
  "metrics": [
    "endpoint error in millimetres",
    "distance error in millimetres"
  ],
  "methods": {
    "stay_put": "Predict zero displacement from the measured issue position.",
    "constant_velocity": "Continue the average velocity between issue minus 40 ms and issue for the next 100 ms.",
    "constant_acceleration": "Fit the exact quadratic through three samples spaced 40 ms apart, then evaluate its displacement 100 ms after issue. Use the same formula on all three recordings.",
    "original": "Use the frozen three-seed neural predictions.",
    "published_blend": "Use the frozen published blend of the neural prediction and zero displacement.",
    "equal_blend": "Average the published neural displacement vector and the constant velocity vector, with equal weights fixed before scoring. Derive the distance from the resulting vector."
  },
  "measurement": {
    "path": "processing/behavior/Position/Hand",
    "axes": "Two planar axes relative to screen center",
    "history_offsets_ms": [
      80,
      40,
      0
    ],
    "horizon_ms": 100,
    "timestamp_tolerance_s": 1e-06,
    "feature_boundary": "Each physical forecast uses the exact archived samples at issue minus 80 ms, issue minus 40 ms, and issue. Check them against the native archive timestamps and trial boundaries. No additional trials or target indices. The archive does not establish live sensor latency or how its positional preprocessing affects timestamp causality."
  },
  "scoring": {
    "primary": "Euclidean error of the predicted endpoint in millimetres. Average the windows within each trial, then the trials equally. Average errors across the three seeds for neural paths. The equal blend uses the corresponding neural seed.",
    "secondary": "Error of scalar distance moved, in millimetres. Earlier neural forecasts retain their separate distance outputs. Kinematic and equal-blend distances come from their vector lengths.",
    "strata": "Show the four previous bands of measured future displacement for explanation only. Also show archived issue windows with under 1 mm of motion in the preceding 40 ms and those with at least 1 mm. These are fixed descriptive groups, never model fitting data.",
    "future_distance_bands_mm": [
      0,
      2,
      10,
      20
    ],
    "past_movement_threshold_mm": 1,
    "bootstrap_draws": 4000,
    "bootstrap_seed": 20261125,
    "paired_effect": "On each recording, subtract the candidate's trial error from its fixed reference's trial error and resample whole matched trials. Report the 2.5th and 97.5th percentiles. This only describes the sampled trials within each day.",
    "parity": "Reproduce the three existing overall trial-equal neural and stay-put scores before interpreting the new comparisons."
  },
  "frozen_seeds": [
    20261124,
    20261125,
    20261126
  ],
  "forecast_packet": {
    "filename": "issued-forecasts.npz",
    "sha256": "ab3624c7b190e6b5a79134383ca715accbc22175eb7c5d727a2570afd5d89bb0",
    "bytes": 15772497
  },
  "recordings": {
    "2010-08-12": {
      "overall": {
        "rows": 46102,
        "trials": 3038,
        "error_mm": {
          "original": [
            8.470406179414844,
            7.721603524524611
          ],
          "published_blend": [
            4.999422027477703,
            3.600286431804599
          ],
          "stay_put": [
            6.651411974245964,
            6.651411974245964
          ],
          "constant_velocity": [
            5.20443734487187,
            3.692038655732786
          ],
          "constant_acceleration": [
            6.3389171616419295,
            4.73245174472376
          ],
          "equal_blend": [
            4.130667791436383,
            2.9923657176638785
          ]
        },
        "paired_gain_mm": {
          "published_blend_over_stay_put": {
            "mean": [
              1.6519899467682677,
              3.0511255424413743
            ],
            "paired_95": [
              [
                1.587913910158945,
                1.7175460517511612
              ],
              [
                2.982781027656428,
                3.1191785455537016
              ]
            ]
          },
          "published_blend_over_constant_velocity": {
            "mean": [
              0.20501531739417347,
              0.09175222392819328
            ],
            "paired_95": [
              [
                0.1225159705418353,
                0.28531111543673654
              ],
              [
                0.018111440435970395,
                0.16521994486917235
              ]
            ]
          },
          "published_blend_over_constant_acceleration": {
            "mean": [
              1.3394951341642256,
              1.1321653129191551
            ],
            "paired_95": [
              [
                1.2432313926111391,
                1.4353743370102554
              ],
              [
                1.0450447307382242,
                1.2208332962802058
              ]
            ]
          },
          "equal_blend_over_constant_velocity": {
            "mean": [
              1.0737695534354994,
              0.6996729380689184
            ],
            "paired_95": [
              [
                1.0266326908785006,
                1.1202564000719029
              ],
              [
                0.6597764357984197,
                0.739521755359349
              ]
            ]
          },
          "equal_blend_over_published_blend": {
            "mean": [
              0.8687542360413233,
              0.6079207141407257
            ],
            "paired_95": [
              [
                0.8242091924486404,
                0.9150570084897228
              ],
              [
                0.5615164494932565,
                0.6556433430225507
              ]
            ]
          }
        }
      },
      "strata": {
        "past_under_1_mm": {
          "rows": 35079,
          "trials": 3038,
          "error_mm": {
            "original": [
              5.102239051425406,
              5.612536844337696
            ],
            "published_blend": [
              1.7692864788452136,
              1.5335273668822909
            ],
            "stay_put": [
              0.9132934815147437,
              0.9132934815147437
            ],
            "constant_velocity": [
              0.8949738949828271,
              0.7255465236379985
            ],
            "constant_acceleration": [
              1.4960078261934548,
              1.1502919938270773
            ],
            "equal_blend": [
              1.2038042048757953,
              0.9582252780197779
            ]
          },
          "paired_gain_mm": {
            "published_blend_over_stay_put": {
              "mean": [
                -0.855992997330468,
                -0.6202338853675458
              ],
              "paired_95": [
                [
                  -0.8973747172016716,
                  -0.8142243836057841
                ],
                [
                  -0.6639172813287988,
                  -0.5762043075196471
                ]
              ]
            },
            "published_blend_over_constant_velocity": {
              "mean": [
                -0.87431258386239,
                -0.807980843244294
              ],
              "paired_95": [
                [
                  -0.9163698823805327,
                  -0.8316532325793651
                ],
                [
                  -0.852286096239436,
                  -0.7633540161961112
                ]
              ]
            },
            "published_blend_over_constant_acceleration": {
              "mean": [
                -0.2732786526517604,
                -0.38323537305521244
              ],
              "paired_95": [
                [
                  -0.313910884246551,
                  -0.2294624500466582
                ],
                [
                  -0.4253296641918988,
                  -0.33907673537162597
                ]
              ]
            },
            "equal_blend_over_constant_velocity": {
              "mean": [
                -0.30883030989296617,
                -0.23267875438178015
              ],
              "paired_95": [
                [
                  -0.32989373881219225,
                  -0.28721153832143725
                ],
                [
                  -0.2521028908614945,
                  -0.21214863539685794
                ]
              ]
            },
            "equal_blend_over_published_blend": {
              "mean": [
                0.5654822739694222,
                0.5753020888625134
              ],
              "paired_95": [
                [
                  0.5434957134696423,
                  0.5875681629239402
                ],
                [
                  0.5491473897884752,
                  0.6016391232900795
                ]
              ]
            }
          }
        },
        "past_at_least_1_mm": {
          "rows": 11023,
          "trials": 3038,
          "error_mm": {
            "original": [
              18.885335003926528,
              14.020138081198716
            ],
            "published_blend": [
              15.402418439280554,
              10.284976067526332
            ],
            "stay_put": [
              25.95364445565146,
              25.95364445565146
            ],
            "constant_velocity": [
              19.85970711007048,
              14.159745336045946
            ],
            "constant_acceleration": [
              23.253076568508966,
              17.357053420097213
            ],
            "equal_blend": [
              13.78391227759184,
              9.875387265278219
            ]
          },
          "paired_gain_mm": {
            "published_blend_over_stay_put": {
              "mean": [
                10.551226016370903,
                15.668668388125134
              ],
              "paired_95": [
                [
                  10.270346455048383,
                  10.832327752405424
                ],
                [
                  15.372645395388092,
                  15.968517951733975
                ]
              ]
            },
            "published_blend_over_constant_velocity": {
              "mean": [
                4.457288670789854,
                3.874769268519578
              ],
              "paired_95": [
                [
                  4.091986243443702,
                  4.813695162870024
                ],
                [
                  3.541491272333804,
                  4.217304973766413
                ]
              ]
            },
            "published_blend_over_constant_acceleration": {
              "mean": [
                7.850658129228389,
                7.072077352570889
              ],
              "paired_95": [
                [
                  7.397955385380722,
                  8.310480786662806
                ],
                [
                  6.636270908829718,
                  7.502906231017978
                ]
              ]
            },
            "equal_blend_over_constant_velocity": {
              "mean": [
                6.075794832478596,
                4.284358070767722
              ],
              "paired_95": [
                [
                  5.859856697682162,
                  6.2873931419567315
                ],
                [
                  4.0935986874026025,
                  4.476454745262902
                ]
              ]
            },
            "equal_blend_over_published_blend": {
              "mean": [
                1.618506161688722,
                0.40958880224812694
              ],
              "paired_95": [
                [
                  1.4152150466924263,
                  1.8274690217425409
                ],
                [
                  0.19248802388141778,
                  0.6284756272787198
                ]
              ]
            }
          }
        },
        "future_0_to_2_mm": {
          "rows": 32913,
          "trials": 3038,
          "error_mm": {
            "original": [
              4.501539277360104,
              5.312360862600693
            ],
            "published_blend": [
              1.2078073545229318,
              1.1741393768401476
            ],
            "stay_put": [
              0.31702989885097144,
              0.31702989885097144
            ],
            "constant_velocity": [
              0.48637080460803567,
              0.3350380250559295
            ],
            "constant_acceleration": [
              1.1746783832911423,
              0.922383048542671
            ],
            "equal_blend": [
              0.7460307969093387,
              0.6006148716637717
            ]
          },
          "paired_gain_mm": {
            "published_blend_over_stay_put": {
              "mean": [
                -0.890777455671959,
                -0.8571094779891762
              ],
              "paired_95": [
                [
                  -0.9292290021700081,
                  -0.8512527177857396
                ],
                [
                  -0.8968166907456383,
                  -0.8169357346955362
                ]
              ]
            },
            "published_blend_over_constant_velocity": {
              "mean": [
                -0.7214365499148957,
                -0.8391013517842159
              ],
              "paired_95": [
                [
                  -0.7590388629527477,
                  -0.682767145861561
                ],
                [
                  -0.8780051974925213,
                  -0.7980655885963671
                ]
              ]
            },
            "published_blend_over_constant_acceleration": {
              "mean": [
                -0.033128971231790746,
                -0.2517563282974748
              ],
              "paired_95": [
                [
                  -0.0744690282703356,
                  0.0082823700146423
                ],
                [
                  -0.2945779235136602,
                  -0.20906725293266218
                ]
              ]
            },
            "equal_blend_over_constant_velocity": {
              "mean": [
                -0.25965999230130277,
                -0.2655768466078417
              ],
              "paired_95": [
                [
                  -0.2780308559395538,
                  -0.24080736762627264
                ],
                [
                  -0.28312560851247304,
                  -0.2472358295448619
                ]
              ]
            },
            "equal_blend_over_published_blend": {
              "mean": [
                0.4617765576135931,
                0.5735245051763758
              ],
              "paired_95": [
                [
                  0.44118399380060647,
                  0.4816762249134992
                ],
                [
                  0.5502719791183288,
                  0.5958571297623465
                ]
              ]
            }
          }
        },
        "future_2_to_10_mm": {
          "rows": 7167,
          "trials": 2809,
          "error_mm": {
            "original": [
              15.527385930618255,
              15.394366878217681
            ],
            "published_blend": [
              8.272236741151438,
              6.823091465150612
            ],
            "stay_put": [
              3.683978093698298,
              3.683978093698298
            ],
            "constant_velocity": [
              4.506150638335604,
              3.613006958016455
            ],
            "constant_acceleration": [
              6.281687017975935,
              4.457275065273417
            ],
            "equal_blend": [
              5.453624462268164,
              4.055403846535438
            ]
          },
          "paired_gain_mm": {
            "published_blend_over_stay_put": {
              "mean": [
                -4.58825864745315,
                -3.1391133714523187
              ],
              "paired_95": [
                [
                  -4.793204925866829,
                  -4.395658217733719
                ],
                [
                  -3.354730106218819,
                  -2.945005103958391
                ]
              ]
            },
            "published_blend_over_constant_velocity": {
              "mean": [
                -3.7660861028158314,
                -3.210084507134157
              ],
              "paired_95": [
                [
                  -4.043022265582497,
                  -3.498817270280663
                ],
                [
                  -3.4846509644826673,
                  -2.936992196193832
                ]
              ]
            },
            "published_blend_over_constant_acceleration": {
              "mean": [
                -1.990549723175509,
                -2.3658163998771955
              ],
              "paired_95": [
                [
                  -2.2816089527829835,
                  -1.6975633914522474
                ],
                [
                  -2.6460297782795363,
                  -2.0813063822765896
                ]
              ]
            },
            "equal_blend_over_constant_velocity": {
              "mean": [
                -0.9474738239325377,
                -0.4423968885189808
              ],
              "paired_95": [
                [
                  -1.0976109963681577,
                  -0.8033139316109741
                ],
                [
                  -0.5808053669151461,
                  -0.30462731429782225
                ]
              ]
            },
            "equal_blend_over_published_blend": {
              "mean": [
                2.8186122788832977,
                2.7676876186151755
              ],
              "paired_95": [
                [
                  2.6843292941601384,
                  2.9603199421435655
                ],
                [
                  2.618978852175121,
                  2.9205422145185103
                ]
              ]
            }
          }
        },
        "future_10_to_20_mm": {
          "rows": 1049,
          "trials": 966,
          "error_mm": {
            "original": [
              17.95486760751817,
              13.963847260588553
            ],
            "published_blend": [
              12.89301233477752,
              8.582737803535496
            ],
            "stay_put": [
              14.476455921435678,
              14.476455921435678
            ],
            "constant_velocity": [
              20.746225930012844,
              19.043923507039
            ],
            "constant_acceleration": [
              15.766691221222898,
              10.605748864249039
            ],
            "equal_blend": [
              12.713990750690856,
              10.467724382474337
            ]
          },
          "paired_gain_mm": {
            "published_blend_over_stay_put": {
              "mean": [
                1.5834435866581245,
                5.893718117900175
              ],
              "paired_95": [
                [
                  1.1846463921021608,
                  1.9674457494050959
                ],
                [
                  5.508171339191966,
                  6.2672354923504
                ]
              ]
            },
            "published_blend_over_constant_velocity": {
              "mean": [
                7.853213595235314,
                10.461185703503535
              ],
              "paired_95": [
                [
                  7.098528381859301,
                  8.589368975785481
                ],
                [
                  9.689323660404927,
                  11.20978590670176
                ]
              ]
            },
            "published_blend_over_constant_acceleration": {
              "mean": [
                2.8736788864453664,
                2.0230110607135434
              ],
              "paired_95": [
                [
                  2.2122296770830445,
                  3.5393322429665233
                ],
                [
                  1.3832169164014636,
                  2.6761093336731974
                ]
              ]
            },
            "equal_blend_over_constant_velocity": {
              "mean": [
                8.032235179321967,
                8.576199124564694
              ],
              "paired_95": [
                [
                  7.5568447253349245,
                  8.512084467939548
                ],
                [
                  8.090667759579354,
                  9.048762856190933
                ]
              ]
            },
            "equal_blend_over_published_blend": {
              "mean": [
                0.17902158408666827,
                -1.8849865789388434
              ],
              "paired_95": [
                [
                  -0.26157463655238977,
                  0.616010943643418
                ],
                [
                  -2.333160994698821,
                  -1.4211127717520406
                ]
              ]
            }
          }
        },
        "future_20_to_inf_mm": {
          "rows": 4973,
          "trials": 3037,
          "error_mm": {
            "original": [
              21.3777727823962,
              10.241705945623954
            ],
            "published_blend": [
              23.417192471760952,
              13.930248092913198
            ],
            "stay_put": [
              52.466759213167364,
              52.466759213167364
            ],
            "constant_velocity": [
              32.829939717906825,
              22.09684293534928
            ],
            "constant_acceleration": [
              39.178664556065435,
              29.910553150504096
            ],
            "equal_blend": [
              22.282757860547445,
              15.47315010758656
            ]
          },
          "paired_gain_mm": {
            "published_blend_over_stay_put": {
              "mean": [
                29.04956674140651,
                38.53651112025443
              ],
              "paired_95": [
                [
                  28.616895221553065,
                  29.467452018828432
                ],
                [
                  38.15486067601182,
                  38.920591403374466
                ]
              ]
            },
            "published_blend_over_constant_velocity": {
              "mean": [
                9.412747246145878,
                8.166594842436163
              ],
              "paired_95": [
                [
                  8.872242927458998,
                  9.936878756231563
                ],
                [
                  7.674892048620417,
                  8.642465068953413
                ]
              ]
            },
            "published_blend_over_constant_acceleration": {
              "mean": [
                15.761472084304417,
                15.980305057590929
              ],
              "paired_95": [
                [
                  15.014253634805803,
                  16.515889083877422
                ],
                [
                  15.240861275056726,
                  16.713351452998555
                ]
              ]
            },
            "equal_blend_over_constant_velocity": {
              "mean": [
                10.547181857359382,
                6.623692827762738
              ],
              "paired_95": [
                [
                  10.230310757485865,
                  10.854848601549747
                ],
                [
                  6.301870675832289,
                  6.941023187784301
                ]
              ]
            },
            "equal_blend_over_published_blend": {
              "mean": [
                1.134434611213504,
                -1.5429020146734198
              ],
              "paired_95": [
                [
                  0.8171029769784862,
                  1.4854469123494927
                ],
                [
                  -1.8879017802594174,
                  -1.1800191612648683
                ]
              ]
            }
          }
        }
      },
      "prior_parity_mm": 1e-10
    },
    "2010-08-19": {
      "overall": {
        "rows": 39297,
        "trials": 3126,
        "error_mm": {
          "original": [
            14.610959447336265,
            13.244753310767685
          ],
          "published_blend": [
            8.18928340261989,
            6.196235117578942
          ],
          "stay_put": [
            7.894748170793269,
            7.894748170793269
          ],
          "constant_velocity": [
            6.048216817115767,
            4.284193338991989
          ],
          "constant_acceleration": [
            7.417486882142548,
            5.62429588762225
          ],
          "equal_blend": [
            5.747845732923012,
            4.3669404363623086
          ]
        },
        "paired_gain_mm": {
          "published_blend_over_stay_put": {
            "mean": [
              -0.29453523182660385,
              1.6985130532143327
            ],
            "paired_95": [
              [
                -0.3933335051933905,
                -0.19662180274629543
              ],
              [
                1.592386955258737,
                1.8068301298709641
              ]
            ]
          },
          "published_blend_over_constant_velocity": {
            "mean": [
              -2.141066585504112,
              -1.9120417785869437
            ],
            "paired_95": [
              [
                -2.2553293830918717,
                -2.0286876741391033
              ],
              [
                -2.0155961030185803,
                -1.8067321820737365
              ]
            ]
          },
          "published_blend_over_constant_acceleration": {
            "mean": [
              -0.7717965204773464,
              -0.5719392299566939
            ],
            "paired_95": [
              [
                -0.8866278545990564,
                -0.6556709052587807
              ],
              [
                -0.6920450641929837,
                -0.4588012242458886
              ]
            ]
          },
          "equal_blend_over_constant_velocity": {
            "mean": [
              0.3003710841927684,
              -0.0827470973703143
            ],
            "paired_95": [
              [
                0.2385550542255938,
                0.3627190895126089
              ],
              [
                -0.136973066403445,
                -0.02770529549792845
              ]
            ]
          },
          "equal_blend_over_published_blend": {
            "mean": [
              2.4414376696968794,
              1.829294681216635
            ],
            "paired_95": [
              [
                2.3774245834705905,
                2.506741736801695
              ],
              [
                1.7640358788388566,
                1.8960802792334819
              ]
            ]
          }
        }
      },
      "strata": {
        "past_under_1_mm": {
          "rows": 27546,
          "trials": 3126,
          "error_mm": {
            "original": [
              12.273664587355508,
              12.609011084414766
            ],
            "published_blend": [
              4.97613061923942,
              4.580265861723951
            ],
            "stay_put": [
              1.140435659908202,
              1.140435659908202
            ],
            "constant_velocity": [
              1.0754113599208006,
              0.8847809795542355
            ],
            "constant_acceleration": [
              1.734302700752541,
              1.3275960368094208
            ],
            "equal_blend": [
              2.826416690853602,
              2.392033142153347
            ]
          },
          "paired_gain_mm": {
            "published_blend_over_stay_put": {
              "mean": [
                -3.835694959331241,
                -3.4398302018157643
              ],
              "paired_95": [
                [
                  -3.937397837451402,
                  -3.737607719507495
                ],
                [
                  -3.548344019405831,
                  -3.3358676727927348
                ]
              ]
            },
            "published_blend_over_constant_velocity": {
              "mean": [
                -3.9007192593186346,
                -3.695484882169722
              ],
              "paired_95": [
                [
                  -4.004043537826281,
                  -3.8024485067198968
                ],
                [
                  -3.802358943264791,
                  -3.5919597756219996
                ]
              ]
            },
            "published_blend_over_constant_acceleration": {
              "mean": [
                -3.241827918486895,
                -3.2526698249145407
              ],
              "paired_95": [
                [
                  -3.342994625662052,
                  -3.1429477235013423
                ],
                [
                  -3.3569442999215497,
                  -3.148157698954045
                ]
              ]
            },
            "equal_blend_over_constant_velocity": {
              "mean": [
                -1.751005330932801,
                -1.5072521625991144
              ],
              "paired_95": [
                [
                  -1.8012365640381136,
                  -1.7011449745921965
                ],
                [
                  -1.5583023462313714,
                  -1.4566480767987942
                ]
              ]
            },
            "equal_blend_over_published_blend": {
              "mean": [
                2.149713928385839,
                2.1882327195706104
              ],
              "paired_95": [
                [
                  2.0993003626248936,
                  2.202311333931175
                ],
                [
                  2.133452856736769,
                  2.246041887235039
                ]
              ]
            }
          }
        },
        "past_at_least_1_mm": {
          "rows": 11751,
          "trials": 3126,
          "error_mm": {
            "original": [
              19.866337585776137,
              14.64610914740424
            ],
            "published_blend": [
              15.631515510446222,
              10.091193726141872
            ],
            "stay_put": [
              24.43381574411835,
              24.43381574411835
            ],
            "constant_velocity": [
              18.44880621668031,
              13.004833228602898
            ],
            "constant_acceleration": [
              22.112371584089708,
              16.85592586109394
            ],
            "equal_blend": [
              12.827570310477396,
              9.285425886679127
            ]
          },
          "paired_gain_mm": {
            "published_blend_over_stay_put": {
              "mean": [
                8.802300233672076,
                14.34262201797644
              ],
              "paired_95": [
                [
                  8.537352560116085,
                  9.075847031832025
                ],
                [
                  14.065167415460696,
                  14.628556913355322
                ]
              ]
            },
            "published_blend_over_constant_velocity": {
              "mean": [
                2.8172907062340635,
                2.9136395024610753
              ],
              "paired_95": [
                [
                  2.4762315846080263,
                  3.1733146478573486
                ],
                [
                  2.600611719520254,
                  3.244923836713293
                ]
              ]
            },
            "published_blend_over_constant_acceleration": {
              "mean": [
                6.480856073643425,
                6.76473213495205
              ],
              "paired_95": [
                [
                  6.059330723358608,
                  6.905829390560676
                ],
                [
                  6.380088601733167,
                  7.15369608662748
                ]
              ]
            },
            "equal_blend_over_constant_velocity": {
              "mean": [
                5.621235906202916,
                3.7194073419238234
              ],
              "paired_95": [
                [
                  5.428742080682112,
                  5.829959110360439
                ],
                [
                  3.5490451002818766,
                  3.8936109189192476
                ]
              ]
            },
            "equal_blend_over_published_blend": {
              "mean": [
                2.803945199968852,
                0.8057678394627448
              ],
              "paired_95": [
                [
                  2.5938640429576787,
                  3.01139413144644
                ],
                [
                  0.5894039137569442,
                  1.0075136269085043
                ]
              ]
            }
          }
        },
        "future_0_to_2_mm": {
          "rows": 25314,
          "trials": 3126,
          "error_mm": {
            "original": [
              11.757224875036636,
              12.619277333148647
            ],
            "published_blend": [
              4.35508983389588,
              4.433357513696448
            ],
            "stay_put": [
              0.39733600903031374,
              0.39733600903031374
            ],
            "constant_velocity": [
              0.5983619991356777,
              0.42723883484697317
            ],
            "constant_acceleration": [
              1.359227920980975,
              1.0525164708461692
            ],
            "equal_blend": [
              2.3168146887257546,
              2.1567274539427377
            ]
          },
          "paired_gain_mm": {
            "published_blend_over_stay_put": {
              "mean": [
                -3.9577538248655633,
                -4.036021504666156
              ],
              "paired_95": [
                [
                  -4.064837297831913,
                  -3.855899888936047
                ],
                [
                  -4.148322122498642,
                  -3.930118236841184
                ]
              ]
            },
            "published_blend_over_constant_velocity": {
              "mean": [
                -3.7567278347602135,
                -4.006118678849497
              ],
              "paired_95": [
                [
                  -3.8639403939273875,
                  -3.6534835744309904
                ],
                [
                  -4.117627522066418,
                  -3.898768017385224
                ]
              ]
            },
            "published_blend_over_constant_acceleration": {
              "mean": [
                -2.9958619129149024,
                -3.3808410428502986
              ],
              "paired_95": [
                [
                  -3.1047945819993887,
                  -2.890413590520388
                ],
                [
                  -3.4949086767348247,
                  -3.27138192482965
                ]
              ]
            },
            "equal_blend_over_constant_velocity": {
              "mean": [
                -1.718452689590074,
                -1.7294886190957646
              ],
              "paired_95": [
                [
                  -1.7706922023454799,
                  -1.6678071686266007
                ],
                [
                  -1.7824890812037821,
                  -1.6789565882056419
                ]
              ]
            },
            "equal_blend_over_published_blend": {
              "mean": [
                2.038275145170124,
                2.2766300597537232
              ],
              "paired_95": [
                [
                  1.9859059407034734,
                  2.093136246215103
                ],
                [
                  2.220706196419544,
                  2.3353062191558274
                ]
              ]
            }
          }
        },
        "future_2_to_10_mm": {
          "rows": 7931,
          "trials": 2991,
          "error_mm": {
            "original": [
              16.464629592153653,
              16.83222715189802
            ],
            "published_blend": [
              8.457752372759044,
              6.955108693484043
            ],
            "stay_put": [
              3.7182632326430736,
              3.7182632326430736
            ],
            "constant_velocity": [
              4.573665538076407,
              3.5153256770461376
            ],
            "constant_acceleration": [
              6.726262657012489,
              4.97100788838567
            ],
            "equal_blend": [
              5.40217032393049,
              3.8308035712373183
            ]
          },
          "paired_gain_mm": {
            "published_blend_over_stay_put": {
              "mean": [
                -4.739489140115952,
                -3.2368454608410007
              ],
              "paired_95": [
                [
                  -4.932210244717015,
                  -4.555451073007391
                ],
                [
                  -3.434535090472274,
                  -3.048371393329219
                ]
              ]
            },
            "published_blend_over_constant_velocity": {
              "mean": [
                -3.884086834682626,
                -3.4397830164379277
              ],
              "paired_95": [
                [
                  -4.107612102235356,
                  -3.6413720078110936
                ],
                [
                  -3.6793445721016353,
                  -3.185588524043629
                ]
              ]
            },
            "published_blend_over_constant_acceleration": {
              "mean": [
                -1.731489715746528,
                -1.9841008050983981
              ],
              "paired_95": [
                [
                  -1.9849762785454501,
                  -1.4768366876260468
                ],
                [
                  -2.2411616563743824,
                  -1.7239850161770187
                ]
              ]
            },
            "equal_blend_over_constant_velocity": {
              "mean": [
                -0.828504785854087,
                -0.31547789419118427
              ],
              "paired_95": [
                [
                  -0.9488080727381715,
                  -0.7046031982337044
                ],
                [
                  -0.4339816583663896,
                  -0.19703389537911586
                ]
              ]
            },
            "equal_blend_over_published_blend": {
              "mean": [
                3.055582048828522,
                3.124305122246744
              ],
              "paired_95": [
                [
                  2.922714167997161,
                  3.1824026690786367
                ],
                [
                  2.9759321938033225,
                  3.2645187906027924
                ]
              ]
            }
          }
        },
        "future_10_to_20_mm": {
          "rows": 1139,
          "trials": 1055,
          "error_mm": {
            "original": [
              22.25389275376491,
              15.679469463539208
            ],
            "published_blend": [
              16.106950888446775,
              9.191405118004
            ],
            "stay_put": [
              14.338231190757066,
              14.338231190757066
            ],
            "constant_velocity": [
              20.260056419478584,
              18.111173926178544
            ],
            "constant_acceleration": [
              16.318767775454774,
              10.955313170846752
            ],
            "equal_blend": [
              12.752364277945933,
              9.026600253033727
            ]
          },
          "paired_gain_mm": {
            "published_blend_over_stay_put": {
              "mean": [
                -1.7687196976896915,
                5.146826072753076
              ],
              "paired_95": [
                [
                  -2.2922220168026604,
                  -1.2517359051393528
                ],
                [
                  4.661095157534958,
                  5.619091442148239
                ]
              ]
            },
            "published_blend_over_constant_velocity": {
              "mean": [
                4.153105531031799,
                8.919768808174561
              ],
              "paired_95": [
                [
                  3.3540741301047454,
                  4.979341436984326
                ],
                [
                  8.074406726303103,
                  9.767048950781744
                ]
              ]
            },
            "published_blend_over_constant_acceleration": {
              "mean": [
                0.21181688700800497,
                1.763908052842743
              ],
              "paired_95": [
                [
                  -0.4488615390630346,
                  0.901020183122136
                ],
                [
                  1.1040643744135255,
                  2.413352076396851
                ]
              ]
            },
            "equal_blend_over_constant_velocity": {
              "mean": [
                7.507692141532639,
                9.084573673144831
              ],
              "paired_95": [
                [
                  7.007291520737635,
                  8.01772779977288
                ],
                [
                  8.660471041907098,
                  9.519598015163718
                ]
              ]
            },
            "equal_blend_over_published_blend": {
              "mean": [
                3.3545866105008355,
                0.164804864970274
              ],
              "paired_95": [
                [
                  2.806770982207933,
                  3.8754824486020025
                ],
                [
                  -0.39927312905670176,
                  0.7183997591946482
                ]
              ]
            }
          }
        },
        "future_20_to_inf_mm": {
          "rows": 4913,
          "trials": 3123,
          "error_mm": {
            "original": [
              24.011310743844803,
              9.878961531906434
            ],
            "published_blend": [
              25.51363473541073,
              13.742673187413615
            ],
            "stay_put": [
              52.980638070993265,
              52.980638070993265
            ],
            "constant_velocity": [
              32.046055992129226,
              21.486497299936875
            ],
            "constant_acceleration": [
              38.490478823622084,
              30.08166953299337
            ],
            "equal_blend": [
              22.07027188823528,
              15.630695497672125
            ]
          },
          "paired_gain_mm": {
            "published_blend_over_stay_put": {
              "mean": [
                27.467003335582636,
                39.23796488357981
              ],
              "paired_95": [
                [
                  26.973720919455594,
                  27.986183166133472
                ],
                [
                  38.84556120236182,
                  39.65831917071464
                ]
              ]
            },
            "published_blend_over_constant_velocity": {
              "mean": [
                6.53242125671854,
                7.743824112523242
              ],
              "paired_95": [
                [
                  5.913994012061734,
                  7.151270058288118
                ],
                [
                  7.2116178061490395,
                  8.28143027228046
                ]
              ]
            },
            "published_blend_over_constant_acceleration": {
              "mean": [
                12.976844088211386,
                16.33899634557971
              ],
              "paired_95": [
                [
                  12.234503814434518,
                  13.723136227027991
                ],
                [
                  15.688195345461683,
                  16.992265776222606
                ]
              ]
            },
            "equal_blend_over_constant_velocity": {
              "mean": [
                9.975784103893913,
                5.855801802264701
              ],
              "paired_95": [
                [
                  9.631733180921184,
                  10.320250946304927
                ],
                [
                  5.515832460370247,
                  6.200656344507758
                ]
              ]
            },
            "equal_blend_over_published_blend": {
              "mean": [
                3.44336284717541,
                -1.8880223102585132
              ],
              "paired_95": [
                [
                  3.0754172953945393,
                  3.8115530726988105
                ],
                [
                  -2.265191740585855,
                  -1.5186322673456831
                ]
              ]
            }
          }
        }
      },
      "prior_parity_mm": 1e-10
    },
    "2010-09-10": {
      "overall": {
        "rows": 45324,
        "trials": 2911,
        "error_mm": {
          "original": [
            4.631717399142173,
            3.537618036754859
          ],
          "published_blend": [
            3.2247835373780176,
            2.112745169128129
          ],
          "stay_put": [
            6.110735969752565,
            6.110735969752565
          ],
          "constant_velocity": [
            4.894758893872299,
            3.5179737732247256
          ],
          "constant_acceleration": [
            5.987560483898191,
            4.512118402755455
          ],
          "equal_blend": [
            3.1560476655719185,
            2.2417312099000273
          ]
        },
        "paired_gain_mm": {
          "published_blend_over_stay_put": {
            "mean": [
              2.885952432374555,
              3.9979908006244513
            ],
            "paired_95": [
              [
                2.837173936829024,
                2.9374214605890456
              ],
              [
                3.950878714848941,
                4.04505911825877
              ]
            ]
          },
          "published_blend_over_constant_velocity": {
            "mean": [
              1.6699753564942974,
              1.4052286040965885
            ],
            "paired_95": [
              [
                1.605688843380956,
                1.7367909444025933
              ],
              [
                1.3505826681754272,
                1.4582596482281354
              ]
            ]
          },
          "published_blend_over_constant_acceleration": {
            "mean": [
              2.762776946520172,
              2.3993732336273417
            ],
            "paired_95": [
              [
                2.682290450566149,
                2.843204127201849
              ],
              [
                2.3248135633226568,
                2.472830783473827
              ]
            ]
          },
          "equal_blend_over_constant_velocity": {
            "mean": [
              1.7387112283003878,
              1.2762425633246948
            ],
            "paired_95": [
              [
                1.700932961626104,
                1.7769187383994303
              ],
              [
                1.244096554798169,
                1.309004220258425
              ]
            ]
          },
          "equal_blend_over_published_blend": {
            "mean": [
              0.06873587180609436,
              -0.12898604077189627
            ],
            "paired_95": [
              [
                0.028542943304230364,
                0.10692497795920668
              ],
              [
                -0.16410584555006807,
                -0.09351162434864436
              ]
            ]
          }
        }
      },
      "strata": {
        "past_under_1_mm": {
          "rows": 35897,
          "trials": 2911,
          "error_mm": {
            "original": [
              2.4437680375988724,
              2.5002408257254274
            ],
            "published_blend": [
              0.8590901718313797,
              0.7096025037665492
            ],
            "stay_put": [
              0.9154962822912591,
              0.9154962822912591
            ],
            "constant_velocity": [
              0.919660569651259,
              0.7404633039907568
            ],
            "constant_acceleration": [
              1.497232659368488,
              1.1938594590126066
            ],
            "equal_blend": [
              0.8152388785047842,
              0.672480502281892
            ]
          },
          "paired_gain_mm": {
            "published_blend_over_stay_put": {
              "mean": [
                0.05640611045988116,
                0.20589377852471213
              ],
              "paired_95": [
                [
                  0.03713930943566571,
                  0.0752790352859403
                ],
                [
                  0.18248203991446735,
                  0.22899724795619522
                ]
              ]
            },
            "published_blend_over_constant_velocity": {
              "mean": [
                0.060570397819881557,
                0.030860800224207483
              ],
              "paired_95": [
                [
                  0.0416064594868773,
                  0.07917176527243558
                ],
                [
                  0.00787271646268974,
                  0.05287387898772155
                ]
              ]
            },
            "published_blend_over_constant_acceleration": {
              "mean": [
                0.6381424875371131,
                0.4842569552460596
              ],
              "paired_95": [
                [
                  0.6182854920550162,
                  0.6588892616492419
                ],
                [
                  0.4623440316973911,
                  0.5072828976818382
                ]
              ]
            },
            "equal_blend_over_constant_velocity": {
              "mean": [
                0.10442169114647545,
                0.06798280170886299
              ],
              "paired_95": [
                [
                  0.09392361402250689,
                  0.1150178430314043
                ],
                [
                  0.056694245696462614,
                  0.07939262742165883
                ]
              ]
            },
            "equal_blend_over_published_blend": {
              "mean": [
                0.04385129332659413,
                0.03712200148465551
              ],
              "paired_95": [
                [
                  0.03492699308251302,
                  0.05324414868573192
                ],
                [
                  0.02504366148051937,
                  0.04978821744819047
                ]
              ]
            }
          }
        },
        "past_at_least_1_mm": {
          "rows": 9427,
          "trials": 2911,
          "error_mm": {
            "original": [
              13.097802054724822,
              7.525159645885539
            ],
            "published_blend": [
              12.38237142873441,
              7.506861668956415
            ],
            "stay_put": [
              26.6318064376363,
              26.6318064376363
            ],
            "constant_velocity": [
              20.70934035435601,
              14.840941439798046
            ],
            "constant_acceleration": [
              24.371070372494636,
              18.217823272247777
            ],
            "equal_blend": [
              12.366970603893249,
              8.505285588050153
            ]
          },
          "paired_gain_mm": {
            "published_blend_over_stay_put": {
              "mean": [
                14.24943500890188,
                19.12494476867987
              ],
              "paired_95": [
                [
                  13.986428211172596,
                  14.515375873220098
                ],
                [
                  18.873046832539348,
                  19.386725881332566
                ]
              ]
            },
            "published_blend_over_constant_velocity": {
              "mean": [
                8.326968925621557,
                7.334079770841582
              ],
              "paired_95": [
                [
                  7.972053806198838,
                  8.6702514006458
                ],
                [
                  7.02881362997841,
                  7.640319971986706
                ]
              ]
            },
            "published_blend_over_constant_acceleration": {
              "mean": [
                11.988698943760161,
                10.710961603291327
              ],
              "paired_95": [
                [
                  11.534520800757466,
                  12.450983366707622
                ],
                [
                  10.291614161946745,
                  11.123684365167614
                ]
              ]
            },
            "equal_blend_over_constant_velocity": {
              "mean": [
                8.342369750462778,
                6.33565585174789
              ],
              "paired_95": [
                [
                  8.144311886518723,
                  8.540345364925543
                ],
                [
                  6.152516294031414,
                  6.518186683354019
                ]
              ]
            },
            "equal_blend_over_published_blend": {
              "mean": [
                0.01540082484120848,
                -0.9984239190937159
              ],
              "paired_95": [
                [
                  -0.1960741005376956,
                  0.21987831561393387
                ],
                [
                  -1.191167691945812,
                  -0.798962723735597
                ]
              ]
            }
          }
        },
        "future_0_to_2_mm": {
          "rows": 33954,
          "trials": 2911,
          "error_mm": {
            "original": [
              2.1588989892981996,
              2.438687394336723
            ],
            "published_blend": [
              0.44120400749980915,
              0.3872070326487298
            ],
            "stay_put": [
              0.30864045240807114,
              0.30864045240807114
            ],
            "constant_velocity": [
              0.4735973171959135,
              0.3112707329853703
            ],
            "constant_acceleration": [
              1.1078417992737786,
              0.8752725214053853
            ],
            "equal_blend": [
              0.3788591686992624,
              0.25119052470897285
            ]
          },
          "paired_gain_mm": {
            "published_blend_over_stay_put": {
              "mean": [
                -0.13256355509173787,
                -0.07856658024065824
              ],
              "paired_95": [
                [
                  -0.1446923124931137,
                  -0.12128812475192051
                ],
                [
                  -0.09066211965623203,
                  -0.06730691594965334
                ]
              ]
            },
            "published_blend_over_constant_velocity": {
              "mean": [
                0.03239330969610525,
                -0.07593629966335931
              ],
              "paired_95": [
                [
                  0.018186771397709377,
                  0.04621949079295361
                ],
                [
                  -0.09032134492735903,
                  -0.06220098641276423
                ]
              ]
            },
            "published_blend_over_constant_acceleration": {
              "mean": [
                0.6666377917739694,
                0.48806548875665307
              ],
              "paired_95": [
                [
                  0.6476385304481697,
                  0.6875777153281865
                ],
                [
                  0.4692448917312928,
                  0.5084036258638356
                ]
              ]
            },
            "equal_blend_over_constant_velocity": {
              "mean": [
                0.09473814849665164,
                0.060080208276396756
              ],
              "paired_95": [
                [
                  0.08721869586164062,
                  0.10221063466209418
                ],
                [
                  0.05247086073946906,
                  0.06774905963533057
                ]
              ]
            },
            "equal_blend_over_published_blend": {
              "mean": [
                0.0623448388005466,
                0.13601650793975614
              ],
              "paired_95": [
                [
                  0.055195245061921805,
                  0.06984649859000593
                ],
                [
                  0.12863987824981882,
                  0.14371335422197182
                ]
              ]
            }
          }
        },
        "future_2_to_10_mm": {
          "rows": 5694,
          "trials": 2622,
          "error_mm": {
            "original": [
              5.93725651214373,
              4.991311986762233
            ],
            "published_blend": [
              3.8584905332953467,
              3.1647624589947374
            ],
            "stay_put": [
              3.694377878330912,
              3.694377878330912
            ],
            "constant_velocity": [
              4.8024926364600455,
              3.785097728626191
            ],
            "constant_acceleration": [
              6.633627193382598,
              4.644567909113135
            ],
            "equal_blend": [
              3.3417518040901757,
              2.485970724042799
            ]
          },
          "paired_gain_mm": {
            "published_blend_over_stay_put": {
              "mean": [
                -0.16411265496444274,
                0.5296154193361726
              ],
              "paired_95": [
                [
                  -0.2297533430022066,
                  -0.10203773776695489
                ],
                [
                  0.46867658904431825,
                  0.5912769269147006
                ]
              ]
            },
            "published_blend_over_constant_velocity": {
              "mean": [
                0.9440021031646906,
                0.6203352696314551
              ],
              "paired_95": [
                [
                  0.7727090774521858,
                  1.1179894786937674
                ],
                [
                  0.4515907516582891,
                  0.7924553458521653
                ]
              ]
            },
            "published_blend_over_constant_acceleration": {
              "mean": [
                2.775136660087242,
                1.4798054501184035
              ],
              "paired_95": [
                [
                  2.539646118891896,
                  3.0138816653384723
                ],
                [
                  1.2521324821459487,
                  1.7112828721732087
                ]
              ]
            },
            "equal_blend_over_constant_velocity": {
              "mean": [
                1.4607408323698712,
                1.2991270045833927
              ],
              "paired_95": [
                [
                  1.3520979445935588,
                  1.56961096985851
                ],
                [
                  1.188888898466356,
                  1.4118134863564482
                ]
              ]
            },
            "equal_blend_over_published_blend": {
              "mean": [
                0.5167387292051807,
                0.6787917349519322
              ],
              "paired_95": [
                [
                  0.4291088238801433,
                  0.6047149447474817
                ],
                [
                  0.5947916301493293,
                  0.7626753408572736
                ]
              ]
            }
          }
        },
        "future_10_to_20_mm": {
          "rows": 1082,
          "trials": 1003,
          "error_mm": {
            "original": [
              12.79773064058207,
              8.441954849745324
            ],
            "published_blend": [
              11.228422221891979,
              8.132702759678555
            ],
            "stay_put": [
              14.591005331025919,
              14.591005331025919
            ],
            "constant_velocity": [
              19.679888218487154,
              18.315839542043317
            ],
            "constant_acceleration": [
              16.08893100464952,
              10.345538290632318
            ],
            "equal_blend": [
              10.07904431826223,
              8.377575354136091
            ]
          },
          "paired_gain_mm": {
            "published_blend_over_stay_put": {
              "mean": [
                3.362583109133943,
                6.458302571347359
              ],
              "paired_95": [
                [
                  3.0916751198060273,
                  3.6347187009278725
                ],
                [
                  6.160752141736405,
                  6.757128744200844
                ]
              ]
            },
            "published_blend_over_constant_velocity": {
              "mean": [
                8.451465996595156,
                10.18313678236478
              ],
              "paired_95": [
                [
                  7.8501044124987995,
                  9.046265671931277
                ],
                [
                  9.554866939648475,
                  10.822410978087674
                ]
              ]
            },
            "published_blend_over_constant_acceleration": {
              "mean": [
                4.860508782757542,
                2.212835530953768
              ],
              "paired_95": [
                [
                  4.239284062461782,
                  5.485942950319782
                ],
                [
                  1.654949246834118,
                  2.7828327245262545
                ]
              ]
            },
            "equal_blend_over_constant_velocity": {
              "mean": [
                9.600843900224906,
                9.938264187907238
              ],
              "paired_95": [
                [
                  9.155963469139762,
                  10.033330436029996
                ],
                [
                  9.473144218935694,
                  10.383022601503166
                ]
              ]
            },
            "equal_blend_over_published_blend": {
              "mean": [
                1.149377903629745,
                -0.24487259445753734
              ],
              "paired_95": [
                [
                  0.7400145121968956,
                  1.5640736407367812
                ],
                [
                  -0.6704914347791063,
                  0.19630139113284836
                ]
              ]
            }
          }
        },
        "future_20_to_inf_mm": {
          "rows": 4594,
          "trials": 2911,
          "error_mm": {
            "original": [
              19.406188274516502,
              8.580629566567971
            ],
            "published_blend": [
              21.26963850394251,
              12.181877734892756
            ],
            "stay_put": [
              51.73251414165536,
              51.73251414165536
            ],
            "constant_velocity": [
              33.09508797329571,
              22.5868776501324
            ],
            "constant_acceleration": [
              40.4158222255699,
              31.274144167996656
            ],
            "equal_blend": [
              21.5930714792511,
              14.996702937132751
            ]
          },
          "paired_gain_mm": {
            "published_blend_over_stay_put": {
              "mean": [
                30.46287563771286,
                39.550636406762635
              ],
              "paired_95": [
                [
                  29.95292005946495,
                  30.970909735504947
                ],
                [
                  39.11801460817385,
                  39.978417837495215
                ]
              ]
            },
            "published_blend_over_constant_velocity": {
              "mean": [
                11.825449469353192,
                10.404999915239678
              ],
              "paired_95": [
                [
                  11.221240079266014,
                  12.423643920635863
                ],
                [
                  9.906168000433745,
                  10.88788774960508
                ]
              ]
            },
            "published_blend_over_constant_acceleration": {
              "mean": [
                19.14618372162743,
                19.092266433103873
              ],
              "paired_95": [
                [
                  18.30317562817111,
                  19.968042826520893
                ],
                [
                  18.314082347901312,
                  19.842632413875346
                ]
              ]
            },
            "equal_blend_over_constant_velocity": {
              "mean": [
                11.502016494044671,
                7.590174712999729
              ],
              "paired_95": [
                [
                  11.163703003947813,
                  11.831716152712092
                ],
                [
                  7.272785490516492,
                  7.898544339423751
                ]
              ]
            },
            "equal_blend_over_published_blend": {
              "mean": [
                -0.32343297530851056,
                -2.814825202239977
              ],
              "paired_95": [
                [
                  -0.7022088300812673,
                  0.04896660249909769
                ],
                [
                  -3.146777296107962,
                  -2.4678235148623346
                ]
              ]
            }
          }
        }
      },
      "prior_parity_mm": 1e-10
    }
  }
};
