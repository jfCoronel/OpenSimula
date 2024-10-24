import OpenSimula as osm

weather_test = {
    "name": "case_Weather_Test",
    "time_step": 600,
    "n_time_steps": 8760*6,
    "initial_time": "01/01/2001 00:00:00",
    "components": [
        {
            "type": "File_met",
            "name": "TMY3",
            "file_type": "TMY3",
            "file_name": "test/WD100.tmy3",
            "tilted_diffuse_model": "PEREZ"
        },
        {
            "type": "Material",
            "name": "Madera",
            "conductivity": 0.14,
            "density": 530,
            "specific_heat": 900
        },
        {
            "type": "Construction",
            "name": "Pared",
            "solar_alpha": [
                1,
                1
            ],
            "materials": [
                "Madera"
            ],
            "thicknesses": [
                0.10
            ]
        },
        {
            "type": "Building",
            "name": "WT_Building",
            "file_met": "TMY3",
            "albedo": 0.2
        },
        {
            "type": "Space_type",
            "name": "ashrae_space",
            "people_density": "0",
            "light_density": "0",
            "other_gains_density": "4.1667",
            "other_gains_radiant_fraction": 0.6,
            "infiltration": "1"
        },
        {
            "type": "Space",
            "name": "space",
            "building": "WT_Building",
            "space_type": "ashrae_space",
            "floor_area": 48,
            "volume": 129.6
        },
        {
            "type": "Exterior_surface",
            "name": "north_wall",
            "construction": "Pared",
            "space": "space",
            "ref_point": [
                8,
                6,
                0
            ],
            "width": 8,
            "height": 2.7,
            "azimuth": 180,
            "altitude": 0
        },
        {
            "type": "Exterior_surface",
            "name": "west_wall",
            "construction": "Pared",
            "space": "space",
            "ref_point": [
                0,
                6,
                0
            ],
            "width": 4,
            "height": 2.7,
            "azimuth": -90,
            "altitude": 0
        },
        {
            "type": "Exterior_surface",
            "name": "south_west_wall",
            "construction": "Pared",
            "space": "space",
            "ref_point": [
                0,
                2,
                0
            ],
            "width": 2.828,
            "height": 2.7,
            "azimuth": -45,
            "altitude": 0
        },
        {
            "type": "Exterior_surface",
            "name": "south_wall",
            "construction": "Pared",
            "space": "space",
            "ref_point": [
                2,
                0,
                0
            ],
            "width": 4,
            "height": 2.7,
            "azimuth": 0,
            "altitude": 0
        },
        {
            "type": "Exterior_surface",
            "name": "south_east_wall",
            "construction": "Pared",
            "space": "space",
            "ref_point": [
                6,
                0,
                0
            ],
            "width": 2.828,
            "height": 2.7,
            "azimuth": 45,
            "altitude": 0
        },
        {
            "type": "Exterior_surface",
            "name": "east_wall",
            "construction": "Pared",
            "space": "space",
            "ref_point": [
                8,
                2,
                0
            ],
            "width": 4,
            "height": 2.7,
            "azimuth": 90,
            "altitude": 0
        },
        {
            "type": "Exterior_surface",
            "name": "roof",
            "construction": "Pared",
            "space": "space",
            "ref_point": [
                2,
                2,
                3.85
            ],
            "width": 4,
            "height": 4,
            "azimuth": 0,
            "altitude": 90
        },
        {
            "type": "Exterior_surface",
            "name": "west_roof",
            "construction": "Pared",
            "space": "space",
            "ref_point": [
                0,
                6,
                2.7
            ],
            "width": 4,
            "height": 2.307,
            "azimuth": -90,
            "altitude": 60
        },
        {
            "type": "Exterior_surface",
            "name": "east_roof",
            "construction": "Pared",
            "space": "space",
            "ref_point": [
                8,
                2,
                2.7
            ],
            "width": 4,
            "height": 2.307,
            "azimuth": 90,
            "altitude": 60
        },
        {
            "type": "Exterior_surface",
            "name": "south_roof",
            "construction": "Pared",
            "space": "space",
            "ref_point": [
                2,
                0,
                2.7
            ],
            "width": 4,
            "height": 2.307,
            "azimuth": 0,
            "altitude": 60
        }
    ]
}

sim = osm.Simulation()
pro = sim.new_project("pro")
pro.read_dict(weather_test)
pro.simulate()
