import OpenSimula as osm

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
        {
            "type": "Week_schedule",
            "name": "working_week",
            "days_schedules": [
                "working_day",
                "working_day",
                "working_day",
                "working_day",
                "working_day",
                "holiday_day",
                "holiday_day",
            ],
        },
        {
            "type": "Week_schedule",
            "name": "holiday_week",
            "days_schedules": ["holiday_day"],
        },
        {
            "type": "Year_schedule",
            "name": "year",
            "periods": ["01/08", "01/09"],
            "weeks_schedules": ["working_week", "holiday_week", "working_week"],
        },
    ],
}


def test_schedule_step():
    sim = osm.Simulation()
    p1 = osm.Project(sim)
    p1.read_dict(project_dic)
    p1.simulate()

    assert p1.component("year").variable("values").array[10] == 100
    assert p1.component("year").variable("values").array[8759] == 0


def test_schedule_linear():
    sim = osm.Simulation()
    p1 = osm.Project(sim)
    p1.read_dict(project_dic)
    p1.component("working_day").parameter("interpolation").value = "LINEAR"
    p1.simulate()

    assert p1.component("year").variable("values").array[10] == 60.0
    assert p1.component("year").variable("values").array[8759] == 0
