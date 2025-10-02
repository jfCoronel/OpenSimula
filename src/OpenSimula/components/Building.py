import numpy as np
from opensimula.Component import Component
from opensimula.Parameters import Parameter_float,Parameter_float_list
from opensimula.Message import Message

class Building(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Building"
        self.parameter("description").value = "Building description"
        # Parameters
        # X-axe vs East angle (0: X->East, 90: x->North)
        self.add_parameter(Parameter_float("azimuth", 0, "°", min=-180, max=180))
        self.add_parameter(Parameter_float_list("ref_point", [0,0,0], "m"))
        self.add_parameter(Parameter_float("initial_temperature", 20, "°C"))
        self.add_parameter(Parameter_float("initial_humidity", 7.3, "g/kg"))

    def check(self):
        errors = super().check()
        file_met = self.project().parameter("simulation_file_met").value
        if file_met == "not_defined":
            msg = Message(f"{self.parameter('name').value}, file_met must be defined in the project 'simulation_file_met'.", "ERROR")
            errors.append(msg)
        #self._create_lists_() # Es necesario crear las listas aquí ???
        return errors


    # _______________ pre_simulation _______________
    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._file_met_ = self.project().parameter("simulation_file_met").component
        self.props = self._sim_.props
        self._create_lists_()
        self._create_ff_matrix_() # View Factors ff_matrix
        self._create_B_matrix_() # Conectivity B_matrix
        self._create_SW_matrices_() # SWDIF_matrix, SWDIR_matrix, SWIG_matrix
        self._create_LW_matrices_() # LWIG_matrix, LWSUR_matrix
        self._create_K_matrices_() # KS_matrix, KS_inv_matrix, KSZ_matrix, KZS_matrix, KZ_matrix

    def _create_lists_(self):
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


    def _create_ff_matrix_(self):
        self.ff_matrix = np.zeros((self._n_surfaces, self._n_surfaces))
        i = 0
        for space in self.spaces:
            n_i = len(space.surfaces)
            self.ff_matrix[i : i + n_i, i : i + n_i] = space.ff_matrix
            i += n_i

    def _create_B_matrix_(self):
        self.B_matrix = np.zeros((self._n_surfaces, self._n_surfaces))
        for i in range(self._n_surfaces):
            for j in range(self._n_surfaces):
                if i != j and self.surfaces[i] == self.surfaces[j]:
                    self.B_matrix[i][j] = 1

    def _create_SW_matrices_(self):
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

    def _create_LW_matrices_(self):
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

    def _create_K_matrices_(self):
        self.KS_matrix = np.copy(-self.LWSUR_matrix)
        self.KSZ_matrix = np.zeros((self._n_surfaces, self._n_spaces))
        self.KZ_matrix = np.zeros((self._n_spaces, self._n_spaces))

        # KS_matriz, KSZ_matrix
        for i in range(self._n_surfaces):
            s_type = self.surfaces[i].parameter("type").value

            if s_type == "Building_surface":
                surface_type = self.surfaces[i].parameter("surface_type").value
                if surface_type == "EXTERIOR":
                    k = self.surfaces[i].k
                    k_01 = self.surfaces[i].k_01
                    self.KS_matrix[i][i] += k[1] - (k_01**2) / k[0]
                    for j in range(self._n_spaces):
                        if self.spaces[j] == self.surfaces[i].get_space():
                            self.KSZ_matrix[i][j] = (
                                self.surfaces[i].area
                                * self.surfaces[i].parameter("h_cv").value[self.sides[i]]
                            )
                elif surface_type == "UNDERGROUND":
                    k = self.surfaces[i].k
                    k_01 = self.surfaces[i].k_01
                    self.KS_matrix[i][i] += k[1]
                    for j in range(self._n_spaces):
                        if self.spaces[j] == self.surfaces[i].get_space():
                            self.KSZ_matrix[i][j] = (
                                self.surfaces[i].area
                                * self.surfaces[i].parameter("h_cv").value[0]
                            )
                elif surface_type == "INTERIOR":
                    k = self.surfaces[i].k
                    k_01 = self.surfaces[i].k_01
                    self.KS_matrix[i][i] += k[self.sides[i]]
                    for j in range(self._n_surfaces):
                        if self.B_matrix[i][j] == 1:
                            self.KS_matrix[i][j] += k_01
                    for j in range(self._n_spaces):
                        if (self.spaces[j]== self.surfaces[i].get_space(self.sides[i])):
                            self.KSZ_matrix[i][j] = (
                                self.surfaces[i].area
                                * self.surfaces[i].parameter("h_cv").value[self.sides[i]]
                            )
                elif surface_type == "VIRTUAL":
                    self.KS_matrix[i][i] += 1.0
                    for j in range(self._n_spaces):
                        if (self.spaces[j] == self.surfaces[i].parameter("spaces").component[self.sides[i]]):
                            self.KSZ_matrix[i][j] = 0
            elif s_type == "Opening":
                k = self.surfaces[i].k
                k_01 = self.surfaces[i].k_01
                if self.surfaces[i].is_exterior():
                    self.KS_matrix[i][i] += k[1] - (k_01**2) / k[0]
                    for j in range(self._n_spaces):
                        if (self.spaces[j] == self.surfaces[i].get_space()):
                            self.KSZ_matrix[i][j] = (
                                self.surfaces[i].area
                                * self.surfaces[i].parameter("h_cv").value[self.sides[i]]
                            )
                else:
                    self.KS_matrix[i][i] += k[self.sides[i]]
                    for j in range(self._n_surfaces):
                        if self.B_matrix[i][j] == 1:
                            self.KS_matrix[i][j] += k_01
                    for j in range(self._n_spaces):
                        if (self.spaces[j]== self.surfaces[i].get_space(self.sides[i])):
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
                self.spaces[i].parameter("volume").value * self.props["RHO_A"] * self.props["C_PA"]
                + self.spaces[i].parameter("furniture_weight").value
                * self.props["C_P_FURNITURE"]
            ) / self.project().parameter("time_step").value
            for j in range(self._n_surfaces):
                self.KZ_matrix[i][i] += self.KSZ_matrix[j][i]
       

    # _______________ pre_iteration _______________
    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        self._calculate_Q_igsw_(time_index)
        self._calculate_Q_iglw_(time_index)
        self._calculate_Q_dif_(time_index)
        self._calculate_FZ_vector_(time_index)
        self._update_K_matrices_(time_index)
        self._calculate_Q_dir_(time_index)
        self._calculate_FS_vector_(time_index)
        self._calculate_FIN_WS_matrices_(time_index)
        self._update_space_K_F_(time_index)

    def _calculate_Q_igsw_(self, time_i):
        E_ig = np.zeros(self._n_spaces)
        for i in range(self._n_spaces):
            E_ig[i] = self.spaces[i].variable("light_radiant").values[time_i]
        self.Q_igsw = np.matmul(self.SWIG_matrix, E_ig)

    def _calculate_Q_iglw_(self, time_i):
        E_ig = np.zeros(self._n_spaces)
        for i in range(self._n_spaces):
            E_ig[i] = (
                self.spaces[i].variable("people_radiant").values[time_i]
                + self.spaces[i].variable("other_gains_radiant").values[time_i]
            )
        self.Q_iglw = np.matmul(self.LWIG_matrix, E_ig)

    def _calculate_Q_dif_(self, time_i):
        E_dif = np.zeros(self._n_surfaces)
        for i in range(self._n_surfaces):
            s_type = self.surfaces[i].parameter("type").value
            if s_type == "Opening":
                if self.surfaces[i].is_exterior():
                    E_dif[i] = self.surfaces[i].variable("E_dif").values[time_i]
            elif s_type == "Building_surface":
                surface_type = self.surfaces[i].parameter("surface_type").value
                if surface_type == "EXTERIOR":
                    E_dif[i] = self.surfaces[i].variable("E_dif").values[time_i]
        self.Q_dif = np.matmul(self.SWDIF_matrix, E_dif)

    def _calculate_FZ_vector_(self, time_i):
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
                    self.spaces[i].parameter("volume").value * self.props["RHO_A"] * self.props["C_PA"]
                    + self.spaces[i].parameter("furniture_weight").value
                    * self.props["C_P_FURNITURE"]
                )
                * T_pre
                / self.project().parameter("time_step").value
            )
            self.FZ_vector[i] += (
                self.spaces[i].variable("infiltration_flow").values[time_i]
                * self.props["RHO_A"]
                * self.props["C_PA"]
                * self._file_met_.variable("temperature").values[time_i]
            )

    def _update_K_matrices_(self, time_i):
        self.KZFIN_matrix = self.KZ_matrix.copy()

        # Add infiltration
        for i in range(self._n_spaces):
            self.KZFIN_matrix[i][i] += (
                self.spaces[i].variable("infiltration_flow").values[time_i]
                * self.props["RHO_A"]
                * self.props["C_PA"]
            )
    
    def _calculate_Q_dir_(self, time_i):
        E_dir = np.zeros(self._n_spaces)
        for i in range(self._n_spaces):
            self.spaces[i].calculate_solar_direct(time_i)
            E_dir[i] = self.spaces[i].variable("solar_direct_gains").values[time_i]
        self.Q_dir = np.matmul(self.SWDIR_matrix, E_dir)

    def _calculate_FS_vector_(self, time_i):
        self.FS_vector = np.zeros(self._n_surfaces)

        for i in range(self._n_surfaces):
            # positive surface incoming
            Q_rad = -(self.Q_dir[i] + self.Q_dif[i] + self.Q_igsw[i] + self.Q_iglw[i])
            s_type = self.surfaces[i].parameter("type").value
            area = self.surfaces[i].area
            if s_type == "Building_surface":
                surface_type = self.surfaces[i].parameter("surface_type").value
                if surface_type == "EXTERIOR":
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
                elif surface_type == "UNDERGROUND":
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
                elif surface_type == "INTERIOR":
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
                elif surface_type == "VIRTUAL":
                    self.FS_vector[i] = 0.0
            elif s_type == "Opening":
                if self.surfaces[i].is_exterior():
                    q_sol_10 = -(self.Q_dir[i] + self.Q_dif[i]) / area
                    E_sol_int = q_sol_10 / self.surfaces[i].radiant_property("alpha", "solar_diffuse", 1)
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
                else:
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
                        f = - Q_rad
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
                        f = - Q_rad
                self.FS_vector[i] = f

    def _calculate_FIN_WS_matrices_(self, time_i): # Without Systems
        self.KFIN_WS_matrix = self.KZFIN_matrix - np.matmul(
            self.KZS_matrix, np.matmul(self.KS_inv_matrix, self.KSZ_matrix)
        )
        self.FFIN_WS_vector = self.FZ_vector - np.matmul(
            self.KZS_matrix, np.matmul(self.KS_inv_matrix, self.FS_vector)
        )

    # _______________ iteration _______________
    def iteration(self, time_index, date, daylight_saving, n_iter):
        super().iteration(time_index, date, daylight_saving, n_iter)
        self._update_space_K_F_(time_index)
        self._store_surfaces_values_(time_index)
        return True
    
    def _update_space_K_F_(self, time_i):
        for i in range(self._n_spaces):
            F_spaces = 0
            for j in range(self._n_spaces):
                if i != j:
                    F_spaces -= self.KFIN_WS_matrix[i][j]* self.spaces[j].variable("temperature").values[time_i]
            K_F={"K": self.KFIN_WS_matrix[i][i], "F":self.FFIN_WS_vector[i], "F_OS": F_spaces}
            self.spaces[i].update_K_F(K_F)
    
    def _store_surfaces_values_(self, time_i):
        # T_spaces
        T_spaces = np.zeros(self._n_spaces)
        for i in range(self._n_spaces):
            T_spaces[i] = self.spaces[i].variable("temperature").values[time_i]

        # Calculate TS,
        self.TS_vector = np.matmul(self.KS_inv_matrix, self.FS_vector) - np.matmul(self.KS_inv_matrix, np.matmul(self.KSZ_matrix,T_spaces))
        
        # Store TS
        for i in range(self._n_surfaces):
            if self.surfaces[i].parameter("type").value == "Building_surface" and self.surfaces[i].parameter("surface_type").value != "VIRTUAL":
                if self.sides[i] == 0:
                    self.surfaces[i].variable("T_s0").values[time_i] = self.TS_vector[i]
                else:
                    self.surfaces[i].variable("T_s1").values[time_i] = self.TS_vector[i]

    
    # _______________ post_iteration _______________
    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)