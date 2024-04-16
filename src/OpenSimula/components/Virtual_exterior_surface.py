from OpenSimula.components.Virtual_surface import Virtual_surface
from OpenSimula.Parameters import Parameter_component, Parameter_float_list
from OpenSimula.Variable import Variable


class Virtual_exterior_surface(Virtual_surface):
    def __init__(self, name, project):
        Virtual_surface.__init__(self, name, project)
        # Parameters
        self.parameter("type").value = "Virtual_exterior_surface"
        self.parameter(
            "description").value = "Building virtual exterior surface"
        self.add_parameter(Parameter_component("space", "not_defined"))

        self.H_RD = 5.705  # 4*sigma*(293^3)

        # Variables
        self.add_variable(Variable("T_rm", "°C"))
        self.add_variable(Variable("E_dir0", "W/m²"))
        self.add_variable(Variable("E_dif0", "W/m²"))

    def building(self):
        return self.parameter("space").component.building()

    def space(self):
        return self.parameter("space").component

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

    def pre_iteration(self, time_index, date):
        super().pre_iteration(time_index, date)
        self._calculate_variables_pre_iteration(time_index)

    def _calculate_variables_pre_iteration(self, time_i):
        self._T_ext = self._file_met.variable("temperature").values[time_i]
        hor_sol_dif = self._file_met.variable("sol_diffuse").values[time_i]
        hor_sol_dir = self._file_met.variable("sol_direct").values[time_i]
        T_sky = self._file_met.variable("sky_temperature").values[time_i]
        E_dif0 = self._F_sky * hor_sol_dif + \
            (1-self._F_sky)*self._albedo*(hor_sol_dif+hor_sol_dir)
        self.variable("E_dif0").values[time_i] = E_dif0
        E_dir0 = self._file_met.solar_direct_rad(time_i, self.orientation_angle(
            "azimuth", 0),  self.orientation_angle("altitude", 0))
        self.variable("E_dir0").values[time_i] = E_dir0
        T_rm = self._F_sky * T_sky + (1-self._F_sky)*self._T_ext
        self.variable("T_rm").values[time_i] = T_rm
