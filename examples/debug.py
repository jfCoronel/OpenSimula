import OpenSimula as osm

bestest_building_960 = {
    "name": "Bestest Building 960",
    "time_step": 3600,
    "n_time_steps": 8760,
    "initial_time": "01/01/2001 00:00:00",
    "components": [
        # MET_FILE
        {
            "type": "File_met",
            "name": "sevilla",
            "file_name": "met_files/sevilla.met"
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
            "solar_alpha": [0.6, 0.6],
            "materials": ["Enlucido", "Aislamiento", "Madera pared"],
            "thicknesses": [0.12, 0.066, 0.009],
        },
        {
            "type": "Construction",
            "name": "Suelo 600",
            "solar_alpha": [0.6, 0.6],
            "materials": ["Aislamiento suelo", "Madera suelo"],
            "thicknesses": [1.003, 0.025],
        },
        {
            "type": "Construction",
            "name": "Techo 600",
            "solar_alpha": [0.6, 0.6],
            "materials": ["Enlucido", "Aislamiento", "Madera pared"],
            "thicknesses": [0.010, 0.01118, 0.019],
        },
        {
            "type": "Glazing",
            "name": "Vidrio simple",
        },
        {
            "type": "Frame",
            "name": "Marco",
            "thermal_resistance": 0.2
        },
        {
            "type": "Opening_type",
            "name": "Ventana",
            "glazing": "Vidrio simple",
            "frame": "Marco",
            "frame_fraction": 0.1,
            "glazing_fraction": 0.9
        },
        # BUILDING
        {
            "type": "Building",
            "name": "Building",
            "file_met": "sevilla",
            "azimuth": 45
        },
        {
            "type": "Space_type",
            "name": "bestest space",
            "people_density": "0",
            "light_density": "0",
            "other_gains_density": "4.1667",
            "other_gains_radiant_fraction": 0.6,
            "infiltration": "0.5"
        },
        {
            "type": "Space",
            "name": "space_1",
            "building": "Building",
            "space_type": "bestest space",
            "floor_area": 48,
            "volume": 48*2.7,
        },
        {
            "type": "Space",
            "name": "space_2",
            "building": "Building",
            "space_type": "bestest space",
            "floor_area": 16,
            "volume": 16*2.7,
        },
        # Surfaces
        {
            "type": "Exterior_surface",
            "name": "north_wall",
            "construction": "Pared 600",
            "space": "space_1",
            "ref_point": [8, 8, 0],
            "width": 8,
            "height": 2.7,
            "azimuth": 180,
            "altitude": 0
        },
        {
            "type": "Exterior_surface",
            "name": "east_wall_1",
            "construction": "Pared 600",
            "space": "space_1",
            "ref_point": [8, 2, 0],
            "width": 6,
            "height": 2.7,
            "azimuth": 90,
            "altitude": 0
        },
        {
            "type": "Exterior_surface",
            "name": "west_wall_1",
            "construction": "Pared 600",
            "space": "space_1",
            "ref_point": [0, 8, 0],
            "width": 6,
            "height": 2.7,
            "azimuth": -90,
            "altitude": 0
        },
        {
            "type": "Exterior_surface",
            "name": "roof_1",
            "construction": "Techo 600",
            "space": "space_1",
            "ref_point": [0, 2, 2.7],
            "width": 8,
            "height": 6,
            "azimuth": 0,
            "altitude": 90
        },
        {
            "type": "Underground_surface",
            "name": "floor_1",
            "construction": "Suelo 600",
            "space": "space_1",
            "ref_point": [0, 8, 0],
            "width": 8,
            "height": 6,
            "azimuth": 0,
            "altitude": -90
        },
        {
            "type": "Exterior_surface",
            "name": "south_wall",
            "construction": "Pared 600",
            "space": "space_2",
            "ref_point": [0, 0, 0],
            "width": 8,
            "height": 2.7,
            "azimuth": 0,
            "altitude": 0
        },
        {
            "type": "Opening",
            "name": "south_window_1",
            "surface": "south_wall",
            "opening_type": "Ventana",
            "ref_point": [0.5, 0.5],
            "width": 3,
            "height": 2
        },
        {
            "type": "Opening",
            "name": "south_window_2",
            "surface": "south_wall",
            "opening_type": "Ventana",
            "ref_point": [4.5, 0.5],
            "width": 3,
            "height": 2
        },
        {
            "type": "Exterior_surface",
            "name": "east_wall_2",
            "construction": "Pared 600",
            "space": "space_2",
            "ref_point": [8, 0, 0],
            "width": 2,
            "height": 2.7,
            "azimuth": 90,
            "altitude": 0
        },
        {
            "type": "Exterior_surface",
            "name": "west_wall_2",
            "construction": "Pared 600",
            "space": "space_2",
            "ref_point": [0, 2, 0],
            "width": 2,
            "height": 2.7,
            "azimuth": -90,
            "altitude": 0
        },
        {
            "type": "Exterior_surface",
            "name": "roof_2",
            "construction": "Techo 600",
            "space": "space_2",
            "ref_point": [0, 0, 2.7],
            "width": 8,
            "height": 2,
            "azimuth": 0,
            "altitude": 90
        },
        {
            "type": "Underground_surface",
            "name": "floor_2",
            "construction": "Suelo 600",
            "space": "space_2",
            "ref_point": [0, 2, 0],
            "width": 8,
            "height": 2,
            "azimuth": 0,
            "altitude": -90
        },
        {
            "type": "Interior_surface",
            "name": "interior_wall",
            "construction": "Pared 600",
            "spaces": ["space_2", "space_1"],
            "ref_point": [0, 2, 0],
            "width": 8,
            "height": 2.7,
            "azimuth": 0,
            "altitude": 0
        },

    ],
}

sim = osm.Simulation()
pro = sim.add_project("pro")
pro.read_dict(bestest_building_960)
