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
        # mixing valve: the supply is never above the heating setpoint nor below the
        # cooling one ("": no limit, the water of the plant)
        self.add_parameter(Parameter_math_exp("heating_supply_setpoint", "", "°C"))
        self.add_parameter(Parameter_math_exp("cooling_supply_setpoint", "", "°C"))
        self.add_parameter(Parameter_math_exp("Q_loss", "0", "W"))
        self.add_parameter(Parameter_float("water_volume", 0, "dm³", min=0))

        # Variables
        self.add_variable(Variable("on_off", unit="flag"))
        self.add_variable(Variable("T_plant", unit="°C"))  # water from the plant
        self.add_variable(Variable("T_supply", unit="°C"))
        self.add_variable(Variable("T_return", unit="°C"))
        self.add_variable(Variable("water_flow", unit="dm³/s"))  # moved by its pumps
        self.add_variable(Variable("plant_flow", unit="dm³/s"))  # taken from the plant
        self.add_variable(Variable("mixing_flow", unit="dm³/s"))  # return mixed in the supply
        self.add_variable(Variable("coils_flow", unit="dm³/s"))
        self.add_variable(Variable("Q_coils", unit="W"))
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
        self.Q_coils = self.coils_flow = 0
        self.Q_coils_used = self.coils_flow_used = 0
        self.water_flow = 0
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
        """Water temperature to the heating coils (°C)."""
        return self._supply(self.plant.get_heating_coil_inlet_T(), 1)

    def get_cooling_coil_inlet_T(self):
        """Water temperature to the cooling coils (°C)."""
        return self._supply(self.plant.get_cooling_coil_inlet_T(), -1)

    def add_coil_load(self, Q_coil, water_flow=0):
        """Add the load of a coil in this iteration.

        Args:
            Q_coil (float): heat the coil gives to the water (W), positive when it heats
                the water (cooling coil), negative when it cools it (heating coil).
            water_flow (float, optional): water flow through the coil (dm³/s).
        """
        self.Q_coils += Q_coil
        self.coils_flow += water_flow

    # _________________ Iteration: the load to the plant _________________

    def iteration(self, time_index, date, daylight_saving, n_iter):
        super().iteration(time_index, date, daylight_saving, n_iter)
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
        self.water_flow = self.design_flow if pumps_on else 0
        rho_cp = self.props["RHOCP_W"](self.T_supply) / 1000  # W/(dm³·K)
        self.var_dic["T_w"] = self.T_supply
        self.var_dic["m_w"] = self.water_flow
        if self.water_flow > 0:
            self.Q_pump = sum(
                p.get_heat_gain(p.parameter("nominal_water_flow").value) for p in self.pumps
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
        if self.Q_plant != 0 or self.plant_flow != 0:
            self.plant.add_coil_load(self.Q_plant, self.plant_flow)
        # the coils add their load again in the next iteration
        self.Q_coils_used, self.coils_flow_used = self.Q_coils, self.coils_flow
        self.Q_coils = self.coils_flow = 0
        return True

    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        on = self.water_flow > 0
        values = {
            "T_plant": self.T_plant,
            "T_supply": self.T_supply,
            "T_return": self.T_return,
            "water_flow": self.water_flow,
            "plant_flow": self.plant_flow,
            "mixing_flow": self.water_flow - self.plant_flow,
            "coils_flow": self.coils_flow_used,
            "Q_coils": self.Q_coils_used if on else 0,
            "Q_loss": self.Q_loss,
            "Q_pump": self.Q_pump,
            "delta_U": self.delta_U,
            "Q_plant": self.Q_plant,
            "pumps_power": sum(
                p.get_power(p.parameter("nominal_water_flow").value) for p in self.pumps
            ) if on else 0,
        }
        for key, value in values.items():
            self.variable(key).values[time_index] = value
