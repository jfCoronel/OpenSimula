import OpenSimula as osm

case_AE104 = {
    "name": "case_AE104",
    "time_step": 3600,
    "n_time_steps": 8760,
    "initial_time": "01/01/2001 00:00:00",
    "simulation_file_met": "T_ext_cte",
    "components": [
        {
            "type": "File_met",
            "name": "T_ext_cte",
            "file_type": "TMY2",
            "file_name": "mets/AE104.TM2"
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
            "people_density": "1",
            "people_sensible": 0,
            "people_latent": 12.21,
            "light_density": "0",
            "other_gains_density": "61.0625",
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
            "type": "HVAC_FC_equipment",
            "name": "FC",
            "nominal_air_flow": 0.28317,
            "fan_power": 201.46,
            "fan_operation": "CONTINUOUS",
            "nominal_heating_capacity": 0,
            "nominal_total_cooling_capacity": 7164,
            "nominal_sensible_cooling_capacity": 5230,
            "nominal_cooling_water_flow": 3.415e-4,
            "wet_coil_model": "CONSTANT_BF"
        },
        {
            "type": "HVAC_FC_system",
            "name": "system",
            "space": "space_1",
            "equipment": "FC",
            "supply_air_flow": 0.28317,
            "outdoor_air_flow": 0.09506,
            "cooling_water_flow": 3.415e-4,
            "cooling_setpoint": "23.889",
            "heating_setpoint": "0",
            "system_on_off": "1",
        }
    ]
}

sim = osm.Simulation()
pro = sim.new_project("pro")
pro.read_dict(case_AE104)
pro.simulate()