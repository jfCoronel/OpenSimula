"""Help of the parameters and variables for the app (opensimula.help): read from the
component pages of the documentation, shipped in help.json, used by the editor schema,
the results viewer and the mkdocs hook that writes the anchors."""

import json
import pathlib
import types

import pytest

import opensimula as osm
from opensimula import help as osm_help
from opensimula.editor.schema import component_types, project_json_schema

DOCS = pathlib.Path(__file__).parent.parent / "mkdocs"
# variables that no component computes yet (always 0): not documented on purpose
UNDOCUMENTED_VARIABLES = {("Opening", "E_ref"), ("Opening", "E_ref_tra"), ("Opening", "debug_f")}


def test_parse_items():
    item = osm_help.parse_item(
        '- **initial_time** [_string_, default = "01/01/2001 00:00:00"]: First instant: '
        "day and hour.")
    assert [n for n, _, _ in item[0]] == ["initial_time"]
    assert item[1] == "First instant: day and hour."
    item = osm_help.parse_item('- **f** [_math_exp_, unit = "W", default = "[1, 2]"]: Power.')
    assert item[0][0][2] == "W" and item[1] == "Power."
    item = osm_help.parse_item("- __Q_sensible__ [W]: Sensible heat.")
    assert item[0] == [("Q_sensible", 2, "W")]
    item = osm_help.parse_item("- **T_mains** (°C), **T_supply** (°C): Mains and supply.")
    assert [n for n, _, _ in item[0]] == ["T_mains", "T_supply"]
    item = osm_help.parse_item("- __T_s0, T_s1__ [°C]: Surface temperatures")
    assert [n for n, _, _ in item[0]] == ["T_s0", "T_s1"]
    item = osm_help.parse_item("- **outside_&lt;zone&gt;** (flag): For each zone.")
    assert item[0][0][0] == "outside_<zone>"
    assert osm_help.parse_item("- A list item that is not a parameter.") is None
    assert osm_help.clean("A `code`, **bold**, _italic_ and [a link](page.md#x).") == \
        "A code, bold, italic and a link."


def test_help_json_is_up_to_date():
    """Rerun `uv run python -m opensimula.help mkdocs` after changing a component page."""
    shipped = json.loads(osm_help.HELP_FILE.read_text(encoding="utf-8"))
    assert shipped == json.loads(json.dumps(osm_help.build(DOCS)))


def test_every_parameter_and_variable_is_documented():
    sim = osm.Simulation()
    sim.console_print = False
    pro = sim.new_project("p")
    missing = []
    for type_name in component_types():
        if type_name == "Test_component":
            continue
        comp = pro.new_component(type_name, f"x_{type_name}")
        for key in comp.parameter_dict():
            if osm_help.parameter_help(type_name, key)[0] is None:
                missing.append((type_name, "parameter", key))
        for key in comp.variable_dict():
            if (type_name, key) not in UNDOCUMENTED_VARIABLES and \
                    osm_help.variable_help(type_name, key)[0] is None:
                missing.append((type_name, "variable", key))
        assert osm_help.component_help(type_name), type_name
    assert missing == []


def test_variables_by_their_pattern():
    text, url = osm_help.variable_help("Water_tank", "T_node_3")
    assert "stratified" in text and url.endswith("#water_tank-var-t_node_1")
    assert osm_help.variable_help("Comfort_indicators", "outside_office")[1].endswith(
        "#comfort_indicators-var-outside_-zone")
    assert osm_help.variable_help("HVAC_MZW_system", "Q_reheat_2")[0]
    assert osm_help.variable_help("Water_tank", "not_a_variable") == (None, None)


def test_the_editor_schema_has_the_help():
    schema = project_json_schema(["DHW_demand"])
    dhw = schema["$defs"]["DHW_demand"]
    assert dhw["x-doc"].endswith("component_list_HVAC_water_systems/#dhw_demand")
    volume = dhw["properties"]["volume_flow"]
    assert volume["description"].startswith("Hot water used")
    assert volume["x-doc"] == osm_help.DOCS_URL + "component_list_HVAC_water_systems/#dhw_demand-volume_flow"
    assert dhw["properties"]["name"]["x-doc"].endswith("component_list/#common-name")


def test_the_results_viewer_sends_the_help():
    from opensimula.editor.results import ResultsViewer

    sim = osm.Simulation()
    sim.console_print = False
    pro = sim.new_project("p")
    pro.read_dict({"name": "p", "n_time_steps": 24, "components": [
        {"type": "Day_schedule", "name": "day", "time_steps": [3600], "values": [0, 1]},
        {"type": "Week_schedule", "name": "week", "days_schedules": ["day"]},
        {"type": "Year_schedule", "name": "year", "periods": [], "weeks_schedules": ["week"]},
    ]})
    pro.simulate(progress=lambda i, n: None)
    viewer = ResultsViewer(pro)
    year = next(c for c in viewer.catalog if c["name"] == "year")
    values = year["variables"][0]
    assert values["name"] == "values" and values["help"]
    assert values["doc"].endswith("component_list_schedules/#year_schedule-var-values")


def test_the_mkdocs_hook_writes_the_anchors():
    import importlib.util

    spec = importlib.util.spec_from_file_location("mkdocs_hooks", DOCS.parent / "mkdocs_hooks.py")
    hooks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hooks)
    page = types.SimpleNamespace(file=types.SimpleNamespace(src_path="component_list_x.md"))
    markdown = "\n".join([
        "### DHW_demand", "#### Parameters",
        '- **volume_flow** [_math_exp_, unit = "l/h", default = "0"]: Hot water used.',
        "#### Variables", "- **T_mains** (°C), **T_supply** (°C): Temperatures."])
    out = hooks.on_page_markdown(markdown, page, None, None).split("\n")
    assert out[2].startswith('- <a id="dhw_demand-volume_flow" class="osm-anchor"></a>**volume_flow**')
    assert 'id="dhw_demand-var-t_mains"' in out[4] and 'id="dhw_demand-var-t_supply"' in out[4]
    other = types.SimpleNamespace(file=types.SimpleNamespace(src_path="user_guide.md"))
    assert hooks.on_page_markdown(markdown, other, None, None) == markdown
