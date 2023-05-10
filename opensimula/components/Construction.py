from opensimula.parameters import Parameter_component_List, Parameter_number
from opensimula.Component import Component


class Construction(Component):
    def __init__(self):
        Component.__init__(self)
        self.parameter["type"].value = "Construction"
        self.parameter["type"].name = "Construction_x"
        self.add_parameter(Parameter_number("solar_absortivity", 1, "frac", 0, 1))
        self.add_parameter(Parameter_component_List("materials", ["not_defined"]))
