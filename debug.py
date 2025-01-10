import OpenSimula as osm
import numpy as np

case960_dict = {
    "name": "Case 960",
    "time_step": 3600,
    "n_time_steps": 8760,
    "initial_time": "01/01/2001 00:00:00",
    "components": [
        {
            "type": "File_met",
            "name": "Denver",
            "file_type": "TMY3",
            "file_name": "test/WD100.tmy3"
        },
        {
            "type": "Material",
            "name": "Concrete_block",
            "conductivity": 0.51,
            "density": 1400,
            "specific_heat": 1000
        },
        {
            "type": "Material",
            "name": "Concrete_slab",
            "conductivity": 1.13,
            "density": 1400,
            "specific_heat": 1000
        },
        {
            "type": "Material",
            "name": "Plasterboard",
            "conductivity": 0.16,
            "density": 950,
            "specific_heat": 840
        },
        {
            "type": "Material",
            "name": "Fiberglass_quilt",
            "conductivity": 0.04,
            "density": 12,
            "specific_heat": 840
        },
        {
            "type": "Material",
            "name": "Wood_siding",
            "conductivity": 0.14,
            "density": 530,
            "specific_heat": 900
        },
        {
            "type": "Material",
            "name": "Foam_insulation",
            "conductivity": 0.04,
            "density": 10,
            "specific_heat": 1400
        },
        {
            "type": "Material",
            "name": "Insulation",
            "conductivity": 0.04,
            "density": 0.1,
            "specific_heat": 0.1
        },
        {
            "type": "Material",
            "name": "Timber_flooring",
            "conductivity": 0.14,
            "density": 650,
            "specific_heat": 1200
        },
        {
            "type": "Material",
            "name": "Roofdeck",
            "conductivity": 0.14,
            "density": 530,
            "specific_heat": 900
        },
        {
            "type": "Material",
            "name": "interior_wall_material",
            "conductivity": 0.510,
            "density": 1400,
            "specific_heat": 1000
        },
        {
            "type": "Construction",
            "name": "Wall",
            "solar_alpha": [
                0.6,
                0.6
            ],
            "materials": [
                "Wood_siding",
                "Foam_insulation",
                "Concrete_block"
            ],
            "thicknesses": [
                0.009,
                0.0615,
                0.100
            ]
        },
        {
            "type": "Construction",
            "name": "Floor",
            "solar_alpha": [
                0,
                0.6
            ],
            "materials": [
                "Insulation",
                "Concrete_slab"
            ],
            "thicknesses": [
                1.007,
                0.080
            ]
        },
        {
            "type": "Construction",
            "name": "Roof",
            "solar_alpha": [
                0.6,
                0.6
            ],
            "materials": [
                "Roofdeck",
                "Fiberglass_quilt",
                "Plasterboard"
            ],
            "thicknesses": [
                0.019,
                0.1118,
                0.010
            ]
        },
        {
            "type": "Construction",
            "name": "interior_wall_const",
            "solar_alpha": [
                0.6,
                0.6
            ],
            "materials": [
                "interior_wall_material"
            ],
            "thicknesses": [
                0.20
            ]
        },
        {
            "type": "Glazing",
            "name": "double_glazing",
            "solar_tau": 0.703,
            "solar_rho": [
                0.128,
                0.128
            ],
            "g": [
                0.769,
                0.769
            ],
            "lw_epsilon": [
                0.84,
                0.84
            ],
            "U": 2.722,
            "f_tau_nor": "-0.1175 * cos_theta^3 - 1.0295 * cos_theta^2 + 2.1354 * cos_theta",
            "f_1_minus_rho_nor": [
                "1.114 * cos_theta^3 - 3.209 * cos_theta^2 + 3.095 * cos_theta",
                "1.114 * cos_theta^3 - 3.209 * cos_theta^2 + 3.095 * cos_theta"
            ]
        },
        {
            "type": "Opening_type",
            "name": "Window",
            "glazing": "double_glazing",
            "frame_fraction": 0,
            "glazing_fraction": 1
        },
        {
            "type": "Space_type",
            "name": "constant_gain_space",
            "people_density": "0",
            "light_density": "0",
            "other_gains_density": "4.1667",
            "other_gains_radiant_fraction": 0.6,
            "infiltration": "0.5"
        },
        {
            "type": "Space_type",
            "name": "sun_zone_gains",
            "people_density": "0",
            "light_density": "0",
            "other_gains_density": "0",
            "infiltration": "0.5"
        },
        {
            "type": "Building",
            "name": "Building",
            "file_met": "Denver",
            "albedo": 0.2,
            "azimuth": 0,
            "shadow_calculation": "INSTANT"
        },
        {
            "type": "Space",
            "name": "back_zone",
            "building": "Building",
            "space_type": "constant_gain_space",
            "floor_area": 48,
            "volume": 129.6,
            "furniture_weight": 0
        },
        {
            "type": "Space",
            "name": "sun_zone",
            "building": "Building",
            "space_type": "sun_zone_gains",
            "floor_area": 16,
            "volume": 43.2,
            "furniture_weight": 0
        },
        {
            "type": "Exterior_surface",
            "name": "north_wall",
            "construction": "Wall",
            "space": "back_zone",
            "ref_point": [
                8,
                6,
                0
            ],
            "width": 8,
            "height": 2.7,
            "azimuth": 180,
            "altitude": 0,
            "h_cv": [
                11.9,
                2.2
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "east_wall",
            "construction": "Wall",
            "space": "back_zone",
            "ref_point": [
                8,
                0,
                0
            ],
            "width": 6,
            "height": 2.7,
            "azimuth": 90,
            "altitude": 0,
            "h_cv": [
                11.9,
                2.2
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "east_wall_2",
            "construction": "Wall",
            "space": "sun_zone",
            "ref_point": [
                8,
                -2,
                0
            ],
            "width": 2,
            "height": 2.7,
            "azimuth": 90,
            "altitude": 0,
            "h_cv": [
                11.9,
                2.2
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "south_wall",
            "construction": "Wall",
            "space": "sun_zone",
            "ref_point": [
                0,
                -2,
                0
            ],
            "width": 8,
            "height": 2.7,
            "azimuth": 0,
            "altitude": 0,
            "h_cv": [
                11.9,
                2.2
            ]
        },
        {
            "type": "Opening",
            "name": "south_window_1",
            "surface": "south_wall",
            "opening_type": "Window",
            "ref_point": [
                0.5,
                0.5
            ],
            "width": 3,
            "height": 2,
            "h_cv": [
                8.0,
                2.4
            ]
        },
        {
            "type": "Opening",
            "name": "south_window_2",
            "surface": "south_wall",
            "opening_type": "Window",
            "ref_point": [
                4.5,
                0.5
            ],
            "width": 3,
            "height": 2,
            "h_cv": [
                8.0,
                2.4
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "west_wall",
            "construction": "Wall",
            "space": "back_zone",
            "ref_point": [
                0,
                6,
                0
            ],
            "width": 6,
            "height": 2.7,
            "azimuth": -90,
            "altitude": 0,
            "h_cv": [
                11.9,
                2.2
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "west_wall_2",
            "construction": "Wall",
            "space": "sun_zone",
            "ref_point": [
                0,
                0,
                0
            ],
            "width": 2,
            "height": 2.7,
            "azimuth": -90,
            "altitude": 0,
            "h_cv": [
                11.9,
                2.2
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "roof_wall",
            "construction": "Roof",
            "space": "back_zone",
            "ref_point": [
                0,
                0,
                2.7
            ],
            "width": 8,
            "height": 6,
            "azimuth": 0,
            "altitude": 90,
            "h_cv": [
                14.4,
                1.8
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "roof_wall_2",
            "construction": "Roof",
            "space": "sun_zone",
            "ref_point": [
                0,
                -2,
                2.7
            ],
            "width": 8,
            "height": 2,
            "azimuth": 0,
            "altitude": 90,
            "h_cv": [
                14.4,
                1.8
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "floor_wall",
            "construction": "Floor",
            "space": "back_zone",
            "ref_point": [
                0,
                6,
                0
            ],
            "width": 8,
            "height": 6,
            "azimuth": 0,
            "altitude": -90,
            "h_cv": [
                0.8,
                2.2
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "floor_wall_2",
            "construction": "Floor",
            "space": "sun_zone",
            "ref_point": [
                0,
                0,
                0
            ],
            "width": 8,
            "height": 2,
            "azimuth": 0,
            "altitude": -90,
            "h_cv": [
                0.8,
                2.2
            ]
        },
        {
            "type": "Interior_surface",
            "name": "interior_wall",
            "construction": "interior_wall_const",
            "spaces": ["sun_zone","back_zone"],
            "ref_point": [0,0,0],
            "width": 8,
            "height": 2.7,
            "azimuth": 0,
            "altitude": 0,
            "h_cv": [
                2.2,
                2.2
            ]
        },
        {
            "type": "HVAC_perfect_system",
            "name": "back_system",
            "space": "back_zone",
            "file_met": "Denver",
            "outdoor_air_flow": "0",
            "heating_setpoint": "20",
            "cooling_setpoint": "27",
            "humidifying_setpoint": "0",
            "dehumidifying_setpoint": "100",
            "system_on_off": "1"
        },
        {
            "type": "HVAC_perfect_system",
            "name": "sun_system",
            "space": "sun_zone",
            "file_met": "Denver",
            "outdoor_air_flow": "0",
            "heating_setpoint": "20",
            "cooling_setpoint": "27",
            "humidifying_setpoint": "0",
            "dehumidifying_setpoint": "100",
            "system_on_off": "1"
        }
    ]
}


sim = osm.Simulation()
pro = sim.new_project("pro")
pro.read_dict(case960_dict)
pro.simulate()