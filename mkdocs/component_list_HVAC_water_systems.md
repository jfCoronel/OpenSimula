## Component List for water side HVAC system definition
### Pump

Component to define pump equipment for water circuits.

This equipment can be used for one or more HVAC systems.

#### Parameters
- **nominal_water_flow** [_float_, unit = "dm³/s", default = 1, min = 0]: Nominal inlet water flow.
- **nominal_pressure** [_float_, unit = "Pa", default = 1, min = 0]: Nominal pressure rise produced by the pump.
- **nominal_power** [_float_, unit = "W", default = 1, min = 0]: Electrical power consumed by the pump at nominal conditions.
- **pressure_expression** [_math_exp_, unit = "frac", default = "1"]: Mathematical expression to correct the pressure rise of the pump in conditions different from the nominal ones.
- **power_expression** [_math_exp_, unit = "frac", default = "1"]: Mathematical expression to correct the electrical power consumed by the pump in conditions different from the nominal ones.

All mathematical expressions can include the following independent variable.

- _F_water_ [frac]: Actual water flow divided by nominal water flow.


**Example:**
<pre><code class="python">
...

pump = osm.components.Pump("pump", project)
param = {
        "nominal_water_flow": 0.002,
        "nominal_pressure": 30000,
        "nominal_power": 100
}
pump.set_parameters(param)
</code></pre>


### Chiller_heat_pump

Component to define chiller and/or heat pump water equipment for cooling and/or heating.

This equipment can be used for one or more HVAC systems.

#### Parameters
- **chiller_type** [_option_, default = "CHILLER", options = ["CHILLER", "HEAT_PUMP", "CHILLER_HEAT_PUMP"]]: Type of equipment. "CHILLER" provides only cooling, "HEAT_PUMP" provides only heating, "CHILLER_HEAT_PUMP" provides both cooling and heating.
- **condensation_type** [_option_, default = "AIR_CONDENSED", options = ["AIR_CONDENSED", "WATER_CONDENSED"]]: Condensation type. "AIR_CONDENSED" for air-cooled equipment and "WATER_CONDENSED" for water-cooled equipment.
- **nominal_water_flow** [_float_, unit = "dm³/s", default = 1, min = 0]: Nominal chilled or hot water flow.
- **nominal_cooling_capacity** [_float_, unit = "W", default = 0, min = 0]: Cooling capacity at nominal cooling conditions.
- **nominal_cooling_power** [_float_, unit = "W", default = 0, min = 0]: Electrical power consumed by the equipment at nominal cooling conditions.
- **nominal_cooling_conditions** [_float-list_, unit = "ºC", default = [35, 12, 7]]: Nominal cooling conditions, in order: condenser inlet dry bulb temperature, chilled water inlet (return) temperature, chilled water outlet (supply) temperature.
- **cooling_capacity_expression** [_math_exp_, unit = "frac", default = "1"]: Mathematical expression to correct the cooling capacity of the equipment in conditions different from the nominal ones.
- **cooling_power_expression** [_math_exp_, unit = "frac", default = "1"]: Mathematical expression to correct the electrical power consumption at full load cooling operation in conditions different from the nominal ones. If left at the default value "1", the `EER_expression` will be used instead.
- **EER_expression** [_math_exp_, unit = "frac", default = "1"]: Mathematical expression to correct the EER, defined as the cooling capacity divided by the electrical power consumption, in conditions different from the nominal ones. This expression should reflect the partial load behavior of the equipment. Used only when `cooling_power_expression` is "1".
- **nominal_heating_capacity** [_float_, unit = "W", default = 0, min = 0]: Heating capacity at nominal heating conditions.
- **nominal_heating_power** [_float_, unit = "W", default = 0, min = 0]: Electrical power consumed by the equipment at nominal heating conditions.
- **nominal_heating_conditions** [_float-list_, unit = "ºC", default = [7, 6, 40, 45]]: Nominal heating conditions, in order: source inlet dry bulb temperature, source inlet wet bulb temperature, hot water inlet (return) temperature, hot water outlet (supply) temperature.
- **heating_capacity_expression** [_math_exp_, unit = "frac", default = "1"]: Mathematical expression to correct the heating capacity of the equipment in conditions different from the nominal ones.
- **heating_power_expression** [_math_exp_, unit = "frac", default = "1"]: Mathematical expression to correct the electrical power consumption at full load heating operation in conditions different from the nominal ones. If left at the default value "1", the `COP_expression` will be used instead.
- **COP_expression** [_math_exp_, unit = "frac", default = "1"]: Mathematical expression to correct the COP, defined as the heating capacity divided by the electrical power consumption, in conditions different from the nominal ones. This expression should reflect the partial load behavior of the equipment. Used only when `heating_power_expression` is "1".
- **expression_max_values** [_float-list_, unit = "-", default = [80, 50, 50, 1.5, 1]]: Maximum values allowed in the mathematical expressions. The order is [ _T_wo_ [ºC], _T_ci_ [ºC], _T_wbci_ [ºC], _F_water_ [frac], _F_load_ [frac] ]. If any variable exceeds these values, the maximum value is taken.
- **expression_min_values** [_float-list_, unit = "-", default = [0, -30, -30, 0, 0]]: Minimum values allowed in the mathematical expressions. The order is [ _T_wo_ [ºC], _T_ci_ [ºC], _T_wbci_ [ºC], _F_water_ [frac], _F_load_ [frac] ]. If any variable is lower than these values, the minimum value is taken.

All mathematical expressions can include the following independent variables.

- _T_wo_ [ºC]: Chilled (cooling) or hot (heating) water outlet temperature.
- _T_ci_ [ºC]: Condenser/source inlet dry bulb temperature (outdoor air for AIR_CONDENSED, condenser water inlet for WATER_CONDENSED).
- _T_wbci_ [ºC]: Condenser/source inlet wet bulb temperature (relevant for AIR_CONDENSED type).
- _F_water_ [frac]: Actual water flow divided by nominal water flow.

`cooling_power_expression`, `EER_expression`, `heating_power_exporession` and `COP_expression` may also include the variable _F_load_,
which represents the partial load state of the equipment, calculated as the thermal capacity
supplied at a given instant divided by the full load capacity at the current operation conditions.

**Example:**
<pre><code class="python">
...

chiller = osm.components.Chiller_heat_pump("chiller", project)
param = {
        "chiller_type": "CHILLER",
        "condensation_type": "AIR_CONDENSED",
        "nominal_water_flow": 0.003,
        "nominal_cooling_capacity": 63000,
        "nominal_cooling_power": 21000,
        "nominal_cooling_conditions": [35, 12, 7],
        "cooling_capacity_expression": "1",
        "EER_expression": "1 + 0.02 * (35 - T_ci) - 0.03 * (T_wo - 7) + 0.2 * F_load - 0.2 * F_load**2"
}
chiller.set_parameters(param)
</code></pre>

### Boiler

Component to define a boiler: hot water equipment for heating that burns a fuel (or uses electricity). Like Chiller_heat_pump it holds the manufacturer's data and is not simulated by itself: the water generator that uses it asks for the heat it can give and the fuel it uses.

Capacities, fuel power and efficiencies are on the lower heating value (LHV) of the fuel. The efficiency is the nominal one multiplied by `efficiency_expression`, which may depend on the part load and on the water temperatures: a condensing boiler condenses the water vapour of the flue gases, and is more efficient, when the return water is cold, below about 55 °C for natural gas.

This equipment can be used for one or more HVAC systems.

#### Parameters
- **fuel** [_option_, default = "NATURAL_GAS", options = ["NATURAL_GAS", "LPG", "DIESEL", "BIOMASS", "ELECTRICITY"]]: Fuel of the boiler. Informative for now; it will be used for primary energy and CO₂ emissions.
- **nominal_heating_capacity** [_float_, unit = "W", default = 0, min = 0]: Heat given at full load. The boiler gives at most this heat, whatever the water temperatures.
- **nominal_efficiency** [_float_, unit = "frac", default = 0.9, min = 0.01]: Efficiency (heat given / fuel power, on the LHV) at nominal conditions.
- **nominal_water_flow** [_float_, unit = "dm³/s", default = 1, min = 0]: Nominal water flow, to calculate _F_water_.
- **max_supply_temperature** [_float_, unit = "°C", default = 80]: Maximum supply water temperature: above it the boiler gives no heat.
- **efficiency_expression** [_math_exp_, unit = "frac", default = "1"]: Mathematical expression to correct the efficiency in conditions different from the nominal ones; the efficiency is `nominal_efficiency` multiplied by it.
- **auxiliary_power** [_float_, unit = "W", default = 0, min = 0]: Electric power of the burner fan, pumps inside the boiler and controls, while the boiler gives heat.
- **expression_max_values** [_float-list_, unit = "-", default = [100, 100, 1.5, 1]]: Maximum values allowed in the mathematical expression. The order is [ _T_wi_ [ºC], _T_wo_ [ºC], _F_water_ [frac], _F_load_ [frac] ]. If any variable exceeds these values, the maximum value is taken.
- **expression_min_values** [_float-list_, unit = "-", default = [0, 0, 0, 0]]: Minimum values allowed in the mathematical expression, in the same order. If any variable is lower than these values, the minimum value is taken.

The efficiency expression can include the following independent variables.

- _T_wi_ [ºC]: Water inlet (return) temperature.
- _T_wo_ [ºC]: Water outlet (supply) temperature.
- _F_water_ [frac]: Actual water flow divided by nominal water flow.
- _F_load_ [frac]: Part load: heat given divided by the nominal heating capacity.

**Example:** a condensing boiler, 88 % efficient with a return at 55 °C or more, up to 96 % with a return at 30 °C.
<pre><code class="python">
...

boiler = osm.components.Boiler("boiler", project)
param = {
        "fuel": "NATURAL_GAS",
        "nominal_heating_capacity": 24000,
        "nominal_efficiency": 0.88,
        "nominal_water_flow": 0.3,
        "efficiency_expression": "1 + 0.0035 * max(55 - T_wi, 0)",
        "auxiliary_power": 50
}
boiler.set_parameters(param)
</code></pre>

### HVAC_water_generator

A generator of hot or chilled water of an HVAC_water_system: an equipment component, a "Chiller_heat_pump" (heating and/or cooling, electric) or a "Boiler" (heating, fuel), with its own primary pump. The water system decides the load it gives in each time step; the generator turns it into the load, part load, power and efficiency of its equipment, and stores them. The water flow through it is the nominal water flow of its equipment.

A Boiler only heats; a Chiller_heat_pump heats, cools or both according to its `chiller_type`.

A generator may have several identical units of its equipment in parallel (`number_of_units`): its capacity and water flow are those of one unit times the number of units, and the units share the load with the `sequencing` of the water system: with "PRIORITY" one after the other (the next one starts when the previous is at full load), with "EQUAL_LOAD" all at the same part load. The power of each unit is calculated with its own part load.

#### Parameters
- **equipment** [_component_, default = "not_defined", component type = Chiller_heat_pump or Boiler]: Equipment that heats and/or cools the water.
- **number_of_units** [_int_, default = 1, min = 1]: Number of identical units of the equipment.
- **pump** [_component_, default = "not_defined", component type = Pump]: Primary pump of the generator, sized for its water flow (all its units). It moves the water through the generator while the generator is available. If not defined, its heat to the water and its power are considered zero.
- **input_variables** [_variable_list_, default = []]: List of variables from other components used in this component. They may be used in parameters of the type math_exp.
- **system_on_off** [_math_exp_, unit = "on/off", default = "1"]: Availability of the generator: if 0 it gives no heat or cold. The mathematical expression may contain any of the variables declared in the "input_variables" parameter.

**Example:**
<pre><code class="python">
...

generator = osm.components.HVAC_water_generator("generator", project)
param = {
        "equipment": "heat_pump",
        "pump": "pump"
}
generator.set_parameters(param)
</code></pre>

#### Variables

After the simulation we will have the following variables of this component:

- __on_off__ [flag]: Availability of the generator (system_on_off).
- __state__ [flag]: Operation: off (0), heating (1), cooling (-1).
- __Q__ [W]: Heat given to the water, positive heating, negative cooling.
- __F_load__ [frac]: Part load of the generator: load given divided by the capacity of all its units.
- __units_on__ [-]: Number of units giving heat or cold.
- __power__ [W]: Electric power of the equipment (for a Boiler, its auxiliary power).
- __fuel_power__ [W]: Fuel power on the lower heating value (Boiler; 0 for a Chiller_heat_pump).
- __efficiency__ [frac]: EER (cooling) or COP (heating) of a Chiller_heat_pump, efficiency on the LHV of a Boiler; with several units, heat given divided by the power (fuel power for a boiler) of all of them.
- __water_flow__ [dm³/s]: Water flow through the generator.
- __T_wi__ [°C]: Inlet (return) water temperature.
- __T_wo__ [°C]: Outlet (supply) water temperature.
- __pump_power__ [W]: Electric power of its pump.

### HVAC_water_system

Component for the simulation of a hydronic water loop that supplies chilled and/or hot water to one or more coils (used by the air side HVAC systems, `HVAC_SZW_system` and `HVAC_MZW_system`) from its generators ("HVAC_water_generator").

The generators are in parallel in the loop: the water flow is the sum of the water flows of the generators available (their `system_on_off`), each one moved by its own pump; a generator that is not available lets no water through. In heating only the generators able to heat run (boilers and heat pumps), in cooling only those able to cool, and they share the load with the `sequencing`: "PRIORITY" in the order of the `generators` list, the next one when the previous is at full load (e.g. a heat pump first and a boiler as backup), or "EQUAL_LOAD", all of them at the same part load.

The coils of the air systems connected to it (parameters `water_source`, `cooling_water_system`, `heating_water_system` and, for the reheat coils of `HVAC_MZW_system`, `reheat_water_source` and `reheat_water_system`) take from it their inlet water temperature and add their load and water flow to it in each iteration.

Changed in version 0.10: `generators` replaces `water_thermal_generator`; the pump is now the one of the generator (`pump` of HVAC_water_generator) and the water flow the nominal one of its equipment (`design_water_flow` is gone).

#### Parameters
- **generators** [_component_list_, default = ["not_defined"], component type = HVAC_water_generator]: Generators of the loop, in order of priority.
- **sequencing** [_option_, default = "PRIORITY", options = ["PRIORITY", "EQUAL_LOAD"]]: How the generators, and the units of each generator, share the load.
- **initial_water_temp** [_float_, unit = "°C", default = 20]: Water temperature used to initialize the loop at the first time step.
- **total_water_volume** [_float_, unit = "dm³", default = 1000, min = 0]: Total water volume of the loop, used to calculate its thermal inertia.
- **input_variables** [_variable_list_, default = []]: List of variables from other components used in this component. They may be used in parameters of the type math_exp.
- **heating_water_setpoint** [_math_exp_, unit = "°C", default = "45"]: Hot water outlet setpoint temperature at the generator when the system is heating. The mathematical expression may contain any of the variables declared in the "input_variables" parameter.
- **cooling_water_setpoint** [_math_exp_, unit = "°C", default = "7"]: Chilled water outlet setpoint temperature at the generator when the system is cooling. The mathematical expression may contain any of the variables declared in the "input_variables" parameter.
- **system_on_off** [_math_exp_, unit = "on/off", default = "1"]: If this value is 0, the system will be off, otherwise it will be on. The mathematical expression may contain any of the variables declared in the "input_variables" parameter.
- **pump_operation** [_option_, default = "ALLWAYS_ON", options = ["ALLWAYS_ON", "ON_LOAD"]]: If "ALLWAYS_ON" the pump runs at design flow whenever the system is on. If "ON_LOAD" the pump (and water flow) only runs when there is a heating or cooling load from the coils or the process load.
- **system_control** [_option_, default = "LOAD_CONTROL", options = ["LOAD_CONTROL", "SCHEDULE_CONTROL"]]: If "LOAD_CONTROL" the system switches automatically between heating and cooling depending on the sign of the load requested by the coils and the process load. If "SCHEDULE_CONTROL" the operating mode is set with the "system_mode" parameter, and any load of the opposite sign is not satisfied.
- **system_mode** [_math_exp_, unit = "-1/0/1", default = "1"]: Operating mode used only when "system_control" is "SCHEDULE_CONTROL": -1 for cooling, 0 for standby, 1 for heating. The mathematical expression may contain any of the variables declared in the "input_variables" parameter.
- **Q_loss** [_math_exp_, unit = "W", default = "0"]: Thermal losses (or gains, if negative) of the water loop to the environment.
- **convergence_DT** [_float_, unit = "°C", default = 0.01, min = 0.0]: Convergence tolerance for the water loop outlet temperature at the generator, used by the iterative solution process.
- **water_limits** [_float_list_, unit = "°C", default = [1, 99], min = 0, max = 100]: Minimum and maximum water temperatures allowed in the loop, used to limit the values of the reported temperature variables.
- **Q_process** [_math_exp_, unit = "W", default = "0"]: Additional heat load applied directly to the water loop (positive heats the water, negative cools it), independent of the coils connected to the system.

**Example:**
<pre><code class="python">
...

water_system = osm.components.HVAC_water_system("water_system", project)
param = {
        "generators": ["generator"],
        "heating_water_setpoint": "50",
        "cooling_water_setpoint": "7",
        "total_water_volume": 100,
        "pump_operation": "ON_LOAD",
        "system_control": "SCHEDULE_CONTROL",
        "input_variables": ["f = mode_schedule.values", "g = on_schedule.values"],
        "system_mode": "f",
        "system_on_off": "g"
}
water_system.set_parameters(param)
</code></pre>

#### Variables

After the simulation we will have the following variables of this component:

- __on_off__ [flag]: Operation of the system: off (0), on (1).
- __mode__ [flag]: Operating mode of the system: cooling (-1), standby (0), heating (1).
- __T_WGO__ [°C]: Generator outlet water temperature.
- __T_WGI__ [°C]: Generator inlet water temperature.
- __T_WCI__ [°C]: Coils inlet water temperature.
- __T_WCO__ [°C]: Coils outlet water temperature.
- __T_WAVG__ [°C]: Average water loop temperature.
- __water_flow__ [dm³/s]: Loop water flow.
- __coils_water_flow__ [dm³/s]: Sum of the water flows the coils report (design flow times their part load).
- __Q_gen__ [W]: Heat supplied (positive) or removed (negative) by the generator.
- __Q_coils__ [W]: Heat exchanged with the coils connected to the system, positive when heating the water, negative when cooling it.
- __Q_process__ [W]: Additional process heat load applied to the water loop.
- __Q_loss__ [W]: Thermal losses of the water loop to the environment.
- __Q_pump__ [W]: Heat gain to the water from the pump.
- __delta_U__ [W]: Rate of change of the internal energy stored in the water loop.
- __pump_power__ [W]: Electrical power consumed by the pumps of the generators.
- __generator_power__ [W]: Electrical power consumed by the generators.
- __generator_fuel_power__ [W]: Fuel power of the generators (boilers), on the lower heating value.
- __generator_efficiency__ [-]: Efficiency of the generators: with one generator, its EER (cooling), COP (heating) or efficiency on the LHV (boiler); with several, the heat given divided by their electric plus fuel power.
- __generator_part_load__ [frac]: Part load of the generators (load given divided by the capacity of those able to run), 0 while they give no heat or cold.
- __heating_water_setpoint__ [°C]: Heating water setpoint temperature.
- __cooling_water_setpoint__ [°C]: Cooling water setpoint temperature.
