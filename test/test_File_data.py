import opensimula as osim

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
    sim = osim.Simulation()
    p1 = sim.new_project("p1")
    p1.read_dict(project_dic)
    p1.simulate()
    t = p1.component("datas").variable("temperature").values

    assert len(t) == 48
    assert t[0] == 15.1
    assert t[-1] == 13.6


def test_File_data_EXCEL():
    sim = osim.Simulation()
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
    sim = osim.Simulation()
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
    sim = osim.Simulation()
    p1 = sim.new_project("p1")
    p1.read_dict(project_dic)
    p1.component("datas").set_parameters(
        {"file_step": "OWN", "initial_time": "01/01/2001 00:30:00", "time_step": 1800})
    p1.simulate()
    t = p1.component("datas").variable("temperature").values

    assert len(t) == 48
    assert t[0] == 15.1
    assert t[1] == 14.1


def test_File_data_SIMULATION_every_column_starts_at_the_first_row():
    # 24 rows and 50 steps: every column repeats the file from its first row
    # (before, the row index went on from one column to the next one, so with a
    # number of steps that is not a multiple of the rows the columns were shifted)
    import pandas as pd

    data = pd.read_csv("test/data_example.csv")
    sim = osim.Simulation()
    p1 = sim.new_project("p1")
    p1.read_dict(project_dic | {"n_time_steps": 50})
    p1.simulate()
    rows = [j % len(data) for j in range(50)]
    for column, name in zip(data.columns, ("n", "temperature", "humidity")):
        values = p1.component("datas").variable(name).values
        assert list(values) == list(data[column].iloc[rows])
