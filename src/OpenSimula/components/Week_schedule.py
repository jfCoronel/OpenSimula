from OpenSimula.Parameters import Parameter_component_list
from OpenSimula.Component import Component


class Week_schedule(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Week_schedule"
        self.parameter("description").value = "Time schedule for a week"
        self.add_parameter(Parameter_component_list(
            "days_schedules", ["not_defined"], ["Day_schedule"]))

    def check(self):
        errors = super().check()
        # Test if 1 or 7 has been defined
        if (
            len(self.parameter("days_schedules").value) != 1
            and len(self.parameter("days_schedules").value) != 7
        ):
            errors.append(
                f"Error: {self.parameter('name').value}, days_schedules parameter must contain 1 or 7 Day_schedule components"
            )

        return errors

    def get_value(self, date):
        if len(self.parameter("days_schedules").value) == 1:
            return self.parameter("days_schedules").component[0].get_value(date)
        else:
            index = date.weekday()
            return self.parameter("days_schedules").component[index].get_value(date)
