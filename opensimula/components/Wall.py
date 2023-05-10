from opensimula.Component import Component
from opensimula.parameters import Parameter_options, Parameter_component
from opensimula.variables import Variable


class Wall(Component):
    def __init__(self):
        Component.__init__(self)
        self.parameter["type"].value = "Wall"
        self.parameter["name"].value = "Wall_x"
        self.add_parameter(Parameter_component("construction", ""))
        self.add_parameter(
            Parameter_options(
                "position", "exterior", ["exterior", "interior", "ground"]
            )
        )

    def check(self):
        # TODO check construction
        return 0

    def pre_simulation(self, n_time_steps):
        self.add_variable(Variable("t_sup1", n_time_steps, unit="°C"))
        self.add_variable(Variable("t_sup2", n_time_steps, unit="°C"))

    def iteration(self, time_index, date):
        return True
