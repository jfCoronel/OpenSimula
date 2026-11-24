import numpy as np
from opensimula.Component import Component
from opensimula.Message import Message
from opensimula.Parameters import (
    Parameter_component,
    Parameter_component_list,
    Parameter_float,
    Parameter_math_exp,
    Parameter_options,
    Parameter_variable_list,
)
from opensimula.Variable import Variable
from opensimula.energy import mode_from_plant, split_dhw
from opensimula.components.Pump import staged_pump_flows


class HVAC_water_circuit(Component):
    """A secondary water circuit fed by an HVAC_water_system (the plant).

    The coils of the air systems can hang from a circuit instead of from the
    plant: a plant may feed several circuits, each with its own pumps, its own
    availability and, with a mixing valve, its own supply temperature (e.g.
    fan coils at 45 °C and an air handling unit at 60 °C from the same boiler).

    Towards the coils it offers what the plant offers (inlet water temperature,
    add_coil_load); towards the plant it is one more coil: it takes water from it
    and gives it back its load (that of its coils, its losses, the heat of its
    pumps and, with a water volume, the change of its stored energy). The mode,
    heating or cooling, is that of the plant.

    With a ``tank`` (Water_tank) it is a charging circuit: its coils (e.g. DHW
    demands) take the water of the tank, and its pumps charge the tank with water of
    the plant while the tank is below ``tank_setpoint`` and the plant can heat and is
    hotter; they run the fraction of the time step the charge needs.
    """

    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "HVAC_water_circuit"
        self.parameter("description").value = "Secondary water circuit fed by a water system"
        self.add_parameter(Parameter_component("water_system", "not_defined", ["HVAC_water_system"]))
        self.add_parameter(Parameter_component_list("pumps", [], ["Pump"]))
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_math_exp("system_on_off", "1", "on/off"))
        self.add_parameter(
            Parameter_options("pump_operation", "ALLWAYS_ON", ["ALLWAYS_ON", "ON_LOAD"])
        )
        # CONSTANT: the design flow while on; VARIABLE: the flow of its coils, between
        # minimum_flow and the design flow, its pumps staged
        self.add_parameter(Parameter_options("flow_control", "CONSTANT", ["CONSTANT", "VARIABLE"]))
        self.add_parameter(Parameter_float("minimum_flow", 0, "frac", min=0, max=1))
        # mixing valve: the supply is never above the heating setpoint nor below the
        # cooling one ("": no limit, the water of the plant)
        self.add_parameter(Parameter_math_exp("heating_supply_setpoint", "", "°C"))
        self.add_parameter(Parameter_math_exp("cooling_supply_setpoint", "", "°C"))
        self.add_parameter(Parameter_math_exp("Q_loss", "0", "W"))
        self.add_parameter(Parameter_float("water_volume", 0, "dm³", min=0))
        self.add_parameter(Parameter_component("tank", "not_defined", ["Water_tank"]))
        self.add_parameter(Parameter_math_exp("tank_setpoint", "60", "°C"))

        # Variables
        self.add_variable(Variable("on_off", unit="flag"))
        self.add_variable(Variable("T_plant", unit="°C"))  # water from the plant
        self.add_variable(Variable("T_supply", unit="°C"))
        self.add_variable(Variable("T_return", unit="°C"))
        self.add_variable(Variable("water_flow", unit="dm³/s"))  # moved by its pumps
        self.add_variable(Variable("plant_flow", unit="dm³/s"))  # taken from the plant
        self.add_variable(Variable("mixing_flow", unit="dm³/s"))  # return mixed in the supply
        self.add_variable(Variable("coils_flow", unit="dm³/s"))
        # loads of its coils and DHW demands: Q_loads = Q_heating_coils + Q_cooling_coils + Q_dhw
        self.add_variable(Variable("Q_loads", unit="W"))
        self.add_variable(Variable("Q_heating_coils", unit="W"))
        self.add_variable(Variable("Q_cooling_coils", unit="W"))
        self.add_variable(Variable("Q_dhw", unit="W"))
        self.add_variable(Variable("Q_loss", unit="W"))
        self.add_variable(Variable("Q_pump", unit="W"))
        self.add_variable(Variable("delta_U", unit="W"))
        self.add_variable(Variable("Q_plant", unit="W"))  # load given to the plant
        self.add_variable(Variable("pumps_power", unit="W"))

    def check(self):
        errors = super().check()
        if self.parameter("water_system").value == "not_defined":
            msg = f"{self.parameter('name').value}, must define the water system that feeds it."
            errors.append(Message(msg, "ERROR"))
        if len(self.parameter("pumps").value) == 0:
            msg = f"{self.parameter('name').value}, must define its pumps."
            errors.append(Message(msg, "ERROR"))
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self.props = self._sim_.props
        self.delta_t = delta_t
        self.plant = self.parameter("water_system").component
        self.pumps = self.parameter("pumps").component
        self.design_flow = sum(p.parameter("nominal_water_flow").value for p in self.pumps)
        self.water_volume = self.parameter("water_volume").value
        self.variable_flow = self.parameter("flow_control").value == "VARIABLE"
        self.tank = (self.parameter("tank").component
                     if self.parameter("tank").value != "not_defined" else None)
        self._dhw_only = None
        self.minimum_flow = self.parameter("minimum_flow").value

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        self.var_dic = self.get_parameter_variable_dictionary(time_index)
        self._on_off = self.parameter("system_on_off").evaluate(self.var_dic) != 0
        self.variable("on_off").values[time_index] = 1 if self._on_off else 0
        self.heating_sp = self._setpoint("heating_supply_setpoint")
        self.cooling_sp = self._setpoint("cooling_supply_setpoint")
        if time_index == 0:
            self.T_mean_pre = None  # the first time step stores no energy
        else:
            self.T_mean_pre = (
                self.variable("T_supply").values[time_index - 1]
                + self.variable("T_return").values[time_index - 1]
            ) / 2
        if self.tank is not None:
            self.tank_sp = self.parameter("tank_setpoint").evaluate(self.var_dic)
            self.T_tank_pre = (self.tank_sp if time_index == 0
                               else self.variable("T_supply").values[time_index - 1])
            self.T_tank = self.T_tank_pre
            # charging in the previous time step without reaching the setpoint: the
            # thermostat goes on up to it
            self.charging_pre = (time_index > 0
                                 and self.variable("plant_flow").values[time_index - 1] > 0
                                 and self.T_tank_pre < self.tank_sp - 1e-6)
        self.Q_coils = self.coils_flow = 0
        self.Q_coils_used = self.coils_flow_used = 0
        self.Q_dhw = self.Q_dhw_used = 0
        self.Q_heat = self.Q_heat_used = self.Q_cool = self.Q_cool_used = 0
        self.water_flow = 0
        self.pump_flows = [0] * len(self.pumps)
        self.Q_pump = self.Q_loss = self.delta_U = self.Q_plant = 0

    def _setpoint(self, key):
        if str(self.parameter(key).value).strip() == "":
            return None
        return self.parameter(key).evaluate(self.var_dic)

    # _________________ What the coils use (as from a plant) _________________

    @property
    def on_off(self):
        """True if the circuit and its plant are on."""
        return bool(self._on_off and self.plant.on_off)

    def can_heat(self):
        """True if the coils can take heat: the circuit is on and its plant can heat (with
        a tank, the circuit is on: the tank gives its water whatever the plant does)."""
        if self.tank is not None:
            return bool(self._on_off)
        return bool(self._on_off and self.plant.can_heat())

    def can_cool(self):
        """True if the coils can take cold: the circuit is on and its plant can cool."""
        return bool(self._on_off and self.plant.can_cool())

    def _supply(self, T_plant, mode=None):
        """Supply temperature: that of the plant, limited by the mixing valve, which
        mixes it with the return: never above the heating setpoint nor below the
        cooling setpoint, whatever the mode of the plant."""
        T = T_plant
        if self.heating_sp is not None:
            T = min(T, self.heating_sp)
        if self.cooling_sp is not None:
            T = max(T, self.cooling_sp)
        return T

    def get_heating_coil_inlet_T(self):
        """Water temperature to the heating coils (°C): that of the tank, if any."""
        if self.tank is not None:
            return self.T_tank
        return self._supply(self.plant.get_heating_coil_inlet_T(), 1)

    def get_cooling_coil_inlet_T(self):
        """Water temperature to the cooling coils (°C): that of the tank, if any."""
        if self.tank is not None:
            return self.T_tank
        return self._supply(self.plant.get_cooling_coil_inlet_T(), -1)

    def add_coil_load(self, Q_coil, water_flow=0, dhw=0.0):
        """Add the load of a coil in this iteration.

        Args:
            Q_coil (float): heat the coil gives to the water (W), positive when it heats
                the water (cooling coil), negative when it cools it (heating coil).
            water_flow (float, optional): water flow through the coil (dm³/s).
            dhw (float, optional): the part of Q_coil that is domestic hot water (W).
        """
        self.Q_coils += Q_coil
        self.coils_flow += water_flow
        self.Q_dhw += dhw
        if Q_coil - dhw < 0:  # coils: heating ones take heat from the water
            self.Q_heat += Q_coil - dhw
        else:
            self.Q_cool += Q_coil - dhw

    # _________________ Iteration: the load to the plant _________________

    def iteration(self, time_index, date, daylight_saving, n_iter):
        super().iteration(time_index, date, daylight_saving, n_iter)
        if self.tank is not None:
            return self._iteration_tank()
        mode = self.plant.mode
        # the water the plant gives to its coils (the setpoint before its first iteration)
        if mode == 1:
            T_plant = self.plant.get_heating_coil_inlet_T()
        elif mode == -1:
            T_plant = self.plant.get_cooling_coil_inlet_T()
        else:
            T_plant = self.plant.T_WCI
        self.T_plant = T_plant
        self.T_supply = self._supply(T_plant, mode)
        load = self.Q_coils != 0
        pumps_on = self.on_off and (self.parameter("pump_operation").value == "ALLWAYS_ON" or load)
        if self.variable_flow:
            self.water_flow = (min(max(self.coils_flow, self.minimum_flow * self.design_flow),
                                   self.design_flow) if self.on_off else 0)
            self.pump_flows = staged_pump_flows(self.pumps, self.water_flow)
        else:
            self.water_flow = self.design_flow if pumps_on else 0
            self.pump_flows = [p.parameter("nominal_water_flow").value if pumps_on else 0
                               for p in self.pumps]
        rho_cp = self.props["RHOCP_W"](self.T_supply) / 1000  # W/(dm³·K)
        self.var_dic["T_w"] = self.T_supply
        self.var_dic["m_w"] = self.water_flow
        if self.water_flow > 0:
            self.Q_pump = sum(
                p.get_heat_gain(f) for p, f in zip(self.pumps, self.pump_flows) if f > 0
            )
            self.Q_loss = self.parameter("Q_loss").evaluate(self.var_dic)
            Q = self.Q_coils + self.Q_loss + self.Q_pump
            self.T_return = self.T_supply + Q / (rho_cp * self.water_flow)
            # water from the plant: mixed with the return to give the supply
            if abs(self.T_return - T_plant) > 1e-9:
                self.plant_flow = self.water_flow * (self.T_return - self.T_supply) / (self.T_return - T_plant)
                self.plant_flow = min(max(self.plant_flow, 0), self.water_flow)
            else:
                self.plant_flow = self.water_flow
        else:
            self.Q_pump = self.Q_loss = 0
            Q = 0
            self.T_return = self.T_supply
            self.plant_flow = 0
        # energy stored in the water of the circuit
        if self.water_volume > 0 and self.T_mean_pre is not None and self.water_flow > 0:
            T_mean = (self.T_supply + self.T_return) / 2
            self.delta_U = rho_cp * self.water_volume * (T_mean - self.T_mean_pre) / self.delta_t
        else:
            self.delta_U = 0
        self.Q_plant = Q - self.delta_U
        # the DHW part of the load given to the plant, in proportion to the coils'
        dhw = self.Q_plant * self.Q_dhw / self.Q_coils if self.Q_coils != 0 else 0.0
        if self.Q_plant != 0 or self.plant_flow != 0:
            self.plant.add_coil_load(self.Q_plant, self.plant_flow, dhw)
        # the coils add their load again in the next iteration
        self.Q_coils_used, self.coils_flow_used = self.Q_coils, self.coils_flow
        self.Q_coils = self.coils_flow = 0
        self.Q_dhw_used, self.Q_dhw = self.Q_dhw, 0
        self.Q_heat_used, self.Q_heat = self.Q_heat, 0
        self.Q_cool_used, self.Q_cool = self.Q_cool, 0
        return True

    def _iteration_tank(self):
        """Charging circuit: the tank, fully mixed, takes the load of its coils, its
        losses and the charge from the plant (water of the plant in, water of the tank
        back), and the heat of its pumps while they run."""
        T_pre = self.T_tank_pre
        rho_cp = self.props["RHOCP_W"](T_pre) / 1000  # W/(dm³·K)
        C = rho_cp * self.tank.get_volume() / self.delta_t
        self.var_dic["T_w"] = T_pre
        self.var_dic["m_w"] = self.design_flow
        self.Q_tank_loss = -self.tank.get_loss(T_pre)
        self.Q_loss = (self.parameter("Q_loss").evaluate(self.var_dic) + self.Q_tank_loss
                       if self._on_off else self.Q_tank_loss)
        Q_free = (self.Q_coils if self._on_off else 0) + self.Q_loss
        T_free = T_pre + Q_free / C
        T_plant = self.plant.get_heating_coil_inlet_T()
        self.T_plant = T_plant
        fraction = Q_charge = Q_pump_full = 0
        start = self.charging_pre or T_free < self.tank_sp - self.tank.get_dead_band()
        if (start and self.on_off and self.plant.can_heat() and T_free < self.tank_sp
                and T_plant > T_free and self.design_flow > 0):
            Q_need = C * (self.tank_sp - T_free)
            Q_max = rho_cp * self.design_flow * (T_plant - T_free)  # pumps the whole step
            Q_pump_full = sum(p.get_heat_gain(p.parameter("nominal_water_flow").value)
                              for p in self.pumps)
            fraction = min(Q_need / (Q_max + Q_pump_full), 1)
            Q_charge = fraction * Q_max
        self.pump_fraction = fraction
        self.water_flow = self.plant_flow = fraction * self.design_flow  # mean of the step
        self.Q_pump = fraction * Q_pump_full
        self.T_tank = T_free + (Q_charge + self.Q_pump) / C
        self.T_supply = self.T_tank
        self.T_return = self.T_tank  # charging water back to the plant
        self.delta_U = C * (self.T_tank - T_pre)
        self.Q_plant = -Q_charge
        dhw = self.Q_plant if self.is_dhw_only() else (
            self.Q_plant * self.Q_dhw / self.Q_coils if self.Q_coils != 0 else 0.0)
        if self.Q_plant != 0 or self.plant_flow != 0:
            self.plant.add_coil_load(self.Q_plant, self.plant_flow, dhw)
        self.Q_coils_used, self.coils_flow_used = self.Q_coils, self.coils_flow
        self.Q_coils = self.coils_flow = 0
        self.Q_dhw_used, self.Q_dhw = self.Q_dhw, 0
        self.Q_heat_used, self.Q_heat = self.Q_heat, 0
        self.Q_cool_used, self.Q_cool = self.Q_cool, 0
        return True

    def is_dhw_only(self):
        """True if all the loads of the circuit are DHW demands."""
        if getattr(self, "_dhw_only", None) is None:
            users = self.referring_components(
                ["DHW_demand", "HVAC_water_circuit", "HVAC_SZW_system", "HVAC_MZW_system"])
            self._dhw_only = len(users) > 0 and all(
                u.parameter("type").value == "DHW_demand" for u in users)
        return self._dhw_only

    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        if self.tank is not None:
            return self._post_iteration_tank(time_index)
        on = self.water_flow > 0
        values = {
            "T_plant": self.T_plant,
            "T_supply": self.T_supply,
            "T_return": self.T_return,
            "water_flow": self.water_flow,
            "plant_flow": self.plant_flow,
            "mixing_flow": self.water_flow - self.plant_flow,
            "coils_flow": self.coils_flow_used,
            "Q_loads": self.Q_coils_used if on else 0,
            "Q_heating_coils": self.Q_heat_used if on else 0,
            "Q_cooling_coils": self.Q_cool_used if on else 0,
            "Q_dhw": self.Q_dhw_used if on else 0,
            "Q_loss": self.Q_loss,
            "Q_pump": self.Q_pump,
            "delta_U": self.delta_U,
            "Q_plant": self.Q_plant,
            "pumps_power": sum(
                p.get_power(f) for p, f in zip(self.pumps, self.pump_flows) if f > 0
            ) if on else 0,
        }
        for key, value in values.items():
            self.variable(key).values[time_index] = value

    def get_energy_use(self):
        """Electricity of its pumps (water transport).

        Returns:
            list: `Energy_use` items (W at each time step).
        """
        plant = self.parameter("water_system").component
        coils = np.asarray(self.variable("Q_loads").values, dtype=float)
        dhw = np.asarray(self.variable("Q_dhw").values, dtype=float)
        share = np.clip(np.divide(dhw, coils, out=np.zeros_like(coils), where=coils < 0), 0, 1)
        if self.is_dhw_only():
            share = np.ones_like(coils)
        return split_dhw("ELECTRICITY", "WATER_TRANSPORT", self.variable("pumps_power").values,
                         share, mode_from_plant(plant.variable("mode").values))

    def _post_iteration_tank(self, time_index):
        values = {
            "T_plant": self.T_plant,
            "T_supply": self.T_tank,
            "T_return": self.T_tank,
            "water_flow": self.water_flow,
            "plant_flow": self.plant_flow,
            "mixing_flow": 0,
            "coils_flow": self.coils_flow_used,
            "Q_loads": self.Q_coils_used if self._on_off else 0,
            "Q_heating_coils": self.Q_heat_used if self._on_off else 0,
            "Q_cooling_coils": self.Q_cool_used if self._on_off else 0,
            "Q_dhw": self.Q_dhw_used if self._on_off else 0,
            "Q_loss": self.Q_loss,
            "Q_pump": self.Q_pump,
            "delta_U": self.delta_U,
            "Q_plant": self.Q_plant,
            "pumps_power": self.pump_fraction * sum(
                p.get_power(p.parameter("nominal_water_flow").value) for p in self.pumps),
        }
        for key, value in values.items():
            self.variable(key).values[time_index] = value
        self.tank.set_state(time_index, self.T_tank)
