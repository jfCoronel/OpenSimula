import numpy as np

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

# Hourly profile of the DHW use of dwellings, % of the daily demand (DB-HE, Anejo D,
# table c)
CTE_HOURLY_PROFILE = [1, 0, 0, 0, 0, 1, 3, 10, 7, 7, 6, 6, 5, 5, 4, 3, 4, 4, 5, 7, 6, 6, 5, 5]
# Mains water temperature of Sevilla by month, °C (DB-HE, Anejo G, table a)
SEVILLA_MAINS = [11, 11, 13, 14, 16, 19, 21, 21, 20, 16, 13, 11]


class DHW_demand(Component):
    """Demand of domestic hot water (DHW) served by a water plant or circuit.

    The demand is a daily volume of hot water at a reference temperature (60 °C, as
    the DB-HE gives it) spread over the day by an hourly profile. Each hour it takes
    from its plant or circuit the heat to warm that water from the mains temperature:
    the plant sees it as one more coil, which takes water at the supply temperature
    and gives it back at the mains temperature (the water drawn is replaced by mains
    water). Distribution losses of networks without recirculation are a fraction of
    the demand; a recirculation loop is a circuit with its losses and pump.

    The plant must give water at least at `minimum_temperature`: otherwise (plant off,
    cooling, or too cold) the demand is not met that hour (`Q_unmet`), and the hours
    it is so because the water is too cold are flagged (`low_temperature`).
    """

    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "DHW_demand"
        self.parameter("description").value = "Domestic hot water demand."
        self.add_parameter(Parameter_component("water_system", "not_defined",
                                               ["HVAC_water_system", "HVAC_water_circuit"]))
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_math_exp("daily_volume", "100", "l/day"))
        self.add_parameter(Parameter_float("reference_temperature", 60, "°C"))
        self.add_parameter(Parameter_float_list("hourly_profile", CTE_HOURLY_PROFILE, "%", min=0))
        self.add_parameter(Parameter_float_list("mains_monthly_temperatures", SEVILLA_MAINS, "°C"))
        self.add_parameter(Parameter_math_exp("mains_temperature", "T_month", "°C"))
        self.add_parameter(Parameter_float("distribution_losses", 0, "frac", min=0))
        self.add_parameter(Parameter_float("minimum_temperature", 45, "°C"))
        self.add_variable(Variable("daily_volume", unit="l/day"))
        self.add_variable(Variable("volume_flow", unit="l/h"))  # at the reference temperature
        self.add_variable(Variable("T_mains", unit="°C"))
        self.add_variable(Variable("T_supply", unit="°C"))  # of the plant or circuit
        self.add_variable(Variable("water_flow", unit="dm³/s"))  # from the plant, at T_supply
        self.add_variable(Variable("Q_demand", unit="W"))  # with distribution losses
        self.add_variable(Variable("Q_supplied", unit="W"))
        self.add_variable(Variable("Q_unmet", unit="W"))
        self.add_variable(Variable("low_temperature", unit="flag"))

    def check(self):
        errors = super().check()
        name = self.parameter("name").value
        if self.parameter("water_system").value == "not_defined":
            errors.append(Message(f"Error: {name}, water_system must be defined", "ERROR"))
        if len(self.parameter("hourly_profile").value) != 24:
            errors.append(Message(f"Error: {name}, hourly_profile must have 24 values", "ERROR"))
        elif sum(self.parameter("hourly_profile").value) <= 0:
            errors.append(Message(f"Error: {name}, hourly_profile must not be all zero", "ERROR"))
        if len(self.parameter("mains_monthly_temperatures").value) != 12:
            errors.append(Message(
                f"Error: {name}, mains_monthly_temperatures must have 12 values", "ERROR"))
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self.props = self._sim_.props
        self.plant = self.parameter("water_system").component
        profile = np.asarray(self.parameter("hourly_profile").value, dtype=float)
        self.profile = profile / profile.sum()

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        var_dic = self.get_parameter_variable_dictionary(time_index)
        var_dic["T_month"] = self.parameter("mains_monthly_temperatures").value[date.month - 1]
        self.T_mains = self.parameter("mains_temperature").evaluate(var_dic)
        self.daily = max(self.parameter("daily_volume").evaluate(var_dic), 0)
        self.volume_flow = self.daily * self.profile[date.hour]  # l/h at T_ref
        T_ref = self.parameter("reference_temperature").value
        rho_cp = self.props["RHOCP_W"](T_ref) / 1000  # J/(dm³·K)
        self.Q_demand = (rho_cp * self.volume_flow / 3600 * max(T_ref - self.T_mains, 0)
                         * (1 + self.parameter("distribution_losses").value))
        self.T_supply = self.T_mains
        self.water_flow = 0
        self.supplied = False
        self.too_cold = False

    def iteration(self, time_index, date, daylight_saving, n_iter):
        super().iteration(time_index, date, daylight_saving, n_iter)
        self.T_supply = self.plant.get_heating_coil_inlet_T()
        self.too_cold = self.T_supply < self.parameter("minimum_temperature").value
        self.supplied = self.Q_demand > 0 and self.plant.can_heat() and not self.too_cold
        if not self.supplied:
            self.water_flow = 0
            return True
        rho_cp = self.props["RHOCP_W"](self.T_supply) / 1000
        dT = self.T_supply - self.T_mains
        # the water taken from the plant to give the heat of the demand
        if dT > 1:
            self.water_flow = self.Q_demand / (rho_cp * dT)
        else:
            self.water_flow = self.volume_flow / 3600
        self.plant.add_coil_load(-self.Q_demand, self.water_flow, -self.Q_demand)
        return True

    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        supplied = self.Q_demand if self.supplied else 0
        values = {
            "daily_volume": self.daily,
            "volume_flow": self.volume_flow,
            "T_mains": self.T_mains,
            "T_supply": self.T_supply,
            "water_flow": self.water_flow,
            "Q_demand": self.Q_demand,
            "Q_supplied": supplied,
            "Q_unmet": self.Q_demand - supplied,
            "low_temperature": float(self.Q_demand > 0 and self.plant.can_heat()
                                     and self.too_cold),
        }
        for key, value in values.items():
            self.variable(key).values[time_index] = value
