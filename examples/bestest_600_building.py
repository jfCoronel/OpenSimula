import OpenSimula as osm

alfa = 0.6

bestest_building_600 = {
    "name": "Bestest Building",
    "time_step": 3600,
    "n_time_steps": 8760,
    "initial_time": "01/01/2001 00:00:00",
    "components": [
        # MET_FILE
        {
            "type": "File_met",
            "name": "drycold",
            "file_name": "examples/met_files/DRYCOLD.met"
        },
        # CONSTRUCTION
        {
            "type": "Material",
            "name": "Enlucido",
            "conductivity": 0.16,
            "density": 950,
            "specific_heat": 840
        },
        {
            "type": "Material",
            "name": "Aislamiento",
            "conductivity": 0.04,
            "density": 12,
            "specific_heat": 840
        },
        {
            "type": "Material",
            "name": "Madera pared",
            "conductivity": 0.14,
            "density": 530,
            "specific_heat": 900
        },
        {
            "type": "Material",
            "name": "Aislamiento suelo",
            "conductivity": 0.04,
            "density": .1,
            "specific_heat": .1,
        },
        {
            "type": "Material",
            "name": "Madera suelo",
            "conductivity": 0.14,
            "density": 650,
            "specific_heat": 1200,
        },
        {
            "type": "Material",
            "name": "Lecho_rocas",
            "conductivity": 0.14,
            "density": 650,
            "specific_heat": 1200,
        },
        {
            "type": "Construction",
            "name": "Pared 600",
            "solar_absortivity": [alfa, alfa],
            "materials": ["Enlucido", "Aislamiento", "Madera pared"],
            "thicknesses": [0.12, 0.066, 0.009],
        },
        {
            "type": "Construction",
            "name": "Suelo 600",
            "solar_absortivity": [alfa, alfa],
            "materials": ["Aislamiento suelo", "Madera suelo"],
            "thicknesses": [1.003, 0.025],
        },
        {
            "type": "Construction",
            "name": "Techo 600",
            "solar_absortivity": [alfa, alfa],
            "materials": ["Enlucido", "Aislamiento", "Madera pared"],
            "thicknesses": [0.010, 0.01118, 0.019],
        },
        {
            "type": "Window",
            "name": "Vidrio doble",
            "solar_absortivity": [0.13, 0.13],
            "solar_transmisivity": [0.66, 0.66],
            "R_glazing": 0.921,
            "R_frame": 0.921,
            "frame_fraction": 0
        },
        # BUILDING
        {
            "type": "Building",
            "name": "Bestest 600",
            "file_met": "drycold"
        },
        {
            "type": "Space_type",
            "name": "bestest space",
            "aux_variables": [],
            "people_density": "0",
            "light_density": "0",
            "other_gains_density": "4.1667",
            "other_gains_radiant_fraction": 0.6,
            "infiltration": "0.5"
        },
        {
            "type": "Space",
            "name": "space_1",
            "building": "Bestest 600",
            "space_type": "bestest space",
            "floor_area": 48,
            "volume": 48*2.7,
        },
        # Surfaces
        {
            "type": "Surface",
            "name": "north_wall",
            "location": "EXTERIOR",
            "virtual": False,
            "construction": "Pared 600",
            "space": "space_1",
            "area": 8*2.7,
            "azimuth": 0,
            "altitude": 0
        },
        {
            "type": "Surface",
            "name": "east_wall",
            "location": "EXTERIOR",
            "construction": "Pared 600",
            "space": "space_1",
            "area": 6*2.7,
            "azimuth": 90,
            "altitude": 0
        },
        {
            "type": "Surface",
            "name": "south_wall",
            "location": "EXTERIOR",
            "construction": "Pared 600",
            "space": "space_1",
            "area": 8*2.7,
            "azimuth": 180,
            "altitude": 0
        },
        {
            "type": "Opening",
            "name": "south_window_1",
            "surface": "south_wall",
            "window": "Vidrio doble",
            "width": 3,
            "height": 2,
        },
        {
            "type": "Opening",
            "name": "south_window_2",
            "surface": "south_wall",
            "window": "Vidrio doble",
            "width": 3,
            "height": 2,
        },
        {
            "type": "Surface",
            "name": "west_wall",
            "location": "EXTERIOR",
            "construction": "Pared 600",
            "space": "space_1",
            "area": 6*2.7,
            "azimuth": -90,
            "altitude": 0
        },
        {
            "type": "Surface",
            "name": "roof",
            "location": "EXTERIOR",
            "construction": "Techo 600",
            "space": "space_1",
            "area": 8*6,
            "azimuth": 0,
            "altitude": 90
        },
        {
            "type": "Surface",
            "name": "floor",
            "location": "UNDERGROUND",
            "construction": "Suelo 600",
            "space": "space_1",
            "area": 8*6,
            "azimuth": 0,
            "altitude": -90
        },
    ],
}

sim = osm.Simulation()
pro = osm.Project("pro", sim)
pro.read_dict(bestest_building_600)
pro.simulate()
print(pro.component("Bestest 600")._SWDIR_matrix)