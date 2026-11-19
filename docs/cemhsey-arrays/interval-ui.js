"use strict";

(() => {
  const el = id => document.getElementById(id);
  const math = globalThis.PinchIntervals;
  const api = globalThis.ArrayPinch;
  const encoder = new TextEncoder();
  const maxPacketBytes = 3 * 1024 * 1024;
  const maxCalibrationPackets = 32;
  const modelChoice = el("band-model");
  const schemeChoice = el("band-scheme");
  const profileFile = el("profile-file");
  const resetProfile = el("reset-profile");
  const files = el("calibration-files");
  const confirm = el("calibration-confirm");
  const calibrate = el("calibrate");
  const save = el("save-profile");
  const canvas = el("forecast-plot");
  const schemeLabel = {pooled: "All cutoffs", by_issue_phase: "Matching cue phase"};
  const trainingPackets = fit => fit?.fit_origin === "user_supplied_local" ? fit.training?.packet_sha256 : undefined;
  const trainingText = {
    checking: "Checking this trial against the fitting packets…",
    matched: "Fitting recording (in-sample). Point errors describe data used to fit these weights.",
    distinct: "The packet differs from the exact fitting packets. Check whether its person or source recording overlaps.",
    unknown: "Training overlap is unknown. These weights have no saved fitting packet fingerprints.",
    unavailable: "Training overlap could not be checked in this browser."
  };

  function validateTraining(fit) {
    const list = trainingPackets(fit);
    if (list === undefined) return;
    if (!Array.isArray(list) || list.length !== 12 || new Set(list).size !== 12 ||
        !list.every(id => typeof id === "string" && /^[a-f0-9]{64}$/.test(id))) {
      throw Error("The fitted model needs 12 distinct fitting packet fingerprints.");
    }
  }

  function setup(writeRows, onProfileChange) {
    let bundled = null;
    try {
      if (globalThis.CEMHSEY_ARRAY_PROFILE) bundled = math.validate(globalThis.CEMHSEY_ARRAY_PROFILE);
    } catch {
      // A damaged profile must not stop any point forecasts.
    }
    let selected = bundled;
    let trial = null;
    let invented = false;
    let trialIdentity = null;
    let fit = null;
    let fitHash = null;
    let checkingFit = false;
    let checkingTrial = false;
    let readingProfile = false;
    let readForecast = null;
    let fitToken = 0;
    let trialToken = 0;
    let profileToken = 0;
    let calibrating = false;
    let index = 0;
    let reveal = false;
    let lastPlot = [];

    function trainingOverlap() {
      if (!trial || invented || fit?.fit_origin !== "user_supplied_local") return null;
      const members = trainingPackets(fit);
      if (!members) return "unknown";
      if (checkingTrial) return "checking";
      if (!trialIdentity) return "unavailable";
      return members.includes(trialIdentity) ? "matched" : "distinct";
    }

    function profileUsesTraining(profile) {
      const members = trainingPackets(fit);
      return members && profile.calibration_packet_sha256?.some(id => members.includes(id));
    }

    function availability() {
      if (!fit || checkingFit) return {note: "Verifying which calibration belongs to these weights…"};
      if (!fitHash) return {note: "Bands need a verifiable copy of the active fit. Point forecasts are available."};
      const overlap = trainingOverlap();
      if (overlap === "matched" || overlap === "checking" || overlap === "unavailable") {
        return {note: overlap === "matched" ? "Calibration bands are withheld for the fitting recording." : trainingText[overlap]};
      }
      if (!selected) return {note: "Choose a profile for these weights to see bands."};
      if (!math.matches(selected, fit, fitHash)) {
        return {note: "This calibration belongs to a different fit. Point forecasts are available."};
      }
      if (profileUsesTraining(selected)) return {note: "This calibration includes a fitting packet. Choose separate calibration trials."};
      if (trial && !math.compatibleTrial(selected, invented)) {
        return {note: invented ? "Bands for local recordings are hidden on the invented pinch." :
          "The invented profile applies only to the invented pinch. Load or make a calibration profile for local packets."};
      }
      if (selected.profile_origin === "user_supplied_local") {
        const members = selected.calibration_packet_sha256;
        if (!members) {
          return {note: "This older local profile has no calibration packet fingerprints. Calculate and save new bands before using it for assessment."};
        }
        if (trial) {
          if (checkingTrial) return {note: "Checking that this packet is outside the local calibration set…"};
          if (!trialIdentity) {
            return {note: "Could not verify this packet’s fingerprint. Reopen the packet in a current browser to use local bands."};
          }
          if (members.includes(trialIdentity)) {
            return {note: "This packet was used to set these widths. Choose a separate assessment packet."};
          }
        }
      }
      return {profile: selected};
    }

    function updateControls() {
      profileFile.disabled = !fit || !globalThis.crypto?.subtle;
      resetProfile.disabled = (!readingProfile && selected === bundled) || !bundled;
      files.disabled = !fitHash;
      calibrate.disabled = !calibrating && (!fitHash || !confirm.checked || !files.files.length);
      save.disabled = selected?.profile_origin !== "user_supplied_local" ||
        !math.matches(selected, fit, fitHash) || !selected.calibration_packet_sha256;
    }

    function draw() {
      if (trial) PinchPlot.draw(canvas, lastPlot, 60 + 10 * index, schemeChoice.value === "by_issue_phase");
    }

    function render() {
      updateControls();
      const {profile, note} = availability();
      const trainingStatus = trainingText[trainingOverlap()] ?? "";
      if (el("training-status").textContent !== trainingStatus) el("training-status").textContent = trainingStatus;
      const origin = profile ? math.origins[profile.profile_origin] : null;
      const phase = math.phaseAt(60 + 10 * index);
      const count = profile ? schemeChoice.value === "pooled" ? profile.pooled_count : profile.phase_counts[phase] : 0;
      const group = schemeChoice.value === "by_issue_phase" ? " in the selected cue phase." : " pooled across cue phases.";
      const description = origin ? origin + " · " + count.toLocaleString() + " calibration cutoffs" + group : note;
      el("band-status").textContent = trial ? description : "";
      el("profile-status").textContent = description;
      if (!trial || !readForecast) return;
      const key = modelChoice.value;
      const scheme = schemeChoice.value;
      const points = [];
      for (let i = 0; i <= index; i++) {
        const {tick, estimates} = readForecast(i);
        const point = estimates[key];
        points.push({tick, point, observed: reveal ? trial.force[tick + math.horizon] : undefined});
      }
      let hasRange = Boolean(profile);
      if (profile) {
        try {
          for (const point of points) point.range = math.band(profile, key, scheme, point.point, point.tick);
        } catch (error) {
          for (const point of points) delete point.range;
          hasRange = false;
          el("band-status").textContent = error.message + " Point forecasts are available.";
        }
      }
      const last = points.at(-1);
      const values = [["Forecast", last.point.toFixed(7)]];
      if (hasRange) values.push(
        ["Lower band edge", last.range.lower.toFixed(7)], ["Upper band edge", last.range.upper.toFixed(7)]
      );
      writeRows(el("selected-values"), values);
      el("band-key").hidden = !hasRange;
      el("observed-key").hidden = !reveal;
      canvas.setAttribute("aria-label", api.labels[key] + " at its target times through the selected cutoff");
      lastPlot = points;
      draw();
    }

    function refresh() {
      try {
        render();
      } catch {
        lastPlot = [];
        writeRows(el("selected-values"), []);
        el("band-status").textContent = "A forecast before this cutoff exceeds the numerical range.";
        el("band-key").hidden = true;
        el("observed-key").hidden = true;
        draw();
      }
    }

    function cancelCalibration() {
      if (!calibrating) return;
      profileToken++;
      calibrating = false;
      readingProfile = false;
      calibrate.textContent = "Calculate local bands";
      el("calibration-status").textContent = "Calibration cancelled.";
      updateControls();
    }

    function setFit(next, exactBytes) {
      const request = ++fitToken;
      profileToken++;
      cancelCalibration();
      readingProfile = false;
      fit = next;
      reveal = false;
      fitHash = null;
      checkingFit = Boolean(exactBytes);
      readForecast = trial ? math.cache(trial, fit) : null;
      el("calibration-status").textContent = "";
      refresh();
      if (!exactBytes) return;
      math.digest(exactBytes).then(identity => {
        if (request === fitToken) fitHash = identity;
      }).catch(() => {}).finally(() => {
        if (request !== fitToken) return;
        checkingFit = false;
        onProfileChange();
        refresh();
      });
    }

    function setTrial(next, isInvented) {
      const request = ++trialToken;
      cancelCalibration();
      trial = next;
      invented = isInvented;
      trialIdentity = null;
      checkingTrial = !isInvented;
      readForecast = math.cache(next, fit);
      if (!checkingTrial) return;
      math.packetIdentity(next).then(identity => {
        if (request === trialToken) trialIdentity = identity;
      }).catch(() => {}).finally(() => {
        if (request !== trialToken) return;
        checkingTrial = false;
        if (selected?.profile_origin === "user_supplied_local" || trainingPackets(fit)) onProfileChange();
        refresh();
      });
    }

    function changeProfile(profile) {
      selected = profile;
      onProfileChange();
      refresh();
    }

    profileFile.addEventListener("change", async () => {
      const file = profileFile.files[0];
      if (!file) return;
      cancelCalibration();
      const request = ++profileToken;
      readingProfile = true;
      updateControls();
      el("profile-status").textContent = "Reading calibration widths…";
      try {
        if (file.size > 32 * 1024) throw Error("Choose a calibration profile under 32 KiB.");
        const profile = math.validate(JSON.parse(await file.text()));
        if (request !== profileToken) return;
        if (!math.matches(profile, fit, fitHash)) throw Error("This calibration does not match the exact active fit.");
        if (profileUsesTraining(profile)) throw Error("This calibration includes a fitting packet. Choose separate calibration trials.");
        changeProfile(profile);
        el("calibration-status").textContent = "";
      } catch (error) {
        if (request !== profileToken) return;
        profileFile.value = "";
        const detail = error instanceof SyntaxError ? "Choose a valid calibration JSON file." : error.message;
        el("profile-status").textContent = detail + " The selected profile remains as before.";
        el("calibration-status").textContent = detail;
      } finally {
        if (request === profileToken) {
          readingProfile = false;
          updateControls();
        }
      }
    });

    resetProfile.addEventListener("click", () => {
      profileToken++;
      cancelCalibration();
      readingProfile = false;
      profileFile.value = "";
      el("calibration-status").textContent = "";
      changeProfile(bundled);
    });

    files.addEventListener("change", () => { cancelCalibration(); updateControls(); });
    confirm.addEventListener("change", () => { if (!confirm.checked) cancelCalibration(); updateControls(); });
    calibrate.addEventListener("click", async () => {
      if (calibrating) {
        cancelCalibration();
        return;
      }
      if (!fitHash || !confirm.checked || !files.files.length) return;
      const inputs = Array.from(files.files);
      if (inputs.length > maxCalibrationPackets) {
        el("calibration-status").textContent = "Choose up to " + maxCalibrationPackets + " calibration packets at once.";
        return;
      }
      const request = ++profileToken;
      const activeFit = fit;
      const activeHash = fitHash;
      const assessment = trial && !invented ? trial : null;
      const identities = new Set();
      const isCurrent = () => request === profileToken;
      calibrating = true;
      readingProfile = false;
      calibrate.textContent = "Cancel calibration";
      updateControls();
      el("calibration-status").textContent = "Checking calibration inputs…";
      try {
        const assessmentIdentity = assessment ? trialIdentity ?? await math.packetIdentity(assessment) : null;
        async function* records() {
          for (const file of inputs) {
            if (!isCurrent()) return;
            if (file.size > maxPacketBytes) throw Error("Each calibration packet must be smaller than 3 MiB.");
            const record = api.packet(JSON.parse(await file.text()), activeFit.protocol_sha256);
            const id = await math.packetIdentity(record);
            if (!isCurrent()) return;
            if (trainingPackets(activeFit)?.includes(id)) throw Error("A calibration packet was used to fit these weights.");
            if (id === assessmentIdentity) throw Error("The active assessment packet is in the calibration set.");
            if (identities.has(id)) throw Error("The calibration set contains a repeated packet.");
            identities.add(id);
            el("calibration-status").textContent = "Calculating residuals · trial " + identities.size + " of " + inputs.length + "…";
            yield record;
          }
        }
        const next = await math.calibrate(records(), activeFit, activeHash, "user_supplied_local", isCurrent);
        if (!next || !isCurrent()) return;
        profileFile.value = "";
        changeProfile(math.validate({
          ...next, calibration_packet_sha256: Array.from(identities).sort()
        }));
        el("calibration-status").textContent = "Local bands are ready. Save the profile to reopen them with these weights.";
      } catch (error) {
        if (isCurrent()) el("calibration-status").textContent = error instanceof SyntaxError ?
          "One calibration packet is not valid JSON." : error.message;
      } finally {
        if (isCurrent()) {
          calibrating = false;
          calibrate.textContent = "Calculate local bands";
          updateControls();
        }
      }
    });

    save.addEventListener("click", () => {
      if (save.disabled) return;
      const blob = new Blob([JSON.stringify(selected, null, 2) + "\n"], {type: "application/json"});
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "cemhsey-local-calibration.json";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });

    modelChoice.addEventListener("change", refresh);
    schemeChoice.addEventListener("change", refresh);
    if (typeof ResizeObserver === "function") new ResizeObserver(draw).observe(canvas);
    else globalThis.addEventListener("resize", draw);

    return {
      setFit, setTrial, schemeLabel, validateTraining, trainingOverlap,
      render(nextIndex, showReadings) {
        index = nextIndex;
        reveal = showReadings;
        refresh();
      },
      score(isCurrent) {
        return math.score(trial, readForecast, availability().profile, isCurrent);
      },
      bundledFitBytes(bundledFit) {
        const source = globalThis.CEMHSEY_ARRAY_FIT_BYTES;
        try {
          return typeof source === "string" && JSON.stringify(JSON.parse(source)) === JSON.stringify(bundledFit) ?
            encoder.encode(source) : null;
        } catch {
          return null;
        }
      }
    };
  }

  globalThis.PinchIntervalUI = {setup};
})();
