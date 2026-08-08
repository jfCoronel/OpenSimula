from opensimula.Parameters import Parameter_boolean, Parameter_float
from opensimula.Component import Component


class Material(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Material"
        self.parameter("description").value = "Material layer properties"
        self.add_parameter(Parameter_float("conductivity", 1, "W/(m·K)", min=0))
        self.add_parameter(Parameter_float("density", 1000, "kg/m³", min=0.001))
        self.add_parameter(Parameter_float("specific_heat", 1000, "J/(kg·K)", min=0.001))
        self.add_parameter(Parameter_boolean("use_resistance", False))
        self.add_parameter(Parameter_float("thermal_resistance", 1, "(m²·K)/W", min=0))

    def thermal_diffusivity(self):
        """Returns thermal diffusivity α = k / (ρ · cp) in m²/s"""
        k = self.parameter("conductivity").value
        rho = self.parameter("density").value
        cp = self.parameter("specific_heat").value
        return k / (rho * cp)
