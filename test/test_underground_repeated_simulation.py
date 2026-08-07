import opensimula as osim
import numpy as np


# UNDERGROUND surfaces build their construction at pre_simulation time, by
# duplicating the one defined by the user and adding the ground and virtual
# layers to the copy. If the copy shares its layer lists with the original, the
# original grows on every simulation and ends up inconsistent, so simulating
# twice in the same process (a Jupyter kernel, for instance) fails.
underground_dict = {
    "name": "Underground test",
    "time_step": 3600,
    "n_time_steps": 48,
    "initial_time": "01/01/2001 00:00:00",
    "simulation_file_met": "Denver",
    "shadow_calculation": "NO",
    "components": [
        {
            "type": "File_met",
            "name": "Denver",
            "file_type": "TMY3",
            "file_name": "mets/WD100.tmy3",
        },
        {
            "type": "Material",
            "name": "Concrete",
            "conductivity": 1.13,
            "density": 1400,
            "specific_heat": 1000,
        },
        {
            "type": "Material",
            "name": "Insulation",
            "conductivity": 0.04,
            "density": 10,
            "specific_heat": 1400,
        },
        {
            "type": "Material",
            "name": "Soil",
            "conductivity": 1.9,
            "density": 1490,
            "specific_heat": 1800,
        },
        {
            "type": "Construction",
            "name": "Slab",
            "solar_alpha": [0.6, 0.6],
            "materials": ["Concrete", "Insulation"],
            "thicknesses": [0.08, 0.1],
        },
        {
            "type": "Construction",
            "name": "Wall",
            "solar_alpha": [0.6, 0.6],
            "materials": ["Concrete", "Insulation"],
            "thicknesses": [0.1, 0.06],
        },
        {
            "type": "Space_type",
            "name": "Simple gains",
            "people_density": "0",
            "light_density": "0",
            "other_gains_density": "4.1667",
            "other_gains_radiant_fraction": 0.6,
            "infiltration": "0.5",
        },
        {"type": "Building", "name": "Building", "azimuth": 0, "ref_point": [0, 0, 0]},
        {
            "type": "Space",
            "name": "Zone",
            "building": "Building",
            "spaces_type": "Simple gains",
            "floor_area": 48,
            "volume": 129.6,
        },
        {
            "type": "Building_surface",
            "name": "Floor",
            "surface_type": "UNDERGROUND",
            "spaces": ["Zone"],
            "construction": "Slab",
            "ground_material": "Soil",
            "ref_point": [0, 0, 0],
            "width": 8,
            "height": 6,
            "azimuth": 0,
            "altitude": -90,
        },
        {
            "type": "Building_surface",
            "name": "Roof",
            "surface_type": "EXTERIOR",
            "spaces": ["Zone"],
            "construction": "Wall",
            "ref_point": [0, 6, 2.7],
            "width": 8,
            "height": 6,
            "azimuth": 0,
            "altitude": 90,
        },
        {
            "type": "Building_surface",
            "name": "South",
            "surface_type": "EXTERIOR",
            "spaces": ["Zone"],
            "construction": "Wall",
            "ref_point": [0, 0, 0],
            "width": 8,
            "height": 2.7,
            "azimuth": 0,
            "altitude": 0,
        },
        {
            "type": "Building_surface",
            "name": "North",
            "surface_type": "EXTERIOR",
            "spaces": ["Zone"],
            "construction": "Wall",
            "ref_point": [8, 6, 0],
            "width": 8,
            "height": 2.7,
            "azimuth": 180,
            "altitude": 0,
        },
        {
            "type": "Building_surface",
            "name": "East",
            "surface_type": "EXTERIOR",
            "spaces": ["Zone"],
            "construction": "Wall",
            "ref_point": [8, 0, 0],
            "width": 6,
            "height": 2.7,
            "azimuth": 90,
            "altitude": 0,
        },
        {
            "type": "Building_surface",
            "name": "West",
            "surface_type": "EXTERIOR",
            "spaces": ["Zone"],
            "construction": "Wall",
            "ref_point": [0, 6, 0],
            "width": 6,
            "height": 2.7,
            "azimuth": -90,
            "altitude": 0,
        },
    ],
}


def _project():
    sim = osim.Simulation()
    pro = sim.new_project("pro")
    pro.read_dict(underground_dict)
    return pro


def test_underground_does_not_grow_its_construction():
    pro = _project()
    slab = pro.component("Slab")
    n_materials = len(slab.parameter("materials").value)
    n_thicknesses = len(slab.parameter("thicknesses").value)

    pro.simulate()

    assert len(slab.parameter("materials").value) == n_materials
    assert len(slab.parameter("thicknesses").value) == n_thicknesses


def test_simulating_twice_gives_the_same_result():
    pro = _project()

    pro.simulate()
    first = pro.component("Floor").variable("T_s0").values.copy()
    pro.simulate()
    second = pro.component("Floor").variable("T_s0").values.copy()

    assert np.array_equal(first, second)


def test_list_parameters_do_not_alias_the_assigned_list():
    pro = _project()
    slab = pro.component("Slab")

    materials = ["Concrete", "Insulation"]
    slab.parameter("materials").value = materials
    materials.append("Soil")

    assert slab.parameter("materials").value == ["Concrete", "Insulation"]


def test_duplicated_component_is_independent():
    pro = _project()
    copy = pro.duplicate_component("Slab", "Slab copy")

    copy.add_exterior_layer("Soil", 0.5)

    assert len(pro.component("Slab").parameter("materials").value) == 2
    assert len(copy.parameter("materials").value) == 3
