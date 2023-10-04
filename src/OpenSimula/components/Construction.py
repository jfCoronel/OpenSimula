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

    def pre_simulation(self, n_time_steps):
        # roots = self._B_roots_()
        self._calc_coef_()
        # print(roots)

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
        material = self.parameter("materials").component[layer]
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
            B = resis * math.sin(aux) / aux
            C = aux * math.sin(aux) / resis
        return np.matrix([[A, B], [C, A]])

    def _dH_Matrix_Layer_(self, s, layer):
        # Calculate dif H Matrix for one layer
        resis = self._resis_layer_(layer)
        tau = self._tau_layer_(layer)
        aux = math.sqrt(tau * s)

        if s == 0:
            L = self.parameter("thicknesses").value[layer]
            alpha = self._alpha_layer_(layer)
            A = L * L / (2 * alpha)
            B = (resis * L * L) * (6 * alpha)
            C = (L * L) * (alpha * resis)
        else:
            A = (tau / 2) * math.sin(aux) / aux
            B = (resis / 2) * (
                tau * math.sin(aux) / math.pow(aux, 3) - math.cos(aux) / s
            )
            C = (tau / (2 * resis)) * (math.sin(aux) / aux + math.cos(aux))
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

    def _B_roots_(self):
        def func(s):
            B = self._H_Matrix_(s)[0, 1]
            return B

        delta_s = 1e-5
        a = 1e-15
        B_a = func(a)
        b = delta_s
        roots = []
        while len(roots) <= 30:
            B_b = func(b)
            if B_a * B_b <= 0:  # Signo contrario o un cero
                bisec = brentq(func, a, b)
                roots.append(bisec)
            a = b
            B_a = B_b
            b = b + delta_s

        return roots

    def _calc_coef_(self):
        sum_resis = 0
        n = len(self.parameter("materials").value)
        dA = []
        dB = []
        dC = []
        for i in range(n):
            sum_resis = sum_resis + self._resis_layer_(i)
            L = self.parameter("thicknesses").value[i]
            dA.append(L * L / (2 * self._alpha_layer_(i)))
            dB.append(L * L * self._resis_layer_(i) / (6 * self._alpha_layer_(i)))
            dC.append(L * L / (self._resis_layer_(i) * self._alpha_layer_(i)))

        # dT = np.zeros((2, 2))
        # for i in range(n):
        #    P1 = np.eye(2)
        #    for j in range(i):
        #        P1 = np.dot(P1, np.matrix([[1, self._resis_layer_(j)], [0, 1]]))
        #    P2 = np.eye(2)
        #    for j in range(i + 1, n):
        #       P2 = np.dot(P2, np.matrix([[1, self._resis_layer_(j)], [0, 1]]))
        #    dT = dT + np.dot(
        #        P1, np.dot(np.matrix([[dA[i], dB[i]], [dC[i], dA[i]]]), P2)
        #    )

        dT = self._dH_Matrix_(0)
        C0 = 1 / sum_resis
        C1x = (dT[0, 0] * sum_resis - dT[0, 1]) / (sum_resis * sum_resis)
        C1y = (-dT[0, 1]) / (sum_resis * sum_resis)
        C1z = (dT[1, 1] * sum_resis - dT[0, 1]) / (sum_resis * sum_resis)
        print(C0)
        print(C1x, C1y, C1z)

        # e_coef
        roots = self._B_roots_()
        ex = []
        ey = []
        ez = []
        for root in roots:
            H = self._H_Matrix_(root)
            dH = self._dH_Matrix_(root)
            ex.append(H[0, 0] / (root * root * dH[0, 1]))
            ey.append(1 / (root * root * dH[0, 1]))
            ez.append(H[1, 1] / (root * root * dH[0, 1]))
        print(ex)
        print(ey)
        print(ez)
