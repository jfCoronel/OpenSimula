import OpenSimula as osm

case_AE303 = {
    "name": "case_AE303",
    "time_step": 3600,
    "n_time_steps": 8760,
    "initial_time": "01/01/2001 00:00:00",
    "simulation_file_met": "T_ext_cte",
    "components": [
        {
            "type": "File_met",
            "name": "T_ext_cte",
            "file_type": "TMY2",
            "file_name": "mets/AE103.TM2"
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
            "name": "constant_gain_1",
            "people_density": "1",
            "people_sensible": 0,
            "people_latent": 12.21,
            "light_density": "0",
            "other_gains_density": "30.521",
            "other_gains_radiant_fraction": 0,
            "infiltration": "0"
        },
        {
            "type": "Space_type",
            "name": "constant_gain_2",
            "people_density": "1",
            "people_sensible": 0,
            "people_latent": 18.31667,
            "light_density": "0",
            "other_gains_density": "48.8542",
            "other_gains_radiant_fraction": 0,
            "infiltration": "0"
        },
        {
            "type": "Building",
            "name": "Building",
            "albedo": 0.2,
            "azimuth": 0,
            "shadow_calculation": "INSTANT"
        },
        {
            "type": "Space",
            "name": "space_1",
            "building": "Building",
            "space_type": "constant_gain_1",
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
            "type": "Space",
            "name": "space_2",
            "building": "Building",
            "space_type": "constant_gain_2",
            "floor_area": 48,
            "volume": 129.6,
            "furniture_weight": 0
        },
        {
            "type": "Exterior_surface",
            "name": "north_wall_2",
            "construction": "Adiabatic_Wall",
            "space": "space_2",
            "ref_point": [
                108,
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
            "name": "east_wall_2",
            "construction": "Adiabatic_Wall",
            "space": "space_2",
            "ref_point": [
                108,
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
            "name": "south_wall_2",
            "construction": "Adiabatic_Wall",
            "space": "space_2",
            "ref_point": [
                100,
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
            "name": "west_wall_2",
            "construction": "Adiabatic_Wall",
            "space": "space_2",
            "ref_point": [
                100,
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
            "name": "roof_wall_2",
            "construction": "Adiabatic_Wall",
            "space": "space_2",
            "ref_point": [
                100,
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
            "name": "floor_wall_2",
            "construction": "Adiabatic_Wall",
            "space": "space_2",
            "ref_point": [
                100,
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
            "type": "HVAC_fan_equipment",
            "name": "supply_fan",
            "nominal_air_flow": 0.60296,
            "nominal_pressure": 498,
            "nominal_power": 436.483,
        },
        {
            "type": "HVAC_coil_equipment",
            "name": "coil",
            "nominal_air_flow": 0.60296,
            "nominal_heating_capacity": 0,
            "nominal_total_cooling_capacity": 14328,
            "nominal_sensible_cooling_capacity": 10460,
            "nominal_cooling_water_flow": 6.83e-4
        },
        {
            "type": "HVAC_coil_equipment",
            "name": "reheat_coil_1",
            "nominal_air_flow": 0.27829,
            "nominal_heating_capacity": 10000,
            "nominal_heating_water_flow": 0.556e-3,
            "nominal_total_cooling_capacity": 0,
            "nominal_sensible_cooling_capacity": 0,
        },
        {
            "type": "HVAC_coil_equipment",
            "name": "reheat_coil_2",
            "nominal_air_flow": 0.32467,
            "nominal_heating_capacity": 10000,
            "nominal_heating_water_flow": 0.556e-3,
            "nominal_total_cooling_capacity": 0,
            "nominal_sensible_cooling_capacity": 0,
        },
        {
           "type": "HVAC_MZW_system",
            "name": "system",
            "spaces": ["space_1","space_2"],
            "air_flow_fractions": [0.46154, 0.53846],
            "return_air_flow_fractions": [0.5, 0.5],
            "return_fan": "supply_fan",
            "cooling_coil": "coil",
            "supply_fan": "supply_fan",
            "air_flow": 0.60296,
            "outdoor_air_fraction": 0.38461,
            "cooling_water_flow": 6.83e-4,
            "heating_water_flow": 0,
            "supply_cooling_setpoint": "12.78",
            "supply_heating_setpoint": "7.7835",
            "system_on_off": "1",
            "terminal_units": "REHEAT_COILS",
            "reheat_coils": ["reheat_coil_1","reheat_coil_2"],
            "spaces_setpoint": ["23.333","24.444"]
        }
    ]
}

sim = osm.Simulation()
pro = sim.new_project("pro")
pro.read_dict(case_AE303)
pro.simulate()