import opensimula as osm

bdd_json = {
    "name": "Base de Datos",
    "type": "Project",
    "components": [
        {
            "type": "File_met",
            "name": "zonaB4",
            "file_name": "test/meteo/zonaB4.met",
        },
        {
            "type": "Material",
            "name": "Mortero cemento",
            "conductivity": 1.4,
            "density": 2000,
            "specific_heat": 1050,
            "thickness": 0.02,
        },
        {
            "type": "Material",
            "name": "Ladrillo hueco",
            "conductivity": 0.49,
            "density": 1200,
            "specific_heat": 920,
            "thickness": 0.11,
        },
        {
            "type": "Construction",
            "name": "Muro Exterior",
            "solar_absortivity": [0.8, 0.8],
            "materials": ["Mortero cemento", "Ladrillo hueco"],
        },
    ],
}

proyecto_json = {
    "type": "Project",
    "name": "Proyecto",
    "time_step": 900,
    "n_time_steps": 8760 * 4,
    "initial_time": "01/01/2001 00:00:00",
    "components": [
        {
            "type": "Outdoor",
            "name": "Outdoor zone",
            "meteo_file": "Base de Datos->zonaB4",
        },
        {
            "type": "Wall",
            "name": "wall_S",
            "construction": "Base de Datos->Muro Exterior",
        },
        {
            "type": "Wall",
            "name": "wall_E",
            "construction": "Base de Datos->Muro Exterior",
        },
        {
            "type": "Wall",
            "name": "wall_W",
            "construction": "Base de Datos->Muro Exterior",
        },
        {
            "type": "Wall",
            "name": "wall_N",
            "construction": "Base de Datos->Muro Exterior",
        },
        {
            "type": "Wall",
            "name": "ceiling",
            "construction": "Base de Datos->Muro Exterior",
        },
        {
            "type": "Space",
            "name": "Room",
            "walls": ["wall_S", "wall_E", "wall_W", "wall_N", "ceiling"],
        },
    ],
}


sim = osm.Simulation()
bdd = osm.Project(sim)
# bdd.read_json("test/examples/bdd_project.json")
bdd.read_dict(bdd_json)

proyecto = osm.Project(sim)
# proyecto.read_json("test/examples/example_project.json")
proyecto.read_dict(proyecto_json)
proyecto.simulate()