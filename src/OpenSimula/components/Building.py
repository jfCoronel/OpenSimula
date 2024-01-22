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
                "rho", "short", self.sides[i])
            tau_matrix[i][i] = self.surfaces[i].radiant_property(
                "tau", "short", self.sides[i])
            # Negative (absortion)
            alpha_matrix[i][i] = -1 * \
                self.surfaces[i].radiant_property(
                    "alpha", "short", self.sides[i])
            area_matrix[i][i] = self.surfaces[i].net_area()

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
        for i in range(n):
            for j in range(m):
                dsr_dist_matrix[i][j] = self.spaces[j].dsr_dist_vector[i]
                ig_dist_matrix[i][j] = self.spaces[j].ig_dist_vector[i]

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
                "rho", "long", self.sides[i])
            tau_matrix[i][i] = self.surfaces[i].radiant_property(
                "tau", "long", self.sides[i])
            # Negative (absortion)
            alpha_matrix[i][i] = -1 * \
                self.surfaces[i].radiant_property(
                    "alpha", "long", self.sides[i])
            area_matrix[i][i] = self.surfaces[i].net_area()

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
        for i in range(n):
            for j in range(m):
                ig_dist_matrix[i][j] = self.spaces[j].ig_dist_vector[i]

        self.LWIG_matrix = np.matmul(aux_matrix, ig_dist_matrix)

        # Temperature matrix
        self.KTEMP_matrix = np.matmul(area_matrix, -1 * alpha_matrix) - \
            np.matmul(aux_matrix, np.matmul(self.ff_matrix, alpha_matrix))

        H_RD = 5.705  # 4*sigma*(293^3)
        self.KTEMP_matrix = H_RD * self.KTEMP_matrix

    def _create_K_matrices(self):
        n = len(self.surfaces)
        m = len(self.spaces)
        self.KS_matrix = np.copy(self.KTEMP_matrix)
        self.KSZ_matriz = np.zeros((n, m))

        # Complete KS_matriz
        for i in range(n):
            s_type = self.surfaces[i].parameter("type")
            if s_type == "Exterior_surface":
                self.KS_matrix[i][i] += self.surfaces[i].K
                for j in range(m):
                    if self.spaces[j] == self.surfaces[i].paremeter("space").component:
                        self.KSZ_matriz[i][j] = self.surfaces[i].net_area() *  self.surfaces[i].parameter("h_cv").value[self.sides[i]]
            elif s_type == "Underground_surface":
                self.KS_matrix[i][i] += self.surfaces[i].K 
                for j in range(m):
                    if self.spaces[j] == self.surfaces[i].paremeter("space").component:
                        self.KSZ_matriz[i][j] = self.surfaces[i].net_area() *  self.surfaces[i].parameter("h_cv").value
            elif s_type == "Interior_surface":
                self.KS_matrix[i][i] += self.surfaces[i].k[self.sides[i ]]
                for j in range(n):
                    if self.B_matrix[i][j] == 1:
                        self.KS_matrix[i][j] += self.surfaces[i].k_01
                for j in range(m):
                    if self.spaces[j] == self.surfaces[i].paremeter("spaces").component[self.sides[i]]:
                        self.KSZ_matriz[i][j] = self.surfaces[i].net_area() *  self.surfaces[i].parameter("h_cv").value[self.sides[i]]
                
