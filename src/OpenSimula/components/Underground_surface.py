from OpenSimula.components.Surface import Surface
from OpenSimula.Parameters import Parameter_component, Parameter_float, Parameter_options, Parameter_boolean
from OpenSimula.Variable import Variable


class Underground_surface(Surface):
    def __init__(self, name, project):
        Surface.__init__(self, name, project)
        # Parameters
        self.parameter("type").value = "Underground_surface"
        self.parameter("description").value = "Building underground surface"
        self.add_parameter(Parameter_component("space", "not_defined"))
        self.add_parameter(Parameter_float("h_cv", 2, "W/m²K", min=0))

        # Variables
        self.add_variable(Variable("T_s", "°C"))
        self.add_variable(Variable("q_cd", "W/m²"))
        self.add_variable(Variable("p", "W/m²"))

    def building(self):
        return self.parameter("space").component.building()

    def check(self):
        errors = super().check()
        # Test space defined
        if self.parameter("space").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, must define its space.")
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._file_met = self.building().parameter("file_met").component
        self._T_ini = self.building().parameter("initial_temperature").value
        self._calculate_K()

    def pre_iteration(self, time_index, date):
        super().pre_iteration(time_index, date)
        p_0, p_1 = self.parameter("construction").component.get_P(
            time_index, self.variable("T_s0").values, self.variable("T_s1").values, self.variable("q_cd0").values, self.variable("q_cd1").values, self._T_ini)
        self.variable("p").values[time_index] = p_1
        self._F = self.net_area() * (- p_1 - self._k_01 *
                                     self._file_met.variable("underground_temperature").values[time_index])

    def _calculate_K(self):
        a_0, a_1, a_01 = self.parameter("construction").component.get_A()
        self._k_1 = self.net_area()*(a_1 - self.parameter("h_cv").value)
        self._k_01 = self.net_area()*a_01
        self._K = self._k_1
