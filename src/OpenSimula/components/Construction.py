import math
import numpy as np
from scipy.optimize import brentq
from OpenSimula.Parameters import (
    Parameter_component_list,
    Parameter_float_list,
    Parameter_options,
)
from OpenSimula.Component import Component


class Construction(Component):
    def __init__(self, project):
        Component.__init__(self, project)
        self.parameter("type").value = "Construction"
        self.parameter("name").value = "Construction_x"
        self.parameter("description").value = "Construction using layers of material"
        self.add_parameter(
            Parameter_float_list("solar_absortivity", [0.8, 0.8], "frac", min=0, max=1)
        )
        self.add_parameter(Parameter_component_list("materials"))
        self.add_parameter(Parameter_float_list("thicknesses", [], "m", min=0))
        self.add_parameter(
            Parameter_options(
                "position", "exterior", ["exterior", "interior", "ground"]
            )
        )

    def check(self):
        errors = super().check()
        # Test if materials an thicknesses size are equals
        if len(self.parameter("materials").value) != len(
            self.parameter("thicknesses").value
        ):
            errors.append(
                f"Error: {self.parameter('name').value}, material and thicknesses parameters must have same length"
            )

        return errors

    ### Functions for Transfer Function Calculation

    def pre_simulation(self, n_time_steps, delta_t):
        self._calc_coef_(delta_t)

    def _resis_layer_(self, layer):
        material = self.parameter("materials").component[layer]
        resis_def = material.parameter("use_resistance").value
        if resis_def:
            return material.parameter("thermal_resistance").value
        else:
            return (
                self.parameter("thicknesses").value[layer]
                / material.parameter("conductivity").value
            )

    def _alpha_layer_(self, layer):
        material = self.parameter("materials").component[layer]
        resis_def = material.parameter("use_resistance").value
        if resis_def:
            return (
                self.parameter("thicknesses").value[layer]
                / material.parameter("thermal_resistance").value
            ) / (
                material.parameter("density").value
                * material.parameter("specific_heat").value
            )
        else:
            return material.parameter("conductivity").value / (
                material.parameter("density").value
                * material.parameter("specific_heat").value
            )

    def _tau_layer_(self, layer):
        L = self.parameter("thicknesses").value[layer]
        return L * L / self._alpha_layer_(layer)

    def _H_Matrix_Layer_(self, s, layer):
        # Calculate H Matrix for one layer
        resis = self._resis_layer_(layer)
        tau = self._tau_layer_(layer)
        aux = math.sqrt(tau * s)

        A = math.cos(aux)
        if s == 0:
            B = resis
            C = 0
        else:
            B = resis * math.sin(aux)
            C = -aux * math.sin(aux) / resis
        return np.matrix([[A, B], [C, A]])

    def _dH_Matrix_Layer_(self, s, layer):
        # Calculate dif H Matrix for one layer
        resis = self._resis_layer_(layer)
        tau = self._tau_layer_(layer)
        aux = math.sqrt(tau * s)

        if s == 0:
            A = tau / 2
            B = (resis * tau) / 6
            C = tau / resis
        else:
            A = (tau / 2) * math.sin(aux) / aux
            B = (resis / (2 * s)) * (math.sin(aux) / aux - math.cos(aux))
            C = (tau / (2 * resis)) * ((math.sin(aux) / aux) + math.cos(aux))
        return np.matrix([[A, B], [C, A]])

    def _H_Matrix_(self, s):
        H = np.eye(2)
        for i in range(len(self.parameter("materials").value)):
            H = np.dot(H, self._H_Matrix_Layer_(s, i))
        return H

    def _dH_Matrix_(self, s):
        H = np.zeros((2, 2))
        n = len(self.parameter("materials").value)
        for i in range(n):
            P1 = np.eye(2)
            for j in range(i):
                P1 = np.dot(P1, self._H_Matrix_Layer_(s, j))
            P2 = np.eye(2)
            for j in range(i + 1, n):
                P2 = np.dot(P2, self._H_Matrix_Layer_(s, j))
            H = H + np.dot(P1, np.dot(self._dH_Matrix_Layer_(s, i), P2))
        return H

    def _B_roots_(self, delta_t):
        def func(s):
            B = self._H_Matrix_(s)[0, 1]
            return B

        delta_s = 1e-5
        a = 1e-15
        B_a = func(a)
        b = delta_s
        roots = []
        exp = 1
        while exp > 1e-10:
            B_b = func(b)
            if B_a * B_b <= 0:  # Signo contrario o un cero
                bisec = brentq(func, a, b)
                roots.append(bisec)
                exp = math.exp(-bisec * delta_t)
            a = b
            B_a = B_b
            b = b + delta_s

        return roots

    def _calc_coef_(self, delta_t):
        min_coef = 1e-10
        dH_0 = self._dH_Matrix_(0)
        H_0 = self._H_Matrix_(0)
        C0 = H_0[0, 0] / H_0[0, 1]
        C1x = (dH_0[0, 0] * H_0[0, 1] - H_0[0, 0] * dH_0[0, 1]) / (
            H_0[0, 1] * H_0[0, 1]
        )
        C1y = (-dH_0[0, 1]) / (H_0[0, 1] * H_0[0, 1])
        C1z = (dH_0[1, 1] * H_0[0, 1] - dH_0[0, 1]) / (H_0[0, 1] * H_0[0, 1])

        # e_coef
        roots = self._B_roots_(delta_t)
        n_coef = len(roots) + 1
        ex = []
        ey = []
        ez = []
        h = []
        for root in roots:
            H = self._H_Matrix_(root)
            dH = self._dH_Matrix_(root)
            ex.append(H[0, 0] / (root * root * dH[0, 1]))
            ey.append(1 / (root * root * dH[0, 1]))
            ez.append(H[1, 1] / (root * root * dH[0, 1]))
            h.append(math.exp(-root * delta_t))
        d = [1, -h[0]]
        for i in range(1, len(roots)):
            u = [1, -h[i]]
            d = np.convolve(d, u)

        ox = []
        oy = []
        oz = []
        for i in range(1, n_coef):
            sum_exp_x = 0
            sum_exp_y = 0
            sum_exp_z = 0
            for j in range(len(roots)):
                exp = math.exp(-(i) * roots[j] * delta_t)
                sum_exp_x = sum_exp_x + ex[j] * exp
                sum_exp_y = sum_exp_y + ey[j] * exp
                sum_exp_z = sum_exp_z + ez[j] * exp
            ox.append(C1x + i * C0 * delta_t + sum_exp_x)
            oy.append(C1y + i * C0 * delta_t + sum_exp_y)
            oz.append(C1z + i * C0 * delta_t + sum_exp_z)

        ramp = [1 / delta_t, -2 / delta_t, 1 / delta_t]
        g = np.convolve(ramp, d)
        a = np.convolve(g, ox)
        b = np.convolve(g, oy)
        c = np.convolve(g, oz)
        # Cut d coefficients
        for i in range(len(d)):
            if math.fabs(d[i]) < min_coef:
                d = d[0 : i + 1]
                break
        # Cut a, b, c coefficients
        for i in range(len(a)):
            if (
                math.fabs(a[i]) < min_coef
                and math.fabs(b[i]) < min_coef
                and math.fabs(c[i]) < min_coef
            ):
                a = a[0 : i + 1]
                b = b[0 : i + 1]
                c = c[0 : i + 1]
                break

        print("a: ", a)
        print("b: ", b)
        print("c: ", c)
        print("d: ", d)
