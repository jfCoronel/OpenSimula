import math
from opensimula.Component import Component
from opensimula.Message import Message
from opensimula.Parameters import (
    Parameter_component,
    Parameter_float,
    Parameter_float_list,
    Parameter_options,
)
from opensimula.Variable import Variable
from shapely.geometry import Polygon
from opensimula.visual_3D.Polygon_3D import Polygon_3D


class Opening(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        # Parameters
        self.parameter("type").value = "Opening"
        self.parameter("description").value = (
            "Openings (windows/doors) in building surfaces"
        )
        self.add_parameter(
            Parameter_component("surface", "not_defined", ["Building_surface"])
        )
        self.add_parameter(
            Parameter_component("opening_type", "not_defined", ["Opening_type"])
        )
        self.add_parameter(
            Parameter_options("shape", "RECTANGLE", ["RECTANGLE", "POLYGON"])
        )
        self.add_parameter(Parameter_float_list("ref_point", [0, 0], "m"))
        self.add_parameter(Parameter_float("width", 1, "m", min=0.0))
        self.add_parameter(Parameter_float("height", 1, "m", min=0.0))
        self.add_parameter(
            Parameter_float_list("x_polygon", [0, 10, 10, 0], "m", min=float("-inf"))
        )
        self.add_parameter(
            Parameter_float_list("y_polygon", [0, 0, 10, 10], "m", min=float("-inf"))
        )
        self.add_parameter(
            Parameter_float("setback", 0, "m", min=0.0)
        )  # Only for rectangular openings
        self.add_parameter(Parameter_float_list("h_cv", [19.3, 2], "W/m²K", min=0))

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
            msg = f"{self.parameter('name').value}, its surface must be defined."
            errors.append(Message(msg, "ERROR"))
        # TODO: Test surface_type EXTERIOR or INTERIOR
        # Test opening_type defined
        if self.parameter("opening_type").value == "not_defined":
            msg = (
                f"{self.parameter('name').value}, opening must define its Opening_type."
            )
            errors.append(Message(msg, "ERROR"))
        # Test if Polygon shape that x_polygon and y_polygon has the same size
        if self.parameter("shape").value == "POLYGON":
            if len(self.parameter("x_polygon").value) != len(
                self.parameter("y_polygon").value
            ):
                msg = f"{self.parameter('name').value}, x_polygo and y_polygon must have the same size."
                errors.append(Message(msg, "ERROR"))
        return errors

    def get_building(self):
        return self.get_surface().get_building()

    def get_space(self, side=0):
        return self.get_surface().get_space(side)

    def get_surface(self):
        return self.parameter("surface").component
    
    def is_exterior(self):
        return (self.get_surface().parameter("surface_type").value == "EXTERIOR")

    # _______ pre_simulation _______
    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._file_met = self.project().parameter("simulation_file_met").component
        self._calculate_K_()
        self.f_dif_setback = self._f_diffuse_setback_()
        if self.is_exterior():
            self._sunny_index = self.project().env_3D.get_sunny_index(
                self.parameter("name").value
            )
        else:
            self._sunny_index = None

    def _calculate_K_(self):
        self.k = [0, 0]
        self.k[0] = self.area * (
            -self.parameter("h_cv").value[0]
            - self.H_RD * self.radiant_property("alpha", "long_wave", 0)
            - 1 / self.parameter("opening_type").component.thermal_resistance()
        )
        self.k[1] = self.area * (
            -1 / self.parameter("opening_type").component.thermal_resistance()
            - self.parameter("h_cv").value[1]
        )
        self.k_01 = (
            self.area / self.parameter("opening_type").component.thermal_resistance()
        )

    def _f_diffuse_setback_(self):
        if (
            self.parameter("shape").value == "POLYGON"
            or self.parameter("setback").value == 0
        ):
            return 1
        else:
            X = self.parameter("width").value / self.parameter("setback").value
            Y = self.parameter("height").value / self.parameter("setback").value
            F = (
                2
                / (math.pi * X * Y)
                * (
                    math.log(((1 + X**2) * (1 + Y**2) / (1 + X**2 + Y**2)) ** 0.5)
                    + X * ((1 + Y**2) ** 0.5) * math.atan(X / ((1 + Y**2) ** 0.5))
                    + Y * ((1 + X**2)) ** 0.5 * math.atan(Y / ((1 + X**2)) ** 0.5)
                    - X * math.atan(X)
                    - Y * math.atan(Y)
                )
            )
            return 1 - F

    # _______ pre_iteration _______
    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        if self.is_exterior():
            self._calculate_exterior_variables_pre_iteration_(time_index)

    def _calculate_exterior_variables_pre_iteration_(self, time_i):
        self._T_ext = self._file_met.variable("temperature").values[time_i]
        # Solar radiation from the surface where the opening is located
        surface = self.get_surface()
        # Diffuse solar radiation
        E_dif_sunny = surface.variable("E_dif_sunny").values[time_i]
        self.variable("E_dif_sunny").values[time_i] = E_dif_sunny
        diffuse_sunny_fraction = self.project().env_3D.get_diffuse_sunny_fraction(
            self._sunny_index
        )
        E_dif = E_dif_sunny * diffuse_sunny_fraction
        self.variable("E_dif").values[time_i] = E_dif

        # Direct solar radiation
        E_dir_sunny = surface.variable("E_dir_sunny").values[time_i]
        self.variable("E_dir_sunny").values[time_i] = E_dir_sunny
        # Setback shadow
        theta = self._file_met.solar_surface_angle(
            time_i,
            surface.orientation_angle("azimuth", 0),
            surface.orientation_angle("altitude", 0),
        )
        self.variable("theta_sun").values[time_i] = theta
        if (
            theta is not None
            and self.parameter("shape").value == "RECTANGLE"
            and self.parameter("setback").value > 0
        ):
            f_setback = self._f_setback_(
                time_i,
                surface.orientation_angle("azimuth", 0),
                surface.orientation_angle("altitude", 0),
            )
        else:
            f_setback = 1
        E_dir = E_dir_sunny * self._calculate_direct_sunny_fraction_(time_i) * f_setback
        self.variable("E_dir").values[time_i] = E_dir

        q_sol0 = self.radiant_property("alpha", "solar_diffuse", 0) * E_dif
        q_sol1 = self.radiant_property("alpha_other_side", "solar_diffuse", 0) * E_dif
        E_dif_tra = self.radiant_property("tau", "solar_diffuse", 0) * E_dif
        if theta is not None:
            q_sol0 += self.radiant_property("alpha", "solar_direct", 0, theta) * E_dir
            q_sol1 += (
                self.radiant_property("alpha_other_side", "solar_direct", 0, theta)
                * E_dir
            )
            E_dir_tra = self.radiant_property("tau", "solar_direct", 0, theta) * E_dir
        else:
            E_dir_tra = 0

        self.variable("q_sol0").values[time_i] = q_sol0
        self.variable("q_sol1").values[time_i] = q_sol1
        self.variable("E_dif_tra").values[time_i] = E_dif_tra
        self.variable("E_dir_tra").values[time_i] = E_dir_tra

        T_rm = surface.variable("T_rm").values[time_i]
        self.variable("T_rm").values[time_i] = T_rm
        h_rd = self.H_RD * self.radiant_property("alpha", "long_wave", 0)
        self.f_0 = self.area * (
            -self.parameter("h_cv").value[0] * self._T_ext - h_rd * T_rm
        )
        # q_sol0 will be corrected by the building

    def _calculate_direct_sunny_fraction_(self, time_i):
        if self.project().parameter("shadow_calculation").value == "INSTANT":
            direct_sunny_fraction = self.project().env_3D.get_direct_sunny_fraction(
                self._sunny_index
            )
        elif self.project().parameter("shadow_calculation").value == "INTERPOLATION":
            azi = self._file_met.variable("sol_azimuth").values[time_i]
            alt = self._file_met.variable("sol_altitude").values[time_i]
            if not math.isnan(alt):
                direct_sunny_fraction = (
                    self.project().env_3D.get_direct_interpolated_sunny_fraction(
                        self._sunny_index, azi, alt
                    )
                )
            else:
                direct_sunny_fraction = 1
        elif self.project().parameter("shadow_calculation").value == "NO":
            direct_sunny_fraction = 1
        return direct_sunny_fraction

    def _f_setback_(self, time_i, azimuth_sur, altitude_sur):
        theta_h = math.fabs(
            self._file_met.variable("sol_azimuth").values[time_i] - azimuth_sur
        )
        f_shadow_h = (
            self.parameter("setback").value
            * math.tan(math.radians(theta_h))
            / self.parameter("width").value
        )
        if f_shadow_h > 1:
            f_shadow_h = 1
        theta_v = math.fabs(
            self._file_met.variable("sol_altitude").values[time_i] - altitude_sur
        )
        f_shadow_v = (
            self.parameter("setback").value
            * math.tan(math.radians(theta_v))
            / self.parameter("height").value
        )
        if f_shadow_v > 1:
            f_shadow_v = 1
        return (1 - f_shadow_h) * (1 - f_shadow_v)

    # _______ post_iteration _______
    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        if self.is_exterior():
            self._calculate_T_s0_(time_index)
        self._calculate_heat_fluxes_(time_index)

    def _calculate_T_s0_(self, time_i):
        T_s0 = (
            self.f_0
            - (
                self.variable("q_sol0").values[time_i]
                + self.variable("q_swig0").values[time_i]
            )
            * self.area
            - self.k_01 * self.variable("T_s1").values[time_i]
        ) / self.k[0]
        self.variable("T_s0").values[time_i] = T_s0

    def _calculate_heat_fluxes_(self, time_i):
        q_cd0 = (
            self.variable("T_s1").values[time_i] - self.variable("T_s0").values[time_i]
        ) / self.parameter("opening_type").component.thermal_resistance()
        self.variable("q_cd").values[time_i] = q_cd0
        if self.is_exterior():
            self.variable("q_cv0").values[time_i] = self.parameter("h_cv").value[0] * (
                self._T_ext - self.variable("T_s0").values[time_i]
            )
            T_z = self.get_surface().get_space().variable("temperature").values[time_i]
            self.variable("q_cv1").values[time_i] = self.parameter("h_cv").value[1] * (
                T_z - self.variable("T_s1").values[time_i]
            )
            h_rd = self.H_RD * self.radiant_property("alpha", "long_wave", 0)
            self.variable("q_lwt0").values[time_i] = h_rd * (
                self.variable("T_rm").values[time_i]
                - self.variable("T_s0").values[time_i]
            )
            self.variable("q_lwt1").values[time_i] = (
                +self.variable("q_cd").values[time_i]
                - self.variable("q_cv1").values[time_i]
                - self.variable("q_sol1").values[time_i]
                - self.variable("q_swig1").values[time_i]
                - self.variable("q_lwig1").values[time_i]
            )
        else:  # interior
            self.variable("q_cv0").values[time_i] = self.parameter("h_cv").value[0] * (
                self.get_space(0).variable("temperature").values[time_i]
                - self.variable("T_s0").values[time_i]
            )
            self.variable("q_cv1").values[time_i] = self.parameter("h_cv").value[1] * (
                self.get_space(1).variable("temperature").values[time_i]
                - self.variable("T_s1").values[time_i]
            )
            self.variable("q_lwt0").values[time_i] = (
                -self.variable("q_cd").values[time_i]
                - self.variable("q_cv0").values[time_i]
                - self.variable("q_sol0").values[time_i]
                - self.variable("q_swig0").values[time_i]
                - self.variable("q_lwig0").values[time_i]
            )
            self.variable("q_lwt1").values[time_i] = (
                + self.variable("q_cd").values[time_i]
                - self.variable("q_cv1").values[time_i]
                - self.variable("q_sol1").values[time_i]
                - self.variable("q_swig1").values[time_i]
                - self.variable("q_lwig1").values[time_i]
            )

    @property
    def area(self):
        if self.parameter("shape").value == "RECTANGLE":
            return self.parameter("width").value * self.parameter("height").value
        elif self.parameter("shape").value == "POLYGON":
            polygon = []
            n = len(self.parameter("x_polygon").value)
            for i in range(0, n):
                polygon.append(
                    [
                        self.parameter("x_polygon").value[i],
                        self.parameter("y_polygon").value[i],
                    ]
                )
            return Polygon(polygon).area

    def radiant_property(self, prop, radiation_type, side, theta=0):
        return self.parameter("opening_type").component.radiant_property(
            prop, radiation_type, side, theta
        )

    def orientation_angle(self, angle, side, coordinate_system="global"):
        return self.get_surface().orientation_angle(angle, side, coordinate_system)

    def get_origin(self, coordinate_system="global"):
        return self.get_surface().get_origin(coordinate_system)

    def get_polygon_2D(self):  # Get polygon_2D
        ref = self.parameter("ref_point").value
        if self.parameter("shape").value == "RECTANGLE":
            w = self.parameter("width").value
            h = self.parameter("height").value
            return [
                [ref[0], ref[1]],
                [ref[0] + w, ref[1]],
                [ref[0] + w, ref[1] + h],
                [ref[0], ref[1] + h],
            ]
        elif self.parameter("shape").value == "POLYGON":
            polygon2D = []
            n = len(self.parameter("x_polygon").value)
            for i in range(0, n):
                polygon2D.append(
                    [
                        self.parameter("x_polygon").value[i] + ref[0],
                        self.parameter("y_polygon").value[i] + ref[1],
                    ]
                )
            return polygon2D

    def get_polygon_3D(self):
        azimuth = self.orientation_angle("azimuth", 0, "global")
        altitude = self.orientation_angle("altitude", 0, "global")
        origin = self.get_origin("global")
        pol_2D = self.get_polygon_2D()
        name = self.parameter("name").value
        if self.is_exterior():
            return Polygon_3D(
                name, origin, azimuth, altitude, pol_2D, color="blue", opacity=0.6
            )
        else:
            return Polygon_3D(
                name,
                origin,
                azimuth,
                altitude,
                pol_2D,
                color="blue",
                opacity=0.6,
                shading=False,
                calculate_shadows=False,
            )
