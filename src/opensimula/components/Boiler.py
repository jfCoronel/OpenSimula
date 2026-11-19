from opensimula.Component import Component
from opensimula.Message import Message
from opensimula.Parameters import (
    Parameter_float,
    Parameter_float_list,
    Parameter_math_exp,
    Parameter_options,
)

FUELS = ["NATURAL_GAS", "LPG", "DIESEL", "BIOMASS", "ELECTRICITY"]


class Boiler(Component):
    """Boiler equipment manufacturer information.

    Equipment data, like DX_unit or Chiller_heat_pump: it is not simulated by
    itself but used by a water generator to know the heat it can give and the
    fuel it uses. Capacities, powers and efficiencies are on the lower heating
    value (LHV) of the fuel.

    The efficiency is the nominal one multiplied by ``efficiency_expression``, a
    function of the part load ``F_load`` and of the water temperatures, return
    ``T_wi`` and supply ``T_wo``, and of the water flow fraction ``F_water``: a
    condensing boiler is more efficient with a cold return.
    """

    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Boiler"
        self.parameter("description").value = "Boiler equipment manufacturer information"
        self.add_parameter(Parameter_options("fuel", "NATURAL_GAS", FUELS))
        self.add_parameter(Parameter_float("nominal_heating_capacity", 0, "W", min=0))
        self.add_parameter(Parameter_float("nominal_efficiency", 0.9, "frac", min=0.01))
        self.add_parameter(Parameter_float("nominal_water_flow", 1, "dm³/s", min=0))
        self.add_parameter(Parameter_float("max_supply_temperature", 80, "°C"))
        self.add_parameter(Parameter_math_exp("efficiency_expression", "1", "frac"))
        self.add_parameter(Parameter_float("auxiliary_power", 0, "W", min=0))
        # T_wi, T_wo, F_water, F_load
        self.add_parameter(Parameter_float_list("expression_max_values", [100, 100, 1.5, 1], "-"))
        self.add_parameter(Parameter_float_list("expression_min_values", [0, 0, 0, 0], "-"))

    def check(self):
        errors = super().check()
        for key in ("expression_max_values", "expression_min_values"):
            if len(self.parameter(key).value) != 4:
                msg = f"Error: {self.parameter('name').value}, {key} size must be 4 (T_wi, T_wo, F_water, F_load)"
                errors.append(Message(msg, "ERROR"))
        return errors

    def get_heating_load(self, T_wo, T_wi, water_flow, Q_required):
        """Heat the boiler gives for a required load.

        Args:
            T_wo (float): supply (outlet) water temperature (°C).
            T_wi (float): return (inlet) water temperature (°C).
            water_flow (float): water flow (dm³/s).
            Q_required (float): heat required (W).

        Returns:
            tuple: (Q, F_load), heat given (W), at most the nominal capacity, and part
                load fraction (0-1). (0, 0) if no heat is required, the capacity is 0
                or the supply temperature is above the maximum.
        """
        capacity = self.parameter("nominal_heating_capacity").value
        if Q_required <= 0 or capacity <= 0:
            return (0, 0)
        if T_wo > self.parameter("max_supply_temperature").value:
            return (0, 0)
        if Q_required >= capacity:
            return (capacity, 1)
        return (Q_required, Q_required / capacity)

    def get_efficiency(self, T_wo, T_wi, water_flow, F_load):
        """Efficiency on the LHV at the given conditions.

        Args:
            T_wo (float): supply water temperature (°C).
            T_wi (float): return water temperature (°C).
            water_flow (float): water flow (dm³/s).
            F_load (float): part load fraction (0-1).

        Returns:
            float: efficiency (heat given / fuel power).
        """
        F_water = water_flow / self.parameter("nominal_water_flow").value
        var_dic = self._var_state_dic([T_wi, T_wo, F_water, F_load])
        return self.parameter("nominal_efficiency").value * self.parameter(
            "efficiency_expression"
        ).evaluate(var_dic)

    def get_fuel_power(self, T_wo, T_wi, water_flow, Q_required):
        """Fuel the boiler uses for a required load.

        Args:
            T_wo (float): supply water temperature (°C).
            T_wi (float): return water temperature (°C).
            water_flow (float): water flow (dm³/s).
            Q_required (float): heat required (W).

        Returns:
            tuple: (fuel_power, efficiency), fuel power on the LHV (W) and efficiency;
                (0, 0) if the boiler gives no heat.
        """
        Q, F_load = self.get_heating_load(T_wo, T_wi, water_flow, Q_required)
        if Q == 0:
            return (0, 0)
        efficiency = self.get_efficiency(T_wo, T_wi, water_flow, F_load)
        return (Q / efficiency, efficiency)

    def get_auxiliary_power(self, Q):
        """Electric power of the burner fan and controls.

        Args:
            Q (float): heat given (W).

        Returns:
            float: auxiliary_power while the boiler gives heat, 0 otherwise (W).
        """
        return self.parameter("auxiliary_power").value if Q > 0 else 0

    def _var_state_dic(self, values):
        maximum = self.parameter("expression_max_values").value
        minimum = self.parameter("expression_min_values").value
        values = [min(max(v, lo), hi) for v, lo, hi in zip(values, minimum, maximum)]
        return {"T_wi": values[0], "T_wo": values[1], "F_water": values[2], "F_load": values[3]}
