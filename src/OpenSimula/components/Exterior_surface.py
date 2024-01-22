from OpenSimula.components.Surface import Surface
from OpenSimula.Parameters import Parameter_component, Parameter_float, Parameter_float_list, Parameter_boolean
from OpenSimula.Variable import Variable


class Exterior_surface(Surface):
    def __init__(self, name, project):
        Surface.__init__(self, name, project)
        # Parameters
        self.parameter("type").value = "Exterior_surface"
        self.parameter("description").value = "Building exterior surface"
        self.add_parameter(Parameter_component("space", "not_defined"))
        self.add_parameter(Parameter_float_list(
            "h_cv", [19.3, 2], "W/m²K", min=0))

        self._H_RD = 5.705  # 4*sigma*(293^3)
        # Variables
        self.add_variable(Variable("T_s0", "°C"))
        self.add_variable(Variable("T_s1", "°C"))
        self.add_variable(Variable("T_rm", "°C"))
        self.add_variable(Variable("solar_direct_rad", "W/m²"))
        self.add_variable(Variable("solar_diffuse_rad", "W/m²"))
        self.add_variable(Variable("q_cd0", "W/m²"))
        self.add_variable(Variable("q_cd1", "W/m²"))
        self.add_variable(Variable("p_0", "W/m²"))
        self.add_variable(Variable("p_1", "W/m²"))

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
        self._albedo = self.building().parameter("albedo").value
        self._T_ini = self.building().parameter("initial_temperature").value
        self._F_sky = 0.5 + 0.5/90 * self.parameter("altitude").value
        self._create_openings_list()
        self._calculate_K()

    def pre_iteration(self, time_index, date):
        super().pre_iteration(time_index, date)
        self._T_ext = self._file_met.variable("temperature").values[time_index]
        if (self.parameter("virtual").value):
            pass  # TODO
        else:
            self._calculate_variables_pre(time_index)

    def _create_openings_list(self):
        project_openings_list = self.project().component_list(type="Opening")
        self.openings = []
        for opening in project_openings_list:
            if opening.parameter("surface").component == self:
                self.openings.append(opening)

    def _calculate_K(self):
        if (self.parameter("virtual").value):
            self.K = 1
        else:
            a_0, a_1, a_01 = self.parameter("construction").component.get_A()
            self.k_0 = self.net_area()*(a_0 - self.parameter("h_cv").value[0] -
                                         self._H_RD * self.radiant_property("alpha","long",0))
            self.k_1 = self.net_area()*(a_1 - self.parameter("h_cv").value[1])
            self.k_01 = self.net_area()*a_01
            self.K = self.k_1 - self.k_01 * self.k_01 / self.k_0

    def _calculate_variables_pre(self, time_i):
        p_0, p_1 = self.parameter("construction").component.get_P(
            time_i, self.variable("T_s0").values, self.variable("T_s1").values, self.variable("q_cd0").values, self.variable("q_cd1").values, self._T_ini)
        self.variable("p_0").values[time_i] = p_0
        self.variable("p_1").values[time_i] = p_1
        hor_sol_dif = self._file_met.variable("sol_diffuse").values[time_i]
        hor_sol_dir = self._file_met.variable("sol_direct").values[time_i]
        T_sky = self._file_met.variable("sky_temperature").values[time_i]
        hor_sol_dif_sur = self._F_sky * hor_sol_dif + \
            (1-self._F_sky)*self._albedo*(hor_sol_dif+hor_sol_dir)
        self.variable("solar_diffuse_rad").values[time_i] = hor_sol_dif_sur
        hor_sol_dir_sur = self._file_met.solar_direct_rad(
            time_i, self.parameter("azimuth").value, self.parameter("altitude").value)
        self.variable("solar_direct_rad").values[time_i] = hor_sol_dir_sur
        T_rm = self._F_sky * T_sky + (1-self._F_sky)*self._T_ext
        self.variable("T_rm").values[time_i] = T_rm
        self._f_0 = self.net_area() * (- p_0 - self.parameter("h_cv").value[0] * self._T_ext - self._H_RD *
                                       self.alpha_lw(0) * T_rm - self.alpha_sw(0) * (hor_sol_dif_sur + hor_sol_dir_sur))
        self._F = self.net_area() * (- p_1) - self._k_01/self._k_0 * self._f_0

    @property
    def net_area(self):
        area = self.parameter("area").value
        for opening in self._openings:
            area -= opening["area"]
        return area
