from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_component, Parameter_component_list, Parameter_float, Parameter_options
from OpenSimula.Variable import Variable


class Surface(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        # Parameters
        self.parameter("type").value = "Surface"
        self.parameter("description").value = "Building surface"
        self.add_parameter(Parameter_options("location", "EXTERNAL", [
                           "EXTERIOR", "INTERIOR", "UNDERGROUND", "ADIABATIC"]))
        self.add_parameter(Parameter_component("construction", ""))
        self.add_parameter(Parameter_component("space", ""))
        self.add_parameter(Parameter_component(
            "adjacent_space", "not_defined"))
        self.add_parameter(Parameter_float("area", 1, "m²", min=0.0))
        self.add_parameter(Parameter_float(
            "azimuth", 0, "°", min=-180, max=180))  # N: 0º, E: 90º, W: -90º, S: 180º
        self.add_parameter(Parameter_float(
            "altitude", 0, "°", min=-90, max=90))  # vertical: 0º, facing up: 90º, facing down: -90º

        # Variables
        self.add_variable(Variable("T_s1", "°C"))
        self.add_variable(Variable("T_s2", "°C"))

    def check(self):
        errors = super().check()
        # Test interior sufaces include adjacent spaces
        if self.parameter("location").value == "INTERIOR" and self.parameter("adjacent_space").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, interior surfaces must define adjacent space"
            )

        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
