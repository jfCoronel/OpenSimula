import datetime as dt
from bisect import bisect
from OpenSimula.Parameters import Parameter_component_list, Parameter_string_list
from OpenSimula.Component import Component
from OpenSimula.Variable import Variable


class Year_schedule(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Year_schedule"
        self.parameter("description").value = "Time schedule for a year"
        self.add_parameter(Parameter_string_list("periods", ["01/06"]))
        self.add_parameter(
            Parameter_component_list(
                "weeks_schedules", ["not_defined",
                                    "not_defined"], ["Week_schedule"]
            )
        )
        # Create Variable
        self.add_variable(Variable(
            "values", "", "Values obtained using year, weeks and days schedules for each of the simulation time steps."))

    def check(self):
        errors = super().check()
        if (
            len(self.parameter("periods").value)
            != len(self.parameter("weeks_schedules").value) - 1
        ):
            errors.append(
                f"Error: {self.parameter('name').value}, periods size must be weeks_schedules size minus 1"
            )
        # Check periods format
        try:
            days = []
            for period in self.parameter("periods").value:
                datetime = dt.datetime.strptime(period, "%d/%m")
                days.append(datetime.timetuple().tm_yday)
            if sorted(days) != days:
                errors.append(
                    f"Error: {self.parameter('name').value}, periods are not ordered"
                )
        except ValueError:
            error = f"Error: {self.parameter('name').value}, periods does not match format (dd/mm)"
            errors.append(error)
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)

        # Create array of periods_days
        self._periods_days_ = []
        for period in self.parameter("periods").value:
            datetime = dt.datetime.strptime(period, "%d/%m")
            self._periods_days_.append(datetime.timetuple().tm_yday)

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        if daylight_saving:  # adding 1 h
            date = date + dt.timedelta(0, 3600)
        self.variable("values").values[time_index] = self.get_value(date)

    def get_value(self, date):
        year_day = date.timetuple().tm_yday
        index = bisect(self._periods_days_, year_day)
        return self.parameter("weeks_schedules").component[index].get_value(date)
