"""Water system with a header (primary / secondary): a condensing boiler and a
constant process load of 6 kW of heating; pumps that give no heat to the water, so
that the temperatures of the steady state can be checked exactly."""

import pathlib

import numpy as np
import pytest

import opensimula as osm

MET = str(pathlib.Path(osm.__file__).parent / "examples" / "sevilla.met")
BOILER = {"type": "Boiler", "name": "boiler", "nominal_heating_capacity": 10000,
          "nominal_efficiency": 0.88, "efficiency_expression": "1 + 0.0035 * max(55 - T_wi, 0)"}


def pump(name, flow, power):
    return {"type": "Pump", "name": name, "nominal_water_flow": flow, "nominal_power": power,
            "power_to_heat_fraction": 0}


def plant(primary_flow, secondary_flows, Q_process="-6000", n=48, boilers=1, **plant_parameters):
    components = [{"type": "File_met", "name": "sevilla", "file_type": "MET", "file_name": MET}]
    generators = []
    for i in range(boilers):
        components.append(BOILER | {"name": f"boiler_{i}", "nominal_water_flow": primary_flow})
        components.append(pump(f"primary_{i}", primary_flow, 50))
        components.append({"type": "HVAC_water_generator", "name": f"g{i}", "equipment": f"boiler_{i}",
                           "pump": f"primary_{i}"})
        generators.append(f"g{i}")
    pumps = []
    for i, flow in enumerate(secondary_flows):
        components.append(pump(f"secondary_{i}", flow, 80))
        pumps.append(f"secondary_{i}")
    components.append({"type": "HVAC_water_system", "name": "plant", "generators": generators,
                       "pumps": pumps, "heating_water_setpoint": "50", "initial_water_temp": 45,
                       "total_water_volume": 100, "Q_process": Q_process} | plant_parameters)
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


def rho_cp(pro):
    T = last(pro, "plant", "T_mean")
    return pro._sim_.props["RHOCP_W"](T) / 1000


def test_primary_larger_than_secondary_hot_water_back_to_the_boiler():
    pro = plant(0.3, [0.2])
    m_p, m_s = 0.3, 0.2
    assert last(pro, "plant", "primary_flow") == pytest.approx(m_p)
    assert last(pro, "plant", "secondary_flow") == pytest.approx(m_s)
    assert last(pro, "plant", "bypass_flow") == pytest.approx(0.1)
    # supply at the setpoint; return colder by the load; boiler inlet: return mixed with
    # the supply that goes back through the bypass
    T_S = last(pro, "plant", "T_supply")
    T_R = last(pro, "plant", "T_return")
    assert T_S == pytest.approx(50, abs=0.01)
    assert T_S - T_R == pytest.approx(6000 / (rho_cp(pro) * m_s), rel=1e-3)
    T_in = last(pro, "plant", "T_generators_in")
    assert T_in == pytest.approx((m_s * T_R + (m_p - m_s) * T_S) / m_p, abs=0.01)
    assert last(pro, "g0", "T_wi") == pytest.approx(T_in)
    assert last(pro, "g0", "Q") == pytest.approx(6000, rel=1e-3)


def test_primary_smaller_than_secondary_supply_below_the_setpoint():
    pro = plant(0.1, [0.2])
    assert last(pro, "plant", "bypass_flow") == pytest.approx(-0.1)
    # the boiler gives 50 °C at its outlet, the supply is a mix with the return
    assert last(pro, "plant", "T_generators_out") == pytest.approx(50, abs=0.01)
    T_S = last(pro, "plant", "T_supply")
    T_R = last(pro, "plant", "T_return")
    assert T_S < 45
    assert T_S == pytest.approx((0.1 * 50 + 0.1 * T_R) / 0.2, abs=0.01)
    assert last(pro, "plant", "T_generators_in") == pytest.approx(T_R)
    assert last(pro, "g0", "T_wo") == pytest.approx(50, abs=0.02)


def test_a_condensing_boiler_loses_efficiency_with_the_bypass():
    balanced = plant(0.2, [0.2])
    bypass = plant(0.4, [0.2])
    assert last(bypass, "g0", "T_wi") > last(balanced, "g0", "T_wi") + 3
    assert last(bypass, "g0", "efficiency") < last(balanced, "g0", "efficiency")


def test_backup_boiler_moves_no_water_while_it_does_not_run():
    # 6 kW: the first boiler alone; the second moves no water
    pro = plant(0.2, [0.3], boilers=2)
    assert np.all(pro.component("g1").variable("Q").values == 0)
    assert np.all(pro.component("g1").variable("water_flow").values == 0)
    assert last(pro, "plant", "primary_flow") == pytest.approx(0.2)
    # 15 kW: the second runs, and moves its water, only while it gives heat
    pro = plant(0.2, [0.3], Q_process="-15000", boilers=2)
    flows = pro.component("g1").variable("water_flow").values
    Q1 = pro.component("g1").variable("Q").values
    assert np.all(flows[Q1 == 0] == 0) and np.allclose(flows[Q1 > 0], 0.2)
    assert last(pro, "g0", "Q") == pytest.approx(10000)
    assert last(pro, "g1", "Q") == pytest.approx(5000, rel=1e-3)
    assert last(pro, "plant", "primary_flow") == pytest.approx(0.4)


def test_pumps_power_primary_and_secondary():
    pro = plant(0.3, [0.1, 0.1])
    assert last(pro, "plant", "secondary_flow") == pytest.approx(0.2)
    assert last(pro, "plant", "secondary_pumps_power") == pytest.approx(160)
    assert last(pro, "plant", "pumps_power") == pytest.approx(210)
    assert last(pro, "g0", "pump_power") == pytest.approx(50)
    # boilers with no auxiliary power: all the electricity is the pumps'
    assert last(pro, "plant", "electric_power") == pytest.approx(210)


def test_plant_off_no_flows():
    pro = plant(0.3, [0.2], n=6, system_on_off="0")
    for v in ("primary_flow", "secondary_flow", "Q_generators", "pumps_power", "electric_power"):
        assert np.all(pro.component("plant").variable(v).values == 0)


def test_heat_of_the_pumps_counted_once():
    # pumps that heat the water: with a small load the supply must stay at the setpoint
    # (the heat of the secondary pumps was counted twice: the water overheated)
    pro = plant(0.3, [0.2], Q_process="-1000", n=72)
    for p in ("primary_0", "secondary_0"):
        pro.component(p).parameter("power_to_heat_fraction").value = 1
    pro.simulate(progress=lambda i, n: None)
    T_S = pro.component("plant").variable("T_supply").values[24:]
    assert np.all(T_S < 50.2)
    h = lambda n: pro.component("plant").variable(n).values[24:]
    residual = h("delta_U") - (h("Q_generators") + h("Q_process") + h("Q_loss") + h("Q_pump"))
    assert np.abs(residual).max() < 1
