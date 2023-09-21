import opensimula as osm

project_dic = {
    "name": "Test project",
    "time_step": 3600,
    "n_time_steps": 8760,
    "components": [
        {
            "type": "Day_schedule",
            "name": "working_day",
            "time_steps": [28800, 18000, 7200, 14400],
            "values": [0, 100, 0, 80, 0],
            "interpolation": "STEP",
        },
        {
            "type": "Day_schedule",
            "name": "holiday_day",
            "time_steps": [],
            "values": [0],
            "interpolation": "STEP",
        },
    ],
}


def test_day_scehdule():
    sim = osm.Simulation()
    p1 = osm.Project(sim)
    p1.read_dict(project_dic)

    assert 3 == 2
