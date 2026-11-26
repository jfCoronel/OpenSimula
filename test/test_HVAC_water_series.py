"""Generators in series at the outlet of a plant with a tank (connection "SERIES")."""

import json
import pathlib

import numpy as np
import pytest

import opensimula as osm

EXAMPLES = pathlib.Path(osm.__file__).parent / "examples"


def example_11(days=31, start="01/01/2001 00:00:00", **change):
    data = json.loads((EXAMPLES / "11_dhw_and_solar.json").read_text(encoding="utf-8"))
    data["initial_time"], data["n_time_steps"] = start, 24 * days
    for c in data["components"]:
        if c["type"] == "File_met":
            c["file_name"] = str(EXAMPLES / "sevilla.met")
        c.update(change.get(c["name"], {}))
    return data


def simulate(data):
    sim = osm.Simulation()
    sim.console_print = False
    pro = sim.new_project("p")
    pro.read_dict(data)
    errors = [m.text for m in sim.message_list() if m.level == "ERROR"]
    assert not errors, errors
    pro.simulate(progress=lambda i, n: None)
    return pro


def values(pro, component, variable):
    return np.asarray(pro.component(component).variable(variable).values, dtype=float)


def test_series_boiler_heats_the_outlet_to_the_setpoint():
    pro = simulate(example_11())
    draw = values(pro, "dhw", "Q_demand") > 0
    T_tank = values(pro, "solar_tank", "temperature")
    Q = values(pro, "boiler_generator", "Q")
    flow = values(pro, "boiler_generator", "water_flow")
    # only when the tank is below the setpoint, with the water drawn, up to 60 °C
    assert np.all(Q[draw & (T_tank >= 60)] == 0)
    heats = Q > 0
    assert heats.sum() > 0
    assert np.allclose(values(pro, "boiler_generator", "T_wo")[heats], 60)
    assert np.allclose(flow[heats], values(pro, "dhw_plant", "secondary_flow")[heats])
    assert np.all(values(pro, "dhw_plant", "T_supply")[draw] >= 60 - 1e-6)
    # the tank gives the rest: its energy balance
    p = "dhw_plant"
    balance = (values(pro, p, "Q_generators") + values(pro, p, "Q_loads") + values(pro, p, "Q_loss")
               + values(pro, p, "Q_pump") - values(pro, p, "delta_U"))
    assert abs(balance.sum()) < 1e-3 * values(pro, p, "Q_generators").sum()
    assert np.allclose(-values(pro, p, "Q_loss"), values(pro, "solar_tank", "Q_loss"))


def test_series_gives_the_same_as_a_preheat_system():
    one = simulate(example_11())
    # the same installation as two plants: solar tank as preheat_system of the boiler plant
    data = example_11(boiler_generator={"connection": "PARALLEL"},
                      dhw_plant={"generators": ["solar_generator"]},
                      dhw={"water_system": "boiler_plant", "preheat_system": "dhw_plant"})
    data["components"].append(
        {"type": "HVAC_water_system", "name": "boiler_plant", "generators": ["boiler_generator"],
         "total_water_volume": 5, "heating_water_setpoint": "60", "initial_water_temp": 60,
         "flow_control": "VARIABLE"})
    two = simulate(data)
    for gen in ("solar_generator", "boiler_generator"):
        assert values(one, gen, "Q").sum() == pytest.approx(values(two, gen, "Q").sum(), rel=0.03)


def test_series_limited_by_its_capacity():
    # (hourly mean loads: a 24 kW boiler is never at full load; 300 W is)
    small = {"nominal_heating_capacity": 300}
    pro = simulate(example_11(days=7, boiler=small))
    Q = values(pro, "boiler_generator", "Q")
    assert Q.max() == pytest.approx(300)
    assert values(pro, "dhw", "Q_unmet").sum() > 0  # the peaks are not met


def test_series_needs_a_tank_and_not_a_collector():
    for change in ({"dhw_plant": {"tank": "not_defined"}},
                   {"solar_generator": {"connection": "SERIES"}}):
        sim = osm.Simulation()
        sim.console_print = False
        pro = sim.new_project("p")
        pro.read_dict(example_11(**change))
        assert any("SERIES" in m.text for m in pro.check() if m.level == "ERROR"), change
