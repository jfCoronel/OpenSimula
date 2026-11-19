"""The examples shipped with the package and `opensimula examples`."""

import json

import numpy as np
import pytest

import opensimula as osm
from opensimula import gui

NAMES = [
    "01_schedules",
    "02_weather",
    "03_walls",
    "04_windows_and_gains",
    "05_ideal_system",
    "06_dx_system",
    "07_fan_coil",
    "08_load_records",
]
# 01-07 build on each other; 08 starts again from 06 without the building
PROGRESSIVE = NAMES[:7]


@pytest.fixture(scope="module")
def folder(tmp_path_factory):
    """The examples copied by the command, as a user gets them."""
    target = tmp_path_factory.mktemp("examples")
    assert gui.copy_examples(str(target)) == 0
    return target


def test_the_command_copies_every_example_and_the_weather(folder):
    assert sorted(p.stem for p in folder.glob("*.json")) == NAMES
    assert (folder / "sevilla.met").is_file()
    assert (folder / "office_loads.csv").is_file()


def test_the_command_keeps_edited_files(folder, capsys):
    edited = folder / "01_schedules.json"
    original = edited.read_text()
    edited.write_text(original.replace("Office hours", "Edited"))
    gui.copy_examples(str(folder))
    assert "Edited" in edited.read_text()
    assert "already there" in capsys.readouterr().out
    edited.write_text(original)


def _simulate(folder, name, monkeypatch, n_time_steps=None):
    monkeypatch.chdir(folder)
    data = json.loads((folder / f"{name}.json").read_text(encoding="utf-8"))
    if n_time_steps:
        data["n_time_steps"] = n_time_steps
    sim = osm.Simulation()
    sim.console_print = False
    pro = sim.new_project(name)
    pro.read_dict(data)
    problems = [m.text for m in sim.message_list() if m.level in ("ERROR", "WARNING")]
    assert problems == []
    pro.simulate()
    return pro


@pytest.mark.parametrize("name", NAMES)
def test_every_example_loads_and_simulates_a_week(folder, name, monkeypatch):
    pro = _simulate(folder, name, monkeypatch, n_time_steps=168)
    assert pro.parameter("description").value
    office = pro.component("office")
    if office is not None:  # from 03 on
        T = office.variable("temperature").values
        assert np.all(np.isfinite(T)) and 0 < T.min() and T.max() < 80


def test_each_example_adds_to_the_previous_one(folder):
    """Progressive: the components of one are, by name, in the next one."""
    previous = set()
    for name in PROGRESSIVE:
        data = json.loads((folder / f"{name}.json").read_text(encoding="utf-8"))
        names = {c["name"] for c in data["components"]}
        # the empty space type of 03 is replaced by the office use in 04,
        # and the ideal and DX systems by the next system
        dropped = previous - names - {"empty", "ideal_system", "heat_pump", "dx_system"}
        assert dropped == set(), name
        previous = names


@pytest.mark.parametrize("name", ["05_ideal_system", "07_fan_coil"])
def test_the_systems_hold_the_office_setpoints(folder, name, monkeypatch):
    pro = _simulate(folder, name, monkeypatch)
    T = pro.component("office").variable("temperature").values
    open_ = pro.component("office_hours").variable("values").values > 0
    assert open_.sum() > 2000
    assert np.sum((T[open_] > 25.5) | (T[open_] < 19.5)) < 10


def test_the_load_records_example_is_06_without_the_building(folder):
    names = lambda n: {c["name"]: c["type"] for c in json.loads((folder / f"{n}.json").read_text(encoding="utf-8"))["components"]}
    building = {"Material", "Construction", "Glazing", "Opening_type", "Building", "Space_type",
                "Space", "Building_surface", "Opening", "Solar_surface"}
    kept = {n for n, t in names("06_dx_system").items() if t not in building}
    example = names("08_load_records")
    assert set(example) == kept | {"load_record", "office"}
    assert example["office"] == "Load_space"


def test_the_load_records_example_is_close_to_the_building(folder, monkeypatch):
    # the DX system against the record behaves as against the building (example 06)
    results = {}
    for name in ("06_dx_system", "08_load_records"):
        pro = _simulate(folder, name, monkeypatch)
        T = pro.component("office").variable("temperature").values
        open_ = pro.component("office_hours").variable("values").values > 0
        results[name] = (
            pro.component("loads").variable("cooling_load").values.sum(),
            int(np.sum(T[open_] > 25.5)),
        )
    cooling_06, hot_06 = results["06_dx_system"]
    cooling_08, hot_08 = results["08_load_records"]
    assert abs(cooling_08 / cooling_06 - 1) < 0.05
    assert abs(hot_08 - hot_06) < 15
