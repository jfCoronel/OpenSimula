import math
from scipy.integrate import quad
from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_float, Parameter_float_list, Parameter_math_exp, Parameter_math_exp_list


class Glazing(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Glazing"
        self.parameter("description").value = "Glazing material."
        self.add_parameter(Parameter_float(
            "solar_tau", 0.849, "frac", min=0, max=1))
        self.add_parameter(Parameter_float_list(
            "solar_rho", [0.077, 0.077], "frac", min=0, max=1))
        self.add_parameter(Parameter_float_list(
            "g", [0.867093, 0.867093], "frac", min=0, max=1))
        self.add_parameter(Parameter_float_list(
            "lw_epsilon", [0.837, 0.837], "frac", min=0, max=1))
        self.add_parameter(Parameter_float(
            "U", 5.686, "W/m²K", min=0))
        self.add_parameter(Parameter_math_exp(
            "f_tau_nor", "1.3186 * cos_theta^3 - 3.5251 * cos_theta^2 + 3.2065 * cos_theta", "frac"))
        f_rho = "1.8562 * cos_theta^3 - 4.4739 * cos_theta^2 + 3.6177 * cos_theta"
        self.add_parameter(Parameter_math_exp_list(
            "f_1_minus_rho_nor", [f_rho, f_rho], "frac"))

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._calc_diffuse_properties()
        self._calc_alpha_fractions()

    def _calc_diffuse_properties(self):
        def tau_integrand(theta):
            tau_n = self.parameter("solar_tau").value
            # variables dictonary
            var_dic = {"cos_theta": math.cos(theta)}
            f_tau = self.parameter("f_tau_nor").evaluate(var_dic)
            tau = tau_n*f_tau
            return 2*tau * math.sin(theta) * math.cos(theta)

        def rho_0_integrand(theta):
            rho_n = self.parameter("solar_rho").value[0]
            # variables dictonary
            var_dic = {"cos_theta": math.cos(theta)}
            f_rho = self.parameter("f_1_minus_rho_nor").evaluate(0, var_dic)
            rho = 1-(1-rho_n)*f_rho
            return 2*rho * math.sin(theta) * math.cos(theta)

        def rho_1_integrand(theta):
            rho_n = self.parameter("solar_rho").value[1]
            # variables dictonary
            var_dic = {"cos_theta": math.cos(theta)}
            f_rho = self.parameter("f_1_minus_rho_nor").evaluate(1, var_dic)
            rho = 1-(1-rho_n)*f_rho
            return 2*rho * math.sin(theta) * math.cos(theta)

        tau = quad(tau_integrand, 0, math.pi/2)[0]
        rho_0 = quad(rho_0_integrand, 0, math.pi/2)[0]
        rho_1 = quad(rho_1_integrand, 0, math.pi/2)[0]
        self.tau_solar_diffuse = tau
        self.rho_solar_diffuse = [rho_0, rho_1]
        self.alpha_solar_diffuse = [1-rho_0-tau, 1-rho_1-tau]

    def _calc_alpha_fractions(self):
        h_CR0 = 25
        h_CR1 = 3.6 + 4.1/0.837 * \
            self.parameter("lw_epsilon").value[1]  # UNE-EN 410:2011
        tau = self.parameter("solar_tau").value
        U = self.parameter("U").value
        if (U > 5):  # simple glazing calculations are inestable
            self.alpha_own_side_fraction = [0.5, 0.5]
        else:
            alpha_1 = 1 - tau - self.parameter("solar_rho").value[0]
            g_1 = self.parameter("g").value[0]
            alpha_11 = (g_1+alpha_1*U/h_CR1-alpha_1-tau)/(U/h_CR0+U/h_CR1-1)
            alpha_2 = 1 - tau - self.parameter("solar_rho").value[1]
            g_2 = self.parameter("g").value[1]
            alpha_22 = (g_2+alpha_2*U/h_CR1-alpha_2-tau)/(U/h_CR0+U/h_CR1-1)
            self.alpha_own_side_fraction = [alpha_11/alpha_1, alpha_22/alpha_2]

    def thermal_resistance(self):
        return (1/self.parameter("U").value - 1/25 - 1/(3.6 + 4.1/0.837 *
                                                        self.parameter("lw_epsilon").value[1]))  # UNE-EN 673:2011

    def radiant_property(self, prop, radiation_type, side, theta=0):
        if (radiation_type == "solar_diffuse"):
            if (prop == "rho"):
                return self.rho_solar_diffuse[side]
            elif (prop == "tau"):
                return self.tau_solar_diffuse
            elif (prop == "alpha"):
                return self.alpha_solar_diffuse[side]*self.alpha_own_side_fraction[side]
            elif (prop == "alpha_other_side"):
                return self.alpha_solar_diffuse[side]*(1-self.alpha_own_side_fraction[side])
        elif (radiation_type == "solar_direct"):
            # variables dictonary
            var_dic = {"cos_theta": math.cos(theta)}
            if (prop == "rho"):
                rho_n = self.parameter("solar_rho").value[side]
                f_rho = self.parameter(
                    "f_1_minus_rho_nor").evaluate(side, var_dic)
                return 1-(1-rho_n)*f_rho
            elif (prop == "tau"):
                return self.parameter("solar_tau").value * self.parameter("f_tau_nor").evaluate(var_dic)
            elif (prop == "alpha"):
                alpha = 1 - self.radiant_property("tau", radiation_type, side, theta) - \
                    self.radiant_property("rho", radiation_type, side, theta)
                return alpha * self.alpha_own_side_fraction[side]
            elif (prop == "alpha_other_side"):
                alpha = 1 - self.radiant_property("tau", radiation_type, side, theta) - \
                    self.radiant_property("rho", radiation_type, side, theta)
                return alpha * (1-self.alpha_own_side_fraction[side])
        elif (radiation_type == "long_wave"):
            if (prop == "rho"):
                return 1-self.parameter("lw_epsilon").value[side]
            elif (prop == "tau"):
                return 0
            elif (prop == "alpha"):
                return self.parameter("lw_epsilon").value[side]
        else:
            pass
