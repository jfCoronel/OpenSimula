import OpenSimula as osm

case_ce100_dict = {
    "name": "Case CE100",
    "time_step": 3600,
    "n_time_steps": 8760,
    "initial_time": "01/01/2001 00:00:00",
    "components": [
        {
            "type": "File_met",
            "name": "T_ext_cte",
            "file_type": "TMY2",
            "file_name": "test/CE100A.TM2"
        },    
        {
            "type": "Material",
            "name": "Insulation",
            "conductivity": 0.01,
            "density": 1,
            "specific_heat": 1
        },
        {
            "type": "Construction",
            "name": "Adiabatic_Wall",
            "solar_alpha": [0.1,0.6],
            "lw_epsilon": [0.9,0.9],
            "materials": [
                "Insulation"
            ],
            "thicknesses": [
                1.0
            ]
        },
        {
            "type": "Space_type",
            "name": "constant_gain_space",
            "people_density": "0",
            "light_density": "0",
            "other_gains_density": "112.5",
            "other_gains_radiant_fraction": 0,
            "infiltration": "0",
            "heating_setpoint": "20",
            "cooling_setpoint": "22.2",
            "heating_on_off": "0",
            "cooling_on_off": "1"
        },
        {
            "type": "HVAC_DX_equipment",
            "name": "HVAC_equipment",
            "nominal_air_flow": 0.4248,
            "nominal_total_cooling_capacity": 7951,
            "nominal_sensible_cooling_capacity": 6136,
            "nominal_compressor_cooling_power": 1860,
            "nominal_fan_cooling_power": 230,
            "nominal_other_cooling_power": 108,
            "nominal_cooling_conditions": [26.7,19.4,35],
            "total_cooling_expression": "0.0003561*T_odb + 0.03788*T_ewb - 0.00002701*T_odb^2 + 0.0003109*T_ewb^2 - 0.0004733*T_odb*T_ewb + 0.48799",
            "sensible_cooling_expression": "0.0009756*T_odb - 0.06613*T_ewb + 0.08618*T_edb - 0.00003684*T_odb^2 - 0.004368*T_ewb^2 - 0.002095*T_edb^2 + 0.0004198*T_odb*T_ewb - 0.0004874*T_odb*T_edb + 0.005634*T_ewb*T_edb + 0.39218",
            "compressor_cooling_expression": "0.01519*T_odb + 0.01531*T_ewb + 0.00005392*T_odb^2 + 0.00009073*T_ewb^2  - 0.0002189*T_odb*T_ewb + 0.22",
            "EER_expression": "1 - 0.229*(1-F_load)"
        },
        {
            "type": "Building",
            "name": "Building",
            "file_met": "T_ext_cte",
            "albedo": 0.2,
            "azimuth": 0,
            "shadow_calculation": "INSTANT"
        },
        {
            "type": "Space",
            "name": "space_1",
            "building": "Building",
            "space_type": "constant_gain_space",
            "floor_area": 48,
            "volume": 129.6,
            "furniture_weight": 0,
            "perfect_conditioning": True
        },
        {
            "type": "HVAC_DX_system",
            "name": "HVAC_system",
            "equipment": "HVAC_equipment",
            "space": "space_1",
            "file_met": "T_ext_cte",
            "supply_air_flow": 0.4248,
            "outdoor_air_flow": 0
        },
        {
            "type": "Exterior_surface",
            "name": "north_wall",
            "construction": "Adiabatic_Wall",
            "space": "space_1",
            "ref_point": [
                8,
                6,
                0
            ],
            "width": 8,
            "height": 2.7,
            "azimuth": 180,
            "altitude": 0,
            "h_cv": [
                24.17,
                3.16
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "east_wall",
            "construction": "Adiabatic_Wall",
            "space": "space_1",
            "ref_point": [
                8,
                0,
                0
            ],
            "width": 6,
            "height": 2.7,
            "azimuth": 90,
            "altitude": 0,
             "h_cv": [
                24.17,
                3.16
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "south_wall",
            "construction": "Adiabatic_Wall",
            "space": "space_1",
            "ref_point": [
                0,
                0,
                0
            ],
            "width": 8,
            "height": 2.7,
            "azimuth": 0,
            "altitude": 0,
             "h_cv": [
                24.17,
                3.16
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "west_wall",
            "construction": "Adiabatic_Wall",
            "space": "space_1",
            "ref_point": [
                0,
                6,
                0
            ],
            "width": 6,
            "height": 2.7,
            "azimuth": -90,
            "altitude": 0,
             "h_cv": [
                24.17,
                3.16
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "roof_wall",
            "construction": "Adiabatic_Wall",
            "space": "space_1",
            "ref_point": [
                0,
                0,
                2.7
            ],
            "width": 8,
            "height": 6,
            "azimuth": 0,
            "altitude": 90,
            "h_cv": [
                24.17,
                1.0
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "floor_wall",
            "construction": "Adiabatic_Wall",
            "space": "space_1",
            "ref_point": [
                0,
                6,
                0
            ],
            "width": 8,
            "height": 6,
            "azimuth": 0,
            "altitude": -90,
            "h_cv": [
                29.3,
                4.13
            ]
        }
    ]
}

sim = osm.Simulation()
pro = sim.new_project("pro")
pro.read_dict(case_ce100_dict)
pro.simulate()


