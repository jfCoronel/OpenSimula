import OpenSimula as osm

project_dic = {
    "name": "Test project",
    "time_step": 3600,
    "n_time_steps": 48,
    "components": [
        {
            "type": "File_data",
            "name": "datas",
            "file_type": "CSV",
            "file_name": "test/data_example.csv",
            "file_step": "SIMULATION"
        }
    ],
}


def test_File_data_CSV():
    sim = osm.Simulation()
    p1 = sim.new_project("p1")
    p1.read_dict(project_dic)
    p1.simulate()
    t = p1.component("datas").variable("temperature").values

    assert len(t) == 48
    assert t[0] == 15.1
    assert t[-1] == 13.6


def test_File_data_EXCEL():
    sim = osm.Simulation()
    p1 = sim.new_project("p1")
    p1.read_dict(project_dic)
    p1.component("datas").parameter("file_type").value = "EXCEL"
    p1.component("datas").parameter(
        "file_name"
    ).value = "test/data_example.xlsx"
    p1.simulate()
    t = p1.component("datas").variable("temperature").values

    assert len(t) == 48
    assert t[0] == 15.1
    assert t[-1] == 13.6


def test_File_data_CSV_2h():
    sim = osm.Simulation()
    p1 = sim.new_project("p1")
    p1.read_dict(project_dic)
    p1.component("datas").set_parameters(
        {"file_step": "OWN", "initial_time": "01/01/2001 00:30:00", "time_step": 7200})
    p1.simulate()
    t = p1.component("datas").variable("temperature").values
    assert len(t) == 48
    assert t[0] == 15.1
    assert t[1] == (14.6+15.1)/2


def test_File_data_CSV_05h():
    sim = osm.Simulation()
    p1 = sim.new_project("p1")
    p1.read_dict(project_dic)
    p1.component("datas").set_parameters(
        {"file_step": "OWN", "initial_time": "01/01/2001 00:30:00", "time_step": 1800})
    p1.simulate()
    t = p1.component("datas").variable("temperature").values

    assert len(t) == 48
    assert t[0] == 15.1
    assert t[1] == 14.1
