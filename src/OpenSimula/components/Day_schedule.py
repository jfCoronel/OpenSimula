from bisect import bisect
from OpenSimula.Parameters import (
    Parameter_int_list,
    Parameter_float_list,
    Parameter_options,
)
from OpenSimula.Component import Component


class Day_schedule(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Day_schedule"
        self.parameter("description").value = "Time schedule for a day"
        self.add_parameter(Parameter_int_list(
            "time_steps", [3600], "s", min=1))
        self.add_parameter(Parameter_float_list("values", [0, 10]))
        self.add_parameter(
            Parameter_options("interpolation", "STEP", ["STEP", "LINEAR"])
        )

    def check(self):
        errors = super().check()
        # Test time_steps and values sizes
        if (
            len(self.parameter("time_steps").value)
            != len(self.parameter("values").value) - 1
        ):
            errors.append(
                f"Error: {self.parameter('name').value}, time_steps size must be values size minus 1"
            )

        # Test total time steps
        total_time = 0
        for dt in self.parameter("time_steps").value:
            total_time += dt
        if total_time > 24 * 3600:
            errors.append(
                f"Error: {self.parameter('name').value}, the sum of the time_steps is greater than one day (86400 s)"
            )
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        # Create array of periods
        self._periods_ = [0]
        acumulated = 0
        for period in self.parameter("time_steps").value:
            acumulated += period
            self._periods_.append(acumulated)
        self._periods_.append(24 * 3600)

    def get_value(self, date):
        seconds = date.hour * 3600 + date.minute * 60 + date.second
        index = bisect(self._periods_, seconds)
        if self.parameter("interpolation").value == "LINEAR":
            x_i = self._periods_[index - 1]
            x_f = self._periods_[index]
            y_i = self.parameter("values").value[index - 1]
            if index < len(self.parameter("values").value):
                y_f = self.parameter("values").value[index]
            else:
                y_f = self.parameter("values").value[0]
            return (seconds - x_i) / (x_f - x_i) * (y_f - y_i) + y_i
        else:
            return self.parameter("values").value[index - 1]
