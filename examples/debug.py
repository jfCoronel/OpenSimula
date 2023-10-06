import OpenSimula as oms

muro_real = {
    "name": "Muro real",
    "time_step": 3600,
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

forjado = {
    "name": "Forjado",
    "time_step": 3600,
    "components": [
        {
            "type": "Material",
            "name": "acabado suelo",
            "conductivity": 1.16,
            "density": 2000,
            "specific_heat": 1050,
        },
        {
            "type": "Material",
            "name": "hormigon",
            "conductivity": 1.4,
            "density": 2000,
            "specific_heat": 1050,
        },
        {
            "type": "Material",
            "name": "forjado",
            "conductivity": 0.7,
            "density": 1500,
            "specific_heat": 1000,
        },
        {
            "type": "Material",
            "name": "yeso",
            "conductivity": 0.3,
            "density": 800,
            "specific_heat": 920,
        },
        {
            "type": "Construction",
            "name": "cubierta",
            "solar_absortivity": [0.8, 0.8],
            "materials": ["acabado suelo", "hormigon", "forjado", "yeso"],
            "thicknesses": [0.03, 0.04, 0.21, 0.015],
        },
    ],
}

muro_1C_esto2 = {
    "name": "Muro 1C esto2",
    "time_step": 3600,
    "components": [
        {
            "type": "Material",
            "name": "Heavy material",
            "conductivity": 2.1,
            "density": 1800,
            "specific_heat": 920,
        },
        {
            "type": "Construction",
            "name": "Muro pesado",
            "solar_absortivity": [0.8, 0.8],
            "materials": ["Heavy material"],
            "thicknesses": [1],
        },
    ],
}

muro_1C_pesado = {
    "name": "Muro 1C pesado",
    "time_step": 60,
    "components": [
        {
            "type": "Material",
            "name": "Heavy material",
            "conductivity": 1.95,
            "density": 2240,
            "specific_heat": 900,
        },
        {
            "type": "Construction",
            "name": "Muro pesado",
            "solar_absortivity": [0.8, 0.8],
            "materials": ["Heavy material"],
            "thicknesses": [0.203],
        },
    ],
}

muro_1C_ligero = {
    "name": "Muro 1C ligero",
    "time_step": 60,
    "components": [
        {
            "type": "Material",
            "name": "Light material",
            "conductivity": 0.03,
            "density": 43,
            "specific_heat": 1210,
        },
        {
            "type": "Construction",
            "name": "Muro ligero",
            "solar_absortivity": [0.8, 0.8],
            "materials": ["Light material"],
            "thicknesses": [0.076],
        },
    ],
}


import OpenSimula as osm

sim = osm.Simulation()
pro = osm.Project(sim)
pro.read_dict(muro_1C_ligero)
pro.simulate()
