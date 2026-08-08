"""JSON Schema generation for OpenSimula project files.

The schema is derived from the component classes themselves, walking their
``Parameter_*`` objects, so the description of the file format never has to be
maintained in a second place.

Components are described as a union discriminated by the ``type`` field, which
is what lets a form generator switch form depending on the component type.

UI metadata that has no standard JSON Schema keyword is emitted with an ``x-``
prefix:

- ``x-unit``: unit of a numeric parameter or math expression.
- ``x-ref``: parameter holding the *name* of another component, with the list
  of component types it accepts.
- ``x-format``: syntax of a string parameter (``variable-ref``, ``math-exp``).
"""

import inspect
import math
import sys

from opensimula import components as _components
from opensimula.Component import Component
from opensimula.Simulation import Simulation

SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"


def component_types():
    """Names of every component type registered in OpenSimula, sorted."""
    names = []
    for name, obj in vars(_components).items():
        if inspect.isclass(obj) and issubclass(obj, Component) and obj is not Component:
            names.append(name)
    return sorted(names)


# ___________________ Parameter -> schema fragment _________________________


def _add_unit(par, schema):
    if getattr(par, "unit", ""):
        schema["x-unit"] = par.unit
    return schema


def _add_bounds(par, schema):
    """Add minimum/maximum, skipping the "no limit" sentinels.

    Integers default to max=sys.maxsize and floats to +/-inf; neither is a real
    constraint, and infinities are not representable in JSON anyway.
    """
    low = par.min
    high = par.max
    if math.isfinite(low) and low != -sys.maxsize:
        schema["minimum"] = low
    if math.isfinite(high) and high != sys.maxsize:
        schema["maximum"] = high
    return schema


def _boolean(par):
    return {"type": "boolean"}


def _string(par):
    return {"type": "string"}


def _integer(par):
    return _add_bounds(par, _add_unit(par, {"type": "integer"}))


def _number(par):
    return _add_bounds(par, _add_unit(par, {"type": "number"}))


def _options(par):
    return {"type": "string", "enum": list(par.options)}


def _allowed_types(par):
    """allowed_types as a list, whatever the component declared.

    A bare string is accepted: list("Material") would otherwise split it into
    characters, and Parameter_component.check() likewise turns into a substring
    test instead of a membership test.
    """
    allowed = par.allowed_types
    if isinstance(allowed, str):
        return [allowed]
    return list(allowed)


def _component_ref(par):
    return {
        "type": "string",
        "x-ref": {"kind": "component", "allowed_types": _allowed_types(par)},
    }


def _variable_ref(par):
    return {"type": "string", "x-format": "variable-ref"}


def _math_exp(par):
    # A math expression is a string, but the setter stringifies whatever it
    # gets, and projects commonly write a plain constant ("outdoor_air_fraction": 0).
    return _add_unit(par, {"type": ["string", "number"], "x-format": "math-exp"})


# Dispatch on the exact class name rather than isinstance: Parameter_float
# subclasses Parameter_int, so isinstance checks would silently depend on the
# order they are written in.
_ITEM_BUILDERS = {
    "Parameter_boolean": _boolean,
    "Parameter_boolean_list": _boolean,
    "Parameter_string": _string,
    "Parameter_string_list": _string,
    "Parameter_int": _integer,
    "Parameter_int_list": _integer,
    "Parameter_float": _number,
    "Parameter_float_list": _number,
    "Parameter_options": _options,
    "Parameter_options_list": _options,
    "Parameter_component": _component_ref,
    "Parameter_component_list": _component_ref,
    "Parameter_variable": _variable_ref,
    "Parameter_variable_list": _variable_ref,
    "Parameter_math_exp": _math_exp,
    "Parameter_math_exp_list": _math_exp,
}


def parameter_schema(par):
    """Schema fragment describing one Parameter, including its default value."""
    class_name = type(par).__name__
    builder = _ITEM_BUILDERS.get(class_name)
    if builder is None:
        # Unknown parameter class: accept anything rather than reject a valid
        # project because the schema generator has not been taught about it.
        return {"default": par.value}

    item = builder(par)
    if class_name.endswith("_list"):
        # Every *_list setter also accepts a bare scalar and wraps it, and real
        # project files rely on that shorthand ("spaces": "P03_E01"), so the
        # schema has to accept both. x-list marks the array as the canonical
        # form for form generators.
        schema = {"anyOf": [{"type": "array", "items": item}, item], "x-list": True}
    else:
        schema = item

    schema["default"] = par.value
    return schema


# ___________________ Container -> object schema _________________________


def _container_properties(container):
    return {
        key: parameter_schema(par) for key, par in container.parameter_dict().items()
    }


def _component_schema(comp, type_name):
    properties = _container_properties(comp)
    # The discriminator. It is pinned to the class name, which is what
    # Project._load_from_dict_ looks up, not to the component's own "type"
    # parameter value; test_editor_schema checks that the two agree.
    properties["type"] = {"const": type_name}
    return {
        "title": type_name,
        "description": comp.parameter("description").value,
        "type": "object",
        "properties": properties,
        "required": ["type"],
        "additionalProperties": False,
    }


def _prototype_project():
    """A throwaway project used only to instantiate one of each component."""
    sim = Simulation()
    sim.console_print = False
    return sim.new_project("_schema_prototype_")


def project_json_schema(types=None):
    """Build the JSON Schema describing an OpenSimula project file.

    Args:
        types (list of str, optional): component type names to include.
            Defaults to every registered component type.

    Returns:
        dict: JSON Schema (draft 2020-12).
    """
    if types is None:
        types = component_types()

    project = _prototype_project()

    defs = {}
    for type_name in types:
        comp = project.new_component(type_name, f"_prototype_{type_name}_")
        if comp is not None:
            defs[type_name] = _component_schema(comp, type_name)

    properties = _container_properties(project)
    properties["components"] = {
        "type": "array",
        "items": {
            "oneOf": [{"$ref": f"#/$defs/{name}"} for name in defs],
            "discriminator": {"propertyName": "type"},
        },
    }

    return {
        "$schema": SCHEMA_DIALECT,
        "$id": "https://opensimula.org/schemas/project.schema.json",
        "title": "OpenSimula project",
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
        "$defs": defs,
    }
