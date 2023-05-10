import opensimula as oms

proyecto1_json = {
    "name": "Proyecto 1",
    "components": [
        {"type": "File_met", "name": "zonaB4", "file_name": "meteo/zonaB4.met"}
    ],
}

proyecto_json = {
    "name": "Proyecto",
    "time_step": 900,
    "n_time_steps": 8760 * 4,
    "initial_time": "01/01/2001 00:00:00",
    "components": [
        {
            "type": "Outdoor",
            "name": "Outdoor zone",
            "meteo_file": "Proyecto 1->zonaB4",
        },
    ],
}


sim = oms.Simulation()
proyecto1 = oms.Project(sim)
proyecto1.load_from_json(proyecto1_json)
proyecto1.check()
proyecto = oms.Project(sim)
proyecto.load_from_json(proyecto_json)
proyecto.check()
proyecto.simulate()

proyecto.info()
