from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_component, Parameter_float
import numpy as np
import math
import psychrolib as sicro
import pyvista as pv


class Building(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Building"
        self.parameter("description").value = "Building description"
        # Parameters
        self.add_parameter(Parameter_component(
            "file_met", "not_defined", ["File_met"]))
        # X-axe vs East angle (0: X->East, 90: x->North)
        self.add_parameter(Parameter_float(
            "azimuth", 0, "°", min=-180, max=180))
        self.add_parameter(Parameter_float(
            "albedo", 0.3, "frac", min=0, max=1))
        self.add_parameter(Parameter_float(
            "initial_temperature", 20, "°C"))
        self.add_parameter(Parameter_float(
            "initial_humidity", 7.3, "g/kg"))

        # Constant values
        self.C_P = 1006  # J/kg·K
        self.C_P_FURNITURE = 1000  # J/kg·K
        self.LAMBDA = 2501  # J/g Latent heat of water at 0ºC

        # Variables

    def check(self):
        errors = super().check()
        if self.parameter("file_met").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, file_met must be defined.")
        self._create_spaces_surfaces_list()
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._file_met = self.parameter("file_met").component
        sicro.SetUnitSystem(sicro.SI)
        self.ATM_PRESSURE = sicro.GetStandardAtmPressure(
            self._file_met.altitude)
        # Density for convert volumetric to mass flows
        self.RHO = sicro.GetDryAirDensity(22.5, self.ATM_PRESSURE)
        self._create_spaces_surfaces_list()
        self._create_ff_matrix()
        self._create_B_matrix()
        self._create_SW_matrices()
        self._create_LW_matrices()
        self._create_K_matrices()

    def _create_spaces_surfaces_list(self):
        project_spaces_list = self.project().component_list(type="Space")
        self.spaces = []
        self.surfaces = []
        self.sides = []
        for space in project_spaces_list:
            if (space.parameter("building").component == self):
                self.spaces.append(space)
                for surface in space.surfaces:
                    self.surfaces.append(surface)
                for side in space.sides:
                    self.sides.append(side)

    def _create_ff_matrix(self):
        n = len(self.surfaces)
        self.ff_matrix = np.zeros((n, n))
        i = 0
        for space in self.spaces:
            n_i = len(space.surfaces)
            self.ff_matrix[i:i+n_i, i:i + n_i] = space.ff_matrix
            i += n_i

    def _create_B_matrix(self):
        n = len(self.surfaces)
        self.B_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i != j and self.surfaces[i] == self.surfaces[j]:
                    self.B_matrix[i][j] = 1

    def _create_SW_matrices(self):
        n = len(self.surfaces)
        self.SWR_matrix = np.identity(n)
        rho_matrix = np.zeros((n, n))
        tau_matrix = np.zeros((n, n))
        alpha_matrix = np.zeros((n, n))
        area_matrix = np.zeros((n, n))

        for i in range(n):
            rho_matrix[i][i] = self.surfaces[i].radiant_property(
                "rho", "solar_diffuse", self.sides[i])
            tau_matrix[i][i] = self.surfaces[i].radiant_property(
                "tau", "solar_diffuse", self.sides[i])
            # Negative (absortion)
            alpha_matrix[i][i] = -1 * \
                self.surfaces[i].radiant_property(
                    "alpha", "solar_diffuse", self.sides[i])
            area_matrix[i][i] = self.surfaces[i].area

        self.SWR_matrix = self.SWR_matrix - \
            np.matmul(self.ff_matrix, rho_matrix) - \
            np.matmul(self.ff_matrix, np.matmul(tau_matrix, self.B_matrix))

        self.SWR_matrix = np.linalg.inv(self.SWR_matrix)
        aux_matrix = np.matmul(area_matrix, np.matmul(
            alpha_matrix, self.SWR_matrix))
        self.SWDIF_matrix = np.matmul(aux_matrix, np.matmul(
            self.ff_matrix, tau_matrix))  # SW Solar Diffuse

        m = len(self.spaces)
        dsr_dist_matrix = np.zeros((n, m))
        ig_dist_matrix = np.zeros((n, m))
        i_glob = 0
        for j in range(m):
            for i in range(len(self.spaces[j].surfaces)):
                dsr_dist_matrix[i_glob][j] = self.spaces[j].dsr_dist_vector[i]
                ig_dist_matrix[i_glob][j] = self.spaces[j].ig_dist_vector[i]
                i_glob += 1

        self.SWDIR_matrix = np.matmul(aux_matrix, dsr_dist_matrix)
        self.SWIG_matrix = np.matmul(aux_matrix, ig_dist_matrix)

    def _create_LW_matrices(self):
        n = len(self.surfaces)
        self.LWR_matrix = np.identity(n)
        rho_matrix = np.zeros((n, n))
        tau_matrix = np.zeros((n, n))
        alpha_matrix = np.zeros((n, n))
        area_matrix = np.zeros((n, n))

        for i in range(n):
            rho_matrix[i][i] = self.surfaces[i].radiant_property(
                "rho", "long_wave", self.sides[i])
            tau_matrix[i][i] = self.surfaces[i].radiant_property(
                "tau", "long_wave", self.sides[i])
            # Negative (absortion)
            alpha_matrix[i][i] = -1 * \
                self.surfaces[i].radiant_property(
                    "alpha", "long_wave", self.sides[i])
            area_matrix[i][i] = self.surfaces[i].area

        self.LWR_matrix = self.LWR_matrix - \
            np.matmul(self.ff_matrix, rho_matrix) - \
            np.matmul(self.ff_matrix, np.matmul(tau_matrix, self.B_matrix))

        self.LWR_matrix = np.linalg.inv(self.LWR_matrix)
        aux_matrix = np.matmul(area_matrix, np.matmul(
            alpha_matrix, self.LWR_matrix))
        self.LWEXT_matrix = np.matmul(aux_matrix, np.matmul(
            self.ff_matrix, tau_matrix))  # Exterior irradiations

        m = len(self.spaces)
        ig_dist_matrix = np.zeros((n, m))
        i_glob = 0
        for j in range(m):
            for i in range(len(self.spaces[j].surfaces)):
                ig_dist_matrix[i_glob][j] = self.spaces[j].ig_dist_vector[i]
                i_glob += 1

        self.LWIG_matrix = np.matmul(aux_matrix, ig_dist_matrix)

        # Temperature matrix
        self.KTEMP_matrix = np.matmul(area_matrix, -1 * alpha_matrix) - \
            np.matmul(aux_matrix, np.matmul(self.ff_matrix, alpha_matrix))

        H_RD = 5.705  # 4*sigma*(293^3)
        self.KTEMP_matrix = H_RD * self.KTEMP_matrix

    def _create_K_matrices(self):
        n = len(self.surfaces)
        m = len(self.spaces)
        self.KS_matrix = np.copy(-self.KTEMP_matrix)
        self.KSZ_matrix = np.zeros((n, m))
        self.KZ_matrix = np.zeros((m, m))

        # KS_matriz, KSZ_matrix
        for i in range(n):
            s_type = self.surfaces[i].parameter("type").value

            if s_type == "Exterior_surface":
                k = self.surfaces[i].k
                k_01 = self.surfaces[i].k_01
                self.KS_matrix[i][i] += k[1] - (k_01**2)/k[0]
                for j in range(m):
                    if self.spaces[j] == self.surfaces[i].parameter("space").component:
                        self.KSZ_matrix[i][j] = self.surfaces[i].area * \
                            self.surfaces[i].parameter(
                                "h_cv").value[self.sides[i]]
            elif s_type == "Underground_surface":
                k = self.surfaces[i].k
                k_01 = self.surfaces[i].k_01
                self.KS_matrix[i][i] += k[1]
                for j in range(m):
                    if self.spaces[j] == self.surfaces[i].parameter("space").component:
                        self.KSZ_matrix[i][j] = self.surfaces[i].area * \
                            self.surfaces[i].parameter("h_cv").value
            elif s_type == "Interior_surface":
                k = self.surfaces[i].k
                k_01 = self.surfaces[i].k_01
                self.KS_matrix[i][i] += k[self.sides[i]]
                for j in range(n):
                    if self.B_matrix[i][j] == 1:
                        self.KS_matrix[i][j] += k_01
                for j in range(m):
                    if self.spaces[j] == self.surfaces[i].parameter("spaces").component[self.sides[i]]:
                        self.KSZ_matrix[i][j] = self.surfaces[i].area * \
                            self.surfaces[i].parameter(
                                "h_cv").value[self.sides[i]]
            elif s_type == "Virtual_exterior_surface":
                self.KS_matrix[i][i] += 1.0
                for j in range(m):
                    if self.spaces[j] == self.surfaces[i].parameter("space").component:
                        self.KSZ_matrix[i][j] = 0
            elif s_type == "Virtual_interior_surface":
                self.KS_matrix[i][i] += 1.0
                for j in range(m):
                    if self.spaces[j] == self.surfaces[i].parameter("spaces").component[self.sides[i]]:
                        self.KSZ_matrix[i][j] = 0
            elif s_type == "Opening":
                k = self.surfaces[i].k
                k_01 = self.surfaces[i].k_01
                self.KS_matrix[i][i] += k[1] - (k_01**2)/k[0]
                for j in range(m):
                    if self.spaces[j] == self.surfaces[i].parameter("surface").component.parameter("space"):
                        self.KSZ_matrix[i][j] = self.surfaces[i].area * \
                            self.surfaces[i].parameter(
                                "h_cv").value[self.sides[i]]

        self.KS_inv_matrix = np.linalg.inv(self.KS_matrix)

        # KZ_matrix without air movement
        for i in range(m):
            self.KZ_matrix[i][i] = (self.spaces[i].parameter("volume").value * self.RHO * self.C_P + self.spaces[i].parameter(
                "furniture_weight").value * self.C_P_FURNITURE) / self.project().parameter("time_step").value
            for j in range(n):
                self.KZ_matrix[i][i] += self.KSZ_matrix[j][i]
        # KZS
        self.KZS_matrix = -1 * self.KSZ_matrix.transpose()

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        self._calculate_Q_dir(time_index)
        self._calculate_Q_igsw(time_index)
        self._calculate_Q_iglw(time_index)
        self._calculate_Q_dif(time_index)
        self._calculate_Q_extlw(time_index)
        self._calculate_FS_vector(time_index)
        self._calculate_FZ_vector(time_index)
        self._update_K_matrices(time_index)
        self._calculate_FINAL_matrices(time_index)
        self.TZ_vector = np.matmul(self.KFIN_inv_matrix, self.FFIN_vector)

    def _calculate_Q_dir(self, time_i):
        E_dir = np.zeros(len(self.spaces))
        for i in range(len(self.spaces)):
            E_dir[i] = self.spaces[i].variable(
                "solar_direct_gains").values[time_i]
        self.Q_dir = np.matmul(self.SWDIR_matrix, E_dir)

    def _calculate_Q_igsw(self, time_i):
        E_ig = np.zeros(len(self.spaces))
        for i in range(len(self.spaces)):
            E_ig[i] = self.spaces[i].variable("light_radiant").values[time_i]
        self.Q_igsw = np.matmul(self.SWIG_matrix, E_ig)

    def _calculate_Q_iglw(self, time_i):
        E_ig = np.zeros(len(self.spaces))
        for i in range(len(self.spaces)):
            E_ig[i] = self.spaces[i].variable(
                "people_radiant").values[time_i] + self.spaces[i].variable("other_gains_radiant").values[time_i]
        self.Q_iglw = np.matmul(self.LWIG_matrix, E_ig)

    def _calculate_Q_dif(self, time_i):
        E_dif = np.zeros(len(self.surfaces))
        for i in range(len(self.surfaces)):
            s_type = self.surfaces[i].parameter("type").value
            if s_type == "Opening" or s_type == "Exterior_surface" or s_type == "Virtual_exterior_surface":
                E_dif[i] = self.surfaces[i].variable("E_dif").values[time_i]
        self.Q_dif = np.matmul(self.SWDIF_matrix, E_dif)

    def _calculate_Q_extlw(self, time_i):
        E_ext = np.zeros(len(self.surfaces))
        for i in range(len(self.surfaces)):
            s_type = self.surfaces[i].parameter("type").value
            if s_type == "Virtual_exterior_surface":
                E_ext[i] = 5.56E-8 * \
                    (self.surfaces[i].variable("T_rm").values[time_i]**4)
        self.Q_extlw = np.matmul(self.LWEXT_matrix, E_ext)

    def _calculate_FS_vector(self, time_i):
        n = len(self.surfaces)
        self.FS_vector = np.zeros(n)

        for i in range(n):
            Q_rad = -(self.Q_dir[i] + self.Q_dif[i] +
                      self.Q_igsw[i] + self.Q_iglw[i] + self.Q_extlw[i])  # positive surface incoming
            s_type = self.surfaces[i].parameter("type").value
            area = self.surfaces[i].area
            if s_type == "Exterior_surface":
                self.surfaces[i].variable("q_sol1").values[time_i] = - (
                    self.Q_dir[i] + self.Q_dif[i])/area
                self.surfaces[i].variable(
                    "q_swig1").values[time_i] = - self.Q_igsw[i]/area
                self.surfaces[i].variable("q_lwig1").values[time_i] = - (
                    self.Q_iglw[i] + self.Q_extlw[i])/area
                self.FS_vector[i] = -self.surfaces[i].area * self.surfaces[i].variable(
                    "p_1").values[time_i] - Q_rad - self.surfaces[i].f_0 * self.surfaces[i].k_01 / self.surfaces[i].k[0]
            elif s_type == "Underground_surface":
                self.surfaces[i].variable("q_sol1").values[time_i] = - (
                    self.Q_dir[i] + self.Q_dif[i])/area
                self.surfaces[i].variable(
                    "q_swig1").values[time_i] = - self.Q_igsw[i]/area
                self.surfaces[i].variable("q_lwig1").values[time_i] = - (
                    self.Q_iglw[i] + self.Q_extlw[i])/area
                self.FS_vector[i] = -self.surfaces[i].area * self.surfaces[i].variable(
                    "p_1").values[time_i] - Q_rad - self.surfaces[i].k_01 * self.surfaces[i].variable("T_s0").values[time_i]
            elif s_type == "Interior_surface":
                if self.sides[i] == 0:
                    self.surfaces[i].variable("q_sol0").values[time_i] = - (
                        self.Q_dir[i] + self.Q_dif[i])/area
                    self.surfaces[i].variable(
                        "q_swig0").values[time_i] = - self.Q_igsw[i]/area
                    self.surfaces[i].variable("q_lwig0").values[time_i] = - (
                        self.Q_iglw[i] + self.Q_extlw[i])/area
                    self.FS_vector[i] = -self.surfaces[i].area * \
                        self.surfaces[i].variable("p_0").values[time_i] - Q_rad
                else:
                    self.surfaces[i].variable("q_sol1").values[time_i] = - (
                        self.Q_dir[i] + self.Q_dif[i])/area
                    self.surfaces[i].variable(
                        "q_swig1").values[time_i] = - self.Q_igsw[i]/area
                    self.surfaces[i].variable("q_lwig1").values[time_i] = - (
                        self.Q_iglw[i] + self.Q_extlw[i])/area
                    self.FS_vector[i] = -self.surfaces[i].area * \
                        self.surfaces[i].variable("p_1").values[time_i] - Q_rad
            elif s_type == "Virtual_exterior_surface" or s_type == "Virtual_interior_surface":
                self.FS_vector[i] = 0.0
            elif s_type == "Opening":
                q_sol_10 =(self.Q_dir[i] + self.Q_dif[i])/area
                E_sol_int = -q_sol_10/self.surfaces[i].radiant_property("alpha", "solar_diffuse", 1)
                E_swig_int = -self.Q_igsw[i]/(area*self.surfaces[i].radiant_property("alpha", "solar_diffuse", 1))
                self.surfaces[i].variable("E_ref").values[time_i] = E_sol_int
                self.surfaces[i].variable("E_ref_tra").values[time_i] = E_sol_int * self.surfaces[i].radiant_property("tau", "solar_diffuse", 1)    
                self.surfaces[i].variable("q_sol1").values[time_i] += q_sol_10 
                self.surfaces[i].variable("q_sol0").values[time_i] += -E_sol_int * self.surfaces[i].radiant_property("alpha_other_side", "solar_diffuse", 1)
                self.surfaces[i].variable("q_swig1").values[time_i] = self.Q_igsw[i]/area
                self.surfaces[i].variable("q_swig0").values[time_i] = - E_swig_int * self.surfaces[i].radiant_property("alpha_other_side", "solar_diffuse", 1)
                self.surfaces[i].variable("q_lwig1").values[time_i] = (self.Q_iglw[i] + self.Q_extlw[i])/area
                f_0 = self.surfaces[i].f_0 + (self.surfaces[i].variable("q_sol0").values[time_i] +self.surfaces[i].variable("q_swig0").values[time_i] ) * area
                self.FS_vector[i] = - Q_rad + self.surfaces[i].variable("q_sol1").values[time_i] * area - f_0 * self.surfaces[i].k_01 / self.surfaces[i].k[0]

    def _calculate_FZ_vector(self, time_i):
        m = len(self.spaces)
        self.FZ_vector = np.zeros(m)
        self.PZ_vector = np.zeros(m)  # Perfect conditioning loads

        for i in range(m):
            if time_i == 0:
                T_pre = self.parameter("initial_temperature").value
            else:
                T_pre = self.spaces[i].variable("temperature").values[time_i-1]
            self.FZ_vector[i] = self.spaces[i].variable("people_convective").values[time_i] + self.spaces[i].variable(
                "other_gains_convective").values[time_i] + self.spaces[i].variable("light_convective").values[time_i]
            self.FZ_vector[i] += (self.spaces[i].parameter("volume").value * self.RHO * self.C_P + self.spaces[i].parameter(
                "furniture_weight").value * self.C_P_FURNITURE) * T_pre / self.project().parameter("time_step").value
            self.FZ_vector[i] += self.spaces[i].variable("infiltration_flow").values[time_i] * \
                self.RHO*self.C_P * \
                self._file_met.variable("temperature").values[time_i]

    def _update_K_matrices(self, time_i):
        m = len(self.spaces)
        self.KZFIN_matrix = self.KZ_matrix.copy()

        # Add infiltration
        for i in range(m):
            self.KZFIN_matrix[i][i] += self.spaces[i].variable(
                "infiltration_flow").values[time_i]*self.RHO*self.C_P

    def _calculate_FINAL_matrices(self, time_i):
        self.KFIN_matrix = self.KZFIN_matrix - \
            np.matmul(self.KZS_matrix, np.matmul(
                self.KS_inv_matrix, self.KSZ_matrix))
        self.KFIN_inv_matrix = np.linalg.inv(self.KFIN_matrix)
        self.FFIN_vector = self.FZ_vector - \
            np.matmul(self.KZS_matrix, np.matmul(
                self.KS_inv_matrix, self.FS_vector))

    def iteration(self, time_index, date, daylight_saving):
        super().iteration(time_index, date, daylight_saving)
        # Comprobar convergencia
        converged = self._converged(time_index)
        if converged:
            self._store_spaces_values(time_index)
            self._store_surfaces_values(time_index)
        else:
            self._calculate_T_P(time_index)
        return converged

    def _converged(self, time_i):
        for i in range(len(self.spaces)):
            heat_on, heat_sp = self.spaces[i].perfect_heating(time_i)
            cool_on, cool_sp = self.spaces[i].perfect_cooling(time_i)
            if heat_on and self.TZ_vector[i] < heat_sp:
                return False
            if cool_on and self.TZ_vector[i] > cool_sp:
                return False
        return True

    def _calculate_T_P(self, time_i):
        # T del espacio 0 -9999 si desconocida
        unknown_T = []
        n_unknown_T = 0
        for i in range(len(self.spaces)):
            heat_on, heat_sp = self.spaces[i].perfect_heating(time_i)
            cool_on, cool_sp = self.spaces[i].perfect_cooling(time_i)
            unknown_T.append(True)
            n_unknown_T += 1
            if heat_on and self.TZ_vector[i] < heat_sp:
                unknown_T[i] = False
                self.TZ_vector[i] = heat_sp
                n_unknown_T -= 1
            if cool_on and self.TZ_vector[i] > cool_sp:
                unknown_T[i] = False
                self.TZ_vector[i] = cool_sp
                n_unknown_T -= 1
        if n_unknown_T > 0:
            K = np.zeros((n_unknown_T, n_unknown_T))
            F = np.zeros(n_unknown_T)
            i0 = 0
            j0 = 0
            for i in range(len(self.spaces)):
                if unknown_T[i]:
                    F[i0] = self.FFIN_vector[i]
                    for j in range(len(self.spaces)):
                        if unknown_T:
                            K[i0][j0] = self.KFIN_matrix[i][j]
                            j0 += 1
                        else:
                            F[i0] -= self.KFIN_matrix[i][j]*self.TZ_vector[j]
                    i0 += 1

            T = np.linalg.solve(K, F)
            i0 = 0
            for i in range(len(self.spaces)):
                if unknown_T[i]:
                    self.TZ_vector[i] = T[i0]
                    i0 += 1

        # Calculate P
        for i in range(len(self.spaces)):
            if unknown_T[i]:
                self.PZ_vector[i] = 0
            else:
                self.PZ_vector[i] = - self.FFIN_vector[i]
                for j in range(len(self.spaces)):
                    self.PZ_vector[i] += self.KFIN_matrix[i][j] * \
                        self.TZ_vector[j]

    def _store_spaces_values(self, time_i):
        # Store TZ y PZ
        for i in range(len(self.spaces)):
            self.spaces[i].variable(
                "temperature").values[time_i] = self.TZ_vector[i]

            self.spaces[i].variable("Q_heating").values[time_i] = 0
            self.spaces[i].variable("Q_cooling").values[time_i] = 0

            if self.PZ_vector[i] > 0:
                self.spaces[i].variable(
                    "Q_heating").values[time_i] = self.PZ_vector[i]
            elif self.PZ_vector[i] < 0:
                self.spaces[i].variable(
                    "Q_cooling").values[time_i] = - self.PZ_vector[i]

        # Calculate hunmidity balance ??

    def _store_surfaces_values(self, time_i):
        # Calculate TS,
        self.TS_vector = np.matmul(self.KS_inv_matrix, self.FS_vector) - np.matmul(
            self.KS_inv_matrix, np.matmul(self.KSZ_matrix, self.TZ_vector))
        # Store TS
        for i in range(len(self.surfaces)):
            if not self.surfaces[i].is_virtual():
                if (self.sides[i] == 0):
                    self.surfaces[i].variable(
                        "T_s0").values[time_i] = self.TS_vector[i]
                else:
                    self.surfaces[i].variable(
                        "T_s1").values[time_i] = self.TS_vector[i]

    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        # When not converged .... ?

    def draw_pyvista(self, opacity=1, coordinate_system="building", space="all"):
        self._create_spaces_surfaces_list()
        plot = pv.Plotter()
        plot.add_axes_at_origin()
        for surface in self.surfaces:
            if space != "all":
                if surface.parameter("type").value == "Interior_surface" or surface.parameter("type").value == "Virtual_interior_surface":
                    is_my_space = surface.space(0).parameter(
                        "name").value == space or surface.space(1).parameter("name").value == space
                else:
                    is_my_space = surface.space().parameter("name").value == space

                if is_my_space:
                    opa = opacity
                else:
                    opa = opacity * 0.25
            else:
                opa = opacity
            polygon = surface.get_pyvista_polygon(coordinate_system)
            faces = [len(polygon), *range(0, len(polygon))]
            polygon_pyvista = pv.PolyData(polygon, faces)
            if surface.parameter("type").value == "Opening":
                color = "blue"
            elif surface.parameter("type").value == "Virtual_exterior_surface" or surface.parameter("type").value == "Virtual_interior_surface":
                color = "red"
                opa = opa*0.4
            elif surface.parameter("type").value == "Interior_surface":
                color = "green"
            elif surface.parameter("type").value == "Underground_surface":
                color = "brown"
            else:
                color = None

            plot.add_mesh(polygon_pyvista, color=color,
                          show_edges=True, opacity=opa)

        plot.show(jupyter_backend="client")
