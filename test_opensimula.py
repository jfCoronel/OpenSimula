# %%
import opensimula as oms

proyecto_json = {
    "name": "Proyecto 1",
    "time_step": 900,
    "n_time_steps": 8760 * 4,
    "initial_time": "01/01/2001 00:00:00",
    "components": [
        {"type": "File_met", "name": "zonaB4", "file_name": "meteo/zonaB4.met"},
        {"type": "Outdoor", "name": "Outdoor zone", "meteo_file": "zonaB4"},
    ],
}

sim = oms.Simulation()
proyecto = oms.Project(sim)
proyecto.load_from_json(proyecto_json)
proyecto.check()
proyecto.simulate()

proyecto.info()
t = proyecto.component[1].variable["temperature"].array
# %%
