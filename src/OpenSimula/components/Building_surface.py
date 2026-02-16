import math
from opensimula.Message import Message
from opensimula.components.Surface import Surface
from opensimula.Parameters import (
    Parameter_component,
    Parameter_float,
    Parameter_float_list,
    Parameter_options,
    Parameter_component_list,
)
from opensimula.Variable import Variable
from opensimula.visual_3D.Polygon_3D import Polygon_3D


class Building_surface(Surface):
    def __init__(self, name, project):
        Surface.__init__(self, name, project)
        # Parameters
        self.parameter("type").value = "Building_surface"
        self.parameter("description").value = "Building surface"
        self.add_parameter(
            Parameter_component("construction", "not_defined", ["Construction"])
        )
        self.add_parameter(
            Parameter_component_list(
                "spaces", ["not_defined", "not_defined"], ["Space"]
            )
        )
        self.add_parameter(
            Parameter_options(
                "surface_type",
                "EXTERIOR",
                ["EXTERIOR", "INTERIOR", "UNDERGROUND", "VIRTUAL"],
            )
        )
        self.add_parameter(Parameter_float_list("h_cv", [19.3, 2], "W/m²K", min=0))
        # Only for underground surfaces
        self.add_parameter(
            Parameter_component("ground_material", "not_defined", ["Material"])
        )
        self.add_parameter(
            Parameter_float("exterior_perimeter_fraction", 1, "frac", min=0, max=1)
        )
        self.add_parameter(
            Parameter_float("exterior_perimeter_wall_thickness", 0.3, "m", min=0)
        )
        self.add_parameter(
            Parameter_float("groundwater_depth", 0, "m", min=0)
        )

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
        self._surface_type_ = self.parameter("surface_type").value
        if self._surface_type_ == "EXTERIOR" or self._surface_type_ == "UNDERGROUND":
            if self.parameter("spaces").value[0] == "not_defined":
                msg = f"{self.parameter('name').value}, must define its space."
                errors.append(Message(msg, "ERROR"))
        elif self._surface_type_ == "INTERIOR" or self._surface_type_ == "VIRTUAL":
            if (
                self.parameter("spaces").value[0] == "not_defined"
                or self.parameter("spaces").value[1] == "not_defined"
            ):
                msg = f"{self.parameter('name').value}, must define two spaces."
                errors.append(Message(msg, "ERROR"))
        # Test construction defined for non-virtual surfaces
        if (
            self._surface_type_ != "VIRTUAL"
            and self.parameter("construction").value == "not_defined"
        ):
            msg = f"{self.parameter('name').value}, Building surfaces must define its construction."
            errors.append(Message(msg, "ERROR"))
        # Test ground material defined for underground surfaces
        if (
            self._surface_type_ == "UNDERGROUND"
            and self.parameter("ground_material").value == "not_defined"
        ):
            msg = f"{self.parameter('name').value}, Underground surfaces must define its ground material."
            errors.append(Message(msg, "ERROR"))
        # Create openings list
        if self._surface_type_ == "EXTERIOR" or self._surface_type_ == "INTERIOR":
            self._create_openings_list_()
        return errors

    def get_building(self):
        return self.parameter("spaces").component[0].get_building()

    def get_space(self, side=0):
        return self.parameter("spaces").component[side]

    def radiant_property(self, prop, radiation_type, side, theta=0):
        if self._surface_type_ == "VIRTUAL":
            if prop == "tau":
                return 1
            else:
                return 0
        else:
            return self.parameter("construction").component.radiant_property(
                prop, radiation_type, side, theta
            )

    # ____________ pre_simulation ____________
    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._file_met = self.project().parameter("simulation_file_met").component
        self._albedo = self.project().parameter("albedo").value
        self._T_ini = self.get_building().parameter("initial_temperature").value
        self._F_sky = (1 + math.sin(math.radians(self.parameter("altitude").value))) / 2
        self._surface_type_ = self.parameter("surface_type").value
        self._construction_ = self.parameter("construction").component
        if self._surface_type_ == "EXTERIOR" or self._surface_type_ == "INTERIOR":
            self._create_openings_list_()
            self._calculate_K_()
        if self._surface_type_ == "EXTERIOR":
            self._sunny_index_ = self.project().env_3D.get_sunny_index(
                self.parameter("name").value
            )
        if self._surface_type_ == "UNDERGROUND":
            self._create_underground_construction_()
            self._construction_.pre_simulation(
                n_time_steps, delta_t
            )  # is not included in list of project components
            self._calculate_K_()
            self._calculate_ground_U_hat_()

    def _create_underground_construction_(self):
        # Test if underground construction already exists and delete it
        und_cons_name = self.parameter("name").value + "_und_cons"
        if self.project().component(und_cons_name) is not None:
            self.project().del_component(self.project().component(und_cons_name))
        # Test if virtual material already exists and delete it
        vir_mat_name = self.parameter("name").value + "_vir_mat"
        if self.project().component(vir_mat_name) is not None:
            self.project().del_component(self.project().component(vir_mat_name))
        # create virtual material with zero properties
        vir_mat = self.project().new_component("Material", vir_mat_name)
        vir_mat.set_parameters({"density": 1, "specific_heat": 1, "conductivity": 1})
        # create new construction for underground surfaces
        self._construction_ = self.project().duplicate_component(
            self.parameter("construction").component.parameter("name").value,
            und_cons_name,
        )
        # Equivalent thickness UNE-EN ISO 13370:2017
        self._B_prime_ = (
            2
            * self.area
            / (self.perimeter * self.parameter("exterior_perimeter_fraction").value)
        )
        R_cons = self._construction_.thermal_resistance()  # m²K/W
        self._k_g_ = (
            self.parameter("ground_material").component.parameter("conductivity").value
        )
        w = self.parameter("exterior_perimeter_wall_thickness").value  # Thickness of perimetral walls
        self._d_t_ = w + self._k_g_ * (
            1 / self.parameter("h_cv").value[0]
            + 1 / self.parameter("h_cv").value[1]
            + R_cons
        )  # m

        if self._d_t_ < self._B_prime_:
            self._U_tot_ = (
                (2 * self._k_g_)
                / (math.pi * self._B_prime_ + self._d_t_)
                * math.log((math.pi * self._B_prime_ / self._d_t_) + 1)
            )
        else:  # Well insulated
            self._U_tot_ = self._k_g_ / (self._d_t_ + 0.457 * self._B_prime_)
        
        # Gorundwater effect
        groundwater_depth = self.parameter("groundwater_depth").value
        self._G_w_ = 1.0
        if groundwater_depth > 0:
            self._G_w_ = 1 + math.exp(-2*groundwater_depth / self._B_prime_)
        self._U_tot_ *= self._G_w_

        # adding 0,5m of ground material t
        self._ground_thickness_ = 0.5  # fixed 50 cm.
        self._construction_.add_exterior_layer(
            self.parameter("ground_material").component.parameter("name").value,
            self._ground_thickness_,
        )
        # Thermal resistanace of the virtual layer
        R_vi = (
            1 / self._U_tot_
            - 1 / self.parameter("h_cv").value[1]
            - R_cons
            - 0.5 / self._k_g_
        )  # m²K/W
        k_vi = 0.1 / R_vi
        # Add virtual layer to the construction
        vir_mat.parameter("conductivity").value = k_vi
        self._construction_.add_exterior_layer(vir_mat_name, 0.1)

    def _calculate_ground_U_hat_(self):
        # Exterior temperature from meteorological file
        # Dinamics transmitance (U_hat and U_hat_ext)
        periodo_segundos = 31536000  # Un año
        rho_g = self.parameter("ground_material").component.parameter("density").value
        c_p_g = (
            self.parameter("ground_material").component.parameter("specific_heat").value
        )
        d_p = math.sqrt((self._k_g_ * periodo_segundos) / (math.pi * rho_g * c_p_g))
        self._U_hat_ext_ = self._G_w_ * self._k_g_ / math.sqrt(
            (0.457 * self._B_prime_ + self._d_t_) ** 2 + d_p**2
        )

    def _create_openings_list_(self):
        project_openings_list = self.project().component_list(comp_type="Opening")
        self.openings = []
        for opening in project_openings_list:
            if opening.parameter("surface").component == self:
                self.openings.append(opening)

    def _calculate_K_(self):
        self.a_0, self.a_1, self.a_01 = self._construction_.get_A()
        self.k_01 = self.area * self.a_01
        if self._surface_type_ == "EXTERIOR":
            self.k[0] = self.area * (
                self.a_0
                - self.parameter("h_cv").value[0]
                - self.H_RD * self.radiant_property("alpha", "long_wave", 0)
            )
            self.k[1] = self.area * (self.a_1 - self.parameter("h_cv").value[1])
        elif self._surface_type_ == "INTERIOR":
            self.k[0] = self.area * (self.a_0 - self.parameter("h_cv").value[0])
            self.k[1] = self.area * (self.a_1 - self.parameter("h_cv").value[1])
        elif self._surface_type_ == "UNDERGROUND":
            self.k[0] = 1  # not used
            self.k[1] = self.area * (
                self.a_1 - self.parameter("h_cv").value[1]
            )  # only one defined

    # ________ pre_iteration ____________
    def pre_iteration(self, time_i, date, daylight_saving):
        super().pre_iteration(time_i, date, daylight_saving)
        # Meterological data
        self._T_ext = self._file_met.variable("temperature").values[time_i]
        if self._surface_type_ != "VIRTUAL":
            # Trasient part
            self._p_0_, self._p_1_ = self._construction_.get_P(
                time_i,
                self.variable("T_s0").values,
                self.variable("T_s1").values,
                self.variable("q_cd0").values,
                self.variable("q_cd1").values,
                self._T_ini,
            )
            self.variable("p_0").values[time_i] = self._p_0_
            self.variable("p_1").values[time_i] = self._p_1_
        if self._surface_type_ == "EXTERIOR":
            self._pre_iteration_exterior_(time_i)
        if self._surface_type_ == "UNDERGROUND":
            year_start = date.replace(month=1, day=1, hour=0, minute=0, second=0)
            seconds_elapsed = (date - year_start).total_seconds()
            DT = self._file_met.DT_monthly_amplitude/2
            T_avg = self._file_met.T_average
            tau = self._file_met.month_min_temp # One month of delay for the minimum temperature, as in UNE-EN ISO 13370:2017
            m = seconds_elapsed / 2628000
            self.variable("T_s0").values[time_i] = (
                T_avg
                - self._U_hat_ext_ / self._U_tot_ * DT * math.cos(2 * math.pi * (m-tau) / 12)
                )

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
        E_dif_sunny = E_dif_sunny + (1 - self._F_sky) * self._albedo * (
            hor_sol_dif + hor_sol_dir
        )
        self.variable("E_dif_sunny").values[time_i] = E_dif_sunny
        diffuse_sunny_fraction = self.project().env_3D.get_diffuse_sunny_fraction(
            self._sunny_index_
        )
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
            -self._p_0_
            - self.parameter("h_cv").value[0] * self._T_ext
            - h_rd * T_rm
            - q_sol0
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

    # ________ post_iteration ____________
    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        if self._surface_type_ == "EXTERIOR":
            self._calculate_exterior_T_s0_(time_index)
        if self._surface_type_ != "VIRTUAL":
            self._calculate_heat_fluxes_(time_index)

    def _calculate_exterior_T_s0_(self, time_i):
        T_s0 = (self.f_0 - self.k_01 * self.variable("T_s1").values[time_i]) / self.k[0]
        self.variable("T_s0").values[time_i] = T_s0

    def _calculate_heat_fluxes_(self, time_i):
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
        if self._surface_type_ == "EXTERIOR":
            self.variable("q_cv0").values[time_i] = self.parameter("h_cv").value[0] * (
                self._T_ext - self.variable("T_s0").values[time_i]
            )
            self.variable("q_cv1").values[time_i] = self.parameter("h_cv").value[1] * (
                self.get_space().variable("temperature").values[time_i]
                - self.variable("T_s1").values[time_i]
            )
            h_rd = self.H_RD * self.radiant_property("alpha", "long_wave", 0)
            self.variable("q_lwt0").values[time_i] = h_rd * (
                self.variable("T_rm").values[time_i]
                - self.variable("T_s0").values[time_i]
            )
            self.variable("q_lwt1").values[time_i] = (
                -self.variable("q_cd1").values[time_i]
                - self.variable("q_cv1").values[time_i]
                - self.variable("q_sol1").values[time_i]
                - self.variable("q_swig1").values[time_i]
                - self.variable("q_lwig1").values[time_i]
            )
        elif self._surface_type_ == "INTERIOR":
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
        elif self._surface_type_ == "UNDERGROUND":
            self.variable("q_cv0").values[time_i] = -self.variable("q_cd0").values[
                time_i
            ]
            self.variable("q_cv1").values[time_i] = self.parameter("h_cv").value[1] * (
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
        if self._surface_type_ == "EXTERIOR" or self._surface_type_ == "INTERIOR":
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
        if self._surface_type_ == "EXTERIOR" or self._surface_type_ == "INTERIOR":
            for opening in self.openings:
                holes_2D.append(opening.get_polygon_2D())
        if self._surface_type_ == "EXTERIOR":
            return Polygon_3D(
                name, origin, azimuth, altitude, pol_2D, holes_2D, color="white"
            )
        elif self._surface_type_ == "INTERIOR":
            return Polygon_3D(
                name,
                origin,
                azimuth,
                altitude,
                pol_2D,
                holes_2D,
                color="green",
                shading=False,
                calculate_shadows=False,
            )
        elif self._surface_type_ == "UNDERGROUND":
            return Polygon_3D(
                name,
                origin,
                azimuth,
                altitude,
                pol_2D,
                holes_2D,
                color="brown",
                shading=False,
                calculate_shadows=False,
            )
        elif self._surface_type_ == "VIRTUAL":
            return Polygon_3D(
                name,
                origin,
                azimuth,
                altitude,
                pol_2D,
                color="green",
                opacity=0.4,
                shading=False,
                calculate_shadows=False,
            )
