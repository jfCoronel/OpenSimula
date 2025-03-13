import OpenSimula as osm

case_ce500_dict = {
    "name": "Case CE500",
    "time_step": 3600,
    "n_time_steps": 8760,
    "initial_time": "01/01/2001 00:00:00",
    "components": [ 
        {
            "type": "File_met",
            "name": "meteo",
            "file_type": "TMY2",
            "file_name": "mets/CE300.TM2"
        },    
        {
            "type": "Material",
            "name": "Insulation",
            "conductivity": 0.00308,
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
            "type": "Day_schedule",
            "name": "latent_day_1",
            "time_steps": [8*3600, 12*3600],
            "values": [0, 0, 0],
            "interpolation": "STEP",
        },
        {
            "type": "Day_schedule",
            "name": "latent_day_2",
            "time_steps": [9*3600, 9*3600],
            "values": [0, 0.375, 0],
            "interpolation": "STEP",
        },
        {
            "type": "Day_schedule",
            "name": "latent_day_3",
            "time_steps": [8*3600, 11*3600],
            "values": [0, 0.5, 0],
            "interpolation": "STEP",
        },
        {
            "type": "Day_schedule",
            "name": "latent_day_4",
            "time_steps": [8*3600, 4*3600, 2*3600, 2*3600, 4*3600],
            "values": [0.375, 0.5, 0.75, 1, 0.5, 0.375],
            "interpolation": "STEP",
        },
        {
            "type": "Day_schedule",
            "name": "latent_day_5",
            "time_steps": [8*3600, 8*3600],
            "values": [0, 0.5, 0],
            "interpolation": "STEP",
        },
        {
            "type": "Day_schedule",
            "name": "latent_day_6",
            "time_steps": [8*3600, 4*3600, 2*3600, 2*3600, 4*3600],
            "values": [0, 0.5, 0.75, 1, 0.5, 0.375],
            "interpolation": "STEP",
        },
        {
            "type": "Day_schedule",
            "name": "sensible_day_1",
            "time_steps": [],
            "values": [0],
            "interpolation": "STEP",
        },
        {
            "type": "Day_schedule",
            "name": "sensible_day_2",
            "time_steps": [9*3600, 9*3600],
            "values": [0, 0.375, 0],
            "interpolation": "STEP",
        },
        {
            "type": "Day_schedule",
            "name": "sensible_day_3",
            "time_steps": [8*3600, 11*3600],
            "values": [0, 0.5, 0],
            "interpolation": "STEP",
        },
        {
            "type": "Day_schedule",
            "name": "sensible_day_4",
            "time_steps": [8*3600, 4*3600, 2*3600, 2*3600, 4*3600],
            "values": [0.375, 0.5, 0.75, 1, 0.5, 0.375],
            "interpolation": "STEP",
        },
        {
            "type": "Day_schedule",
            "name": "sensible_day_5",
            "time_steps": [8*3600, 8*3600],
            "values": [0, 0.5, 0],
            "interpolation": "STEP",
        },
        {
            "type": "Day_schedule",
            "name": "sensible_day_6",
            "time_steps": [8*3600, 4*3600, 2*3600, 2*3600, 4*3600],
            "values": [0, 0.5, 0.75, 1, 0.5, 0.375],
            "interpolation": "STEP",
        },
        {
            "type": "Week_schedule",
            "name": "latent_week_1",
            "days_schedules": ["latent_day_1"],
        },
        {
            "type": "Week_schedule",
            "name": "latent_week_2",
            "days_schedules": ["latent_day_2"],
        },
        {
            "type": "Week_schedule",
            "name": "latent_week_3",
            "days_schedules": ["latent_day_3"],
        },
        {
            "type": "Week_schedule",
            "name": "latent_week_4",
            "days_schedules": ["latent_day_4"],
        },
        {
            "type": "Week_schedule",
            "name": "latent_week_5",
            "days_schedules": ["latent_day_5"],
        },
        {
            "type": "Week_schedule",
            "name": "latent_week_6",
            "days_schedules": ["latent_day_6"],
        },
        {
            "type": "Week_schedule",
            "name": "sensible_week_1",
            "days_schedules": ["sensible_day_1"],
        },
        {
            "type": "Week_schedule",
            "name": "sensible_week_2",
            "days_schedules": ["sensible_day_2"],
        },
        {
            "type": "Week_schedule",
            "name": "sensible_week_3",
            "days_schedules": ["sensible_day_3"],
        },
        {
            "type": "Week_schedule",
            "name": "sensible_week_4",
            "days_schedules": ["sensible_day_4"],
        },
        {
            "type": "Week_schedule",
            "name": "sensible_week_5",
            "days_schedules": ["sensible_day_5"],
        },
        {
            "type": "Week_schedule",
            "name": "sensible_week_6",
            "days_schedules": ["sensible_day_6"],
        },
        {
            "type": "Year_schedule",
            "name": "latent_schedule",
            "periods": ["10/03", "10/04","11/04","20/04","12/10","18/10","05/11"],
            "weeks_schedules": ["latent_week_1"
                                , "latent_week_2"
                                , "latent_week_1"
                                , "latent_week_3"
                                , "latent_week_4"
                                , "latent_week_5"
                                , "latent_week_6"
                                , "latent_week_1"],
        },
        {
            "type": "Year_schedule",
            "name": "sensible_schedule",
            "periods": ["10/03", "10/04","11/04","20/04","12/10","18/10","05/11"],
            "weeks_schedules": ["sensible_week_1"
                                , "sensible_week_2"
                                , "sensible_week_1"
                                , "sensible_week_3"
                                , "sensible_week_4"
                                , "sensible_week_5"
                                , "sensible_week_6"
                                , "sensible_week_1"],
        },
        {
            "type": "Space_type",
            "name": "space_gains",
            "input_variables": ["f_l = latent_schedule.values","f_s = sensible_schedule.values"],
            "people_density": "f_l",
            "people_sensible": 0,
            "people_latent": 38.883,            
            "light_density": "0",
            "other_gains_density": "95.704*f_s",
            "other_gains_radiant_fraction": 0,
            "infiltration": "0"
        },
        {
            "type": "Building",
            "name": "Building",
            "file_met": "meteo",
            "albedo": 0.2,
            "azimuth": 0,
            "shadow_calculation": "INSTANT"
        },
        {
            "type": "Space",
            "name": "space_1",
            "building": "Building",
            "space_type": "space_gains",
            "floor_area": 196,
            "volume": 588,
            "furniture_weight": 0
        },
        {
            "type": "Exterior_surface",
            "name": "north_wall",
            "construction": "Adiabatic_Wall",
            "space": "space_1",
            "ref_point": [
                14,
                14,
                0
            ],
            "width": 14,
            "height": 3,
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
                14,
                0,
                0
            ],
            "width": 14,
            "height": 3,
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
            "width": 14,
            "height": 3,
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
                14,
                0
            ],
            "width": 14,
            "height": 3,
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
                3
            ],
            "width": 14,
            "height": 14,
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
                14,
                0
            ],
            "width": 14,
            "height": 14,
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
            "nominal_air_flow": 1.888,
            "nominal_total_cooling_capacity": 33277,
            "nominal_sensible_cooling_capacity": 26043,
            "nominal_cooling_power": 10937,
            "indoor_fan_power": 1242,
            "indoor_fan_operation": "CICLING",      
            "nominal_cooling_conditions": [26.67,19.44,35],            
            "total_cooling_capacity_expression": "-3.762e-03 * T_odb + 1.941e-02 * T_iwb + 4.783e-03 * T_idb -2.535e-05 * T_odb**2 + 1.232e-03 * T_iwb**2 + 4.448e-04 * T_idb**2 -2.754e-04 * T_odb * T_iwb + 5.977e-05 * T_odb * T_idb -1.297e-03 * T_iwb * T_idb + 6.851e-01",
            "sensible_cooling_capacity_expression": "-4.491e-03*T_odb -3.135e-02*T_iwb -1.011e-01*T_idb -6.467e-05*T_odb**2 -4.991e-03*T_iwb**2 +6.132e-03*T_idb**2 +3.255e-04*T_odb*T_iwb -1.873e-04*T_odb*T_idb +4.163e-03*T_iwb*T_idb +4.984e-07*T_odb**3 +3.308e-05*T_iwb**3 -1.075e-04*T_idb**3 + 1.6552",            
            "cooling_power_expression": "7.990e-03 * T_odb +6.779e-05 * T_iwb + 5.339e-04 * T_idb -2.125e-05 * T_odb**2 +4.948e-04 * T_iwb**2 +1.983e-04 * T_idb**2 + 1.931e-04 * T_odb * T_iwb +7.733e-05 * T_odb * T_idb -5.698e-04 * T_iwb * T_idb + 4.978e-01",
            "EER_expression": "1 - 0.229*(1-F_load)",
            "expression_max_values": [40,35,50,30,1.5,1]
        },
        {
            "type": "HVAC_DX_system",
            "name": "system",
            "space": "space_1",
            "file_met": "meteo",
            "equipment": "HVAC_equipment",
            "supply_air_flow": 1.888,
            "outdoor_air_flow": 0,
            "heating_setpoint": "20",
            "cooling_setpoint": "25",
            "system_on_off": "1",
            "control_type": "TEMPERATURE"
        }
    ]
}


sim = osm.Simulation()
pro = sim.new_project("pro")
pro.read_dict(case_ce500_dict)
pro.simulate(5)
