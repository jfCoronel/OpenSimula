from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_options, Parameter_component
from OpenSimula.Variable import Variable


class Wall(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Wall"
        self.parameter("description").value = "enclosure of the building's spaces"

        self.add_parameter(Parameter_component("construction", ""))

    def pre_simulation(self, n_time_steps, delta_t):
        self.del_all_variables()
        self.add_variable(Variable("t_sup1", n_time_steps, unit="°C"))
        self.add_variable(Variable("t_sup2", n_time_steps, unit="°C"))
