import datetime as dt
from bisect import bisect
from opensimula.Parameters import Parameter_component_list, Parameter_string_list
from opensimula.Component import Component
from opensimula.Variable import Variable


class Year_schedule(Component):
    def __init__(self, project):
        Component.__init__(self, project)
        self.parameter("type").value = "Year_schedule"
        self.parameter("name").value = "year_schedule_x"
        self.parameter("description").value = "Time schedule for a year"
        self.add_parameter(Parameter_string_list("periods", ["01/06"]))
        self.add_parameter(
            Parameter_component_list("weeks_schedules", ["not_defined", "not_defined"])
        )

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

    def pre_simulation(self, n_time_steps):
        super().pre_simulation(n_time_steps)
        self.del_all_variables()
        # Create Variable
        self.add_variable(Variable("values", n_time_steps))
        # Create array of periods_days
        self._periods_days_ = []
        for period in self.parameter("periods").value:
            datetime = dt.datetime.strptime(period, "%d/%m")
            self._periods_days_.append(datetime.timetuple().tm_yday)

    def pre_iteration(self, time_index, date):
        super().pre_iteration(time_index, date)
        self.variable("values").array[time_index] = self.get_value(date)

    def get_value(self, date):
        year_day = date.timetuple().tm_yday
        index = bisect(self._periods_days_, year_day)
        return self.parameter("weeks_schedules").component[index].get_value(date)
