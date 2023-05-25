from opensimula.Component import Component
from opensimula.parameters import Parameter_component_list
from opensimula.variables import Variable


class Space(Component):
    def __init__(self):
        Component.__init__(self)
        self.parameter["type"].value = "Space"
        self.parameter["name"].value = "Space_x"
        self.parameter["description"].value = "Indoor building space"
        self.add_parameter(Parameter_component_list("walls", ["not_defined"]))

    def check(self):
        n_errors = super().check()
        return n_errors

    def pre_simulation(self, n_time_steps):
        self.del_all_variables()
        self.add_variable(Variable("temperature", n_time_steps, unit="°C"))
        self.add_variable(Variable("rel_humidity", n_time_steps, unit="%"))

    def iteration(self, time_index, date):
        return True
