import OpenSimula as osm

case_he100_dict = {
    "name": "Case HE100",
    "time_step": 3600,
    "n_time_steps": 8760,
    "initial_time": "01/01/2001 00:00:00",
    "components": [
        {
            "type": "File_met",
            "name": "HEATING_WEATHER",
            "file_type": "WYEC2",
            "file_name": "mets/HE100W.WY2"
        },    
        {
            "type": "Material",
            "name": "Insulation",
            "conductivity": 0.01,
            "density": 1,
            "specific_heat": 1
        },
        {
            "type": "Material",
            "name": "Roof_Material",
            "conductivity": 0.0714,
            "density": 1,
            "specific_heat": 1
        },
        {
            "type": "Construction",
            "name": "Adiabatic_Wall",
            "solar_alpha": [0,0],
            "lw_epsilon": [0,0],
            "materials": [
                "Insulation"
            ],
            "thicknesses": [
                1.0
            ]
        },
        {
            "type": "Construction",
            "name": "Roof_Wall",
            "solar_alpha": [0,0],
            "lw_epsilon": [0,0],
            "materials": [
                "Roof_Material"
            ],
            "thicknesses": [
                0.01
            ]
        },
        {
            "type": "Space_type",
            "name": "constant_gain_space",
            "people_density": "0",
            "light_density": "0",
            "other_gains_density": "112.5",
            "other_gains_radiant_fraction": 0,
            "infiltration": "0"
        },
        {
            "type": "Building",
            "name": "Building",
            "file_met": "HEATING_WEATHER",
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
                0,
                0
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
                0,
                0
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
                0,
                0
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
                0,
                0
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "roof_wall",
            "construction": "Roof_Wall",
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
                20,
                20
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
                0,
                0
            ]
        },
        {
            "type": "HVAC_DX_equipment",
            "name": "HVAC_equipment",
            "nominal_air_flow": 0.833333,
            "nominal_heating_capacity": 10000,
            "nominal_heating_power": 10000,
            "indoor_fan_power": 0,
            "indoor_fan_operation": "CONTINUOUS",
            "COP_expression": "F_load/(0.0080472574+0.87564457*F_load+0.29249943*F_load**2-0.17624156*F_load**3)",
        },
        {
            "type": "HVAC_DX_system",
            "name": "system",
            "space": "space_1",
            "file_met": "HEATING_WEATHER",
            "equipment": "HVAC_equipment",
            "supply_air_flow": 0.833333,
            "outdoor_air_flow": 0,
            "heating_setpoint": "20",
            "cooling_setpoint": "30",
            "system_on_off": "1",
            "control_type": "PERFECT"
        }
    ]
}


sim = osm.Simulation()
pro = sim.new_project("pro")
pro.read_dict(case_he100_dict)
pro.component("HEATING_WEATHER").set_location(39.833,-104.65,1650,-7*15)
pro.simulate(5)