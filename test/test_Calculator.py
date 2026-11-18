import opensimula as osim
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
            "file_name": "mets/WD100.tmy3"
        },{
            "type": "Calculator",
            "name": "Cambiar unidad",
           "input_variables": ["T = Denver.temperature", "w = Denver.abs_humidity"],
            "output_variables": ["T_F","W_kg", "degree_hour_20"],
            "output_units": ["ºF","kg/kg a.s.","ºC"],
            "output_expressions": ["T * 9/5 + 32", "w / 1000", "0.0 if T > 20 else (20 - T)"],
        }
    ]
}


def test_conversion():
    sim = osim.Simulation()
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


def test_calculator_sees_the_results_of_the_time_step(monkeypatch):
    """Variables computed during the time step (a space load) reach the
    calculator: it used to read them before they were computed, always 0."""
    import json
    import pathlib

    import numpy as np

    folder = pathlib.Path(__file__).resolve().parents[1] / "ASHRAE_140" / "LOAD_TEST"
    data = json.loads((folder / "cases" / "case_600.json").read_text())
    data["n_time_steps"] = 72
    data["components"].append({
        "type": "Calculator",
        "name": "loads",
        "input_variables": ["Q = spaces_1.system_sensible_heat", "T = spaces_1.temperature"],
        "output_variables": ["load_kW", "temperature"],
        "output_units": ["kW", "°C"],
        "output_expressions": ["Q / 1000", "T"],
    })
    monkeypatch.chdir(folder)
    sim = osim.Simulation()
    sim.console_print = False
    pro = sim.new_project("calc")
    pro.read_dict(data)
    pro.simulate()
    space = pro.component("spaces_1")
    loads = pro.component("loads")
    Q = space.variable("system_sensible_heat").values
    assert np.abs(Q).max() > 1000  # January in Denver: there is a load
    assert np.allclose(loads.variable("load_kW").values, Q / 1000)
    assert np.allclose(loads.variable("temperature").values, space.variable("temperature").values)
