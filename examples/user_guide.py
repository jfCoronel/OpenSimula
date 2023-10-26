import OpenSimula as osm

sim = osm.Simulation()
pro = osm.Project("Project one",sim)
pro.parameter("description").value = "Project example"
pro.parameter("time_step").value = 60*15
pro.parameter("n_time_steps").value = 24*4*7
pro.parameter("initial_time").value = "01/06/2001 00:00:00"
pro.parameter_dataframe()

working_day = osm.components.Day_schedule("working_day",pro)
working_day.parameter("time_steps").value = [8*3600, 5*3600, 2*3600, 4*3600]
working_day.parameter("values").value = [0, 100, 0, 80, 0]

holiday_day = osm.components.Day_schedule("holiday_day",pro)
holiday_day.parameter("time_steps").value = []
holiday_day.parameter("values").value = [0]

week = osm.components.Week_schedule("week",pro)
week.parameter("days_schedules").value = ["working_day","working_day","working_day","working_day","working_day","holiday_day","holiday_day"]

year = osm.components.Year_schedule("year",pro)
year.parameter("periods").value = []
year.parameter("weeks_schedules").value = ["week"]

pro.check()
pro.simulate()