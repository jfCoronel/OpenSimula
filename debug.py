import OpenSimula.Simulation as Simulation
calculator_dict = {
    "name": "Calculator Test",
    "time_step": 3600,
    "n_time_steps": 8760,
    "initial_time": "01/01/2001 00:00:00",
    "components": [
        {
            "type": "File_met",
            "name": "Denver",
            "file_type": "TMY3",
            "file_name": "mets/WD100.tmy3"
        },{
            "type": "Calculator",
            "name": "Cambiar unidad",
           "input_variables": ["T = Denver.temperature", "w = Denver.abs_humidity"],
            "output_variables": ["T_F","W_kg", "degree_hour_20"],
            "output_units": ["ºF","kg/kg a.s.","ºC"],
            "output_expressions": ["T * 9/5 + 32", "w * math.pi", "0.0 if T > 20 else (20 - T)"],
        }
    ]
}

sim = Simulation()
p1 = sim.new_project("p1")
p1.read_dict(calculator_dict)
p1.simulate()