from opensimula.parameters import Parameter_component, Parameter_number
from opensimula.core import Component


class Construction(Component):
    def __init__(self):
        Component.__init__(self)
        self.add_parameter(Parameter_number(
            "solar_absortivity", 1, "frac", 0, 1))
        self.add_parameter(Parameter_component("material", "not_defined"))
