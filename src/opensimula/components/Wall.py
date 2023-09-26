from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_options, Parameter_component
from OpenSimula.Variable import Variable


class Wall(Component):
    def __init__(self, project):
        Component.__init__(self, project)
        self.parameter("type").value = "Wall"
        self.parameter("name").value = "Wall_x"
        self.parameter("description").value = "enclosure of the building's spaces"

        self.add_parameter(Parameter_component("construction", ""))
        self.add_parameter(
            Parameter_options(
                "position", "exterior", ["exterior", "interior", "ground"]
            )
        )

    def pre_simulation(self, n_time_steps):
        self.del_all_variables()
        self.add_variable(Variable("t_sup1", n_time_steps, unit="°C"))
        self.add_variable(Variable("t_sup2", n_time_steps, unit="°C"))
