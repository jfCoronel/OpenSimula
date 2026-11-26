from opensimula.Component import Component
from opensimula.Message import Message
from opensimula.Parameters import (
    Parameter_component,
    Parameter_float,
    Parameter_float_list,
    Parameter_math_exp,
    Parameter_variable_list,
)
from opensimula.Variable import Variable

# Mains water temperature of Sevilla by month, °C (DB-HE, Anejo G, table a)
SEVILLA_MAINS = [11, 11, 13, 14, 16, 19, 21, 21, 20, 16, 13, 11]


class DHW_demand(Component):
    """Demand of domestic hot water (DHW) served by a water plant or circuit.

    The demand is the instantaneous use of hot water (l/h) at a use temperature (60 °C
    by default, as the DB-HE gives the volumes), both expressions: the volume usually
    follows a schedule (for dwellings, the hourly profile of the DB-HE, Anejo D table
    c) or a data file. Each time step it takes
    from its plant or circuit the heat to warm that water from the mains temperature:
    the plant sees it as one more coil, which takes water at the supply temperature
    and gives it back at the mains temperature (the water drawn is replaced by mains
    water). Distribution losses of networks without recirculation are a fraction of
    the demand; a recirculation loop is a circuit with its losses and pump.

    Water hotter than the use temperature is mixed with mains water by the user (the
    same heat, less water from the plant). Water colder than the use temperature is
    used as it comes: only the heat from the mains to the supply temperature is met,
    the rest is unmet (`Q_unmet`) and the time step is flagged (`low_temperature`).
    A plant that is off or cannot heat (e.g. a two-pipe plant cooling) meets nothing.
    """

    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "DHW_demand"
        self.parameter("description").value = "Domestic hot water demand."
        self.add_parameter(Parameter_component("water_system", "not_defined",
                                               ["HVAC_water_system", "HVAC_water_circuit"]))
        # preheating in series (e.g. a solar tank): the water enters it instead of the
        # mains and the water_system heats it from there
        self.add_parameter(Parameter_component("preheat_system", "not_defined",
                                               ["HVAC_water_system", "HVAC_water_circuit"]))
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_math_exp("volume_flow", "0", "l/h"))
        self.add_parameter(Parameter_math_exp("use_temperature", "60", "°C"))
        self.add_parameter(Parameter_float_list("mains_monthly_temperatures", SEVILLA_MAINS, "°C"))
        self.add_parameter(Parameter_math_exp("mains_temperature", "T_month", "°C"))
        self.add_parameter(Parameter_float("distribution_losses", 0, "frac", min=0))
        self.add_variable(Variable("volume_flow", unit="l/h"))  # at the use temperature
        self.add_variable(Variable("T_use", unit="°C"))
        self.add_variable(Variable("T_mains", unit="°C"))
        self.add_variable(Variable("T_preheat", unit="°C"))  # of the preheat system
        self.add_variable(Variable("T_supply", unit="°C"))  # of the plant or circuit
        self.add_variable(Variable("water_flow", unit="dm³/s"))  # from the plant, at T_supply
        self.add_variable(Variable("Q_demand", unit="W"))  # with distribution losses
        self.add_variable(Variable("Q_preheat", unit="W"))  # given by the preheat system
        self.add_variable(Variable("Q_supplied", unit="W"))
        self.add_variable(Variable("Q_unmet", unit="W"))
        self.add_variable(Variable("low_temperature", unit="flag"))

    def check(self):
        errors = super().check()
        name = self.parameter("name").value
        if self.parameter("water_system").value == "not_defined":
            errors.append(Message(f"Error: {name}, water_system must be defined", "ERROR"))
        if len(self.parameter("mains_monthly_temperatures").value) != 12:
            errors.append(Message(
                f"Error: {name}, mains_monthly_temperatures must have 12 values", "ERROR"))
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self.props = self._sim_.props
        self.plant = self.parameter("water_system").component
        self.preheat = (self.parameter("preheat_system").component
                        if self.parameter("preheat_system").value != "not_defined" else None)

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        var_dic = self.get_parameter_variable_dictionary(time_index)
        var_dic["T_month"] = self.parameter("mains_monthly_temperatures").value[date.month - 1]
        self.T_mains = self.parameter("mains_temperature").evaluate(var_dic)
        self.volume_flow = max(self.parameter("volume_flow").evaluate(var_dic), 0)  # l/h at T_use
        self.T_use = self.parameter("use_temperature").evaluate(var_dic)
        rho_cp = self.props["RHOCP_W"](self.T_use) / 1000  # J/(dm³·K)
        self.Q_demand = (rho_cp * self.volume_flow / 3600 * max(self.T_use - self.T_mains, 0)
                         * (1 + self.parameter("distribution_losses").value))
        self.T_supply = self.T_preheat = self.T_mains
        self.water_flow = 0
        self.Q_supplied = self.Q_preheat = 0
        self.too_cold = False

    def iteration(self, time_index, date, daylight_saving, n_iter):
        super().iteration(time_index, date, daylight_saving, n_iter)
        # preheating: the water drawn enters the preheat system (mains water replaces
        # it) and gives the heat up to its temperature (all of it, mixed, if hotter)
        T_in = self.T_mains
        self.Q_preheat = 0
        if self.preheat is not None:
            self.T_preheat = self.preheat.get_heating_coil_inlet_T()
            dT_pre = self.T_preheat - self.T_mains
            if self.Q_demand > 0 and self.preheat.can_heat() and dT_pre > 0:
                self.Q_preheat = self.Q_demand * min(dT_pre / (self.T_use - self.T_mains), 1)
                rho_cp = self.props["RHOCP_W"](self.T_preheat) / 1000
                self.preheat.add_coil_load(-self.Q_preheat, self.Q_preheat / (rho_cp * dT_pre),
                                           -self.Q_preheat)
                T_in = min(self.T_preheat, self.T_use)
        Q_rest = self.Q_demand - self.Q_preheat
        # the water system heats the rest, from T_in (a plant with DHW priority gives
        # water at its setpoint, up to the capacity of its generators)
        priority = getattr(self.plant, "dhw_priority", False)
        self.T_supply = (self.plant.dhw_supply_T() if priority
                         else self.plant.get_heating_coil_inlet_T())
        can_heat = Q_rest > 0 and self.plant.can_heat()
        self.too_cold = can_heat and self.T_supply < self.T_use
        dT = self.T_supply - T_in
        if not can_heat or dT <= 0:
            self.Q_supplied = self.Q_preheat
            self.water_flow = 0
            return True
        # hotter than T_use: mixed with mains water, the whole demand; colder: used as
        # it comes, only the heat up to T_supply
        Q = Q_rest * min(dT / (self.T_use - T_in), 1)
        if priority:
            Q = self.plant.take_dhw_heat(Q)
        rho_cp = self.props["RHOCP_W"](self.T_supply) / 1000
        self.water_flow = Q / (rho_cp * dT)  # from the plant, at T_supply
        self.plant.add_coil_load(-Q, self.water_flow, -Q)
        self.Q_supplied = self.Q_preheat + Q
        return True

    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        values = {
            "volume_flow": self.volume_flow,
            "T_use": self.T_use,
            "T_mains": self.T_mains,
            "T_preheat": self.T_preheat,
            "T_supply": self.T_supply,
            "water_flow": self.water_flow,
            "Q_demand": self.Q_demand,
            "Q_preheat": self.Q_preheat,
            "Q_supplied": self.Q_supplied,
            "Q_unmet": self.Q_demand - self.Q_supplied,
            "low_temperature": float(self.too_cold),
        }
        for key, value in values.items():
            self.variable(key).values[time_index] = value
