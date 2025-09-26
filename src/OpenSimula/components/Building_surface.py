import math
from OpenSimula.Message import Message
from OpenSimula.components.Surface import Surface
from OpenSimula.Parameters import Parameter_component, Parameter_float_list, Parameter_options, Parameter_component_list
from OpenSimula.Variable import Variable
from OpenSimula.visual_3D.Polygon_3D import Polygon_3D


class Building_surface(Surface):
    def __init__(self, name, project):
        Surface.__init__(self, name, project)
        # Parameters
        self.parameter("type").value = "Building_surface"
        self.parameter("description").value = "Building surface"
        self.add_parameter(Parameter_component("construction", "not_defined", ["Construction"]))
        self.add_parameter(Parameter_component_list("spaces", ["not_defined", "not_defined"], ["Space"]))
        self.add_parameter(Parameter_options("surface_type", "EXTERIOR", ["EXTERIOR", "INTERIOR", "UNDERGROUND"]))
        self.add_parameter(Parameter_float_list("h_cv", [19.3, 2], "W/m²K", min=0))

        # Constants
        self.H_RD = 5.705  # 4*sigma*(293^3)
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
        # For exterior surface
        self.add_variable(Variable("T_rm", "°C"))

        # k values must be calculated by each subclass
        self.k = [1.0, 2.0]
        self.k_01 = -1

    def check(self):
        errors = super().check()
        # Test space defined
        surface_type = self.parameter("surface_type").value
        if surface_type == "EXTERIOR" or surface_type == "UNDERGROUND":
            if self.parameter("spaces").value[0] == "not_defined":
                msg = f"{self.parameter('name').value}, must define its space."
                errors.append(Message(msg, "ERROR"))
        elif surface_type == "INTERIOR":
            if (
                self.parameter("spaces").value[0] == "not_defined"
                or self.parameter("spaces").value[1] == "not_defined"
            ):
                msg = f"{self.parameter('name').value}, must define two spaces."
                errors.append(Message(msg, "ERROR"))
        # Test construction defined
        if self.parameter("construction").value == "not_defined":
            msg = f"{self.parameter('name').value}, Building surfaces must define its construction."
            errors.append(Message(msg, "ERROR"))
        self._create_openings_list_()
        return errors

    def get_building(self):
        return self.parameter("spaces").component[0].get_building()

    def get_space(self,side=0):
        return self.parameter("spaces").component[side]
    
    def radiant_property(self, prop, radiation_type, side, theta=0):
        return self.parameter("construction").component.radiant_property(prop, radiation_type, side, theta)

    # ____________ pre_simulation ____________
    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._file_met = self.project().parameter("simulation_file_met").component
        self._albedo = self.project().parameter("albedo").value
        self._T_ini = self.get_building().parameter("initial_temperature").value
        self._F_sky = (1 + math.sin(math.radians(self.parameter("altitude").value))) / 2
        self._create_openings_list_()
        self._calculate_K_()
        self._sunny_index_ = self.project().env_3D.get_sunny_index(self.parameter("name").value)

    def _create_openings_list_(self):
        project_openings_list = self.project().component_list(comp_type="Opening")
        self.openings = []
        for opening in project_openings_list:
            if opening.parameter("surface").component == self:
                self.openings.append(opening)

    def _calculate_K_(self):
        self.a_0, self.a_1, self.a_01 = self.parameter("construction").component.get_A()
        self.k_01 = self.area * self.a_01
        surface_type = self.parameter("surface_type").value
        if surface_type == "EXTERIOR":
            self.k[0] = self.area * (self.a_0
                - self.parameter("h_cv").value[0]
                - self.H_RD * self.radiant_property("alpha", "long_wave", 0)
            )
            self.k[1] = self.area * (self.a_1 - self.parameter("h_cv").value[1])
        elif surface_type == "INTERIOR":
            # interior
            self.k[0] = self.area * (self.a_0 - self.parameter("h_cv").value[0])
            self.k[1] = self.area * (self.a_1 - self.parameter("h_cv").value[1])
        elif surface_type == "UNDERGROUND":
            # Underground
            self.k[0] = 1  # not used
            self.k[1] = self.area * (self.a_1 - self.parameter("h_cv").value[0]) # only one defined
    

    #________ pre_iteration ____________
    def pre_iteration(self, time_i, date, daylight_saving):
        super().pre_iteration(time_i, date, daylight_saving)
        surface_type = self.parameter("surface_type").value
        # Meterological data
        self._T_ext = self._file_met.variable("temperature").values[time_i]
        # Trasient part
        self._p_0_, self._p_1_ = self.parameter("construction").component.get_P(
            time_i,
            self.variable("T_s0").values,
            self.variable("T_s1").values,
            self.variable("q_cd0").values,
            self.variable("q_cd1").values,
            self._T_ini,
        )
        self.variable("p_0").values[time_i] = self._p_0_
        self.variable("p_1").values[time_i] = self._p_1_
       
        if surface_type == "EXTERIOR":
            self._pre_iteration_exterior_(time_i)
        elif surface_type == "UNDERGROUND":
            self.variable("T_s0").values[time_i] = self._file_met.variable("underground_temperature").values[time_i]
            
    def _pre_iteration_exterior_(self, time_i):
        # Meterological data
        hor_sol_dif = self._file_met.variable("sol_diffuse").values[time_i]
        hor_sol_dir = self._file_met.variable("sol_direct").values[time_i]
        T_sky = self._file_met.variable("sky_temperature").values[time_i]

        # Diffuse solar radiation
        E_dif_sunny = self._file_met.solar_diffuse_rad(
                time_i,
                self.orientation_angle("azimuth", 0),
                self.orientation_angle("altitude", 0),
            )
        E_dif_sunny = E_dif_sunny + (1 - self._F_sky) * self._albedo * (hor_sol_dif + hor_sol_dir)
        self.variable("E_dif_sunny").values[time_i] = E_dif_sunny
        diffuse_sunny_fraction = self.project().env_3D.get_diffuse_sunny_fraction(self._sunny_index_)
        E_dif = E_dif_sunny * diffuse_sunny_fraction
        self.variable("E_dif").values[time_i] = E_dif
        # Direct solar radiation
        E_dir_sunny = self._file_met.solar_direct_rad(
                time_i,
                self.orientation_angle("azimuth", 0),
                self.orientation_angle("altitude", 0),
        )
        self.variable("E_dir_sunny").values[time_i] = E_dir_sunny
        E_dir = E_dir_sunny * self._calculate_direct_sunny_fraction_(time_i)
        self.variable("E_dir").values[time_i] = E_dir
        q_sol0 = self.radiant_property("alpha", "solar_diffuse", 0) * (E_dif + E_dir)
        self.variable("q_sol0").values[time_i] = q_sol0
                # Mean radiant temperature
        T_rm = self._F_sky * T_sky + (1 - self._F_sky) * self._T_ext
        self.variable("T_rm").values[time_i] = T_rm
        # f_0
        h_rd = self.H_RD * self.radiant_property("alpha", "long_wave", 0)
        self.f_0 = self.area * (
            -self._p_0_ - self.parameter("h_cv").value[0] * self._T_ext - h_rd * T_rm - q_sol0
        )

    def _calculate_direct_sunny_fraction_(self, time_i):
        if self.project().parameter("shadow_calculation").value == "INSTANT":
            direct_sunny_fraction = self.project().env_3D.get_direct_sunny_fraction(
                self._sunny_index_
            )
        elif self.project().parameter("shadow_calculation").value == "INTERPOLATION":
            azi = self._file_met.variable("sol_azimuth").values[time_i]
            alt = self._file_met.variable("sol_altitude").values[time_i]
            if not math.isnan(alt):
                direct_sunny_fraction = (
                    self.project().env_3D.get_direct_interpolated_sunny_fraction(
                        self._sunny_index_, azi, alt
                    )
                )
            else:
                direct_sunny_fraction = 1
        elif self.project().parameter("shadow_calculation").value == "NO":
            direct_sunny_fraction = 1
        return direct_sunny_fraction


    #________ post_iteration ____________
    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        surface_type = self.parameter("surface_type").value
        if surface_type == "EXTERIOR":
            self._calculate_exterior_T_s0_(time_index)
        self._calculate_heat_fluxes_(time_index)

    def _calculate_exterior_T_s0_(self, time_i):
        T_s0 = (self.f_0 - self.k_01 * self.variable("T_s1").values[time_i]) / self.k[0]
        self.variable("T_s0").values[time_i] = T_s0

    def _calculate_heat_fluxes_(self, time_i):
        surface_type = self.parameter("surface_type").value
        self.variable("q_cd0").values[time_i] = (
            self.a_0 * self.variable("T_s0").values[time_i]
            + self.a_01 * self.variable("T_s1").values[time_i]
            + self.variable("p_0").values[time_i]
        )
        self.variable("q_cd1").values[time_i] = (
            self.a_01 * self.variable("T_s0").values[time_i]
            + self.a_1 * self.variable("T_s1").values[time_i]
            + self.variable("p_1").values[time_i]
        )
        if surface_type == "EXTERIOR":
            self.variable("q_cv0").values[time_i] = self.parameter("h_cv").value[0] * (
                self._T_ext - self.variable("T_s0").values[time_i]
            )
            self.variable("q_cv1").values[time_i] = self.parameter("h_cv").value[1] * (
                self.get_space().variable("temperature").values[time_i]
                - self.variable("T_s1").values[time_i]
            )
            h_rd = self.H_RD * self.radiant_property("alpha", "long_wave", 0)
            self.variable("q_lwt0").values[time_i] = h_rd * (
                self.variable("T_rm").values[time_i] - self.variable("T_s0").values[time_i]
            )
            self.variable("q_lwt1").values[time_i] = (
                -self.variable("q_cd1").values[time_i]
                - self.variable("q_cv1").values[time_i]
                - self.variable("q_sol1").values[time_i]
                - self.variable("q_swig1").values[time_i]
                - self.variable("q_lwig1").values[time_i]
            )
        elif surface_type == "INTERIOR":
            self.variable("q_cv0").values[time_i] = self.parameter("h_cv").value[0] * (
                self.get_space(0).variable("temperature").values[time_i]
                - self.variable("T_s0").values[time_i]
            )
            self.variable("q_cv1").values[time_i] = self.parameter("h_cv").value[1] * (
                self.get_space(1).variable("temperature").values[time_i]
                - self.variable("T_s1").values[time_i]
            )
            self.variable("q_lwt0").values[time_i] = (
                -self.variable("q_cd0").values[time_i]
                - self.variable("q_cv0").values[time_i]
                - self.variable("q_sol0").values[time_i]
                - self.variable("q_swig0").values[time_i]
                - self.variable("q_lwig0").values[time_i]
            )
            self.variable("q_lwt1").values[time_i] = (
                -self.variable("q_cd1").values[time_i]
                - self.variable("q_cv1").values[time_i]
                - self.variable("q_sol1").values[time_i]
                - self.variable("q_swig1").values[time_i]
                - self.variable("q_lwig1").values[time_i]
            )
        elif surface_type == "UNDERGROUND":
            self.variable("q_cv0").values[time_i] = -self.variable("q_cd0").values[time_i]
            self.variable("q_cv1").values[time_i] = self.parameter("h_cv").value * (
                self.get_space().variable("temperature").values[time_i]
                - self.variable("T_s1").values[time_i]
            )
            self.variable("q_lwt1").values[time_i] = (
                -self.variable("q_cd1").values[time_i]
                - self.variable("q_cv1").values[time_i]
                - self.variable("q_sol1").values[time_i]
                - self.variable("q_swig1").values[time_i]
                - self.variable("q_lwig1").values[time_i]
            )

    @property
    def area(self):
        area = super().area
        for opening in self.openings:
            area -= opening.area
        return area

    def get_polygon_3D(self):
        azimuth = self.orientation_angle("azimuth", 0, "global")
        altitude = self.orientation_angle("altitude", 0, "global")
        origin = self.get_origin("global")
        pol_2D = self.get_polygon_2D()
        name = self.parameter("name").value
        holes_2D = []
        for opening in self.openings:
            holes_2D.append(opening.get_polygon_2D())
        if self.parameter("surface_type").value == "EXTERIOR":
            return Polygon_3D(
                name, origin, azimuth, altitude, pol_2D, holes_2D, color="white"
            )
        elif self.parameter("surface_type").value == "INTERIOR":
            return Polygon_3D(
                name, origin, azimuth, altitude, pol_2D, holes_2D, color="green", shading=False, calculate_shadows=False
            )
        elif self.parameter("surface_type").value == "UNDERGROUND":         
            return Polygon_3D(
                name, origin, azimuth, altitude, pol_2D, holes_2D, color="brown", shading=False, calculate_shadows=False
            )
