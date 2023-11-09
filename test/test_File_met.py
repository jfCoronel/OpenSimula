import pytest
import OpenSimula as osm

project = {
    "name": "Project test meteo",
    "time_step": 3600,
    "n_time_steps": 8760,
    "components": [
        {
            "type": "File_met",
            "name": "sevilla",
            "file_name": "examples/met_files/sevilla.met"
        }
    ],
}


def test_File_met_1h():
    sim = osm.Simulation()
    p1 = osm.Project("p1",sim)
    p1.read_dict(project)
    p1.simulate()
    hs = p1.component("sevilla").variable("sol_hour").values
    t = p1.component("sevilla").variable("temperature").values

    assert len(hs) == 8760
    assert hs[10] == pytest.approx(8.5533, 0.001)
    assert t[10] == pytest.approx(13.591, 0.001)
    assert hs[-1] == pytest.approx(21.5609, 0.001)

def test_File_met_15m():
    sim = osm.Simulation()
    p1 = osm.Project("p1",sim)
    p1.read_dict(project)
    p1.parameter("time_step").value = 15*60
    p1.parameter("n_time_steps").value = 8760*4
    p1.simulate()
    hs = p1.component("sevilla").variable("sol_hour").values
    t = p1.component("sevilla").variable("temperature").values

    assert len(hs) == 8760*4
    assert hs[40] == pytest.approx(8.5533, 0.001)
    assert t[40] == pytest.approx(13.591, 0.001)
    assert hs[-4] == pytest.approx(21.5609, 0.001)



