from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_options, Parameter_component
from OpenSimula.Variable import Variable


class Wall(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        # Parameters
        self.parameter("type").value = "Wall"
        self.parameter("description").value = "enclosure of the building's spaces"
        self.add_parameter(Parameter_component("construction", ""))
        # Variables
        self.add_variable(Variable("T_sup1","°C"))
        self.add_variable(Variable("T_sup2","°C"))

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps,delta_t)
