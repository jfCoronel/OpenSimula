from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_component_list
from OpenSimula.Variable import Variable


class Space(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Space"
        self.parameter("description").value = "Indoor building space"
        # Parameters
        self.add_parameter(Parameter_component_list("walls"))

        # Variables
        self.add_variable(Variable("temperature", unit="°C"))
        self.add_variable(Variable("rel_humidity", unit="%"))

    def pre_simulation(self, n_time_steps, delta_t):
       super().pre_simulation(n_time_steps,delta_t)
