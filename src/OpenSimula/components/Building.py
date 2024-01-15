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

        # Variables

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._create_spaces_surfaces_list()
        self._create_ff_matrix()
        self._create_B_matrix()
        self._create_SW_matrices()

    def _create_spaces_surfaces_list(self):
        project_spaces_list = self.project().component_list(type="Space")
        self._spaces = []
        self._surfaces = []
        for space in project_spaces_list:
            if (space.parameter("building").component == self):
                space_dic = {"comp": space,
                             "floor_area": space.parameter("floor_area").value,
                             "volume": space.parameter("volume").value,
                             "n_surfaces": len(space._surfaces)
                             }
                self._spaces.append(space_dic)
                self._surfaces = self._surfaces + space._surfaces

    def _create_ff_matrix(self):
        n = len(self._surfaces)
        self._ff_matrix = np.zeros((n, n))
        i = 0
        for space in self._spaces:
            self._ff_matrix[i:i+space["n_surfaces"], i:i +
                            space["n_surfaces"]] = space["comp"]._ff_matrix
            i += space["n_surfaces"]

    def _create_B_matrix(self):
        n = len(self._surfaces)
        self._B_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i != j and self._surfaces[i]["comp"] == self._surfaces[j]["comp"]:
                    self._B_matrix[i][j] = 1

    def _create_SW_matrices(self):
        n = len(self._surfaces)
        self._SWRM_matrix = np.identity(n)
        rho_matrix = np.zeros((n, n))
        tau_matrix = np.zeros((n, n))

        for i in range(n):
            rho_matrix[i][i] = self._surfaces[i]["rho_sw"]
            tau_matrix[i][i] = self._surfaces[i]["tau_sw"]
        self._SWRM_matrix = self._SWRM_matrix - \
            np.matmul(self._ff_matrix, rho_matrix) - \
            np.matmul(self._ff_matrix, np.matmul(tau_matrix, self._B_matrix))

        self._SWRM_matrix = np.linalg.inv(self._SWRM_matrix)
        self._SWDIF_matrix = np.matmul(
            self._SWRM_matrix, np.matmul(self._ff_matrix, tau_matrix))

        m = len(self._spaces)
        dsr_dist_matrix = np.zeros((n, m))
        ig_dist_matrix = np.zeros((n, m))
        for i in range(n):
            for j in range(m):
                dsr_dist_matrix[i][j] = self._spaces[j]["comp"]._dsr_dist_vector[i]
                ig_dist_matrix[i][j] = self._spaces[j]["comp"]._ig_dist_vector[i]

        self._SWDIR_matrix = np.matmul(self._SWRM_matrix, dsr_dist_matrix)
        self._SWIG_matrix = np.matmul(self._SWRM_matrix, ig_dist_matrix)
