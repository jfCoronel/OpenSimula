"""HVAC_radiant_floor_system: pipes in the heat source plane of the floor construction
(Construction.source_layer), fed by a water plant."""

import numpy as np
import pytest

import opensimula as osm
from test_construction_source import fd
from test_radiators import office, simulate, values

FLOOR = [("floor_insulation", 0.05, 0.035, 30, 1400), ("screed", 0.03, 1.4, 2000, 1000),
         ("screed", 0.03, 1.4, 2000, 1000), ("tile", 0.01, 1.3, 2300, 840)]
WALLS = ["south_wall", "east_wall", "north_wall", "west_wall", "roof_surface", "floor_surface"]


def floor_office(water="40", control="PROPORTIONAL", days=10, flow=0.15):
    """The office of example 04 with a radiant floor (pipes 6 cm under the tiles) and a
    boiler at 40 °C."""
    d = office(water=water, days=days)
    d["components"] = [c for c in d["components"] if c["type"] not in ("Radiator", "HVAC_radiator_system")]
    for c in d["components"]:
        if c["name"] == "floor":
            c["materials"] = [layer[0] for layer in FLOOR]
            c["thicknesses"] = [layer[1] for layer in FLOOR]
            c["source_layer"] = 2
        if c["name"] == "floor_insulation":
            c.update({"conductivity": 0.035, "density": 30, "specific_heat": 1400})
    d["components"] += [
        {"type": "Material", "name": "screed", "conductivity": 1.4, "density": 2000, "specific_heat": 1000},
        {"type": "Material", "name": "tile", "conductivity": 1.3, "density": 2300, "specific_heat": 840},
        {"type": "HVAC_radiant_floor_system", "name": "floor_heating", "space": "office",
         "surfaces": ["floor_surface"], "water_system": "plant", "nominal_water_flow": flow,
         "heating_setpoint": "20", "control": control},
    ]
    return d


def test_the_construction_follows_the_finite_differences():
    """With the surface temperatures and the source of the simulation, a fine
    finite-difference model of the floor gives the same fluxes and plane temperature."""
    pro = simulate(floor_office())
    T_ini = pro.component("building").parameter("initial_temperature").value
    q_s = values(pro, "floor_surface", "q_source")
    assert q_s.max() > 50
    T_0 = values(pro, "floor_surface", "T_s0") - T_ini
    T_1 = values(pro, "floor_surface", "T_s1") - T_ini
    layers = [(L, k, rho * c) for _, L, k, rho, c in FLOOR]
    H = 24 * 5
    inputs = (np.r_[0, q_s[:H]], np.r_[0, T_0[:H]], np.r_[0, T_1[:H]])
    # the finite differences converge with order 1: extrapolated from two meshes
    coarse = fd(layers, 2, *inputs, dt=20, nodes_per_cm=2)
    fine = fd(layers, 2, *inputs, dt=10, nodes_per_cm=4)
    ref = 2 * fine - coarse
    assert np.allclose(values(pro, "floor_surface", "T_source")[:H] - T_ini, ref[:, 2], atol=0.005)
    assert np.allclose(values(pro, "floor_surface", "q_cd1")[:H], ref[:, 1], atol=0.05)
    assert np.allclose(values(pro, "floor_surface", "q_cd0")[:H], ref[:, 0], atol=0.05)
    assert np.allclose(values(pro, "floor_heating", "T_source"), values(pro, "floor_surface", "T_source"))


def test_balance_of_the_air():
    """The heat of the floor reaches the air only through the surfaces: the air balance
    (capacity, convection of the surfaces, gains, infiltration) holds without it."""
    pro = simulate(floor_office())
    props = pro._sim_.props
    C = 129.6 * props["RHO_A"] * props["C_PA"] + 10 * props["C_P_FURNITURE"]
    T_ini = pro.component("building").parameter("initial_temperature").value
    T = values(pro, "office", "temperature")
    convection = -sum(pro.component(n).area * values(pro, n, "q_cv1") for n in WALLS)
    for o in pro.component_list(comp_type="Opening"):
        convection -= o.area * np.asarray(o.variable("q_cv1").values)
    gains = sum(values(pro, "office", v) for v in ("people_convective", "other_gains_convective",
                                                     "light_convective"))
    met = pro.parameter("simulation_file_met").component
    T_ext = np.asarray(met.variable("temperature").values)[:len(T)]
    infiltration = values(pro, "office", "infiltration_flow") * props["RHO_A"] * props["C_PA"] * (T_ext - T)
    residual = C * (T - np.r_[T_ini, T[:-1]]) / 3600 - convection - gains - infiltration
    assert np.abs(residual).max() < 1e-6
    # for the zone the floor is a system: the heat it gives to the air in the time step
    assert values(pro, "floor_heating", "Q").sum() > 0
    assert np.all(values(pro, "office", "u_system_sensible_heat") >= -1e-9)


def test_water_side_and_plant():
    pro = simulate(floor_office())
    Q = values(pro, "floor_heating", "Q")
    on = Q > 0
    assert np.allclose(Q, values(pro, "floor_heating", "q_source") * 48)
    assert np.allclose(-values(pro, "plant", "Q_heating_coils"), Q)
    rho_cp = pro._sim_.props["RHOCP_W"](40) / 1000
    heat = rho_cp * values(pro, "floor_heating", "water_flow") * (
        values(pro, "floor_heating", "T_wi") - values(pro, "floor_heating", "T_wo"))
    assert np.allclose(heat[on], Q[on], rtol=1e-6)
    # the water leaves between the temperature of the plane and that it came
    T_wo = values(pro, "floor_heating", "T_wo")[on]
    assert np.all(T_wo >= values(pro, "floor_heating", "T_source")[on] - 1e-9)
    assert np.all(T_wo < 40)
    p = "plant"
    balance = (values(pro, p, "Q_generators") + values(pro, p, "Q_loads") + values(pro, p, "Q_loss")
               + values(pro, p, "Q_pump") - values(pro, p, "delta_U"))
    assert abs(balance.sum()) < 1e-3 * values(pro, p, "Q_generators").sum()


def test_thermostat_and_water_temperature():
    pro = simulate(floor_office())
    T = values(pro, "office", "temperature")
    valve = values(pro, "floor_heating", "valve")
    # proportional valve: fully open below 19 °C, closed above 21 °C
    partly = (valve > 0) & (valve < 1)
    assert partly.sum() > 0
    assert np.allclose(valve[partly], (21 - T[partly]) / 2)
    assert T.min() > 19
    # always open: more heat; colder water: less heat
    always = simulate(floor_office(control="NONE"))
    assert values(always, "floor_heating", "Q").sum() > 1.5 * values(pro, "floor_heating", "Q").sum()
    cold = simulate(floor_office(water="30"))
    assert values(cold, "floor_heating", "Q").max() < values(pro, "floor_heating", "Q").max()


def test_off_and_checks():
    data = floor_office(days=2)
    for c in data["components"]:
        if c["name"] == "floor_heating":
            c["system_on_off"] = "0"
    pro = simulate(data)
    assert np.all(values(pro, "floor_heating", "Q") == 0)
    assert np.all(values(pro, "floor_surface", "q_source") == 0)
    # a surface without source
    data = floor_office(days=2)
    for c in data["components"]:
        if c["name"] == "floor_heating":
            c["surfaces"] = ["floor_surface", "south_wall"]
    sim = osm.Simulation()
    sim.console_print = False
    p = sim.new_project("p")
    p.read_dict(data)
    assert any("south_wall" in m.text and "source_layer" in m.text
               for m in p.check() if m.level == "ERROR")


def test_exterior_layers_keep_the_source_plane():
    """The underground surfaces add two exterior layers to their construction: the source
    stays in the same plane."""
    sim = osm.Simulation()
    p = sim.new_project("p")
    p.new_component("Material", "m")
    c = p.new_component("Construction", "c")
    c.set_parameters({"materials": ["m", "m"], "thicknesses": [0.1, 0.1], "source_layer": 1})
    c.add_exterior_layer("m", 0.5)
    assert c.parameter("source_layer").value == 2


# _________________ a floor between two zones _________________

def two_floors(days=10):
    """The office with another one above it, heated by a radiant floor in the slab
    between them (side 0 the office below, side 1 the office above)."""
    d = floor_office(days=days)
    d["components"] = [c for c in d["components"] if c["name"] != "floor_heating"]
    d["components"] += [
        {"type": "Material", "name": "concrete", "conductivity": 1.65, "density": 2300, "specific_heat": 1000},
        {"type": "Construction", "name": "slab", "materials": ["concrete", "floor_insulation", "screed",
                                                               "screed", "tile"],
         "thicknesses": [0.2, 0.03, 0.03, 0.03, 0.01], "source_layer": 3},
        {"type": "Space", "name": "upper", "building": "building", "spaces_type": "office_use",
         "floor_area": 48, "volume": 129.6, "furniture_weight": 10},
    ]
    for c in d["components"]:
        if c["name"] == "roof_surface":
            c.update({"construction": "slab", "spaces": ["office", "upper"], "surface_type": "INTERIOR"})
    for name, ref, width, azimuth in (("south", [0, 0], 8, 0), ("east", [8, 0], 6, 90),
                                      ("north", [8, 6], 8, 180), ("west", [0, 6], 6, -90)):
        d["components"].append({"type": "Building_surface", "name": f"upper_{name}", "construction": "wall",
                                "spaces": "upper", "ref_point": ref + [2.7], "width": width,
                                "height": 2.7, "azimuth": azimuth, "altitude": 0})
    d["components"] += [
        {"type": "Building_surface", "name": "upper_roof", "construction": "roof", "spaces": "upper",
         "ref_point": [0, 0, 5.4], "width": 8, "height": 6, "azimuth": 0, "altitude": 90},
        {"type": "HVAC_radiant_floor_system", "name": "floor_heating", "space": "upper",
         "surfaces": ["roof_surface"], "water_system": "plant", "nominal_water_flow": 0.15,
         "heating_setpoint": "20"},
    ]
    return d


def test_floor_between_two_zones():
    pro = simulate(two_floors())
    Q = values(pro, "floor_heating", "Q")
    assert Q.sum() > 0
    T_upper, T_office = values(pro, "upper", "temperature"), values(pro, "office", "temperature")
    assert T_upper.min() > 19
    # the heat of the source goes up and, through the insulation, a little down: the
    # office below, without heating, is warmer than without the floor of the upper one
    data = two_floors()
    for c in data["components"]:
        if c["name"] == "floor_heating":
            c["system_on_off"] = "0"
    off = simulate(data)
    up = (values(pro, "roof_surface", "q_cd1") - values(off, "roof_surface", "q_cd1")).sum()
    down = (values(pro, "roof_surface", "q_cd0") - values(off, "roof_surface", "q_cd0")).sum()
    assert up > 2 * down > 0
    assert T_office.mean() > values(off, "office", "temperature").mean()
    # air balance of the office below (the source reaches it through its ceiling)
    props = pro._sim_.props
    C = 129.6 * props["RHO_A"] * props["C_PA"] + 10 * props["C_P_FURNITURE"]
    T_ini = pro.component("building").parameter("initial_temperature").value
    names = ["south_wall", "east_wall", "north_wall", "west_wall", "floor_surface"]
    convection = -sum(pro.component(n).area * values(pro, n, "q_cv1") for n in names)
    convection -= pro.component("roof_surface").area * values(pro, "roof_surface", "q_cv0")
    for o in pro.component_list(comp_type="Opening"):
        convection -= o.area * np.asarray(o.variable("q_cv1").values)
    gains = sum(values(pro, "office", v) for v in ("people_convective", "other_gains_convective",
                                                     "light_convective"))
    met = pro.parameter("simulation_file_met").component
    T_ext = np.asarray(met.variable("temperature").values)[:len(T_office)]
    infiltration = values(pro, "office", "infiltration_flow") * props["RHO_A"] * props["C_PA"] * (T_ext - T_office)
    residual = C * (T_office - np.r_[T_ini, T_office[:-1]]) / 3600 - convection - gains - infiltration
    # (the source of the upper zone reaches the office through the iterations of the step)
    assert np.abs(residual).max() < 0.01
    assert np.all(values(pro, "office", "u_system_sensible_heat") == 0)
