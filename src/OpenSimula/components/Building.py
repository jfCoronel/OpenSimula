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
            self._ff_matrix[i:i+space["n_surfaces"],i:i+space["n_surfaces"]] = space["comp"]._ff_matrix
            i += space["n_surfaces"]
            

    