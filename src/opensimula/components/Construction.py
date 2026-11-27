import math
import numpy as np
from scipy.optimize import brentq
from opensimula.Message import Message
from opensimula.Parameters import Parameter_component_list, Parameter_float_list, Parameter_int
from opensimula.Component import Component

class Construction(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Construction"
        self.parameter(
            "description").value = "Construction using layers of material"

        self.add_parameter(Parameter_float_list(
            "solar_alpha", [0.8, 0.8], "frac", min=0, max=1))
        self.add_parameter(Parameter_float_list(
            "lw_epsilon", [0.9, 0.9], "frac", min=0, max=1))
        self.add_parameter(Parameter_component_list(
            "materials", [], ["Material"]))
        self.add_parameter(Parameter_float_list("thicknesses", [], "m", min=0))
        # active layer: a heat source (e.g. the pipes of a radiant floor) in the plane
        # after this layer (1 to number of layers - 1, from side 0); 0: none
        self.add_parameter(Parameter_int("source_layer", 0, "", min=0))

    def check(self):
        errors = super().check()
        # Test if materials an thicknesses size are equals
        if len(self.parameter("materials").value) != len(self.parameter("thicknesses").value):
            msg =f"Error: {self.parameter('name').value}, material and thicknesses parameters must have same length"
            errors.append(Message(msg, "error"))
        k = self.parameter("source_layer").value
        if k > 0 and k >= len(self.parameter("materials").value):
            msg = (f"Error: {self.parameter('name').value}, source_layer must be between 1 and the "
                   "number of layers - 1 (the source is in the plane after that layer)")
            errors.append(Message(msg, "ERROR"))
        return errors

    def has_source(self):
        """True if the construction has an active layer (a heat source plane)."""
        return self.parameter("source_layer").value > 0

    def add_exterior_layer(self, material_name, thickness):
        """Add a new exterior layer (at index 0) to the construction.

        Args:
            material_name (str): Name of the material component to add
            thickness (float): Thickness of the layer in meters
        """
        # Copies, because the getter returns the parameter own list and
        # inserting into it would modify the construction before validation
        materials = list(self.parameter("materials").value)
        thicknesses = list(self.parameter("thicknesses").value)
        materials.insert(0, material_name)
        thicknesses.insert(0, thickness)
        self.parameter("materials").value = materials
        self.parameter("thicknesses").value = thicknesses
        if self.has_source():  # the source stays in the same plane
            self.parameter("source_layer").value = self.parameter("source_layer").value + 1

    # Functions for Transfer Function Calculation

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._calc_trans_fun_(delta_t)

    def get_T_step_fluxes(self):
        n_q = len(self._coef_Q)
        n_t = len(self._coef_T_a)
        Q_old_1 = np.zeros(n_q)
        Q_old_2 = np.zeros(n_q)
        T_old = np.ones(n_t)
        # T_old[0] = 0
        q_2 = 1
        Q_2 = []
        Q_1 = []
        n = 0
        while n <= 1 or math.fabs(q_2) > 1e-15:
            q_2 = np.dot(
                self._coef_T_a - self._coef_T_b, T_old.transpose()
            ) - np.dot(self._coef_Q, Q_old_2.transpose())
            q_1 = np.dot(
                self._coef_T_b - self._coef_T_c, T_old.transpose()
            ) - np.dot(self._coef_Q, Q_old_1.transpose())
            Q_2.append(q_2)
            Q_1.append(q_1)
            Q_old_2 = np.roll(Q_old_2, 1)
            Q_old_2[0] = 0
            Q_old_2[1] = q_2
            Q_old_1 = np.roll(Q_old_1, 1)
            Q_old_1[0] = 0
            Q_old_1[1] = q_1
            T_old = np.roll(T_old, 1)
            T_old[0] = 0
            n = n + 1
        return (Q_1, Q_2)

    def thermal_resistance(self):
        resis_tot = 0
        for i in range(len(self.parameter("materials").value)):
            resis_tot = resis_tot + self._resis_layer_(i)
        return resis_tot

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

    def get_A(self):
        """
            Conduction actual time coefficients
        Returns:
            (a_0, a_1, a_01): 
        """
        return (-self._coef_T_c[0], -self._coef_T_a[0], self._coef_T_b[0])

    def get_P(self, time_i, T_s0, T_s1, q_cd0, q_cd1, T_ini):
        """
            Conduction P for one time instant
        Returns:
            (p_0, p_1): 
        """
        p0 = 0
        p1 = 0
        for i in range(1, len(self._coef_T_a)):
            j = time_i - i
            if j < 0:
                T_0 = T_ini
                T_1 = T_ini
            else:
                T_0 = T_s0[j]
                T_1 = T_s1[j]
            p0 += -self._coef_T_c[i] * T_0 + self._coef_T_b[i] * T_1
            p1 += -self._coef_T_a[i] * T_1 + self._coef_T_b[i] * T_0
        for i in range(1, len(self._coef_Q)):
            j = time_i - i
            if j < 0:
                q_0 = 0
                q_1 = 0
            else:
                q_0 = q_cd0[j]
                q_1 = q_cd1[j]
            p0 += -self._coef_Q[i] * q_0
            p1 += -self._coef_Q[i] * q_1
        return (p0, p1)

    def get_source_A(self):
        """Current time coefficients of the source: heat to side 0 and side 1 (W/m², as
        q_cd0 and q_cd1) per W/m² of source.

        Returns:
            tuple: (s_0, s_1).
        """
        return (self._coef_S0[0], self._coef_S1[0])

    def get_P_source(self, time_i, q_source):
        """Part of the history terms p_0 and p_1 due to the past source fluxes (the past
        conduction fluxes q_cd0, q_cd1, with the source included, are in get_P).

        Args:
            time_i (int): time step.
            q_source (numpy.ndarray): source flux of the past time steps (W/m²).

        Returns:
            tuple: (p_0, p_1).
        """
        p0 = p1 = 0.0
        for i in range(1, len(self._coef_S0)):
            j = time_i - i
            if j >= 0:
                p0 += self._coef_S0[i] * q_source[j]
                p1 += self._coef_S1[i] * q_source[j]
        return (p0, p1)

    def get_T_source(self, time_i, T_s0, T_s1, q_source, T_source, T_ini):
        """Temperature of the source plane: T = t_0·T_s0 + t_1·T_s1 + t_s·q_source + h,
        with the current values of the time step and the history h.

        Returns:
            tuple: (t_0, t_1, t_s, h).
        """
        h = 0.0
        for i in range(1, len(self._coef_TP0)):
            j = time_i - i
            if j < 0:
                h += (self._coef_TP0[i] + self._coef_TP1[i]) * T_ini
            else:
                h += (self._coef_TP0[i] * T_s0[j] + self._coef_TP1[i] * T_s1[j]
                      + self._coef_TPS[i] * q_source[j])
        for i in range(1, len(self._coef_Q)):
            j = time_i - i
            h -= self._coef_Q[i] * (T_ini if j < 0 else T_source[j])
        return (self._coef_TP0[0], self._coef_TP1[0], self._coef_TPS[0], h)

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
            B = resis / aux * math.sin(aux)
            C = -aux * math.sin(aux) / resis
        return np.array([[A, B], [C, A]])

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
        return np.array([[A, B], [C, A]])

    def _H_Matrix_(self, s):
        H = np.eye(2)
        for i in range(len(self.parameter("materials").value)):
            H = np.dot(H, self._H_Matrix_Layer_(s, i))
        return H

    def _H_range_(self, s, first, last):
        """Transmission matrix of the layers first..last-1."""
        H = np.eye(2)
        for i in range(first, last):
            H = np.dot(H, self._H_Matrix_Layer_(s, i))
        return H

    def _dH_range_(self, s, first, last):
        """Derivative of the transmission matrix of the layers first..last-1."""
        H = np.zeros((2, 2))
        for i in range(first, last):
            P1 = self._H_range_(s, first, i)
            P2 = self._H_range_(s, i + 1, last)
            H = H + np.dot(P1, np.dot(self._dH_Matrix_Layer_(s, i), P2))
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

        delta_s = 1e-6
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

    def _calc_trans_fun_(self, delta_t):
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
        # n_coef terms of the response series give n_coef valid a, b, c coefficients, as many
        # as d has: with one fewer, the steady state (sum(a)/sum(d) = U) failed for light
        # constructions with few roots, e.g. 6.59 instead of 5.05 W/m²K for a thin panel
        for i in range(1, n_coef + 1):
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
                d = d[0: i+1]
                break
        # Only the first n_coef terms of the convolutions are valid (the response series
        # above are truncated after n_coef terms)
        a = np.resize(a, n_coef)
        b = np.resize(b, n_coef)
        c = np.resize(c, n_coef)
        # Cut a, b, c coefficients
        for i in range(len(a)):
            if (
                math.fabs(a[i]) < min_coef
                and math.fabs(b[i]) < min_coef
                and math.fabs(c[i]) < min_coef
            ):
                a = a[0: i+1]
                b = b[0: i+1]
                c = c[0: i+1]
                break
        self._coef_T_a = a
        self._coef_T_b = b
        self._coef_T_c = c
        self._coef_Q = d
        if self.has_source():
            self._calc_source_trans_fun_(delta_t, roots, d)

    def _numerator_(self, N, dN, roots, d, delta_t):
        """Coefficients of the numerator of a transfer function N(s)/B(s) (B: element
        [0, 1] of the transmission matrix of the construction, whose roots give the
        denominator d), from the response to a ramp, as for the conduction ones.

        Args:
            N (callable): N(s).
            dN (callable): derivative of N(s).
        """
        n_coef = len(roots) + 1
        H_0, dH_0 = self._H_Matrix_(0), self._dH_Matrix_(0)
        B_0, dB_0 = H_0[0, 1], dH_0[0, 1]
        C0 = N(0) / B_0
        C1 = (dN(0) * B_0 - N(0) * dB_0) / (B_0 * B_0)
        e = [N(r) / (r * r * self._dH_Matrix_(r)[0, 1]) for r in roots]
        o = []
        for i in range(1, n_coef + 1):
            o.append(C1 + i * C0 * delta_t
                     + sum(e[j] * math.exp(-i * roots[j] * delta_t) for j in range(len(roots))))
        g = np.convolve([1 / delta_t, -2 / delta_t, 1 / delta_t], d)
        return np.resize(np.convolve(g, o), n_coef)

    def _calc_source_trans_fun_(self, delta_t, roots, d):
        """Transfer functions of the heat source plane: the conduction fluxes at the two
        sides (as q_cd0 and q_cd1, heat from the construction to its surfaces) per W/m²
        of source, and the temperature of the source plane from the two surface
        temperatures and the source. The construction is split at the plane, H = H_A·H_B;
        with the source q_s: q_cd1 = (B_A/B)·q_s, q_cd0 = ((D_A·B − D·B_A)/B)·q_s and
        T_s = (B_B·T_0 + (A_B·B − B_B·A)·T_1 + B_B·B_A·q_s)/B, with the same
        denominator (roots of B) as the conduction transfer functions."""
        n = len(self.parameter("materials").value)
        k = self.parameter("source_layer").value

        def parts(s):
            return (self._H_range_(s, 0, k), self._H_range_(s, k, n),
                    self._dH_range_(s, 0, k), self._dH_range_(s, k, n),
                    self._H_Matrix_(s), self._dH_Matrix_(s))

        def num(f, df):
            return (lambda s: f(*parts(s))), (lambda s: df(*parts(s)))

        # q_cd1 per q_s: B_A
        S1 = num(lambda HA, HB, dA, dB, H, dH: HA[0, 1],
                 lambda HA, HB, dA, dB, H, dH: dA[0, 1])
        # q_cd0 per q_s: D_A·B − D·B_A
        S0 = num(lambda HA, HB, dA, dB, H, dH: HA[1, 1] * H[0, 1] - H[1, 1] * HA[0, 1],
                 lambda HA, HB, dA, dB, H, dH: (dA[1, 1] * H[0, 1] + HA[1, 1] * dH[0, 1]
                                                - dH[1, 1] * HA[0, 1] - H[1, 1] * dA[0, 1]))
        # temperature of the plane: per T_0 (B_B), per T_1 (A_B·B − B_B·A), per q_s (B_B·B_A)
        TP0 = num(lambda HA, HB, dA, dB, H, dH: HB[0, 1],
                  lambda HA, HB, dA, dB, H, dH: dB[0, 1])
        TP1 = num(lambda HA, HB, dA, dB, H, dH: HB[0, 0] * H[0, 1] - HB[0, 1] * H[0, 0],
                  lambda HA, HB, dA, dB, H, dH: (dB[0, 0] * H[0, 1] + HB[0, 0] * dH[0, 1]
                                                 - dB[0, 1] * H[0, 0] - HB[0, 1] * dH[0, 0]))
        TPS = num(lambda HA, HB, dA, dB, H, dH: HB[0, 1] * HA[0, 1],
                  lambda HA, HB, dA, dB, H, dH: dB[0, 1] * HA[0, 1] + HB[0, 1] * dA[0, 1])
        self._coef_S0 = self._numerator_(*S0, roots, d, delta_t)
        self._coef_S1 = self._numerator_(*S1, roots, d, delta_t)
        self._coef_TP0 = self._numerator_(*TP0, roots, d, delta_t)
        self._coef_TP1 = self._numerator_(*TP1, roots, d, delta_t)
        self._coef_TPS = self._numerator_(*TPS, roots, d, delta_t)
