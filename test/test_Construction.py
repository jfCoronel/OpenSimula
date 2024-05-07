import OpenSimula as osm
import pytest

project_dic = {
    "name": "Constructions test",
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
            "type": "Material",
            "name": "Heavy material",
            "conductivity": 1.95,
            "density": 2240,
            "specific_heat": 900,
        },
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
            "name": "Light wall",
            "solar_alpha": [0.8, 0.8],
            "materials": ["Light material"],
            "thicknesses": [0.076],
        },
        {
            "type": "Construction",
            "name": "Heavy wall",
            "solar_alpha": [0.8, 0.8],
            "materials": ["Heavy material"],
            "thicknesses": [0.25],
        },
        {
            "type": "Construction",
            "name": "Multilayer wall",
            "solar_alpha": [0.8, 0.8],
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


def test_walls_1h():
    sim = osm.Simulation()
    pro = sim.new_project("Constructions test")
    pro.read_dict(project_dic)
    pro.simulate()

    wall = pro.component("Light wall")
    assert sum(wall._coef_T_a) == pytest.approx(sum(wall._coef_T_b), 0.00001)
    assert sum(wall._coef_T_a) == pytest.approx(sum(wall._coef_T_c), 0.00001)
    U = sum(wall._coef_T_a)/sum(wall._coef_Q)
    assert 1/wall.thermal_resistance() == pytest.approx(U, 0.00001)

    wall = pro.component("Heavy wall")
    assert sum(wall._coef_T_a) == pytest.approx(sum(wall._coef_T_b), 0.00001)
    assert sum(wall._coef_T_a) == pytest.approx(sum(wall._coef_T_c), 0.00001)
    U = sum(wall._coef_T_a)/sum(wall._coef_Q)
    assert 1/wall.thermal_resistance() == pytest.approx(U, 0.00001)

    wall = pro.component("Multilayer wall")
    assert sum(wall._coef_T_a) == pytest.approx(sum(wall._coef_T_b), 0.00001)
    assert sum(wall._coef_T_a) == pytest.approx(sum(wall._coef_T_c), 0.00001)
    U = sum(wall._coef_T_a)/sum(wall._coef_Q)
    assert 1/wall.thermal_resistance() == pytest.approx(U, 0.00001)


def test_walls_15min():
    sim = osm.Simulation()
    pro = sim.new_project("Constructions test")
    pro.read_dict(project_dic)
    pro.parameter("time_step").value = 60*15
    pro.simulate()

    wall = pro.component("Light wall")
    assert sum(wall._coef_T_a) == pytest.approx(sum(wall._coef_T_b), 0.00001)
    assert sum(wall._coef_T_a) == pytest.approx(sum(wall._coef_T_c), 0.00001)
    U = sum(wall._coef_T_a)/sum(wall._coef_Q)
    assert 1/wall.thermal_resistance() == pytest.approx(U, 0.00001)

    wall = pro.component("Heavy wall")
    assert sum(wall._coef_T_a) == pytest.approx(sum(wall._coef_T_b), 0.00001)
    assert sum(wall._coef_T_a) == pytest.approx(sum(wall._coef_T_c), 0.00001)
    U = sum(wall._coef_T_a)/sum(wall._coef_Q)
    assert 1/wall.thermal_resistance() == pytest.approx(U, 0.00001)

    wall = pro.component("Multilayer wall")
    assert sum(wall._coef_T_a) == pytest.approx(sum(wall._coef_T_b), 0.00001)
    assert sum(wall._coef_T_a) == pytest.approx(sum(wall._coef_T_c), 0.00001)
    U = sum(wall._coef_T_a)/sum(wall._coef_Q)
    assert 1/wall.thermal_resistance() == pytest.approx(U, 0.00001)
