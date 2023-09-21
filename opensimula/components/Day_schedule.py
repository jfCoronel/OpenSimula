from opensimula.Parameters import (
    Parameter_int_list,
    Parameter_float_list,
    Parameter_options,
)
from opensimula.Component import Component


class Day_schedule(Component):
    def __init__(self, project):
        Component.__init__(self, project)
        self.parameter("type").value = "Day_schedule"
        self.parameter("name").value = "day_schedule_x"
        self.parameter("description").value = "Time schedule for a day"
        self.add_parameter(Parameter_int_list("time_steps", [3600], "s"))
        self.add_parameter(Parameter_float_list("values", [0, 10]))
        self.add_parameter(
            Parameter_options("interpolation", "STEP", ["STEP", "LINEAR"])
        )

    def check(self):
        errors = super().check()  # Check parameters
        # Test time_steps and values sizes
        if (
            len(self.parameter("time_steps").value)
            != len(self.parameter("values").value) - 1
        ):
            errors.append(
                f"Error in component: {self.parameter('name').value}, time_steps size must be values size minus 1"
            )

        # Test total time steps
        total_time = 0
        for dt in self.parameter("time_steps").value:
            total_time += dt
        if total_time > 24 * 3600:
            errors.append(
                f"Error in component: {self.parameter('name').value}, the sum of the time_steps is greater than one day (86400 s)"
            )
        return errors
