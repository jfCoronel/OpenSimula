from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_component, Parameter_float
from OpenSimula.Variable import Variable
import numpy as np


class Building(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Building"
        self.parameter("description").value = "Building description"
        # Parameters
        self.add_parameter(Parameter_component("file_met", "not_defined"))
        self.add_parameter(Parameter_float(
            "albedo", 0.3, "frac", min=0, max=1))
        self.add_parameter(Parameter_float(
            "initial_temperature", 20, "ºC"))

        # Variables

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._file_met = self.parameter("file_met").component
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
        self._ff_matrix = np.zeros((n, n))
        i = 0
        for space in self.spaces:
            n_i = len(space.surfaces)
            self.ff_matrix[i:i+n_i, i:i + n_i] = space._ff_matrix
            i += n_i

    def _create_B_matrix(self):
        n = len(self.surfaces)
        self._B_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i != j and self.surfaces[i] == self.surfaces[j]:
                    self._B_matrix[i][j] = 1

    def _create_SW_matrices(self):
        n = len(self.surfaces)
        self._SWRM_matrix = np.identity(n)
        rho_matrix = np.zeros((n, n))
        tau_matrix = np.zeros((n, n))
        alpha_matrix = np.zeros((n, n))
        area_matrix = np.zeros((n, n))

        for i in range(n):
            rho_matrix[i][i] = self.surfaces[i].radiant_property(
                "rho", "short", self.sides[i])
            tau_matrix[i][i] = self.surfaces[i].radiant_property(
                "tau", "short", self.sides[i])
            # Negative (absortion)
            alpha_matrix[i][i] = -1 * \
                self.surfaces[i].radiant_property(
                    "alpha", "short", self.sides[i])
            area_matrix[i][i] = self.surfaces[i].net_area()

        self._SWRM_matrix = self._SWRM_matrix - \
            np.matmul(self._ff_matrix, rho_matrix) - \
            np.matmul(self._ff_matrix, np.matmul(tau_matrix, self._B_matrix))

        self._SWRM_matrix = np.linalg.inv(self._SWRM_matrix)
        aux_matrix = np.matmul(area_matrix, np.matmul(
            alpha_matrix, self._SWRM_matrix))
        self._SWDIF_matrix = np.matmul(aux_matrix, np.matmul(
            self._ff_matrix, tau_matrix))  # SW Solar Diffuse

        m = len(self.spaces)
        dsr_dist_matrix = np.zeros((n, m))
        ig_dist_matrix = np.zeros((n, m))
        for i in range(n):
            for j in range(m):
                dsr_dist_matrix[i][j] = self.spaces[j]._dsr_dist_vector[i]
                ig_dist_matrix[i][j] = self.spaces[j]._ig_dist_vector[i]

        self._SWDIR_matrix = np.matmul(aux_matrix, dsr_dist_matrix)
        self._SWIG_matrix = np.matmul(aux_matrix, ig_dist_matrix)

    def _create_LW_matrices(self):
        n = len(self.surfaces)
        self._LWRM_matrix = np.identity(n)
        rho_matrix = np.zeros((n, n))
        tau_matrix = np.zeros((n, n))
        alpha_matrix = np.zeros((n, n))
        area_matrix = np.zeros((n, n))

        for i in range(n):
            rho_matrix[i][i] = self.surfaces[i].radiant_property(
                "rho", "long", self.sides[i])
            tau_matrix[i][i] = self.surfaces[i].radiant_property(
                "tau", "long", self.sides[i])
            # Negative (absortion)
            alpha_matrix[i][i] = -1 * \
                self.surfaces[i].radiant_property(
                    "alpha", "long", self.sides[i])
            area_matrix[i][i] = self.surfaces[i].net_area()

        self._LWRM_matrix = self._LWRM_matrix - \
            np.matmul(self._ff_matrix, rho_matrix) - \
            np.matmul(self._ff_matrix, np.matmul(tau_matrix, self._B_matrix))

        self._LWRM_matrix = np.linalg.inv(self._LWRM_matrix)
        aux_matrix = np.matmul(area_matrix, np.matmul(
            alpha_matrix, self._LWRM_matrix))
        self._LWEXT_matrix = np.matmul(aux_matrix, np.matmul(
            self._ff_matrix, tau_matrix))  # Exterior irradiations

        m = len(self.spaces)
        ig_dist_matrix = np.zeros((n, m))
        for i in range(n):
            for j in range(m):
                ig_dist_matrix[i][j] = self.spaces[j]._ig_dist_vector[i]

        self._LWIG_matrix = np.matmul(aux_matrix, ig_dist_matrix)

        # Temperature matrix
        self._KTEMP_matrix = np.matmul(area_matrix, -1 * alpha_matrix) - \
            np.matmul(aux_matrix, np.matmul(self._ff_matrix, alpha_matrix))

        LINEAR_CTE = 4 * 5.67E-8 * (293**3)
        self._KTEMP_matrix = LINEAR_CTE * self._KTEMP_matrix

    def _create_K_matrices(self):
        n = len(self.surfaces)
        m = len(self.spaces)
        self._KS_matrix = np.copy(self._KTEMP_matrix)
        self._KSZ_matriz = np.zeros((n, m))

        for i in range(n):
            surface = self._surfaces[i]["comp"]
            location = surface.parameter("location").value
            if (location == "INTERIOR"):
                self._KS_matrix[i][i] += surface._k_1
                self._KS_matrix[i][self._surfaces[i]
                                   ["i_adjacent"]] += surface._k_01
            else:
                self._KS_matrix[i][i] += surface._K
