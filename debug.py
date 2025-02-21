import OpenSimula.Simulation as Simulation
import OpenSimula as osm

case_dict = {
    "name": "met test",
    "time_step": 3600,
    "n_time_steps": 8760,
    "initial_time": "01/01/2001 00:00:00",
    "components": [
        {
            "type": "File_met",
            "name": "sevilla_met",
            "file_type": "MET",
            "file_name": "mets/sevilla.met"
        },
        {
            "type": "File_data",
            "name": "sevilla_dat",
            "file_type": "CSV",
            "file_name": "mets/sevilla.csv",
            "file_step": "SIMULATION"
        }
    ]
}


sim = osm.Simulation()
pro = sim.new_project("pro")
pro.read_dict(case_dict)
pro.simulate()