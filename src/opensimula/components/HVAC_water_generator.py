import numpy as np
from opensimula.Component import Component
from opensimula.Message import Message
from opensimula.Parameters import (
    Parameter_component,
    Parameter_int,
    Parameter_math_exp,
    Parameter_variable_list,
)
from opensimula.Variable import Variable
from opensimula.energy import Energy_use, mode_from_plant, positive, where


class HVAC_water_generator(Component):
    """A generator of hot or chilled water of an HVAC_water_system.

    It uses an equipment component for the manufacturer's data, a
    Chiller_heat_pump (heating and/or cooling, electric) or a Boiler (heating,
    fuel), and has its own primary pump. The plant (HVAC_water_system) decides
    the load it gives in each time step; the generator turns it into the
    equipment's load, part load, power and efficiency, and stores them.

    It may have ``number_of_units`` identical units of the equipment, in
    parallel: its capacity and water flow are those of one unit times the number
    of units, and the load is shared among them with the sequencing of the plant
    (PRIORITY: one unit after the other; EQUAL_LOAD: all at the same part load).
    """

    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "HVAC_water_generator"
        self.parameter("description").value = "Generator of hot or chilled water of a water system"
        self.add_parameter(
            Parameter_component("equipment", "not_defined", ["Chiller_heat_pump", "Boiler"])
        )
        self.add_parameter(Parameter_int("number_of_units", 1, "", min=1))
        self.add_parameter(Parameter_component("pump", "not_defined", ["Pump"]))
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_math_exp("system_on_off", "1", "on/off"))

        # Variables
        self.add_variable(Variable("on_off", unit="flag"))  # availability
        self.add_variable(Variable("state", unit="flag"))  # 0: off, 1: heating, -1: cooling
        self.add_variable(Variable("Q", unit="W"))  # positive heating, negative cooling
        self.add_variable(Variable("F_load", unit="frac"))
        self.add_variable(Variable("units_on", unit="-"))
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
        self.n_units = self.parameter("number_of_units").value
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
        """Water flow of the generator (dm³/s): the nominal one of its equipment times
        the number of units."""
        equipment = self.parameter("equipment").component
        return equipment.parameter("nominal_water_flow").value * self.parameter("number_of_units").value

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
        return self._load_of_units(1, T_wo, T_wi, water_flow, Q_required)

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
        return self._load_of_units(-1, T_wo, T_wi, water_flow, Q_required)

    def get_capacity(self, mode, T_wo, T_wi, water_flow):
        """Heat (mode 1) or cold (mode -1) the generator gives at full load (W, positive)."""
        if (mode == 1 and not self.can_heat()) or (mode == -1 and not self.can_cool()):
            return 0
        return self.n_units * self._unit_capacity(mode, T_wo, T_wi, water_flow / self.n_units)

    def _unit_load(self, mode, T_wo, T_wi, flow, Q):
        """(Q, F_load) of one unit for a required load Q (positive)."""
        if mode == 1:
            if self.is_boiler:
                return self.equipment.get_heating_load(T_wo, T_wi, flow, Q)
            return self.equipment.get_heating_load(T_wo, self.T_OA, self.T_OAwb, flow, Q)
        return self.equipment.get_cooling_load(T_wo, self.T_OA, self.T_OAwb, flow, Q)

    def _unit_capacity(self, mode, T_wo, T_wi, flow):
        return self._unit_load(mode, T_wo, T_wi, flow, float("inf"))[0]

    def _load_of_units(self, mode, T_wo, T_wi, water_flow, Q_required):
        if self.n_units == 1:
            return self._unit_load(mode, T_wo, T_wi, water_flow, Q_required)
        if Q_required <= 0:
            return (0, 0)
        capacity = self.get_capacity(mode, T_wo, T_wi, water_flow)
        if capacity <= 0:
            return (0, 0)
        if Q_required >= capacity:
            return (capacity, 1)
        return (Q_required, Q_required / capacity)

    def _unit_loads(self, Q, capacity_unit, sequencing):
        """Loads of the units (positive) sharing Q."""
        n = self.n_units
        if n == 1:
            return [Q]
        if sequencing == "EQUAL_LOAD":
            return [Q / n] * n
        loads = []
        rest = Q
        for _ in range(n):
            q = min(rest, capacity_unit)
            loads.append(q)
            rest -= q
        return loads

    def _unit_operation(self, mode, T_wo, T_wi, flow, q):
        """(electric power, fuel power, efficiency) of one unit giving q (positive)."""
        if q <= 0:
            return (0, 0, 0)
        if mode == 1:
            if self.is_boiler:
                fuel, eff = self.equipment.get_fuel_power(T_wo, T_wi, flow, q)
                return (self.equipment.get_auxiliary_power(q), fuel, eff)
            power, eff = self.equipment.get_heating_power(T_wo, self.T_OA, self.T_OAwb, flow, q)
            return (power, 0, eff)
        power, eff = self.equipment.get_cooling_power(T_wo, self.T_OA, self.T_OAwb, flow, q)
        return (power, 0, eff)

    def get_pump_heat(self, water_flow):
        """Heat of the primary pump to the water (W)."""
        return 0 if self.pump is None or water_flow == 0 else self.pump.get_heat_gain(water_flow)

    def get_pump_power(self, water_flow):
        """Electric power of the primary pump (W)."""
        return 0 if self.pump is None or water_flow == 0 else self.pump.get_power(water_flow)

    def set_operation(self, time_index, Q, T_wo, T_wi, water_flow, sequencing="PRIORITY"):
        """Store the operation of the time step decided by the plant.

        Args:
            time_index (int): time index.
            Q (float): heat given to the water (W), positive heating, negative cooling.
            T_wo (float): supply water temperature (°C).
            T_wi (float): return water temperature (°C).
            water_flow (float): water flow (dm³/s).
            sequencing (str, optional): how the units share the load, "PRIORITY" or
                "EQUAL_LOAD". Defaults to "PRIORITY".

        Returns:
            tuple: (power, fuel_power, F_load): electric power (W), fuel power on the
                LHV (W) and part load of the generator.
        """
        power = fuel = efficiency = F_load = 0
        units_on = 0
        if Q != 0:
            mode = 1 if Q > 0 else -1
            flow = water_flow / self.n_units
            if self.n_units == 1:
                _, F_load = self._unit_load(mode, T_wo, T_wi, flow, abs(Q))
                loads = [abs(Q)]
            else:
                capacity_unit = self._unit_capacity(mode, T_wo, T_wi, flow)
                loads = self._unit_loads(abs(Q), capacity_unit, sequencing)
                F_load = abs(Q) / (self.n_units * capacity_unit) if capacity_unit > 0 else 0
            for q in loads:
                p, f, efficiency = self._unit_operation(mode, T_wo, T_wi, flow, q)
                power += p
                fuel += f
                units_on += 1 if q > 0 else 0
            if self.n_units > 1:  # of the generator: heat / power (fuel for a boiler)
                used = fuel if self.is_boiler else power
                efficiency = abs(Q) / used if used > 0 else 0
        self.variable("state").values[time_index] = 1 if Q > 0 else (-1 if Q < 0 else 0)
        self.variable("Q").values[time_index] = Q
        self.variable("F_load").values[time_index] = F_load
        self.variable("units_on").values[time_index] = units_on
        self.variable("power").values[time_index] = power
        self.variable("fuel_power").values[time_index] = fuel
        self.variable("efficiency").values[time_index] = efficiency
        self.variable("water_flow").values[time_index] = water_flow
        self.variable("T_wi").values[time_index] = T_wi
        self.variable("T_wo").values[time_index] = T_wo
        self.variable("pump_power").values[time_index] = self.get_pump_power(water_flow)
        return (power, fuel, F_load)

    def get_energy_use(self):
        """Energy of the equipment (electricity, and fuel for a boiler) for heating
        or cooling, the ambient energy a heat pump takes in heating and the
        electricity of its pump (water transport).

        Returns:
            list: `Energy_use` items (W at each time step).
        """
        v = self.variable
        Q = v("Q").values
        power = v("power").values
        heating, cooling = Q > 0, Q < 0
        # the pump works with the mode of the plant (it runs also while the
        # generator gives no heat); the plant tells its generators who it is
        plant = getattr(self, "plant", None)
        mode = mode_from_plant(plant.variable("mode").values) if plant else np.sign(Q)
        uses = [
            Energy_use("ELECTRICITY", "HEATING", where(heating, power)),
            Energy_use("ELECTRICITY", "COOLING", where(cooling, power)),
            Energy_use("ELECTRICITY", "WATER_TRANSPORT", np.array(v("pump_power").values, dtype=float),
                       mode),
        ]
        equipment = self.parameter("equipment").component
        if equipment.parameter("type").value == "Boiler":
            fuel = equipment.parameter("fuel").value
            uses.append(Energy_use(fuel, "HEATING", where(heating, v("fuel_power").values)))
        else:
            uses.append(Energy_use("AMBIENT", "HEATING", where(heating, positive(Q - power))))
        return uses
