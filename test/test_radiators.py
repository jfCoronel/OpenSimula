"""Radiator (EN 442) and HVAC_radiator_system: radiators of a zone fed by a water plant."""

import json
import pathlib

import numpy as np
import pytest

import opensimula as osm

EX = pathlib.Path(osm.__file__).parent / "examples"


def office(water="70", control="THERMOSTATIC", units=2, cooling=False, days=31):
    """The office of example 04 heated by two 2 kW radiators and a gas boiler."""
    d = json.loads((EX / "04_windows_and_gains.json").read_text(encoding="utf-8"))
    d["initial_time"], d["n_time_steps"] = "01/01/2001 00:00:00", 24 * days
    for c in d["components"]:
        if c["type"] in ("File_met", "File_data"):
            c["file_name"] = str(EX / pathlib.Path(c["file_name"]).name)
    d["components"] += [
        {"type": "Boiler", "name": "boiler", "nominal_heating_capacity": 24000,
         "nominal_efficiency": 0.92, "nominal_water_flow": 0.3},
        {"type": "Pump", "name": "pump", "nominal_water_flow": 0.3, "nominal_power": 60},
        {"type": "HVAC_water_generator", "name": "gen", "equipment": "boiler", "pump": "pump"},
        {"type": "HVAC_water_system", "name": "plant", "generators": ["gen"],
         "heating_water_setpoint": water, "total_water_volume": 30, "pump_operation": "ON_LOAD"},
        {"type": "Radiator", "name": "panel", "nominal_heat_output": 2000, "exponent": 1.3},
        {"type": "HVAC_radiator_system", "name": "radiators", "space": "office", "radiator": "panel",
         "number_of_units": units, "water_system": "plant", "heating_setpoint": "20",
         "control": control},
    ]
    if cooling:
        d["components"].append({"type": "HVAC_perfect_system", "name": "cooler", "spaces": "office",
                                "heating_setpoint": "-50", "cooling_setpoint": "25"})
    return d


def simulate(data):
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


def radiator(**parameters):
    sim = osm.Simulation()
    pro = sim.new_project("p")
    r = pro.new_component("Radiator", "r")
    r.set_parameters({"nominal_heat_output": 1000, **parameters})
    r._sim_ = sim
    r.pre_simulation(1, 3600)
    return r


def test_radiator_en_442():
    r = radiator()
    # nominal conditions 75 / 65 / 20 °C with its nominal flow: the nominal heat
    Q, T_wo = r.heat_output(75, r.nominal_flow, 20)
    assert Q == pytest.approx(1000, rel=1e-6) and T_wo == pytest.approx(65, abs=1e-4)
    # colder water: the characteristic equation and the heat of the water agree
    Q, T_wo = r.heat_output(50, r.nominal_flow, 20)
    dT = r.log_mean(50, T_wo, 20)
    assert Q == pytest.approx(1000 * (dT / r.dT_nom) ** 1.3, rel=1e-6)
    mc = r.props["RHOCP_W"](50) / 1000 * r.nominal_flow
    assert Q == pytest.approx(mc * (50 - T_wo), rel=1e-6)
    assert Q < 0.5 * 1000
    # the flow for a part of the heat: less flow, colder return
    flow, T_wo_part = r.flow_for(300, 75, 20)
    assert 0 < flow < r.nominal_flow and T_wo_part < 65
    assert r.heat_output(75, flow, 20)[0] == pytest.approx(300, rel=1e-4)
    assert r.heat_output(20, r.nominal_flow, 20) == (0.0, 20)


def test_thermostatic_radiators_hold_the_setpoint():
    pro = simulate(office())
    T = values(pro, "office", "temperature")
    Q = values(pro, "radiators", "Q")
    assert T.min() > 20 - 0.01
    assert Q.sum() > 0 and np.all(values(pro, "radiators", "F_load") <= 1 + 1e-9)
    # for the plant the radiators are a heating coil; its balance holds
    assert np.allclose(-values(pro, "plant", "Q_heating_coils"), Q)
    p = "plant"
    balance = (values(pro, p, "Q_generators") + values(pro, p, "Q_loads") + values(pro, p, "Q_loss")
               + values(pro, p, "Q_pump") - values(pro, p, "delta_U"))
    assert abs(balance.sum()) < 1e-3 * values(pro, p, "Q_generators").sum()
    # the heat of the water: flow and temperatures
    on = Q > 0
    rho_cp = pro._sim_.props["RHOCP_W"](60) / 1000
    heat = rho_cp * values(pro, "radiators", "water_flow") * (
        values(pro, "radiators", "T_wi") - values(pro, "radiators", "T_wo"))
    assert np.allclose(heat[on], Q[on], rtol=0.02)


def test_colder_water_gives_less_heat():
    hot, cold = simulate(office()), simulate(office(water="45"))
    assert values(cold, "radiators", "Q").max() < values(hot, "radiators", "Q").max()
    # at the peaks the radiators are at full capacity and the office below 20 °C
    full = values(cold, "radiators", "F_load") >= 1 - 1e-9
    assert full.sum() > 0
    assert values(cold, "office", "temperature")[full].min() < 20


def test_no_control_gives_all_it_can():
    pro = simulate(office(control="NONE", days=7))
    assert values(pro, "office", "temperature").mean() > 30
    assert np.allclose(values(pro, "radiators", "water_flow")[values(pro, "radiators", "Q") > 0],
                       2 * pro.component("panel").nominal_flow)


def test_radiators_and_a_cooling_system_in_the_same_zone():
    pro = simulate(office(cooling=True))
    T = values(pro, "office", "temperature")
    assert T.min() > 20 - 0.01 and T.max() < 25 + 0.01
    assert values(pro, "radiators", "Q").sum() > 0
    assert values(pro, "cooler", "Q_sensible").min() < 0


def test_zone_setpoints_and_checks():
    pro = simulate(office(days=2))
    control = pro.component("radiators").get_zone_setpoints()[0]
    assert control.zone is pro.component("office")
    assert np.all(control.heating_setpoint == 20) and np.all(np.isinf(control.cooling_setpoint))
    data = office(days=2)
    for c in data["components"]:
        if c["name"] == "radiators":
            c["water_system"] = "not_defined"
    sim = osm.Simulation()
    sim.console_print = False
    p = sim.new_project("p")
    p.read_dict(data)
    assert any("water_system" in m.text for m in p.check() if m.level == "ERROR")


def test_heat_of_uncontrolled_systems_is_stored():
    """The heat of an uncontrolled system (Q_s: radiators, MZW reheat) was not in the
    variable u_system_sensible_heat of the zone (only that of its air)."""
    pro = simulate(office(days=7))
    Q = values(pro, "radiators", "Q")
    radiant = values(pro, "radiators", "Q_radiant")
    # the heat that reaches the air: the convective part and, of the radiant one, what
    # the surfaces give to the air in the same time step
    to_air = Q - radiant + pro.component("office").radiant_to_air() * radiant
    assert np.allclose(values(pro, "office", "u_system_sensible_heat"), to_air)


# _________________ radiant part _________________

def with_radiant(data, fraction, distribution=None):
    for c in data["components"]:
        if c["name"] == "panel":
            c["radiant_fraction"] = fraction
        if c["name"] == "radiators" and distribution is not None:
            c["radiant_distribution"] = distribution
    return data


def building_of(pro):
    return next(c for c in pro.component_list() if c.parameter("type").value == "Building")


def test_radiant_part_reaches_the_surfaces():
    pro = simulate(with_radiant(office(days=3), 0.3))
    space, building = pro.component("office"), building_of(pro)
    for distribution in (None, [1, 0, 0], [0.3, 0.2, 0.5]):
        R, absorbed, to_air = building.radiant_response(space, distribution)
        assert absorbed.sum() == pytest.approx(-1)  # all of it is absorbed
        assert 0 < R < 1 and to_air[0] == R
    # all to the floor: the floor absorbs most of it (the rest is reflected)
    _, absorbed, _ = building.radiant_response(space, [1, 0, 0])
    floor = [i for i, s in enumerate(building.surfaces)
             if s.orientation_angle("altitude", building.sides[i]) == 90]
    assert -absorbed[floor].sum() > 0.85
    # the long-wave heat of the surfaces: internal gains and the radiators
    total = sum(s.area * values(pro, s.parameter("name").value,
                                "q_lwig0" if building.sides[i] == 0 else "q_lwig1")
                for i, s in enumerate(building.surfaces)
                if s.parameter("type").value == "Opening" or s.parameter("surface_type").value != "VIRTUAL")
    gains = values(pro, "office", "people_radiant") + values(pro, "office", "other_gains_radiant")
    assert np.allclose(total - gains, values(pro, "radiators", "Q_radiant"), atol=1e-6)


def test_more_radiant_more_heat_for_the_same_air_temperature():
    heat = {}
    for fraction in (0.0, 0.3):
        pro = simulate(with_radiant(office(days=14), fraction))
        assert values(pro, "office", "temperature").min() > 20 - 0.01
        heat[fraction] = values(pro, "radiators", "Q").sum()
    assert heat[0.3] > heat[0.0]


def load_space_radiators(fraction):
    d = json.loads((EX / "08_load_records.json").read_text(encoding="utf-8"))
    d["initial_time"], d["n_time_steps"] = "01/01/2001 00:00:00", 24 * 7
    for c in d["components"]:
        if c["type"] in ("File_met", "File_data"):
            c["file_name"] = str(EX / pathlib.Path(c["file_name"]).name)
    d["components"] = [c for c in d["components"] if c["type"] != "HVAC_DX_system"]
    zone = next(c["name"] for c in d["components"] if c["type"] == "Load_space")
    d["components"] += [
        {"type": "Boiler", "name": "boiler", "nominal_heating_capacity": 24000,
         "nominal_efficiency": 0.92, "nominal_water_flow": 0.3},
        {"type": "HVAC_water_generator", "name": "gen", "equipment": "boiler"},
        {"type": "HVAC_water_system", "name": "plant", "generators": ["gen"],
         "heating_water_setpoint": "70", "total_water_volume": 30},
        {"type": "Radiator", "name": "panel", "nominal_heat_output": 2000, "radiant_fraction": fraction},
        {"type": "HVAC_radiator_system", "name": "radiators", "space": zone, "radiator": "panel",
         "number_of_units": 2, "water_system": "plant", "heating_setpoint": "20"},
    ]
    return simulate(d), zone


def test_radiant_part_to_the_mass_of_a_load_space():
    convective, zone = load_space_radiators(0.0)
    radiant, _ = load_space_radiators(0.8)
    for pro in (convective, radiant):
        assert values(pro, zone, "temperature").min() > 20 - 0.01
    # the radiant heat warms the thermal mass; the air gets the convective part and,
    # of the radiant part, what the mass gives it in the same time step
    assert values(radiant, zone, "mass_temperature").mean() > values(convective, zone, "mass_temperature").mean()
    b = radiant.component(zone).radiant_to_air()
    assert 0 < b < 1
    Q, Q_r = values(radiant, "radiators", "Q"), values(radiant, "radiators", "Q_radiant")
    assert np.allclose(values(radiant, zone, "u_system_sensible_heat"), Q - Q_r + b * Q_r)
