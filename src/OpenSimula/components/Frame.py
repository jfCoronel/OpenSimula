from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_float, Parameter_float_list, Parameter_math_exp_list


class Frame(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Frame"
        self.parameter(
            "description").value = "Opening frame"

        self.add_parameter(Parameter_float_list(
            "solar_alpha", [0.85, 0.85], "frac", min=0, max=1))
        self.add_parameter(Parameter_float_list(
            "lw_epsilon", [0.9, 0.9], "frac", min=0, max=1))
        self.add_parameter(Parameter_float(
            "thermal_resistance", 0.2, "m²K/W", min=0))

    def radiant_property(self, prop, radiation_type, side, theta=0):
        if (radiation_type == "solar_diffuse" or radiation_type == "solar_direct"):
            if (prop == "rho"):
                return 1-self.parameter("solar_alpha").value[side]
            elif (prop == "tau"):
                return 0
            elif (prop == "alpha"):
                return self.parameter("solar_alpha").value[side]
            elif (prop == "alpha_other_side"):
                return 0
        elif (radiation_type == "long_wave"):
            if (prop == "rho"):
                return 1-self.parameter("lw_epsilon").value[side]
            elif (prop == "tau"):
                return 0
            elif (prop == "alpha"):
                return self.parameter("lw_epsilon").value[side]
