import { createJSONEditor } from "https://esm.sh/vanilla-jsoneditor@3.13.0";
import Ajv2020 from "https://esm.sh/ajv@8.17.1/dist/2020";

// How long to wait after the last keystroke before pushing the document to the
// kernel. Syncing on every keystroke would round-trip a whole building on each
// character.
const DEBOUNCE_MS = 400;

function buildValidator(schema) {
  if (!schema || Object.keys(schema).length === 0) {
    return { validate: null, error: null };
  }
  try {
    // discriminator:true makes Ajv pick the branch matching "type" instead of
    // reporting one failure per component type, which turns
    // "must NOT have additional properties" into "conductivity must be >= 0".
    const ajv = new Ajv2020({
      strict: false,
      allErrors: true,
      discriminator: true,
    });
    return { validate: ajv.compile(schema), error: null };
  } catch (err) {
    return { validate: null, error: String(err.message || err) };
  }
}

function toValidationErrors(ajvErrors) {
  return (ajvErrors || []).map((err) => ({
    // Ajv gives "/components/3/conductivity"; the editor wants a path array.
    path: (err.instancePath || "").split("/").filter((part) => part !== ""),
    message: err.message,
    severity: "error",
  }));
}

export default {
  render({ model, el }) {
    const container = document.createElement("div");
    container.className = "opensimula-editor";
    el.appendChild(container);

    const status = document.createElement("div");
    status.className = "opensimula-editor-status";
    el.appendChild(status);

    let { validate, error: schemaError } = buildValidator(model.get("schema"));
    if (schemaError) {
      status.textContent = `Schema could not be compiled: ${schemaError}`;
      status.dataset.state = "error";
    }

    // Set while we are writing the editor's content from the model, so the
    // resulting onChange does not bounce straight back to the kernel.
    let applyingFromModel = false;
    let timer = null;

    const publish = (json) => {
      // Traitlets compares by identity, so this has to be a new object.
      model.set("value", { ...json });
      model.set("errors", validate && !validate(json)
        ? toValidationErrors(validate.errors)
        : []);
      model.save_changes();
    };

    const runValidator = (json) => {
      if (!validate) return [];
      return validate(json) ? [] : toValidationErrors(validate.errors);
    };

    const showStatus = (errors) => {
      if (schemaError) return;
      if (errors.length === 0) {
        status.textContent = "Valid project";
        status.dataset.state = "ok";
      } else {
        const first = errors[0];
        const where = first.path.length ? `/${first.path.join("/")}` : "/";
        status.textContent =
          errors.length === 1
            ? `1 error — ${where} ${first.message}`
            : `${errors.length} errors — ${where} ${first.message}`;
        status.dataset.state = "error";
      }
    };

    const editor = createJSONEditor({
      target: container,
      props: {
        content: { json: model.get("value") },
        mode: "tree",
        mainMenuBar: true,
        navigationBar: true,
        // The editor calls this on every content change; it is what draws the
        // inline error markers next to offending values.
        validator: validate ? (json) => runValidator(json) : undefined,
        onChange: (content, previousContent, { contentErrors }) => {
          if (applyingFromModel) return;
          // Do not publish while the text is not parseable JSON: the document
          // would arrive at the kernel truncated mid-edit.
          if (contentErrors && contentErrors.parseError) {
            status.textContent = "Invalid JSON — not synced";
            status.dataset.state = "error";
            return;
          }
          const json = content.json !== undefined
            ? content.json
            : JSON.parse(content.text);
          showStatus(runValidator(json));
          clearTimeout(timer);
          timer = setTimeout(() => publish(json), DEBOUNCE_MS);
        },
      },
    });

    showStatus(runValidator(model.get("value")));

    const onValueChange = () => {
      const json = model.get("value");
      const current = editor.get();
      const shown = current.json !== undefined ? current.json : undefined;
      // Skip the echo of the value we just published ourselves.
      if (JSON.stringify(shown) === JSON.stringify(json)) return;
      applyingFromModel = true;
      editor.update({ json });
      applyingFromModel = false;
      showStatus(runValidator(json));
    };

    const onSchemaChange = () => {
      ({ validate, error: schemaError } = buildValidator(model.get("schema")));
      editor.updateProps({
        validator: validate ? (json) => runValidator(json) : undefined,
      });
      showStatus(runValidator(model.get("value")));
    };

    model.on("change:value", onValueChange);
    model.on("change:schema", onSchemaChange);

    return () => {
      clearTimeout(timer);
      model.off("change:value", onValueChange);
      model.off("change:schema", onSchemaChange);
      editor.destroy();
    };
  },
};
