"""Water_tank: storage tanks in a plant (electric water heater) and in a DHW charging
circuit of a heating plant."""

import json
import pathlib

import numpy as np
import pytest

import opensimula as osm
from opensimula.cte import dhw_profile_schedules

EXAMPLES = pathlib.Path(osm.__file__).parent / "examples"
MZW = pathlib.Path(__file__).parent / "mzw_four_pipe.json"
MET = str(EXAMPLES / "sevilla.met")


def simulate(data, start="01/01/2001 00:00:00", days=7):
    data["initial_time"] = start
    data["n_time_steps"] = 24 * days
    for c in data["components"]:
        if c["type"] in ("File_met", "File_data"):
            c["file_name"] = str(EXAMPLES / pathlib.Path(c["file_name"]).name)
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


def dhw(water_system, daily=120):
    return [*dhw_profile_schedules("profile"),
            {"type": "DHW_demand", "name": "dhw", "water_system": water_system,
             "input_variables": ["f = profile.values"], "volume_flow": f"{daily} * f"}]


def water_heater(tank=None):
    """Electric water heater: 1.5 kW resistance and a 100 l tank at 60 °C."""
    return {"name": "heater", "time_step": 3600, "simulation_file_met": "sevilla", "components": [
        {"type": "File_met", "name": "sevilla", "file_type": "MET", "file_name": MET},
        {"type": "Boiler", "name": "resistance", "fuel": "ELECTRICITY",
         "nominal_heating_capacity": 1500, "nominal_efficiency": 1, "nominal_water_flow": 0.05},
        {"type": "HVAC_water_generator", "name": "gen", "equipment": "resistance"},
        {"type": "Water_tank", "name": "tank", "volume": 100, "UA": 1.2, **(tank or {})},
        {"type": "HVAC_water_system", "name": "heater", "generators": ["gen"], "tank": "tank",
         "heating_water_setpoint": "60", "initial_water_temp": 60},
        *dhw("heater"),
        {"type": "Energy_indicators", "name": "energy"},
    ]}


def test_electric_water_heater_balance():
    pro = simulate(water_heater())
    # held at the setpoint, it loses UA·(60 − 20) every hour
    assert np.allclose(values(pro, "tank", "temperature"), 60)
    assert np.allclose(values(pro, "tank", "Q_loss"), 1.2 * 40)
    assert values(pro, "dhw", "Q_unmet").sum() == pytest.approx(0, abs=1e-6)
    electricity = values(pro, "gen", "fuel_power").sum()
    expected = (values(pro, "dhw", "Q_supplied").sum() + values(pro, "tank", "Q_loss").sum()
                + values(pro, "heater", "delta_U").sum())
    assert electricity == pytest.approx(expected, rel=1e-6)
    # all of it is DHW: the losses and the heat stored too
    assert pro.component("heater").is_dhw_only()
    r = pro.component("energy").report()
    assert r.annual.loc["DHW", "ELECTRICITY"] == pytest.approx(electricity / 1000)
    assert "HEATING" not in r.annual.index


def test_ambient_temperature_is_an_expression():
    pro = simulate(water_heater({"input_variables": ["T = sevilla.temperature"],
                                 "ambient_temperature": "T"}), days=2)
    T_out = values(pro, "sevilla", "temperature")
    assert np.allclose(values(pro, "tank", "T_ambient"), T_out)
    assert np.allclose(values(pro, "tank", "Q_loss"), 1.2 * (60 - T_out))


def test_dead_band_of_the_thermostat():
    pro = simulate(water_heater({"dead_band": 5}))
    T = values(pro, "tank", "temperature")
    assert T.min() >= 55 - 1.5 and T.max() <= 60 + 1e-6  # (a draw can go a bit below)
    on = values(pro, "heater", "Q_generators") > 0
    always = simulate(water_heater())
    assert on.sum() < (values(always, "heater", "Q_generators") > 0).sum()
    # it starts when the water, without heating (draw and losses of that hour), would be
    # below 55 °C
    starts = np.flatnonzero(on[1:] & ~on[:-1]) + 1
    C = pro._sim_.props["RHOCP_W"](60) / 1000 * 100 / 3600
    free = T[starts - 1] - (values(pro, "dhw", "Q_demand")[starts]
                            + values(pro, "tank", "Q_loss")[starts]) / C
    assert len(starts) > 0 and np.all(free < 55 + 0.1)


def charging_circuit(plant_on="1", dead_band=0):
    data = json.loads(MZW.read_text(encoding="utf-8"))
    for c in data["components"]:
        if c["name"] == "hot_water":
            c.update({"heating_water_setpoint": "70", "system_on_off": plant_on})
    data["components"] += [
        {"type": "Pump", "name": "charge_pump", "nominal_water_flow": 0.1, "nominal_power": 40},
        {"type": "Water_tank", "name": "tank", "volume": 200, "UA": 1.5, "dead_band": dead_band},
        {"type": "HVAC_water_circuit", "name": "dhw_circuit", "water_system": "hot_water",
         "pumps": ["charge_pump"], "tank": "tank", "tank_setpoint": "60"},
        *dhw("dhw_circuit", 200),
        {"type": "Energy_indicators", "name": "energy"},
    ]
    return data


def test_charging_circuit_balance_and_dhw_share():
    pro = simulate(charging_circuit())
    c = "dhw_circuit"
    balance = (values(pro, c, "Q_loads") + values(pro, c, "Q_loss") + values(pro, c, "Q_pump")
               - values(pro, c, "Q_plant") - values(pro, c, "delta_U"))
    assert np.allclose(balance, 0, atol=1e-6)
    assert np.allclose(values(pro, "tank", "temperature"), 60)
    assert values(pro, "dhw", "Q_unmet").sum() == pytest.approx(0, abs=1e-6)
    # the whole charge is DHW for the plant, which also heats the coils of the zones
    assert pro.component(c).is_dhw_only()
    assert not pro.component("hot_water").is_dhw_only()
    assert np.allclose(values(pro, "hot_water", "Q_dhw"), values(pro, c, "Q_plant"))
    r = pro.component("energy").report()
    assert r.annual.loc["DHW", "TOTAL"] > 0 and r.annual.loc["HEATING", "TOTAL"] > 0


def test_tank_gives_water_while_the_plant_is_off():
    # the plant works only in office hours: at night the tank gives its water and cools
    pro = simulate(charging_circuit(plant_on="f"), days=3)
    off = values(pro, "hot_water", "on_off") == 0
    draws = off & (values(pro, "dhw", "Q_demand") > 0)
    assert values(pro, "dhw", "Q_supplied")[draws].sum() > 0
    assert np.all(values(pro, "dhw_circuit", "plant_flow")[off] == 0)
    T = values(pro, "tank", "temperature")
    assert T[off].min() < 60


def test_charging_circuit_dead_band():
    pro = simulate(charging_circuit(dead_band=5))
    charging = values(pro, "dhw_circuit", "plant_flow") > 0
    always = simulate(charging_circuit())
    assert charging.sum() < (values(always, "dhw_circuit", "plant_flow") > 0).sum()
    T = values(pro, "tank", "temperature")
    assert T.max() <= 60 + 1e-6 and T.min() > 50


# _________________ Stratified tank _________________

def stratified(nodes=6, area=2.0, position=0.5, dead_band=5):
    """One 200 l tank with solar collectors (bottom) and an electric heater (middle)."""
    return {"name": "s", "time_step": 3600, "simulation_file_met": "sevilla", "components": [
        {"type": "File_met", "name": "sevilla", "file_type": "MET", "file_name": MET},
        {"type": "Solar_collector", "name": "collector", "area": area,
         "nominal_water_flow": 0.02 * max(area, 0.5)},
        {"type": "Pump", "name": "solar_pump", "nominal_water_flow": 0.04, "nominal_power": 30},
        {"type": "HVAC_water_generator", "name": "solar_gen", "equipment": "collector",
         "pump": "solar_pump"},
        {"type": "Boiler", "name": "resistance", "fuel": "ELECTRICITY",
         "nominal_heating_capacity": 1500, "nominal_efficiency": 1, "nominal_water_flow": 0.05},
        {"type": "HVAC_water_generator", "name": "heater_gen", "equipment": "resistance"},
        {"type": "Water_tank", "name": "tank", "volume": 200, "UA": 1.5, "number_of_nodes": nodes,
         "backup_position": position, "dead_band": dead_band},
        {"type": "HVAC_water_system", "name": "plant", "generators": ["solar_gen", "heater_gen"],
         "tank": "tank", "heating_water_setpoint": "60", "initial_water_temp": 60},
        *dhw("plant"),
        {"type": "Energy_indicators", "name": "energy"},
    ]}


def tank_component(nodes):
    sim = osm.Simulation()
    pro = sim.new_project("p")
    tank = pro.new_component("Water_tank", "t")
    tank.set_parameters({"volume": 100, "number_of_nodes": nodes})
    tank.pre_simulation(1, 3600)
    return tank


def test_mixing_and_draw_of_the_nodes():
    tank = tank_component(4)
    # a node warmer than the ones above rises: the out of order blocks take their mean
    assert np.allclose(tank.mix([60, 40, 50, 20]), [60, 45, 45, 20])
    assert np.allclose(tank.mix([30, 40, 50, 60]), [45, 45, 45, 45])
    # a draw of half a node in an hour: the top leaves, mains water enters the bottom
    T, T_out = tank.advect(np.array([60.0, 50, 40, 30]), 12.5 / 3600, 10, 3600)
    assert T_out == 60
    assert np.allclose(T, [55, 45, 35, 20])
    # energy: what leaves minus what enters
    assert np.sum(T) * 25 == pytest.approx((60 + 50 + 40 + 30) * 25 - 12.5 * (60 - 10))
    # heat in a node, mixed upwards
    T = tank.add_heat(np.array([50.0, 50, 50, 50]), 2, 1000, 4.18, 3600)
    assert T[0] == pytest.approx(T[2]) and T[3] == 50 and T[0] > 50


def test_stratified_balance_and_solar_fraction():
    results = {}
    for nodes in (1, 6):
        pro = simulate(stratified(nodes), days=365)
        p = "plant"
        balance = (values(pro, p, "Q_generators") + values(pro, p, "Q_loads")
                   + values(pro, p, "Q_loss") + values(pro, p, "Q_pump") - values(pro, p, "delta_U"))
        assert abs(balance.sum()) < 1e-6 * values(pro, p, "Q_generators").sum()
        solar = values(pro, "solar_gen", "Q").sum()
        results[nodes] = solar / (solar + values(pro, "heater_gen", "Q").sum())
        if nodes == 6:
            T = np.array([values(pro, "tank", f"T_node_{i}") for i in range(1, 7)])
            assert np.all(np.diff(T, axis=0) <= 1e-9)  # top warmest
            assert np.allclose(values(pro, "tank", "temperature"), T.mean(axis=0))
            assert values(pro, "dhw", "Q_unmet").sum() < 0.01 * values(pro, "dhw", "Q_demand").sum()
    # with the bottom cold, the collectors give much more
    assert results[6] > results[1] + 0.1


def test_backup_heats_only_above_its_node():
    pro = simulate(stratified(nodes=4, area=0, position=0.5, dead_band=0), days=3)
    T = np.array([values(pro, "tank", f"T_node_{i}") for i in range(1, 5)])
    # thermostat on node 2 (the heater at half height): the nodes above at 60 °C
    assert np.allclose(T[:2, 24:], 60, atol=1e-6)
    # the nodes below get only mains water: colder and colder
    assert T[3, -1] < 30


def test_stratified_tank_in_a_charging_circuit():
    """The DHW tank of the charging circuit stratified (6 nodes, coil in the middle)."""
    data = charging_circuit(dead_band=5)
    for c in data["components"]:
        if c["type"] == "Water_tank":
            c.update({"number_of_nodes": 6, "backup_position": 0.5})
    pro = simulate(data)
    c = "dhw_circuit"
    balance = (values(pro, c, "Q_loads") + values(pro, c, "Q_loss") + values(pro, c, "Q_pump")
               - values(pro, c, "Q_plant") - values(pro, c, "delta_U"))
    assert np.allclose(balance, 0, atol=1e-6)
    T = np.array([values(pro, "tank", f"T_node_{i}") for i in range(1, 7)])
    assert np.all(np.diff(T, axis=0) <= 1e-9)  # top warmest
    # the thermostat on the node of the coil (node 3): from 55 °C up to 60 °C
    assert T[2].max() <= 60 + 1e-6 and T[2, 24:].min() > 55 - 1.5
    # the bottom gets the mains water and is not heated by the coil
    assert T[5].min() < 40
    assert values(pro, "dhw", "Q_unmet").sum() < 0.02 * values(pro, "dhw", "Q_demand").sum()
    # the whole charge is DHW for the plant
    assert np.allclose(values(pro, "hot_water", "Q_dhw"), values(pro, c, "Q_plant"))
