import math

import numpy as np

from opensimula.Component import Component
from opensimula.Message import Message
from opensimula.Parameters import (
    Parameter_component,
    Parameter_component_list,
    Parameter_float,
    Parameter_int,
    Parameter_math_exp,
    Parameter_options,
    Parameter_variable_list,
)
from opensimula.Variable import Variable
from opensimula.comfort import Zone_control

# water at the usual temperatures of a radiant floor (30-45 °C)
NU_WATER = 0.65e-6  # kinematic viscosity, m²/s
K_WATER = 0.63  # conductivity, W/(m·K)
PR_WATER = 4.3


class HVAC_radiant_floor_system(Component):
    """Radiant floor (or ceiling) of a zone fed by a water plant or circuit (heating only).

    The pipes are in the heat source plane of the construction of its ``surfaces``
    (``source_layer`` of the Construction), whose transfer functions give the heat that
    goes from the plane to each side and the temperature of the plane. The water gives
    the plane, with the effectiveness of the pipes,

        Q = ε·ρ·c·m·(T_wi − T_plane),  ε = 1 − exp(−UA / (ρ·c·m)),

    with UA = area / R_t and R_t (m²K/W, per m² of floor) the resistances between the
    water and the plane of the thermal resistance method of EN ISO 11855: convection of
    the water (inside the pipes, laminar or Gnielinski), the wall of the pipe and the
    layer around the pipes, R_x = T·ln(T / (π·d)) / (2π·λ), with T the pipe spacing, d
    the outer diameter and λ the conductivity of the layer before the source plane. The
    heat is the same per m² in all the surfaces (the flow is shared by area).

    A zone thermostat opens the valve in proportion to the air temperature, fully open at
    heating_setpoint − throttling_range/2 and closed at heating_setpoint +
    throttling_range/2 (``control`` "PROPORTIONAL"), or the valve is always open
    ("NONE"). For the zone it is an uncontrolled system, like the radiators: the zone
    may have another system that controls it.
    """

    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "HVAC_radiant_floor_system"
        self.parameter("description").value = "Radiant floor of a zone fed by a water system"
        self.add_parameter(Parameter_component("space", "not_defined", ["Space"]))
        self.add_parameter(Parameter_component_list("surfaces", [], ["Building_surface"]))
        self.add_parameter(Parameter_component("water_system", "not_defined",
                                               ["HVAC_water_system", "HVAC_water_circuit"]))
        self.add_parameter(Parameter_float("nominal_water_flow", 0.1, "dm³/s", min=0))
        self.add_parameter(Parameter_int("number_of_circuits", 1, "", min=1))
        self.add_parameter(Parameter_float("pipe_spacing", 0.15, "m", min=0.01))
        self.add_parameter(Parameter_float("pipe_diameter", 0.016, "m", min=0.001))
        self.add_parameter(Parameter_float("pipe_wall_thickness", 0.002, "m", min=0))
        self.add_parameter(Parameter_float("pipe_conductivity", 0.35, "W/(m·K)", min=0.001))
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_math_exp("heating_setpoint", "20", "°C"))
        self.add_parameter(Parameter_math_exp("system_on_off", "1", "on/off"))
        self.add_parameter(Parameter_options("control", "PROPORTIONAL", ["PROPORTIONAL", "NONE"]))
        self.add_parameter(Parameter_float("throttling_range", 2, "K", min=0.01))
        self.add_variable(Variable("on_off", unit="flag"))  # availability (system_on_off)
        self.add_variable(Variable("state", unit="flag"))  # 1 heating, 0 off
        self.add_variable(Variable("heating_setpoint", unit="°C"))
        self.add_variable(Variable("Q", unit="W"))  # heat of the water to the source planes
        self.add_variable(Variable("q_source", unit="W/m²"))
        self.add_variable(Variable("T_source", unit="°C"))  # area mean
        self.add_variable(Variable("valve", unit="frac"))
        self.add_variable(Variable("water_flow", unit="dm³/s"))
        self.add_variable(Variable("T_wi", unit="°C"))
        self.add_variable(Variable("T_wo", unit="°C"))

    def check(self):
        errors = super().check()
        name = self.parameter("name").value
        for key in ("space", "water_system"):
            if self.parameter(key).value == "not_defined":
                errors.append(Message(f"Error: {name}, {key} must be defined", "ERROR"))
        surfaces = self.parameter("surfaces").component
        if not surfaces:
            errors.append(Message(f"Error: {name}, surfaces must have at least one surface", "ERROR"))
        for surface in surfaces or []:
            if surface is None:
                continue
            construction = surface.parameter("construction").component
            if surface.parameter("surface_type").value == "VIRTUAL" or construction is None \
                    or not construction.has_source():
                errors.append(Message(
                    f"Error: {name}, surface {surface.parameter('name').value} must have a "
                    "construction with source_layer", "ERROR"))
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self.space = self.parameter("space").component
        self.surfaces = list(self.parameter("surfaces").component)
        self.water_system = self.parameter("water_system").component
        self.name = self.parameter("name").value
        self.building = self.space.parameter("building").component
        self.props = self._sim_.props
        self.areas = np.array([s.area for s in self.surfaces])
        self.area = float(self.areas.sum())
        self.nominal_flow = self.parameter("nominal_water_flow").value
        self.n_circuits = self.parameter("number_of_circuits").value
        T = self.parameter("pipe_spacing").value
        d = self.parameter("pipe_diameter").value
        self.d_i = max(d - 2 * self.parameter("pipe_wall_thickness").value, 1e-4)
        R_r = T * math.log(d / self.d_i) / (2 * math.pi * self.parameter("pipe_conductivity").value)
        # pipes and the layer around them, per m² of floor (without the water)
        self.R_pipe = []
        for surface in self.surfaces:
            construction = surface.parameter("construction").component
            layer = construction.parameter("source_layer").value - 1
            material = construction.parameter("materials").component[layer]
            R_x = T * math.log(T / (math.pi * d)) / (2 * math.pi * material.parameter("conductivity").value)
            self.R_pipe.append(R_r + max(R_x, 0.0))
        self.R_pipe = np.array(self.R_pipe)
        self.spacing = T
        for surface in self.surfaces:
            surface.source_space = self.space

    def R_water(self, flow):
        """Convective resistance of the water inside the pipes per m² of floor (m²K/W)
        with the total water flow (dm³/s)."""
        if flow <= 0:
            return math.inf
        velocity = flow / 1000 / self.n_circuits / (math.pi * self.d_i ** 2 / 4)
        Re = velocity * self.d_i / NU_WATER
        if Re < 2300:
            Nu = 4.36
        else:
            f = (0.79 * math.log(Re) - 1.64) ** -2
            Nu = (f / 8) * (Re - 1000) * PR_WATER / (1 + 12.7 * math.sqrt(f / 8) * (PR_WATER ** (2 / 3) - 1))
            Nu = max(Nu, 4.36)
        h = Nu * K_WATER / self.d_i
        return self.spacing / (math.pi * self.d_i * h)

    def water_heat(self, T_wi, flow, T_plane):
        """Heat of the water to the source planes (W) with the total flow (dm³/s) and the
        temperature of the plane of each surface: ε·ρ·c·m·(T_wi − T_plane) by surface,
        the flow shared by area."""
        if flow <= 0:
            return 0.0
        rho_cp = self.props["RHOCP_W"](T_wi) / 1000  # W/(dm³·K)
        R_w = self.R_water(flow)
        mc = rho_cp * flow * self.areas / self.area
        UA = self.areas / (self.R_pipe + R_w)
        eps = 1 - np.exp(-UA / mc)
        return float(np.sum(eps * mc * (T_wi - T_plane)))

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        var_dic = self.get_parameter_variable_dictionary(time_index)
        self.T_sp = self.parameter("heating_setpoint").evaluate(var_dic)
        self.on = self.parameter("system_on_off").evaluate(var_dic) != 0
        self.Q = self.q = self.valve = self.water_flow = 0.0
        self.T_wi = self.T_wo = 0.0
        self.T_plane = 0.0

    def _valve(self, T_a):
        if self.parameter("control").value == "NONE":
            return 1.0
        TR = self.parameter("throttling_range").value
        return min(max((self.T_sp + TR / 2 - T_a) / TR, 0.0), 1.0)

    def iteration(self, time_index, date, daylight_saving, n_iter):
        super().iteration(time_index, date, daylight_saving, n_iter)
        space = self.space
        space.del_uncontrol_system(self.name)
        for surface in self.surfaces:
            surface.source_flux = 0.0
        self.Q = self.q = self.valve = self.water_flow = 0.0
        self.T_wi = self.T_wo = self.water_system.get_heating_coil_inlet_T()
        # the zone without the floor: K·T = F + e·q, e the heat to the air of the zone
        # per W/m² of the sources in this time step
        K, F = space.get_thermal_equation(False)
        j = self.building.spaces.index(space)
        e = sum(self.building.source_response(s)[1][j] for s in self.surfaces)

        def air(q):
            return (F + e * q) / K

        # temperature of the planes, linear with q (the air of the zone too)
        T_0 = self.building.source_temperatures(self.surfaces, 0.0, space, air(0.0))
        dT = self.building.source_temperatures(self.surfaces, 1.0, space, air(1.0)) - T_0

        def planes(q):
            return T_0 + dT * q

        self.T_plane = float(np.dot(self.areas, T_0) / self.area)
        if not (self.on and self.water_system.can_heat()):
            return True

        def water(q):
            valve = self._valve(air(q))
            return self.water_heat(self.T_wi, valve * self.nominal_flow, planes(q)), valve

        Q_0, _ = water(0.0)
        if Q_0 <= 0:
            return True
        # the source flux that the water gives: A·q = Q_water(q), Q_water decreases with q
        low, high = 0.0, Q_0 / self.area
        for _ in range(60):
            mid = (low + high) / 2
            if self.area * mid < water(mid)[0]:
                low = mid
            else:
                high = mid
        self.q = (low + high) / 2
        self.Q, self.valve = water(self.q)
        self.q = self.Q / self.area
        self.water_flow = self.valve * self.nominal_flow
        self.T_plane = float(np.dot(self.areas, planes(self.q)) / self.area)
        if self.Q <= 0:
            self.Q = self.q = 0.0
            return True
        rho_cp = self.props["RHOCP_W"](self.T_wi) / 1000
        self.T_wo = self.T_wi - self.Q / (rho_cp * self.water_flow)
        for surface in self.surfaces:
            surface.source_flux = self.q
        space.add_uncontrol_system({"name": self.name, "M_a": 0, "T_a": 0, "w_a": 0,
                                    "Q_s": e * self.q, "M_w": 0})
        self.water_system.add_coil_load(-self.Q, self.water_flow)
        return True

    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        values = {
            "on_off": 1 if self.on else 0,
            "state": 1 if self.Q > 0 else 0,
            "heating_setpoint": self.T_sp,
            "Q": self.Q,
            "q_source": self.q,
            "T_source": self.T_plane,
            "valve": self.valve,
            "water_flow": self.water_flow,
            "T_wi": self.T_wi,
            "T_wo": self.T_wo if self.Q > 0 else self.T_wi,
        }
        for key, value in values.items():
            self.variable(key).values[time_index] = value

    def get_zone_setpoints(self):
        """The zone it serves, with its heating setpoint (no cooling).

        Returns:
            list: one `Zone_control` (values at each time step).
        """
        on = np.array(self.variable("on_off").values) != 0
        heating = np.array(self.variable("heating_setpoint").values, dtype=float)
        return [Zone_control(self.space, heating, np.full(len(heating), np.inf), on)]
