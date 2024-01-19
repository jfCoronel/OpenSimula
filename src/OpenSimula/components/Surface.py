from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_component, Parameter_float, Parameter_options, Parameter_boolean
from OpenSimula.Variable import Variable


class Surface(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        # Parameters
        self.parameter("type").value = "Surface"
        self.parameter("description").value = "Building surface"
        self.add_parameter(Parameter_boolean("virtual", False))
        self.add_parameter(Parameter_options("location", "EXTERNAL", [
                           "EXTERIOR", "INTERIOR", "UNDERGROUND", "ADIABATIC"]))
        self.add_parameter(Parameter_component("construction", "not_defined"))
        self.add_parameter(Parameter_component("space", "not_defined"))
        self.add_parameter(Parameter_component(
            "adjacent_space", "not_defined"))
        self.add_parameter(Parameter_float("area", 1, "m²", min=0.0))
        self.add_parameter(Parameter_float(
            "azimuth", 0, "°", min=-180, max=180))  # S: 0º, E: 90º, W: -90º, N: 180º
        self.add_parameter(Parameter_float(
            "altitude", 0, "°", min=-90, max=90))  # vertical: 0º, facing up: 90º, facing down: -90º

        # Variables
        self.add_variable(Variable("T_s1", "°C"))
        self.add_variable(Variable("T_s2", "°C"))
        self.add_variable(Variable("T_rm", "°C"))
        self.add_variable(Variable("solar_direct_rad", "W/m²"))
        self.add_variable(Variable("solar_diffuse_rad", "W/m²"))

    def building(self):
        return self.parameter("space").component.building()

    def check(self):
        errors = super().check()
        # Test space defined
        if self.parameter("space").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, must define its space.")
        # Test construction defined
        if (not self.parameter("virtual").value) and self.parameter("construction").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, non virtual surfaces must define its construction."
            )
        # Test interior sufaces include adjacent spaces
        if self.parameter("location").value == "INTERIOR" and self.parameter("adjacent_space").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, interior surfaces must define adjacent space"
            )
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._file_met = self.building().parameter("file_met").component
        self._albedo = self.building().parameter("albedo").value
        self._F_sky = 0.5 + 0.5/90 * self.parameter("altitude").value
        self._create_openings_list()

    def pre_iteration(self, time_index, date):
        super().pre_iteration(time_index, date)
        self._T_ext = self._file_met.variable("temperature").values[time_index]
        if (self.parameter("location").value == "EXTERIOR"):
            hor_sol_dif = self._file_met.variable(
                "sol_diffuse").values[time_index]
            hor_sol_dir = self._file_met.variable(
                "sol_direct").values[time_index]
            T_sky = self._file_met.variable(
                "sky_temperature").values[time_index]
            self.variable("solar_diffuse_rad").values[time_index] = self._F_sky * hor_sol_dif + (
                1-self._F_sky)*self._albedo*(hor_sol_dif+hor_sol_dir)
            self.variable("solar_direct_rad").values[time_index] = self._file_met.solar_direct_rad(
                time_index, self.parameter("azimuth").value, self.parameter("altitude").value)
            self.variable(
                "T_rm").values[time_index] = self._F_sky * T_sky + (1-self._F_sky)*self._T_ext

    def _create_openings_list(self):
        project_openings_list = self.project().component_list(type="Opening")
        self._openings = []
        for opening in project_openings_list:
            if opening.parameter("surface").component == self:
                opening_dic = {"comp": opening,
                               "area": opening.area,
                               "virtual": opening.parameter("virtual").value
                               }
                self._openings.append(opening_dic)

    @property
    def net_area(self):
        area = self.parameter("area").value
        for opening in self._openings:
            area -= opening["area"]
        return area

    def rho_sw(self, face_number=0):
        if (self.parameter("virtual").value):
            return 0
        else:
            if face_number == 0:
                return 1-self.parameter("construction").component.parameter("solar_absortivity").value[0]
            else:
                return 1-self.parameter("construction").component.parameter("solar_absortivity").value[1]

    def tau_sw(self, face_number=0):
        if (self.parameter("virtual").value):
            return 1
        else:
            return 0

    def alpha_sw(self, face_number=0):
        if (self.parameter("virtual").value):
            return 0
        else:
            if face_number == 0:
                return self.parameter("construction").component.parameter("solar_absortivity").value[0]
            else:
                return self.parameter("construction").component.parameter("solar_absortivity").value[1]

    def rho_lw(self, face_number=0):
        if (self.parameter("virtual").value):
            return 0
        else:
            if face_number == 0:
                return 1-self.parameter("construction").component.parameter("lw_absortivity").value[0]
            else:
                return 1-self.parameter("construction").component.parameter("lw_absortivity").value[1]

    def tau_lw(self, face_number=0):
        if (self.parameter("virtual").value):
            return 1
        else:
            return 0

    def alpha_lw(self, face_number=0):
        if (self.parameter("virtual").value):
            return 0
        else:
            if face_number == 0:
                return self.parameter("construction").component.parameter("lw_absortivity").value[0]
            else:
                return self.parameter("construction").component.parameter("lw_absortivity").value[1]
