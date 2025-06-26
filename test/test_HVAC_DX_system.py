import OpenSimula as osm
import pytest
import numpy as np

case610_dict = {
    "name": "Case 610",
    "time_step": 3600,
    "n_time_steps": 8760,
    "initial_time": "01/01/2001 00:00:00",
    "simulation_file_met": "Denver",
    "components": [
        {
            "type": "File_met",
            "name": "Denver",
            "file_type": "TMY3",
            "file_name": "mets/WD100.tmy3"
        },
        {
            "type": "Material",
            "name": "Plasterboard",
            "conductivity": 0.16,
            "density": 950,
            "specific_heat": 840
        },
        {
            "type": "Material",
            "name": "Fiberglass_quilt",
            "conductivity": 0.04,
            "density": 12,
            "specific_heat": 840
        },
        {
            "type": "Material",
            "name": "Wood_siding",
            "conductivity": 0.14,
            "density": 530,
            "specific_heat": 900
        },
        {
            "type": "Material",
            "name": "Insulation",
            "conductivity": 0.04,
            "density": 0.1,
            "specific_heat": 0.1
        },
        {
            "type": "Material",
            "name": "Timber_flooring",
            "conductivity": 0.14,
            "density": 650,
            "specific_heat": 1200
        },
        {
            "type": "Material",
            "name": "Roofdeck",
            "conductivity": 0.14,
            "density": 530,
            "specific_heat": 900
        },
        {
            "type": "Construction",
            "name": "Wall",
            "solar_alpha": [
                0.6,
                0.6
            ],
            "materials": [
                "Wood_siding",
                "Fiberglass_quilt",
                "Plasterboard"
            ],
            "thicknesses": [
                0.009,
                0.066,
                0.012
            ]
        },
        {
            "type": "Construction",
            "name": "Floor",
            "solar_alpha": [
                0,
                0.6
            ],
            "materials": [
                "Insulation",
                "Timber_flooring"
            ],
            "thicknesses": [
                1.003,
                0.025
            ]
        },
        {
            "type": "Construction",
            "name": "Roof",
            "solar_alpha": [
                0.6,
                0.6
            ],
            "materials": [
                "Roofdeck",
                "Fiberglass_quilt",
                "Plasterboard"
            ],
            "thicknesses": [
                0.019,
                0.1118,
                0.010
            ]
        },
        {
            "type": "Glazing",
            "name": "double_glazing",
            "solar_tau": 0.703,
            "solar_rho": [
                0.128,
                0.128
            ],
            "g": [
                0.769,
                0.769
            ],
            "lw_epsilon": [
                0.84,
                0.84
            ],
            "U": 2.722,
            "f_tau_nor": "-0.1175 * cos_theta**3 - 1.0295 * cos_theta**2 + 2.1354 * cos_theta",
            "f_1_minus_rho_nor": [
                "1.114 * cos_theta**3 - 3.209 * cos_theta**2 + 3.095 * cos_theta",
                "1.114 * cos_theta**3 - 3.209 * cos_theta**2 + 3.095 * cos_theta"
            ]
        },
        {
            "type": "Opening_type",
            "name": "Window",
            "glazing": "double_glazing",
            "frame_fraction": 0,
            "glazing_fraction": 1
        },
        {
            "type": "Space_type",
            "name": "constant_gain_space",
            "people_density": "0",
            "light_density": "0",
            "other_gains_density": "4.1667",
            "other_gains_radiant_fraction": 0.6,
            "infiltration": "0.5"
        },
        {
            "type": "Building",
            "name": "Building",
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
            "furniture_weight": 0
        },
        {
            "type": "Exterior_surface",
            "name": "north_wall",
            "construction": "Wall",
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
                11.9,
                2.2
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "east_wall",
            "construction": "Wall",
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
                11.9,
                2.2
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "south_wall",
            "construction": "Wall",
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
                11.9,
                2.2
            ]
        },
        {
            "type": "Opening",
            "name": "south_window_1",
            "surface": "south_wall",
            "opening_type": "Window",
            "ref_point": [
                0.5,
                0.2
            ],
            "width": 3,
            "height": 2,
            "h_cv": [
                8.0,
                2.4
            ]
        },
        {
            "type": "Opening",
            "name": "south_window_2",
            "surface": "south_wall",
            "opening_type": "Window",
            "ref_point": [
                4.5,
                0.2
            ],
            "width": 3,
            "height": 2,
            "h_cv": [
                8.0,
                2.4
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "west_wall",
            "construction": "Wall",
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
                11.9,
                2.2
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "roof_wall",
            "construction": "Roof",
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
                14.4,
                1.8
            ]
        },
        {
            "type": "Exterior_surface",
            "name": "floor_wall",
            "construction": "Floor",
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
                0.8,
                2.2
            ]
        },
        {
            "type": "Shadow_surface",
            "name": "overhang",
            "building": "Building",
            "ref_point": [
                0,
                -1,
                2.7
            ],
            "width": 8,
            "height": 1,
            "azimuth": 0,
            "altitude": 90
        },
        {
            "type": "HVAC_DX_equipment",
            "name": "HVAC_equipment",
            "nominal_air_flow": 0.417,
            "nominal_total_cooling_capacity": 6900,
            "nominal_sensible_cooling_capacity": 4800,
            "nominal_cooling_power": 2400,
            "indoor_fan_power": 240,
            "total_cooling_capacity_expression": "0.88078 + 0.014248 * T_iwb + 0.00055436 * T_iwb**2 - 0.0075581 * T_odb +	3.2983E-05 * T_odb**2 - 0.00019171 * T_odb * T_iwb",
            "sensible_cooling_capacity_expression": "0.50060 - 0.046438 * T_iwb - 0.00032472 * T_iwb**2 - 0.013202 * T_odb + 7.9307E-05 * T_odb**2 + 0.069958 * T_idb - 3.4276E-05 * T_idb**2",
            "cooling_power_expression": "0.11178 + 0.028493 * T_iwb - 0.00041116 * T_iwb**2 + 0.021414 * T_odb + 0.00016113 * T_odb**2 - 0.00067910 * T_odb * T_iwb",
            "EER_expression": "0.20123 - 0.031218 * F_load + 1.9505 * F_load**2 - 1.1205 * F_load**3",
            "nominal_heating_capacity": 6500,
            "nominal_heating_power": 2825,
            "heating_capacity_expression": "0.81474	+ 0.030682602 * T_owb + 3.2303E-05 * T_owb**2",
            "heating_power_expression": "1.2012 - 0.040063 * T_owb + 0.0010877 * T_owb**2",
            "COP_expression": "0.085652 + 0.93881 * F_load - 0.18344 * F_load**2 + 0.15897 * F_load**3"
        },
        {
            "type": "HVAC_DX_system",
            "name": "system",
            "space": "space_1",
            "equipment": "HVAC_equipment",
            "air_flow": 0.417,
            "outdoor_air_fraction": 0,
            "heating_setpoint": "20",
            "cooling_setpoint": "27",
            "system_on_off": "1",
        }
    ]
}


def test_HVAC_DX_system_without_vent():
    sim = osm.Simulation()
    pro = sim.new_project("pro")
    pro.read_dict(case610_dict)
    pro.simulate()

    load = pro.component("system").variable("Q_sensible").values
    state = pro.component("system").variable("state").values
    heating = np.where(state>0,load,0)
    annual_heating = heating.sum()/1e6
    cooling = np.where(state<0,load,0)
    annual_cooling = cooling.sum()/1e6
    peak_heating = heating.max()/1000
    peak_cooling = cooling.max()/1000
    power = pro.component("system").variable("power").values.sum()/1e6
    annual_latent = pro.component("system").variable("Q_latent").values.sum()/1e6

    assert annual_heating == pytest.approx(3.64855416)
    assert annual_cooling == pytest.approx(5.003493)
    assert peak_heating == pytest.approx(2.75092863)
    assert peak_cooling == pytest.approx(5.7020798)
    assert power == pytest.approx(14.61111)
    assert annual_latent == pytest.approx(0.05586481)
    

def test_HVAC_DX_system_with_vent():
    sim = osm.Simulation()
    pro = sim.new_project("pro")
    pro.read_dict(case610_dict)
    pro.component("system").parameter("outdoor_air_fraction").value = 0.1
    pro.simulate()

    load = pro.component("system").variable("Q_sensible").values
    state = pro.component("system").variable("state").values
    heating = np.where(state>0,load,0)
    annual_heating = heating.sum()/1e6
    cooling = np.where(state<0,load,0)
    annual_cooling = cooling.sum()/1e6
    peak_heating = heating.max()/1000
    peak_cooling = cooling.max()/1000
    power = pro.component("system").variable("power").values.sum()/1e6
    annual_latent = pro.component("system").variable("Q_latent").values.sum()/1e6
    print(annual_heating,annual_cooling,peak_heating,peak_cooling,power,annual_latent)

    assert annual_heating == pytest.approx(6.566097)
    assert annual_cooling == pytest.approx(4.089069)
    assert peak_heating == pytest.approx(4.011399)
    assert peak_cooling == pytest.approx(5.382866)
    assert power == pytest.approx(16.74587)
    assert annual_latent == pytest.approx(0.07842919622)

