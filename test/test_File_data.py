import opensimula as osm

project_dic = {
    "name": "Test project",
    "time_step": 3600,
    "n_time_steps": 8760,
    "components": [
        {
            "type": "File_data",
            "name": "datas",
            "file_type": "CSV",
            "file_name": "test/examples/data_example.csv",
        }
    ],
}


def test_File_data_CSV():
    sim = osm.Simulation()
    p1 = osm.Project(sim)
    p1.read_dict(project_dic)
    p1.simulate()
    t = p1.component("datas").variable("temperature").array

    assert len(t) == 8760
    assert t[0] == 15.1
    assert t[-1] == 13.6


def test_File_data_EXCEL():
    sim = osm.Simulation()
    p1 = osm.Project(sim)
    p1.read_dict(project_dic)
    p1.component("datas").parameter("file_type").value = "EXCEL"
    p1.component("datas").parameter(
        "file_name"
    ).value = "test/examples/data_example.xlsx"
    p1.simulate()
    t = p1.component("datas").variable("temperature").array

    assert len(t) == 8760
    assert t[0] == 15.1
    assert t[-1] == 13.6
