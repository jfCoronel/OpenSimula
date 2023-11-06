import OpenSimula as oms

project_dic = {
    "name": "Test project",
    "time_step": 3600,
    "n_time_steps": 8760,
    "components": [
        {
            "type": "File_data",
            "name": "datas",
            "file_type": "CSV",
            "file_name": "examples/input_files/data_example.csv",
            "file_step": "OWN",
            "initial_time": "01/01/2001 00:00:00",
            "time_step":3600
        }
    ],
}

sim = oms.Simulation()
proyecto = oms.Project("proyecto",sim)
proyecto.read_dict(project_dic)
proyecto.simulate()