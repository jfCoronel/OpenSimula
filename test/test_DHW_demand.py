"""DHW_demand: domestic hot water served by water plants and circuits."""

import json
import pathlib

import numpy as np
import pytest

import opensimula as osm
from opensimula.components.DHW_demand import CTE_HOURLY_PROFILE

EXAMPLES = pathlib.Path(osm.__file__).parent / "examples"
MZW = pathlib.Path(__file__).parent / "mzw_four_pipe.json"
MET = str(EXAMPLES / "sevilla.met")


def run(data, start="01/01/2001 00:00:00", days=7):
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


def instantaneous(dhw=None, plant=None):
    """A gas boiler giving DHW only, with a small water volume (no tank)."""
    return {"name": "dhw", "time_step": 3600, "simulation_file_met": "sevilla", "components": [
        {"type": "File_met", "name": "sevilla", "file_type": "MET", "file_name": MET},
        {"type": "Boiler", "name": "boiler", "nominal_heating_capacity": 24000,
         "nominal_efficiency": 0.92, "nominal_water_flow": 0.3},
        {"type": "Pump", "name": "pump", "nominal_water_flow": 0.3, "nominal_power": 50},
        {"type": "HVAC_water_generator", "name": "gen", "equipment": "boiler", "pump": "pump"},
        {"type": "HVAC_water_system", "name": "plant", "generators": ["gen"],
         "total_water_volume": 5, "heating_water_setpoint": "60", "pump_operation": "ON_LOAD",
         **(plant or {})},
        {"type": "DHW_demand", "name": "dhw", "water_system": "plant", "daily_volume": "120",
         **(dhw or {})},
        {"type": "Energy_indicators", "name": "energy"},
    ]}


def values(pro, component, variable):
    return np.asarray(pro.component(component).variable(variable).values)


def test_demand_from_volume_profile_and_mains():
    pro = run(instantaneous(dhw={"distribution_losses": 0.1}), start="01/07/2001 00:00:00", days=2)
    f = np.array(CTE_HOURLY_PROFILE * 2) / sum(CTE_HOURLY_PROFILE)
    assert np.allclose(values(pro, "dhw", "volume_flow"), 120 * f)
    assert np.all(values(pro, "dhw", "T_mains") == 21)  # Sevilla in July (Anejo G)
    props = pro.component("dhw").props
    rho_cp = props["RHOCP_W"](60) / 1000
    expected = rho_cp * 120 * f / 3600 * (60 - 21) * 1.1
    assert np.allclose(values(pro, "dhw", "Q_demand"), expected)
    assert np.allclose(values(pro, "dhw", "Q_supplied"), expected)
    assert values(pro, "dhw", "Q_unmet").sum() == 0
    # the water taken from the plant carries that heat from T_supply to T_mains
    supplied = expected > 0
    T_s = values(pro, "dhw", "T_supply")
    rho_cp_s = np.array([props["RHOCP_W"](t) / 1000 for t in T_s])
    assert np.allclose(values(pro, "dhw", "water_flow")[supplied],
                       expected[supplied] / (rho_cp_s[supplied] * (T_s[supplied] - 21)))


def test_dhw_only_plant_energy_is_dhw():
    pro = run(instantaneous())
    assert np.allclose(values(pro, "plant", "Q_dhw"), values(pro, "plant", "Q_coils"))
    heating = values(pro, "gen", "Q") > 0
    assert heating.sum() > 0
    share = pro.component("plant").dhw_share()
    assert np.allclose(share[heating], 1)
    r = pro.component("energy").report(water_transport="BY_MODE")
    assert r.annual.loc["DHW", "NATURAL_GAS"] == pytest.approx(
        values(pro, "gen", "fuel_power").sum() / 1000)
    assert "HEATING" not in r.annual.index
    # the pump of the generator, by the mode of the plant: DHW while it heats
    plant_heats = values(pro, "plant", "mode") == 1
    assert r.annual.loc["DHW", "ELECTRICITY"] == pytest.approx(
        (values(pro, "gen", "pump_power")[plant_heats].sum() + values(pro, "gen", "power").sum()) / 1000)


def test_combined_plant_splits_heating_and_dhw():
    data = json.loads(MZW.read_text(encoding="utf-8"))
    data["components"] += [
        {"type": "DHW_demand", "name": "dhw", "water_system": "hot_water", "daily_volume": "200"},
    ]
    pro = run(data)
    gen = pro.component("boiler_generator")
    fuel = values(pro, "boiler_generator", "fuel_power")
    uses = gen.get_energy_use()
    gas = {u.service: u.values for u in uses if u.carrier == gen.parameter("equipment").component
           .parameter("fuel").value}
    assert gas["HEATING"].sum() > 0 and gas["DHW"].sum() > 0
    assert np.allclose(gas["HEATING"] + gas["DHW"], fuel)
    # DHW share: the DHW load over the load of coils and processes, while heating
    Q_dhw, Q_coils = values(pro, "hot_water", "Q_dhw"), values(pro, "hot_water", "Q_coils")
    heating = (Q_coils < 0) & (values(pro, "hot_water", "mode") == 1)
    share = pro.component("hot_water").dhw_share()
    assert np.allclose(share[heating], np.clip(Q_dhw[heating] / Q_coils[heating], 0, 1))
    assert np.allclose(gas["DHW"], fuel * share)


def test_dhw_through_a_circuit_reaches_the_plant():
    data = json.loads((EXAMPLES / "10_energy_and_comfort.json").read_text(encoding="utf-8"))
    data["components"].append({"type": "DHW_demand", "name": "dhw", "water_system": "north_circuit",
                               "daily_volume": "120", "minimum_temperature": 40})
    pro = run(data)
    assert values(pro, "dhw", "Q_supplied").sum() > 0
    # the circuit passes the DHW part of its load to the plant
    Q_dhw_c, Q_coils_c = values(pro, "north_circuit", "Q_dhw"), values(pro, "north_circuit", "Q_coils")
    Q_plant = values(pro, "north_circuit", "Q_plant")
    part = np.divide(Q_plant * Q_dhw_c, Q_coils_c, out=np.zeros_like(Q_plant), where=Q_coils_c != 0)
    on = values(pro, "water_plant", "mode") == 1
    assert np.allclose(values(pro, "water_plant", "Q_dhw")[on], part[on], atol=1e-6)
    r = pro.component("energy").report()
    assert r.annual.loc["DHW", "TOTAL"] > 0


def test_not_supplied_when_the_plant_is_off_or_too_cold():
    pro = run(instantaneous(plant={"system_on_off": "0"}), days=1)
    assert values(pro, "dhw", "Q_supplied").sum() == 0
    assert values(pro, "dhw", "Q_unmet").sum() == pytest.approx(values(pro, "dhw", "Q_demand").sum())
    assert values(pro, "dhw", "low_temperature").sum() == 0  # off, not cold
    cold = run(instantaneous(plant={"heating_water_setpoint": "40"}), days=1)
    assert values(cold, "dhw", "Q_supplied").sum() == 0
    assert values(cold, "dhw", "low_temperature").sum() > 0


def test_checks():
    data = instantaneous(dhw={"hourly_profile": [1, 2, 3]})
    sim = osm.Simulation()
    sim.console_print = False
    pro = sim.new_project("p")
    pro.read_dict(data)
    assert any("hourly_profile" in m.text for m in pro.check() if m.level == "ERROR")
