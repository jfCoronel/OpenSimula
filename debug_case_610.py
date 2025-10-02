import datetime as dt
import numpy as np
import opensimula as osm

case610_dict = {
    "name": "Case 610",
    "time_step": 3600,
    "n_time_steps": 8760,
    "initial_time": "01/01/2001 00:00:00",
    "simulation_file_met": "Sevilla",
    "components": [
        {
            "type": "File_met",
            "name": "Sevilla",
            "file_type": "MET",
            "file_name": "mets/sevilla.met"
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
            "type": "Construction",
            "name": "Wall",
            "solar_alpha": [
                0.6,
                0.6
            ],
            "materials": [
                "Wood_siding",
                "Fiberglass_quilt",
                "Plasterboard"
            ],
            "thicknesses": [
                0.009,
                0.066,
                0.012
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
                "Timber_flooring"
            ],
            "thicknesses": [
                1.003,
                0.025
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
            "f_tau_nor": "-0.1175 * cos_theta**3 - 1.0295 * cos_theta**2 + 2.1354 * cos_theta",
            "f_1_minus_rho_nor": [
                "1.114 * cos_theta**3 - 3.209 * cos_theta**2 + 3.095 * cos_theta",
                "1.114 * cos_theta**3 - 3.209 * cos_theta**2 + 3.095 * cos_theta"
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
            "type": "Building",
            "name": "Building",
            "azimuth": 0
        },
        {
            "type": "Space",
            "name": "spaces_1",
            "building": "Building",
            "spaces_type": "constant_gain_space",
            "floor_area": 48,
            "volume": 129.6,
            "furniture_weight": 0
        },
        {
            "type": "Building_surface",
            "name": "north_wall",
            "construction": "Wall",
            "spaces": "spaces_1",
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
            "type": "Building_surface",
            "name": "east_wall",
            "construction": "Wall",
            "spaces": "spaces_1",
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
            "type": "Building_surface",
            "name": "south_wall",
            "construction": "Wall",
            "spaces": "spaces_1",
            "ref_point": [
                0,
                0,
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
                0.2
            ],
            "shape": "POLYGON",
            "x_polygon":[0, 3, 3, 0],
            "y_polygon":[0, 0, 2, 2],
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
                0.2
            ],
            "width": 3,
            "height": 2,
            "h_cv": [
                8.0,
                2.4
            ]
        },
        {
            "type": "Building_surface",
            "name": "west_wall",
            "construction": "Wall",
            "spaces": "spaces_1",
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
            "type": "Building_surface",
            "name": "roof_wall",
            "construction": "Roof",
            "spaces": "spaces_1",
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
            "type": "Building_surface",
            "name": "floor_wall",
            "construction": "Floor",
            "spaces": "spaces_1",
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
            "type": "Solar_surface",
            "name": "overhang",
            "coordinate_system": "GLOBAL",
            "ref_point": [
                0,
                -1,
                2.7
            ],
            "calculate_solar_radiation": True,
            "width": 8,
            "height": 1,
            "azimuth": 0,
            "altitude": 90
        },
        {
            "type": "HVAC_perfect_system",
            "name": "system",
            "spaces": "spaces_1",
            "outdoor_air_flow": "0",
            "heating_setpoint": "20",
            "cooling_setpoint": "27",
            "system_on_off": "1"
        }
    ]
}


sim = osm.Simulation()
pro = sim.new_project("pro")
pro.read_dict(case610_dict)
#pro.show_3D()
date = dt.datetime(2001,3,21,12,0,0)
#pro.show_3D_shadows(date)
pro.show_3D_shadows_animation(date)
pro.simulate()


# Heating and Cooling Loads
load = pro.component("spaces_1").variable("system_sensible_heat").values
annual_heating = np.where(load>0,load,0).sum()/1e6
annual_cooling = np.where(load<0,-load,0).sum()/1e6
peak_heating = load.max()/1000
peak_cooling = -load.min()/1000

print(f"Annual heating load: {annual_heating:.4f} MWh")
print(f"Peak heating load: {peak_heating:.4f} kW")
print(f"Annual cooling load: {annual_cooling:.4f} MWh")
print(f"Peak cooling load: {peak_cooling:.4f} kW")
