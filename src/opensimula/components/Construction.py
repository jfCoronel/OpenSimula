from opensimula.Parameters import Parameter_component_list, Parameter_float_list
from opensimula.Component import Component


class Construction(Component):
    def __init__(self, project):
        Component.__init__(self, project)
        self.parameter("type").value = "Construction"
        self.parameter("name").value = "Construction_x"
        self.parameter("description").value = "Construction using layers of material"
        self.add_parameter(
            Parameter_float_list("solar_absortivity", [0.8, 0.8], "frac", 0, 1)
        )
        self.add_parameter(Parameter_component_list("materials", ["not_defined"]))
