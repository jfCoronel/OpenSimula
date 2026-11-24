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
    "09_water_plant",
    "10_energy_and_comfort",
    "11_dhw_and_solar",
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


def test_the_water_plant_example_heat_pump_first_boiler_as_backup(folder, monkeypatch):
    pro = _simulate(folder, "09_water_plant", monkeypatch, n_time_steps=24 * 21)
    hp = pro.component("heat_pump_generator")
    boiler = pro.component("boiler_generator").variable("Q").values
    assert boiler.sum() > 0
    # the boiler only helps the heat pump at full load, and never cools
    assert np.all(hp.variable("F_load").values[boiler > 0] == pytest.approx(1))
    assert np.all(boiler >= 0)
    # the mixing valve of the south circuit: never above 45 °C
    assert pro.component("south_circuit").variable("T_supply").values.max() <= 45 + 1e-9


def test_the_fan_coil_gives_the_plant_its_latent_heat(folder, monkeypatch):
    # a week of July: the coil dehumidifies; the plant gets sensible + latent heat
    monkeypatch.chdir(folder)
    data = json.loads((folder / "07_fan_coil.json").read_text(encoding="utf-8"))
    data["initial_time"] = "01/07/2001 00:00:00"
    data["n_time_steps"] = 24 * 7
    sim = osm.Simulation()
    sim.console_print = False
    pro = sim.new_project("p")
    pro.read_dict(data)
    pro.simulate(progress=lambda i, n: None)
    coil = pro.component("fan_coil")
    cooling = np.isin(coil.variable("state").values, [-1, -2])
    Q_total = coil.variable("Q_total").values
    assert cooling.sum() > 10
    assert coil.variable("Q_latent").values[cooling].sum() > 0
    Q_coils = pro.component("water_system").variable("Q_loads").values
    assert np.allclose(Q_coils[cooling], Q_total[cooling], rtol=1e-6, atol=1e-6)
    # the water leaves the coil warmer by the total heat, from the plant's temperature
    T_iw, T_ow = coil.variable("T_iw").values, coil.variable("T_ow").values
    flow = coil.parameter("cooling_water_flow").value / 1000  # m³/s
    rhocp = coil.props["RHOCP_W"](T_iw[cooling])
    assert np.allclose(T_ow[cooling] - T_iw[cooling], Q_total[cooling] / (flow * rhocp))
    T_plant = pro.component("water_system").variable("T_supply").values
    assert np.all(np.abs(T_iw[cooling] - T_plant[cooling]) < 2)


def test_the_energy_and_comfort_example_is_09_with_the_indicators(folder, monkeypatch):
    load = lambda n: json.loads((folder / f"{n}.json").read_text(encoding="utf-8"))
    example, water = load("10_energy_and_comfort"), load("09_water_plant")
    assert example["components"][:-2] == water["components"]
    assert [c["type"] for c in example["components"][-2:]] == ["Energy_indicators", "Comfort_indicators"]
    pro = _simulate(folder, "10_energy_and_comfort", monkeypatch, n_time_steps=24 * 7)
    r = pro.component("energy").report()
    assert r.summary["reference_area"] == 96 and r.summary["primary_nren"] > 0
    assert pro.component("comfort").report().summary["hours_counted"] > 0


def test_the_dhw_and_solar_example(folder, monkeypatch):
    pro = _simulate(folder, "11_dhw_and_solar", monkeypatch, n_time_steps=24 * 31)
    dhw = pro.component("dhw")
    demand = np.sum(dhw.variable("Q_demand").values)
    preheat = np.sum(dhw.variable("Q_preheat").values)
    assert np.sum(dhw.variable("Q_unmet").values) == pytest.approx(0, abs=1e-6)
    assert 0.4 < preheat / demand < 0.8  # January
    # the boiler heats only the rest, from the temperature of the solar tank
    boiler = np.sum(pro.component("boiler_generator").variable("Q").values)
    stored = np.sum(pro.component("boiler_plant").variable("delta_U").values)
    assert boiler - stored == pytest.approx(demand - preheat, rel=1e-3)
    r = pro.component("energy").report()
    assert r.annual.loc["DHW", "SOLAR_THERMAL"] > 0 and r.annual.loc["DHW", "NATURAL_GAS"] > 0
