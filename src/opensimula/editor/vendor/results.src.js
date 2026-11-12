// Results viewer of OpenSimula (anywidget front end).
//
// Bundled with uPlot by `npm run build` into ../static/results.js, a module with
// no runtime imports: see README.md for why it has to be self-contained.
//
// Python prepares the data (resampling, interval) and sends the points to draw
// in the "series" traitlet; this side only lists the variables, keeps the
// selection and draws.

import uPlot from "uplot";
import uplotCss from "uplot/dist/uPlot.min.css";

// Categorical palette, fixed order: a series keeps its slot (colour) while it
// stays selected, whatever else is added or removed.
const PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"];
const MAX_SERIES = PALETTE.length;
const MAX_TABLE_ROWS = 2000;
const CHART_HEIGHTS = [200, 300, 400, 500];

const FREQUENCIES = [
  ["none", "Time step"],
  ["hourly", "Hourly"],
  ["daily", "Daily"],
  ["monthly", "Monthly"],
  ["yearly", "Yearly"],
];
const AGGREGATIONS = [
  ["mean", "Mean"],
  ["sum", "Sum"],
  ["max", "Maximum"],
  ["min", "Minimum"],
];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function h(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else node.setAttribute(key, value);
  }
  for (const child of children) node.appendChild(child);
  return node;
}

// The dates are the simulation's own (no time zone): they travel as seconds of
// the same wall time in UTC, and are shown in UTC so that they do not move.
function utc(seconds) {
  return new Date(seconds * 1000);
}

function pad(n) {
  return String(n).padStart(2, "0");
}

function formatDate(seconds, frequency) {
  const d = utc(seconds);
  const day = `${pad(d.getUTCDate())} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
  if (frequency === "yearly") return String(d.getUTCFullYear());
  if (frequency === "monthly") return `${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
  if (frequency === "daily") return day;
  return `${day} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`;
}

function formatValue(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "–";
  const abs = Math.abs(value);
  if (abs !== 0 && (abs >= 1e6 || abs < 1e-3)) return value.toExponential(3);
  return value.toLocaleString("en-US", { maximumFractionDigits: abs >= 100 ? 1 : 3 });
}

// Tick labels of the time axis, by the spacing between ticks (seconds)
function timeTick(seconds, incr) {
  const d = utc(seconds);
  if (incr >= 365 * 86400) return String(d.getUTCFullYear());
  if (incr >= 28 * 86400) return d.getUTCMonth() === 0 ? `${MONTHS[0]} ${d.getUTCFullYear()}` : MONTHS[d.getUTCMonth()];
  if (incr >= 86400) return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
  const time = `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`;
  return d.getUTCHours() === 0 && d.getUTCMinutes() === 0 ? `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}` : time;
}

function isoDay(text) {
  return text ? text.slice(0, 10) : "";
}

function render({ model, el }) {
  const style = document.createElement("style");
  style.textContent = uplotCss;
  el.appendChild(style);

  const search = h("input", { class: "osm-r-search", type: "search", placeholder: "Filter variables…" });
  const tree = h("div", { class: "osm-r-tree" });
  const list = h("div", { class: "osm-r-list" }, [search, tree]);

  const frequency = h("select");
  for (const [value, label] of FREQUENCIES) frequency.appendChild(h("option", { value, text: label }));
  const aggregation = h("select");
  for (const [value, label] of AGGREGATIONS) aggregation.appendChild(h("option", { value, text: label }));
  const from = h("input", { type: "date" });
  const to = h("input", { type: "date" });
  const chartHeight = h("select");
  const viewButton = h("button", { type: "button", text: "Table" });
  const csvButton = h("button", { type: "button", text: "CSV" });
  const clearButton = h("button", { type: "button", text: "Clear" });
  const toolbar = h("div", { class: "osm-r-toolbar" }, [
    h("label", { text: "Frequency" }, [frequency]),
    h("label", { text: "Aggregation" }, [aggregation]),
    h("label", { text: "From" }, [from]),
    h("label", { text: "To" }, [to]),
    h("label", { text: "Height" }, [chartHeight]),
    h("span", { class: "osm-r-spacer" }),
    viewButton,
    csvButton,
    clearButton,
  ]);
  const content = h("div", { class: "osm-r-content" });
  const main = h("div", { class: "osm-r-main" }, [toolbar, content]);
  const root = h("div", { class: "osm-results" }, [list, main]);
  root.style.height = `${model.get("height")}px`;
  el.appendChild(root);

  let showTable = false;
  const expanded = new Set(); // "type" and "type/component" rows that are open
  let charts = [];
  let timeRange = null; // [min, max] shown, kept when the charts are drawn again

  // The charts share the time axis: a zoom or a pan of one is applied to all.
  // uPlot runs the setScale hooks later, not inside setScale, so a chart that
  // receives the range calls this again: only the charts that do not show it
  // yet are changed, or the range would bounce between them for ever.
  function shareTimeRange(u) {
    const { min, max } = u.scales.x;
    const [first, last] = [u.data[0][0], u.data[0][u.data[0].length - 1]];
    timeRange = min <= first && max >= last ? null : [min, max];
    const tolerance = 1e-6 * (max - min);
    for (const chart of charts) {
      const x = chart.scales.x;
      if (chart !== u && (Math.abs(x.min - min) > tolerance || Math.abs(x.max - max) > tolerance)) {
        chart.setScale("x", { min, max });
      }
    }
  }

  // Shift + drag moves the time range without changing the zoom
  function panHandler(u, target, handler) {
    return (event) => {
      if (!event.shiftKey || event.button !== 0) return handler(event);
      event.preventDefault();
      const startX = event.clientX;
      const { min, max } = u.scales.x;
      const [first, last] = [u.data[0][0], u.data[0][u.data[0].length - 1]];
      const perPixel = (max - min) / u.over.getBoundingClientRect().width;
      u.over.style.cursor = "grabbing";
      const move = (e) => {
        let shift = (startX - e.clientX) * perPixel;
        shift = Math.max(first - min, Math.min(last - max, shift)); // not past the data
        u.setScale("x", { min: min + shift, max: max + shift });
      };
      const up = () => {
        u.over.style.cursor = "";
        document.removeEventListener("mousemove", move);
        document.removeEventListener("mouseup", up);
      };
      document.addEventListener("mousemove", move);
      document.addEventListener("mouseup", up);
      return null;
    };
  }
  const syncKey = `osm-results-${Math.random().toString(36).slice(2)}`;

  // ____________________ selection ____________________

  function selection() {
    return model.get("selection") || [];
  }

  function selected(component, variable) {
    return selection().find((s) => s.component === component && s.variable === variable);
  }

  function toggle(component, variable) {
    const current = selection();
    const existing = selected(component, variable);
    let next;
    if (existing) {
      next = current.filter((s) => s !== existing);
    } else {
      if (current.length >= MAX_SERIES) return;
      const used = new Set(current.map((s) => s.slot));
      const slot = PALETTE.findIndex((_, i) => !used.has(i));
      next = [...current, { component, variable, slot }];
    }
    model.set("selection", next);
    model.save_changes();
  }

  // ____________________ tree ____________________

  function renderTree() {
    tree.textContent = "";
    const filter = search.value.trim().toLowerCase();
    const full = selection().length >= MAX_SERIES;
    const groups = new Map();
    for (const component of model.get("catalog") || []) {
      if (!groups.has(component.type)) groups.set(component.type, []);
      groups.get(component.type).push(component);
    }
    for (const [type, components] of groups) {
      const typeOpen = filter !== "" || expanded.has(type);
      const groupRow = h("div", { class: "osm-r-group", text: `${typeOpen ? "▾" : "▸"} ${type}` });
      groupRow.addEventListener("click", () => {
        expanded.has(type) ? expanded.delete(type) : expanded.add(type);
        renderTree();
      });
      const rows = [];
      for (const component of components) {
        const key = `${type}/${component.name}`;
        const variables = component.variables.filter(
          (v) => filter === "" || `${component.name}.${v.name}`.toLowerCase().includes(filter),
        );
        if (variables.length === 0) continue;
        const hasSelected = component.variables.some((v) => selected(component.name, v.name));
        const open = filter !== "" || expanded.has(key);
        const componentRow = h("div", {
          class: "osm-r-component",
          text: `${open ? "▾" : "▸"} ${component.name}${hasSelected ? " ●" : ""}`,
        });
        componentRow.addEventListener("click", () => {
          expanded.has(key) ? expanded.delete(key) : expanded.add(key);
          renderTree();
        });
        rows.push(componentRow);
        if (!open) continue;
        for (const variable of variables) {
          const item = selected(component.name, variable.name);
          const keyLine = h("span", { class: "osm-r-key" });
          if (item) keyLine.style.background = PALETTE[item.slot];
          const row = h("div", { class: "osm-r-variable" }, [
            keyLine,
            h("span", { text: variable.name }),
            h("span", { class: "osm-r-unit", text: variable.unit }),
          ]);
          if (item) row.classList.add("selected");
          if (!item && full) {
            row.classList.add("disabled");
            row.title = `At most ${MAX_SERIES} variables at the same time`;
          } else {
            row.addEventListener("click", () => toggle(component.name, variable.name));
          }
          rows.push(row);
        }
      }
      if (rows.length === 0) continue;
      tree.appendChild(groupRow);
      if (typeOpen) for (const row of rows) tree.appendChild(row);
    }
  }

  // ____________________ charts ____________________

  function destroyCharts() {
    for (const chart of charts) chart.destroy();
    charts = [];
  }

  function seriesLabel(s) {
    return `${s.component}.${s.variable}`;
  }

  function chartWidth() {
    return Math.max(200, content.clientWidth - 20);
  }

  function renderCharts(series) {
    const freq = model.get("frequency");
    // One chart per unit: never two scales on one chart
    const byUnit = new Map();
    for (const s of series) {
      const unit = s.unit || "–";
      if (!byUnit.has(unit)) byUnit.set(unit, []);
      byUnit.get(unit).push(s);
    }
    for (const [unit, group] of byUnit) {
      const box = h("div", { class: "osm-r-chart" }, [h("div", { class: "osm-r-chart-title", text: unit })]);
      content.appendChild(box);
      const data = [group[0].x, ...group.map((s) => s.y)];
      const points = group[0].x.length;
      const opts = {
        width: chartWidth(),
        height: model.get("chart_height"),
        tzDate: (ts) => uPlot.tzDate(utc(ts), "Etc/UTC"),
        // focus: the series nearest to the cursor is highlighted, the others dimmed
        cursor: {
          sync: { key: syncKey },
          drag: { x: true, y: false },
          focus: { prox: 16 },
          bind: { mousedown: panHandler },
        },
        hooks: { setScale: [(u, key) => key === "x" && shareTimeRange(u)] },
        focus: { alpha: 0.3 },
        legend: { live: true },
        scales: { x: { time: true } },
        axes: [
          {
            stroke: "#57606a",
            grid: { stroke: "#eaeef2", width: 1 },
            ticks: { stroke: "#d0d7de", width: 1 },
            values: (u, splits, axis, space, incr) => splits.map((v) => timeTick(v, incr)),
          },
          {
            stroke: "#57606a",
            grid: { stroke: "#eaeef2", width: 1 },
            ticks: { stroke: "#d0d7de", width: 1 },
            // wide enough for the longest label of the axis
            size: (u, values) => 18 + 7 * Math.max(4, ...(values || []).map((v) => String(v).length)),
            values: (u, splits) => splits.map(formatValue),
          },
        ],
        series: [
          { label: "Date", value: (u, v) => (v === null ? "–" : formatDate(v, freq)) },
          ...group.map((s) => ({
            label: seriesLabel(s),
            stroke: PALETTE[s.slot],
            width: 2,
            // markers only when there are few points, so they can be hovered
            points: { show: points <= 60, size: 8 },
            value: (u, v) => formatValue(v),
            spanGaps: false,
          })),
        ],
      };
      const chart = new uPlot(opts, data, box);
      // the zoom of the charts already drawn, when one more variable is added
      if (timeRange) chart.setScale("x", { min: timeRange[0], max: timeRange[1] });
      charts.push(chart);
    }
  }

  // ____________________ table ____________________

  function tableRows(series) {
    const x = series[0].x;
    return x.map((t, i) => [t, ...series.map((s) => s.y[i])]);
  }

  function renderTable(series) {
    const freq = model.get("frequency");
    const rows = tableRows(series);
    const head = h("tr", {}, [
      h("th", { text: "Date" }),
      ...series.map((s) => h("th", { text: `${seriesLabel(s)}${s.unit ? ` [${s.unit}]` : ""}` })),
    ]);
    const body = h("tbody");
    for (const row of rows.slice(0, MAX_TABLE_ROWS)) {
      body.appendChild(
        h("tr", {}, row.map((v, i) => h("td", { text: i === 0 ? formatDate(v, freq) : formatValue(v) }))),
      );
    }
    content.appendChild(h("table", { class: "osm-r-table" }, [h("thead", {}, [head]), body]));
    if (rows.length > MAX_TABLE_ROWS) {
      content.appendChild(
        h("div", {
          class: "osm-r-note",
          text: `First ${MAX_TABLE_ROWS} of ${rows.length} rows. Use a coarser frequency, a shorter interval, or the CSV export.`,
        }),
      );
    }
  }

  function downloadCsv() {
    const series = model.get("series") || [];
    if (series.length === 0) return;
    const freq = model.get("frequency");
    const header = ["date", ...series.map((s) => `${seriesLabel(s)}${s.unit ? ` [${s.unit}]` : ""}`)];
    const lines = [header.map((c) => `"${c}"`).join(",")];
    for (const row of tableRows(series)) {
      const d = utc(row[0]);
      const date = `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`;
      lines.push([freq === "none" || freq === "hourly" ? date : date.slice(0, 10), ...row.slice(1).map((v) => (v === null ? "" : v))].join(","));
    }
    const blob = new Blob([lines.join("\n")], { type: "text/csv" });
    const link = h("a", { href: URL.createObjectURL(blob), download: "opensimula_results.csv" });
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  }

  // ____________________ main panel ____________________

  function renderContent() {
    destroyCharts();
    content.textContent = "";
    const series = model.get("series") || [];
    const message = model.get("message");
    csvButton.disabled = series.length === 0;
    viewButton.disabled = series.length === 0;
    clearButton.disabled = selection().length === 0;
    viewButton.textContent = showTable ? "Chart" : "Table";
    if (message) {
      content.appendChild(h("div", { class: "osm-r-message", text: message }));
      return;
    }
    if (series.length === 0) {
      content.appendChild(
        h("div", { class: "osm-r-message", text: "Select variables on the left to plot them." }),
      );
      return;
    }
    if (series[0].x.length === 0) {
      content.appendChild(h("div", { class: "osm-r-message", text: "No values in this interval." }));
      return;
    }
    showTable ? renderTable(series) : renderCharts(series);
  }

  function renderToolbar() {
    frequency.value = model.get("frequency");
    // the heights offered, plus the current one if it was set from Python to another value
    const heights = [...new Set([...CHART_HEIGHTS, model.get("chart_height")])].sort((a, b) => a - b);
    chartHeight.textContent = "";
    for (const value of heights) chartHeight.appendChild(h("option", { value, text: `${value} px` }));
    chartHeight.value = model.get("chart_height");
    aggregation.value = model.get("aggregation");
    aggregation.disabled = model.get("frequency") === "none";
    const period = model.get("period") || [];
    const interval = model.get("interval") || [];
    for (const input of [from, to]) {
      input.min = isoDay(period[0]);
      input.max = isoDay(period[1]);
    }
    from.value = interval.length === 2 ? interval[0] : isoDay(period[0]);
    to.value = interval.length === 2 ? interval[1] : isoDay(period[1]);
  }

  function setInterval_() {
    const period = model.get("period") || [];
    let start = from.value || isoDay(period[0]);
    let end = to.value || isoDay(period[1]);
    if (start > end) [start, end] = [end, start];
    const whole = start === isoDay(period[0]) && end === isoDay(period[1]);
    model.set("interval", whole ? [] : [start, end]);
    model.save_changes();
  }

  frequency.addEventListener("change", () => {
    model.set("frequency", frequency.value);
    model.save_changes();
  });
  aggregation.addEventListener("change", () => {
    model.set("aggregation", aggregation.value);
    model.save_changes();
  });
  chartHeight.addEventListener("change", () => {
    model.set("chart_height", Number(chartHeight.value));
    model.save_changes();
  });
  from.addEventListener("change", setInterval_);
  to.addEventListener("change", setInterval_);
  viewButton.addEventListener("click", () => {
    showTable = !showTable;
    renderContent();
  });
  csvButton.addEventListener("click", downloadCsv);
  clearButton.addEventListener("click", () => {
    model.set("selection", []);
    model.save_changes();
  });
  search.addEventListener("input", renderTree);

  model.on("change:catalog", renderTree);
  model.on("change:selection", () => {
    renderTree();
    renderContent();
  });
  // a new frequency or interval changes the data: start again from all of it
  model.on("change:frequency", () => (timeRange = null));
  model.on("change:interval", () => (timeRange = null));
  model.on("change:series", renderContent);
  model.on("change:message", renderContent);
  model.on("change:frequency", renderToolbar);
  model.on("change:aggregation", renderToolbar);
  model.on("change:interval", renderToolbar);
  model.on("change:period", renderToolbar);
  model.on("change:chart_height", () => {
    renderToolbar();
    renderContent();
  });
  model.on("change:height", () => {
    root.style.height = `${model.get("height")}px`;
  });

  const resize = new ResizeObserver(() => {
    for (const chart of charts) chart.setSize({ width: chartWidth(), height: model.get("chart_height") });
  });
  resize.observe(content);

  renderTree();
  renderToolbar();
  renderContent();

  return () => {
    resize.disconnect();
    destroyCharts();
  };
}

export default { render };
