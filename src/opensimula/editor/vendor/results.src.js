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
import {
  VIEW_LAYOUT,
  axisRanges,
  column,
  defaultCamera,
  modelBounds,
  plotlyLoaded,
  receivePlotly,
} from "./view3d.js";

// Categorical palette, fixed order: a series keeps its slot (colour) while it
// stays selected, whatever else is added or removed.
const PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"];
const MAX_SERIES = PALETTE.length;
const MAX_TABLE_ROWS = 2000;
const CHART_HEIGHTS = [200, 300, 400, 500];
const VIEW_HEIGHT = 340; // the 3D view, added to the height of the widget
const INK = "#1f2328"; // outline of the surface clicked in the 3D view
// Colour of the surfaces by a variable: one hue when the values have one sign,
// two hues around a neutral grey at zero when they have both (heat flows).
const SEQUENTIAL = [[0, "#eef4fc"], [0.5, "#5b9be6"], [1, "#0b3d7a"]];
const DIVERGING = [[0, "#1d5fb0"], [0.5, "#e5e5e5"], [1, "#c0392b"]];
const NO_VALUE = "rgb(200, 200, 200)";
const STATISTICS = [
  ["mean", "Mean"],
  ["max", "Maximum"],
  ["min", "Minimum"],
];

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
  if (value === 0) return "0"; // also -0, which toLocaleString() writes "-0"
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
  const view3dButton = h("button", { type: "button", text: "3D", title: "Show the geometry of the project" });
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
    view3dButton,
    viewButton,
    csvButton,
    clearButton,
  ]);
  const content = h("div", { class: "osm-r-content" });
  const plot = h("div", { class: "osm-r-plot" });
  const colorVariable = h("select");
  const colorStatistic = h("select");
  for (const [value, label] of STATISTICS) colorStatistic.appendChild(h("option", { value, text: label }));
  const viewBar = h("div", { class: "osm-r-view-bar" }, [
    h("label", { text: "Colour" }, [colorVariable]),
    colorStatistic,
  ]);
  const view = h("div", { class: "osm-r-view" }, [plot, viewBar]);
  view.style.height = `${VIEW_HEIGHT}px`;
  view.hidden = true;
  const main = h("div", { class: "osm-r-main" }, [toolbar, view, content]);
  const root = h("div", { class: "osm-results" }, [list, main]);
  el.appendChild(root);

  function setHeight() {
    root.style.height = `${model.get("height") + (model.get("show_3d") ? VIEW_HEIGHT : 0)}px`;
  }
  setHeight();

  let showTable = false;
  const expanded = new Set(); // "type" and "type/component" rows that are open
  let charts = [];
  let timeRange = null; // [min, max] shown, kept when the charts are drawn again
  let focused = null; // component clicked in the 3D view, or opened in the list

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

  // Removes variables from the selection, from the charts themselves
  function remove(items) {
    const gone = new Set(items.map((s) => `${s.component}.${s.variable}`));
    model.set("selection", selection().filter((s) => !gone.has(`${s.component}.${s.variable}`)));
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
          class: component.name === focused ? "osm-r-component focused" : "osm-r-component",
          text: `${open ? "▾" : "▸"} ${component.name}${hasSelected ? " ●" : ""}`,
        });
        componentRow.dataset.component = component.name;
        componentRow.addEventListener("click", () => {
          expanded.has(key) ? expanded.delete(key) : expanded.add(key);
          // the component is also picked out in the 3D view, if it is drawn there
          if (expanded.has(key) && hasMesh(component.name)) focused = component.name;
          renderTree();
          renderView();
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
      const close = h("button", {
        type: "button",
        class: "osm-r-close",
        text: "×",
        title: group.length > 1 ? `Remove the ${group.length} variables of this chart` : "Remove this variable",
        "aria-label": "Close chart",
      });
      close.addEventListener("click", () => remove(group));
      const head = h("div", { class: "osm-r-chart-head" }, [h("div", { class: "osm-r-chart-title", text: unit }), close]);
      const box = h("div", { class: "osm-r-chart" }, [head]);
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
      // Legend: click hides or shows a variable (uPlot), Shift+click removes it.
      // Caught on the way down, before uPlot's own click on the row.
      const legend = chart.root.querySelector(".u-legend");
      if (legend) {
        const rows = [...legend.querySelectorAll(".u-series")];
        rows.forEach((row, i) => {
          if (i > 0) row.title = "Click: hide or show · Shift+click: remove";
        });
        legend.addEventListener(
          "click",
          (event) => {
            if (!event.shiftKey) return;
            const i = rows.indexOf(event.target.closest(".u-series"));
            if (i < 1) return;
            event.stopPropagation();
            event.preventDefault();
            remove([group[i - 1]]);
          },
          true,
        );
      }
    }
  }


  // ____________________ 3D view ____________________

  // Where the user has turned the model to: react() puts back the camera of
  // the layout, so it is captured on real input and handed back on every
  // redraw (the same as the 3D view of the editor).
  let viewCamera = null;
  let viewInfos = [];
  let viewBound = false;
  let wheelTimer = null;

  function geometry() {
    return model.get("geometry") || {};
  }

  function hasMesh(name) {
    return (geometry().meshes || []).some((mesh) => mesh.component === name);
  }

  // Lowest slot (first colour) of the variables of each component plotted
  function componentSlots() {
    const slots = new Map();
    for (const s of selection()) {
      if (!slots.has(s.component) || s.slot < slots.get(s.component)) slots.set(s.component, s.slot);
    }
    return slots;
  }

  // Variables of the components drawn in the 3D view, for the colour selector
  function fillColourOptions() {
    const drawn = new Set((geometry().meshes || []).map((m) => m.component));
    const names = new Map();
    for (const component of model.get("catalog") || []) {
      if (!drawn.has(component.name)) continue;
      for (const v of component.variables) names.set(v.name, v.unit);
    }
    const current = model.get("color_variable");
    colorVariable.textContent = "";
    colorVariable.appendChild(h("option", { value: "", text: "Series" }));
    for (const [name, unit] of [...names].sort((a, b) => a[0].localeCompare(b[0]))) {
      colorVariable.appendChild(h("option", { value: name, text: unit ? `${name} [${unit}]` : name }));
    }
    colorVariable.value = names.has(current) ? current : "";
    colorStatistic.value = model.get("color_statistic");
    colorStatistic.disabled = !colorVariable.value;
  }

  function viewMessage(text) {
    plot.textContent = text;
    plot.classList.add("osm-r-view-empty");
  }

  function requestView() {
    // the geometry and plotly are sent by Python only when first needed
    const needGeometry = Object.keys(geometry()).length === 0;
    if (needGeometry || !plotlyLoaded()) {
      viewMessage("Loading the 3D view…");
      model.send({ type: "load-3d", has_plotly: Boolean(plotlyLoaded()) });
    }
    renderView();
  }

  // The surface values sent by Python for the colour variable chosen, if any
  function colouring() {
    const sv = model.get("surface_values") || {};
    if (!model.get("color_variable") || sv.variable !== model.get("color_variable")) return null;
    const values = Object.values(sv.values || {});
    if (values.length === 0) return { ...sv, values: {} };
    let low = Math.min(...values);
    let high = Math.max(...values);
    let scale = SEQUENTIAL;
    if (low < 0 && high > 0) {
      const m = Math.max(-low, high);
      [low, high, scale] = [-m, m, DIVERGING];
    }
    if (high - low < 1e-9) [low, high] = [low - 1, high + 1];
    return { ...sv, low, high, scale };
  }

  function colourTrace(trace, mesh, colour, first) {
    const value = colour.values[mesh.component];
    const label = `${colour.variable} (${colour.statistic})`;
    if (value === undefined) {
      trace.color = NO_VALUE;
      trace.hovertemplate = `<b>${mesh.name}</b><br>${label}: no value<extra></extra>`;
      return false;
    }
    delete trace.color;
    trace.intensity = mesh.points.map(() => value);
    trace.cmin = colour.low;
    trace.cmax = colour.high;
    trace.colorscale = colour.scale;
    trace.showscale = first;
    if (first) {
      trace.colorbar = {
        title: { text: colour.unit, side: "top" },
        thickness: 12,
        len: 0.85,
        tickfont: { size: 10 },
      };
    }
    trace.hovertemplate = `<b>${mesh.name}</b><br>${label}: ${formatValue(value)} ${colour.unit}<extra></extra>`;
    return true;
  }

  function traces(meshes) {
    const slots = componentSlots();
    const colour = colouring();
    let scaleShown = false;
    const out = [];
    const infos = [];
    for (const mesh of meshes) {
      const own = slots.get(mesh.component);
      out.push({
        type: "mesh3d",
        x: column(mesh.points, 0),
        y: column(mesh.points, 1),
        z: column(mesh.points, 2),
        i: column(mesh.faces, 0),
        j: column(mesh.faces, 1),
        k: column(mesh.faces, 2),
        color: own === undefined ? mesh.color : PALETTE[own],
        opacity: mesh.opacity,
        name: mesh.name,
        hovertemplate: `<b>${mesh.name}</b><br>${mesh.component_type}<extra></extra>`,
        flatshading: true,
        lighting: { ambient: 0.85, diffuse: 0.5, specular: 0.05 },
      });
      if (colour && colourTrace(out[out.length - 1], mesh, colour, !scaleShown)) scaleShown = true;
      infos.push(mesh);
      const outline = mesh.outline || [];
      if (!outline.length) continue;
      // the outline tells the space: in the colour of its series if plotted
      const space = (mesh.spaces || []).map((name) => slots.get(name)).find((slot) => slot !== undefined);
      let line = { color: "black", width: 2 };
      if (space !== undefined && !colour) line = { color: PALETTE[space], width: 4 };
      if (mesh.component === focused) line = { color: INK, width: 7 };
      const closed = [...outline, outline[0]];
      out.push({
        type: "scatter3d",
        mode: "lines",
        x: column(closed, 0),
        y: column(closed, 1),
        z: column(closed, 2),
        line,
        hoverinfo: "skip",
        showlegend: false,
      });
      infos.push(null);
    }
    return { out, infos };
  }

  // The panel is wider and lower than the editor's: the default eye of the
  // editor leaves the building small in it.
  function closerCamera(bounds) {
    const { eye } = defaultCamera(bounds);
    return { eye: { x: 0.85 * eye.x, y: 0.85 * eye.y, z: 0.85 * eye.z } };
  }

  function readCamera() {
    const scene = plot._fullLayout && plot._fullLayout.scene;
    if (!scene) return null;
    const live = scene._scene && typeof scene._scene.getCamera === "function" ? scene._scene.getCamera() : scene.camera;
    return live && live.eye ? JSON.parse(JSON.stringify(live)) : null;
  }

  function rememberCamera() {
    const camera = readCamera();
    if (camera) viewCamera = camera;
  }

  // A surface clicked in the 3D view is opened in the list, with its spaces
  function reveal(name) {
    const catalog = model.get("catalog") || [];
    const mesh = (geometry().meshes || []).find((m) => m.component === name);
    focused = name;
    search.value = "";
    for (const target of [name, ...(mesh ? mesh.spaces : [])]) {
      const component = catalog.find((c) => c.name === target);
      if (!component) continue;
      expanded.add(component.type);
      expanded.add(`${component.type}/${component.name}`);
    }
    renderTree();
    const row = [...tree.querySelectorAll(".osm-r-component")].find((r) => r.dataset.component === name);
    // scrolled inside the list only: scrollIntoView() would also move the page
    if (row) tree.scrollTop += row.getBoundingClientRect().top - tree.getBoundingClientRect().top;
    renderView();
  }

  async function renderView() {
    if (view.hidden) return;
    const geo = geometry();
    const plotly = plotlyLoaded();
    if (!plotly || Object.keys(geo).length === 0) return; // still loading
    if ((geo.meshes || []).length === 0) {
      viewMessage("This project has no geometry to show.");
      return;
    }
    try {
      const Plotly = await plotly;
      if (view.hidden) return;
      if (plot.classList.contains("osm-r-view-empty")) {
        plot.textContent = ""; // the "Loading" text, before plotly draws here
        plot.classList.remove("osm-r-view-empty");
      }
      const { out, infos } = traces(geo.meshes);
      viewInfos = infos;
      const layout = { ...VIEW_LAYOUT, scene: { ...VIEW_LAYOUT.scene } };
      const bounds = modelBounds(geo);
      if (bounds) {
        const [x, y, z] = axisRanges(bounds);
        layout.scene.xaxis = { ...layout.scene.xaxis, range: x };
        layout.scene.yaxis = { ...layout.scene.yaxis, range: y };
        layout.scene.zaxis = { ...layout.scene.zaxis, range: z };
        layout.scene.camera = viewCamera || closerCamera(bounds);
        viewCamera = layout.scene.camera;
      }
      await Plotly.react(plot, out, layout, { responsive: true, displaylogo: false });
      if (viewCamera) await Plotly.relayout(plot, { "scene.camera": viewCamera });
      if (!viewBound) {
        plot.addEventListener("mouseup", rememberCamera);
        plot.addEventListener("pointerup", rememberCamera);
        plot.addEventListener(
          "wheel",
          () => {
            clearTimeout(wheelTimer);
            wheelTimer = setTimeout(rememberCamera, 200);
          },
          { passive: true },
        );
        plot.on("plotly_click", (event) => {
          const point = event.points && event.points[0];
          const mesh = point && viewInfos[point.curveNumber];
          if (!mesh) return;
          // Out of plotly's own dispatch: redrawing from inside it tears the
          // WebGL scene down while it is in use. A click also arrives once per
          // trace under the pointer; only the first does anything.
          setTimeout(() => {
            if (focused !== mesh.component) reveal(mesh.component);
          }, 0);
        });
        viewBound = true;
      }
    } catch (err) {
      viewMessage(`Could not load the 3D view: ${err.message || err}`);
    }
  }

  function updateView() {
    const show = Boolean(model.get("show_3d"));
    view.hidden = !show;
    view3dButton.classList.toggle("active", show);
    view3dButton.title = show ? "Hide the 3D view" : "Show the geometry of the project";
    setHeight();
    if (show) requestView();
  }

  // model.set() fires change:show_3d, which updates the view
  view3dButton.addEventListener("click", () => {
    model.set("show_3d", !model.get("show_3d"));
    model.save_changes();
  });

  model.on("msg:custom", (msg, buffers) => {
    if (msg && msg.type === "plotly" && buffers && buffers.length) {
      receivePlotly(buffers[0]).then(renderView, (err) => viewMessage(`Could not load the 3D view: ${err.message || err}`));
    }
  });
  model.on("change:geometry", () => {
    fillColourOptions();
    renderView();
  });
  model.on("change:surface_values", renderView);
  model.on("change:color_statistic", fillColourOptions);
  model.on("change:color_variable", () => {
    fillColourOptions();
    renderView(); // back to the series colours at once, without waiting for Python
  });
  colorVariable.addEventListener("change", () => {
    model.set("color_variable", colorVariable.value);
    model.save_changes();
  });
  colorStatistic.addEventListener("change", () => {
    model.set("color_statistic", colorStatistic.value);
    model.save_changes();
  });
  model.on("change:show_3d", updateView);

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

  model.on("change:catalog", () => {
    renderTree();
    fillColourOptions();
  });
  model.on("change:selection", () => {
    renderTree();
    renderContent();
    renderView(); // the colours of the surfaces plotted
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
  model.on("change:height", setHeight);

  const resize = new ResizeObserver(() => {
    for (const chart of charts) chart.setSize({ width: chartWidth(), height: model.get("chart_height") });
  });
  resize.observe(content);
  const resizeView = new ResizeObserver(() => {
    const plotly = plotlyLoaded();
    if (!view.hidden && plotly && viewBound) plotly.then((P) => P.Plots.resize(plot)).catch(() => {});
  });
  resizeView.observe(view);

  renderTree();
  renderToolbar();
  renderContent();
  fillColourOptions();
  updateView();

  return () => {
    resize.disconnect();
    resizeView.disconnect();
    clearTimeout(wheelTimer);
    destroyCharts();
    const plotly = plotlyLoaded();
    if (plotly && viewBound) plotly.then((P) => P.purge(plot)).catch(() => {});
  };
}

export default { render };
