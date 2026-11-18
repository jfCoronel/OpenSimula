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
]


@pytest.fixture(scope="module")
def folder(tmp_path_factory):
    """The examples copied by the command, as a user gets them."""
    target = tmp_path_factory.mktemp("examples")
    assert gui.copy_examples(str(target)) == 0
    return target


def test_the_command_copies_every_example_and_the_weather(folder):
    assert sorted(p.stem for p in folder.glob("*.json")) == NAMES
    assert (folder / "sevilla.met").is_file()


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
    for name in NAMES:
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
