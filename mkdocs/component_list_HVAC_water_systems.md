## Component List for water side HVAC system definition
### Pump

Component to define pump equipment for water circuits.

This equipment can be used for one or more HVAC systems.

#### Parameters
- **nominal_water_flow** [_float_, unit = "m³/s", default = 1, min = 0]: Nominal inlet water flow.
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
- **nominal_water_flow** [_float_, unit = "m³/s", default = 1, min = 0]: Nominal chilled or hot water flow.
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
