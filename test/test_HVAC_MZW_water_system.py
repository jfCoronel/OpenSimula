"""HVAC_MZW_system connected to water systems (four pipes): a VAV unit with reheat
serving two Load_space zones, a hot water plant with a boiler (heating coil and
reheat) and a chilled water plant with a chiller. Two weeks of January and two of
July."""

import json
import pathlib

import numpy as np
import pytest

import opensimula as osm

EXAMPLES = pathlib.Path(osm.__file__).parent / "examples"
PROJECT = pathlib.Path(__file__).parent / "mzw_four_pipe.json"


def simulate(start, days=14, plant=None, **ahu):
    d = json.loads(PROJECT.read_text(encoding="utf-8"))
    d["initial_time"] = start
    d["n_time_steps"] = 24 * days
    for c in d["components"]:
        if c["type"] in ("File_met", "File_data"):
            c["file_name"] = str(EXAMPLES / c["file_name"])
        if c["name"] == "ahu":
            c.update(ahu)
        if plant and c["name"] in plant:
            c.update(plant[c["name"]])
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


@pytest.fixture(scope="module")
def winter():
    return simulate("01/01/2001 00:00:00")


@pytest.fixture(scope="module")
def summer():
    return simulate("01/07/2001 00:00:00")


def test_reheat_load_goes_to_the_hot_water_plant(winter):
    reheat = values(winter, "ahu", "Q_reheat_0") + values(winter, "ahu", "Q_reheat_1")
    assert reheat.sum() > 0
    # the coils cool the hot water by what they give to the air: heating coil + reheat
    heating_coil = np.where(np.isin(values(winter, "ahu", "state"), [1, 2]),
                            values(winter, "ahu", "Q_sensible"), 0)
    Q_coils = values(winter, "hot_water", "Q_coils")
    assert np.allclose(-Q_coils, reheat + heating_coil, rtol=1e-6, atol=1e-6)
    assert values(winter, "boiler_generator", "Q").sum() > 0
    assert np.all(values(winter, "hot_water", "coils_flow")[reheat > 0] > 0)


def test_cooling_load_goes_to_the_chilled_water_plant(summer):
    Q_coils = values(summer, "chilled_water", "Q_coils")
    cooling = np.isin(values(summer, "ahu", "state"), [-1, -2])
    assert cooling.sum() > 0
    assert np.all(Q_coils[cooling] > 0)
    assert np.all(Q_coils[~cooling] == 0)
    assert values(summer, "chiller_generator", "Q").min() < 0
    # chilled water at the setpoint while there is load
    T = values(summer, "chilled_water", "T_generators_out")
    assert np.allclose(T[cooling], 7, atol=0.5)


def test_zones_held_while_open(summer):
    open_ = values(summer, "office_hours", "values") > 0
    for zone in ("zone_south", "zone_north"):
        T = values(summer, zone, "temperature")[open_]
        assert np.mean(np.abs(T - 21) < 1) > 0.9


def test_plant_off_no_cooling():
    # a coil fed by a plant that is off gives nothing
    pro = simulate("01/07/2001 00:00:00", days=3, plant={"chilled_water": {"system_on_off": "0"}})
    assert np.all(~np.isin(values(pro, "ahu", "state"), [-1, -2]))
    assert np.all(values(pro, "chiller_generator", "Q") == 0)


def test_vav_with_the_return_equal_to_the_supply():
    # no outdoor air: the fraction from the flow balance may be -1e-16 by rounding,
    # which made the mixed air humidity negative (psychrolib error)
    pro = simulate("01/07/2001 00:00:00", days=10, return_air_flow=0.8)
    assert np.all(values(pro, "ahu", "outdoor_air_fraction") >= 0)


def test_no_cooling_from_a_plant_in_heating_mode():
    # the hot water plant (SCHEDULE_CONTROL, heating) stays at 20 °C in summer: the coil
    # cooled with it while the plant discarded the load (energy from nowhere)
    pro = simulate("01/07/2001 00:00:00", days=3, cooling_water_system="hot_water")
    assert np.all(~np.isin(values(pro, "ahu", "state"), [-1, -2]))
    assert np.all(values(pro, "hot_water", "Q_coils") <= 0)
