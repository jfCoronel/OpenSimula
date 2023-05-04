from opensimula.parameters import Parameter_string, Parameter_component
from opensimula.Component import Component


class Outdoor(Component):
    def __init__(self):
        Component.__init__(self)
        self.parameter["type"].value = "Outdoor"
        self.parameter["name"].value = "Outdoor_x"
        self.add_parameter(Parameter_string(
            "description", "Outdoor zone from a meteorological file"))
        self.add_parameter(Parameter_component("meteo_file", "not_defined"))

    def check(self):
        #
        self.parameter['meteo_file'].findComponent()
        if (self.parameter['meteo_file'].component == None):
            self.message("Error in component: " +
                         self.parameter["name"].value + ", type: " + self.parameter['type'].value)
            self.message(
                "   meteo_file: "+self.parameter["meteo_file"].value + " component not found")
            return 1
        else:
            return 0
