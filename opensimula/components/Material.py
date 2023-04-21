from opensimula.parameters import Parameter_boolean, Parameter_number
from opensimula.Component import Component


class Material(Component):
    def __init__(self):
        Component.__init__(self)
        self.parameter["type"].value = "Material"
        self.add_parameter(Parameter_number("conductivity", 1, "W/(m·K)"))
        self.add_parameter(Parameter_number("density", 1000, "kg/m³"))
        self.add_parameter(Parameter_number("specific_heat", 1000, "J/(kg·K)"))
        self.add_parameter(Parameter_number("thickness", 0.1, "m"))
        self.add_parameter(Parameter_boolean("simplified_definition", False))
        self.add_parameter(Parameter_number(
            "thermal_resistance", 1, "(m²·K)/W"))
        self.add_parameter(Parameter_number("weight", 10, "kg/m²"))
