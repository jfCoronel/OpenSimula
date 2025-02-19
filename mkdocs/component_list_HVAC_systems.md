## Component List for HVAC system definition
### HVAC_perfect_system

Component for the perfect conditioning of a space. With this component we can obtain the heating and cooling loads (sensible and latent).

#### Parameters
- **file_met** [_component_, default = "not_defined", component type = File_met]: Reference to the component where the weather file is defined.
- **space** [_component_, default = "not_defined", component type = Space]: Reference to the "Space" component to be controlled by this system.
- **input_variables** [_variable_list_, default = []]: List of variables from other components used in this component. They may be used in parameters of the type math_exp.
- **outdoor_air_flow** [_math_exp_, unit = "m³/s", default = "0"]: Outside air flow rate (ventilation) supplied to the space. This flow rate is only entered if the system is in operation. The mathematical expression may contain any of the variables declared in the "input_variables" parameter, to be able to reflect the time variation of this value.
- **heating_setpoint** [_math_exp_, unit = "°C", default = "20"]: Space heating setpoint temperature. The mathematical expression may contain any of the variables declared in the "input_variables" parameter, to be able to reflect the time variation of this value.
- **cooling_setpoint** [_math_exp_, unit = "°C", default = "25"]: Space Cooling setpoint temperature. The mathematical expression may contain any of the variables declared in the "input_variables" parameter, to be able to reflect the time variation of this value.
- **humidifying_setpoint** [_math_exp_, unit = "%", default = "0"]: Space relative humidity setpoint for humidification. If the relative humidity of the space is below this value, latent heat is added to maintain the relative humidity. The mathematical expression may contain any of the variables declared in the "input_variables" parameter, to be able to reflect the time variation of this value.
- **dehumidifying_setpoint** [_math_exp_, unit = "%", default = "100"]: Space relative humidity setpoint for dehumidification. If the relative humidity of the space is higher this value, latent heat is removed to maintain the relative humidity. The mathematical expression may contain any of the variables declared in the "input_variables" parameter, to be able to reflect the time variation of this value.
- **sytem_on_off** [_math_exp_, unit = "on/off", default = "1"]: If this value is 0, the system will be off, otherwise it will be on. The mathematical expression may contain any of the variables declared in the "input_variables" parameter, to be able to reflect the time variation of this value.

If outside air (ventilation) is present, it is introduced into the space as ‘uncontrolled system heat’, and the load values associated with the ventilation can be viewed in the space. The load supplied by the system is that required to maintain the space within the specified temperature and humidity set points, including ventilation if present.

**Example:**
<pre><code class="python">
...

system = osm.components.HVAC_perfect_system("system",project)
param = {
        "space": "space_1",
        "file_met": "Denver",
        "outdoor_air_flow": "0.1",
        "heating_setpoint": "20",
        "cooling_setpoint": "27",
        "humidifying_setpoint": "30",
        "dehumidifying_setpoint": "70",
        "input_variables":["f = HVAC_schedule.values"],
        "system_on_off": "f"
}
system.set_parameters(param)
</code></pre>

#### Variables

After the simulation we will have the following variables of this component:

- __Q_sensible__ [W]: Sensible heat supplied by the system, positive for heating and negative for cooling.
- __Q_latent__ [W]: Latent heat supplied by the system, positive for humidification, negative for dehumidification.
- __outdoor_air_flow__ [m³/s]: Outside air flow rate (ventilation) supplied to the space.
- __heating_setpoint__ [°C]: Heating setpoint temperature.
- __cooling_setpoint__ [°C]: Cooling setpoint temperature.
- __humififying_setpoint__ [%]: Low relative humidity setpoint.
- __dehumidifying_setpoint__ [%]: High relative humidity setpoint.
- __state__ [flag]: Operation of the system: off (0), heating (1), colling (-1), venting (3).

### HVAC_DX_equipment

Component to define a direct expansion air conditioning equipment. It can be used to define compact or split 1x1 units. 

This equipment can be used for one or more HVAC systems.

#### Parameters
- **nominal_air_flow** [_float_, unit = "m³/s", default = 1, min = 0]: Nominal supply air flow.
- **nominal_total_cooling_capacity** [_float_, unit = "W", default = 0, min = 0]: Total cooling capacity at nominal cooling conditions.
- **nominal_sensible_cooling_capacity** [_float_, unit = "W", default = 0, min = 0]: Sensible cooling capacity at nominal cooling conditions.
- **nominal_cooling_power** [_float_, unit = "W", default = 0, min = 0]: Electrical power consumed by the equipment at nominal cooling conditions. It must include all the consumptions: compressor, external fan, etc. except the power specified in “no_load_power”.
- **no_load_power** [_float_, unit = "W", default = 0, min = 0]: Electrical power consumed by the equipment at all times (even when the coil is not operating). This consumption is added to that obtained with the mathematical expressions when there is a load.
- **no_load_heat** [_float_, unit = "W", default = 0, min = 0]: Heat added to the air stream at all times (even when the coil is not operating), e.g., heat added by the supply fan.
- **nominal_cooling_conditions** [_float-list_, unit = "ºC", default = [27, 19, 35]]: Nominal cooling conditions, in order: indoor dry bulb temperature, indoor wet bulb temperature, outdoor dry bulb temperature.
- **total_cooling_capacity_expression** [_math_exp_, unit = "frac", default = "1"]: Mathematical expression to correct the total cooling capacity of the equipment in conditions different from the nominal ones. 
- **sensible_cooling_capacity_expression** [_math_exp_, unit = "frac", default = "1"]: Mathematical expression to correct the sensible cooling capacity of the equipment in conditions different from the nominal ones.
- **cooling_power_expression** [_math_exp_, unit = "frac", default = "1"]: Mathematical expression to correct the electric power consumption at cooling full load operation of the equipment in conditions different from the nominal ones.
- **EER_expression** [_math_exp_, unit = "frac", default = "1"]: Mathematical expression to correct the EER, defined as cooling total load supplied by de equipment divided by de electric power consumption, of the equipment in conditions different from the nominal ones. This expression should reflect the partial load behavior of the equipment.
- **nominal_heating_capacity** [_float_, unit = "W", default = 0, min = 0]: Heating capacity at nominal heating conditions.
- **nominal_heating_power** [_float_, unit = "W", default = 0, min = 0]: Electrical power consumed by the equipment at nominal heating conditions. It must include all the consumptions: compressor, external fan, etc, except the power specified in “no_load_power”.
- **nominal_heating_conditions** [_float-list_, unit = "ºC", default = [20, 7, 6]]: Nominal heating conditions, in order: indoor dry bulb temperature, outdoor dry bulb temperature, outdoor wet bulb temperature.
- **heating_capacity_expression** [_math_exp_, unit = "frac", default = "1"]: Mathematical expression to correct the heating capacity of the equipment in conditions different from the nominal ones. 
- **heating_power_expression** [_math_exp_, unit = "frac", default = "1"]: Mathematical expression to correct the electric power consumption at heating full load operation of the equipment in conditions different from the nominal ones.
- **COP_expression** [_math_exp_, unit = "frac", default = "1"]: Mathematical expression to correct the COP, defined as heating load supplied by de equipment divided by de electric power consumption, of the equipment in conditions different from the nominal ones. This expression should reflect the partial load behavior of the equipment.
- **dry_coil_model** [_option_, default = "SENSIBLE", options = ["SENSIBLE","TOTAL","INTERPOLATION"]]: When calculating the total and sensible capacity of the equipment under non-nominal conditions, it is possible that the total capacity is lower than the sensible capacity. In such a case it will be assumed that the coil does not dehumidify and that the total capacity is equal to the sensible capacity. We will use for both values the value of the sensible if the chosen option is “SENSIBLE” and the total if the chosen option is “TOTAL”.
- **power_dry_coil_correction** [_boolean_, default = True]: When the total and sensible power are equal, dry coil, the power expression may be incorrect. If this parameter is activated the simulation will look for the wet bulb temperature that makes the total and sensible capacities equal and use that temperature in the expression that corrects the cooling power.
- **expression_max_values** [_float-list_, unit = "-", default = [60,30,60,30,1.5,1]]: Maximum values allowed in the mathematical expressions. The order is [ _T_idb_ [ºC] , _T_iwb_ [ºC] ,_T_odb_ [ºC], _T_owb_ [ºC], _F_air_ [frac], _F_load_ [frac] ]. If any variable exceeds these values, the maximum value is taken.
- **expression_min_values** [_float-list_, unit = "-", default = [0,0,-30,-30,0,0]]: Minimum values allowed in the mathematical expressions. The order is [ _T_idb_ [ºC] , _T_iwb_ [ºC] ,_T_odb_ [ºC], _T_owb_ [ºC], _F_air_ [frac], _F_load_ [frac] ]. If any variable is lower than these values, the minimum value is taken.

All mathematical expressions can include the following independent variables.

- _T_idb_ [ºC]: Indoor dry bulb temperature, at the coil inlet of the indoor unit.
- _T_iwb_ [ºC]: Indoor wet bulb temperature, at the coil inlet of the indoor unit.
- _T_odb_ [ºC]: Outdoor dry bulb temperature.
- _T_owb_ [ºC]: Outdoor wet bulb temperature.
- _F_air_ [frac]: Actual supply air flow divided by nominal supply air flow.

"EER_expression" and "COP_expression" may also include the variable _F_load_, 
which represents the partial load state of the equipment, calculated as the thermal power 
supplied at a given instant divided by the cooling or heating capacity at the current operation conditions.


**Example:**
<pre><code class="python">
...

equipment = osm.components.HVAC_DX_equipment("equipment",project)
param = {
            "nominal_air_flow": 0.417,
            "nominal_total_cooling_capacity": 6000,
            "nominal_sensible_cooling_capacity": 4800,
            "nominal_cooling_power": 2400,
            "no_load_power": 240,
            "no_load_heat": 240,
            "total_cooling_capacity_expression": "0.88078 + 0.014248 * T_iwb + 0.00055436 * T_iwb**2 - 0.0075581 * T_odb + 3.2983E-05 * T_odb**2 - 0.00019171 * T_odb * T_iwb",
            "sensible_cooling_capacity_expression": "0.50060 - 0.046438 * T_iwb - 0.00032472 * T_iwb**2 - 0.013202 * T_odb + 7.9307E-05 * T_odb**2 + 0.069958 * T_idb - 3.4276E-05 * T_idb**2",
            "cooling_power_expression": "0.11178 + 0.028493 * T_iwb - 0.00041116 * T_iwb**2 + 0.021414 * T_odb + 0.00016113 * T_odb**2 - 0.00067910 * T_odb * T_iwb",
            "EER_expression": "0.20123 - 0.031218 * F_load + 1.9505 * F_load**2 - 1.1205 * F_load**3",
            "nominal_heating_capacity": 6500,
            "nominal_heating_power": 2825,
            "heating_capacity_expression": "0.81474	+ 0.030682602 * T_owb + 3.2303E-05 * T_owb**2",
            "heating_power_expression": "1.2012 - 0.040063 * T_owb + 0.0010877 * T_owb**2",
            "COP_expression": "0.085652 + 0.93881 * F_load - 0.18344 * F_load**2 + 0.15897 * F_load**3"
}
equipment.set_parameters(param)
</code></pre>

### HVAC_DX_system

Component for the simulation of an air-conditioning system for a space and using equipment in direct expansion "HVAC_DX_equipment".

#### Parameters
- **file_met** [_component_, default = "not_defined", component type = File_met]: Reference to the component where the weather file is defined.
- **space** [_component_, default = "not_defined", component type = Space]: Reference to the "Space" component to be air-conditioned by this system.
- **equipment** [_component_, default = "not_defined", component type = HVAC_DX_equipment]: Reference to the "HVAC_DX_equipment" component used by this system.
- **supply_air_flow** [_float_, unit = "m³/s", default = 1, min = 0]: Supply air flow used for all the simulation.
- **outdoor_air_flow** [_float_, unit = "m³/s", default = 0, min = 0]: Outdoor air flow used for all the simulation. The outside air is mixed with the return air from the room before it enters the indoor coil.
- **input_variables** [_variable_list_, default = []]: List of variables from other components used in this component. They may be used in parameters of the type math_exp.
- **heating_setpoint** [_math_exp_, unit = "°C", default = "20"]: Space heating setpoint temperature. The mathematical expression may contain any of the variables declared in the "input_variables" parameter, to be able to reflect the time variation of this value.
- **cooling_setpoint** [_math_exp_, unit = "°C", default = "25"]: Space Cooling setpoint temperature. The mathematical expression may contain any of the variables declared in the "input_variables" parameter, to be able to reflect the time variation of this value.
- **sytem_on_off** [_math_exp_, unit = "on/off", default = "1"]: If this value is 0, the system will be off, otherwise it will be on. The mathematical expression may contain any of the variables declared in the "input_variables" parameter, to be able to reflect the time variation of this value.
- **control_type** [_option_, default = "PERFECT", options = ["PERFECT","TEMPERATURE"]]: Type of control used, for the case ‘PERFECT’ the system will maintain exactly the desired temperature in the space, provided it has sufficient capacity. For the ‘TEMPERATURE’ case the power supplied by the system is calculated through a linear regulation law with the room temperature using the thermostat bandwidths, see figure below.
- **cooling_bandwidth** [_float_, unit = "ºC", default = 1, min = 0]: Bandwidth used in case _control_type_ is set to "TEMPERATURE" for the cooling setpoint.
- **heating_bandwidth** [_float_, unit = "ºC", default = 1, min = 0]: Bandwidth used in case _control_type_ is set to "TEMPERATURE" for the heating setpoint.
- **relaxing_coefficient** [_float_, unit = "frac", default = 1, min = 0, max =1]: Relaxation coefficient used for space temperature and humidity convergence. The equipment provides a sensible and latent power the average between the one obtained in the previous iteration and the one obtained in the current iteration. Thus for a relaxing coefficient of 1 the last calculated power will be used and for 0.5 an average between the previous iteration and the current one. The use of this coefficient smoothes the change in system operation between iteration and iteration. If it is detected that the instant does not converge, the system will progressively reduce the coefficient to help convergence.

If outside air (ventilation) is present, and the "no_load_heat" specified at the equipment, it is introduced into the space as ‘uncontrolled system heat’, so these loads can be viewed at the space.

The following figure shows the control equations used for the different ranges as a function of space temperature. This control is the one used if the parameter ‘control_type’ is set to ‘TEMPERATURE’.

![control_type_temperature](img/control_type_temperature.png)

**Example:**
<pre><code class="python">
...

system = osm.components.HVAC_DX_system("system",project)
param = {
        "space": "space_1",
        "file_met": "Denver",
        "equipment": "HVAC_equipment",
        "supply_air_flow": 0.417,
        "outdoor_air_flow": 0,
        "heating_setpoint": "20",
        "cooling_setpoint": "27",
        "system_on_off": "1",
        "control_type": "PERFECT"
}
system.set_parameters(param)
</code></pre>

#### Variables

After the simulation we will have the following variables of this component:

- __Q_sensible__ [W]: Sensible heat supplied by the system, positive for heating and negative for cooling.
- __Q_latent__ [W]: Latent heat supplied by the system, negative for dehumidification.
- __heating_setpoint__ [°C]: Heating setpoint temperature.
- __cooling_setpoint__ [°C]: Cooling setpoint temperature.
- __state__ [flag]: Operation of the system: off (0), heating (1), heating at maximum capacity (2), colling (-1), cooling at maximum capacity (-2), venting (3).
- __power__ [W]: Electrical power consumed by the system.
- __EER__ [frac]: System efficiency ratio for cooling, defined as the total thermal load supplied divided by the electrical power consumed.
- __COP__ [frac]: System efficiency ratio for heating, defined as the thermal load supplied divided by the electrical power consumed.
- __T_odb__ [ºC]: Outdoor dry bulb temperature.
- __T_owb__ [ºC]: Outdoor wet bulb temperature.
- __T_idb__ [ºC]: Indoor dry bulb temperature, at the coil inlet of the indoor unit.
- __T_iwb__ [ºC]: Indoor wet bulb temperature, at the coil inlet of the indoor unit.
- __F_air__ [frac]: Actual supply air flow divided by nominal supply air flow.
- __F_load__ [frac]: Partial load state of the system, calculated as the thermal power 
supplied at a given instant divided by the cooling or heating capacity at the current operation conditions. Positive for heating and negative for cooling
- __T_supply__ [ºC]: Supply air dry bulb temperature.
- __w_supply__ [g/kg]: Supply air absolute humidity.
- __efficiency_degradation__ [frac]: EER or COP degradation factor obtained from the _EER_expression_ or _COP_expression_ of the equipment.




