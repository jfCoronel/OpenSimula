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
            "file_name": "test/sevilla.met"
        },
        {
            "type": "File_met",
            "name": "denver",
            "file_type": "TMY3",
            "file_name": "test/WD100.tmy3"
        },
        {
            "type": "File_met",
            "name": "ASHRAE_124_TMY2",
            "file_type": "TMY2",
            "file_name": "test/CE100A.TM2"
        }
    ]
}


def test_File_met_1h():
    sim = osm.Simulation()
    p1 = sim.new_project("p1")
    p1.read_dict(project)
    p1.simulate()
    hs = p1.component("sevilla").variable("sol_hour").values
    t = p1.component("sevilla").variable("temperature").values

    assert len(hs) == 8760
    assert hs[10] == pytest.approx(9.042, 0.001)
    assert t[10] == pytest.approx(15.269, 0.001)
    assert hs[-1] == pytest.approx(22.06089, 0.001)


def test_File_met_15m():
    sim = osm.Simulation()
    p1 = sim.new_project("p1")
    p1.read_dict(project)
    p1.parameter("time_step").value = 15*60
    p1.parameter("n_time_steps").value = 8760*4
    p1.simulate()
    hs = p1.component("sevilla").variable("sol_hour").values
    t = p1.component("sevilla").variable("temperature").values

    assert len(hs) == 8760*4
    assert hs[40] == pytest.approx(8.667, 0.001)
    assert t[40] == pytest.approx(14.634, 0.001)
    assert hs[-4] == pytest.approx(21.68589, 0.001)


def test_File_tmy3_1h():
    sim = osm.Simulation()
    p1 = sim.new_project("p1")
    p1.read_dict(project)
    p1.simulate()
    t = p1.component("denver").variable("temperature").values
    t_wb = p1.component("denver").variable("wet_bulb_temp").values
    t_sky = p1.component("denver").variable("sky_temperature").values
    r_dir = p1.component("denver").variable("sol_direct").values
    r_dif = p1.component("denver").variable("sol_diffuse").values

    assert len(t) == 8760
    assert t[12] == pytest.approx(4.4, 0.001)
    assert t_wb[12] == pytest.approx(-1.277, 0.001)
    assert t_sky[12] == pytest.approx(-10.07, 0.001)
    assert r_dir[12] == pytest.approx(173, 0.1)
    assert r_dif[12] == pytest.approx(189, 0.1)

    # Radiación inclinada sur
    assert p1.component("denver").solar_direct_rad(
        12, 0, 0) == pytest.approx(337.97, 0.01)
    assert p1.component("denver").solar_diffuse_rad(
        12, 0, 0) == pytest.approx(186.04, 0.01)


def test_File_tmy2_1h():
    sim = osm.Simulation()
    p1 = sim.new_project("p1")
    p1.read_dict(project)
    p1.simulate()
    t = p1.component("ASHRAE_124_TMY2").variable("temperature").values
    hr = p1.component("ASHRAE_124_TMY2").variable("rel_humidity").values
    r_dir = p1.component("ASHRAE_124_TMY2").variable("sol_direct").values
    r_dif = p1.component("ASHRAE_124_TMY2").variable("sol_diffuse").values

    assert len(t) == 8760
    assert t[12] == pytest.approx(46.1, 0.001)
    assert hr[12] == pytest.approx(16, 0.001)
    assert r_dir[12] == pytest.approx(8, 0.1)
    assert r_dif[12] == pytest.approx(137, 0.1)
