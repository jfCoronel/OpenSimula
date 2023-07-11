from opensimula.Parameters import Parameter_boolean, Parameter_float
from opensimula.Component import Component


class Material(Component):
    def __init__(self):
        Component.__init__(self)
        self.parameter["type"].value = "Material"
        self.parameter["name"].value = "Material_x"
        self.parameter["description"].value = "Material layer properties"
        self.add_parameter(Parameter_float("conductivity", 1, "W/(m·K)"))
        self.add_parameter(Parameter_float("density", 1000, "kg/m³"))
        self.add_parameter(Parameter_float("specific_heat", 1000, "J/(kg·K)"))
        self.add_parameter(Parameter_float("thickness", 0.1, "m"))
        self.add_parameter(Parameter_boolean("simplified_definition", False))
        self.add_parameter(Parameter_float("thermal_resistance", 1, "(m²·K)/W"))
        self.add_parameter(Parameter_float("weight", 10, "kg/m²"))
