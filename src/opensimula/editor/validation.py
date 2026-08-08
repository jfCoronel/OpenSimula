"""Schema validation of a project document, on the Python side.

The widget validates in the browser to draw its inline markers, but that only
happens when there is a browser. Anything acting on a document, above all
applying it to a project, needs an answer without one.

Errors are reported in the shape the frontend uses, so both sides read the
same: {"path": [...], "message": str, "severity": "error"}.
"""

import jsonschema

COMPONENTS = "components"


def _problem(path, message):
    return {
        "path": [str(part) for part in path],
        "message": message,
        "severity": "error",
    }


def _project_schema(schema):
    """The schema with the component list left unchecked.

    Components are validated one by one against their own definition instead:
    the "components" union reports one failure per component type, and the
    first of them names the wrong problem. Ajv is told to use the "type"
    discriminator; jsonschema has no such option, so the union is opened here.
    """
    shallow = dict(schema)
    shallow["properties"] = dict(schema.get("properties", {}))
    shallow["properties"][COMPONENTS] = {"type": "array"}
    shallow.pop("$defs", None)
    return shallow


def _component_schema(schema, type_name):
    definition = dict(schema["$defs"][type_name])
    definition["$defs"] = schema["$defs"]  # keep $ref resolvable
    return definition


def validate_document(document, schema):
    """Validate a project document against the project JSON Schema.

    Args:
        document (dict): the project definition.
        schema (dict): schema to validate against.

    Returns:
        list of dict: one entry per problem, empty if the document is valid.
    """
    if not schema:
        return []

    found = []
    validator_for = jsonschema.validators.validator_for

    shallow = _project_schema(schema)
    for error in validator_for(shallow)(shallow).iter_errors(document):
        found.append(_problem(error.absolute_path, error.message))

    definitions = schema.get("$defs", {})
    components = document.get(COMPONENTS)
    if not isinstance(components, list):
        return found

    for index, component in enumerate(components):
        base = [COMPONENTS, index]
        if not isinstance(component, dict):
            found.append(_problem(base, "component is not an object"))
            continue
        type_name = component.get("type")
        if type_name not in definitions:
            found.append(_problem(base + ["type"], f"unknown component type {type_name!r}"))
            continue
        sub = _component_schema(schema, type_name)
        for error in validator_for(sub)(sub).iter_errors(component):
            found.append(_problem(base + list(error.absolute_path), error.message))

    return found


def format_errors(errors):
    """Validation errors as readable lines."""
    return [
        "/" + "/".join(error.get("path", [])) + ": " + error.get("message", "")
        for error in errors
    ]
