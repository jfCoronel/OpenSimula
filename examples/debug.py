import OpenSimula as oms

project_dic = {
    "name": "Base de Datos",
    "components": [
        {
            "type": "Material",
            "name": "Mortero cemento",
            "conductivity": 0.8,
            "density": 1500,
            "specific_heat": 1000,
        },
        {
            "type": "Material",
            "name": "Ladrillo hueco",
            "conductivity": 0.49,
            "density": 1200,
            "specific_heat": 920,
        },
        {
            "type": "Material",
            "name": "Poliestireno expandido",
            "conductivity": 0.03,
            "density": 10,
            "specific_heat": 1000,
        },
        {
            "type": "Construction",
            "name": "Muro Exterior",
            "solar_absortivity": [0.8, 0.8],
            "materials": [
                "Mortero cemento",
                "Poliestireno expandido",
                "Ladrillo hueco",
            ],
            "thicknesses": [0.04, 0.05, 0.24],
        },
    ],
}


import OpenSimula as osm

sim = osm.Simulation()
pro = osm.Project(sim)
pro.read_dict(project_dic)
pro.simulate()
