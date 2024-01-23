from OpenSimula.components.Surface import Surface
from OpenSimula.Parameters import Parameter_component, Parameter_component_list, Parameter_float, Parameter_float_list, Parameter_boolean
from OpenSimula.Variable import Variable


class Interior_surface(Surface):
    def __init__(self, name, project):
        Surface.__init__(self, name, project)
        # Parameters
        self.parameter("type").value = "Interior_surface"
        self.parameter("description").value = "Building interior surface"
        self.add_parameter(Parameter_component_list(
            "spaces", ["not_defined", "not_defined"]))
        self.add_parameter(Parameter_float_list(
            "h_cv", [2, 2], "W/m²K", min=0))

        # Variables
        self.add_variable(Variable("T_s0", "°C"))
        self.add_variable(Variable("T_s1", "°C"))
        self.add_variable(Variable("q_cd0", "W/m²"))
        self.add_variable(Variable("q_cd1", "W/m²"))
        self.add_variable(Variable("p_0", "W/m²"))
        self.add_variable(Variable("p_1", "W/m²"))

    def building(self):
        return self.parameter("spaces").component[0].building()

    def check(self):
        errors = super().check()
        # Test space defined
        if self.parameter("spaces").value[0] == "not_defined" or self.parameter("spaces").value[1] == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, must define two spaces.")
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._T_ini = self.building().parameter("initial_temperature").value
        self._calculate_K()

    def pre_iteration(self, time_index, date):
        super().pre_iteration(time_index, date)
        self._T_ext = self._file_met.variable("temperature").values[time_index]
        """
        if (self.parameter("virtual").value):
            pass  # TODO
        else:
            p_0, p_1 = self.parameter("construction").component.get_P(
                time_index, self.variable("T_s0").values, self.variable("T_s1").values, self.variable("q_cd0").values, self.variable("q_cd1").values, self._T_ini)
            self.variable("p_0").values[time_index] = p_0
            self.variable("p_1").values[time_index] = p_1
            self._f_0 = self.net_area * (- p_0)
            self._f_1 = self.net_area * (- p_1)
        """

    def _calculate_K(self):
        if (self.parameter("virtual").value):
            self.k = [1, 1]
        else:
            a_0, a_1, a_01 = self.parameter("construction").component.get_A()
            self.k = [self.net_area * (a_0 - self.parameter("h_cv").value[0]),
                      self.net_area * (a_1 - self.parameter("h_cv").value[1])]
            self.k_01 = self.net_area * a_01
