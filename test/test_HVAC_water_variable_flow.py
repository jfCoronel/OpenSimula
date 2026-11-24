"""Variable water flow (flow_control VARIABLE) in plants and circuits."""

import json
import pathlib

import numpy as np
import pytest

import opensimula as osm
from opensimula.components.Pump import staged_pump_flows
from opensimula.cte import dhw_profile_schedules

EXAMPLES = pathlib.Path(osm.__file__).parent / "examples"
MET = str(EXAMPLES / "sevilla.met")
# condensing boiler: 0.98 with the water entering at 30 °C, 0.25 % less per K above
CONDENSING = {"nominal_efficiency": 0.98, "efficiency_expression": "1 - 0.0025 * max(T_wi - 30, 0)"}


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


def instantaneous_boiler(flow_control, boiler=None):
    """A gas boiler without pump (mains pressure) giving only DHW, 120 l/day at 60 °C."""
    return {"name": "dhw", "time_step": 3600, "simulation_file_met": "sevilla", "components": [
        {"type": "File_met", "name": "sevilla", "file_type": "MET", "file_name": MET},
        {"type": "Boiler", "name": "boiler", "nominal_heating_capacity": 24000,
         "nominal_efficiency": 0.92, "nominal_water_flow": 0.3, **(boiler or {})},
        {"type": "HVAC_water_generator", "name": "gen", "equipment": "boiler"},
        {"type": "HVAC_water_system", "name": "plant", "generators": ["gen"],
         "total_water_volume": 5, "heating_water_setpoint": "60", "pump_operation": "ON_LOAD",
         "flow_control": flow_control},
        *dhw_profile_schedules("profile"),
        {"type": "DHW_demand", "name": "dhw", "water_system": "plant",
         "input_variables": ["f = profile.values"], "volume_flow": "120 * f"},
    ]}


def test_staged_pump_flows():
    sim = osm.Simulation()
    pro = sim.new_project("p")
    pumps = []
    for i, flow in enumerate([0.2, 0.2, 0.1]):
        p = pro.new_component("Pump", f"p{i}")
        p.parameter("nominal_water_flow").value = flow
        pumps.append(p)
    assert staged_pump_flows(pumps, 0) == [0, 0, 0]
    assert staged_pump_flows(pumps, 0.15) == pytest.approx([0.15, 0, 0])
    assert staged_pump_flows(pumps, 0.3) == pytest.approx([0.15, 0.15, 0])
    assert staged_pump_flows(pumps, 0.45) == pytest.approx([0.18, 0.18, 0.09])
    assert staged_pump_flows(pumps, 1.0) == pytest.approx([0.4, 0.4, 0.2])  # above nominal


def test_instantaneous_boiler_takes_mains_water():
    pro = simulate(instantaneous_boiler("VARIABLE"))
    draw = values(pro, "dhw", "Q_demand") > 0
    # the boiler moves only the water drawn, which enters it at the mains temperature
    assert np.allclose(values(pro, "plant", "primary_flow")[draw],
                       values(pro, "dhw", "water_flow")[draw])
    assert np.all(values(pro, "plant", "primary_flow")[~draw] == 0)
    T_in = values(pro, "plant", "T_generators_in")[draw]
    assert np.allclose(T_in, values(pro, "dhw", "T_mains")[draw], atol=1.5)
    assert values(pro, "dhw", "Q_unmet").sum() == 0
    # energy balance of the plant
    balance = (values(pro, "plant", "Q_generators") + values(pro, "plant", "Q_coils")
               + values(pro, "plant", "Q_loss") + values(pro, "plant", "Q_pump")
               - values(pro, "plant", "delta_U"))
    assert abs(balance.sum()) < 1e-3 * values(pro, "plant", "Q_generators").sum()


def test_condensing_boiler_better_with_variable_flow():
    efficiency = {}
    for flow_control in ("CONSTANT", "VARIABLE"):
        pro = simulate(instantaneous_boiler(flow_control, CONDENSING))
        efficiency[flow_control] = (values(pro, "plant", "Q_generators").sum()
                                    / values(pro, "gen", "fuel_power").sum())
    assert efficiency["VARIABLE"] == pytest.approx(0.98, abs=0.005)  # mains water, ~11 °C
    assert efficiency["CONSTANT"] < 0.92  # the water comes back almost at 60 °C


def header_plant(minimum_flow, Q_process="-6000"):
    def pump(name, flow, power):
        return {"type": "Pump", "name": name, "nominal_water_flow": flow, "nominal_power": power,
                "power_to_heat_fraction": 0, "power_expression": "F_water"}
    return {"name": "p", "time_step": 3600, "simulation_file_met": "sevilla", "components": [
        {"type": "File_met", "name": "sevilla", "file_type": "MET", "file_name": MET},
        {"type": "Boiler", "name": "boiler", "nominal_heating_capacity": 10000,
         "nominal_efficiency": 0.9, "nominal_water_flow": 0.5},
        pump("primary", 0.5, 50), pump("s0", 0.2, 80), pump("s1", 0.2, 80),
        {"type": "HVAC_water_generator", "name": "g", "equipment": "boiler", "pump": "primary"},
        {"type": "HVAC_water_system", "name": "plant", "generators": ["g"], "pumps": ["s0", "s1"],
         "heating_water_setpoint": "50", "initial_water_temp": 45, "total_water_volume": 100,
         "Q_process": Q_process, "flow_control": "VARIABLE", "minimum_flow": minimum_flow},
    ]}


@pytest.mark.parametrize("minimum_flow, pumps_power", [(0.375, 60), (0.6, 96)])
def test_header_secondary_pumps_staged(minimum_flow, pumps_power):
    # no coil asks for water: the secondary moves the minimum flow (of 0.4 dm³/s)
    pro = simulate(header_plant(minimum_flow), days=2)
    assert np.allclose(values(pro, "plant", "secondary_flow"), 0.4 * minimum_flow)
    # 0.15: one pump at 0.75 of its flow; 0.24: both at 0.6 (power_expression F_water)
    assert np.allclose(values(pro, "plant", "secondary_pumps_power"), pumps_power)
    # the process load is served with the minimum flow
    assert values(pro, "plant", "Q_generators")[-1] == pytest.approx(6000, rel=1e-3)


def test_warning_process_without_minimum_flow():
    sim = osm.Simulation()
    sim.console_print = False
    pro = sim.new_project("p")
    pro.read_dict(header_plant(0))
    assert any("minimum_flow" in m.text for m in pro.check() if m.level == "WARNING")


def test_circuit_flow_of_its_coils():
    data = json.loads((EXAMPLES / "10_energy_and_comfort.json").read_text(encoding="utf-8"))
    power = {}
    for flow_control in ("CONSTANT", "VARIABLE"):
        for c in data["components"]:
            if c["type"] == "HVAC_water_circuit":
                c["flow_control"] = flow_control
        pro = simulate(data)
        circuit = next(c.parameter("name").value for c in pro.component_list()
                       if c.parameter("type").value == "HVAC_water_circuit")
        power[flow_control] = values(pro, circuit, "pumps_power").sum()
        if flow_control == "VARIABLE":
            design = sum(p.parameter("nominal_water_flow").value
                         for p in pro.component(circuit).parameter("pumps").component)
            on = values(pro, circuit, "on_off") == 1
            flow = values(pro, circuit, "water_flow")
            assert np.allclose(flow[on], np.clip(values(pro, circuit, "coils_flow")[on], 0, design))
    assert power["VARIABLE"] < power["CONSTANT"]
