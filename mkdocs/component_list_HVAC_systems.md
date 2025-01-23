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
- __state__ [flag]: Operation of the system: off (0), heating (1), colling (2), venting (3).

### HVAC_DX_equipment

Component to define a direct expansion air conditioning system. It can be used to define compact or split 1x1 units. 

his equipment can be used for one or more HVAC systems.

#### Parameters
- **nominal_air_flow** [_float_, unit = "m³/s", default = 1, min = 0]: Nominal supply air flow.
- **nominal_total_cooling_capacity** [_float_, unit = "W", default = 0, min = 0]: Total cooling capacity at nominal cooling conditions.
- **nominal_sensible_cooling_capacity** [_float_, unit = "W", default = 0, min = 0]: Sensible cooling capacity at nominal cooling conditions.
- **nominal_cooling_power** [_float_, unit = "W", default = 0, min = 0]: Electrical power consumed by the equipment at nominal cooling conditions. It must include all the consumptions: compressor, external fan, internal fan, etc.
- **no_load_power** [_float_, unit = "W", default = 0, min = 0]: Electrical power consumed by the equipment at times when it does not supply thermal load.
- **nominal_cooling_conditions** [_float-list_, unit = "ºC", default = [27, 19, 35]]: Nominal cooling conditions, in order: indoor dry bulb temperature, indoor wet bulb temperature, outdoor dry bulb temperature.
- **total_cooling_capacity_expression** [_math_exp_, unit = "frac", default = "1"]: Mathematical expression to correct the total cooling capacity of the equipment in conditions different from the nominal ones. 
- **sensible_cooling_capacity_expression** [_math_exp_, unit = "frac", default = "1"]: Mathematical expression to correct the sensible cooling capacity of the equipment in conditions different from the nominal ones.
- **cooling_power_expression** [_math_exp_, unit = "frac", default = "1"]: Mathematical expression to correct the electric power consumption at cooling full load operation of the equipment in conditions different from the nominal ones.
- **EER_expression** [_math_exp_, unit = "frac", default = "1"]: Mathematical expression to correct the EER, defined as cooling total load supplied by de equipment divided by de electric power consumption, of the equipment in conditions different from the nominal ones. This expression should reflect the partial load behavior of the equipment.
- **nominal_heating_capacity** [_float_, unit = "W", default = 0, min = 0]: Heating capacity at nominal heating conditions.
- **nominal_heating_power** [_float_, unit = "W", default = 0, min = 0]: Electrical power consumed by the equipment at nominal heating conditions. It must include all the consumptions: compressor, external fan, internal fan, etc.
- **nominal_heating_conditions** [_float-list_, unit = "ºC", default = [20, 7, 6]]: Nominal heating conditions, in order: indoor dry bulb temperature, outdoor dry bulb temperature, outdoor wet bulb temperature.
- **heating_capacity_expression** [_math_exp_, unit = "frac", default = "1"]: Mathematical expression to correct the heating capacity of the equipment in conditions different from the nominal ones. 
- **heating_power_expression** [_math_exp_, unit = "frac", default = "1"]: Mathematical expression to correct the electric power consumption at heating full load operation of the equipment in conditions different from the nominal ones.
- **COP_expression** [_math_exp_, unit = "frac", default = "1"]: Mathematical expression to correct the COP, defined as heating load supplied by de equipment divided by de electric power consumption, of the equipment in conditions different from the nominal ones. This expression should reflect the partial load behavior of the equipment.
- **dry_coil_model** [_option_, default = "SENSIBLE", options = ["SENSIBLE","TOTAL","INTERPOLATION"]]: When calculating the total and sensible capacity of the equipment under non-nominal conditions, it is possible that the total capacity is lower than the sensible capacity. In such a case it will be assumed that the coil does not dehumidify and that the total capacity is equal to the sensible capacity. We will use for both values the value of the sensible if the chosen option is “SENSIBLE” and the total if the chosen option is “TOTAL”.
- **power_dry_coil_correction** [_boolean_, default = True]: When the total and sensible power are equal, dry coil, the power expression may be incorrect. If this parameter is activated the simulation will look for the wet bulb temperature that makes the total and sensible capacities equal and use that temperature in the expression that corrects the cooling power.

TODO: Explicar las variables de las que pueden depender las expresiones matemáticas ...











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
- __state__ [flag]: Operation of the system: off (0), heating (1), colling (2), venting (3).


