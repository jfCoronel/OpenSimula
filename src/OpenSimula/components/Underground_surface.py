from OpenSimula.components.Surface import Surface
from OpenSimula.Parameters import Parameter_component, Parameter_float
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

    def building(self):
        return self.parameter("space").component.building()

    def check(self):
        errors = super().check()
        # Test space defined
        if self.parameter("space").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, must define its space.")
         # Test virtual
        if self.parameter("virtual").value == True and (self.parameter("h_cv").value != 0):
            self.parameter("h_cv").value = 0
            errors.append(
                f"Warning : h_cv set to 0 for virtual surfaces.")
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._file_met = self.building().parameter("file_met").component
        self._T_ini = self.building().parameter("initial_temperature").value
        self._calculate_K()

    def pre_iteration(self, time_index, date):
        super().pre_iteration(time_index, date)
        self._calculate_variables_pre_iteration(time_index)

    def post_iteration(self, time_index, date):
        super().post_iteration(time_index, date)
        self._calculate_heat_fluxes(time_index)

    def _calculate_heat_fluxes(self, time_i):
        if (not self.parameter("virtual").value):
            self.variable("q_cd0").values[time_i] = self.a_0 * self.variable("T_s0").values[time_i] + \
                self.a_01 * \
                self.variable("T_s1").values[time_i] + \
                self.variable("p_0").values[time_i]
            self.variable("q_cd1").values[time_i] = self.a_01 * self.variable("T_s0").values[time_i] + \
                self.a_1 * \
                self.variable("T_s1").values[time_i] + \
                self.variable("p_1").values[time_i]

            self.variable("q_cv0").values[time_i] = - \
                self.variable("q_cd0").values[time_i]
            self.variable("q_cv1").values[time_i] = self.parameter("h_cv").value * (self.parameter(
                "space").component.variable("temperature").values[time_i] - self.variable("T_s1").values[time_i])
            self.variable("q_lwt1").values[time_i] = - self.variable("q_cd1").values[time_i] - self.variable("q_cv1").values[time_i] - \
                self.variable("q_sol1").values[time_i] - self.variable(
                    "q_swig1").values[time_i] - self.variable("q_lwig1").values[time_i]

    def _calculate_K(self):
        if (self.parameter("virtual").value):
            self.k = [1.0, 2.0]
            self.k_01 = -1
        else:
            self.a_0, self.a_1, self.a_01 = self.parameter(
                "construction").component.get_A()
            self.k[0] = 1  # not used
            self.k[1] = self.area * (self.a_1 - self.parameter("h_cv").value)
            self.k_01 = self.area * self.a_01

    def _calculate_variables_pre_iteration(self, time_i):
        self.variable("T_s0").values[time_i] = self._file_met.variable(
            "underground_temperature").values[time_i]
        if (self.parameter("virtual").value == False):
            p_0, p_1 = self.parameter("construction").component.get_P(
                time_i, self.variable("T_s0").values, self.variable("T_s1").values, self.variable("q_cd0").values, self.variable("q_cd1").values, self._T_ini)
            self.variable("p_0").values[time_i] = p_0
            self.variable("p_1").values[time_i] = p_1
