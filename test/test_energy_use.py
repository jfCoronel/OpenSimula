"""Component.get_energy_use(): what each consumer reports, once and only once."""

import json
import pathlib

import numpy as np
import pytest

import opensimula as osm
from opensimula.energy import CARRIERS, SERVICES

EXAMPLES = pathlib.Path(osm.__file__).parent / "examples"
MZW = pathlib.Path(__file__).parent / "mzw_four_pipe.json"


def simulate(path, start, days, changes=None):
    data = json.loads(path.read_text(encoding="utf-8"))
    data["initial_time"] = start
    data["n_time_steps"] = 24 * days
    for c in data["components"]:
        if c["type"] in ("File_met", "File_data"):
            c["file_name"] = str(EXAMPLES / pathlib.Path(c["file_name"]).name)
        if changes and c["name"] in changes:
            c.update(changes[c["name"]])
    sim = osm.Simulation()
    sim.console_print = False
    pro = sim.new_project("p")
    pro.read_dict(data)
    errors = [m.text for m in sim.message_list() if m.level == "ERROR"]
    assert not errors, errors
    pro.simulate(progress=lambda i, n: None)
    return pro


def uses(component):
    """{(carrier, service): values} of a component, checking the format."""
    result = {}
    n = component.project().parameter("n_time_steps").value
    for use in component.get_energy_use():
        assert use.carrier in CARRIERS and use.service in SERVICES, use[:2]
        assert use.values.shape == (n,) and np.all(use.values >= -1e-9), use[:2]
        assert (use.carrier, use.service) not in result
        result[(use.carrier, use.service)] = use.values
    return result


def total(pro, carrier, exclude=("Space",)):
    """Sum over the project of one carrier, all services (W·step)."""
    return sum(
        v.sum()
        for c in pro.component_list()
        if type(c).__name__ not in exclude
        for (car, _), v in uses(c).items()
        if car == carrier
    )


def values(pro, component, variable):
    return pro.component(component).variable(variable).values


@pytest.fixture(scope="module")
def ideal():
    return simulate(EXAMPLES / "05_ideal_system.json", "01/03/2001 00:00:00", 14)


@pytest.fixture(scope="module")
def dx():
    return simulate(EXAMPLES / "06_dx_system.json", "01/03/2001 00:00:00", 14)


@pytest.fixture(scope="module")
def plant():
    return simulate(EXAMPLES / "09_water_plant.json", "01/01/2001 00:00:00", 14)


def test_components_without_energy_report_nothing(ideal):
    assert ideal.component("sevilla").get_energy_use() == []
    assert ideal.component("wall").get_energy_use() == []


def test_space_lighting_and_equipment(ideal):
    u = uses(ideal.component("office"))
    light = values(ideal, "office", "light_convective") + values(ideal, "office", "light_radiant")
    assert u[("ELECTRICITY", "LIGHTING")].sum() > 0
    assert np.allclose(u[("ELECTRICITY", "LIGHTING")], light)
    other = sum(values(ideal, "office", f"other_gains_{k}") for k in ("convective", "radiant", "latent"))
    assert np.allclose(u[("ELECTRICITY", "EQUIPMENT")], other)


def test_ideal_system_heat_without_equipment(ideal):
    u = uses(ideal.component("ideal_system"))
    assert set(u) == {("THERMAL", "HEATING_WITHOUT_EQUIPMENT"), ("THERMAL", "COOLING_WITHOUT_EQUIPMENT")}
    heating, cooling = u[("THERMAL", "HEATING_WITHOUT_EQUIPMENT")], u[("THERMAL", "COOLING_WITHOUT_EQUIPMENT")]
    assert heating.sum() > 0 and cooling.sum() > 0
    Q = values(ideal, "ideal_system", "Q_sensible") + values(ideal, "ideal_system", "Q_latent")
    assert (heating - cooling).sum() == pytest.approx(Q.sum())
    assert total(ideal, "ELECTRICITY") == 0


def test_dx_system(dx):
    u = uses(dx.component("dx_system"))
    power = values(dx, "dx_system", "power")
    electricity = sum(v for (c, _), v in u.items() if c == "ELECTRICITY")
    assert np.allclose(electricity, power)  # compressor + fan, nothing lost or repeated
    assert np.allclose(u[("ELECTRICITY", "AIR_TRANSPORT")], values(dx, "dx_system", "indoor_fan_power"))
    state = values(dx, "dx_system", "state")
    heating = np.isin(state, [1, 2])
    assert heating.sum() > 0 and np.isin(state, [-1, -2]).sum() > 0
    assert np.all(u[("ELECTRICITY", "HEATING")][~heating] == 0)
    # ambient energy of the heat pump: heat given minus compressor
    Q = values(dx, "dx_system", "Q_sensible")
    ambient = u[("AMBIENT", "HEATING")]
    assert ambient.sum() > 0
    assert np.allclose(ambient[heating], np.clip(Q - u[("ELECTRICITY", "HEATING")], 0, None)[heating])


def test_water_plant_counts_each_power_once(plant):
    # the plant's electric_power has its generators and pumps; circuits and fans apart
    expected = (
        values(plant, "water_plant", "electric_power").sum()
        + sum(values(plant, c, "pumps_power").sum() for c in ("south_circuit", "north_circuit"))
        + sum(values(plant, f, "supply_fan_power").sum() + values(plant, f, "return_fan_power").sum()
              for f in ("fan_coil_south", "fan_coil_north"))
    )
    assert expected > 0
    assert total(plant, "ELECTRICITY") == pytest.approx(expected)
    fuel = plant.component("boiler").parameter("fuel").value
    assert total(plant, fuel) == pytest.approx(values(plant, "water_plant", "generators_fuel_power").sum())
    assert total(plant, fuel) > 0
    # coils fed by the plant: no heat without equipment
    assert total(plant, "THERMAL") == 0


def test_water_generators(plant):
    hp = uses(plant.component("heat_pump_generator"))
    Q = values(plant, "heat_pump_generator", "Q")
    power = values(plant, "heat_pump_generator", "power")
    assert np.allclose(hp[("ELECTRICITY", "HEATING")] + hp[("ELECTRICITY", "COOLING")], power)
    assert np.allclose(hp[("AMBIENT", "HEATING")], np.clip(np.where(Q > 0, Q - power, 0), 0, None))
    assert hp[("AMBIENT", "HEATING")].sum() > 0
    boiler = uses(plant.component("boiler_generator"))
    assert ("AMBIENT", "HEATING") not in boiler
    assert np.allclose(boiler[("ELECTRICITY", "WATER_TRANSPORT")], values(plant, "boiler_generator", "pump_power"))


def test_coils_without_water_system_heat_without_equipment():
    pro = simulate(MZW, "01/01/2001 00:00:00", 7,
                   {"ahu": {"water_source": "UNKNOWN", "reheat_water_source": "UNKNOWN"}})
    u = uses(pro.component("ahu"))
    state = values(pro, "ahu", "state")
    reheat = values(pro, "ahu", "Q_reheat_0") + values(pro, "ahu", "Q_reheat_1")
    heating_coil = np.where(np.isin(state, [1, 2]), values(pro, "ahu", "Q_sensible"), 0)
    assert reheat.sum() > 0
    assert np.allclose(u[("THERMAL", "HEATING_WITHOUT_EQUIPMENT")], heating_coil + reheat)
    assert ("THERMAL", "COOLING_WITHOUT_EQUIPMENT") in u
    # the plants get no load: no energy from them
    assert total(pro, "NATURAL_GAS") == 0
