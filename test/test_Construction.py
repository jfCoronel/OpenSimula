import OpenSimula as osm

light_wall = {
    "name": "Light wall project",
    "time_step": 3600,
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
            "name": "Light wall",
            "solar_absortivity": [0.8, 0.8],
            "materials": ["Light material"],
            "thicknesses": [0.076],
        },
    ],
}

heavy_wall = {
    "name": "Heavy wall project",
    "time_step": 3600,
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
            "name": "Heavy wall",
            "solar_absortivity": [0.8, 0.8],
            "materials": ["Heavy material"],
            "thicknesses": [0.203],
        },
    ],
}

multilayer_wall = {
    "name": "Multilayer wall project",
    "time_step": 3600,
    "components": [
        {
            "type": "Material",
            "name": "Gypsum board",
            "conductivity": 0.16,
            "density": 800,
            "specific_heat": 1090,
        },
        {
            "type": "Material",
            "name": "EPS board",
            "conductivity": 0.03,
            "density": 43,
            "specific_heat": 1210,
        },
        {
            "type": "Material",
            "name": "Heavyweight concrete",
            "conductivity": 1.95,
            "density": 2240,
            "specific_heat": 900,
        },
        {
            "type": "Material",
            "name": "Stucco",
            "conductivity": 0.72,
            "density": 1856,
            "specific_heat": 840,
        },
        {
            "type": "Construction",
            "name": "Multilayer wall",
            "solar_absortivity": [0.8, 0.8],
            "materials": [
                "Gypsum board",
                "EPS board",
                "Heavyweight concrete",
                "EPS board",
                "Stucco",
            ],
            "thicknesses": [0.016, 0.076, 0.203, 0.076, 0.025],
        },
    ],
}


def test_light_wall():
    sim = osm.Simulation()
    pro = osm.Project(sim)
    pro.read_dict(light_wall)
    pro.simulate()
