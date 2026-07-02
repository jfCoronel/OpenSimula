import opensimula as osm

dict = {
    "name": "Process water system",
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
            "type": "File_data",
            "name": "data_file",
            "file_type": "CSV",
            "file_name": "jupyter/debug/ASHRAE_140_CASE_610.csv",
            "file_step": "SIMULATION"
        },
        {
            "type": "Day_schedule",
            "name": "working_day",
            "time_steps": [28800, 43200],
            "values": [0, 1, 0],
            "interpolation": "STEP",
        },
        {
            "type": "Day_schedule",
            "name": "off_day",
            "time_steps": [],
            "values": [0],
            "interpolation": "STEP",
        },
        {
            "type": "Day_schedule",
            "name": "heating_day",
            "time_steps": [],
            "values": [1],
            "interpolation": "STEP",
        },
        {
            "type": "Day_schedule",
            "name": "cooling_day",
            "time_steps": [],
            "values": [-1],
            "interpolation": "STEP",
        },
        {
            "type": "Week_schedule",
            "name": "working_week",
            "days_schedules": [
                "working_day"
            ],
        },
        {
            "type": "Week_schedule",
            "name": "off_week",
            "days_schedules": [
                "off_day"
            ],
        },
        {
            "type": "Week_schedule",
            "name": "heating_week",
            "days_schedules": [
                "heating_day"
            ],
        },
        {
            "type": "Week_schedule",
            "name": "cooling_week",
            "days_schedules": [
                "heating_day"
            ],
        },
        {
            "type": "Year_schedule",
            "name": "on_schedule",
            "periods": [],
            "weeks_schedules": ["working_week"],
        },
        {
            "type": "Year_schedule",
            "name": "mode_schedule",
            "periods": ["31/3","30/9"],
            "weeks_schedules": ["heating_week", "cooling_week", "heating_week"],
        },
        {
            "type":"Pump",
            "name":"pump",
            "nominal_water_flow": 0.4137,
            "nominal_pressure": 100000,
            "nominal_power": 70,
        },
        {
            "type":"Chiller_heat_pump",
            "name":"heat_pump",
            "chiller_type":"CHILLER_HEAT_PUMP",
            "nominal_cooling_capacity": 8000,
            "nominal_cooling_power": 2000,
            "nominal_heating_capacity": 9000,
            "nominal_heating_power": 3600,
            "nominal_water_flow": 0.4137
        },
        {
            "type":"HVAC_water_system",
            "name":"water_system",
            "water_thermal_generator": "heat_pump",
            "pump": "pump",
            "design_water_flow": 0.4137,
            "heating_water_setpoint": "50",
            "cooling_water_setpoint": "7",
            "total_water_volume": 0.1,
            "system_on_off":"g",
            "pump_operation": "ON_LOAD",
            "system_control": "SCHEDULE_CONTROL",
            "system_mode":"f",
            "input_variables":["Q = data_file.Q_total","f = mode_schedule.values","g= on_schedule.values"],
            "Q_process":"Q",
        }
    ]
}

sim = osm.Simulation()

pro = sim.new_project("pro")
pro.read_dict(dict)
pro.simulate()