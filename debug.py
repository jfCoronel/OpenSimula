import OpenSimula as osm
import pandas as pd
import numpy as np

case_ce200_dict = {
    "name": "Case CE200",
    "time_step": 3600,
    "n_time_steps": 8760,
    "initial_time": "01/01/2001 00:00:00",
    "components": [
        {
            "type": "File_met",
            "name": "T_ext_cte",
            "file_type": "TMY2",
            "file_name": "test/CE200A.TM2"
        },    
        {
            "type": "Material",
            "name": "Insulation",
            "conductivity": 0.01,
            "density": 1,
            "specific_heat": 1
        },
        {
            "type": "Construction",
            "name": "Adiabatic_Wall",
            "solar_alpha": [0.1,0.6],
            "lw_epsilon": [0.9,0.9],
            "materials": [
                "Insulation"
            ],
            "thicknesses": [
                1.0
            ]
        },
        {
            "type": "Space_type",
            "name": "constant_gain_space",
            "people_density": "0",
            "light_density": "0",
            "other_gains_density": "165.35",
            "other_gains_radiant_fraction": 0,
            "other_gains_latent_fraction": 0.22893,
            "infiltration": "0"
        },
        {
            "type": "Building",
            "name": "Building",
            "file_met": "T_ext_cte",
            "albedo": 0.2,
            "azimuth": 0,
            "shadow_calculation": "INSTANT"
        },
        {
            "type": "Space",
            "name": "space_1",
            "building": "Building",
            "space_type": "constant_gain_space",
            "floor_area": 48,
            "volume": 129.6,
            "furniture_weight": 0
        },
        {
            "type": "Exterior_surface",
            "name": "north_wall",
            "construction": "Adiabatic_Wall",
            "space": "space_1",
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
                24.17,
                3.16
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "east_wall",
            "construction": "Adiabatic_Wall",
            "space": "space_1",
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
                24.17,
                3.16
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "south_wall",
            "construction": "Adiabatic_Wall",
            "space": "space_1",
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
                24.17,
                3.16
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "west_wall",
            "construction": "Adiabatic_Wall",
            "space": "space_1",
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
                24.17,
                3.16
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "roof_wall",
            "construction": "Adiabatic_Wall",
            "space": "space_1",
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
                24.17,
                1.0
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "floor_wall",
            "construction": "Adiabatic_Wall",
            "space": "space_1",
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
                24.17,
                4.13
            ]
        },
        {
            "type": "HVAC_DX_equipment",
            "name": "HVAC_equipment",
            "nominal_air_flow": 0.4248,
            "nominal_total_cooling_capacity": 7951,
            "nominal_sensible_cooling_capacity": 6136,
            "nominal_cooling_power": 2198,
            "no_load_power": 230,
            "nominal_cooling_conditions": [26.7,19.4,35],
            "total_cooling_capacity_expression": "9.099e-04 * T_odb + 4.351e-02 * T_iwb -3.475e-05 * T_odb^2 + 1.512e-04 * T_iwb^2 -4.703e-04 * T_odb * T_iwb + 4.281e-01",
            "sensible_cooling_capacity_expression": "1.148e-03 * T_odb - 7.886e-02 * T_iwb + 1.044e-01 * T_idb - 4.117e-05 * T_odb^2 - 3.917e-03 * T_iwb^2 - 2.450e-03 * T_idb^2 + 4.042e-04 * T_odb * T_iwb - 4.762e-04 * T_odb * T_idb + 5.503e-03 * T_iwb * T_idb  + 2.903e-01",
            "cooling_power_expression": "1.198e-02 * T_odb + 1.432e-02 * T_iwb + 5.656e-05 * T_odb^2 + 3.725e-05 * T_iwb^2 - 1.840e-04 * T_odb * T_iwb + 3.454e-01",
            "EER_expression": "1 - 0.229*(1-F_load)",
            "expression_max_values": [27,22,50,30,1,1]
        },
        {
            "type": "HVAC_DX_system",
            "name": "system",
            "space": "space_1",
            "file_met": "T_ext_cte",
            "equipment": "HVAC_equipment",
            "supply_air_flow": 0.4248,
            "outdoor_air_flow": 0,
            "heating_setpoint": "20",
            "cooling_setpoint": "26.7",
            "system_on_off": "1",
            "control_type": "PERFECT",
            "relaxing_coefficient": 0.2
        }
    ]
}


sim = osm.Simulation()
pro = sim.new_project("pro")
pro.read_dict(case_ce200_dict)
pro.simulate(1)