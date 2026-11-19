"use strict";

(() => {
  const maxMatBytes = 250 * 1024 * 1024;
  const peopleCount = 3;
  const days = [1, 2];
  const repeats = [1, 2];
  const trialCount = peopleCount * days.length * repeats.length;
  const issueCount = 592;
  const horizon = 24;
  const matName = /^S([1-9][0-9]*)_Day([12])_Session5_Task2_Trial([12])\.mat$/;
  const bindings = ["protocol_sha256", "population_sha256", "baseline_sha256", "baseline_protocol_sha256"];

  function groupFiles(files) {
    if (files.length > trialCount) throw Error("This fit uses exactly 12 MATLAB recordings.");
    const people = new Map();
    for (const file of files) {
      const match = matName.exec(file.name);
      if (!match || match[0] !== file.name || file.size < 1 || file.size > maxMatBytes) {
        throw Error("Choose compatible Session 5, Task 2 MAT files from Days 1 and 2.");
      }
      const [, person, day, repeat] = match;
      const byDayRepeat = people.get(person) ?? new Map();
      const slot = `${day}${repeat}`;
      if (byDayRepeat.has(slot)) throw Error("Choose each person, day and repeat only once.");
      byDayRepeat.set(slot, file);
      people.set(person, byDayRepeat);
    }
    if (people.size > peopleCount) throw Error("Choose files from exactly three people.");
    return people;
  }

  function roster(files) {
    if (files.length !== trialCount) throw Error("Choose exactly 12 MATLAB recordings.");
    const people = groupFiles(files);
    if (people.size !== peopleCount || [...people.values()].some(group => group.size !== days.length * repeats.length)) {
      throw Error("Choose both repeats from both days for exactly three people.");
    }
    // IDs can be wider than a JavaScript integer. Sort their canonical decimal text.
    const sorted = [...people.keys()].sort((a, b) => a.length - b.length || (a < b ? -1 : 1));
    return sorted.flatMap(person => days.flatMap(day => repeats.map(repeat => people.get(person).get(`${day}${repeat}`))));
  }

  function fitSpecification(reader) {
    const bundled = reader.checkFit(JSON.parse(globalThis.CEMHSEY_ARRAY_FIT_BYTES));
    const arms = Object.entries(bundled.models).map(([name, model]) => [name, model.feature_names]);
    const [largest, columns] = arms.reduce((a, b) => a[1].length > b[1].length ? a : b);
    if (arms.some(([, keys]) => keys.some((key, i) => key !== columns[i]))) {
      throw Error("These reader models use a different feature layout.");
    }
    return { bundled, arms, largest, width: columns.length };
  }

  async function addTrial(design, trial, trialIndex, reader, largest, signal, progress) {
    const { values, deltas, width } = design;
    const windows = [reader.bin(trial.rms, 0), reader.bin(trial.rms, 1)];
    let computeMs = 0;
    let start = performance.now();
    for (let i = 0; i < issueCount; i++) {
      const older = windows[i % windows.length];
      const recent = reader.bin(trial.rms, i + 2);
      windows[i % windows.length] = recent;
      const row = reader.features(trial, i, older, recent);
      const features = row.inputs[largest];
      const delta = trial.force[row.tick + horizon] - row.now;
      if (features.length !== width || !features.every(Number.isFinite) || !Number.isFinite(delta)) {
        throw Error("A training row has invalid force or muscle readings.");
      }
      const index = trialIndex * issueCount + i;
      values.set(features, index * width);
      deltas[index] = delta;
      if (performance.now() - start >= 12 && i < issueCount - 1) {
        computeMs += performance.now() - start;
        progress((i + 1) / issueCount);
        await new Promise(resolve => setTimeout(resolve, 0));
        signal.throwIfAborted();
        start = performance.now();
      }
    }
    progress(1);
    return computeMs + performance.now() - start;
  }

  async function readTrial(file, importer, signal, onProgress) {
    signal.throwIfAborted();
    const operation = importer.start(file, { onProgress: ({ fraction }) => onProgress(fraction) });
    const cancel = () => operation.cancel();
    signal.addEventListener("abort", cancel, { once: true });
    try {
      return await operation.promise;
    } finally {
      signal.removeEventListener("abort", cancel);
    }
  }

  async function fitCohort(files, { signal, onProgress = () => {} }) {
    signal.throwIfAborted();
    const reader = globalThis.ArrayPinch;
    const { bundled, arms, largest, width } = fitSpecification(reader);
    const selection = roster(files);
    const design = { values: new Float64Array(trialCount * issueCount * width),
      deltas: new Float64Array(trialCount * issueCount), width };
    const seen = new Set();
    const times = [];

    for (let i = 0; i < selection.length; i++) {
      const report = (stage, fraction) => onProgress({ stage, trial: i + 1, total: trialCount, fraction });
      const start = performance.now();
      report("read", 0);
      let trial;
      try {
        trial = await readTrial(selection[i], globalThis.CemhseyMat, signal, fraction => report("read", fraction));
      } catch {
        signal.throwIfAborted();
        throw Error(`Recording ${i + 1} could not be read. Use original MAT files with the prescribed force and EMG readings.`);
      }
      signal.throwIfAborted();
      const parsedAt = performance.now();
      // Reuse the reader's canonical packet identity across MAT and JSON.
      const digest = await globalThis.PinchIntervals.packetIdentity(trial);
      signal.throwIfAborted();
      if (seen.has(digest)) throw Error("Two selected recordings contain identical force and EMG summaries. Check for duplicate recordings.");
      seen.add(digest);
      const hashedAt = performance.now();
      report("features", 0);
      const featureComputeMs = await addTrial(design, trial, i, reader, largest, signal, fraction => report("features", fraction));
      times.push({ readMs: parsedAt - start, fingerprintMs: hashedAt - parsedAt,
        featureMs: performance.now() - hashedAt, featureComputeMs });
    }

    onProgress({ stage: "fit", trial: trialCount, total: trialCount, fraction: 0 });
    const { models, computeMs, totalMs } = await globalThis.CemhseyRidge.solveInWorker(design, arms, signal);
    signal.throwIfAborted();
    const fit = reader.checkFit({
      format: bundled.format,
      ...Object.fromEntries(bindings.map(key => [key, bundled[key]])),
      timing_mode: bundled.timing_mode,
      fit_origin: "user_supplied_local",
      training: {
        people: peopleCount,
        days_per_person: days.length,
        repeats_per_person_day: repeats.length,
        trials: trialCount,
        issue_ticks_per_trial: issueCount,
        issue_windows: trialCount * issueCount,
        input: "user_selected_session5_task2_mat",
        packet_sha256: [...seen].sort(),
      },
      evaluation: "not_performed",
      calibration: "requires_separate_trials",
      models,
    }, bundled.protocol_sha256);
    return { fit, timing: { trials: times, ridgeWorkerMs: computeMs, ridgeRoundTripMs: totalMs } };
  }


  function mount(host, { onApply } = {}) {
    const embedded = typeof onApply === "function";
    const id = name => embedded ? `embedded-fit-${name}` : name;
    const find = name => host.querySelector(`#${id(name)}`);
    const title = embedded ? "h3" : "h2";
    host.innerHTML = `
      <section aria-labelledby="${id("choose-title")}">
        <${title} id="${id("choose-title")}">Choose the training recordings</${title}>
        <p>Add the original CEMHSEY GRASP MATLAB files for Session&nbsp;5, Task&nbsp;2. Choose exactly three people and both repeats from Days&nbsp;1 and&nbsp;2 for each person. You can add files from several folders.</p>
        <label for="${id("training-files")}">Add training MAT files</label>
        <input class="fit-files" id="${id("training-files")}" type="file" accept=".mat" multiple disabled>
        <div class="actions fit-actions">
          <button id="${id("run-fit")}" type="button" disabled>Fit four models</button>
          <button id="${id("clear-training")}" class="secondary" type="button" disabled>Clear selection</button>
          <button id="${id("cancel-fit")}" class="secondary" type="button" disabled>Cancel fit</button>
        </div>
        <progress class="fit-progress" id="${id("fit-progress")}" aria-label="Training progress" max="12" value="0" hidden></progress>
        <p id="${id("fit-status")}" class="hint fit-status" role="status">Opening the fitter…</p>
      </section>
      <section id="${id("result")}" aria-labelledby="${id("save-title")}" hidden>
        <${title} id="${id("save-title")}">Use the fitted weights</${title}>
        ${embedded ? "<p>Apply the weights to this reader, or download them to use again later.</p>" :
          "<p>Download the JSON, then open <strong>Choose forecast weights</strong> in the array reader and select the file.</p>"}
        <div class="actions">
          ${embedded ? `<button id="${id("apply-fit")}" type="button">Use this fit in the reader</button>` : ""}
          <button id="${id("download-fit")}" class="${embedded ? "secondary" : ""}" type="button">Download fitted weights</button>
          ${embedded ? "" : '<a href="../index.html">Open the array reader</a>'}
        </div>
        ${embedded ? `<p id="${id("apply-status")}" class="hint" role="status"></p>` : ""}
      </section>
      <section aria-labelledby="${id("check-title")}">
        <${title} id="${id("check-title")}">Keep a separate test</${title}>
        <p>A forecast on a training recording is an in-sample check. This fit uses 592 forecast times per recording and has no independent evaluation. Use held-out people and days to test generalisation. Build calibration bands on separate trials, then assess their coverage on fresh recordings.</p>
        <details>
          <summary>What goes into the fit?</summary>
          <p>The four models start with recent force and the task cue, then add whole-forearm amplitude, contrasts across the five electrode grids, and similarity in channel ranks. Each model learns the change from the current pinch reading. Force is a fraction of same-day maximum voluntary contraction. The nominal sample indices do not establish physical synchronisation or device latency.</p>
          <p>A fixed ridge penalty limits the size of the slopes after they are put on a common scale. The training recordings determine the centre and spread of each feature. <a href="${embedded ? "" : "../"}PROTOCOL.md">Read the frozen study protocol</a>.</p>
        </details>
        <p class="hint">The browser reads one recording at a time on this device. The download holds weights, scaling values, training counts and fingerprints of the force and EMG summaries. The reader uses those fingerprints to flag reused training inputs. Someone with the same recording can check for a match, so keep the download private if you used private recordings.</p>
      </section>`;

    const input = find("training-files");
    const clear = find("clear-training");
    const run = find("run-fit");
    const cancel = find("cancel-fit");
    const progress = find("fit-progress");
    const status = find("fit-status");
    const result = find("result");
    const download = find("download-fit");
    const apply = find("apply-fit");
    const applyStatus = find("apply-status");
    let selected = [];
    let controller = null;
    let ready = null;
    let applying = false;

    function setStatus(message) {
      if (status.textContent !== message) status.textContent = message;
    }

    function syncControls() {
      const busy = controller !== null || applying;
      input.disabled = busy;
      clear.disabled = busy || selected.length === 0;
      run.disabled = busy || selected.length !== trialCount;
      cancel.disabled = controller === null || controller.signal.aborted;
      result.hidden = ready === null;
      if (apply) apply.disabled = applying;
    }

    input.addEventListener("change", () => {
      const added = Array.from(input.files);
      input.value = "";
      if (!added.length || controller || applying) return;
      try {
        const next = [...selected, ...added];
        groupFiles(next);
        if (next.length === trialCount) roster(next);
        selected = next;
        ready = null;
        setStatus(selected.length === trialCount ? "12 of 12 recordings selected. Ready to fit."
          : `${selected.length} of 12 recordings selected. Add the remaining files.`);
        syncControls();
      } catch (error) {
        setStatus(`${error.message} ${selected.length} of 12 recordings are still selected.`);
      }
    });

    clear.addEventListener("click", () => {
      selected = [];
      ready = null;
      setStatus("Selection cleared. Choose the training recordings.");
      syncControls();
      input.focus();
    });

    run.addEventListener("click", async () => {
      if (controller || applying || selected.length !== trialCount) return;
      controller = new AbortController();
      const signal = controller.signal;
      const files = selected;
      selected = [];
      ready = null;
      if (applyStatus) applyStatus.textContent = "";
      progress.hidden = false;
      progress.value = 0;
      syncControls();
      cancel.focus();
      try {
        const { fit } = await fitCohort(files, { signal, onProgress: ({ stage, trial, total, fraction }) => {
          if (signal.aborted) return;
          if (stage === "fit") {
            progress.removeAttribute("value");
            setStatus("Solving the four forecast models…");
          } else {
            const part = Number.isFinite(fraction) ? Math.min(1, Math.max(0, fraction)) : 0;
            const read = stage === "read";
            progress.value = Math.max(progress.value, trial - 1 + (read ? 0.8 * part : 0.8 + 0.2 * part));
            setStatus(`${read ? "Reading" : "Preparing"} recording ${trial} of ${total}…`);
          }
        } });
        ready = new TextEncoder().encode(`${JSON.stringify(fit)}\n`);
        setStatus(embedded ? "Fit complete. The reader is ready for your new weights." :
          "Fit complete. Save the weights to use them in the reader.");
      } catch (error) {
        setStatus(signal.aborted ? "Fit cancelled. Choose recordings to start again." : error.message);
      } finally {
        progress.hidden = true;
        controller = null;
        syncControls();
        if (ready) (apply ?? download).focus();
        else input.focus();
      }
    });

    cancel.addEventListener("click", () => {
      controller?.abort();
      syncControls();
    });

    apply?.addEventListener("click", async () => {
      if (!ready || applying) return;
      applying = true;
      applyStatus.textContent = "Applying these weights…";
      syncControls();
      try {
        await onApply(ready.slice());
        applyStatus.textContent = "These weights are now active in the reader.";
      } catch (error) {
        applyStatus.textContent = error.message;
      } finally {
        applying = false;
        syncControls();
      }
    });

    download.addEventListener("click", () => {
      if (!ready) return;
      const blob = new Blob([ready], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "cemhsey-array-local-fit.json";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });

    try {
      fitSpecification(globalThis.ArrayPinch);
      if (!globalThis.CemhseyMat?.start || !globalThis.CemhseyRidge?.solveInWorker ||
          !globalThis.PinchIntervals?.packetIdentity || !globalThis.crypto?.subtle) {
        throw Error("The browser could not start the local fitter.");
      }
      setStatus("No recordings selected.");
      syncControls();
    } catch {
      setStatus("The local fitter could not open. Keep all the reader files together and open it over HTTPS or from the extracted ZIP.");
    }
  }

  globalThis.CemhseyBrowserFit = { roster, fitCohort, mount };
  const standalone = globalThis.document?.querySelector("#standalone-fit");
  if (standalone) mount(standalone);
})();
