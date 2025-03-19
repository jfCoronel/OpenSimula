import OpenSimula as osm

case_FC_test = {
    "name": "case_FC_test",
    "time_step": 3600,
    "n_time_steps": 8760,
    "initial_time": "01/01/2001 00:00:00",
    "simulation_file_met": "sevilla",
    "components": [
        {
            "type": "File_met",
            "name": "sevilla",
            "file_name": "mets/sevilla.met"
        },
        {
            "type": "HVAC_FC_equipment",
            "name": "FC",
            "nominal_air_flow": 0.5622,
            "fan_power": 0,
            "fan_operation": "CONTINUOUS",
            "nominal_heating_capacity": 14800,
            "nominal_heating_water_flow": 0.5069e-3,
            "nominal_total_cooling_capacity": 15250,
            "nominal_sensible_cooling_capacity": 10640,

        }
    ]
}


sim = osm.Simulation()
pro = sim.new_project("pro")
pro.read_dict(case_FC_test)
pro.simulate()

print(pro.component("FC").get_heating_state(20,15,50,1,1,1))
print(pro.component("FC").get_heating_state(20,15,30,1,1,1))