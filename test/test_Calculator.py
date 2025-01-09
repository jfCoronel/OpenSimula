import OpenSimula as osm
import pytest

calculator_dict = {
    "name": "Calculator Test",
    "time_step": 3600,
    "n_time_steps": 8760,
    "initial_time": "01/01/2001 00:00:00",
    "components": [
        {
            "type": "File_met",
            "name": "Denver",
            "file_type": "TMY3",
            "file_name": "test/WD100.tmy3"
        },{
            "type": "Calculator",
            "name": "Cambiar unidad",
           "input_variables": ["T = Denver.temperature", "w = Denver.abs_humidity"],
            "output_variables": ["T_F","W_kg", "degree_hour_20"],
            "output_units": ["ºF","kg/kg a.s.","ºC"],
            "output_expressions": ["T * 9/5 + 32", "w / 1000", "if(T < 20, 20 - T, 0)"],
        }
    ]
}


def test_conversion():
    sim = osm.Simulation()
    pro = sim.new_project("pro")
    pro.read_dict(calculator_dict)
    pro.simulate()

    t_f = pro.component("Cambiar unidad").variable("T_F").values
    w_kg = pro.component("Cambiar unidad").variable("W_kg").values
    degree = pro.component("Cambiar unidad").variable("degree_hour_20").values

    assert t_f[4] == pytest.approx(8.60)
    assert w_kg[4] == pytest.approx(0.001275777)
    assert t_f.mean() == pytest.approx(51.575616438)
    assert degree.sum() == pytest.approx(91224.1)
