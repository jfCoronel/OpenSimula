import OpenSimula as oms

project_dic = {
    "name": "Project_test_met",
    "time_step": 3600,
    "n_time_steps": 8760,
    "initial_time": "01/01/2001 00:00:00",
    "components": [
        {"type": "File_met", "name": "sevilla", "file_name": "examples/met_files/sevilla.met"},
        
    ]
}


sim = oms.Simulation()
proyecto = oms.Project("proyecto",sim)
proyecto.read_dict(project_dic)
proyecto.simulate()