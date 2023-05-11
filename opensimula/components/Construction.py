from opensimula.parameters import Parameter_component_List, Parameter_float_List
from opensimula.Component import Component


class Construction(Component):
    def __init__(self):
        Component.__init__(self)
        self.parameter["type"].value = "Construction"
        self.parameter["name"].value = "Construction_x"
        self.parameter["description"].value = "Construction using layers of material"
        self.add_parameter(
            Parameter_float_List("solar_absortivity", [0.8, 0.8], "frac", 0, 1)
        )
        self.add_parameter(Parameter_component_List("materials", ["not_defined"]))
