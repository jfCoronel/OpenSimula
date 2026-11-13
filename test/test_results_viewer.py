import opensimula as osim
import pytest

# A year of a schedule: working days 08:00-13:00 at 100 and 15:00-19:00 at 80,
# weekends at 0, and the whole of August at 0.
project_dic = {
    "name": "Results project",
    "time_step": 3600,
    "n_time_steps": 8760,
    "initial_time": "01/01/2001 00:00:00",
    "components": [
        {
            "type": "Day_schedule",
            "name": "working_day",
            "time_steps": [28800, 18000, 7200, 14400],
            "values": [0, 100, 0, 80, 0],
            "interpolation": "STEP",
        },
        {
            "type": "Day_schedule",
            "name": "holiday_day",
            "time_steps": [],
            "values": [0],
            "interpolation": "STEP",
        },
        {
            "type": "Week_schedule",
            "name": "working_week",
            "days_schedules": ["working_day"] * 5 + ["holiday_day"] * 2,
        },
        {
            "type": "Week_schedule",
            "name": "holiday_week",
            "days_schedules": ["holiday_day"],
        },
        {
            "type": "Year_schedule",
            "name": "year",
            "periods": ["01/08", "01/09"],
            "weeks_schedules": ["working_week", "holiday_week", "working_week"],
        },
    ],
}


def simulated_project():
    sim = osim.Simulation()
    sim.console_print = False
    project = sim.new_project("p")
    project.read_dict(project_dic)
    project.simulate()
    return project


def test_viewer_before_simulation():
    sim = osim.Simulation()
    project = sim.new_project("p")
    project.read_dict(project_dic)
    viewer = project.results()
    assert viewer.catalog == []
    assert "simulate" in viewer.message


def test_viewer_catalog_and_selection():
    project = simulated_project()
    viewer = project.results("year.values")
    names = {c["name"] for c in viewer.catalog}
    assert "year" in names
    assert viewer.period[0].startswith("2001-01-01")
    assert len(viewer.series) == 1
    series = viewer.series[0]
    assert series["slot"] == 0
    assert len(series["x"]) == 8760
    # a variable selected twice is kept once
    viewer.select("year.values")
    assert len(viewer.selection) == 1


def test_viewer_resampling_and_interval():
    project = simulated_project()
    viewer = project.results("year.values")

    viewer.frequency = "monthly"
    viewer.aggregation = "max"
    y = viewer.series[0]["y"]
    assert len(y) == 12
    assert y[0] == 100  # January, working weeks
    assert y[7] == 0  # August, holiday weeks

    viewer.frequency = "daily"
    viewer.aggregation = "sum"
    viewer.interval = ["2001-01-01", "2001-01-07"]
    y = viewer.series[0]["y"]
    assert len(y) == 7
    # 1 January 2001 is a Monday: 5 h at 100 + 4 h at 80
    assert y[0] == pytest.approx(820)
    assert y[5] == 0  # Saturday

    df = viewer.dataframe()
    assert list(df.columns) == ["year.values"]
    assert len(df) == 7


def test_viewer_unknown_variable():
    project = simulated_project()
    viewer = project.results()
    with pytest.raises(ValueError):
        viewer.select("year.value")
    assert viewer.selection == []


def test_viewer_3d_view():
    project = simulated_project()
    viewer = project.results(show_3d=True)
    assert viewer.show_3d
    assert viewer.geometry == {}  # nothing is sent until the view asks for it
    sent = []
    viewer.send = lambda content, buffers=None: sent.append((content, buffers))
    viewer._on_message_(viewer, {"type": "load-3d", "has_plotly": False}, [])
    assert viewer.geometry == {"meshes": [], "spaces": []}  # schedules only
    assert sent[0][0] == {"type": "plotly"}
    assert len(sent[0][1][0]) > 1_000_000  # the plotly bundle
    # a page that already has plotly gets only the geometry
    viewer._on_message_(viewer, {"type": "load-3d", "has_plotly": True}, [])
    assert len(sent) == 1


def test_viewer_surface_colours(monkeypatch):
    monkeypatch.chdir("ASHRAE_140/LOAD_TEST")  # weather path of the case file
    sim = osim.Simulation()
    sim.console_print = False
    project = sim.new_project("600")
    project.read_json("cases/case_600.json")
    project.set_parameters({"n_time_steps": 48})
    project.simulate()
    viewer = project.results()
    viewer.color_variable = "T_s0"
    assert viewer.surface_values == {}  # no geometry until the 3D view is opened
    viewer._on_message_(viewer, {"type": "load-3d", "has_plotly": True}, [])
    values = viewer.surface_values
    assert values["variable"] == "T_s0" and values["unit"] == "°C"
    assert {"south_wall", "south_window_1", "roof_wall"} <= set(values["values"])
    t_mean = values["values"]["south_wall"]
    viewer.color_statistic = "max"
    assert viewer.surface_values["values"]["south_wall"] >= t_mean
    viewer.color_variable = "q_cd0"  # walls only: windows have no value
    assert "south_window_1" not in viewer.surface_values["values"]
    viewer.color_variable = ""
    assert viewer.surface_values == {}


def test_viewer_surface_colours_at_cursor(monkeypatch):
    import numpy as np

    monkeypatch.chdir("ASHRAE_140/LOAD_TEST")
    sim = osim.Simulation()
    sim.console_print = False
    project = sim.new_project("600")
    project.read_json("cases/case_600.json")
    project.set_parameters({"n_time_steps": 48})
    project.simulate()
    viewer = project.results(show_3d=True)
    viewer._on_message_(viewer, {"type": "load-3d", "has_plotly": True}, [])
    viewer.color_variable = "T_s1"
    viewer.color_statistic = "instant"
    values = viewer.surface_values
    names, x = values["names"], values["x"]
    assert "south_window_1" in names and len(x) == 48
    matrix = np.frombuffer(viewer.surface_series, dtype=np.float32).reshape(len(names), len(x))
    wall = project.component("south_wall").variable("T_s1").values
    assert matrix[names.index("south_wall")] == pytest.approx(wall, abs=1e-4)
    # resampled like the charts
    viewer.frequency = "daily"
    assert len(viewer.surface_values["x"]) == 2
    assert len(viewer.surface_series) == 4 * len(names) * 2
    # back to a statistic: no series sent
    viewer.color_statistic = "mean"
    assert viewer.surface_series == b""
