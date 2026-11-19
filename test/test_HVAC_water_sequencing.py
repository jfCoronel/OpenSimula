"""Several generators in a water system and several units in a generator: a constant
process load of 6 kW (heating) or 6 kW (cooling), no pumps, no losses, so that in the
steady state the plant gives exactly the load."""

import pathlib

import numpy as np
import pytest

import opensimula as osm

MET = str(pathlib.Path(osm.__file__).parent / "examples" / "sevilla.met")
# boiler: 4 kW, 90 % at full load, 20 % less at no load
BOILER = {"type": "Boiler", "nominal_heating_capacity": 4000, "nominal_efficiency": 0.9,
          "nominal_water_flow": 0.2, "efficiency_expression": "1 - 0.2 * (1 - F_load)"}


def eff(F):
    return 0.9 * (1 - 0.2 * (1 - F))


def plant(generators, equipment, sequencing="PRIORITY", Q_process="-6000", n=48):
    components = [{"type": "File_met", "name": "sevilla", "file_type": "MET", "file_name": MET}]
    components += equipment + generators
    components.append({"type": "HVAC_water_system", "name": "plant",
                       "generators": [g["name"] for g in generators], "sequencing": sequencing,
                       "heating_water_setpoint": "50", "cooling_water_setpoint": "7",
                       "initial_water_temp": 50 if Q_process.startswith("-") else 7,
                       "total_water_volume": 100, "Q_process": Q_process})
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


def two_boilers(sequencing, **second):
    equipment = [BOILER | {"name": "b1"}, BOILER | {"name": "b2"}]
    generators = [{"type": "HVAC_water_generator", "name": "g1", "equipment": "b1"},
                  {"type": "HVAC_water_generator", "name": "g2", "equipment": "b2"} | second]
    return plant(generators, equipment, sequencing)


def test_priority_the_second_after_the_first_at_full_load():
    pro = two_boilers("PRIORITY")
    assert last(pro, "plant", "Q_generators") == pytest.approx(6000)
    assert last(pro, "g1", "Q") == pytest.approx(4000)
    assert last(pro, "g2", "Q") == pytest.approx(2000)
    assert last(pro, "g1", "F_load") == pytest.approx(1)
    assert last(pro, "g2", "F_load") == pytest.approx(0.5)
    fuel = 4000 / eff(1) + 2000 / eff(0.5)
    assert last(pro, "plant", "generators_fuel_power") == pytest.approx(fuel)
    # both in parallel in the loop
    assert last(pro, "plant", "primary_flow") == pytest.approx(0.4)


def test_equal_load_all_at_the_same_part_load():
    pro = two_boilers("EQUAL_LOAD")
    for g in ("g1", "g2"):
        assert last(pro, g, "Q") == pytest.approx(3000)
        assert last(pro, g, "F_load") == pytest.approx(0.75)
    assert last(pro, "plant", "generators_fuel_power") == pytest.approx(6000 / eff(0.75))


def test_a_generator_off_lets_no_water_through_and_the_other_gives_what_it_can():
    pro = two_boilers("PRIORITY", system_on_off="0")
    assert last(pro, "g2", "Q") == 0
    assert last(pro, "g2", "water_flow") == 0
    assert last(pro, "plant", "primary_flow") == pytest.approx(0.2)
    assert last(pro, "g1", "Q") == pytest.approx(4000)
    # 2 kW missing: the water cools below the setpoint
    assert last(pro, "plant", "T_generators_out") < 45


@pytest.mark.parametrize("sequencing", ["PRIORITY", "EQUAL_LOAD"])
def test_units_of_a_generator(sequencing):
    pro = plant([{"type": "HVAC_water_generator", "name": "g", "equipment": "b", "number_of_units": 2}],
                [BOILER | {"name": "b"}], sequencing)
    assert last(pro, "g", "Q") == pytest.approx(6000)
    assert last(pro, "g", "F_load") == pytest.approx(0.75)
    assert last(pro, "g", "units_on") == 2
    assert last(pro, "g", "water_flow") == pytest.approx(0.4)
    if sequencing == "PRIORITY":
        fuel = 4000 / eff(1) + 2000 / eff(0.5)
    else:
        fuel = 6000 / eff(0.75)
    assert last(pro, "g", "fuel_power") == pytest.approx(fuel)
    assert last(pro, "g", "efficiency") == pytest.approx(6000 / fuel)


def test_heat_pump_first_and_boiler_as_backup():
    heat_pump = {"type": "Chiller_heat_pump", "name": "hp", "chiller_type": "HEAT_PUMP",
                 "nominal_heating_capacity": 4000, "nominal_heating_power": 1250,
                 "heating_capacity_expression": "1", "heating_power_expression": "1",
                 "nominal_water_flow": 0.2}
    generators = [{"type": "HVAC_water_generator", "name": "hp_gen", "equipment": "hp"},
                  {"type": "HVAC_water_generator", "name": "boiler_gen", "equipment": "b"}]
    pro = plant(generators, [heat_pump, BOILER | {"name": "b"}])
    assert last(pro, "hp_gen", "Q") == pytest.approx(4000)
    assert last(pro, "boiler_gen", "Q") == pytest.approx(2000)
    assert last(pro, "plant", "generators_power") == pytest.approx(1250)
    assert last(pro, "plant", "generators_fuel_power") == pytest.approx(2000 / eff(0.5))


def test_only_the_generators_able_to_cool_run_in_cooling():
    chiller = {"type": "Chiller_heat_pump", "name": "ch", "chiller_type": "CHILLER",
               "nominal_cooling_capacity": 8000, "nominal_cooling_power": 2500,
               "cooling_capacity_expression": "1", "cooling_power_expression": "1",
               "nominal_water_flow": 0.4}
    generators = [{"type": "HVAC_water_generator", "name": "boiler_gen", "equipment": "b"},
                  {"type": "HVAC_water_generator", "name": "chiller_gen", "equipment": "ch"}]
    pro = plant(generators, [BOILER | {"name": "b"}, chiller], Q_process="6000")
    assert last(pro, "boiler_gen", "Q") == 0
    assert last(pro, "chiller_gen", "Q") == pytest.approx(-6000)
    assert last(pro, "chiller_gen", "F_load") == pytest.approx(0.75)
    assert np.all(pro.component("boiler_gen").variable("Q").values == 0)


def test_a_pump_without_flow_gives_no_heat():
    # the power expression of a pump is constant by default: with no flow its heat to
    # the water must be 0 (a generator not available added the heat of its pump)
    pro = plant([{"type": "HVAC_water_generator", "name": "g", "equipment": "b", "pump": "p"}],
                [BOILER | {"name": "b"}, {"type": "Pump", "name": "p", "nominal_water_flow": 0.2,
                                          "nominal_power": 70}], n=2)
    g = pro.component("g")
    assert g.get_pump_heat(0) == 0
    assert g.get_pump_heat(0.2) == pytest.approx(70)
