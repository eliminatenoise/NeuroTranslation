(() => {
  const section = document.getElementById("comparison");
  const scope = document.getElementById("recording");
  const condition = document.getElementById("condition");
  const scores = document.getElementById("score-rows");
  const changes = document.getElementById("change-rows");
  const summary = document.getElementById("selection");
  const scoreboard = JSON.parse(document.getElementById("benchmark-data").textContent);
  const number = new Intl.NumberFormat("en", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const count = new Intl.NumberFormat("en");
  const ceiling = Math.ceil(Math.max(...Object.values(scoreboard.scopes).flatMap(
    (group) => Object.values(group.mean_error_ns).flatMap((values) => Object.values(values))
  )));

  function cell(row, tag, value) {
    const node = document.createElement(tag);
    node.textContent = value;
    if (tag === "th") node.scope = "row";
    row.append(node);
    return node;
  }

  function signed(value) {
    return value < 0 ? `−${number.format(-value)}` : value > 0 ? `+${number.format(value)}` : number.format(value);
  }

  function render() {
    const group = scoreboard.scopes[scope.value];
    const state = condition.value;
    const rows = scoreboard.methods
      .map(({ id, label }) => ({ id, label, error: group.mean_error_ns[id][state] }))
      .sort((left, right) => left.error - right.error);
    scores.replaceChildren(...rows.map(({ id, label, error }) => {
      const row = document.createElement("tr");
      row.dataset.method = id;
      if (id === "augmented_08") row.className = "highlight";
      cell(row, "th", label);
      const result = cell(row, "td", number.format(error));
      const bar = document.createElement("meter");
      bar.min = 0;
      bar.max = ceiling;
      bar.value = error;
      bar.setAttribute("aria-hidden", "true");
      result.prepend(bar);
      return row;
    }));

    const contrasts = group.paired_comparisons;
    const labelFor = new Map(scoreboard.methods.map(({ id, label }) => [id, label]));
    changes.replaceChildren(...Object.entries(contrasts).map(([id, comparison]) => {
      const row = document.createElement("tr");
      const interval = comparison.participant_bootstrap_95_ns[state];
      row.dataset.comparator = id;
      cell(row, "th", labelFor.get(id));
      cell(row, "td", signed(comparison.average_model_minus_control_ns[state]));
      cell(row, "td", `${signed(interval[0])} to ${signed(interval[1])}`);
      cell(row, "td", `${comparison.people_with_lower_error[state]} of ${group.people}`);
      return row;
    }));
    summary.textContent = `${group.label} · ${count.format(group.issues)} forecast times · ${group.people} people`;
  }

  scope.addEventListener("change", render);
  condition.addEventListener("change", render);
  render();
  section.hidden = false;
})();
