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
        self._create_source_lists_() # surfaces with a heat source plane

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

        SWR_matrix = _radiosity_inverse_(SWR_matrix)
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

        LWR_matrix = _radiosity_inverse_(LWR_matrix)
        aux_matrix = np.matmul(area_matrix, np.matmul(alpha_matrix,LWR_matrix))

        ig_dist_matrix = np.zeros((self._n_surfaces, self._n_spaces))
        i_glob = 0
        for j in range(self._n_spaces):
            for i in range(len(self.spaces[j].surfaces)):
                ig_dist_matrix[i_glob][j] = self.spaces[j].ig_dist_vector[i]
                i_glob += 1

        self.LWIG_matrix = np.matmul(aux_matrix, ig_dist_matrix)
        self.LWAUX_matrix = aux_matrix  # absorbed by each surface per incident radiation
        self._radiant_cache = {}

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
                                * self.surfaces[i].parameter("h_cv").value[self.sides[i]]
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
        self._time_i_ = time_index
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
    
    # _______________ radiant heat of systems _______________
    def radiant_response(self, space, distribution=None):
        """Response of the building to 1 W of radiant heat of a system in a space.

        The radiation is distributed over the surfaces of the space (by area, or among
        floor, ceiling and walls with the given fractions and by area within each group),
        reflected and absorbed with the long-wave radiosity of the building, and the
        surfaces give part of it to the air of the spaces in the same time step.

        Args:
            space (Space): space of the system.
            distribution (list, optional): fractions to the floor, ceiling and walls.

        Returns:
            tuple: (fraction to the air of the space, heat absorbed by each surface per W
                (with the sign of the internal gains), heat to the air of each space per W).
        """
        key = (space.parameter("name").value, tuple(distribution) if distribution else None)
        if key in self._radiant_cache:
            return self._radiant_cache[key]
        j = self.spaces.index(space)
        offset = sum(len(self.spaces[k].surfaces) for k in range(j))
        n = len(space.surfaces)
        areas = np.array([s.area for s in space.surfaces])
        if distribution:
            groups = np.array([0 if space.surfaces[i].orientation_angle("altitude", space.sides[i]) == 90
                               else 1 if space.surfaces[i].orientation_angle("altitude", space.sides[i]) == -90
                               else 2 for i in range(n)])
            fractions = np.array([distribution[g] if areas[groups == g].sum() > 0 else 0.0
                                  for g in range(3)], dtype=float)
            fractions = fractions / fractions.sum() if fractions.sum() > 0 else np.ones(3) / 3
            local = np.array([fractions[groups[i]] / areas[groups == groups[i]].sum() for i in range(n)])
        else:
            local = np.full(n, 1 / areas.sum())
        dist = np.zeros(self._n_surfaces)
        dist[offset:offset + n] = local
        absorbed = np.matmul(self.LWAUX_matrix, dist)
        to_air = -np.matmul(self.KZS_matrix, np.matmul(self.KS_inv_matrix, absorbed))
        result = (float(to_air[j]), absorbed, to_air)
        self._radiant_cache[key] = result
        return result

    def _radiant_systems_(self):
        """Radiant heat of the systems in this iteration: [(space index, W, response)]."""
        sources = []
        for j, space in enumerate(self.spaces):
            for Q, distribution in space.radiant_systems.values():
                if Q != 0:
                    sources.append((j, Q, self.radiant_response(space, distribution)))
        return sources

    # _______________ heat source planes (active layers) _______________
    def _create_source_lists_(self):
        """Surfaces with a heat source plane and the rows of their sides in KS."""
        self.source_surfaces = []
        self._source_rows_ = {}
        for i, surface in enumerate(self.surfaces):
            if surface.parameter("type").value == "Building_surface" and surface.has_source():
                if surface not in self._source_rows_:
                    self.source_surfaces.append(surface)
                    self._source_rows_[surface] = [None, None]
                self._source_rows_[surface][self.sides[i]] = i
        self._source_cache = {}

    def source_response(self, surface):
        """Response of the building to 1 W/m² of the heat source plane of a surface.

        Returns:
            tuple: (term of the surface equations, KS·T_s = FS − KSZ·T_z, per W/m²;
                heat to the air of each space per W/m², in the same time step).
        """
        if surface in self._source_cache:
            return self._source_cache[surface]
        s_0, s_1 = surface._construction_.get_source_A()
        area = surface.area
        g = np.zeros(self._n_surfaces)
        row_0, row_1 = self._source_rows_[surface]
        surface_type = surface.parameter("surface_type").value
        if row_1 is not None:
            g[row_1] = -area * s_1
            if surface_type == "EXTERIOR":  # through T_s0 = (f_0 − k_01·T_s1)/k_0
                g[row_1] += area * s_0 * surface.k_01 / surface.k[0]
        if row_0 is not None:
            g[row_0] = -area * s_0
        to_air = -np.matmul(self.KZS_matrix, np.matmul(self.KS_inv_matrix, g))
        self._source_cache[surface] = (g, to_air)
        return self._source_cache[surface]

    def _sources_(self, exclude=()):
        """Heat source planes on in this iteration: [(surface, W/m², response)]."""
        return [(s, s.source_flux, self.source_response(s)) for s in self.source_surfaces
                if s.source_flux != 0 and s not in exclude]

    def _source_FS_(self, exclude=()):
        FS = np.zeros(self._n_surfaces)
        for _, q, (g, _) in self._sources_(exclude):
            FS += g * q
        return FS

    def source_temperatures(self, surfaces, q_source, space, T_space):
        """Temperature of the source planes of some surfaces, all with the source flux
        q_source, with the air of a space at T_space (the other spaces and sources as
        they are in this iteration).

        Args:
            surfaces (list): Building_surface with source.
            q_source (float): flux of their sources (W/m²).
            space (Space): space whose air temperature is given.
            T_space (float): its air temperature (°C).

        Returns:
            numpy.ndarray: temperature of the source plane of each surface (°C).
        """
        time_i = self._time_i_
        T_spaces = np.array([sp.variable("temperature").values[time_i] for sp in self.spaces])
        T_spaces[self.spaces.index(space)] = T_space
        FS = self.FS_vector + self._radiant_FS_() + self._source_FS_(exclude=surfaces)
        for surface in surfaces:
            FS += self.source_response(surface)[0] * q_source
        TS = np.matmul(self.KS_inv_matrix, FS - np.matmul(self.KSZ_matrix, T_spaces))
        result = []
        for surface in surfaces:
            row_0, row_1 = self._source_rows_[surface]
            T_1 = TS[row_1] if row_1 is not None else None
            surface_type = surface.parameter("surface_type").value
            if surface_type == "EXTERIOR":
                s_0 = surface._construction_.get_source_A()[0]
                T_0 = (surface.f_0 - surface.area * s_0 * q_source - surface.k_01 * T_1) / surface.k[0]
            elif surface_type == "UNDERGROUND":
                T_0 = surface.variable("T_s0").values[time_i]
            else:
                T_0 = TS[row_0] if row_0 is not None else None
            if T_0 is None or T_1 is None:  # interior surface with a side out of the building
                raise ValueError(f"{surface.parameter('name').value}: both sides must be in the building")
            result.append(surface.source_temperature(T_0, T_1, q_source))
        return np.array(result)

    def _radiant_FS_(self):
        Q_radiant = np.zeros(self._n_surfaces)
        for _, Q, (_, absorbed, _) in self._radiant_systems_():
            Q_radiant += absorbed * Q
        return Q_radiant

    def _update_space_K_F_(self, time_i):
        sources = self._radiant_systems_()
        heat_sources = self._sources_()
        for i in range(self._n_spaces):
            F_spaces = 0
            # radiant heat of the systems of other spaces that reaches this one (that of
            # its own systems is given by them)
            for j, Q, (_, _, to_air) in sources:
                if j != i:
                    F_spaces += to_air[i] * Q
            # heat source planes, except those of the systems of this space
            for surface, q, (_, to_air) in heat_sources:
                if getattr(surface, "source_space", None) is not self.spaces[i]:
                    F_spaces += to_air[i] * q
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

        # radiant heat of the systems, absorbed by the surfaces
        Q_radiant = self._radiant_FS_()
        FS = self.FS_vector + Q_radiant + self._source_FS_()
        if np.any(Q_radiant != 0) or getattr(self, "_radiant_stored_", False):
            # long-wave radiant heat of the surfaces: internal gains and systems
            for i in range(self._n_surfaces):
                surface = self.surfaces[i]
                if surface.parameter("type").value == "Building_surface" and \
                        surface.parameter("surface_type").value == "VIRTUAL":
                    continue
                side = "q_lwig0" if self.sides[i] == 0 else "q_lwig1"
                surface.variable(side).values[time_i] = -(self.Q_iglw[i] + Q_radiant[i]) / surface.area
            self._radiant_stored_ = bool(np.any(Q_radiant != 0))

        # Calculate TS,
        self.TS_vector = np.matmul(self.KS_inv_matrix, FS) - np.matmul(self.KS_inv_matrix, np.matmul(self.KSZ_matrix,T_spaces))
        
        # Store TS
        # Openings too: their T_s1 (and, for interior ones, T_s0) is only known here,
        # and Opening.post_iteration() computes T_s0 and the heat fluxes from it.
        for i in range(self._n_surfaces):
            surface = self.surfaces[i]
            s_type = surface.parameter("type").value
            if s_type == "Opening" or (
                s_type == "Building_surface" and surface.parameter("surface_type").value != "VIRTUAL"
            ):
                if self.sides[i] == 0:
                    self.surfaces[i].variable("T_s0").values[time_i] = self.TS_vector[i]
                else:
                    self.surfaces[i].variable("T_s1").values[time_i] = self.TS_vector[i]

    
    # _______________ post_iteration _______________
    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)


def _radiosity_inverse_(matrix):
    """Inverse of a radiosity matrix (I - F·rho - F·tau·B).

    In a closed enclosure whose surfaces neither absorb nor transmit (rho = 1, e.g. surfaces
    with solar absorptance or emissivity 0, as in the ASHRAE 140 ground-coupling cases) the
    matrix is singular, since the rows of F sum to 1. Nothing is absorbed then, so any
    generalised inverse gives the same (zero) absorbed radiation: use the pseudo-inverse.
    """
    try:
        return np.linalg.inv(matrix)
    except np.linalg.LinAlgError:
        return np.linalg.pinv(matrix)
