import pytest

import opensimula as osm


def boiler(**parameters):
    sim = osm.Simulation()
    pro = sim.new_project("p")
    pro.read_dict({
        "name": "p",
        "components": [{"type": "Boiler", "name": "boiler", "nominal_heating_capacity": 20000,
                        "nominal_efficiency": 0.9} | parameters],
    })
    errors = [m.text for m in sim.message_list() if m.level == "ERROR"]
    assert not errors, errors
    return pro.component("boiler")


def test_heating_load_up_to_the_capacity():
    b = boiler()
    assert b.get_heating_load(70, 50, 1, 5000) == (5000, 0.25)
    assert b.get_heating_load(70, 50, 1, 30000) == (20000, 1)
    assert b.get_heating_load(70, 50, 1, 0) == (0, 0)
    assert b.get_heating_load(70, 50, 1, -100) == (0, 0)


def test_no_heat_above_the_maximum_supply_temperature():
    b = boiler(max_supply_temperature=60)
    assert b.get_heating_load(65, 50, 1, 5000) == (0, 0)
    assert b.get_fuel_power(65, 50, 1, 5000) == (0, 0)


def test_fuel_power_with_the_nominal_efficiency():
    b = boiler()
    fuel, efficiency = b.get_fuel_power(70, 50, 1, 9000)
    assert efficiency == pytest.approx(0.9)
    assert fuel == pytest.approx(10000)


def test_condensing_boiler_more_efficient_with_a_cold_return():
    b = boiler(nominal_efficiency=0.88, efficiency_expression="1 + 0.0035 * max(55 - T_wi, 0)")
    assert b.get_efficiency(80, 60, 1, 1) == pytest.approx(0.88)
    assert b.get_efficiency(40, 30, 1, 1) == pytest.approx(0.88 * (1 + 0.0035 * 25))


def test_part_load_and_expression_limits():
    b = boiler(efficiency_expression="1 - 0.1 * (1 - F_load)",
               expression_max_values=[100, 100, 1.5, 1], expression_min_values=[0, 0, 0, 0.3])
    assert b.get_efficiency(70, 50, 1, 1) == pytest.approx(0.9)
    assert b.get_efficiency(70, 50, 1, 0.5) == pytest.approx(0.9 * 0.95)
    # F_load below its minimum (0.3) is evaluated at the minimum
    assert b.get_efficiency(70, 50, 1, 0.1) == pytest.approx(0.9 * 0.93)


def test_auxiliary_power_only_while_heating():
    b = boiler(auxiliary_power=60)
    assert b.get_auxiliary_power(5000) == 60
    assert b.get_auxiliary_power(0) == 0


def test_fuel_options_are_checked():
    sim = osm.Simulation()
    pro = sim.new_project("p")
    pro.read_dict({"name": "p", "components": [{"type": "Boiler", "name": "b", "fuel": "COAL"}]})
    assert any(m.level == "ERROR" for m in sim.message_list())
