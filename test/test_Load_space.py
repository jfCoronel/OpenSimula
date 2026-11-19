import pathlib

import numpy as np

import opensimula as osm

EXAMPLES = pathlib.Path(osm.__file__).parent / "examples"


def run(components, n=200):
    """A one-week project in Sevilla with the components given."""
    sim = osm.Simulation()
    sim.console_print = False
    pro = sim.new_project("p")
    pro.read_dict({
        "name": "p",
        "time_step": 3600,
        "n_time_steps": n,
        "initial_time": "01/01/2001 00:00:00",
        "simulation_file_met": "sevilla",
        "components": [{"type": "File_met", "name": "sevilla", "file_type": "MET",
                        "file_name": str(EXAMPLES / "sevilla.met")}] + components,
    })
    errors = [m.text for m in sim.message_list() if m.level == "ERROR"]
    assert not errors, errors
    pro.simulate(progress=lambda i, n: None)
    return pro


def zone(**parameters):
    return {"type": "Load_space", "name": "zone"} | parameters


def ideal(**setpoints):
    return {"type": "HVAC_perfect_system", "name": "ideal", "spaces": "zone",
            "heating_setpoint": "24", "cooling_setpoint": "24",
            "humidifying_setpoint": "50", "dehumidifying_setpoint": "50"} | setpoints


def values(pro, component, variable):
    return pro.component(component).variable(variable).values


def test_ideal_system_supplies_the_record():
    # at the reference conditions the system supplies exactly the loads
    pro = run([zone(sensible_load="1500", latent_load="-200"), ideal()])
    assert np.allclose(values(pro, "zone", "temperature"), 24)
    assert np.allclose(values(pro, "zone", "rel_humidity"), 50, atol=1e-6)
    assert np.allclose(values(pro, "zone", "system_sensible_heat"), 1500)
    assert np.allclose(values(pro, "zone", "system_latent_heat"), -200)
    assert np.allclose(values(pro, "zone", "unmet_sensible_heat"), 0, atol=1e-6)


def test_infiltration_correction():
    # simulated infiltration different from the record's: the load changes by the
    # infiltration difference at the reference temperature
    pro = run([zone(sensible_load="1000", load_infiltration="0.5", infiltration="2"), ideal()])
    props = pro._sim_.props
    V = 100 * 2.7
    T_ext = values(pro, "sevilla", "temperature")
    expected = 1000 + props["RHO_A"] * props["C_PA"] * V * 1.5 / 3600 * (24 - T_ext)
    assert np.allclose(values(pro, "zone", "system_sensible_heat"), expected)
    assert np.allclose(values(pro, "zone", "sensible_load"), expected)
    assert np.allclose(values(pro, "zone", "temperature"), 24)


def test_free_floating_steady_state():
    # a constant heating load with no system: the zone settles below the reference by
    # Q / (H_ao + H_inf + H_am·H_mo / (H_am + H_mo)); no infiltration, so no weather
    pro = run([zone(sensible_load="1000", load_infiltration="0", infiltration="0",
                    construction="VERY_LIGHT")], n=8000)
    area, U = 100, 1.0
    H_ao = H_mo = U * area / 2
    H_am = 9.1 * 2.5 * area
    theta = -1000 / (H_ao + H_am * H_mo / (H_am + H_mo))
    T = values(pro, "zone", "temperature")
    assert abs(T[-1] - (24 + theta)) < 0.05
    # first hour: much smaller, the air and the mass take the heat
    assert 24 + theta < T[0] < 24
    assert np.all(np.diff(T) <= 1e-9)
    assert np.allclose(values(pro, "zone", "unmet_sensible_heat"), 1000)


def test_heavier_responds_slower():
    T = {}
    for construction in ("VERY_LIGHT", "VERY_HEAVY"):
        pro = run([zone(sensible_load="-2000", construction=construction)], n=24)
        T[construction] = values(pro, "zone", "temperature")
    assert np.all(T["VERY_HEAVY"] < T["VERY_LIGHT"])
    assert np.all(T["VERY_HEAVY"] > 24)


def test_any_time_step():
    # the same 6 hours with steps of 1 h and of 10 min end at nearly the same temperature
    end = {}
    for step, n in ((3600, 6), (600, 36)):
        sim = osm.Simulation()
        sim.console_print = False
        pro = sim.new_project("p")
        pro.read_dict({"name": "p", "time_step": step, "n_time_steps": n,
                       "initial_time": "01/01/2001 00:00:00", "simulation_file_met": "sevilla",
                       "components": [{"type": "File_met", "name": "sevilla", "file_type": "MET",
                                       "file_name": str(EXAMPLES / "sevilla.met")},
                                      zone(sensible_load="-2000", infiltration="0", load_infiltration="0")]})
        pro.simulate(progress=lambda i, n: None)
        end[step] = values(pro, "zone", "temperature")[-1]
    assert abs(end[3600] - end[600]) < 0.3


def test_air_systems_accept_a_load_space():
    pro = run([
        zone(sensible_load="-3000"),
        {"type": "DX_unit", "name": "unit", "nominal_air_flow": 0.4,
         "nominal_total_cooling_capacity": 6000, "nominal_sensible_cooling_capacity": 4500,
         "nominal_cooling_power": 2000},
        {"type": "HVAC_DX_system", "name": "dx", "equipment": "unit", "spaces": "zone",
         "air_flow": 0.4, "outdoor_air_fraction": "0"},
    ], n=24)
    # the DX unit cools: the zone stays at the cooling setpoint (25 °C) instead of warming up
    # at 25 °C, 1 K above the reference, the zone loses part of the load: the unit ends
    # supplying a little less than 3000 W
    assert np.allclose(values(pro, "zone", "temperature")[2:], 25, atol=0.05)
    assert 2700 < values(pro, "dx", "Q_sensible")[-1] < 3000
