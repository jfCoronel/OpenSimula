from OpenSimula.Component import Component
from OpenSimula.Parameters import (
    Parameter_component,
    Parameter_float,
    Parameter_options,
)
import numpy as np
import math
import psychrolib as sicro
from scipy.interpolate import RegularGridInterpolator
from scipy.integrate import dblquad
import matplotlib.pyplot as plt
import pyvista as pv
from OpenSimula.components.utils.sun_shadows import Building_3D, Polygon_3D


class Building(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Building"
        self.parameter("description").value = "Building description"
        # Parameters
        self.add_parameter(Parameter_component("file_met", "not_defined", ["File_met"]))
        # X-axe vs East angle (0: X->East, 90: x->North)
        self.add_parameter(Parameter_float("azimuth", 0, "°", min=-180, max=180))
        self.add_parameter(Parameter_float("albedo", 0.3, "frac", min=0, max=1))
        self.add_parameter(Parameter_float("initial_temperature", 20, "°C"))
        self.add_parameter(Parameter_float("initial_humidity", 7.3, "g/kg"))
        self.add_parameter(
            Parameter_options(
                "shadow_calculation", "INSTANT", ["NO", "INSTANT", "INTERPOLATION"]
            )
        )

        # Constant values
        self.C_P = 1006  # J/kg·K
        self.C_P_FURNITURE = 1000  # J/kg·K
        self.LAMBDA = 2501  # J/g Latent heat of water at 0ºC

        # Variables

        # Building_3D
        self.building_3D = None

    def check(self):
        errors = super().check()
        if self.parameter("file_met").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, file_met must be defined."
            )
        self._create_lists()
        return errors

    def _create_lists(self):
        project_spaces_list = self.project().component_list(comp_type="Space")
        self.spaces = []
        self.surfaces = []
        self.sides = []
        for space in project_spaces_list:
            if space.parameter("building").component == self:
                self.spaces.append(space)
                for surface in space.surfaces:
                    self.surfaces.append(surface)
                for side in space.sides:
                    self.sides.append(side)
        self._n_spaces = len(self.spaces)
        self._n_surfaces = len(self.surfaces)
        # Shadow_surfaces
        self.shadow_surfaces = self.project().component_list(comp_type="Shadow_surface")

    # pre_simulation
    # _______________
    # _______________
    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._file_met = self.parameter("file_met").component
        sicro.SetUnitSystem(sicro.SI)
        self.ATM_PRESSURE = sicro.GetStandardAtmPressure(self._file_met.altitude)
        self.RHO = sicro.GetDryAirDensity(22.5, self.ATM_PRESSURE)
        self._create_lists()
        self._create_ff_matrix() # View Factors ff_matrix
        self._create_B_matrix() # Conectivity B_matrix
        self._create_SW_matrices() # SWDIF_matrix, SWDIR_matrix, SWIG_matrix
        self._create_LW_matrices() # LWIG_matrix, LWSUR_matrix
        self._create_K_matrices() # KS_matrix, KS_inv_matrix, KSZ_matrix, KZS_matrix, KZ_matrix
        if self.parameter("shadow_calculation").value != "NO":
            self._create_building_3D()
            self._sim_.print("Calculating solar direct shadows ...")
            self._create_shadow_interpolation_table()
            self._sim_.print("Calculating solar diffuse shadows ...")
            self._create_diffuse_shadow()

    def _create_ff_matrix(self):
        self.ff_matrix = np.zeros((self._n_surfaces, self._n_surfaces))
        i = 0
        for space in self.spaces:
            n_i = len(space.surfaces)
            self.ff_matrix[i : i + n_i, i : i + n_i] = space.ff_matrix
            i += n_i

    def _create_B_matrix(self):
        self.B_matrix = np.zeros((self._n_surfaces, self._n_surfaces))
        for i in range(self._n_surfaces):
            for j in range(self._n_surfaces):
                if i != j and self.surfaces[i] == self.surfaces[j]:
                    self.B_matrix[i][j] = 1

    def _create_SW_matrices(self):
        SWR_matrix = np.identity(self._n_surfaces)
        rho_matrix = np.zeros((self._n_surfaces, self._n_surfaces))
        tau_matrix = np.zeros((self._n_surfaces, self._n_surfaces))
        alpha_matrix = np.zeros((self._n_surfaces, self._n_surfaces))
        area_matrix = np.zeros((self._n_surfaces, self._n_surfaces))

        for i in range(self._n_surfaces):
            rho_matrix[i][i] = self.surfaces[i].radiant_property("rho", "solar_diffuse", self.sides[i])
            tau_matrix[i][i] = self.surfaces[i].radiant_property("tau", "solar_diffuse", self.sides[i])
            # Negative (absortion)
            alpha_matrix[i][i] = -1 * self.surfaces[i].radiant_property("alpha", "solar_diffuse", self.sides[i])
            area_matrix[i][i] = self.surfaces[i].area

        SWR_matrix = (SWR_matrix - np.matmul(self.ff_matrix, rho_matrix)
            - np.matmul(self.ff_matrix, np.matmul(tau_matrix, self.B_matrix)))

        SWR_matrix = np.linalg.inv(SWR_matrix)
        aux_matrix = np.matmul(area_matrix, np.matmul(alpha_matrix, SWR_matrix))
        self.SWDIF_matrix = np.matmul(aux_matrix, np.matmul(self.ff_matrix, tau_matrix))  # SW Solar Diffuse

       
        dsr_dist_matrix = np.zeros((self._n_surfaces, self._n_spaces))
        ig_dist_matrix = np.zeros((self._n_surfaces, self._n_spaces))
        i_glob = 0
        for j in range(self._n_spaces):
            for i in range(len(self.spaces[j].surfaces)):
                dsr_dist_matrix[i_glob][j] = self.spaces[j].dsr_dist_vector[i]
                ig_dist_matrix[i_glob][j] = self.spaces[j].ig_dist_vector[i]
                i_glob += 1

        self.SWDIR_matrix = np.matmul(aux_matrix, dsr_dist_matrix)
        self.SWIG_matrix = np.matmul(aux_matrix, ig_dist_matrix)

    def _create_LW_matrices(self):
        LWR_matrix = np.identity(self._n_surfaces)
        rho_matrix = np.zeros((self._n_surfaces, self._n_surfaces))
        tau_matrix = np.zeros((self._n_surfaces, self._n_surfaces))
        alpha_matrix = np.zeros((self._n_surfaces, self._n_surfaces))
        area_matrix = np.zeros((self._n_surfaces,self._n_surfaces))

        for i in range(self._n_surfaces):
            rho_matrix[i][i] = self.surfaces[i].radiant_property("rho", "long_wave", self.sides[i])
            tau_matrix[i][i] = self.surfaces[i].radiant_property("tau", "long_wave", self.sides[i])
            # Negative (absortion)
            alpha_matrix[i][i] = -1 * self.surfaces[i].radiant_property("alpha", "long_wave", self.sides[i])
            area_matrix[i][i] = self.surfaces[i].area

        LWR_matrix = (LWR_matrix - np.matmul(self.ff_matrix, rho_matrix)
            - np.matmul(self.ff_matrix, np.matmul(tau_matrix, self.B_matrix)))

        LWR_matrix = np.linalg.inv(LWR_matrix)
        aux_matrix = np.matmul(area_matrix, np.matmul(alpha_matrix,LWR_matrix))

        ig_dist_matrix = np.zeros((self._n_surfaces, self._n_spaces))
        i_glob = 0
        for j in range(self._n_spaces):
            for i in range(len(self.spaces[j].surfaces)):
                ig_dist_matrix[i_glob][j] = self.spaces[j].ig_dist_vector[i]
                i_glob += 1

        self.LWIG_matrix = np.matmul(aux_matrix, ig_dist_matrix)

        # Temperature matrix
        self.LWSUR_matrix = np.matmul(area_matrix, -1 * alpha_matrix) - np.matmul(
            aux_matrix, np.matmul(self.ff_matrix, alpha_matrix)
        )

        H_RD = 5.705  # 4*sigma*(293^3)
        self.LWSUR_matrix = H_RD * self.LWSUR_matrix

    def _create_K_matrices(self):
        self.KS_matrix = np.copy(-self.LWSUR_matrix)
        self.KSZ_matrix = np.zeros((self._n_surfaces, self._n_spaces))
        self.KZ_matrix = np.zeros((self._n_spaces, self._n_spaces))

        # KS_matriz, KSZ_matrix
        for i in range(self._n_surfaces):
            s_type = self.surfaces[i].parameter("type").value

            if s_type == "Exterior_surface":
                k = self.surfaces[i].k
                k_01 = self.surfaces[i].k_01
                self.KS_matrix[i][i] += k[1] - (k_01**2) / k[0]
                for j in range(self._n_spaces):
                    if self.spaces[j] == self.surfaces[i].parameter("space").component:
                        self.KSZ_matrix[i][j] = (
                            self.surfaces[i].area
                            * self.surfaces[i].parameter("h_cv").value[self.sides[i]]
                        )
            elif s_type == "Underground_surface":
                k = self.surfaces[i].k
                k_01 = self.surfaces[i].k_01
                self.KS_matrix[i][i] += k[1]
                for j in range(self._n_spaces):
                    if self.spaces[j] == self.surfaces[i].parameter("space").component:
                        self.KSZ_matrix[i][j] = (
                            self.surfaces[i].area
                            * self.surfaces[i].parameter("h_cv").value
                        )
            elif s_type == "Interior_surface":
                k = self.surfaces[i].k
                k_01 = self.surfaces[i].k_01
                self.KS_matrix[i][i] += k[self.sides[i]]
                for j in range(self._n_surfaces):
                    if self.B_matrix[i][j] == 1:
                        self.KS_matrix[i][j] += k_01
                for j in range(self._n_spaces):
                    if (
                        self.spaces[j]
                        == self.surfaces[i].parameter("spaces").component[self.sides[i]]
                    ):
                        self.KSZ_matrix[i][j] = (
                            self.surfaces[i].area
                            * self.surfaces[i].parameter("h_cv").value[self.sides[i]]
                        )
            elif s_type == "Virtual_surface":
                self.KS_matrix[i][i] += 1.0
                for j in range(self._n_spaces):
                    if (
                        self.spaces[j]
                        == self.surfaces[i].parameter("spaces").component[self.sides[i]]
                    ):
                        self.KSZ_matrix[i][j] = 0
            elif s_type == "Opening":
                k = self.surfaces[i].k
                k_01 = self.surfaces[i].k_01
                self.KS_matrix[i][i] += k[1] - (k_01**2) / k[0]
                for j in range(self._n_spaces):
                    if (
                        self.spaces[j]
                        == self.surfaces[i]
                        .parameter("surface")
                        .component.parameter("space")
                        .component
                    ):
                        self.KSZ_matrix[i][j] = (
                            self.surfaces[i].area
                            * self.surfaces[i].parameter("h_cv").value[self.sides[i]]
                        )

        self.KS_inv_matrix = np.linalg.inv(self.KS_matrix)
        # KZS
        self.KZS_matrix = -1 * self.KSZ_matrix.transpose()
        
        # KZ_matrix without air movement or systems
        for i in range(self._n_spaces):
            self.KZ_matrix[i][i] = (
                self.spaces[i].parameter("volume").value * self.RHO * self.C_P
                + self.spaces[i].parameter("furniture_weight").value
                * self.C_P_FURNITURE
            ) / self.project().parameter("time_step").value
            for j in range(self._n_surfaces):
                self.KZ_matrix[i][i] += self.KSZ_matrix[j][i]
       

    def _create_building_3D(self, coordinate_system="global"):
        self.building_3D = Building_3D()
        for surface in [*self.surfaces, *self.shadow_surfaces]:
            azimuth = surface.orientation_angle("azimuth", 0, coordinate_system)
            altitude = surface.orientation_angle("altitude", 0, coordinate_system)
            origin = surface.get_origin(coordinate_system)
            pol_2D = surface.get_polygon_2D()
            s_type = surface.parameter("type").value

            if s_type == "Exterior_surface":
                holes_2D = []
                for opening in surface.openings:
                    holes_2D.append(opening.get_polygon_2D())
                polygon = Polygon_3D(origin, azimuth, altitude, pol_2D, holes_2D)
            else:
                polygon = Polygon_3D(origin, azimuth, altitude, pol_2D)
            self.building_3D.add_polygon(polygon, s_type, surface)

    def _create_shadow_interpolation_table(self):
        self.shadow_azimuth_grid = np.linspace(0, 350, 36)
        self.shadow_altitude_grid = np.linspace(-85, 85, 18)
        self.sunny_fraction_tables = np.zeros(
            (len(self.building_3D.sunny_surface), 36, 18)
        )
        j = 0
        for azimuth in self.shadow_azimuth_grid:
            azi_rd = math.radians(azimuth)
            k = 0
            for altitude in self.shadow_altitude_grid:
                alt_rd = math.radians(altitude)
                sun_position = np.array(
                    [
                        math.cos(alt_rd) * math.sin(azi_rd),
                        -math.cos(alt_rd) * math.cos(azi_rd),
                        math.sin(alt_rd),
                    ]
                )
                sunny_frac = self.building_3D.get_sunny_fractions(sun_position)
                for i in range(len(sunny_frac)):
                    self.sunny_fraction_tables[i][j][k] = sunny_frac[i]
                k = k + 1
            j = j + 1
        self.sunny_interpolation_functions = []
        for i in range(0, len(self.building_3D.sunny_surface)):
            self.sunny_interpolation_functions.append(
                RegularGridInterpolator(
                    (self.shadow_azimuth_grid, self.shadow_altitude_grid),
                    self.sunny_fraction_tables[i],
                    bounds_error=False,
                    fill_value=None,
                    method="cubic",
                )
            )

    def _create_diffuse_shadow(self):
        def integral(i):
            sunny_value = 0
            shadow_value = 0
            n = 0
            for j in range(len(self.shadow_azimuth_grid)):
                for k in range(len(self.shadow_altitude_grid)):
                    theta = self.building_3D.sunny_surface[i].get_angle_with_normal(
                        self.shadow_azimuth_grid[j], self.shadow_altitude_grid[k]
                    )
                    if theta < math.pi / 2:
                        f = 0.5 * math.sin(2 * theta)
                        sunny_value = sunny_value + f
                        shadow_value = (
                            shadow_value + f * self.sunny_fraction_tables[i][j][k]
                        )
                        n = n + 1
            return shadow_value / sunny_value

        self.shadow_diffuse_fraction = []
        for i in range(0, len(self.building_3D.sunny_surface)):
            self.shadow_diffuse_fraction.append(integral(i))

    # pre_iteration
    # _______________
    # _______________
    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        self._calculate_shadows(time_index) # sunny_fractions
        self._first_iteration = True
        self._calculate_Q_igsw(time_index)
        self._calculate_Q_iglw(time_index)
        self._calculate_Q_dif(time_index)
        self._calculate_FZ_vector(time_index)
        self._update_K_matrices(time_index)

    def _calculate_shadows(self, time_i):
        self.sunny_fractions = [1] * len(self.building_3D.sunny_list)
        if self.parameter("shadow_calculation").value != "NO":
            azi = self._file_met.variable("sol_azimuth").values[time_i]
            alt = self._file_met.variable("sol_altitude").values[time_i]
            if not math.isnan(alt):
                if self.parameter("shadow_calculation").value == "INSTANT":
                    azi_rd = math.radians(azi)
                    alt_rd = math.radians(alt)
                    sun_position = np.array(
                        [
                            math.cos(alt_rd) * math.sin(azi_rd),
                            -math.cos(alt_rd) * math.cos(azi_rd),
                            math.sin(alt_rd),
                        ]
                    )
                    self.sunny_fractions = self.building_3D.get_sunny_fractions(
                        sun_position
                    )
                elif self.parameter("shadow_calculation").value == "INTERPOLATION":
                    for i in range(0, len(self.building_3D.sunny_surface)):
                        if azi < 0:
                            azi = azi + 360
                        self.sunny_fractions[i] = self.sunny_interpolation_functions[i](
                            (azi, alt)
                        )

    def _calculate_Q_igsw(self, time_i):
        E_ig = np.zeros(self._n_spaces)
        for i in range(self._n_spaces):
            E_ig[i] = self.spaces[i].variable("light_radiant").values[time_i]
        self.Q_igsw = np.matmul(self.SWIG_matrix, E_ig)

    def _calculate_Q_iglw(self, time_i):
        E_ig = np.zeros(self._n_spaces)
        for i in range(self._n_spaces):
            E_ig[i] = (
                self.spaces[i].variable("people_radiant").values[time_i]
                + self.spaces[i].variable("other_gains_radiant").values[time_i]
            )
        self.Q_iglw = np.matmul(self.LWIG_matrix, E_ig)

    def _calculate_Q_dif(self, time_i):
        E_dif = np.zeros(self._n_surfaces)
        for i in range(self._n_surfaces):
            s_type = self.surfaces[i].parameter("type").value
            if s_type == "Opening" or s_type == "Exterior_surface":
                E_dif[i] = self.surfaces[i].variable("E_dif").values[time_i]
        self.Q_dif = np.matmul(self.SWDIF_matrix, E_dif)

    def _calculate_FZ_vector(self, time_i):
        self.FZ_vector = np.zeros(self._n_spaces)

        for i in range(self._n_spaces):
            if time_i == 0:
                T_pre = self.parameter("initial_temperature").value
            else:
                T_pre = self.spaces[i].variable("temperature").values[time_i - 1]
            self.FZ_vector[i] = (
                self.spaces[i].variable("people_convective").values[time_i]
                + self.spaces[i].variable("other_gains_convective").values[time_i]
                + self.spaces[i].variable("light_convective").values[time_i]
            )
            self.FZ_vector[i] += (
                (
                    self.spaces[i].parameter("volume").value * self.RHO * self.C_P
                    + self.spaces[i].parameter("furniture_weight").value
                    * self.C_P_FURNITURE
                )
                * T_pre
                / self.project().parameter("time_step").value
            )
            self.FZ_vector[i] += (
                self.spaces[i].variable("infiltration_flow").values[time_i]
                * self.RHO
                * self.C_P
                * self._file_met.variable("temperature").values[time_i]
            )

    def _update_K_matrices(self, time_i):
        self.KZFIN_matrix = self.KZ_matrix.copy()

        # Add infiltration
        for i in range(self._n_spaces):
            self.KZFIN_matrix[i][i] += (
                self.spaces[i].variable("infiltration_flow").values[time_i]
                * self.RHO
                * self.C_P
            )

    def iteration(self, time_index, date, daylight_saving):
        super().iteration(time_index, date, daylight_saving)
        if self._first_iteration:  # Only in the 1st iteration
            self._calculate_Q_dir(time_index)
            self._calculate_FS_vector(time_index)
            self._calculate_FIN_WS_matrices(time_index)
            self._update_space_K_F(time_index)
            self._first_iteration = False
            return False # Force iteration
        else:
            self._update_space_K_F(time_index)
            self._store_surfaces_values(time_index)
            return True

    def _calculate_Q_dir(self, time_i):
        E_dir = np.zeros(self._n_spaces)
        for i in range(self._n_spaces):
            E_dir[i] = self.spaces[i].variable("solar_direct_gains").values[time_i]
        self.Q_dir = np.matmul(self.SWDIR_matrix, E_dir)

    def _calculate_FS_vector(self, time_i):
        self.FS_vector = np.zeros(self._n_surfaces)

        for i in range(self._n_surfaces):
            # positive surface incoming
            Q_rad = -(self.Q_dir[i] + self.Q_dif[i] + self.Q_igsw[i] + self.Q_iglw[i])
            s_type = self.surfaces[i].parameter("type").value
            area = self.surfaces[i].area
            if s_type == "Exterior_surface":
                self.surfaces[i].variable("q_sol1").values[time_i] = (
                    -(self.Q_dir[i] + self.Q_dif[i]) / area
                )
                self.surfaces[i].variable("q_swig1").values[time_i] = (
                    -self.Q_igsw[i] / area
                )
                self.surfaces[i].variable("q_lwig1").values[time_i] = (
                    -(self.Q_iglw[i]) / area
                )
                f = (
                    -area * self.surfaces[i].variable("p_1").values[time_i]
                    - Q_rad
                    - self.surfaces[i].f_0
                    * self.surfaces[i].k_01
                    / self.surfaces[i].k[0]
                )
                self.FS_vector[i] = f
                self.surfaces[i].variable("debug_f").values[time_i] = f
            elif s_type == "Underground_surface":
                self.surfaces[i].variable("q_sol1").values[time_i] = (
                    -(self.Q_dir[i] + self.Q_dif[i]) / area
                )
                self.surfaces[i].variable("q_swig1").values[time_i] = (
                    -self.Q_igsw[i] / area
                )
                self.surfaces[i].variable("q_lwig1").values[time_i] = (
                    -(self.Q_iglw[i]) / area
                )
                f = (
                    -area * self.surfaces[i].variable("p_1").values[time_i]
                    - Q_rad
                    - self.surfaces[i].k_01
                    * self.surfaces[i].variable("T_s0").values[time_i]
                )
                self.FS_vector[i] = f
                self.surfaces[i].variable("debug_f").values[time_i] = f
            elif s_type == "Interior_surface":
                if self.sides[i] == 0:
                    self.surfaces[i].variable("q_sol0").values[time_i] = (
                        -(self.Q_dir[i] + self.Q_dif[i]) / area
                    )
                    self.surfaces[i].variable("q_swig0").values[time_i] = (
                        -self.Q_igsw[i] / area
                    )
                    self.surfaces[i].variable("q_lwig0").values[time_i] = (
                        -(self.Q_iglw[i]) / area
                    )
                    f = (
                        -self.surfaces[i].area
                        * self.surfaces[i].variable("p_0").values[time_i]
                        - Q_rad
                    )
                    self.FS_vector[i] = f
                    self.surfaces[i].variable("debug_f0").values[time_i] = f
                else:
                    self.surfaces[i].variable("q_sol1").values[time_i] = (
                        -(self.Q_dir[i] + self.Q_dif[i]) / area
                    )
                    self.surfaces[i].variable("q_swig1").values[time_i] = (
                        -self.Q_igsw[i] / area
                    )
                    self.surfaces[i].variable("q_lwig1").values[time_i] = (
                        -(self.Q_iglw[i]) / area
                    )
                    f = (
                        -self.surfaces[i].area
                        * self.surfaces[i].variable("p_1").values[time_i]
                        - Q_rad
                    )
                    self.FS_vector[i] = f
                    self.surfaces[i].variable("debug_f1").values[time_i] = f
            elif s_type == "Virtual_surface":
                self.FS_vector[i] = 0.0
            elif s_type == "Opening":
                q_sol_10 = -(self.Q_dir[i] + self.Q_dif[i]) / area
                E_sol_int = q_sol_10 / self.surfaces[i].radiant_property(
                    "alpha", "solar_diffuse", 1
                )
                E_swig_int = -self.Q_igsw[i] / (
                    area
                    * self.surfaces[i].radiant_property("alpha", "solar_diffuse", 1)
                )
                self.surfaces[i].variable("E_ref").values[time_i] = E_sol_int
                self.surfaces[i].variable("E_ref_tra").values[time_i] = (
                    E_sol_int
                    * self.surfaces[i].radiant_property("tau", "solar_diffuse", 1)
                )
                self.surfaces[i].variable("q_sol1").values[time_i] += q_sol_10
                self.surfaces[i].variable("q_sol0").values[
                    time_i
                ] += E_sol_int * self.surfaces[i].radiant_property(
                    "alpha_other_side", "solar_diffuse", 1
                )
                self.surfaces[i].variable("q_swig1").values[time_i] = (
                    -self.Q_igsw[i] / area
                )
                self.surfaces[i].variable("q_swig0").values[time_i] = (
                    E_swig_int
                    * self.surfaces[i].radiant_property(
                        "alpha_other_side", "solar_diffuse", 1
                    )
                )
                self.surfaces[i].variable("q_lwig1").values[time_i] = (
                    -(self.Q_iglw[i]) / area
                )
                f_0 = (
                    self.surfaces[i].f_0
                    - (
                        self.surfaces[i].variable("q_sol0").values[time_i]
                        + self.surfaces[i].variable("q_swig0").values[time_i]
                    )
                    * area
                )
                f = (
                    -Q_rad
                    - (self.surfaces[i].variable("q_sol1").values[time_i] - q_sol_10)
                    * area
                    - f_0 * self.surfaces[i].k_01 / self.surfaces[i].k[0]
                )
                self.FS_vector[i] = f
                self.surfaces[i].variable("debug_f").values[time_i] = f

    def _calculate_FIN_WS_matrices(self, time_i): # Without Systems
        self.KFIN_WS_matrix = self.KZFIN_matrix - np.matmul(
            self.KZS_matrix, np.matmul(self.KS_inv_matrix, self.KSZ_matrix)
        )
        self.FFIN_WS_vector = self.FZ_vector - np.matmul(
            self.KZS_matrix, np.matmul(self.KS_inv_matrix, self.FS_vector)
        )
    
    def _update_space_K_F(self, time_i):
        for i in range(self._n_spaces):
            F_spaces = 0
            for j in range(self._n_spaces):
                if i != j:
                    F_spaces -= self.KFIN_WS_matrix[i][j]* self.spaces[j].variable("temperature").values[time_i]
            K_F={"K": self.KFIN_WS_matrix[i][i], "F":self.FFIN_WS_vector[i], "F_OS": F_spaces}
            self.spaces[i].update_K_F(K_F)
    
    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        #self._store_surfaces_values(time_index)

    def _store_surfaces_values(self, time_i):
        # T_spaces
        T_spaces = np.zeros(self._n_spaces)
        for i in range(self._n_spaces):
            T_spaces[i] = self.spaces[i].variable("temperature").values[time_i]

        # Calculate TS,
        self.TS_vector = np.matmul(self.KS_inv_matrix, self.FS_vector) - np.matmul(self.KS_inv_matrix, np.matmul(self.KSZ_matrix,T_spaces))
        
        # Store TS
        for i in range(self._n_surfaces):
            if self.surfaces[i].parameter("type").value != "Virtual_surface":
                if self.sides[i] == 0:
                    self.surfaces[i].variable("T_s0").values[time_i] = self.TS_vector[i]
                else:
                    self.surfaces[i].variable("T_s1").values[time_i] = self.TS_vector[i]

    def show3D(self, hide=[], opacity=1, coordinate_system="global", space="all"):
        self._create_building_3D(coordinate_system)
        if space != "all":
            if not isinstance(opacity, list):
                opacity = [opacity] * len(self.building_3D.polygons)
            i = 0
            for surface in [*self.surfaces, *self.shadow_surfaces]:
                if (
                    surface.parameter("type").value == "Interior_surface"
                    or surface.parameter("type").value == "Virtual_surface"
                ):
                    is_my_space = (
                        surface.space(0).parameter("name").value == space
                        or surface.space(1).parameter("name").value == space
                    )
                elif surface.parameter("type").value == "Shadow_surface":
                    is_my_space = False
                else:
                    is_my_space = surface.space().parameter("name").value == space

                if not is_my_space:
                    opacity[i] = opacity[i] * 0.25
                i = i + 1
        self.building_3D.show(hide, opacity)

    def show3D_shadows(self, date):
        self._create_building_3D()
        self._file_met = self.parameter("file_met").component
        cos = self._file_met.sun_cosines(date)
        if len(cos) == 3:
            self.building_3D.show_shadows(cos)
        else:
            self._sim_.print(
                "Warning: " + date.strftime("%H:%M,  %d/%m/%Y") + " is night"
            )

    def get_direct_sunny_fraction(self, surface):
        if self.parameter("shadow_calculation").value == "NO":
            return 1
        else:
            i = self.building_3D.sunny_surface.index(surface)
            return self.sunny_fractions[i]

    def get_diffuse_sunny_fraction(self, surface):
        if self.parameter("shadow_calculation").value == "NO":
            return 1
        else:
            i = self.building_3D.sunny_surface.index(surface)
            return self.shadow_diffuse_fraction[i]

    def show_sunny_fraction(self, i):
        fig, ax = plt.subplots()
        X, Y = np.meshgrid(self.shadow_azimuth_grid, self.shadow_altitude_grid)
        ax.imshow(self.sunny_fraction_tables[i], vmin=0, vmax=1)
        plt.show()
