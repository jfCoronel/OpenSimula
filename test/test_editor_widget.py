import copy
import json
import pathlib

import pytest

import opensimula as osm
import opensimula.editor.widget as widget_module
from opensimula.editor import ProjectEditor, default_schema, format_errors

ROOT = pathlib.Path(__file__).parent.parent


@pytest.fixture
def project():
    sim = osm.Simulation()
    sim.console_print = False
    project = sim.new_project("editor_project")
    project.read_json(str(ROOT / "test/test_project_1.json"))
    return project


def test_editor_loads_the_project_document(project):
    editor = project.editor()
    assert isinstance(editor, ProjectEditor)
    assert editor.project is project
    assert editor.value == project.write_dict()
    assert len(editor.value["components"]) == len(project.component_list())


def test_editor_carries_the_generated_schema(project):
    editor = project.editor()
    assert editor.schema["$id"] == default_schema()["$id"]
    assert "Material" in editor.schema["$defs"]


def test_schema_is_generated_once():
    assert default_schema() is default_schema()


def test_editor_accepts_a_document_without_a_project():
    document = {"name": "standalone", "components": []}
    editor = ProjectEditor(value=document)
    assert editor.project is None
    assert editor.value == document
    assert editor.schema["$id"] == default_schema()["$id"]


def test_synced_traitlets(project):
    editor = project.editor()
    for name in ("value", "schema", "errors"):
        assert editor.trait_metadata(name, "sync") is True


def test_frontend_assets_are_present_and_loadable():
    # Not ProjectEditor._esm: anywidget turns the Path into a FileContents.
    static = pathlib.Path(widget_module.__file__).parent / "static"
    for name in ("editor.js", "editor.css"):
        asset = static / name
        assert asset.is_file(), f"{name} missing"
        assert asset.stat().st_size > 0

    source = (static / "editor.js").read_text()
    # The widget contract with anywidget, and the one module it loads from a CDN.
    assert "export default" in source
    assert "ajv@" in source
    # Ajv defaults to draft-07 and would refuse the 2020-12 schema, and without
    # discriminator the oneOf reports one error per component type.
    assert "discriminator: true" in source
    # The form is built from the schema metadata, not from hardcoded fields.
    for keyword in ("x-ref", "x-unit", "x-list", "x-format"):
        assert keyword in source, f"{keyword} not used by the form builder"


def test_document_is_json_serialisable(project):
    """The value traitlet crosses to the frontend as JSON."""
    json.dumps(project.editor().value)


def test_error_report_formats_paths():
    assert format_errors(
        [{"path": ["components", "3", "conductivity"], "message": "must be >= 0"}]
    ) == ["/components/3/conductivity: must be >= 0"]
    assert format_errors([]) == []


def test_validate_runs_without_a_frontend(project):
    """The errors traitlet is filled by the browser, so it stays empty in a
    script and would report any document as valid."""
    editor = project.editor()
    assert editor.errors == []
    assert editor.validate() == []
    assert editor.is_valid() is True

    broken = copy.deepcopy(editor.value)
    broken["components"][0]["int"] = -1  # Parameter_int defaults to min=0
    editor.value = broken

    assert editor.errors == []  # nothing has rendered it
    errors = editor.validate()
    assert len(errors) == 1
    assert errors[0]["path"] == ["components", "0", "int"]
    assert "minimum" in errors[0]["message"]
    assert editor.is_valid() is False
    assert editor.error_report() == ["/components/0/int: " + errors[0]["message"]]


def test_validate_names_the_offending_component_type(project):
    editor = project.editor()
    broken = copy.deepcopy(editor.value)
    broken["components"][0]["type"] = "Nonexistent"
    editor.value = broken

    errors = editor.validate()
    assert len(errors) == 1
    assert "Nonexistent" in errors[0]["message"]


def test_apply_rebuilds_the_project(project):
    editor = project.editor()
    n_components = len(project.component_list())
    name = project.component_list()[0].parameter("name").value

    edited = copy.deepcopy(editor.value)
    edited["components"][0]["description"] = "edited through the widget"
    editor.value = edited

    result = editor.apply()

    assert all(not isinstance(item, dict) for item in result)  # check() messages
    assert len(project.component_list()) == n_components  # rebuilt, not doubled
    assert project.component(name).parameter("description").value == (
        "edited through the widget"
    )
    assert project.write_dict() == editor.value


def test_apply_leaves_the_project_untouched_when_invalid(project):
    editor = project.editor()
    before = project.write_dict()

    broken = copy.deepcopy(editor.value)
    broken["components"][0]["int"] = -1
    editor.value = broken

    result = editor.apply()

    assert result == editor.validate()
    assert project.write_dict() == before


def test_apply_can_target_another_project(project):
    sim = project._sim_
    other = sim.new_project("other")
    editor = project.editor()

    editor.apply(other)

    assert len(other.component_list()) == len(project.component_list())
    assert other.parameter("name").value == project.parameter("name").value


def test_apply_without_a_project_is_an_error():
    editor = ProjectEditor(value={"name": "p", "components": []})
    with pytest.raises(ValueError):
        editor.apply()
