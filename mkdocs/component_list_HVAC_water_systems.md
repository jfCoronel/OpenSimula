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

A generator of hot or chilled water of an HVAC_water_system: an equipment component, a "Chiller_heat_pump" (heating and/or cooling, electric), a "Boiler" (heating, fuel) or a "Solar_collector" (heating, solar thermal energy), with its own primary pump. A solar collector generator cannot be controlled: the plant (which must have a tank) always takes the heat the sun gives, up to the `max_temperature` of the collector, and its other generators give only what is missing up to the setpoint; its pump (the pump of the solar loop) runs while the collector gives heat. The water system decides the load it gives in each time step; the generator turns it into the load, part load, power and efficiency of its equipment, and stores them. The water flow through it is the nominal water flow of its equipment.

A Boiler only heats; a Chiller_heat_pump heats, cools or both according to its `chiller_type`.

A generator may have several identical units of its equipment in parallel (`number_of_units`): its capacity and water flow are those of one unit times the number of units, and the units share the load with the `sequencing` of the water system: with "PRIORITY" one after the other (the next one starts when the previous is at full load), with "EQUAL_LOAD" all at the same part load. The power of each unit is calculated with its own part load.

#### Parameters
- **equipment** [_component_, default = "not_defined", component type = Chiller_heat_pump, Boiler or Solar_collector]: Equipment that heats and/or cools the water.
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

Component for the simulation of a water plant that supplies chilled and/or hot water to one or more coils (used by the air side HVAC systems, `HVAC_SZW_system` and `HVAC_MZW_system`) from its generators ("HVAC_water_generator").

The coils of the air systems connected to it (parameters `water_source`, `cooling_water_system`, `heating_water_system` and, for the reheat coils of `HVAC_MZW_system`, `reheat_water_source` and `reheat_water_system`) take from it their inlet water temperature and add their load and water flow to it in each iteration. They can also hang from an `HVAC_water_circuit` fed by the plant, which for the plant is one more coil.

The water of the plant (`total_water_volume`) is considered as one volume at one temperature: the heat of the generators, the coils, the process load, the losses and the pumps changes it. In heating only the generators able to heat run (boilers and heat pumps), in cooling only those able to cool, and they share the load with the `sequencing`: "PRIORITY" in the order of the `generators` list, the next one when the previous is at full load (e.g. a heat pump first and a boiler as backup), or "EQUAL_LOAD", all of them at the same part load.

**Without secondary pumps** (`pumps` empty, the default) the generators are in series with the coils, in parallel among them: the water flow is the sum of the water flows of the generators available (their `system_on_off`), each one moved by its own pump; a generator that is not available lets no water through.

**With secondary pumps** the plant has a header (a hydraulic decoupler, or a buffer tank) between the primary circuit of the generators and the secondary one of the coils:

- The secondary pumps move their nominal water flow to the coils (`secondary_flow`), and the pump of each generator its nominal water flow only while it runs (`primary_flow`): a backup boiler moves no water while it is not needed.
- Each generator tries to give the setpoint at its outlet.
- If the primary flow is larger than the secondary one, the rest goes back to the generators through the bypass (`bypass_flow` positive) and mixes with the return: the generators get warmer water in heating (colder in cooling), which lowers the efficiency of a condensing boiler.
- If it is smaller, part of the return goes to the supply (`bypass_flow` negative): the water to the coils is below the setpoint in heating (above it in cooling).

Changed in version 0.10: `generators` replaces `water_thermal_generator`; the pumps are those of the generators (`pump` of HVAC_water_generator) and, with a header, the secondary `pumps`; the water flow is the nominal one of the equipment (`design_water_flow` is gone). The variables have new names (`T_supply`, `T_return`, `T_generators_out`, `T_generators_in`, `Q_generators`...); the efficiency and part load of each generator are in its own variables.

#### Parameters
- **generators** [_component_list_, default = ["not_defined"], component type = HVAC_water_generator]: Generators of the loop, in order of priority.
- **sequencing** [_option_, default = "PRIORITY", options = ["PRIORITY", "EQUAL_LOAD"]]: How the generators, and the units of each generator, share the load.
- **pumps** [_component_list_, default = [], component type = Pump]: Secondary pumps, in parallel. With them the plant has a header (primary / secondary); without them (the default) the loop is moved by the pumps of the generators.
- **initial_water_temp** [_float_, unit = "°C", default = 20]: Water temperature used to initialize the loop at the first time step.
- **total_water_volume** [_float_, unit = "dm³", default = 1000, min = 0]: Total water volume of the loop, used to calculate its thermal inertia.
- **tank** [_component_, default = "not_defined", component type = Water_tank]: Storage tank (DHW tank, electric water heater, buffer tank). Its water is the water of the plant (its volume replaces `total_water_volume`, its losses are added to `Q_loss`) and the plant works as with a header: the generators heat the tank up to the heating setpoint, moving water only while they run, and the loads take the water of the tank (without secondary pumps, the flow they ask for: e.g. the mains pressure of a DHW demand). The thermostat starts the generators when the tank, without them, would be `dead_band` below the setpoint and keeps them on up to it.
- **input_variables** [_variable_list_, default = []]: List of variables from other components used in this component. They may be used in parameters of the type math_exp.
- **heating_water_setpoint** [_math_exp_, unit = "°C", default = "45"]: Hot water outlet setpoint temperature at the generator when the system is heating. The mathematical expression may contain any of the variables declared in the "input_variables" parameter.
- **cooling_water_setpoint** [_math_exp_, unit = "°C", default = "7"]: Chilled water outlet setpoint temperature at the generator when the system is cooling. The mathematical expression may contain any of the variables declared in the "input_variables" parameter.
- **system_on_off** [_math_exp_, unit = "on/off", default = "1"]: If this value is 0, the system will be off, otherwise it will be on. The mathematical expression may contain any of the variables declared in the "input_variables" parameter.
- **pump_operation** [_option_, default = "ALLWAYS_ON", options = ["ALLWAYS_ON", "ON_LOAD"]]: If "ALLWAYS_ON" the pumps that move the water to the coils (those of the generators, or the secondary pumps with a header) run whenever the system is on. If "ON_LOAD" they only run when there is a heating or cooling load from the coils or the process load. Only with `flow_control` "CONSTANT".
- **flow_control** [_option_, default = "CONSTANT", options = ["CONSTANT", "VARIABLE"]]: "CONSTANT": the water moves at the design flow while the pumps run (three-way valves). "VARIABLE" (two-way valves): the flow is the one the coils, circuits and DHW demands ask for, between `minimum_flow` and the design flow; with no demand the water stands. Without a header the generators share that flow in proportion to their nominal flows and their pumps work at it (the `F_water` of their `power_expression`); with a header it is the secondary flow, the secondary pumps are staged (in the order of the list, as many as needed, sharing the flow in proportion to their nominal flows) and the primary is unchanged. An instantaneous boiler for DHW then sees only the water drawn, at the mains temperature.
- **minimum_flow** [_float_, unit = "frac", default = 0, min = 0, max = 1]: With `flow_control` "VARIABLE", lowest flow as a fraction of the design flow (of the generators, or of the secondary pumps with a header) while the system is on. A `Q_process` has no flow of its own: it needs a minimum flow above 0.
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
- __T_supply__ [°C]: Water temperature to the coils (secondary supply).
- __T_return__ [°C]: Water temperature from the coils (secondary return).
- __T_generators_out__ [°C]: Water temperature at the outlet of the generators (mixed).
- __T_generators_in__ [°C]: Water temperature at the inlet of the generators.
- __T_mean__ [°C]: Mean water temperature of the plant (the variable `T_w` of the expression `Q_loss`).
- __primary_flow__ [dm³/s]: Water flow through the generators.
- __secondary_flow__ [dm³/s]: Water flow to the coils (the same as the primary one without a header).
- __bypass_flow__ [dm³/s]: Water flow through the header from the supply to the return (positive) or from the return to the supply (negative); 0 without a header.
- __coils_flow__ [dm³/s]: Sum of the water flows the coils report (design flow times their part load).
- __Q_generators__ [W]: Heat given to the water by the generators: positive heating, negative cooling.
- __Q_loads__ [W]: Load of everything connected to the system: coils of air systems, circuits and DHW demands; positive when they heat the water, negative when they cool it. Q_loads = Q_heating_coils + Q_cooling_coils + Q_dhw (except with SCHEDULE_CONTROL, which discards the loads of the other mode).
- __Q_heating_coils__ [W]: Load of the heating coils, of air systems directly or through circuits (negative).
- __Q_cooling_coils__ [W]: Load of the cooling coils (positive).
- __Q_dhw__ [W]: Load of the DHW demands (negative).
- __Q_process__ [W]: Additional process heat load applied to the water.
- __Q_loss__ [W]: Thermal losses of the water to the environment.
- __Q_pump__ [W]: Heat given to the water by all the pumps.
- __delta_U__ [W]: Rate of change of the internal energy of the water.
- __generators_power__ [W]: Electric power of the generators (heat pumps and chillers, auxiliary power of boilers).
- __generators_fuel_power__ [W]: Fuel power of the generators (boilers), on the lower heating value.
- __pumps_power__ [W]: Electric power of all the pumps (generators and secondary).
- __secondary_pumps_power__ [W]: Electric power of the secondary pumps.
- __electric_power__ [W]: Electric power of the plant: generators and pumps.
- __heating_water_setpoint__ [°C]: Heating water setpoint temperature.
- __cooling_water_setpoint__ [°C]: Cooling water setpoint temperature.

### HVAC_water_circuit

A secondary water circuit fed by an HVAC_water_system (the plant). The coils of the air systems (`HVAC_SZW_system`, `HVAC_MZW_system`) can hang from a circuit instead of from the plant: in their parameters `heating_water_system`, `cooling_water_system` and `reheat_water_system` they refer to the circuit. A plant can feed several circuits, each with its own pumps, its own availability and, with a mixing valve, its own supply temperature: e.g. the fan coils at 40 °C and the coils of an air handling unit at 60 °C from the same boiler.

Towards the coils the circuit offers what a plant offers: the inlet water temperature and the place to add their load. Towards the plant it is one more coil: it takes water from it and gives it back its load, that of its coils plus its losses, the heat of its pumps and, with a water volume, the change of the energy stored in its water. The mode, heating or cooling, is that of the plant.

The pumps of the circuit move their nominal water flow while it is on. The mixing valve mixes the water of the plant with the return of the circuit, so that the supply is never above `heating_supply_setpoint` nor below `cooling_supply_setpoint`; without them (the default, empty) the supply is the water of the plant. The water taken from the plant (`plant_flow`) is then the part of the flow of the circuit that the mixing needs.

#### Parameters
- **water_system** [_component_, default = "not_defined", component type = HVAC_water_system]: The plant that feeds the circuit.
- **pumps** [_component_list_, default = [], component type = Pump]: Pumps of the circuit, in parallel, at their nominal water flow.
- **input_variables** [_variable_list_, default = []]: List of variables from other components used in this component. They may be used in parameters of the type math_exp.
- **system_on_off** [_math_exp_, unit = "on/off", default = "1"]: If 0 the circuit is off: its pumps stop and its coils get no heat or cold. It is also off while its plant is off.
- **pump_operation** [_option_, default = "ALLWAYS_ON", options = ["ALLWAYS_ON", "ON_LOAD"]]: If "ALLWAYS_ON" the pumps run whenever the circuit is on; if "ON_LOAD" only when its coils have a load. Only with `flow_control` "CONSTANT".
- **flow_control** [_option_, default = "CONSTANT", options = ["CONSTANT", "VARIABLE"]]: "CONSTANT": the design flow of its pumps while they run. "VARIABLE": the flow its coils ask for, between `minimum_flow` and the design flow, its pumps staged as the secondary pumps of a plant.
- **minimum_flow** [_float_, unit = "frac", default = 0, min = 0, max = 1]: With `flow_control` "VARIABLE", lowest flow as a fraction of the design flow while the circuit is on.
- **heating_supply_setpoint** [_math_exp_, unit = "°C", default = ""]: Maximum supply temperature (mixing valve). Empty: no limit.
- **cooling_supply_setpoint** [_math_exp_, unit = "°C", default = ""]: Minimum supply temperature (mixing valve). Empty: no limit.
- **Q_loss** [_math_exp_, unit = "W", default = "0"]: Heat losses (negative) or gains (positive) of the water of the circuit; may use `T_w`, its supply temperature, and `m_w`, its water flow.
- **water_volume** [_float_, unit = "dm³", default = 0, min = 0]: Water volume of the circuit: the plant also gives the heat to warm it up or cool it down.
- **tank** [_component_, default = "not_defined", component type = Water_tank]: With a tank the circuit is a charging circuit (e.g. the DHW tank of a boiler that also heats): its coils (DHW demands) take the water of the tank, at its temperature, even while the plant is off; its pumps charge the tank with water of the plant while the tank is below `tank_setpoint`, the plant can heat and its water is hotter, running the fraction of the time step the charge needs (the water goes back to the plant at the temperature of the tank). The mixing valve and `water_volume` do not apply. The thermostat starts the charge `dead_band` below the setpoint (see Water_tank). If only DHW demands hang from the circuit, all its load to the plant (losses of the tank included) and its pumps count as DHW.
- **tank_setpoint** [_math_exp_, unit = "°C", default = "60"]: Charging setpoint of the tank.

**Example:**
<pre><code class="python">
...

floor_circuit = osm.components.HVAC_water_circuit("floor_circuit", project)
param = {
        "water_system": "hot_water",
        "pumps": ["floor_pump"],
        "heating_supply_setpoint": "35",
        "water_volume": 300
}
floor_circuit.set_parameters(param)
</code></pre>

#### Variables

After the simulation we will have the following variables of this component:

- __on_off__ [flag]: Availability of the circuit (system_on_off).
- __T_plant__ [°C]: Temperature of the water from the plant.
- __T_supply__ [°C]: Supply water temperature of the circuit, to its coils.
- __T_return__ [°C]: Return water temperature of the circuit.
- __water_flow__ [dm³/s]: Water flow moved by its pumps.
- __plant_flow__ [dm³/s]: Water flow taken from the plant.
- __mixing_flow__ [dm³/s]: Water flow of the return mixed into the supply by the mixing valve.
- __coils_flow__ [dm³/s]: Sum of the water flows the coils report.
- __Q_loads__ [W]: Load of its coils and DHW demands, positive when they heat the water, negative when they cool it: Q_loads = Q_heating_coils + Q_cooling_coils + Q_dhw.
- __Q_heating_coils__, __Q_cooling_coils__ [W]: Load of its heating coils (negative) and of its cooling coils (positive).
- __Q_dhw__ [W]: Load of its DHW demands (negative).
- __Q_loss__ [W]: Heat losses (negative) or gains of the circuit.
- __Q_pump__ [W]: Heat given to the water by its pumps.
- __delta_U__ [W]: Rate of change of the energy stored in its water.
- __Q_plant__ [W]: Load given to the plant: Q_loads + Q_loss + Q_pump - delta_U.
- __pumps_power__ [W]: Electric power of its pumps.

### Solar_collector

Field of solar thermal collectors, with the data of its EN ISO 9806 test (on the aperture area). Equipment data, like a Boiler: an `HVAC_water_generator` uses it, in a plant with a tank (`Water_tank`). The useful heat follows the quasi-steady model of EN ISO 9806:

Q = A · [η0 · (K_b · G_b + K_d · G_d) − a1 · (T_m − T_a) − a2 · (T_m − T_a)²]

G_b and G_d are the beam and diffuse irradiance on the collector plane, from the weather file (the diffuse with the `tilted_diffuse_model` of the File_met, plus the radiation reflected by the ground with the `albedo` of the project); K_b = 1 − b0 · (1/cos θ − 1) is the incidence angle modifier of the beam (θ, angle of incidence) and K_d that of the diffuse; T_a is the outdoor air temperature and T_m the mean temperature of the fluid in the collector: with the water of the tank entering at T_in, the flow m of the loop and a heat exchanger of effectiveness ε between the loop and the tank, T_m = T_in + Q / (m·c) · (1/ε − 1/2). The collector gives heat (its pump runs) while Q > 0 and the tank is below `max_temperature`. Shadows on the collectors are not considered yet.

#### Parameters

- **area** [_float_, unit = "m²", default = 2]: Aperture area of the field.
- **eta_0** [_float_, unit = "frac", default = 0.75]: Peak efficiency η0 (zero loss efficiency).
- **a1** [_float_, unit = "W/(m²·K)", default = 3.5]: Heat loss coefficient.
- **a2** [_float_, unit = "W/(m²·K²)", default = 0.015]: Temperature dependence of the heat loss coefficient.
- **b0** [_float_, default = 0.15]: Incidence angle modifier constant of the beam irradiance.
- **K_diffuse** [_float_, unit = "frac", default = 0.9]: Incidence angle modifier of the diffuse irradiance.
- **tilt** [_float_, unit = "°", default = 45, min = 0, max = 90]: Tilt of the collectors from the horizontal.
- **azimuth** [_float_, unit = "°", default = 0, min = -180, max = 180]: Orientation of the collectors: 0 south, negative to the east, positive to the west (as the solar azimuth of the File_met).
- **nominal_water_flow** [_float_, unit = "dm³/s", default = 0.04]: Flow of the solar loop (typically 0.02 dm³/s per m², "low flow" installations about half).
- **exchanger_effectiveness** [_float_, unit = "frac", default = 1, min = 0.01, max = 1]: Effectiveness of the heat exchanger between the collector loop and the tank (1: no exchanger).
- **max_temperature** [_float_, unit = "°C", default = 90]: Maximum temperature of the tank: the collectors do not heat it above it.

#### Variables

- **irradiance** (W/m²): Total irradiance on the collector plane.
- **effective_irradiance** (W/m²): With the incidence angle modifiers, K_b · G_b + K_d · G_d.

The heat given, its efficiency (Q / (A · G)) and the power of the pump are variables of the generator (`Q`, `efficiency`, `pump_power`).

The heat of the collectors is final energy of the carrier **SOLAR_THERMAL** (service DHW or HEATING, as the rest of the heat of the plant). It is renewable energy produced on site, with the factors of the energy taken by heat pumps from the environment (1 / 0 / 0), and not counted in the totals of final energy.

**Example** (2 m² of collectors and a 150 l solar tank that preheats the DHW; the backup, in series, is the `water_system` of the DHW demand):
<pre><code class="python">
...

pro.new_component("Solar_collector", "collector").set_parameters({
    "area": 2, "eta_0": 0.75, "a1": 3.5, "a2": 0.015, "tilt": 45, "azimuth": 0,
    "nominal_water_flow": 0.04})
pro.new_component("Pump", "solar_pump").set_parameters({"nominal_water_flow": 0.04, "nominal_power": 30})
pro.new_component("HVAC_water_generator", "solar_gen").set_parameters({
    "equipment": "collector", "pump": "solar_pump"})
pro.new_component("Water_tank", "solar_tank").set_parameters({"volume": 150, "UA": 1.2})
pro.new_component("HVAC_water_system", "solar_plant").set_parameters({
    "generators": ["solar_gen"], "tank": "solar_tank"})
pro.new_component("DHW_demand", "dhw").set_parameters({
    "water_system": "boiler_plant", "preheat_system": "solar_plant",
    "input_variables": ["f = profile.values"], "volume_flow": "120 * f"})
</code></pre>

### Water_tank

Water storage tank: a DHW tank, an electric water heater or a buffer tank. Equipment data, like a Boiler: it is used by the `HVAC_water_system` or the `HVAC_water_circuit` that refers to it in its `tank` parameter, whose water is then the water of the tank. Its heat losses are UA·(T − T_ambient).

By default the tank is fully mixed (one temperature). With `number_of_nodes` > 1 (only in a plant) it is **stratified**: N layers of the same volume, node 1 at the top and node N at the bottom. Each time step:

1. the water drawn by the loads leaves at the top and the same flow comes back at the bottom (mains water for a DHW demand), pushing the layers up;
2. each node loses UA/N·(T_node − T_ambient);
3. the solar collectors heat the bottom node, taking its water (the coldest: they work better);
4. the other generators heat the node of the backup heater (`backup_position`), where its thermostat is, up to the setpoint of the plant (with the `dead_band`), as much as their capacity gives;
5. heated water rises: a layer warmer than the one above mixes with it.

The water to the loads is the mean temperature of the water leaving the top in the time step. With the backup in the middle of the tank, the bottom stays cold for the collectors, which is why a single tank with solar and backup needs the stratification (with one node the backup keeps the whole tank hot and the solar fraction falls: 0.56 instead of 0.75 in the example below).

#### Parameters

- **volume** [_float_, unit = "dm³", default = 150]: Water volume.
- **UA** [_float_, unit = "W/K", default = 1.5, min = 0]: Heat loss coefficient. From the standing loss of the ErP label, S in W (measured with 45 K between the water and the room): UA = S / 45; from a standing loss Q in kWh/24h at 45 K (EN 12897): UA = Q · 1000 / (24 · 45). E.g. S = 60 W → UA = 1.33 W/K; Q = 1.5 kWh/24h → UA = 1.39 W/K.
- **dead_band** [_float_, unit = "K", default = 0, min = 0]: Dead band of the thermostat: the heating starts when the water, without it, would be this much below the setpoint, and goes on up to the setpoint. With 0 the tank is held at the setpoint.
- **input_variables** [_variable_list_, default = []]: Variables of other components used in the expression.
- **ambient_temperature** [_math_exp_, unit = "°C", default = "20"]: Temperature of the room the tank is in, e.g. that of a space (`T = space.temperature`) or the outdoor air.
- **number_of_nodes** [_int_, default = 1, min = 1, max = 50]: Number of layers of a stratified tank (1: fully mixed). Only in a plant. 4 to 10 nodes are usual; the results change little above 6.
- **backup_position** [_float_, unit = "frac", default = 0.5]: Height of the backup heater and its thermostat in a stratified tank, as a fraction of the height from the bottom (0.5: in the middle): only the water above it is kept at the setpoint.

#### Variables

- **temperature** (°C): Temperature of the water (the mean one in a stratified tank).
- **T_node_1** ... **T_node_N** (°C): Temperature of each node of a stratified tank, from the top.
- **T_ambient** (°C): Temperature of the room.
- **Q_loss** (W): Heat lost by the tank (positive).

**Example** (electric water heater of 100 l):
<pre><code class="python">
...

pro.new_component("Boiler", "resistance").set_parameters({
    "fuel": "ELECTRICITY", "nominal_heating_capacity": 1500,
    "nominal_efficiency": 1, "nominal_water_flow": 0.05})
pro.new_component("HVAC_water_generator", "heater_gen").set_parameters({"equipment": "resistance"})
pro.new_component("Water_tank", "tank").set_parameters({"volume": 100, "UA": 1.2, "dead_band": 5})
pro.new_component("HVAC_water_system", "heater").set_parameters({
    "generators": ["heater_gen"], "tank": "tank", "heating_water_setpoint": "60"})
# and a DHW_demand with "water_system": "heater"
</code></pre>

**Example** (one 200 l stratified tank with solar collectors and an electric heater in the middle):
<pre><code class="python">
pro.new_component("Water_tank", "tank").set_parameters({
    "volume": 200, "UA": 1.5, "number_of_nodes": 6, "backup_position": 0.5, "dead_band": 5})
pro.new_component("HVAC_water_system", "plant").set_parameters({
    "generators": ["solar_gen", "heater_gen"], "tank": "tank", "heating_water_setpoint": "60"})
# Sevilla, 2 m² of collectors, 120 l/day: solar fraction 0.75 (0.56 with one node)
</code></pre>

### DHW_demand

Demand of domestic hot water (DHW) served by a water plant or circuit. The demand is the instantaneous use of hot water (l/h) at a use temperature (60 °C by default, as the DB-HE gives the volumes), both expressions: the volume follows a schedule (for dwellings, the hourly profile of the DB-HE), a data file (`File_data`, e.g. measured uses) or anything else. Each time step it takes from its plant or circuit the heat to warm that water from the mains temperature, plus the distribution losses: the plant sees it as one more coil that takes water at the supply temperature and gives it back at the mains temperature (the water drawn is replaced by mains water). The load is DHW for the energy indicators: the plant splits the energy of its generators and pumps between HEATING and DHW by the heat delivered to each kind of load.

Water from the plant hotter than the use temperature is mixed by the user with mains water: the whole demand is met, with less water from the plant. Water colder than the use temperature is used as it comes: only the heat from the mains temperature to the supply temperature is met, the rest is unmet (`Q_unmet`) and the time step is flagged (`low_temperature`). A plant or circuit that is off or cannot heat (e.g. a two-pipe plant cooling) meets nothing.

#### Parameters

- **water_system** [_component_, default = "not_defined", component type = HVAC_water_system or HVAC_water_circuit]: Plant or circuit that gives the hot water.
- **preheat_system** [_component_, default = "not_defined", component type = HVAC_water_system or HVAC_water_circuit]: Preheating in series, e.g. a solar tank: the water drawn enters it (mains water replaces it) and leaves at its temperature; it gives the heat up to that temperature (all the demand, mixed with mains water, if hotter than the use temperature) and the `water_system` (the backup) heats the rest from there.
- **input_variables** [_variable_list_, default = []]: Variables of other components used in the expressions.
- **volume_flow** [_math_exp_, unit = "l/h", default = "0"]: Hot water used, at the use temperature (negative values count as 0). Usually a daily volume times a schedule, e.g. `"120 * f"` with `f` the hourly profile below.
- **use_temperature** [_math_exp_, unit = "°C", default = "60"]: Temperature of the water used. It can use `T_month` (as below) and the input variables.
- **mains_monthly_temperatures** [_float_list_, unit = "°C", default = Sevilla, DB-HE Anejo G]: Mains water temperature of each month: [11, 11, 13, 14, 16, 19, 21, 21, 20, 16, 13, 11].
- **mains_temperature** [_math_exp_, unit = "°C", default = "T_month"]: Mains water temperature; `T_month` is the value of the month from the previous parameter.
- **distribution_losses** [_float_, unit = "frac", default = 0]: Losses of the distribution network without recirculation, as a fraction of the demand.

#### Variables

- **volume_flow** (l/h), **T_use** (°C): Hot water used and its temperature.
- **T_mains** (°C), **T_supply** (°C): Mains water temperature and supply temperature of the plant or circuit.
- **T_preheat** (°C), **Q_preheat** (W): Temperature of the preheat system and heat it gives (mains temperature and 0 without one).
- **water_flow** (dm³/s): Water taken from the plant, at its supply temperature.
- **Q_demand** (W): Heat of the demand, with the distribution losses.
- **Q_supplied** (W), **Q_unmet** (W): Heat given by the plant and heat not met.
- **low_temperature** (flag): 1 when the plant heats but its water is colder than the use temperature (demand partly unmet).

The plants and circuits store the load of their DHW demands in the variable **Q_dhw** (W), part of their **Q_loads**.

**Example:**
<pre><code class="python">
...

from opensimula.cte import dhw_profile_schedules

# Day, week and year schedules with the hourly profile of dwellings (DB-HE Anejo D table c)
for c in dhw_profile_schedules("dhw_profile"):
    pro.new_component(c.pop("type"), c.pop("name")).set_parameters(c)
pro.new_component("DHW_demand", "dhw").set_parameters({
    "water_system": "boiler_plant",
    "input_variables": ["f = dhw_profile.values"],
    "volume_flow": "120 * f",  # 120 l/day at 60 °C
    "mains_monthly_temperatures": [8, 8, 10, 12, 14, 17, 20, 19, 17, 13, 10, 8],
})
</code></pre>

**Hourly profile of dwellings.** The DB-HE (Anejo D, table c) gives the share of the daily DHW demand used in each hour, the same every day:

| Hour | % | Hour | % | Hour | % | Hour | % |
|---|---|---|---|---|---|---|---|
| 0 | 1 | 6 | 3 | 12 | 5 | 18 | 5 |
| 1 | 0 | 7 | 10 | 13 | 5 | 19 | 7 |
| 2 | 0 | 8 | 7 | 14 | 4 | 20 | 6 |
| 3 | 0 | 9 | 7 | 15 | 3 | 21 | 6 |
| 4 | 0 | 10 | 6 | 16 | 4 | 22 | 5 |
| 5 | 1 | 11 | 6 | 17 | 4 | 23 | 5 |

`opensimula.cte.dhw_profile_schedules(name)` returns it as three components (a Day_schedule, a Week_schedule and the Year_schedule `name`, as dicts) whose variable `values` is the fraction of the daily volume of each hour. The DB-HE gives no profile for other uses: there the schedule is the user's.

