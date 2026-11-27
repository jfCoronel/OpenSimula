import math

from opensimula.Component import Component
from opensimula.Message import Message
from opensimula.Parameters import Parameter_float, Parameter_float_list


class Radiator(Component):
    """Radiator (manufacturer data, EN 442).

    Equipment data, like a Water_coil: an HVAC_radiator_system uses it. Its heat output
    follows the characteristic equation of EN 442,

        Q = Q_nom · (ΔT_lm / ΔT_lm,nom)^n,

    with ΔT_lm the logarithmic mean temperature difference between the water (in at
    T_wi, out at T_wo) and the air of the room T_a, ΔT_lm = (T_wi − T_wo) /
    ln((T_wi − T_a) / (T_wo − T_a)), and ΔT_lm,nom that of the nominal conditions (75 /
    65 / 20 °C: 49.83 K). For a water flow m the outlet temperature is the one that
    gives the same heat to the room and from the water, ρ·c·m·(T_wi − T_wo) = Q.
    """

    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Radiator"
        self.parameter("description").value = "Radiator equipment manufacturer information (EN 442)"
        self.add_parameter(Parameter_float("nominal_heat_output", 1000, "W", min=0))
        self.add_parameter(Parameter_float("exponent", 1.3, "-", min=0.5, max=2))
        # water in, water out and air at the nominal heat output
        self.add_parameter(Parameter_float_list("nominal_conditions", [75, 65, 20], "°C"))
        # 0: the flow of the nominal conditions
        self.add_parameter(Parameter_float("nominal_water_flow", 0, "dm³/s", min=0))

    def check(self):
        errors = super().check()
        T_wi, T_wo, T_a = (list(self.parameter("nominal_conditions").value) + [0, 0, 0])[:3]
        if len(self.parameter("nominal_conditions").value) != 3 or not T_wi > T_wo > T_a:
            msg = (f"Error: {self.parameter('name').value}, nominal_conditions must be [water in, "
                   "water out, air] with water in > water out > air")
            errors.append(Message(msg, "ERROR"))
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self.props = self._sim_.props
        T_wi, T_wo, T_a = self.parameter("nominal_conditions").value
        self.dT_nom = self.log_mean(T_wi, T_wo, T_a)
        self.Q_nom = self.parameter("nominal_heat_output").value
        self.n = self.parameter("exponent").value
        flow = self.parameter("nominal_water_flow").value
        if flow <= 0:  # the flow of the nominal conditions
            rho_cp = self.props["RHOCP_W"](T_wi) / 1000  # as in heat_output
            flow = self.Q_nom / (rho_cp * (T_wi - T_wo)) if self.Q_nom > 0 else 0
        self.nominal_flow = flow

    @staticmethod
    def log_mean(T_wi, T_wo, T_a):
        """Logarithmic mean temperature difference between the water and the air (K)."""
        d1, d2 = T_wi - T_a, T_wo - T_a
        if d1 <= 0 or d2 <= 0:
            return 0.0
        if abs(d1 - d2) < 1e-9:
            return d1
        return (d1 - d2) / math.log(d1 / d2)

    def heat_output(self, T_wi, water_flow, T_a):
        """Heat to the room (W) and outlet water temperature (°C) of one radiator.

        Args:
            T_wi (float): water inlet temperature (°C).
            water_flow (float): water flow (dm³/s).
            T_a (float): air temperature of the room (°C).

        Returns:
            tuple: (Q, T_wo); (0, T_wi) if the water is not warmer than the air.
        """
        if water_flow <= 0 or T_wi <= T_a or self.Q_nom <= 0:
            return 0.0, T_wi
        mc = self.props["RHOCP_W"](T_wi) / 1000 * water_flow  # W/K

        def excess(T_wo):  # heat of the water minus heat to the room
            return mc * (T_wi - T_wo) - self.Q_nom * (self.log_mean(T_wi, T_wo, T_a) / self.dT_nom) ** self.n

        low, high = T_a + 1e-9, T_wi  # excess > 0 at low, < 0 at high
        for _ in range(60):
            mid = (low + high) / 2
            if excess(mid) > 0:
                low = mid
            else:
                high = mid
        T_wo = (low + high) / 2
        return mc * (T_wi - T_wo), T_wo

    def flow_for(self, Q, T_wi, T_a):
        """Water flow (dm³/s) with which one radiator gives Q (W), at most the nominal flow,
        and the outlet temperature.

        Returns:
            tuple: (water_flow, T_wo).
        """
        Q_max, T_wo = self.heat_output(T_wi, self.nominal_flow, T_a)
        if Q <= 0:
            return 0.0, T_wi
        if Q >= Q_max:
            return self.nominal_flow, T_wo
        low, high = 0.0, self.nominal_flow  # the heat grows with the flow
        for _ in range(60):
            mid = (low + high) / 2
            if self.heat_output(T_wi, mid, T_a)[0] < Q:
                low = mid
            else:
                high = mid
        return high, self.heat_output(T_wi, high, T_a)[1]
