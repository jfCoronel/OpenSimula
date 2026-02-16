import opensimula as osm

caseGC50b_dict = {
    "name": "Case GC50b",
    "time_step": 3600,
    "n_time_steps": 8760,
    "initial_time": "01/01/2001 00:00:00",
    "simulation_file_met": "GC30b_met",
    "shadow_calculation": "NO",
    "components": [
        {
            "type": "File_met",
            "name": "GC30b_met",
            "file_type": "TMY2",
            "file_name": "mets/GC30b.TM2"
        },
        {
            "type": "Material",
            "name": "Insulation",
            "conductivity": 0.0001,
            "density": 1,
            "specific_heat": 1
        },
        {
            "type": "Material",
            "name": "Ground",
            "conductivity": 1.9,
            "density": 1490,
            "specific_heat": 1800
        },
        {
            "type": "Construction",
            "name": "Adiabatic_Wall",
            "solar_alpha": [0,0],
            "lw_epsilon": [0,0],
            "materials": [
                "Insulation"
            ],
            "thicknesses": [
                1.0
            ]
        },
        {
            "type": "Construction",
            "name": "Floor_Slab",
            "solar_alpha": [0,0],
            "lw_epsilon": [0,0],
            "materials": [
                "Ground"
            ],
            "thicknesses": [
                0.01
            ]
        },
        {
            "type": "Space_type",
            "name": "no_gain_space",
            "people_density": "0",
            "light_density": "0",
            "other_gains_density": "0",
            "infiltration": "0"
        },
        {
            "type": "Building",
            "name": "Building",
            "azimuth": 0,
            "initial_temperature": 10
        },
        {
            "type": "Space",
            "name": "space_1",
            "building": "Building",
            "spaces_type": "no_gain_space",
            "floor_area": 144,
            "volume": 388.8,
            "furniture_weight": 0
        },
        {
            "type": "Building_surface",
            "name": "north_wall",
            "construction": "Adiabatic_Wall",
            "spaces": "space_1",
            "ref_point": [
                12,
                12,
                0
            ],
            "width": 12,
            "height": 2.7,
            "azimuth": 180,
            "altitude": 0,
            "h_cv": [
                100,
                7.95
            ]
        },
        {
            "type": "Building_surface",
            "name": "east_wall",
            "construction": "Adiabatic_Wall",
            "spaces": "space_1",
            "ref_point": [
                12,
                0,
                0
            ],
            "width": 12,
            "height": 2.7,
            "azimuth": 90,
            "altitude": 0,
            "h_cv": [
                100,
                7.95
            ]
        },
        {
            "type": "Building_surface",
            "name": "south_wall",
            "construction": "Adiabatic_Wall",
            "spaces": "space_1",
            "ref_point": [
                0,
                0,
                0
            ],
            "width": 12,
            "height": 2.7,
            "azimuth": 0,
            "altitude": 0,
            "h_cv": [
                100,
                7.95
            ]
        },
        {
            "type": "Building_surface",
            "name": "west_wall",
            "construction": "Adiabatic_Wall",
            "spaces": "space_1",
            "ref_point": [
                0,
                12,
                0
            ],
            "width": 12,
            "height": 2.7,
            "azimuth": -90,
            "altitude": 0,
            "h_cv": [
                100,
                7.95
            ]
        },
        {
            "type": "Building_surface",
            "name": "roof_wall",
            "construction": "Adiabatic_Wall",
            "spaces": "space_1",
            "ref_point": [
                0,
                0,
                2.7
            ],
            "width": 12,
            "height": 12,
            "azimuth": 0,
            "altitude": 90,
            "h_cv": [
                100,
                7.95
            ]
        },
        {
            "type": "Building_surface",
            "name": "floor_wall",
            "surface_type": "UNDERGROUND",
            "construction": "Floor_Slab",
            "ground_material": "Ground",
            "exterior_perimeter_wall_thickness": 0.24,
            "spaces": "space_1",
            "ref_point": [
                0,
                12,
                0
            ],
            "width": 12,
            "height": 12,
            "azimuth": 0,
            "altitude": -90,
            "h_cv": [
                100,
                7.95
            ]
        },
        {
            "type": "HVAC_perfect_system",
            "name": "system",
            "spaces": "space_1",
            "outdoor_air_flow": "0",
            "heating_setpoint": "30",
            "cooling_setpoint": "50",
            "system_on_off": "1"
        }
    ]
}

sim = osm.Simulation()
pro = sim.new_project("pro")
pro.read_dict(caseGC50b_dict)
pro.simulate()

