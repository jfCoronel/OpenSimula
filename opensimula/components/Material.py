from ..parameters import Parameter_boolean
from ..parameters import Parameter_number
from ..core import Component


class Material(Component):
    def __init__(self):
        Component.__init__(self)
        self.addParameter(Parameter_number("conductivity", 1, "W/(m·K)"))
        self.addParameter(Parameter_number("density", 1000, "kg/m³"))
        self.addParameter(Parameter_number("specific_heat", 1000, "J/(kg·K)"))
        self.addParameter(Parameter_number("thickness", 0.1, "m"))
        self.addParameter(Parameter_boolean("is_thermal_resistance", False))
        self.addParameter(Parameter_number(
            "thermal_resistance", 1, "(m²·K)/W"))
