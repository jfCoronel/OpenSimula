from opensimula.Component import Component
from opensimula.Message import Message
from opensimula.Parameters import (
    Parameter_component,
    Parameter_math_exp,
    Parameter_variable_list,
)
from opensimula.Variable import Variable


class HVAC_water_generator(Component):
    """A generator of hot or chilled water of an HVAC_water_system.

    It uses an equipment component for the manufacturer's data, a
    Chiller_heat_pump (heating and/or cooling, electric) or a Boiler (heating,
    fuel), and has its own primary pump. The plant (HVAC_water_system) decides
    the load it gives in each time step; the generator turns it into the
    equipment's load, part load, power and efficiency, and stores them.
    """

    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "HVAC_water_generator"
        self.parameter("description").value = "Generator of hot or chilled water of a water system"
        self.add_parameter(
            Parameter_component("equipment", "not_defined", ["Chiller_heat_pump", "Boiler"])
        )
        self.add_parameter(Parameter_component("pump", "not_defined", ["Pump"]))
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_math_exp("system_on_off", "1", "on/off"))

        # Variables
        self.add_variable(Variable("on_off", unit="flag"))  # availability
        self.add_variable(Variable("state", unit="flag"))  # 0: off, 1: heating, -1: cooling
        self.add_variable(Variable("Q", unit="W"))  # positive heating, negative cooling
        self.add_variable(Variable("F_load", unit="frac"))
        self.add_variable(Variable("power", unit="W"))  # electric power of the equipment
        self.add_variable(Variable("fuel_power", unit="W"))  # LHV, boilers
        self.add_variable(Variable("efficiency", unit="frac"))  # EER, COP or boiler efficiency
        self.add_variable(Variable("water_flow", unit="dm³/s"))
        self.add_variable(Variable("T_wi", unit="°C"))
        self.add_variable(Variable("T_wo", unit="°C"))
        self.add_variable(Variable("pump_power", unit="W"))

    def check(self):
        errors = super().check()
        if self.parameter("equipment").value == "not_defined":
            msg = f"{self.parameter('name').value}, must define its equipment (Chiller_heat_pump or Boiler)."
            errors.append(Message(msg, "ERROR"))
        if self.project().parameter("simulation_file_met").value == "not_defined":
            msg = f"{self.parameter('name').value}, file_met must be defined in the project 'simulation_file_met'."
            errors.append(Message(msg, "ERROR"))
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self.equipment = self.parameter("equipment").component
        self.is_boiler = self.parameter("equipment").component.parameter("type").value == "Boiler"
        self.pump = self.get_pump()
        self.file_met = self.project().parameter("simulation_file_met").component

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        self.T_OA = self.file_met.variable("temperature").values[time_index]
        self.T_OAwb = self.file_met.variable("wet_bulb_temp").values[time_index]
        var_dic = self.get_parameter_variable_dictionary(time_index)
        self.on_off = self.parameter("system_on_off").evaluate(var_dic) != 0
        self.variable("on_off").values[time_index] = 1 if self.on_off else 0

    # _________________ What the plant asks _________________

    def nominal_water_flow(self):
        """Water flow of the generator (dm³/s): the nominal one of its equipment."""
        return self.parameter("equipment").component.parameter("nominal_water_flow").value

    def get_pump(self):
        """The primary pump (Pump component), None if not defined."""
        if self.parameter("pump").value == "not_defined":
            return None
        return self.parameter("pump").component

    def can_heat(self):
        """True if the equipment can heat and the generator is available."""
        if not self.on_off:
            return False
        if self.is_boiler:
            return True
        return self.equipment.parameter("chiller_type").value != "CHILLER"

    def can_cool(self):
        """True if the equipment can cool and the generator is available."""
        if not self.on_off or self.is_boiler:
            return False
        return self.equipment.parameter("chiller_type").value != "HEAT_PUMP"

    def get_heating_load(self, T_wo, T_wi, water_flow, Q_required):
        """Heat the generator gives for a required load.

        Args:
            T_wo (float): supply water temperature (°C).
            T_wi (float): return water temperature (°C).
            water_flow (float): water flow (dm³/s).
            Q_required (float): heat required (W).

        Returns:
            tuple: (Q, F_load), heat given (W) and part load fraction.
        """
        if not self.can_heat():
            return (0, 0)
        if self.is_boiler:
            return self.equipment.get_heating_load(T_wo, T_wi, water_flow, Q_required)
        return self.equipment.get_heating_load(T_wo, self.T_OA, self.T_OAwb, water_flow, Q_required)

    def get_cooling_load(self, T_wo, T_wi, water_flow, Q_required):
        """Cold the generator gives for a required cooling load (both positive).

        Args:
            T_wo (float): supply water temperature (°C).
            T_wi (float): return water temperature (°C).
            water_flow (float): water flow (dm³/s).
            Q_required (float): cooling required (W, positive).

        Returns:
            tuple: (Q, F_load), cooling given (W, positive) and part load fraction.
        """
        if not self.can_cool():
            return (0, 0)
        return self.equipment.get_cooling_load(T_wo, self.T_OA, self.T_OAwb, water_flow, Q_required)

    def get_pump_heat(self, water_flow):
        """Heat of the primary pump to the water (W)."""
        return 0 if self.pump is None else self.pump.get_heat_gain(water_flow)

    def get_pump_power(self, water_flow):
        """Electric power of the primary pump (W)."""
        return 0 if self.pump is None or water_flow == 0 else self.pump.get_power(water_flow)

    def set_operation(self, time_index, Q, T_wo, T_wi, water_flow):
        """Store the operation of the time step decided by the plant.

        Args:
            time_index (int): time index.
            Q (float): heat given to the water (W), positive heating, negative cooling.
            T_wo (float): supply water temperature (°C).
            T_wi (float): return water temperature (°C).
            water_flow (float): water flow (dm³/s).

        Returns:
            tuple: (power, efficiency, F_load) of the equipment: electric power (W),
                EER, COP or boiler efficiency, and part load.
        """
        power = fuel = efficiency = F_load = 0
        if Q > 0:
            if self.is_boiler:
                _, F_load = self.equipment.get_heating_load(T_wo, T_wi, water_flow, Q)
                fuel, efficiency = self.equipment.get_fuel_power(T_wo, T_wi, water_flow, Q)
                power = self.equipment.get_auxiliary_power(Q)
            else:
                _, F_load = self.equipment.get_heating_load(T_wo, self.T_OA, self.T_OAwb, water_flow, Q)
                power, efficiency = self.equipment.get_heating_power(T_wo, self.T_OA, self.T_OAwb, water_flow, Q)
        elif Q < 0:
            _, F_load = self.equipment.get_cooling_load(T_wo, self.T_OA, self.T_OAwb, water_flow, -Q)
            power, efficiency = self.equipment.get_cooling_power(T_wo, self.T_OA, self.T_OAwb, water_flow, -Q)
        self.variable("state").values[time_index] = 1 if Q > 0 else (-1 if Q < 0 else 0)
        self.variable("Q").values[time_index] = Q
        self.variable("F_load").values[time_index] = F_load
        self.variable("power").values[time_index] = power
        self.variable("fuel_power").values[time_index] = fuel
        self.variable("efficiency").values[time_index] = efficiency
        self.variable("water_flow").values[time_index] = water_flow
        self.variable("T_wi").values[time_index] = T_wi
        self.variable("T_wo").values[time_index] = T_wo
        self.variable("pump_power").values[time_index] = self.get_pump_power(water_flow)
        return (power, efficiency, F_load)
