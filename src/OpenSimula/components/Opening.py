from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_component, Parameter_float, Parameter_float_list
from OpenSimula.Variable import Variable


class Opening(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        # Parameters
        self.parameter("type").value = "Opening"
        self.parameter(
            "description").value = "Rectangular opening in building surfaces"
        self.add_parameter(Parameter_component("surface", "not_defined"))
        self.add_parameter(Parameter_component("opening_type", "not_defined"))
        self.add_parameter(Parameter_float("width", 1, "m", min=0.0))
        self.add_parameter(Parameter_float("height", 1, "m", min=0.0))
        self.add_parameter(Parameter_float_list(
            "h_cv", [19.3, 2], "W/m²K", min=0))

        self.H_RD = 5.705  # 4*sigma*(293^3)
        # Variables
        self.add_variable(Variable("T_s0", "°C"))
        self.add_variable(Variable("T_s1", "°C"))
        self.add_variable(Variable("T_rm", "°C"))
        self.add_variable(Variable("E_dir0", "W/m²"))
        self.add_variable(Variable("E_dif0", "W/m²"))
        self.add_variable(Variable("q_sol_dir_trans", "W/m²"))
        self.add_variable(Variable("q_sol_01", "W/m²"))
        self.add_variable(Variable("q_sol_10", "W/m²"))
        self.add_variable(Variable("q_cv0", "W/m²"))
        self.add_variable(Variable("q_cv1", "W/m²"))
        self.add_variable(Variable("q_cd", "W/m²"))
        self.add_variable(Variable("q_sol0", "W/m²"))
        self.add_variable(Variable("q_sol1", "W/m²"))
        self.add_variable(Variable("q_swig0", "W/m²"))
        self.add_variable(Variable("q_swig1", "W/m²"))
        self.add_variable(Variable("q_lwig0", "W/m²"))
        self.add_variable(Variable("q_lwig1", "W/m²"))
        self.add_variable(Variable("q_lwt0", "W/m²"))
        self.add_variable(Variable("q_lwt1", "W/m²"))

    def check(self):
        errors = super().check()
        # Test surface
        if self.parameter("surface").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, its surface must be defined.")
        # Test opening_type defined
        if self.parameter("opening_type").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, opening must define its Opening_type."
            )
        return errors

    def building(self):
        return self.parameter("surface").component.building()

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._file_met = self.building().parameter("file_met").component
        self._calculate_K()

    def _calculate_K(self):
        self.k = [0, 0]
        self.k[0] = self.area * (- self.parameter("h_cv").value[0] - self.H_RD * self.radiant_property(
            "alpha", "long_wave", 0) - 1/self.parameter("opening_type").component.thermal_resistance())
        self.k[1] = self.area * (-1/self.parameter(
            "opening_type").component.thermal_resistance() - self.parameter("h_cv").value[1])
        self.k_01 = self.area / \
            self.parameter("opening_type").component.thermal_resistance()

    def pre_iteration(self, time_index, date):
        super().pre_iteration(time_index, date)
        self._calculate_variables_pre_iteration(time_index)

    def _calculate_variables_pre_iteration(self, time_i):
        self._T_ext = self._file_met.variable("temperature").values[time_i]
        surface = self.parameter("surface").component
        self.variable("E_dif0").values[time_i] = surface.variable(
            "E_dif0").values[time_i]
        self.variable("E_dir0").values[time_i] = surface.variable(
            "E_dir0").values[time_i]
        self.variable("T_rm").values[time_i] = surface.variable(
            "T_rm").values[time_i]
        theta = self._file_met.solar_surface_angle(time_i, surface.parameter(
            "azimuth").value, surface.parameter("altitude").value)
        q_sol = self.radiant_property(
            "alpha", "solar_diffuse", 0) * self.variable("E_dif0").values[time_i]
        q_sol_01 = self.radiant_property(
            "alpha_other_side", "solar_diffuse", 0, theta) * self.variable("E_dif0").values[time_i]
        if theta is not None:
            self.variable("q_sol_dir_trans").values[time_i] = self.variable(
                "E_dir0").values[time_i]*self.radiant_property("tau", "solar_direct", 0, theta)
            q_sol += self.radiant_property("alpha", "solar_direct",
                                           0, theta) * self.variable("E_dir0").values[time_i]
            q_sol_01 += self.radiant_property("alpha_other_side", "solar_direct",
                                              0, theta) * self.variable("E_dir0").values[time_i]
            self.variable("q_sol_01").values[time_i] = q_sol_01
            self.variable("q_sol0").values[time_i] = q_sol
        else:
            self.variable("q_sol_dir_trans").values[time_i] = 0
            self.variable("q_sol_01").values[time_i] = 0
        h_rd = self.H_RD * self.radiant_property("alpha", "long_wave", 0)
        T_rm = self.variable("T_rm").values[time_i]
        self.f_0 = self.area * \
            (- self.parameter("h_cv").value[0]
             * self._T_ext - h_rd * T_rm - q_sol)

    def post_iteration(self, time_index, date):
        super().post_iteration(time_index, date)
        self._calculate_T_s0(time_index)
        self._calculate_heat_fluxes(time_index)

    def _calculate_T_s0(self, time_i):
        T_s0 = (self.f_0 - (self.variable("q_sol_10").values[time_i] + self.variable("q_swig0").values[time_i])*self.area - self.k_01 *
                self.variable("T_s1").values[time_i])/self.k[0]
        self.variable("T_s0").values[time_i] = T_s0

    def _calculate_heat_fluxes(self, time_i):
        q_cd0 = (self.variable("T_s1").values[time_i] - self.variable(
            "T_s0").values[time_i]) / self.parameter("opening_type").component.thermal_resistance()
        self.variable("q_cd").values[time_i] = q_cd0
        self.variable("q_cv0").values[time_i] = self.parameter(
            "h_cv").value[0] * (self._T_ext - self.variable("T_s0").values[time_i])
        T_z = self.parameter("surface").component.parameter(
            "space").component.variable("temperature").values[time_i]
        self.variable("q_cv1").values[time_i] = self.parameter(
            "h_cv").value[1] * (T_z - self.variable("T_s1").values[time_i])
        h_rd = self.H_RD * self.radiant_property("alpha", "long_wave", 0)
        self.variable("q_lwt0").values[time_i] = h_rd * (self.variable(
            "T_rm").values[time_i] - self.variable("T_s0").values[time_i])

        self.variable("q_lwt1").values[time_i] = self.variable("q_cd").values[time_i] - self.variable("q_cv1").values[time_i] - \
            self.variable("q_sol1").values[time_i] - self.variable("q_sol_01").values[time_i] - self.variable(
            "q_swig1").values[time_i] - self.variable("q_lwig1").values[time_i]

    @property
    def area(self):
        return self.parameter("width").value * self.parameter("height").value

    def radiant_property(self, prop, radiation_type, side, theta=0):
        return self.parameter("opening_type").component.radiant_property(prop, radiation_type, side, theta)

    def orientation_angle(self, angle, side):
        return self.parameter("surface").component.orientation_angle(angle, side)

    def is_virtual(self):
        return False
