from opensimula.Property_boolean import Property_boolean
from opensimula.Property_float import Property_float
from opensimula.Component import Component


class Material(Component):
    def __init__(self):
        Component.__init__(self)
        self.addProperty(Property_float("conductivity", 1))
        self.addProperty(Property_float("density", 1000))
        self.addProperty(Property_float("specific_heat", 1000))
        self.addProperty(Property_float("thickness", 0.1))
        self.addProperty(Property_boolean("is_thermal_resistance", False))
        self.addProperty(Property_float("thermal_resistance", 1))
