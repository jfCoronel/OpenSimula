"""HVAC_water_generator: the fan coil of example 07 with a boiler or its heat pump,
against the office of example 08 (a Load_space, no building: quick)."""

import json
import pathlib

import numpy as np
import pytest

import opensimula as osm

EXAMPLES = pathlib.Path(osm.__file__).parent / "examples"
BUILDING = {"Material", "Construction", "Glazing", "Opening_type", "Building", "Space_type",
            "Space", "Building_surface", "Opening", "Solar_surface"}
BOILER = {"type": "Boiler", "name": "boiler", "nominal_heating_capacity": 9000,
          "nominal_efficiency": 0.88, "nominal_water_flow": 0.4137,
          "efficiency_expression": "1 + 0.0035 * max(55 - T_wi, 0)", "auxiliary_power": 40}


def fan_coil_project(boiler=False, days=14, **generator):
    """Example 07 with the office of example 08; the first two weeks of January."""
    d = json.loads((EXAMPLES / "07_fan_coil.json").read_text(encoding="utf-8"))
    e08 = json.loads((EXAMPLES / "08_load_records.json").read_text(encoding="utf-8"))
    comps = [c for c in d["components"] if c["type"] not in BUILDING]
    for c in e08["components"]:
        if c["name"] in ("load_record", "office"):
            c = dict(c)
            if c["type"] == "File_data":
                c["file_name"] = str(EXAMPLES / c["file_name"])
            comps.append(c)
    for c in comps:
        if c["type"] == "File_met":
            c["file_name"] = str(EXAMPLES / c["file_name"])
        if c["type"] == "HVAC_water_generator":
            c.update(generator)
            if boiler:
                c["equipment"] = "boiler"
    if boiler:
        comps.append(BOILER)
    d["components"] = comps
    d["n_time_steps"] = 24 * days
    sim = osm.Simulation()
    sim.console_print = False
    pro = sim.new_project("p")
    pro.read_dict(d)
    errors = [m.text for m in sim.message_list() if m.level == "ERROR"]
    assert not errors, errors
    pro.simulate(progress=lambda i, n: None)
    return pro


def values(pro, component, variable):
    return pro.component(component).variable(variable).values


def test_heat_pump_generator_stores_its_operation():
    pro = fan_coil_project()
    Q = values(pro, "generator", "Q")
    assert np.allclose(Q, values(pro, "water_system", "Q_gen"))
    assert np.allclose(values(pro, "generator", "power"), values(pro, "water_system", "generator_power"))
    heating, cooling = Q > 0, Q < 0
    assert heating.sum() > 0 and cooling.sum() > 0
    assert np.all(values(pro, "generator", "state")[heating] == 1)
    assert np.all(values(pro, "generator", "state")[cooling] == -1)
    assert np.all(values(pro, "generator", "fuel_power") == 0)  # electric
    # COP and EER around the nominal ones (3.2 and 3.0), lower at part load
    assert 2 < values(pro, "generator", "efficiency")[heating].mean() < 3.3
    F = values(pro, "generator", "F_load")
    assert np.all(F[Q == 0] == 0) and np.all((F[Q != 0] > 0) & (F[Q != 0] <= 1))


def test_boiler_generator_heats_with_fuel():
    pro = fan_coil_project(boiler=True)
    Q = values(pro, "generator", "Q")
    fuel = values(pro, "generator", "fuel_power")
    eff = values(pro, "generator", "efficiency")
    on = Q > 0
    assert on.sum() > 0
    assert np.all(Q >= 0)  # a boiler only heats
    assert np.allclose(fuel[on], Q[on] / eff[on])
    assert np.all(values(pro, "generator", "power")[on] == 40)  # auxiliary
    # at 50 °C supply the return is below 55 °C: it condenses, above the nominal 88 %
    assert np.all(eff[on] > 0.88) and np.all(eff[on] < 0.97)
    # the office is heated while open (cooling hours are not, there is no cold)
    T = values(pro, "office", "temperature")
    open_ = values(pro, "office_hours", "values") > 0
    assert np.mean(T[open_] >= 19.5) > 0.95


def test_generator_off_gives_nothing():
    pro = fan_coil_project(days=3, system_on_off="0")
    assert np.all(values(pro, "generator", "Q") == 0)
    assert np.all(values(pro, "generator", "on_off") == 0)


def test_one_generator_only_for_now():
    d = {"name": "p", "simulation_file_met": "m", "components": [
        {"type": "File_met", "name": "m", "file_type": "MET", "file_name": str(EXAMPLES / "sevilla.met")},
        {"type": "Chiller_heat_pump", "name": "chiller"},
        {"type": "HVAC_water_generator", "name": "g1", "equipment": "chiller"},
        {"type": "HVAC_water_generator", "name": "g2", "equipment": "chiller"},
        {"type": "HVAC_water_system", "name": "plant", "generators": ["g1", "g2"]},
    ]}
    sim = osm.Simulation()
    sim.console_print = False
    pro = sim.new_project("p")
    pro.read_dict(d)
    assert any("only one generator" in m.text for m in sim.message_list() if m.level == "ERROR")


@pytest.mark.parametrize("old", ["water_thermal_generator", "pump", "design_water_flow"])
def test_old_parameters_are_gone(old):
    sim = osm.Simulation()
    pro = sim.new_project("p")
    plant = pro.new_component("HVAC_water_system", "plant")
    assert old not in plant.parameter_dict()
