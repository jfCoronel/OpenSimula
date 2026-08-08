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
      <div class="osm-detail"></div>`;
    el.appendChild(root);

    const status = document.createElement("div");
    status.className = "osm-status";
    el.appendChild(status);

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

    function render() {
      refreshErrors();
      renderTree();
      renderDetail();
    }

    fillTypes();
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

    model.on("change:value", onValueChange);
    model.on("change:schema", onSchemaChange);

    return () => {
      clearTimeout(timer);
      model.off("change:value", onValueChange);
      model.off("change:schema", onSchemaChange);
    };
  },
};
