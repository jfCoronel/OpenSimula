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
    for name in ("value", "schema", "errors", "geometry"):
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
    # The 3D view: loaded on demand, and framed for the model rather than for
    # plotly's unit cube, whose default camera crops a building.
    assert "plotly.js-gl3d-dist-min" in source
    assert "import(PLOTLY_URL)" in source
    assert "defaultCamera" in source
    # Filtering by space is what brings interior partitions into view. The rest
    # of the building stays as a wireframe, which keeps the scene bounds and
    # the context, and hoverinfo "skip" keeps it out of the way of the mouse.
    assert "splitMeshes" in source
    assert "axisRanges" in source
    assert "ghostTrace" in source
    assert "plotly_click" in source
    # react() puts back its own camera unless handed one. The angle to hand it
    # is captured on real mouse input and read off the live scene: listening to
    # plotly instead meant a redraw reported its own camera as the user's, and
    # every click then snapped back to the opening view.
    assert "rememberCamera" in source
    # One plot call per selection, carrying the camera with it. Two calls draw
    # the rebuilt default angle before the second one corrects it, and the jump
    # is plainly visible.
    assert "plotly.update(" in source
    assert "highlightGeometry" in source
    assert "restoreCamera" in source
    assert "getCamera" in source
    assert 'addEventListener("mouseup"' in source


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


@pytest.fixture
def building():
    sim = osm.Simulation()
    sim.console_print = False
    project = sim.new_project("hulc")
    project.read_json(str(ROOT / "jupyter_test/edificio_curso_hulc.json"))
    return project


def test_polygons_carry_their_component_and_spaces(building):
    """A viewer cannot offer to show one space at a time unless the geometry
    says which space each polygon belongs to."""
    geometry = building.geometry_dict()
    known = {c.parameter("name").value for c in building.component_list("Space")}

    assert len(geometry["meshes"]) > 0
    assert set(geometry["spaces"]) <= known
    for mesh in geometry["meshes"]:
        assert building.component(mesh["component"]) is not None
        assert mesh["spaces"], f"{mesh['name']} belongs to no space"
        assert set(mesh["spaces"]) <= known


def test_interior_surfaces_bound_two_spaces(building):
    interior = [
        mesh
        for mesh in building.geometry_dict()["meshes"]
        if mesh["surface_type"] == "INTERIOR"
        and mesh["component_type"] == "Building_surface"
    ]
    assert interior
    assert all(len(mesh["spaces"]) == 2 for mesh in interior)


def test_openings_inherit_from_their_surface(building):
    meshes = {m["component"]: m for m in building.geometry_dict()["meshes"]}
    openings = [m for m in meshes.values() if m["component_type"] == "Opening"]
    assert openings
    for opening in openings:
        surface = building.component(opening["component"]).get_surface()
        parent = meshes[surface.parameter("name").value]
        assert opening["spaces"] == parent["spaces"]
        assert opening["surface_type"] == parent["surface_type"]


def test_geometry_is_json_serialisable(building):
    """It crosses to the frontend as JSON, so no numpy scalars may survive."""
    blob = json.dumps(building.geometry_dict())
    assert json.loads(blob)["meshes"]


def test_geometry_of_a_project_without_geometry(project):
    assert project.geometry_dict() == {"meshes": [], "spaces": []}


def test_editor_carries_the_geometry(building):
    editor = building.editor()
    assert editor.trait_metadata("geometry", "sync") is True
    assert editor.geometry == building.geometry_dict()


def test_geometry_follows_apply(building):
    """The 3D view shows the project, so it is reloaded when apply() does."""
    editor = building.editor()
    surface = next(
        c
        for c in building.component_list("Building_surface")
        if c.parameter("shape").value == "POLYGON"
    )
    name = surface.parameter("name").value
    before = next(m for m in editor.geometry["meshes"] if m["component"] == name)

    edited = copy.deepcopy(editor.value)
    component = next(c for c in edited["components"] if c.get("name") == name)
    component["x_polygon"] = [x * 2 for x in component["x_polygon"]]
    editor.value = edited
    assert editor.geometry["meshes"] == building.geometry_dict()["meshes"]  # not yet

    editor.apply()

    after = next(m for m in editor.geometry["meshes"] if m["component"] == name)
    assert after["points"] != before["points"]


def test_plotly_figure_can_be_composed(building):
    """show_3D(jupyter=True) used to only draw the figure and drop it, so it
    could not be reused. Not calling show_3D() here: the vedo path opens a
    window and blocks."""
    from opensimula.visual_3D.Environment_3D import Environment_3D

    environment = Environment_3D()
    building.create_3D_environment(environment)
    figure = environment.plotly_figure()

    assert len(figure.data) > 0
    # One mesh and one outline per polygon, plus the ground plane traces.
    assert len(figure.data) >= 2 * len(environment.pol_3D)
