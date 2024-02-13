from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_float, Parameter_float_list, Parameter_math_exp


class Glazing(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Glazing"
        self.parameter("description").value = "Glazing material."
        self.add_parameter(Parameter_float(
            "solar_tau", 0.85, "frac", min=0, max=1))
        self.add_parameter(Parameter_float_list(
            "solar_rho", [0.07, 0.07], "frac", min=0, max=1))
        self.add_parameter(Parameter_float_list(
            "g", [0.87, 0.87], "frac", min=0, max=1))
        self.add_parameter(Parameter_float_list(
            "lw_alpha", [0.84, 0.84], "frac", min=0, max=1))
        self.add_parameter(Parameter_float("U", 5.7, "W/m²K", min=0))
        self.add_parameter(Parameter_math_exp(
            "f_tau_nor", "1.3186 * cos_theta^3 - 3.5251 * cos_theta^2 + 3.2065 * cos_theta", "frac"))
        self.add_parameter(Parameter_math_exp(
            "f_1_minus_rho_nor", "1.8562 * cos_theta^3 - 4.4739 * cos_theta^2 + 3.6177 * cos_theta", "frac"))
