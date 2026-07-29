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
            "name": "process_load",
            "file_type": "CSV",
            "file_name": "jupyter_test/process_load.csv",
            "file_step": "SIMULATION"
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
            "nominal_cooling_power": 4000,
            "nominal_heating_capacity": 9000,
            "nominal_heating_power": 4500,
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
            "total_water_volume": 100,
            "system_on_off":"1",
            "pump_operation": "ON_LOAD",
            "system_control": "LOAD_CONTROL",
            "system_mode":"0",
            "input_variables":["Q = process_load.Q",],
            "Q_process":"Q",
        }
    ]
}

sim = osm.Simulation()

pro = sim.new_project("pro")
pro.read_dict(dict)
pro.simulate()