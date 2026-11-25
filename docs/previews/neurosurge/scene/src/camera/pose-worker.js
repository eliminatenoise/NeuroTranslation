// Classic worker because the official WASM loader uses importScripts.
let detector;
let poseForSelection, observedWrists, observedArmGeometry, observedLimbPaths, limbVisible;
let handDetector, loadHandDetector, followHands, handSelections;
let startingHandDetector, handUnavailable = false;
let runningMode = 'VIDEO';
self.onmessage = async ({ data }) => {
  try {
    if (data.type === 'init') {
      const { FilesetResolver, PoseLandmarker, HandLandmarker } = await import('./vendor/vision_bundle.mjs');
      ({ poseForSelection, observedWrists, observedArmGeometry, observedLimbPaths } = await import('./limb-pose.mjs'));
      ({ followHands, handSelections } = await import('./hand-pose.mjs'));
      const {createLimbEvidence} = await import('./limb-evidence.mjs');
      limbVisible = createLimbEvidence();
      const asset = path => new URL(path, self.location.href).href;
      const fileset = await FilesetResolver.forVisionTasks(asset('vendor/wasm'));
      loadHandDetector = () => HandLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: asset('vendor/hand_landmarker.task'), delegate: 'CPU' },
        runningMode: 'IMAGE', numHands: 2,
        minHandDetectionConfidence: .6, minHandPresenceConfidence: .6, minTrackingConfidence: .6
      });
      detector = await PoseLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: asset('vendor/pose_landmarker_lite.task'), delegate: 'CPU' },
        runningMode, numPoses: 1, outputSegmentationMasks: false,
        minPoseDetectionConfidence: 0.6, minPosePresenceConfidence: 0.6, minTrackingConfidence: 0.6
      });
      self.postMessage({type: 'ready'});
    } else if (data.type === 'frame') {
      const {frame, timestamp, limb, selection} = data;
      try {
        let hands, handStatus;
        const wantsHands = Object.hasOwn(handSelections, limb);
        if (wantsHands) {
          // The optional model must not delay a later arm or leg selection.
          startingHandDetector ??= Promise.resolve().then(loadHandDetector).then(
            ready => { handDetector = ready; }, () => { handUnavailable = true; }
          );
          // A finite picture sequence needs its tracker before the first sample.
          if (data.waitForHand === true) await startingHandDetector;
          if (handDetector && !handUnavailable) {
            try { hands = followHands(handDetector.detect(frame), limb); }
            catch { handUnavailable = true; }
          }
          handStatus = handUnavailable ? 'unavailable' : !handDetector ? 'loading' : undefined;
          // The recorder only needs a hand pose. Movement mirror also uses
          // the body landmarks for its separate point forecast.
          if (!data.jointPoints) {
            self.postMessage({type: 'pose', result: hands?.pose ?? null, selection, timestamp,
              limbPaths: hands?.paths, handStatus});
            return;
          }
        }
        // An occluded knee can inherit the other shin's position from VIDEO
        // tracking across frames. Identify the two knees anew in each image.
        const checkBothFeet = limb === 'bothKnees' || limb === 'armsAndKnees';
        const mode = checkBothFeet || data.independent ? 'IMAGE' : 'VIDEO';
        if (runningMode !== mode) {
          await detector.setOptions({runningMode: mode});
          runningMode = mode;
        }
        const pose = runningMode === 'IMAGE' ? detector.detect(frame) : detector.detectForVideo(frame, timestamp);
        const points = pose.landmarks[0];
        const hasDetail = (side, allowPlainThigh) => limbVisible(frame, points, side,
          checkBothFeet && (side === 'leftLeg' || side === 'rightLeg'), allowPlainThigh);
        const selectedPose = choice => poseForSelection(points, frame.width, frame.height, choice, hasDetail);
        const result = wantsHands ? hands?.pose ?? null : selectedPose(limb);
        const message = {type: 'pose', result, selection, timestamp};
        if (handStatus) message.handStatus = handStatus;
        if (data.limbPaths === true && result) message.limbPaths = hands ? hands.paths : observedLimbPaths(points, result);
        if (data.jointPoints === true) {
          const xy = Array(33).fill(null);
          for (let i = 0; i < xy.length; i++) {
            const p = points?.[i];
            if (p && p.visibility >= .65 && p.x >= 0 && p.x <= 1 && p.y >= 0 && p.y <= 1) {
              xy[i] = [p.x * frame.width, p.y * frame.height];
            }
          }
          // The forecast uses the same wrist evidence even when a different body part follows.
          const wrists = limb === 'bothArms' || limb === 'armsAndKnees' ? result : selectedPose('bothArms');
          if (!wrists?.leftArm) xy[15] = null;
          if (!Number.isFinite(wrists?.joints?.r_elbow_flex)) xy[16] = null;
          message.xy = xy;
        }
        if (data.captureWrists === true && (result?.leftArm || Number.isFinite(result?.joints?.r_elbow_flex))) {
          message.wrists = observedWrists(points, frame.width, frame.height, result);
          message.armGeometry = observedArmGeometry(points, frame.width, frame.height, result);
        }
        self.postMessage(message);
      } finally {
        frame.close();
      }
    }
  } catch (error) {
    self.postMessage({type: 'error', message: String(error.message || error)});
  }
};
