import math

import numpy as np

from opensimula.Component import Component
from opensimula.Message import Message
from opensimula.Parameters import (
    Parameter_float,
    Parameter_int,
    Parameter_math_exp,
    Parameter_variable_list,
)
from opensimula.Variable import Variable


class Water_tank(Component):
    """Water storage tank: a DHW tank, an electric water heater or a buffer tank.

    Equipment data, like a Boiler: it is used by the HVAC_water_system or the
    HVAC_water_circuit that refers to it in its ``tank`` parameter, whose water is then
    the water of the tank. Its heat losses are UA·(T − T_ambient), with the ambient
    temperature an expression (e.g. the temperature of the space it is in). The system
    that holds it stores its temperature and losses in the variables of the tank.

    With ``number_of_nodes`` > 1 the tank is stratified: N layers of the same volume,
    from the top (node 1) to the bottom (node N). The water drawn leaves at the top and
    the water that comes back (mains water for DHW) enters at the bottom, pushing the
    layers up; the solar collectors heat the bottom node and the other generators (or,
    in a charging circuit, the water of the plant) the node at ``backup_position``,
    where the thermostat is; heated water rises (a layer warmer than the one above
    mixes with it).
    """

    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Water_tank"
        self.parameter("description").value = "Water storage tank"
        self.add_parameter(Parameter_float("volume", 150, "dm³", min=0.001))
        self.add_parameter(Parameter_float("UA", 1.5, "W/K", min=0))
        # thermostat: charging starts when the water is dead_band below the setpoint and
        # goes on up to the setpoint
        self.add_parameter(Parameter_float("dead_band", 0, "K", min=0))
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_math_exp("ambient_temperature", "20", "°C"))
        self.add_parameter(Parameter_int("number_of_nodes", 1, "", min=1, max=50))
        # height of the backup heater (and its thermostat), fraction from the bottom
        self.add_parameter(Parameter_float("backup_position", 0.5, "frac", min=0, max=1))
        self.add_variable(Variable("temperature", unit="°C"))  # mean
        self.add_variable(Variable("T_ambient", unit="°C"))
        self.add_variable(Variable("Q_loss", unit="W"))  # heat lost, positive

    def check(self):
        errors = super().check()
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        self.n_nodes = self.parameter("number_of_nodes").value
        for key in [k for k in self._variables_ if k.startswith("T_node_")]:
            self.del_variable(self._variables_[key])
        if self.n_nodes > 1:
            for i in range(1, self.n_nodes + 1):
                self.add_variable(Variable(f"T_node_{i}", unit="°C"))
        super().pre_simulation(n_time_steps, delta_t)
        N = self.n_nodes
        p = self.parameter("backup_position").value
        self.backup_node = min(N - 1, max(0, math.ceil((1 - p) * N) - 1))  # 0 is the top
        self.solar_node = N - 1
        self.nodes = None  # temperatures of the nodes, set by the system that holds it

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        var_dic = self.get_parameter_variable_dictionary(time_index)
        self.T_ambient = self.parameter("ambient_temperature").evaluate(var_dic)

    def get_dead_band(self):
        """Dead band of the thermostat (K)."""
        return self.parameter("dead_band").value

    def get_volume(self):
        """Water volume (dm³)."""
        return self.parameter("volume").value

    def get_loss(self, T):
        """Heat lost by the tank with its water at T (W, positive when it loses)."""
        return self.parameter("UA").value * (T - self.T_ambient)

    def set_state(self, time_index, T, nodes=None, loss=None):
        """Store the temperature of the water (the mean one), the losses (those the
        system holding it used in its balance, if given) and, for a stratified tank,
        the temperature of its nodes."""
        self.variable("temperature").values[time_index] = T
        self.variable("T_ambient").values[time_index] = self.T_ambient
        if loss is not None:
            self.variable("Q_loss").values[time_index] = loss
        elif nodes is None:
            self.variable("Q_loss").values[time_index] = self.get_loss(T)
        else:
            self.variable("Q_loss").values[time_index] = sum(self.get_loss(t) for t in nodes) / len(nodes)
        if nodes is not None:
            for i, t in enumerate(nodes):
                self.variable(f"T_node_{i + 1}").values[time_index] = t
            self.nodes = np.array(nodes, dtype=float)

    # _________________ Stratified tank: the physics of its nodes _________________

    def node_volume(self):
        return self.get_volume() / self.n_nodes

    def advect(self, T, flow, T_in, dt):
        """Water drawn at the top and the same flow entering at the bottom at T_in.

        Args:
            T (numpy.ndarray): temperatures of the nodes, top first.
            flow (float): flow (dm³/s).
            T_in (float): temperature of the water entering at the bottom.
            dt (float): time (s).

        Returns:
            tuple: (temperatures, mean temperature of the water leaving at the top).
        """
        T = np.array(T, dtype=float)
        volume = flow * dt
        if volume <= 0:
            return T, T[0]
        n = max(1, math.ceil(volume / self.node_volume()))
        f = volume / n / self.node_volume()  # fraction of a node renewed in a sub-step
        out = 0.0
        for _ in range(n):
            out += T[0]
            below = np.append(T[1:], T_in)
            T = T + f * (below - T)
        return T, out / n

    def losses(self, T, rho_cp, dt):
        """Temperatures after the losses of each node (explicit) and the heat lost (W)."""
        UA = self.parameter("UA").value / self.n_nodes
        q = UA * (np.asarray(T) - self.T_ambient)
        return np.asarray(T) - q * dt / (rho_cp * self.node_volume()), float(q.sum())

    @staticmethod
    def mix(T):
        """Mix the inversions: a node warmer than the one above rises (the blocks of
        nodes out of order take their mean temperature), top first, non increasing."""
        blocks = []  # [sum, count]
        for t in T:
            blocks.append([t, 1])
            while len(blocks) > 1 and blocks[-1][0] / blocks[-1][1] > blocks[-2][0] / blocks[-2][1] + 1e-12:
                s, c = blocks.pop()
                blocks[-1][0] += s
                blocks[-1][1] += c
        out = []
        for s, c in blocks:
            out += [s / c] * c
        return np.array(out)

    def draw_and_losses(self, T0, flow, Q_loads, rho_cp, dt):
        """A time step of a stratified tank without its heaters: the water drawn by the
        loads leaves at the top and comes back at the bottom at the temperature that
        gives their load, then each node loses heat.

        Args:
            T0 (numpy.ndarray): temperatures of the nodes at the start, top first.
            flow (float): flow of the loads (dm³/s).
            Q_loads (float): heat of the loads to the water (W, negative when they take it).
            rho_cp (float): W/(dm³·K).
            dt (float): time step (s).

        Returns:
            tuple: (temperatures, mean temperature of the water leaving at the top,
                temperature of the water coming back, heat lost in W).
        """
        T, T_out = self.advect(T0, flow, T0[-1], dt)
        if flow > 0:  # second pass, with the return that gives the load
            T_ret = T_out + Q_loads / (rho_cp * flow)
            T, T_out = self.advect(T0, flow, T_ret, dt)
        else:
            T_ret = T_out
        T, lost = self.losses(T, rho_cp, dt)
        return T, T_out, T_ret, lost

    def heat_to_setpoint(self, T, node, setpoint, rho_cp, dt):
        """Heat (W) that, given to a node and mixed, leaves that node at the setpoint
        (0 if it is already there)."""
        if T[node] >= setpoint:
            return 0.0
        low, high = 0.0, rho_cp * self.get_volume() * (setpoint - T[node]) / dt
        for _ in range(60):
            mid = (low + high) / 2
            if self.add_heat(T, node, mid, rho_cp, dt)[node] < setpoint:
                low = mid
            else:
                high = mid
        return high

    def add_heat(self, T, node, Q, rho_cp, dt):
        """Temperatures after giving the heat Q (W) to a node and mixing."""
        T = np.array(T, dtype=float)
        T[node] += Q * dt / (rho_cp * self.node_volume())
        return self.mix(T)
