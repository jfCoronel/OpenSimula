import math
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
        self.add_parameter(Parameter_component(
            "surface", "not_defined", ["Exterior_surface"]))
        self.add_parameter(Parameter_component(
            "opening_type", "not_defined", ["Opening_type"]))
        self.add_parameter(Parameter_float_list("ref_point", [0, 0], "m"))
        self.add_parameter(Parameter_float("width", 1, "m", min=0.0))
        self.add_parameter(Parameter_float("height", 1, "m", min=0.0))
        self.add_parameter(Parameter_float("setback", 0, "m", min=0.0))
        self.add_parameter(Parameter_float_list(
            "h_cv", [19.3, 2], "W/m²K", min=0))

        self.H_RD = 5.705  # 4*sigma*(293^3)
        # Variables
        self.add_variable(Variable("T_s0", "°C"))
        self.add_variable(Variable("T_s1", "°C"))
        self.add_variable(Variable("T_rm", "°C"))
        self.add_variable(Variable("E_dir_sunny", "W/m²"))
        self.add_variable(Variable("E_dir", "W/m²"))
        self.add_variable(Variable("E_dif_sunny", "W/m²"))
        self.add_variable(Variable("E_dif", "W/m²"))
        self.add_variable(Variable("E_dir_tra", "W/m²"))
        self.add_variable(Variable("E_dif_tra", "W/m²"))
        self.add_variable(Variable("theta_sun", "°"))
        self.add_variable(Variable("E_ref", "W/m²"))
        self.add_variable(Variable("E_ref_tra", "W/m²"))
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
        self.add_variable(Variable("debug_f", ""))

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

    def space(self):
        return self.parameter("surface").component.space()

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._file_met = self.building().parameter("file_met").component
        self._calculate_K()
        self.f_dif_setback = self._f_diffuse_setback()

    def _calculate_K(self):
        self.k = [0, 0]
        self.k[0] = self.area * (- self.parameter("h_cv").value[0] - self.H_RD * self.radiant_property(
            "alpha", "long_wave", 0) - 1/self.parameter("opening_type").component.thermal_resistance())
        self.k[1] = self.area * (-1/self.parameter(
            "opening_type").component.thermal_resistance() - self.parameter("h_cv").value[1])
        self.k_01 = self.area / \
            self.parameter("opening_type").component.thermal_resistance()

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        self._shadow_calculated = False
        self._calculate_variables_pre_iteration(time_index)

    def _calculate_variables_pre_iteration(self, time_i):
        self._T_ext = self._file_met.variable("temperature").values[time_i]
        surface = self.parameter("surface").component
        E_dif_sunny = surface.variable("E_dif_sunny").values[time_i]
        self.variable("E_dif_sunny").values[time_i] = E_dif_sunny
        diffuse_sunny_fracion = self.building().get_diffuse_sunny_fraction(self)
        E_dif = E_dif_sunny * diffuse_sunny_fracion * self.f_dif_setback
        self.variable("E_dif").values[time_i] = E_dif
        self.variable("T_rm").values[time_i] = surface.variable(
            "T_rm").values[time_i]
        theta = self._file_met.solar_surface_angle(time_i, surface.orientation_angle(
            "azimuth", 0), surface.orientation_angle("altitude", 0))
        self.variable("theta_sun").values[time_i] = theta
        # Setback shadow
        if (theta is not None and self.parameter("setback").value > 0):
            f_setback = self._f_setback_(time_i, surface.orientation_angle(
                "azimuth", 0), surface.orientation_angle(
                "altitude", 0))
        else:
            f_setback = 1
        E_dir_sunny = surface.variable("E_dir_sunny").values[time_i]
        self.variable("E_dir_sunny").values[time_i] = E_dir_sunny
        self.variable("E_dir").values[time_i] = E_dir_sunny * f_setback
        self.variable("q_sol0").values[time_i] = self.radiant_property(
            "alpha", "solar_diffuse", 0) * E_dif
        self.variable("q_sol1").values[time_i] = self.radiant_property(
            "alpha_other_side", "solar_diffuse", 0) * E_dif
        self.variable("E_dif_tra").values[time_i] = self.radiant_property(
            "tau", "solar_diffuse", 0)*E_dif

        h_rd = self.H_RD * self.radiant_property("alpha", "long_wave", 0)
        T_rm = self.variable("T_rm").values[time_i]
        self.f_0 = self.area * \
            (- self.parameter("h_cv").value[0] * self._T_ext - h_rd * T_rm)
        # q_sol0 will be added by the building

    def iteration(self, time_index, date, daylight_saving):
        super().iteration(time_index, date, daylight_saving)
        # Calculate shadows only once
        if not self._shadow_calculated:
            sunny_fracion = self.building().get_direct_sunny_fraction(self)
            E_dir = self.variable("E_dir").values[time_index] * sunny_fracion
            theta = self.variable("theta_sun").values[time_index]
            self.variable("E_dir").values[time_index] = E_dir
            if E_dir > 0:
                self.variable("E_dir_tra").values[time_index] = E_dir * \
                    self.radiant_property("tau", "solar_direct", 0, theta)
                self.variable("q_sol0").values[time_index] += self.radiant_property(
                    "alpha", "solar_direct", 0, theta) * E_dir
                self.variable("q_sol1").values[time_index] += self.radiant_property(
                    "alpha_other_side", "solar_direct", 0, theta) * E_dir
            else:
                self.variable("E_dir_tra").values[time_index] = 0
            self._shadow_calculated = True
        return True

    def _f_setback_(self, time_i, azimuth_sur, altitude_sur):
        theta_h = math.fabs(self._file_met.variable(
            "sol_azimuth").values[time_i] - azimuth_sur)
        f_shadow_h = self.parameter(
            "setback").value*math.tan(math.radians(theta_h)) / self.parameter("width").value
        if f_shadow_h > 1:
            f_shadow_h = 1
        theta_v = math.fabs(self._file_met.variable(
            "sol_altitude").values[time_i] - altitude_sur)
        f_shadow_v = self.parameter(
            "setback").value*math.tan(math.radians(theta_v))/self.parameter("height").value
        if f_shadow_v > 1:
            f_shadow_v = 1
        return (1-f_shadow_h)*(1-f_shadow_v)

    def _f_diffuse_setback(self):
        if (self.parameter("setback").value == 0):
            return 1
        else:
            X = self.parameter("width").value/self.parameter("setback").value
            Y = self.parameter("height").value/self.parameter("setback").value
            F = 2/(math.pi*X*Y)*(math.log(((1+X**2)*(1+Y**2)/(1+X**2+Y**2))**0.5) + X*((1+Y**2)**0.5) * math.atan(
                X/((1+Y**2)**0.5)) + Y*((1+X**2))**0.5 * math.atan(Y/((1+X**2))**0.5) - X*math.atan(X)-Y*math.atan(Y))
            return (1-F)

    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        self._calculate_T_s0(time_index)
        self._calculate_heat_fluxes(time_index)

    def _calculate_T_s0(self, time_i):
        T_s0 = (self.f_0 - (self.variable("q_sol0").values[time_i] + self.variable("q_swig0").values[time_i])*self.area - self.k_01 *
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

        self.variable("q_lwt1").values[time_i] = + self.variable("q_cd").values[time_i] - self.variable("q_cv1").values[time_i] - \
            self.variable("q_sol1").values[time_i] - self.variable(
            "q_swig1").values[time_i] - self.variable("q_lwig1").values[time_i]

    @property
    def area(self):
        return self.parameter("width").value * self.parameter("height").value

    def radiant_property(self, prop, radiation_type, side, theta=0):
        return self.parameter("opening_type").component.radiant_property(prop, radiation_type, side, theta)

    def orientation_angle(self, angle, side, coordinate_system="global"):
        return self.parameter("surface").component.orientation_angle(angle, side, coordinate_system)

    def get_angle_with_normal(self, sol_azimuth, sol_altitude):
        return self.parameter("surface").component.get_angle_with_normal(sol_azimuth, sol_altitude)

    def is_virtual(self):
        return False

    def get_origin(self, coordinate_system="global"):
        sur_component = self.parameter("surface").component
        return sur_component.get_origin(coordinate_system)

    def get_polygon_2D(self):  # Get polygon_2D
        ref = self.parameter("ref_point").value
        w = self.parameter("width").value
        h = self.parameter("height").value
        return [[ref[0], ref[1]], [ref[0]+w, ref[1]],
                [ref[0]+w, ref[1]+h], [ref[0], ref[1]+h]]
