"""Solar_collector: solar thermal DHW with a solar tank and a backup in series."""

import pathlib

import numpy as np
import pytest

import opensimula as osm
from opensimula.cte import dhw_profile_schedules

EXAMPLES = pathlib.Path(osm.__file__).parent / "examples"
MET = str(EXAMPLES / "sevilla.met")


def solar_dhw(area=2.0, volume=150, daily=120, collector=None, solar_plant=None):
    """Collectors heating a solar tank; the DHW is preheated in it and an
    instantaneous gas boiler (variable flow) heats the rest."""
    return {"name": "solar", "time_step": 3600, "simulation_file_met": "sevilla", "components": [
        {"type": "File_met", "name": "sevilla", "file_type": "MET", "file_name": MET},
        {"type": "Solar_collector", "name": "collector", "area": area, "eta_0": 0.75, "a1": 3.5,
         "a2": 0.015, "tilt": 45, "azimuth": 0, "nominal_water_flow": 0.02 * area,
         **(collector or {})},
        {"type": "Pump", "name": "solar_pump", "nominal_water_flow": 0.02 * area, "nominal_power": 30},
        {"type": "HVAC_water_generator", "name": "solar_gen", "equipment": "collector",
         "pump": "solar_pump"},
        {"type": "Water_tank", "name": "solar_tank", "volume": volume, "UA": 1.2},
        {"type": "HVAC_water_system", "name": "solar_plant", "generators": ["solar_gen"],
         "tank": "solar_tank", "heating_water_setpoint": "60", "initial_water_temp": 20,
         **(solar_plant or {})},
        {"type": "Boiler", "name": "boiler", "nominal_heating_capacity": 24000,
         "nominal_efficiency": 0.92, "nominal_water_flow": 0.3},
        {"type": "HVAC_water_generator", "name": "boiler_gen", "equipment": "boiler"},
        {"type": "HVAC_water_system", "name": "boiler_plant", "generators": ["boiler_gen"],
         "total_water_volume": 5, "heating_water_setpoint": "60", "flow_control": "VARIABLE"},
        *dhw_profile_schedules("profile"),
        {"type": "DHW_demand", "name": "dhw", "water_system": "boiler_plant",
         "preheat_system": "solar_plant", "input_variables": ["f = profile.values"],
         "volume_flow": f"{daily} * f"},
        {"type": "Energy_indicators", "name": "energy"},
    ]}


def simulate(data, start="01/01/2001 00:00:00", days=7):
    data["initial_time"] = start
    data["n_time_steps"] = 24 * days
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


def collector(**parameters):
    sim = osm.Simulation()
    pro = sim.new_project("p")
    c = pro.new_component("Solar_collector", "c")
    c.set_parameters(parameters)
    c.props = sim.props
    c.T_a, c.G_eff, c.G = 20.0, 1000.0, 1000.0
    return c


def test_useful_heat_of_the_collector():
    # at the mean temperature of the air and normal incidence: eta_0 · A · G
    c = collector(area=2, eta_0=0.8, a1=4, a2=0.02)
    assert c.get_useful_heat(20, 1e6) == pytest.approx(1600, rel=1e-4)
    # the mean temperature of the fluid satisfies the EN ISO 9806 equation
    flow, T_in = 0.04, 50
    Q = c.get_useful_heat(T_in, flow)
    mc = c.props["RHOCP_W"](T_in) / 1000 * flow
    x = T_in + Q / (2 * mc) - 20
    assert Q == pytest.approx(2 * (0.8 * 1000 - 4 * x - 0.02 * x**2), rel=1e-9)
    # a heat exchanger gives less; colder than needed or no sun: nothing
    assert collector(exchanger_effectiveness=0.7).get_useful_heat(T_in, flow) < \
        collector().get_useful_heat(T_in, flow)
    assert c.get_useful_heat(200, flow) == 0
    c.G_eff = 0
    assert c.get_useful_heat(20, flow) == 0


def test_solar_fraction_and_balance_of_a_year():
    pro = simulate(solar_dhw(), days=365)
    demand = values(pro, "dhw", "Q_demand").sum()
    preheat = values(pro, "dhw", "Q_preheat").sum()
    assert values(pro, "dhw", "Q_unmet").sum() == pytest.approx(0, abs=1e-3)
    assert 0.6 < preheat / demand < 0.85  # Sevilla, 2 m², 150 l, 120 l/day
    p = "solar_plant"
    balance = (values(pro, p, "Q_generators") + values(pro, p, "Q_loads") + values(pro, p, "Q_loss")
               + values(pro, p, "Q_pump") - values(pro, p, "delta_U"))
    assert abs(balance.sum()) < 1e-4 * values(pro, p, "Q_generators").sum()
    assert values(pro, "solar_tank", "temperature").max() <= 90 + 1e-6
    # the solar heat is renewable final energy of DHW, not in the final energy totals
    r = pro.component("energy").report()
    solar = values(pro, "solar_gen", "Q").sum() / 1000
    assert r.annual.loc["DHW", "SOLAR_THERMAL"] == pytest.approx(solar)
    assert r.annual.loc["DHW", "TOTAL"] == pytest.approx(
        r.annual.loc["DHW", "NATURAL_GAS"] + r.annual.loc["DHW", "ELECTRICITY"])
    assert r.indicators.loc["DHW", "Primary ren [kWh]"] >= solar


def test_maximum_temperature_of_the_tank():
    # big field, small tank, no use: the tank stops at the maximum temperature
    pro = simulate(solar_dhw(area=10, volume=50, daily=0, collector={"max_temperature": 70}),
                   start="01/07/2001 00:00:00", days=3)
    T = values(pro, "solar_tank", "temperature")
    assert T.max() == pytest.approx(70, abs=1e-6)


def test_backup_only_heats_from_the_preheat_temperature():
    pro = simulate(solar_dhw(), start="01/07/2001 00:00:00", days=3)
    draw = values(pro, "dhw", "Q_demand") > 0
    T_pre = values(pro, "dhw", "T_preheat")[draw]
    T_m = values(pro, "dhw", "T_mains")[draw]
    share = np.clip((T_pre - T_m) / (60 - T_m), 0, 1)
    Q = values(pro, "dhw", "Q_demand")[draw]
    assert np.allclose(values(pro, "dhw", "Q_preheat")[draw], Q * share)
    # the boiler heats the rest: the water enters it at the preheat temperature
    # (less the heat stored in its 5 l of water, warmed up from 20 °C at the start)
    gen = values(pro, "boiler_plant", "Q_generators") - values(pro, "boiler_plant", "delta_U")
    assert gen.sum() == pytest.approx((Q * (1 - share)).sum(), rel=1e-3)


def test_collector_needs_a_tank():
    data = solar_dhw()
    for c in data["components"]:
        if c["name"] == "solar_plant":
            del c["tank"]
    sim = osm.Simulation()
    sim.console_print = False
    pro = sim.new_project("p")
    pro.read_dict(data)
    assert any("Solar_collector" in m.text for m in pro.check() if m.level == "ERROR")
