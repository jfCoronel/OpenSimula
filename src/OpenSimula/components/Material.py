from OpenSimula.Parameters import Parameter_boolean, Parameter_float
from OpenSimula.Component import Component


class Material(Component):
    def __init__(self, project):
        Component.__init__(self, project)
        self.parameter("type").value = "Material"
        self.parameter("name").value = "Material_x"
        self.parameter("description").value = "Material layer properties"
        self.add_parameter(Parameter_float("conductivity", 1, "W/(m·K)", min=0))
        self.add_parameter(Parameter_float("density", 1000, "kg/m³", min=0))
        self.add_parameter(Parameter_float("specific_heat", 1000, "J/(kg·K)", min=0))
        self.add_parameter(Parameter_boolean("use_resistance", False))
        self.add_parameter(Parameter_float("thermal_resistance", 1, "(m²·K)/W"))
