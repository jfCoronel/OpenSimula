import ast
import json
import pathlib

import jsonschema
import nbformat
import pytest

import opensimula as osm
from opensimula.editor import component_types, project_json_schema

ROOT = pathlib.Path(__file__).parent.parent

# Real project files, used as the corpus that keeps the generated schema honest:
# if the schema rejects one of these, the schema is wrong, not the file.
PROJECT_FILES = [
    "test/test_project_1.json",
    "test/test_project_2.json",
    "jupyter_test/edificio_curso_hulc.json",
    "mkdocs/jupyters/getting_started.json",
]


@pytest.fixture(scope="module")
def schema():
    return project_json_schema()


def test_schema_is_itself_valid(schema):
    validator = jsonschema.validators.validator_for(schema)
    validator.check_schema(schema)


def test_every_component_type_has_a_definition(schema):
    assert set(schema["$defs"]) == set(component_types())


def test_component_defs_are_discriminated_by_type(schema):
    items = schema["properties"]["components"]["items"]
    assert items["discriminator"] == {"propertyName": "type"}
    assert len(items["oneOf"]) == len(schema["$defs"])
    for name, definition in schema["$defs"].items():
        assert definition["properties"]["type"] == {"const": name}


def test_declared_type_matches_class_name():
    """A component whose "type" parameter differs from its class name cannot
    survive write_dict() -> read_dict(): the dict records the "type" value, and
    _load_from_dict_ resolves it as a class name."""
    sim = osm.Simulation()
    sim.console_print = False
    project = sim.new_project("round_trip")
    for type_name in component_types():
        comp = project.new_component(type_name, f"c_{type_name}")
        assert comp.parameter("type").value == type_name


def test_list_parameters_accept_the_scalar_shorthand(schema):
    spaces = schema["$defs"]["Building_surface"]["properties"]["spaces"]
    assert spaces["x-list"] is True
    jsonschema.validate(
        {"components": [{"type": "Building_surface", "spaces": "one_space"}]}, schema
    )
    jsonschema.validate(
        {"components": [{"type": "Building_surface", "spaces": ["a", "b"]}]}, schema
    )


def test_allowed_types_are_always_lists():
    """A component declaring allowed_types as a bare string turns
    Parameter_component.check() into a substring test, and would reach the
    schema as one entry per character."""
    sim = osm.Simulation()
    sim.console_print = False
    project = sim.new_project("allowed_types")
    for type_name in component_types():
        comp = project.new_component(type_name, f"c_{type_name}")
        for key, par in comp.parameter_dict().items():
            allowed = getattr(par, "allowed_types", None)
            if allowed is not None:
                assert isinstance(allowed, list), f"{type_name}.{key} is {allowed!r}"


def test_every_reference_names_known_component_types(schema):
    known = set(schema["$defs"])
    for name, definition in schema["$defs"].items():
        for key, prop in definition["properties"].items():
            item = prop["anyOf"][1] if prop.get("x-list") else prop
            ref = item.get("x-ref") if isinstance(item, dict) else None
            if ref:
                unknown = set(ref["allowed_types"]) - known
                assert not unknown, f"{name}.{key} allows unknown types {unknown}"


def test_parameter_metadata_reaches_the_schema(schema):
    material = schema["$defs"]["Material"]["properties"]
    assert material["conductivity"]["type"] == "number"
    assert material["conductivity"]["x-unit"] == "W/(m·K)"
    assert material["conductivity"]["minimum"] == 0

    project = schema["properties"]
    assert project["albedo"]["minimum"] == 0
    assert project["albedo"]["maximum"] == 1
    assert project["shadow_calculation"]["enum"] == ["NO", "INSTANT", "INTERPOLATION"]
    assert project["simulation_file_met"]["x-ref"] == {
        "kind": "component",
        "allowed_types": ["File_met"],
    }


def test_unbounded_numbers_have_no_limits(schema):
    # n_time_steps is min=1 with no upper bound (sys.maxsize sentinel)
    n_time_steps = schema["properties"]["n_time_steps"]
    assert n_time_steps["minimum"] == 1
    assert "maximum" not in n_time_steps


@pytest.mark.parametrize("relative_path", PROJECT_FILES)
def test_real_projects_validate(schema, relative_path):
    path = ROOT / relative_path
    if not path.exists():
        pytest.skip(f"{relative_path} not present")
    document = json.loads(path.read_text())
    jsonschema.validate(document, schema)


def _project_dicts_in_notebooks(directory):
    """Yield (notebook, project dict) for every project literal in the notebooks.

    The ASHRAE 140 cases define their projects as dict literals inside code
    cells, which makes them the largest corpus of real project definitions in
    the repository. They are read with ast.literal_eval, so cells that build a
    dict from variables are skipped rather than executed.
    """
    for notebook_path in sorted(directory.rglob("*.ipynb")):
        notebook = nbformat.read(notebook_path, as_version=4)
        for cell in notebook.cells:
            if cell.cell_type != "code":
                continue
            try:
                tree = ast.parse(cell.source)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Dict):
                    continue
                try:
                    document = ast.literal_eval(node)
                except ValueError:
                    continue
                if isinstance(document, dict) and "components" in document:
                    yield notebook_path.name, document


def test_ashrae_140_projects_validate(schema):
    directory = ROOT / "ASHRAE_140"
    if not directory.is_dir():
        pytest.skip("ASHRAE_140 not present")

    validator = jsonschema.Draft202012Validator(schema)
    failures = []
    n_documents = 0
    for notebook, document in _project_dicts_in_notebooks(directory):
        n_documents += 1
        for component in document["components"]:
            type_name = component.get("type")
            assert type_name in schema["$defs"], f"{notebook}: unknown type {type_name}"
            # Validate against the component's own definition: a oneOf failure
            # reports one error per branch and buries the real cause.
            definition = dict(schema["$defs"][type_name])
            definition["$defs"] = schema["$defs"]
            for error in jsonschema.Draft202012Validator(definition).iter_errors(
                component
            ):
                path = "/".join(str(p) for p in error.absolute_path)
                failures.append(f"{notebook}: {type_name}.{path}: {error.message}")
        validator.validate(document)

    assert n_documents > 0, "no project dicts found in the notebooks"
    assert failures == [], "\n".join(failures[:20])


def test_unknown_parameter_is_rejected(schema):
    document = {
        "name": "p",
        "components": [
            {"type": "Material", "name": "m", "not_a_parameter": 1},
        ],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(document, schema)


def test_out_of_range_value_is_rejected(schema):
    document = {
        "name": "p",
        "components": [
            {"type": "Material", "name": "m", "conductivity": -1},
        ],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(document, schema)
