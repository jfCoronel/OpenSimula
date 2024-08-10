from OpenSimula.components.Surface import Surface
from OpenSimula.Parameters import Parameter_component
from OpenSimula.Variable import Variable


class Real_surface(Surface):
    def __init__(self, name, project):
        Surface.__init__(self, name, project)
        # Parameters
        self.parameter("type").value = "Real_surface"
        self.parameter("description").value = "Building real surface"
        self.add_parameter(Parameter_component(
            "construction", "not_defined", ["Construction"]))

        # Variables
        self.add_variable(Variable("T_s0", "°C"))
        self.add_variable(Variable("T_s1", "°C"))
        self.add_variable(Variable("q_cd0", "W/m²"))
        self.add_variable(Variable("q_cd1", "W/m²"))
        self.add_variable(Variable("p_0", "W/m²"))
        self.add_variable(Variable("p_1", "W/m²"))
        self.add_variable(Variable("q_cv0", "W/m²"))
        self.add_variable(Variable("q_cv1", "W/m²"))
        self.add_variable(Variable("q_sol0", "W/m²"))
        self.add_variable(Variable("q_sol1", "W/m²"))
        self.add_variable(Variable("q_swig0", "W/m²"))
        self.add_variable(Variable("q_swig1", "W/m²"))
        self.add_variable(Variable("q_lwig0", "W/m²"))
        self.add_variable(Variable("q_lwig1", "W/m²"))
        self.add_variable(Variable("q_lwt0", "W/m²"))
        self.add_variable(Variable("q_lwt1", "W/m²"))

        # k values must be calculated by each subclass
        self.k = [1.0, 2.0]
        self.k_01 = -1

    def check(self):
        errors = super().check()
        # Test construction defined
        if self.parameter("construction").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, non virtual surfaces must define its construction."
            )
        return errors

    def radiant_property(self, prop, radiation_type, side, theta=0):
        return self.parameter("construction").component.radiant_property(prop, radiation_type, side, theta)
