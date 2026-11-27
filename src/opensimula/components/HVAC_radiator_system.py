import numpy as np

from opensimula.Component import Component
from opensimula.Message import Message
from opensimula.Parameters import (
    Parameter_component,
    Parameter_int,
    Parameter_math_exp,
    Parameter_options,
    Parameter_variable_list,
)
from opensimula.Variable import Variable
from opensimula.comfort import Zone_control


class HVAC_radiator_system(Component):
    """Radiators of a zone fed by a water plant or circuit (heating only).

    The radiators (``number_of_units`` of the ``radiator`` equipment) take water from the
    water system at its supply temperature and give it back colder: for the plant they
    are one more coil. With ``control`` "THERMOSTATIC" a thermostatic valve (or a zone
    thermostat) adjusts the water flow to hold the heating setpoint of the zone, up to
    the heat of the radiators at their nominal flow with the water they get; with
    "NONE" the valve is fully open and they give all they can.

    For the zone the radiators are an uncontrolled system (heat to its air): the zone
    may have another system that controls it, e.g. one that only cools. All their heat
    goes to the air of the zone (their radiant part is not separated yet).
    """

    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "HVAC_radiator_system"
        self.parameter("description").value = "Radiators of a zone fed by a water system"
        self.add_parameter(Parameter_component("space", "not_defined", ["Space", "Load_space"]))
        self.add_parameter(Parameter_component("radiator", "not_defined", ["Radiator"]))
        self.add_parameter(Parameter_int("number_of_units", 1, "", min=1))
        self.add_parameter(Parameter_component("water_system", "not_defined",
                                               ["HVAC_water_system", "HVAC_water_circuit"]))
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_math_exp("heating_setpoint", "20", "°C"))
        self.add_parameter(Parameter_math_exp("system_on_off", "1", "on/off"))
        self.add_parameter(Parameter_options("control", "THERMOSTATIC", ["THERMOSTATIC", "NONE"]))
        self.add_variable(Variable("on_off", unit="flag"))  # availability (system_on_off)
        self.add_variable(Variable("state", unit="flag"))  # 1 heating, 0 off
        self.add_variable(Variable("heating_setpoint", unit="°C"))
        self.add_variable(Variable("Q", unit="W"))  # heat to the zone
        self.add_variable(Variable("F_load", unit="frac"))  # Q / capacity
        self.add_variable(Variable("water_flow", unit="dm³/s"))
        self.add_variable(Variable("T_wi", unit="°C"))
        self.add_variable(Variable("T_wo", unit="°C"))

    def check(self):
        errors = super().check()
        name = self.parameter("name").value
        for key in ("space", "radiator", "water_system"):
            if self.parameter(key).value == "not_defined":
                errors.append(Message(f"Error: {name}, {key} must be defined", "ERROR"))
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self.space = self.parameter("space").component
        self.radiator = self.parameter("radiator").component
        self.water_system = self.parameter("water_system").component
        self.n_units = self.parameter("number_of_units").value
        self.name = self.parameter("name").value

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        var_dic = self.get_parameter_variable_dictionary(time_index)
        self.T_sp = self.parameter("heating_setpoint").evaluate(var_dic)
        self.on = self.parameter("system_on_off").evaluate(var_dic) != 0
        self.Q = self.water_flow = self.capacity = 0.0
        self.T_wi = self.T_wo = 0.0

    def _output(self, T_wi, flow, T_a):
        """(heat, T_wo) of all the units with the total flow."""
        Q, T_wo = self.radiator.heat_output(T_wi, flow / self.n_units, T_a)
        return self.n_units * Q, T_wo

    def iteration(self, time_index, date, daylight_saving, n_iter):
        super().iteration(time_index, date, daylight_saving, n_iter)
        space = self.space
        space.del_uncontrol_system(self.name)
        self.Q = self.water_flow = self.capacity = 0.0
        self.T_wi = self.T_wo = self.water_system.get_heating_coil_inlet_T()
        if not (self.on and self.water_system.can_heat()):
            return True
        # the zone without the radiators: K·T = F + Q
        K, F = space.get_thermal_equation(False)
        nominal = self.radiator.nominal_flow * self.n_units
        T_free = F / K
        thermostatic = self.parameter("control").value == "THERMOSTATIC"
        Q_required = max(K * self.T_sp - F, 0.0) if thermostatic else float("inf")
        if Q_required <= 0 or self.T_wi <= T_free:
            return True
        capacity_sp, _ = self._output(self.T_wi, nominal, self.T_sp)
        if thermostatic and Q_required <= capacity_sp:
            # the valve gives the heat that holds the setpoint
            self.Q = Q_required
            self.capacity = capacity_sp
            flow, self.T_wo = self.radiator.flow_for(self.Q / self.n_units, self.T_wi, self.T_sp)
            self.water_flow = flow * self.n_units
        else:
            # fully open: the zone at the temperature where the radiators give what
            # they can, K·T = F + Q(T), between T_free and the water temperature
            low, high = T_free, self.T_wi
            for _ in range(60):
                T = (low + high) / 2
                if K * T - F < self._output(self.T_wi, nominal, T)[0]:
                    low = T
                else:
                    high = T
            T_a = (low + high) / 2
            self.Q, self.T_wo = self._output(self.T_wi, nominal, T_a)
            self.capacity = self.Q
            self.water_flow = nominal
        space.add_uncontrol_system({"name": self.name, "M_a": 0, "T_a": 0, "w_a": 0,
                                    "Q_s": self.Q, "M_w": 0})
        if self.Q > 0:
            self.water_system.add_coil_load(-self.Q, self.water_flow)
        return True

    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        values = {
            "on_off": 1 if self.on else 0,
            "state": 1 if self.Q > 0 else 0,
            "heating_setpoint": self.T_sp,
            "Q": self.Q,
            "F_load": self.Q / self.capacity if self.capacity > 0 else 0,
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
