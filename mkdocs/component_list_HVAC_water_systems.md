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

### HVAC_water_system

Component for the simulation of a hydronic water loop that supplies chilled and/or hot water to one or more coils (used by the air side HVAC systems, e.g. `HVAC_SZW_system` or `HVAC_MZW_system`) from a "Chiller_heat_pump" generator, optionally moved by a "Pump".

#### Parameters
- **water_thermal_generator** [_component_, default = "not_defined", component type = Chiller_heat_pump]: Reference to the "Chiller_heat_pump" component that heats and/or cools the loop water.
- **pump** [_component_, default = "not_defined", component type = Pump]: Reference to the "Pump" component that circulates the loop water. If not defined, the pump heat gain and power are considered zero.
- **design_water_flow** [_float_, unit = "dm³/s", default = 1, min = 0]: Loop water flow used while the system is on.
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
        "water_thermal_generator": "heat_pump",
        "pump": "pump",
        "design_water_flow": 0.4137,
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
- __Q_gen__ [W]: Heat supplied (positive) or removed (negative) by the generator.
- __Q_coils__ [W]: Heat exchanged with the coils connected to the system, positive when heating the water, negative when cooling it.
- __Q_process__ [W]: Additional process heat load applied to the water loop.
- __Q_loss__ [W]: Thermal losses of the water loop to the environment.
- __Q_pump__ [W]: Heat gain to the water from the pump.
- __delta_U__ [W]: Rate of change of the internal energy stored in the water loop.
- __pump_power__ [W]: Electrical power consumed by the pump.
- __generator_power__ [W]: Electrical power consumed by the generator.
- __generator_efficiency__ [-]: Generator efficiency (EER for cooling, COP for heating).
- __generator_part_load__ [frac]: Partial load state of the generator.
- __heating_water_setpoint__ [°C]: Heating water setpoint temperature.
- __cooling_water_setpoint__ [°C]: Cooling water setpoint temperature.
