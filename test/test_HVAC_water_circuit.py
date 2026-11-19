"""HVAC_water_circuit: secondary circuits fed by a water system. A boiler plant at 60 °C;
the load of the circuits is their own heat loss (no coils), and their pumps give no
heat to the water, so that the steady state can be checked exactly."""

import json
import pathlib

import numpy as np
import pytest

import opensimula as osm

EXAMPLES = pathlib.Path(osm.__file__).parent / "examples"
MET = str(EXAMPLES / "sevilla.met")


def circuit(name, flow, **parameters):
    return [{"type": "Pump", "name": f"{name}_pump", "nominal_water_flow": flow, "nominal_power": 40,
             "power_to_heat_fraction": 0},
            {"type": "HVAC_water_circuit", "name": name, "water_system": "plant",
             "pumps": [f"{name}_pump"]} | parameters]


def plant(circuits, n=48, **plant_parameters):
    components = [
        {"type": "File_met", "name": "sevilla", "file_type": "MET", "file_name": MET},
        {"type": "Boiler", "name": "boiler", "nominal_heating_capacity": 15000, "nominal_water_flow": 0.3,
         "max_supply_temperature": 90},
        {"type": "HVAC_water_generator", "name": "generator", "equipment": "boiler"},
        {"type": "HVAC_water_system", "name": "plant", "generators": ["generator"],
         "heating_water_setpoint": "60", "initial_water_temp": 60, "total_water_volume": 100}
        | plant_parameters,
    ]
    for c in circuits:
        components += c
    sim = osm.Simulation()
    sim.console_print = False
    pro = sim.new_project("p")
    pro.read_dict({"name": "p", "n_time_steps": n, "simulation_file_met": "sevilla",
                   "components": components})
    errors = [m.text for m in sim.message_list() if m.level == "ERROR"]
    assert not errors, errors
    pro.simulate(progress=lambda i, n: None)
    return pro


def last(pro, component, variable):
    return pro.component(component).variable(variable).values[-1]


def rho_cp(pro, T):
    return pro._sim_.props["RHOCP_W"](T) / 1000


def test_circuit_with_a_mixing_valve():
    pro = plant([circuit("floor", 0.2, heating_supply_setpoint="40", Q_loss="-3000")])
    T_plant = last(pro, "floor", "T_plant")
    assert T_plant == pytest.approx(60, abs=0.01)
    assert last(pro, "floor", "T_supply") == pytest.approx(40)
    T_return = last(pro, "floor", "T_return")
    assert 40 - T_return == pytest.approx(3000 / (rho_cp(pro, 40) * 0.2))
    # water from the plant, mixed with the return, gives the supply
    plant_flow = last(pro, "floor", "plant_flow")
    assert plant_flow == pytest.approx(0.2 * (T_return - 40) / (T_return - T_plant))
    assert last(pro, "floor", "mixing_flow") == pytest.approx(0.2 - plant_flow)
    # the plant gives the load of the circuit
    assert last(pro, "floor", "Q_plant") == pytest.approx(-3000)
    assert last(pro, "plant", "Q_coils") == pytest.approx(-3000)
    assert last(pro, "generator", "Q") == pytest.approx(3000, rel=1e-3)
    assert last(pro, "floor", "pumps_power") == pytest.approx(40)


def test_circuit_without_setpoint_gets_the_water_of_the_plant():
    pro = plant([circuit("ahu", 0.3, Q_loss="-3000")])
    assert last(pro, "ahu", "T_supply") == pytest.approx(60, abs=0.01)
    assert last(pro, "ahu", "plant_flow") == pytest.approx(0.3)
    assert last(pro, "ahu", "mixing_flow") == pytest.approx(0)


def test_two_circuits_at_different_temperatures_from_one_boiler():
    pro = plant([circuit("floor", 0.2, heating_supply_setpoint="35", Q_loss="-2000"),
                 circuit("radiators", 0.1, heating_supply_setpoint="55", Q_loss="-4000")])
    assert last(pro, "floor", "T_supply") == pytest.approx(35)
    assert last(pro, "radiators", "T_supply") == pytest.approx(55)
    assert last(pro, "plant", "Q_coils") == pytest.approx(-6000)
    assert last(pro, "generator", "Q") == pytest.approx(6000, rel=1e-3)
    assert last(pro, "plant", "coils_flow") == pytest.approx(
        last(pro, "floor", "plant_flow") + last(pro, "radiators", "plant_flow"))


def test_circuit_off_takes_nothing():
    pro = plant([circuit("floor", 0.2, Q_loss="-3000", system_on_off="0")], n=6)
    for v in ("water_flow", "plant_flow", "Q_plant", "pumps_power"):
        assert np.all(pro.component("floor").variable(v).values == 0)
    assert np.all(pro.component("plant").variable("Q_coils").values == 0)


def test_water_volume_of_the_circuit():
    # starting cold, the plant must also heat the water of the circuit
    with_volume = plant([circuit("floor", 0.2, heating_supply_setpoint="40", Q_loss="-3000",
                                 water_volume=500)], n=48)
    dU = with_volume.component("floor").variable("delta_U").values
    assert np.all(np.abs(dU[1:]) < 1e3)
    # in the steady state nothing is stored
    assert dU[-1] == pytest.approx(0, abs=1)


def test_fan_coil_on_a_circuit():
    """Example 07 against the office of example 08, the fan coil on a circuit at 40 °C
    fed by the loop at 50 °C."""
    d = json.loads((EXAMPLES / "07_fan_coil.json").read_text(encoding="utf-8"))
    e08 = json.loads((EXAMPLES / "08_load_records.json").read_text(encoding="utf-8"))
    building = {"Material", "Construction", "Glazing", "Opening_type", "Building", "Space_type",
                "Space", "Building_surface", "Opening", "Solar_surface"}
    comps = [c for c in d["components"] if c["type"] not in building]
    comps += [dict(c) for c in e08["components"] if c["name"] in ("load_record", "office")]
    for c in comps:
        if c["type"] in ("File_met", "File_data"):
            c["file_name"] = str(EXAMPLES / c["file_name"])
        if c["name"] == "fan_coil":
            c.update(heating_water_system="fan_coils", cooling_water_system="fan_coils")
    comps += circuit("fan_coils", 0.2, water_system="water_system", heating_supply_setpoint="40",
                     cooling_supply_setpoint="10")
    d["components"] = comps
    d["n_time_steps"] = 24 * 14
    sim = osm.Simulation()
    sim.console_print = False
    pro = sim.new_project("p")
    pro.read_dict(d)
    assert not [m.text for m in sim.message_list() if m.level == "ERROR"]
    pro.simulate(progress=lambda i, n: None)
    v = lambda c, n: pro.component(c).variable(n).values
    heating = v("fan_coil", "state") == 1
    cooling = v("fan_coil", "state") == -1
    assert heating.sum() > 0 and cooling.sum() > 0
    assert np.allclose(v("fan_coils", "T_supply")[heating], 40, atol=0.1)
    assert np.allclose(v("fan_coils", "T_supply")[cooling], 10, atol=0.1)
    # the loop sees the load of the circuit, the circuit that of the coil
    assert np.all(v("fan_coils", "Q_coils")[heating] < 0)
    assert np.allclose(v("water_system", "Q_coils")[heating], v("fan_coils", "Q_plant")[heating])
