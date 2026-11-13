// Graph view of the components of a project, for the editor: one box per
// component with the parameters that refer to other components, and an arrow
// from each of those parameters to the component it names. Plain SVG, no
// library. Bundled into static/editor.js by esbuild (npm run build).

const SVG = "http://www.w3.org/2000/svg";

// Box geometry, in SVG units (pixels at zoom 1)
const BOX_WIDTH = 200;
const HEADER = 36;
const ROW = 18;
const FOOTER = 20;
const COLUMN_GAP = 90;
const ROW_GAP = 16;
const MARGIN = 24;
const ROW_CHARS = 30; // characters that fit in a row of a box

// Zoom below which the text of the boxes is too small to read
const MIN_FIT = 0.8;

// A type with more components than this is drawn as one box until expanded
const GROUP_ABOVE = 6;

// Colour of the band of each box, by family of components: fixed order of
// the categorical palette of the results viewer.
const FAMILIES = [
  ["data", "Weather and data", "#2a78d6", ["File_met", "File_data"]],
  ["schedule", "Schedules", "#eda100", ["Day_schedule", "Week_schedule", "Year_schedule"]],
  ["construction", "Constructions", "#1baf7a", ["Material", "Glazing", "Frame", "Construction", "Opening_type"]],
  ["building", "Building", "#eb6834", ["Building", "Space_type", "Space", "Building_surface", "Solar_surface", "Opening", "Surface"]],
  ["hvac", "HVAC", "#6250d6", []], // any type starting with HVAC_, and the equipment
  ["other", "Other", "#8c959f", []],
];
const EQUIPMENT = ["DX_unit", "Water_coil", "Fan", "Pump", "Chiller_heat_pump"];

export function familyOf(type) {
  for (const [key, , , types] of FAMILIES) if (types.includes(type)) return key;
  if (type.startsWith("HVAC_") || EQUIPMENT.includes(type)) return "hvac";
  return "other";
}

export const familyLegend = () => FAMILIES.map(([key, label, colour]) => ({ key, label, colour }));
const familyColour = (type) => FAMILIES.find(([key]) => key === familyOf(type))[2];

const isRefList = (sch) => sch?.["x-list"] === true;
const refSchema = (sch) => (isRefList(sch) ? sch.anyOf[1] : sch);

function short(text, room = ROW_CHARS - 2) {
  const s = String(text);
  return s.length > room ? `${s.slice(0, Math.max(4, room - 1))}…` : s;
}

// ____________________ model ____________________

// Nodes and edges of the document: every reference parameter whose value names
// a component of the document becomes an edge (references to another project,
// "project->name", and dangling names are left out: the form reports them).
export function buildGraph(components, defs) {
  const byName = new Map(components.map((c, index) => [c.name, { comp: c, index }]));
  const nodes = [];
  const edges = [];
  components.forEach((comp, index) => {
    const def = defs[comp.type] || { properties: {} };
    const refs = [];
    let modified = 0;
    let total = 0;
    for (const [key, sch] of Object.entries(def.properties || {})) {
      if (key === "type" || key === "name") continue;
      const item = refSchema(sch);
      if (item && item["x-ref"]) {
        const raw = comp[key];
        const values = (Array.isArray(raw) ? raw : raw === undefined ? [] : [raw]).map(String);
        const targets = values.filter((v) => byName.has(v) && v !== comp.name);
        if (values.length === 0 || values.every((v) => v === "not_defined" || v === "")) continue;
        refs.push({ key, values, targets });
        for (const target of targets) edges.push({ from: comp.name, key, to: target });
      } else {
        total += 1;
        if (comp[key] !== undefined && JSON.stringify(comp[key]) !== JSON.stringify(sch.default)) modified += 1;
      }
    }
    nodes.push({ id: comp.name, name: comp.name, type: comp.type, index, refs, modified, total });
  });
  return { nodes, edges };
}

// What a component uses, all the way down, and what uses it directly: the
// part of the graph that matters when looking at one component.
export function neighbourhood(graph, name) {
  const keep = new Set([name]);
  const uses = new Map();
  for (const e of graph.edges) {
    if (!uses.has(e.from)) uses.set(e.from, []);
    uses.get(e.from).push(e.to);
  }
  const stack = [name];
  while (stack.length) {
    for (const next of uses.get(stack.pop()) || []) {
      if (!keep.has(next)) {
        keep.add(next);
        stack.push(next);
      }
    }
  }
  for (const e of graph.edges) if (e.to === name) keep.add(e.from);
  return keep;
}

// The graph without the components of the families switched off in the
// legend, and their arrows; the selected component is always kept
function withoutFamilies(graph, hidden, pinned) {
  if (!hidden || hidden.size === 0) return graph;
  const shown = (n) => n.id === pinned || !hidden.has(familyOf(n.type));
  const nodes = graph.nodes.filter(shown);
  const ids = new Set(nodes.map((n) => n.id));
  return { nodes, edges: graph.edges.filter((e) => ids.has(e.from) && ids.has(e.to)) };
}

// Types with many components folded into one box each, unless expanded
function fold(graph, expanded, pinned) {
  const count = new Map();
  for (const n of graph.nodes) count.set(n.type, (count.get(n.type) || 0) + 1);
  const folded = (n) => count.get(n.type) > GROUP_ABOVE && !expanded.has(n.type) && n.id !== pinned;
  const nodeOf = new Map();
  const nodes = [];
  const groups = new Map();
  for (const n of graph.nodes) {
    if (!folded(n)) {
      nodes.push(n);
      nodeOf.set(n.id, n.id);
      continue;
    }
    const id = `group:${n.type}`;
    nodeOf.set(n.id, id);
    if (!groups.has(id)) {
      const group = { id, group: true, name: `${count.get(n.type)} × ${n.type}`, type: n.type, refs: [], members: 0 };
      groups.set(id, group);
      nodes.push(group);
    }
    groups.get(id).members += 1;
  }
  // a group shows the union of the reference parameters of its members
  for (const n of graph.nodes) {
    const group = groups.get(nodeOf.get(n.id));
    if (!group) continue;
    for (const r of n.refs) if (!group.refs.some((g) => g.key === r.key)) group.refs.push({ key: r.key, values: [], targets: [] });
  }
  const seen = new Set();
  const edges = [];
  for (const e of graph.edges) {
    const from = nodeOf.get(e.from);
    const to = nodeOf.get(e.to);
    if (from === to) continue;
    const key = `${from}|${e.key}|${to}`;
    if (seen.has(key)) continue;
    seen.add(key);
    edges.push({ from, key: e.key, to });
  }
  return { nodes, edges };
}

// ____________________ layout ____________________

// Layered: a component is drawn to the right of everything it refers to, so
// the materials and schedules end up on the left and the systems on the right.
// Within a column, the boxes are ordered by the mean position of their
// neighbours (a few sweeps of the barycentre heuristic) to uncross the arrows.
function layout(graph) {
  const uses = new Map(graph.nodes.map((n) => [n.id, []]));
  const usedBy = new Map(graph.nodes.map((n) => [n.id, []]));
  for (const e of graph.edges) {
    uses.get(e.from)?.push(e.to);
    usedBy.get(e.to)?.push(e.from);
  }
  const depth = new Map();
  const visiting = new Set();
  const depthOf = (id) => {
    if (depth.has(id)) return depth.get(id);
    if (visiting.has(id)) return 0; // a cycle: cut it here
    visiting.add(id);
    const d = Math.max(-1, ...uses.get(id).map(depthOf)) + 1;
    visiting.delete(id);
    depth.set(id, d);
    return d;
  };
  graph.nodes.forEach((n) => depthOf(n.id));

  const columns = [];
  for (const n of graph.nodes) {
    const d = depth.get(n.id);
    (columns[d] ||= []).push(n);
  }
  for (const column of columns) {
    column.sort((a, b) => familyOf(a.type).localeCompare(familyOf(b.type)) || a.type.localeCompare(b.type) || a.name.localeCompare(b.name));
  }
  const position = new Map();
  const index = () => columns.forEach((column) => column.forEach((n, i) => position.set(n.id, i)));
  index();
  const barycentre = (column, neighbours) => {
    const value = new Map();
    for (const n of column) {
      const near = neighbours.get(n.id).filter((id) => position.has(id));
      value.set(n.id, near.length ? near.reduce((s, id) => s + position.get(id), 0) / near.length : position.get(n.id));
    }
    column.sort((a, b) => value.get(a.id) - value.get(b.id));
  };
  for (let sweep = 0; sweep < 4; sweep += 1) {
    for (let c = 1; c < columns.length; c += 1) if (columns[c]) barycentre(columns[c], uses);
    index();
    for (let c = columns.length - 2; c >= 0; c -= 1) if (columns[c]) barycentre(columns[c], usedBy);
    index();
  }

  const boxes = new Map();
  let width = 0;
  let height = 0;
  columns.forEach((column, c) => {
    if (!column) return;
    let y = MARGIN;
    const x = MARGIN + c * (BOX_WIDTH + COLUMN_GAP);
    for (const n of column) {
      const h = HEADER + n.refs.length * ROW + FOOTER;
      boxes.set(n.id, { x, y, w: BOX_WIDTH, h, node: n });
      y += h + ROW_GAP;
    }
    width = Math.max(width, x + BOX_WIDTH + MARGIN);
    height = Math.max(height, y + MARGIN - ROW_GAP);
  });
  return { boxes, width, height };
}

// ____________________ view ____________________

function el(tag, attrs = {}, text) {
  const node = document.createElementNS(SVG, tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  if (text !== undefined) node.textContent = text;
  return node;
}

// The graph panel. onSelect(index) is called with the index of the component
// clicked, or with null to clear the selection (a click on the empty
// background); update() redraws it from the document.
export function createGraphView(container, { onSelect }) {
  const svg = el("svg", { class: "osm-graph-svg" });
  const scene = el("g");
  const edgeLayer = el("g", { class: "osm-graph-edges" });
  const boxLayer = el("g");
  scene.append(edgeLayer, boxLayer);
  svg.appendChild(scene);
  container.appendChild(svg);

  let view = { x: 0, y: 0, k: 1 };
  // ids are global in the page: one per editor, or two editors share arrows
  const markerId = `osm-arrow-${Math.random().toString(36).slice(2)}`;
  let laid = null;
  let fitted = false;
  let state = { components: [], defs: {}, selected: null, focus: false, hidden: new Set() };
  const expanded = new Set();

  const apply = () => scene.setAttribute("transform", `translate(${view.x},${view.y}) scale(${view.k})`);

  function fit() {
    if (!laid) return;
    const { width, height } = container.getBoundingClientRect();
    if (!width || !height) return;
    // the whole graph if it fits at a readable size; if not, readable from the
    // top left corner, and the rest a drag away
    const k = Math.max(MIN_FIT, Math.min(1, width / laid.width, height / laid.height));
    const x = laid.width * k <= width ? (width - laid.width * k) / 2 : 0;
    const y = laid.height * k <= height ? (height - laid.height * k) / 2 : 0;
    view = { k, x, y };
    apply();
    fitted = true;
  }

  function zoom(factor, cx, cy) {
    const { width, height } = container.getBoundingClientRect();
    const [px, py] = [cx ?? width / 2, cy ?? height / 2];
    const k = Math.min(3, Math.max(0.1, view.k * factor));
    view = { k, x: px - ((px - view.x) * k) / view.k, y: py - ((py - view.y) * k) / view.k };
    apply();
  }

  // Bring a box into sight if it is out of the panel
  function reveal(id) {
    const box = laid && laid.boxes.get(id);
    if (!box) return;
    const { width, height } = container.getBoundingClientRect();
    const [left, top] = [view.x + box.x * view.k, view.y + box.y * view.k];
    const [right, bottom] = [left + box.w * view.k, top + box.h * view.k];
    if (left >= 0 && top >= 0 && right <= width && bottom <= height) return;
    view.x = width / 2 - (box.x + box.w / 2) * view.k;
    view.y = Math.min(height / 2, height - 20) - (box.y + Math.min(box.h, height / 2) / 2) * view.k;
    apply();
  }

  // ---- drawing ----

  function draw() {
    const full = withoutFamilies(buildGraph(state.components, state.defs), state.hidden, state.selected);
    let graph = full;
    let kept = null;
    if (state.focus && state.selected && full.nodes.some((n) => n.id === state.selected)) {
      kept = neighbourhood(full, state.selected);
      graph = {
        nodes: full.nodes.filter((n) => kept.has(n.id)),
        edges: full.edges.filter((e) => kept.has(e.from) && kept.has(e.to)),
      };
    } else {
      graph = fold(full, expanded, state.selected);
    }
    laid = layout(graph);

    // what is lit up: the selected box, its arrows and the boxes at their ends
    const lit = new Set();
    if (state.selected) {
      lit.add(state.selected);
      for (const e of graph.edges) {
        if (e.from === state.selected) lit.add(e.to);
        if (e.to === state.selected) lit.add(e.from);
      }
    }
    // filtered, everything left is related to the selection: nothing is dimmed
    const dim = (id) => !kept && state.selected && laid.boxes.has(state.selected) && !lit.has(id);

    edgeLayer.textContent = "";
    boxLayer.textContent = "";
    for (const e of graph.edges) {
      const from = laid.boxes.get(e.from);
      const to = laid.boxes.get(e.to);
      if (!from || !to) continue;
      const row = from.node.refs.findIndex((r) => r.key === e.key);
      const y1 = from.y + HEADER + (row + 0.5) * ROW;
      const x1 = from.x;
      const x2 = to.x + to.w;
      const y2 = to.y + HEADER / 2;
      const bend = Math.max(40, Math.abs(x1 - x2) / 2);
      const active = state.selected && (e.from === state.selected || e.to === state.selected);
      const cls = active ? "osm-graph-edge active" : dim(e.from) || dim(e.to) ? "osm-graph-edge dim" : "osm-graph-edge";
      edgeLayer.appendChild(
        el("path", {
          class: cls,
          d: `M${x1},${y1} C${x1 - bend},${y1} ${x2 + bend},${y2} ${x2},${y2}`,
          "marker-end": `url(#${active ? markerId + "-active" : markerId})`,
        }),
      );
    }
    for (const box of laid.boxes.values()) boxLayer.appendChild(drawBox(box, dim(box.node.id)));

    // arrow head, defined once per draw (cheap) so it follows the CSS colours
    const defs = el("defs");
    for (const [id, cls] of [[markerId, "osm-graph-arrow"], [`${markerId}-active`, "osm-graph-arrow active"]]) {
      const marker = el("marker", { id, viewBox: "0 0 8 8", refX: "7", refY: "4", markerWidth: "7", markerHeight: "7", orient: "auto" });
      marker.appendChild(el("path", { d: "M0,0 L8,4 L0,8 z", class: cls }));
      defs.appendChild(marker);
    }
    edgeLayer.prepend(defs);
    if (!fitted) fit();
  }

  function drawBox(box, dimmed) {
    const n = box.node;
    const classes = ["osm-graph-box"];
    if (n.group) classes.push("group");
    if (n.id === state.selected) classes.push("selected");
    if (dimmed) classes.push("dim");
    const g = el("g", { class: classes.join(" "), transform: `translate(${box.x},${box.y})` });
    g.appendChild(el("rect", { class: "osm-graph-frame", width: box.w, height: box.h, rx: 4 }));
    g.appendChild(el("rect", { class: "osm-graph-band", width: 4, height: box.h, rx: 2, fill: familyColour(n.type) }));
    g.appendChild(el("text", { class: "osm-graph-name", x: 12, y: 15 }, short(n.name)));
    g.appendChild(el("text", { class: "osm-graph-type", x: 12, y: 29 }, n.group ? "click to expand" : n.type));
    n.refs.forEach((r, i) => {
      const y = HEADER + i * ROW;
      g.appendChild(el("line", { class: "osm-graph-sep", x1: 8, x2: box.w, y1: y, y2: y }));
      const value = n.group ? "" : r.values.length > 1 ? `${r.values.length} items` : r.values[0];
      const text = el("text", { class: "osm-graph-row", x: 12, y: y + 13 });
      text.appendChild(el("tspan", { class: "osm-graph-key" }, r.key));
      // the value takes what the key leaves of the row
      if (value) text.appendChild(el("tspan", { dx: 6 }, short(value, ROW_CHARS - r.key.length - 1)));
      if (value && String(value).length > ROW_CHARS - r.key.length - 1) text.appendChild(el("title", {}, String(value)));
      g.appendChild(text);
      if (r.values.length > 1) text.appendChild(el("title", {}, r.values.join(", ")));
    });
    const foot = n.group
      ? `${n.members} components`
      : `${n.total} parameters${n.modified ? `, ${n.modified} changed` : ""}`;
    g.appendChild(el("text", { class: "osm-graph-foot", x: 12, y: box.h - 6 }, foot));
    g.appendChild(el("title", {}, n.group ? `${n.name}: click to show them one by one` : `${n.type}: ${n.name}`));
    g.addEventListener("click", (event) => {
      event.stopPropagation();
      if (moved) return;
      if (n.group) {
        expanded.add(n.type);
        draw();
      } else {
        onSelect(n.index);
      }
    });
    return g;
  }

  // ---- pan (drag) and zoom (buttons, Ctrl/⌘ + wheel, pinch) ----

  let drag = null;
  let moved = false;
  svg.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    drag = { x: event.clientX, y: event.clientY, vx: view.x, vy: view.y };
    moved = false;
  });
  const onMove = (event) => {
    if (!drag) return;
    const [dx, dy] = [event.clientX - drag.x, event.clientY - drag.y];
    if (!moved && Math.hypot(dx, dy) < 4) return;
    moved = true;
    svg.classList.add("dragging");
    view.x = drag.vx + dx;
    view.y = drag.vy + dy;
    apply();
  };
  window.addEventListener("pointermove", onMove);
  const endDrag = () => {
    drag = null;
    svg.classList.remove("dragging");
    // the click that ends a drag must not select the box under the pointer
    setTimeout(() => (moved = false), 0);
  };
  window.addEventListener("pointerup", endDrag);
  // a click on the background (not the end of a drag) clears the selection
  svg.addEventListener("click", () => {
    if (!moved && state.selected) onSelect(null);
  });
  // the plain wheel is left to the page, as in the charts of the results viewer
  svg.addEventListener(
    "wheel",
    (event) => {
      if (!event.ctrlKey && !event.metaKey) return;
      event.preventDefault();
      const r = svg.getBoundingClientRect();
      zoom(Math.exp(-event.deltaY * 0.002), event.clientX - r.left, event.clientY - r.top);
    },
    { passive: false },
  );

  return {
    update(next) {
      const before = state;
      state = { ...state, ...next };
      // a new set of boxes (filter on or off) is fitted again
      if (before.focus !== state.focus || (state.focus && before.selected !== state.selected)) fitted = false;
      if ([...before.hidden].sort().join() !== [...state.hidden].sort().join()) fitted = false;
      draw();
      if (state.selected) reveal(state.selected);
    },
    fit() {
      fit();
    },
    zoom,
    collapseAll() {
      expanded.clear();
      fitted = false;
      draw();
    },
    destroy() {
      window.removeEventListener("pointerup", endDrag);
      window.removeEventListener("pointermove", onMove);
    },
  };
}
