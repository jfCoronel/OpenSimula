## Component List for HVAC system definition
### HVAC_perfect_system

Component for the perfect conditioning of a space. With this component we can obtain the heating and cooling loads (sensible and latent).

#### Parameters
- **file_met** [_component_, default = "not_defined", component type = File_met]: Reference to the component where the weather file is defined.
- **space** [_component_, default = "not_defined", component type = Space]: Reference to the "Space" component to be controlled by this system.
- **outdoor_air_flow** [_float_, unit = "m³/s ", default = 0, min = 0]: Outside air flow rate (ventilation) that is treated by the system. This flow rate is only entered if the system is in operation.
- **input_variables** [_variable_list_, default = []]: List of variables from other components used in this component. They may be used in parameters of the type math_exp.
- **heating_setpoint** [_math_exp_, unit = "°C", default = "20"]: Space heating setpoint temperature. The mathematical expression may contain any of the variables declared in the "input_variables" parameter, to be able to reflect the time variation of this value.
- **cooling_setpoint** [_math_exp_, unit = "°C", default = "25"]: Space Cooling setpoint temperature. The mathematical expression may contain any of the variables declared in the "input_variables" parameter, to be able to reflect the time variation of this value.
- **humidifying_setpoint** [_math_exp_, unit = "%", default = "0"]: Space relative humidity setpoint for humidification. If the relative humidity of the space is below this value, latent heat is added to maintain the relative humidity. The mathematical expression may contain any of the variables declared in the "input_variables" parameter, to be able to reflect the time variation of this value.
- **dehumidifying_setpoint** [_math_exp_, unit = "%", default = "100"]: Space relative humidity setpoint for dehumidification. If the relative humidity of the space is higher this value, latent heat is removed to maintain the relative humidity. The mathematical expression may contain any of the variables declared in the "input_variables" parameter, to be able to reflect the time variation of this value.
- **sytem_on_off** [_math_exp_, unit = "on/off", default = "1"]: If this value is 0, the system will be off, otherwise it will be on. The mathematical expression may contain any of the variables declared in the "input_variables" parameter, to be able to reflect the time variation of this value.

**Example:**
<pre><code class="python">
...

system = osm.components.HVAC_perfect_system("system",project)
param = {
        "space": "space_1",
        "file_met": "Denver",
        "outdoor_air_flow": 0.1,
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

- __Q_sensible_space__ [W]: Sensible heat introduced by the system to control the space temprature. Positive for heating and negative for cooling.
- __Q_latent_space__ [W]: Latent heat introduced by the system to control humidity. Positive for humidification and negative for dehumidification.
- __Q_sensible_vent__ [W]: Sensible heat introduced by the ventilation air.
- __Q_latent_vent__ [W]: Latent heat introduced by the ventilation air.
- __Q_sensible_system__ [W]: Total sensible heat supplied by the system. Sum of space and ventilation.
- __Q_sensible_system__ [W]: Total latent heat supplied by the system. Sum of space and ventilation.
- __heating_setpoint__ [°C]: Heating setpoint temperature.
- __cooling_setpoint__ [°C]: Cooling setpoint temperature.
- __humififying_setpoint__ [%]: Low relative humidity setpoint.
- __dehumidifying_setpoint__ [%]: High relative humidity setpoint.
- __system_on_off__ [on/off]: Operation of the system, on (1), off (0).

