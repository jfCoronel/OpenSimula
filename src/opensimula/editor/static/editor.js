import Ajv2020 from "https://esm.sh/ajv@8.17.1/dist/2020";

// How long to wait after the last keystroke before pushing the document to the
// kernel. Syncing on every keystroke would round-trip a whole building on each
// character.
const DEBOUNCE_MS = 400;

// ____________________ schema helpers ____________________

// A list parameter is {anyOf: [{type: array, items: ITEM}, ITEM], x-list: true}
// because every *_list setter also accepts a bare scalar.
const isList = (sch) => sch?.["x-list"] === true;
const itemSchema = (sch) => (isList(sch) ? sch.anyOf[1] : sch);

function fieldKind(sch) {
  const item = itemSchema(sch);
  if (item["x-ref"]) return "ref";
  if (item.enum) return "enum";
  if (item.type === "boolean") return "boolean";
  if (item.type === "integer") return "integer";
  if (item.type === "number") return "number";
  if (item["x-format"] === "math-exp") return "math";
  return "string";
}

// A number needs room for a number, not for a sentence: keeping the numeric
// fields short is what leaves the unit on the same line as the value.
function widthClass(kind, sch) {
  // A checkbox has to keep its own size: giving it a width centres the box
  // inside it instead of putting it where the other fields start.
  if (kind === "boolean" && !isList(sch)) return "osm-w-auto";
  if (isList(sch)) return "osm-w-wide";
  if (kind === "integer" || kind === "number") return "osm-w-num";
  if (kind === "enum" || kind === "ref") return "osm-w-mid";
  return "osm-w-wide";
}

const sameValue = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// ____________________ 3D view ____________________

// The gl3d bundle only, 1.7MB against the 4.5MB of full plotly, and loaded on
// first use so opening the editor does not pay for a view that may stay shut.
const PLOTLY_URL = "https://esm.sh/plotly.js-gl3d-dist-min@3.7.0";
let plotlyPromise = null;

function loadPlotly() {
  if (!plotlyPromise) {
    plotlyPromise = import(PLOTLY_URL).then((module) => module.default || module);
  }
  return plotlyPromise;
}

// Same look as Project.show_3D(jupyter=True); see _plotly_scene_layout_().
const AXIS_STYLE = {
  showbackground: true,
  backgroundcolor: "rgb(220, 220, 220)",
  tickfont: { size: 9, color: "gray" },
  title: { font: { size: 10, color: "gray" } },
};

const VIEW_LAYOUT = {
  paper_bgcolor: "rgb(235, 235, 235)",
  scene: {
    xaxis: { title: { text: "X [m]" }, ...AXIS_STYLE },
    yaxis: { title: { text: "Y [m]" }, ...AXIS_STYLE },
    zaxis: { title: { text: "Z [m]" }, ...AXIS_STYLE },
    aspectmode: "data",
    bgcolor: "rgb(235, 235, 235)",
  },
  margin: { l: 0, r: 0, t: 0, b: 0 },
  showlegend: false,
};

const column = (rows, index) => rows.map((row) => row[index]);

// The selected component, so it can be picked out of a wall of white surfaces.
const HIGHLIGHT = "rgb(255, 127, 14)";

function modelBounds(geometry) {
  const low = [Infinity, Infinity, Infinity];
  const high = [-Infinity, -Infinity, -Infinity];
  for (const mesh of geometry.meshes || []) {
    for (const point of mesh.points) {
      for (let axis = 0; axis < 3; axis += 1) {
        if (point[axis] < low[axis]) low[axis] = point[axis];
        if (point[axis] > high[axis]) high[axis] = point[axis];
      }
    }
  }
  if (!Number.isFinite(low[0])) return null;
  return { low, high, size: high.map((value, axis) => Math.max(value - low[axis], 1e-6)) };
}

function axisRanges(bounds) {
  // Pinned to the whole model, not to what a filter leaves visible. Otherwise
  // aspectmode "data" rebuilds the scene box around one space, which blows it
  // up to fill the panel and leaves the camera pointing at the wrong place.
  // Held fixed, an isolated space stays where it belongs, at its real size.
  const margin = Math.max(...bounds.size) * 0.05;
  return [0, 1, 2].map((axis) => [
    bounds.low[axis] - margin,
    bounds.high[axis] + margin,
  ]);
}

function defaultCamera(bounds) {
  // With aspectmode "data" plotly stretches the scene box to the shape of the
  // model, normalised to unit volume, so a building wider than it is tall gets
  // a box bigger than the unit cube. Its default eye is placed for that cube
  // and ends up inside the building; the distance has to follow the box.
  const unit = Math.cbrt(bounds.size[0] * bounds.size[1] * bounds.size[2]);
  const reach = Math.max(...bounds.size.map((value) => value / unit));
  // Looking down from the south east, the usual angle to read a building from.
  // The distance was set by eye against the HULC model: closer than this and a
  // building of its proportions starts to touch the bottom of the panel.
  return { eye: { x: 1.1 * reach, y: -1.1 * reach, z: 0.76 * reach } };
}

// The colour of the building around the space being looked at.
const GHOST = "rgb(176, 176, 176)";

function splitMeshes(geometry, filters) {
  // The space filter does not drop the rest of the building, it pushes it back
  // as a wireframe: the space keeps its place in a recognisable model, and the
  // scene bounds stay the same, so filtering cannot move the camera.
  const active = [];
  const ghost = [];
  for (const mesh of geometry.meshes || []) {
    if (!filters.openings && mesh.component_type === "Opening") continue;
    const inSpace = !filters.space || mesh.spaces.includes(filters.space);
    (inSpace ? active : ghost).push(mesh);
  }
  return { active, ghost };
}

function faceNormal(points, faces) {
  const [a, b, c] = faces[0].map((index) => points[index]);
  const u = [b[0] - a[0], b[1] - a[1], b[2] - a[2]];
  const v = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
  const n = [
    u[1] * v[2] - u[2] * v[1],
    u[2] * v[0] - u[0] * v[2],
    u[0] * v[1] - u[1] * v[0],
  ];
  const length = Math.hypot(n[0], n[1], n[2]) || 1;
  return n.map((value) => value / length);
}

// Lifted off the surface it covers, or the two coplanar faces fight for depth
// and the highlight speckles.
const HIGHLIGHT_LIFT = 0.006;

function highlightGeometry(mesh) {
  if (!mesh) return { x: [], y: [], z: [], i: [], j: [], k: [] };
  const n = faceNormal(mesh.points, mesh.faces);
  // One sheet on each side. Lifting to one side only hides the highlight
  // behind the surface itself when looked at from the other: a floor is
  // normally seen from below, and the sheet was going on top of it.
  const shift = (sign) =>
    mesh.points.map((p) => [
      p[0] + sign * n[0] * HIGHLIGHT_LIFT,
      p[1] + sign * n[1] * HIGHLIGHT_LIFT,
      p[2] + sign * n[2] * HIGHLIGHT_LIFT,
    ]);
  const points = [...shift(1), ...shift(-1)];
  const behind = mesh.points.length;
  const faces = [
    ...mesh.faces,
    ...mesh.faces.map((face) => face.map((index) => index + behind)),
  ];
  return {
    x: column(points, 0),
    y: column(points, 1),
    z: column(points, 2),
    i: column(faces, 0),
    j: column(faces, 1),
    k: column(faces, 2),
  };
}

function ghostTrace(mesh) {
  const outline = mesh.outline || [];
  if (!outline.length) return null;
  const closed = [...outline, outline[0]];
  return {
    type: "scatter3d",
    mode: "lines",
    x: column(closed, 0),
    y: column(closed, 1),
    z: column(closed, 2),
    line: { color: GHOST, width: 1 },
    // What makes it scenery: no hover, and so no click either. Only the
    // surfaces of the filtered space answer the mouse.
    hoverinfo: "skip",
    showlegend: false,
  };
}

function geometryTraces(active, ghost, selected) {
  const traces = [];
  // What each trace is, so a click can say which component was hit and so the
  // highlight can be moved without rebuilding the scene.
  const infos = [];
  for (const mesh of active) {
    traces.push({
      type: "mesh3d",
      x: column(mesh.points, 0),
      y: column(mesh.points, 1),
      z: column(mesh.points, 2),
      i: column(mesh.faces, 0),
      j: column(mesh.faces, 1),
      k: column(mesh.faces, 2),
      color: mesh.color,
      opacity: mesh.opacity,
      name: mesh.name,
      hovertemplate: `<b>${mesh.name}</b><extra></extra>`,
      flatshading: true,
      lighting: { ambient: 0.85, diffuse: 0.5, specular: 0.05 },
    });
    infos.push({ kind: "mesh", owner: mesh.component, mesh });
    const outline = mesh.outline || [];
    if (outline.length) {
      const closed = [...outline, outline[0]];
      traces.push({
        type: "scatter3d",
        mode: "lines",
        x: column(closed, 0),
        y: column(closed, 1),
        z: column(closed, 2),
        line: { color: "black", width: 2 },
        hoverinfo: "skip",
        showlegend: false,
      });
      infos.push({ kind: "outline", owner: mesh.component, mesh });
    }
  }
  for (const mesh of ghost) {
    const trace = ghostTrace(mesh);
    if (!trace) continue;
    traces.push(trace);
    infos.push({ kind: "ghost", owner: null, mesh });
  }
  // One trace for the highlight, always last. Moving it is a single call, so
  // the camera can travel in the same call and no intermediate frame is drawn.
  traces.push({
    type: "mesh3d",
    ...highlightGeometry(active.find((mesh) => mesh.component === selected)),
    color: HIGHLIGHT,
    opacity: 1,
    flatshading: true,
    lighting: { ambient: 0.85, diffuse: 0.5, specular: 0.05 },
    hoverinfo: "skip",
    showlegend: false,
  });
  infos.push({ kind: "highlight", owner: null, mesh: null });
  return { traces, infos };
}

// "Was this written in the file?" cannot be answered: write_dict() emits every
// parameter, so the document always carries them all. What is well defined,
// and what the form can show, is whether the value still equals the default
// declared by the component class.
const isDefault = (sch, value) =>
  value === undefined || sameValue(value, sch.default);

function buildValidator(schema) {
  if (!schema || Object.keys(schema).length === 0) return {};
  try {
    // discriminator:true makes Ajv pick the branch matching "type" instead of
    // reporting one failure per component type, which turns
    // "must NOT have additional properties" into "conductivity must be >= 0".
    const ajv = new Ajv2020({ strict: false, allErrors: true, discriminator: true });
    return { validate: ajv.compile(schema) };
  } catch (err) {
    return { schemaError: String(err.message || err) };
  }
}

// ____________________ value coercion ____________________

function parseScalar(kind, raw) {
  if (kind === "integer") {
    const n = parseInt(raw, 10);
    return Number.isNaN(n) ? raw : n;
  }
  if (kind === "number" || kind === "math") {
    if (raw.trim() === "") return raw;
    const n = Number(raw);
    // A math expression stays a string unless it is a plain constant.
    return Number.isNaN(n) ? raw : n;
  }
  return raw;
}

const parseList = (kind, raw) =>
  raw.split(",").map((part) => parseScalar(kind, part.trim())).filter(
    (v) => v !== "",
  );

const formatList = (value) => (Array.isArray(value) ? value.join(", ") : String(value ?? ""));

export default {
  render({ model, el }) {
    let doc = structuredClone(model.get("value"));
    let schema = model.get("schema");
    let { validate, schemaError } = buildValidator(schema);
    let selection = { kind: "project" };
    let timer = null;
    let errorsByPath = new Map();

    const defs = () => schema.$defs || {};
    const components = () => (Array.isArray(doc.components) ? doc.components : []);

    const root = document.createElement("div");
    root.className = "osm-editor";
    root.innerHTML = `
      <div class="osm-list">
        <div class="osm-tree"></div>
        <div class="osm-list-actions">
          <select class="osm-new-type"></select>
          <button class="osm-new" type="button">Add</button>
          <button class="osm-delete" type="button">Delete</button>
        </div>
      </div>
      <div class="osm-right">
        <div class="osm-detail"></div>
        <div class="osm-view" hidden>
          <div class="osm-view-bar">
            <label>Space
              <select class="osm-space-filter"></select>
            </label>
            <label><input type="checkbox" class="osm-openings" checked> Openings</label>
            <span class="osm-view-count"></span>
          </div>
          <div class="osm-plot"></div>
        </div>
      </div>`;
    el.appendChild(root);

    const bar = document.createElement("div");
    bar.className = "osm-bar";
    bar.innerHTML = `
      <div class="osm-status"></div>
      <button class="osm-toggle osm-form-toggle" type="button">Hide parameters</button>
      <button class="osm-toggle osm-view-toggle" type="button">Show 3D</button>`;
    el.appendChild(bar);

    const status = bar.querySelector(".osm-status");
    const view = root.querySelector(".osm-view");
    const viewToggle = bar.querySelector(".osm-view-toggle");
    const formToggle = bar.querySelector(".osm-form-toggle");
    const plot = view.querySelector(".osm-plot");
    const spaceFilter = view.querySelector(".osm-space-filter");
    const openingsToggle = view.querySelector(".osm-openings");
    const viewCount = view.querySelector(".osm-view-count");

    const tree = root.querySelector(".osm-tree");
    const detail = root.querySelector(".osm-detail");
    const newType = root.querySelector(".osm-new-type");
    const collapsed = new Set();

    // ____________________ sync ____________________

    const publish = () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        // Traitlets compares by identity, so this has to be a new object.
        model.set("value", structuredClone(doc));
        model.set("errors", collectErrors());
        model.save_changes();
      }, DEBOUNCE_MS);
    };

    // ____________________ validation ____________________

    function danglingReferences() {
      // The schema cannot check this: references are component names, and
      // whether a name exists is a property of the document, not of the type.
      const byName = new Map(components().map((c) => [c.name, c]));
      const found = [];
      const scan = (container, sch, basePath) => {
        for (const [key, propSchema] of Object.entries(sch.properties || {})) {
          const item = itemSchema(propSchema);
          if (!item["x-ref"]) continue;
          const raw = container[key];
          if (raw === undefined) continue;
          const values = Array.isArray(raw) ? raw : [raw];
          values.forEach((name, i) => {
            if (name === "not_defined" || name === "" || String(name).includes("->")) return;
            const target = byName.get(name);
            const allowed = item["x-ref"].allowed_types || [];
            const path = isList(propSchema) ? `${basePath}/${key}/${i}` : `${basePath}/${key}`;
            if (!target) {
              found.push({ path, message: `no component named "${name}"`, severity: "warning" });
            } else if (allowed.length && !allowed.includes(target.type)) {
              found.push({
                path,
                message: `"${name}" is a ${target.type}, expected ${allowed.join(" or ")}`,
                severity: "warning",
              });
            }
          });
        }
      };
      scan(doc, schema, "");
      components().forEach((comp, i) => {
        const def = defs()[comp.type];
        if (def) scan(comp, def, `/components/${i}`);
      });
      return found;
    }

    function collectErrors() {
      const found = [];
      if (validate && !validate(doc)) {
        for (const err of validate.errors || []) {
          found.push({
            path: (err.instancePath || "").split("/").filter((p) => p !== ""),
            message: err.message,
            severity: "error",
          });
        }
      }
      for (const warn of danglingReferences()) {
        found.push({
          path: warn.path.split("/").filter((p) => p !== ""),
          message: warn.message,
          severity: warn.severity,
        });
      }
      return found;
    }

    function refreshErrors() {
      const found = collectErrors();
      errorsByPath = new Map();
      for (const e of found) {
        const key = "/" + e.path.join("/");
        if (!errorsByPath.has(key)) errorsByPath.set(key, e);
      }
      const errors = found.filter((e) => e.severity === "error");
      const warnings = found.filter((e) => e.severity === "warning");
      if (schemaError) {
        status.textContent = `Schema could not be compiled: ${schemaError}`;
        status.dataset.state = "error";
      } else if (errors.length === 0 && warnings.length === 0) {
        status.textContent = "No problems";
        status.dataset.state = "ok";
      } else {
        const parts = [];
        if (errors.length) parts.push(`${errors.length} error${errors.length > 1 ? "s" : ""}`);
        if (warnings.length) parts.push(`${warnings.length} warning${warnings.length > 1 ? "s" : ""}`);
        const first = errors[0] || warnings[0];
        status.textContent = `${parts.join(", ")} — /${first.path.join("/")} ${first.message}`;
        status.dataset.state = errors.length ? "error" : "warn";
      }
      return found;
    }

    // ____________________ left panel ____________________

    function pathOf(index, key) {
      return index === null ? `/${key}` : `/components/${index}/${key}`;
    }

    function countsByType() {
      const grouped = new Map();
      components().forEach((comp, index) => {
        if (!grouped.has(comp.type)) grouped.set(comp.type, []);
        grouped.get(comp.type).push({ comp, index });
      });
      return grouped;
    }

    function renderTree() {
      tree.innerHTML = "";
      const projectRow = document.createElement("div");
      projectRow.className = "osm-item osm-project";
      projectRow.textContent = doc.name ? `Project: ${doc.name}` : "Project";
      projectRow.classList.toggle("selected", selection.kind === "project");
      projectRow.onclick = () => {
        selection = { kind: "project" };
        render();
      };
      tree.appendChild(projectRow);

      const withErrors = new Set();
      for (const key of errorsByPath.keys()) {
        const match = key.match(/^\/components\/(\d+)/);
        if (match) withErrors.add(Number(match[1]));
      }

      for (const [type, entries] of [...countsByType()].sort()) {
        const header = document.createElement("div");
        header.className = "osm-group";
        header.textContent = `${collapsed.has(type) ? "▸" : "▾"} ${type} (${entries.length})`;
        header.onclick = () => {
          collapsed.has(type) ? collapsed.delete(type) : collapsed.add(type);
          renderTree();
        };
        tree.appendChild(header);
        if (collapsed.has(type)) continue;

        for (const { comp, index } of entries) {
          const row = document.createElement("div");
          row.className = "osm-item";
          row.textContent = comp.name ?? `(${type})`;
          row.classList.toggle("selected", selection.kind === "component" && selection.index === index);
          row.classList.toggle("has-error", withErrors.has(index));
          row.onclick = () => {
            selection = { kind: "component", index };
            render();
          };
          tree.appendChild(row);
        }
      }
    }

    // ____________________ fields ____________________

    function makeInput(kind, sch, value, onCommit) {
      const item = itemSchema(sch);
      let input;

      if (kind === "boolean" && !isList(sch)) {
        input = document.createElement("input");
        input.type = "checkbox";
        input.checked = value === true;
        input.onchange = () => onCommit(input.checked);
        return input;
      }

      if (kind === "enum" && !isList(sch)) {
        input = document.createElement("select");
        for (const option of item.enum) {
          const el = document.createElement("option");
          el.value = el.textContent = option;
          input.appendChild(el);
        }
        input.value = value ?? "";
        input.onchange = () => onCommit(input.value);
        return input;
      }

      if (kind === "ref" && !isList(sch)) {
        input = document.createElement("select");
        const allowed = item["x-ref"].allowed_types || [];
        const names = components()
          .filter((c) => allowed.length === 0 || allowed.includes(c.type))
          .map((c) => c.name);
        // Keep whatever is stored even if it points nowhere, so opening the
        // form never silently rewrites a dangling reference.
        if (value !== undefined && !names.includes(value)) names.unshift(value);
        for (const name of names) {
          const el = document.createElement("option");
          el.value = el.textContent = name;
          input.appendChild(el);
        }
        input.value = value ?? "";
        input.onchange = () => onCommit(input.value);
        return input;
      }

      input = document.createElement("input");
      if (isList(sch)) {
        input.type = "text";
        input.value = formatList(value);
        input.placeholder = "comma separated";
        input.onchange = () => onCommit(parseList(kind, input.value));
      } else if (kind === "integer" || kind === "number") {
        input.type = "number";
        input.step = kind === "integer" ? "1" : "any";
        if (item.minimum !== undefined) input.min = item.minimum;
        if (item.maximum !== undefined) input.max = item.maximum;
        input.value = value ?? "";
        input.onchange = () => onCommit(parseScalar(kind, input.value));
      } else {
        input.type = "text";
        if (kind === "math") input.classList.add("osm-mono");
        input.value = value ?? "";
        input.onchange = () => onCommit(parseScalar(kind, input.value));
      }
      return input;
    }

    function renderForm(container, sch, index) {
      const title = document.createElement("div");
      title.className = "osm-detail-title";
      title.textContent =
        index === null ? "Project parameters" : `${container.type}: ${container.name ?? ""}`;
      detail.appendChild(title);

      const grid = document.createElement("div");
      grid.className = "osm-form";
      detail.appendChild(grid);

      for (const [key, propSchema] of Object.entries(sch.properties || {})) {
        // "type" is the discriminator and "components" is the list itself.
        if (key === "type" || key === "components") continue;

        const kind = fieldKind(propSchema);
        const item = itemSchema(propSchema);

        const label = document.createElement("label");
        label.className = "osm-label";
        label.textContent = key;
        grid.appendChild(label);

        const cell = document.createElement("div");
        cell.className = "osm-cell";
        const control = document.createElement("div");
        control.className = "osm-control";
        cell.appendChild(control);

        const commit = (next) => {
          container[key] = next;
          publish();
          refreshErrors();
          markField(cell, pathOf(index, key));
          markModified(cell, propSchema, container[key]);
          // A rename changes the left panel and every reference dropdown.
          if (key === "name") render();
        };

        const input = makeInput(kind, propSchema, container[key], commit);
        input.classList.add(widthClass(kind, propSchema));
        control.appendChild(input);

        if (item["x-unit"]) {
          const unit = document.createElement("span");
          unit.className = "osm-unit";
          unit.textContent = item["x-unit"];
          control.appendChild(unit);
        }

        if (propSchema.default !== undefined) {
          const revert = document.createElement("button");
          revert.type = "button";
          revert.className = "osm-revert";
          revert.textContent = "↺";
          revert.title = `Reset to default (${JSON.stringify(propSchema.default)})`;
          revert.onclick = () => {
            commit(structuredClone(propSchema.default));
            renderDetail();
          };
          control.appendChild(revert);
        }

        const note = document.createElement("div");
        note.className = "osm-note";
        cell.appendChild(note);
        grid.appendChild(cell);
        markField(cell, pathOf(index, key));
        markModified(cell, propSchema, container[key]);
      }
    }

    function markModified(cell, sch, value) {
      // Bold, and the reset button only where there is something to reset.
      const modified = !isDefault(sch, value);
      cell.classList.toggle("modified", modified);
    }

    function markField(cell, path) {
      const note = cell.querySelector(".osm-note");
      if (!note) return;
      // A list reports errors on /path/<i>; show the first one on the field.
      let problem = errorsByPath.get(path);
      if (!problem) {
        for (const [key, value] of errorsByPath) {
          if (key.startsWith(path + "/")) { problem = value; break; }
        }
      }
      cell.classList.toggle("has-error", problem?.severity === "error");
      cell.classList.toggle("has-warning", problem?.severity === "warning");
      note.textContent = problem ? problem.message : "";
    }

    function renderDetail() {
      detail.innerHTML = "";
      if (selection.kind === "project") {
        renderForm(doc, schema, null);
        return;
      }
      const comp = components()[selection.index];
      if (!comp) {
        selection = { kind: "project" };
        renderDetail();
        return;
      }
      const def = defs()[comp.type];
      if (!def) {
        detail.textContent = `Unknown component type: ${comp.type}`;
        return;
      }
      renderForm(comp, def, selection.index);
    }

    // ____________________ add / delete ____________________

    function fillTypes() {
      newType.innerHTML = "";
      for (const type of Object.keys(defs()).sort()) {
        const option = document.createElement("option");
        option.value = option.textContent = type;
        newType.appendChild(option);
      }
    }

    root.querySelector(".osm-new").onclick = () => {
      const type = newType.value;
      const def = defs()[type];
      if (!def) return;
      const created = { type };
      for (const [key, propSchema] of Object.entries(def.properties || {})) {
        if (key === "type") continue;
        if (propSchema.default !== undefined) created[key] = structuredClone(propSchema.default);
      }
      const taken = new Set(components().map((c) => c.name));
      let n = 1;
      while (taken.has(`${type}_${n}`)) n += 1;
      created.name = `${type}_${n}`;

      if (!Array.isArray(doc.components)) doc.components = [];
      doc.components.push(created);
      selection = { kind: "component", index: doc.components.length - 1 };
      publish();
      render();
    };

    root.querySelector(".osm-delete").onclick = () => {
      if (selection.kind !== "component") return;
      doc.components.splice(selection.index, 1);
      selection = { kind: "project" };
      publish();
      render();
    };

    // ____________________ render ____________________

    // ____________________ 3D view ____________________

    // Where the user has turned the model to. react() does not preserve it: a
    // layout without a camera makes plotly put back its own, so it has to be
    // captured and handed back on every redraw.
    let viewCamera = null;
    let wheelTimer = null;
    let viewInfos = [];
    let viewBound = false;
    const filters = { space: "", openings: true };

    function selectedComponentName() {
      if (selection.kind !== "component") return null;
      const comp = components()[selection.index];
      return comp ? comp.name : null;
    }

    function fillSpaceFilter(geometry) {
      const spaces = geometry.spaces || [];
      const previous = filters.space;
      spaceFilter.innerHTML = "";
      for (const [value, label] of [["", "all"], ...spaces.map((s) => [s, s])]) {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        spaceFilter.appendChild(option);
      }
      // A space that no longer exists cannot stay selected, or the view would
      // silently show nothing.
      filters.space = spaces.includes(previous) ? previous : "";
      spaceFilter.value = filters.space;
    }

    async function renderView() {
      if (view.hidden) return;
      const geometry = model.get("geometry") || {};
      if ((geometry.meshes || []).length === 0) {
        plot.textContent = "This project has no geometry to show.";
        plot.classList.add("osm-view-empty");
        viewCount.textContent = "";
        return;
      }
      plot.classList.remove("osm-view-empty");

      const { active, ghost } = splitMeshes(geometry, filters);
      const { traces, infos } = geometryTraces(active, ghost, selectedComponentName());
      viewInfos = infos;
      viewCount.textContent = ghost.length
        ? `${active.length} of ${geometry.meshes.length}`
        : `${active.length} surfaces`;

      try {
        const plotly = await loadPlotly();
        const layout = { ...VIEW_LAYOUT, scene: { ...VIEW_LAYOUT.scene } };
        const bounds = modelBounds(geometry);
        if (bounds) {
          const [x, y, z] = axisRanges(bounds);
          layout.scene.xaxis = { ...layout.scene.xaxis, range: x };
          layout.scene.yaxis = { ...layout.scene.yaxis, range: y };
          layout.scene.zaxis = { ...layout.scene.zaxis, range: z };
          layout.scene.camera = viewCamera || defaultCamera(bounds);
          viewCamera = layout.scene.camera;
        }
        // react(), not newPlot(): it keeps the camera, so the view does not
        // jump back to its default angle every time the geometry is reloaded.
        await plotly.react(plot, traces, layout, {
          responsive: true,
          displaylogo: false,
        });
        await restoreCamera(plotly);
        if (!viewBound) {
          // pointerup covers a touch drag, where there is no mouseup.
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
            if (!point) return;
            const info = viewInfos[point.curveNumber];
            if (!info) return;
            const index = components().findIndex((c) => c.name === info.owner);
            if (index < 0) return;
            // Out of plotly's own event dispatch. Touching the plot from
            // inside it tears the WebGL scene down while it is still being
            // used, and the tab locks up.
            setTimeout(() => {
              // One click arrives several times, once per trace under the
              // pointer; only the first has anything to do.
              if (selection.kind === "component" && selection.index === index) return;
              selection = { kind: "component", index };
              render();
            }, 0);
          });
          viewBound = true;
        }
      } catch (err) {
        plot.textContent = `Could not load the 3D view: ${err.message || err}`;
        plot.classList.add("osm-view-empty");
      }
    }

    function readCamera() {
      // The live camera, the one a drag moves. plotly keeps it on the scene
      // object; _fullLayout.scene.camera is only what was last set into the
      // layout, so reading that gives back our own angle, never the user's.
      const scene = plot._fullLayout && plot._fullLayout.scene;
      if (!scene) return null;
      const live =
        scene._scene && typeof scene._scene.getCamera === "function"
          ? scene._scene.getCamera()
          : scene.camera;
      return live && live.eye ? JSON.parse(JSON.stringify(live)) : null;
    }

    function rememberCamera() {
      // Only on real input. Listening to plotly instead means a redraw that
      // resets the scene reports its own camera as if the user had moved
      // there, and the angle to go back to is lost.
      const camera = readCamera();
      if (camera) viewCamera = camera;
    }

    async function restoreCamera(plotly) {
      // Whatever plotly decided to rebuild, the model goes back to the angle
      // the user left it at. Unconditionally: comparing first would trust a
      // reading that a rebuild may already have replaced.
      if (!viewCamera) return;
      await plotly.relayout(plot, { "scene.camera": viewCamera });
    }

    async function highlightSelection() {
      if (view.hidden || !plotlyPromise || viewInfos.length === 0) return;
      const index = viewInfos.findIndex((info) => info.kind === "highlight");
      if (index < 0) return;
      const selected = selectedComponentName();
      const mesh = viewInfos.find(
        (info) => info.kind === "mesh" && info.owner === selected,
      );
      const shape = highlightGeometry(mesh ? mesh.mesh : null);
      try {
        const plotly = await loadPlotly();
        // plotly decides what to apply by diffing against gd.layout, so handing
        // it the camera already recorded there counts as no change and it is
        // skipped, leaving whatever a rebuild put in its place. Forgetting the
        // recorded one makes the camera part of the update take effect.
        if (plot.layout && plot.layout.scene) delete plot.layout.scene.camera;
        // update(), not restyle() then relayout(): moving the highlight can
        // make plotly rebuild the gl scene, which brings the camera back to
        // its opening angle. Two calls draw that angle before the second one
        // corrects it, and the jump is plainly visible. One call does not.
        await plotly.update(
          plot,
          {
            x: [shape.x],
            y: [shape.y],
            z: [shape.z],
            i: [shape.i],
            j: [shape.j],
            k: [shape.k],
          },
          viewCamera ? { "scene.camera": viewCamera } : {},
          [index],
        );
      } catch (err) {
        /* the view will catch up on its next full redraw */
      }
    }

    spaceFilter.onchange = () => {
      filters.space = spaceFilter.value;
      renderView();
    };

    openingsToggle.onchange = () => {
      filters.openings = openingsToggle.checked;
      renderView();
    };

    function resizeView() {
      // The view keeps its plot when the panel changes size; only plotly has
      // to be told. Never load it just to resize a plot that is not there.
      if (view.hidden || !plotlyPromise) return;
      plotlyPromise.then((plotly) => plotly.Plots.resize(plot)).catch(() => {});
    }

    function updatePanels() {
      // The classes drive the sizing: the widget only grows when both panels
      // are up, and the view takes the whole column when it is alone.
      root.classList.toggle("show-form", !detail.hidden);
      root.classList.toggle("show-view", !view.hidden);
      formToggle.textContent = detail.hidden ? "Show parameters" : "Hide parameters";
      viewToggle.textContent = view.hidden ? "Show 3D" : "Hide 3D";
      // Closing the last open panel would leave an empty half, so whichever is
      // on its own cannot be closed.
      formToggle.disabled = !detail.hidden && view.hidden;
      viewToggle.disabled = !view.hidden && detail.hidden;
    }

    formToggle.onclick = () => {
      detail.hidden = !detail.hidden;
      updatePanels();
      resizeView();
    };

    viewToggle.onclick = () => {
      view.hidden = !view.hidden;
      updatePanels();
      renderView();
    };

    function render() {
      refreshErrors();
      renderTree();
      renderDetail();
      // The highlighted surface follows whatever is selected in the tree.
      highlightSelection();
    }

    fillTypes();
    fillSpaceFilter(model.get("geometry") || {});
    updatePanels();
    render();

    const onValueChange = () => {
      const incoming = model.get("value");
      // Skip the echo of the value we just published ourselves.
      if (JSON.stringify(incoming) === JSON.stringify(doc)) return;
      doc = structuredClone(incoming);
      render();
    };

    const onSchemaChange = () => {
      schema = model.get("schema");
      ({ validate, schemaError } = buildValidator(schema));
      fillTypes();
      render();
    };

    // The 3D view follows the project, which changes when apply() reloads it.
    const onGeometryChange = () => {
      fillSpaceFilter(model.get("geometry") || {});
      renderView();
    };

    model.on("change:value", onValueChange);
    model.on("change:schema", onSchemaChange);
    model.on("change:geometry", onGeometryChange);

    return () => {
      clearTimeout(timer);
      clearTimeout(wheelTimer);
      model.off("change:value", onValueChange);
      model.off("change:schema", onSchemaChange);
      model.off("change:geometry", onGeometryChange);
      // Only if it was ever loaded: purging must not pull in 1.7MB to do it.
      if (plotlyPromise) {
        plotlyPromise.then((plotly) => plotly.purge(plot)).catch(() => {});
      }
    };
  },
};
