# OpenSimula — HVAC Systems, Calculator & Results

## HVAC Systems

```python
# HVAC_perfect_system — ideal loads, no real equipment
{"type": "HVAC_perfect_system", "name": "ideal_sys",
 "space": "zone_1",
 "input_variables": ["f = my_year.values"],
 "outdoor_air_flow": 0.05,         # m³/s or math expression
 "heating_setpoint": "20",         # °C, math expression
 "cooling_setpoint": "26",
 "humidifying_setpoint": "-100",   # g/kg, very low = disabled
 "dehumidifying_setpoint": "100",  # g/kg, very high = disabled
 "system_on_off": "f"}             # 1=on, 0=off
# Variables: Q_sensible, Q_latent, Q_total [W], outdoor_air_flow [m³/s],
#            heating_setpoint, cooling_setpoint [°C], state [1=heat,-1=cool,0=off]

# DX_unit — direct-expansion equipment model
{"type": "DX_unit", "name": "dx_equip",
 "nominal_air_flow": 0.417,                      # m³/s
 "nominal_total_cooling_capacity": 5000,          # W
 "nominal_sensible_cooling_capacity": 3750,
 "nominal_cooling_power": 1500, "indoor_fan_power": 150,
 "nominal_cooling_conditions": [27, 19, 35, 24],  # [T_idb,T_iwb,T_odb,T_owb] °C
 "total_cooling_capacity_expression": "1.0",      # vars: T_idb,T_iwb,T_odb,T_owb,F_air,F_load
 "sensible_cooling_capacity_expression": "1.0",
 "cooling_power_expression": "1.0",
 "nominal_heating_capacity": 5500, "nominal_heating_power": 1600,
 "nominal_heating_conditions": [21, 7, 6],        # [T_idb,T_odb,T_owb] °C
 "heating_capacity_expression": "1.0",
 "heating_power_expression": "1.0",
 "indoor_fan_operation": "CONTINUOUS",            # "CONTINUOUS" or "CYCLING"
 "dry_coil_model": "TOTAL"}                       # "SENSIBLE" or "TOTAL"

# HVAC_DX_system — DX air-conditioning system
{"type": "HVAC_DX_system", "name": "dx_sys",
 "space": "zone_1", "equipment": "dx_equip",
 "air_flow": 0.417, "outdoor_air_fraction": 0.1,
 "input_variables": ["f = my_year.values"],
 "heating_setpoint": "20", "cooling_setpoint": "26", "system_on_off": "f",
 "economizer": "NO",    # "NO","TEMPERATURE","TEMPERATURE_NOT_INTEGRATED","ENTHALPY","ENTHALPY_LIMITED"
 "economizer_DT": 2}    # K, temperature difference threshold
# Variables: state, Q_sensible, Q_latent, Q_total [W], total_power [W],
#            EER, COP, T_supply, T_mixed, T_outdoor [°C], fan_power [W]

# Water_coil — water heating/cooling coil
{"type": "Water_coil", "name": "cool_coil",
 "nominal_air_flow": 0.5,
 "nominal_cooling_water_flow": 0.02,
 "nominal_total_cooling_capacity": 10000,
 "nominal_sensible_cooling_capacity": 7500,
 "nominal_cooling_conditions": [27, 19, 7, 0.02],  # [T_idb,T_iwb,T_iw,F_water]
 "nominal_heating_water_flow": 0.02,
 "nominal_heating_capacity": 12000,
 "nominal_heating_conditions": [21, 60, 0.02],     # [T_idb,T_iw,F_water]
 "heating_epsilon_expression": "1.0",              # vars: T_idb,T_iwb,T_iw,F_air,F_water
 "cooling_epsilon_expression": "1.0",
 "cooling_adp_epsilon_expression": "1.0"}

# Fan
{"type": "Fan", "name": "supply_fan",
 "nominal_air_flow": 0.5, "nominal_pressure": 250, "nominal_power": 150,
 "pressure_expression": "1.0",  # function of F_air
 "power_expression": "1.0"}

# HVAC_SZW_system — single-zone water-based HVAC
{"type": "HVAC_SZW_system", "name": "szw_sys",
 "space": "zone_1",
 "cooling_coil": "cool_coil", "heating_coil": "heat_coil",
 "supply_fan": "supply_fan", "return_fan": "not_defined",
 "air_flow": 0.5, "outdoor_air_fraction": 0.15,
 "input_variables": ["f = my_year.values"],
 "heating_setpoint": "20", "cooling_setpoint": "26", "system_on_off": "f",
 "fan_operation": "CYCLING",      # "CONTINUOUS" or "CYCLING"
 "water_source": "UNKNOWN",       # "UNKNOWN" or "WATER_LOOP"
 "cooling_water_flow": 0.02, "heating_water_flow": 0.02,
 "inlet_cooling_water_temp": 7, "inlet_heating_water_temp": 60,
 "water_flow_control": "ON_OFF",  # "ON_OFF" or "PROPORTIONAL"
 "economizer": "NO"}
# Variables: state, Q_sensible, Q_latent, Q_total [W], fan_power [W],
#            T_supply, T_mixed, T_outdoor [°C], coil_effectiveness

# HVAC_MZW_system — multi-zone water-based HVAC (VAV/Reheat)
{"type": "HVAC_MZW_system", "name": "mzw_sys",
 "spaces": ["zone_1", "zone_2"],
 "air_flow_fractions": [0.5, 0.5], "min_air_flow_fractions": [0.3, 0.3],
 "cooling_coil": "cool_coil", "heating_coil": "heat_coil",
 "supply_fan": "supply_fan", "air_flow": 1.0, "outdoor_air_fraction": 0.15,
 "supply_heating_setpoint": "12", "supply_cooling_setpoint": "14",
 "spaces_setpoint": ["20", "22"],   # one math expression per space
 "system_on_off": "1",
 "vav": True, "reheat": True,
 "reheat_coils": ["reheat_1", "reheat_2"]}  # one Water_coil per zone
```

## Calculator — Custom Variables

```python
{"type": "Calculator", "name": "my_calc",
 "input_variables": ["T = met.temperature", "w = met.abs_humidity"],
 "output_variables": ["T_F", "W_kg"],
 "output_units": ["°F", "kg/kg a.s."],
 "output_expressions": ["T * 9/5 + 32", "w / 1000"]}
# Standard Python math functions supported. Aliases from input_variables usable in expressions.
```

## Accessing Results After Simulation

```python
# Single variable — numpy array
values = pro.component("zone_1").variable("temperature").values

# All variables as DataFrame
df = pro.component("zone_1").variable_dataframe(
    units=True,       # include units in column names
    frequency="M",    # None=sim step | "H"=hourly | "D"=daily | "M"=monthly | "Y"=yearly
    value="mean",     # "mean" | "max" | "min" | "sum"
    interval=None     # None=all, or [start_datetime, end_datetime]
)

# Plot one or more variables
sim.plot(pro.dates(), [
    pro.component("zone_1").variable("temperature"),
    pro.component("met").variable("temperature")
], names=["Zone", "Outdoor"], frequency="D", value="mean")

# Inspect parameters and component lists
pro.component("zone_1").parameter_dataframe()
pro.component_dataframe("Space")           # all Space components
```

## Key Tips

- **Validate first**: call `pro.check()` before `pro.simulate()` to catch reference errors
- **Math expressions**: plain Python syntax; vars come from `input_variables` aliases
- **Schedule linkage**: connect Year_schedule to HVAC setpoints and Space_type via `input_variables`
- **Shadow calculation**: `"INTERPOLATION"` = fast; `"INSTANT"` = accurate
- **Simulation order**: Space_type → Building_surface → Solar_surface → Opening → Space → Building → HVAC → Calculator
- **Component reference format**: `"name"` (same project) or `"project->name"` (cross-project)
