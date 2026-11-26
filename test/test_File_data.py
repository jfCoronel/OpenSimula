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


# _________________ file_step ANNUAL: rows of a year from 1 January _________________

def annual(tmp_path, start, n_time_steps, time_step=3600, file_step="ANNUAL"):
    """A file of 8760 hourly rows whose value is the number of the row."""
    import pandas as pd
    path = tmp_path / "year.csv"
    pd.DataFrame({"row [-]": range(8760)}).to_csv(path, index=False)
    sim = osim.Simulation()
    sim.console_print = False
    p = sim.new_project("p")
    p.read_dict({"name": "p", "time_step": time_step, "n_time_steps": n_time_steps,
                 "initial_time": start, "components": [
                     {"type": "File_data", "name": "year", "file_name": str(path),
                      "file_step": file_step}]})
    return sim, p


def test_annual_reads_the_row_of_the_date(tmp_path):
    sim, p = annual(tmp_path, "01/07/2001 00:00:00", 48)
    p.simulate()
    rows = p.component("year").variable("row").values
    assert rows[0] == 181 * 24 and rows[47] == 181 * 24 + 47  # 1 July is day 182


def test_annual_again_every_year(tmp_path):
    sim, p = annual(tmp_path, "31/12/2001 22:00:00", 4)
    p.simulate()
    assert list(p.component("year").variable("row").values) == [8758, 8759, 0, 1]


def test_annual_with_shorter_time_steps(tmp_path):
    sim, p = annual(tmp_path, "01/01/2001 00:00:00", 8, time_step=900)
    p.simulate()
    assert list(p.component("year").variable("row").values) == [0, 0, 0, 0, 1, 1, 1, 1]


def test_warning_annual_file_read_by_simulation_steps(tmp_path):
    sim, p = annual(tmp_path, "01/07/2001 00:00:00", 48, file_step="SIMULATION")
    assert any("ANNUAL" in m.text for m in p.check() if m.level == "WARNING")
    sim, p = annual(tmp_path, "01/01/2001 00:00:00", 48, file_step="SIMULATION")
    assert not any("ANNUAL" in m.text for m in p.check() if m.level == "WARNING")
