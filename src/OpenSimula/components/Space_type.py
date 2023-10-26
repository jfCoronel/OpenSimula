from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_float, Parameter_component
from OpenSimula.Variable import Variable


class Space_type(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Space_type"
        self.parameter("description").value = "Type of space, internal gains definition"
        self.add_parameter(Parameter_float("people_density", 10, "m²/p", min=0.01))
        self.add_parameter(Parameter_float("people_sensible", 70, "W/p", min=0))
        self.add_parameter(Parameter_float("people_latent", 35, "W/p", min=0))
        self.add_parameter(
            Parameter_float("people_radiant_fraction", 0.6, "", min=0, max=1)
        )
        self.add_parameter(Parameter_component("people_schedule"))
        self.add_parameter(Parameter_float("light_density", 10, "W/m²", min=0))
        self.add_parameter(
            Parameter_float("light_radiant_fraction", 0.6, "", min=0, max=1)
        )
        self.add_parameter(Parameter_component("light_schedule"))
        self.add_parameter(Parameter_float("other_gains_density", 10, "W/m²", min=0))
        self.add_parameter(
            Parameter_float("other_gains_latent_fraction", 0.0, "", min=0, max=1)
        )
        self.add_parameter(
            Parameter_float("other_gains_radiant_fraction", 0.5, "", min=0, max=1)
        )
        self.add_parameter(Parameter_component("other_gains_schedule"))

    def pre_simulation(self, n_time_steps, delta_t):
        self.del_all_variables()
        self.add_variable(Variable("people_convective", n_time_steps, unit="W/m²"))
        self.add_variable(Variable("people_radiant", n_time_steps, unit="W/m²"))
        self.add_variable(Variable("people_latent", n_time_steps, unit="W/m²"))
        self.add_variable(Variable("light_convective", n_time_steps, unit="W/m²"))
        self.add_variable(Variable("light_radiant", n_time_steps, unit="W/m²"))
        self.add_variable(Variable("other_gains_convective", n_time_steps, unit="W/m²"))
        self.add_variable(Variable("other_gains_radiant", n_time_steps, unit="W/m²"))
        self.add_variable(Variable("other_gains_latent", n_time_steps, unit="W/m²"))

    def pre_iteration(self, time_index, date):
        # People
        if self.parameter("people_schedule").value == "not_defined":
            people = 1
        else:
            people = (
                self.parameter("people_schedule")
                .component.variable("values")
                .array[time_index]
            )
        self.variable("people_convective").array[time_index] = (
            people
            * self.parameter("people_sensible").value
            * (1 - self.parameter("people_radiant_fraction").value)
            / self.parameter("people_density").value
        )
        self.variable("people_radiant").array[time_index] = (
            people
            * self.parameter("people_sensible").value
            * self.parameter("people_radiant_fraction").value
            / self.parameter("people_density").value
        )

        self.variable("people_latent").array[time_index] = (
            people
            * self.parameter("people_latent").value
            / self.parameter("people_density").value
        )

        # Light
        if self.parameter("light_schedule").value == "not_defined":
            light = 1
        else:
            light = (
                self.parameter("light_schedule")
                .component.variable("values")
                .array[time_index]
            )
        self.variable("light_convective").array[time_index] = (
            light
            * self.parameter("light_density").value
            * (1 - self.parameter("light_radiant_fraction").value)
        )
        self.variable("light_radiant").array[time_index] = (
            light
            * self.parameter("light_density").value
            * self.parameter("light_radiant_fraction").value
        )

        # Other gains
        if self.parameter("other_gains_schedule").value == "not_defined":
            other = 1
        else:
            other = (
                self.parameter("other_gains_schedule")
                .component.variable("values")
                .array[time_index]
            )
        self.variable("other_gains_convective").array[time_index] = (
            other
            * self.parameter("other_gains_density").value
            * (1 - self.parameter("other_gains_latent_fraction").value)
            * (1 - self.parameter("other_gains_radiant_fraction").value)
        )
        self.variable("other_gains_radiant").array[time_index] = (
            other
            * self.parameter("other_gains_density").value
            * (1 - self.parameter("other_gains_latent_fraction").value)
            * self.parameter("other_gains_radiant_fraction").value
        )
        self.variable("other_gains_latent").array[time_index] = (
            other
            * self.parameter("other_gains_density").value
            * self.parameter("other_gains_latent_fraction").value
        )
