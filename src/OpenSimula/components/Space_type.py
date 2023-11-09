from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_float, Parameter_component, Parameter_variable_list
from OpenSimula.Variable import Variable


class Space_type(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Space_type"
        self.parameter("description").value = "Type of space, internal gains definition"
        # Parameters
        self.add_parameter(Parameter_variable_list("aux_variables"))
        self.add_parameter(Parameter_float("people_density", 10, "m²/p", min=0.01))
        self.add_parameter(Parameter_float("people_sensible", 70, "W/p", min=0))
        self.add_parameter(Parameter_float("people_latent", 35, "W/p", min=0))
        self.add_parameter(Parameter_float("people_radiant_fraction", 0.6, "", min=0, max=1))
        self.add_parameter(Parameter_float("light_density", 10, "W/m²", min=0))
        self.add_parameter(Parameter_float("light_radiant_fraction", 0.6, "", min=0, max=1))
        self.add_parameter(Parameter_float("other_gains_density", 10, "W/m²", min=0))
        self.add_parameter(Parameter_float("other_gains_latent_fraction", 0.0, "", min=0, max=1))
        self.add_parameter(Parameter_float("other_gains_radiant_fraction", 0.5, "", min=0, max=1))
        # Variables
        self.add_variable(Variable("people_convective", unit="W/m²"))
        self.add_variable(Variable("people_radiant", unit="W/m²"))
        self.add_variable(Variable("people_latent", unit="W/m²"))
        self.add_variable(Variable("light_convective", unit="W/m²"))
        self.add_variable(Variable("light_radiant", unit="W/m²"))
        self.add_variable(Variable("other_gains_convective", unit="W/m²"))
        self.add_variable(Variable("other_gains_radiant", unit="W/m²"))
        self.add_variable(Variable("other_gains_latent", unit="W/m²"))

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps,delta_t)
        

    def pre_iteration(self, time_index, date):
        # People
        if self.parameter("people_schedule").value == "not_defined":
            people = 1
        else:
            people = (
                self.parameter("people_schedule")
                .component.variable("values")
                .values[time_index]
            )
        self.variable("people_convective").values[time_index] = (
            people
            * self.parameter("people_sensible").value
            * (1 - self.parameter("people_radiant_fraction").value)
            / self.parameter("people_density").value
        )
        self.variable("people_radiant").values[time_index] = (
            people
            * self.parameter("people_sensible").value
            * self.parameter("people_radiant_fraction").value
            / self.parameter("people_density").value
        )

        self.variable("people_latent").values[time_index] = (
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
                .values[time_index]
            )
        self.variable("light_convective").values[time_index] = (
            light
            * self.parameter("light_density").value
            * (1 - self.parameter("light_radiant_fraction").value)
        )
        self.variable("light_radiant").values[time_index] = (
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
                .values[time_index]
            )
        self.variable("other_gains_convective").values[time_index] = (
            other
            * self.parameter("other_gains_density").value
            * (1 - self.parameter("other_gains_latent_fraction").value)
            * (1 - self.parameter("other_gains_radiant_fraction").value)
        )
        self.variable("other_gains_radiant").values[time_index] = (
            other
            * self.parameter("other_gains_density").value
            * (1 - self.parameter("other_gains_latent_fraction").value)
            * self.parameter("other_gains_radiant_fraction").value
        )
        self.variable("other_gains_latent").values[time_index] = (
            other
            * self.parameter("other_gains_density").value
            * self.parameter("other_gains_latent_fraction").value
        )
