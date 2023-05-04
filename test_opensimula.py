
import opensimula as oms

proyecto_json = {
    "name": "Proyecto 1",
    "components": [
        {
            "type": "File_met",
            "name": "zonaB4",
            "file_name": "meteo/zonaB4.met"
        },
        {
            "type": "Outdoor",
            "name": "Outdoor zone",
            "meteo_file": "zonaB4"
        }
    ]
}

sim = oms.Simulation()
proyecto = oms.Project(sim)
proyecto.load_from_json(proyecto_json)
proyecto.check()

sim.info()
proyecto.info()
