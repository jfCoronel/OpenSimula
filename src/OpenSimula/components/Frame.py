from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_float, Parameter_float_list, Parameter_math_exp_list


class Frame(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Frame"
        self.parameter(
            "description").value = "Window frame"

        self.add_parameter(Parameter_float_list(
            "solar_alpha", [0.85, 0.85], "frac", min=0, max=1))
        self.add_parameter(Parameter_float_list(
            "lw_alpha", [0.9, 0.9], "frac", min=0, max=1))
        self.add_parameter(Parameter_float(
            "thermal_resistance", 0.2, "m²K/W", min=0))
