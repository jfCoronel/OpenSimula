# OpenSimula AI Assistant Instructions

OpenSimula is a component-based time simulation environment in Python for building energy modeling and HVAC system simulation.

When helping with OpenSimula code, always provide complete, working Python code using these patterns.

## Core Usage Pattern

```python
import opensimula.Simulation as Simulation

sim = Simulation()
pro = sim.new_project("Project name")
pro.read_dict(project_dict)   # or pro.read_json("file.json")
pro.simulate()

# Access results
comp = pro.component("component_name")
comp.variable("variable_name").values          # numpy array
comp.variable_dataframe(frequency="M", value="mean")  # pandas DataFrame

# Plot
sim.plot(pro.dates(), [comp.variable("variable_name")])
```

## Project Definition Dictionary

```python
project_dict = {
    "name": "Project name",
    "time_step": 3600,                     # seconds (default 3600)
    "n_time_steps": 8760,                  # 8760 = annual hourly
    "initial_time": "01/01/2001 00:00:00", # format DD/MM/YYYY hh:mm:ss
    "simulation_file_met": "met_name",     # optional, File_met component reference
    "albedo": 0.3,
    "shadow_calculation": "INSTANT",       # "NO", "INSTANT", "INTERPOLATION"
    "n_max_iteration": 1000,
    "components": [ ... ]
}
```

Every component dictionary requires `"type"` and `"name"`. Component references use `"component_name"` (same project) or `"project_name->component_name"` (other project).

## Schedules

```python
# Day_schedule — value variation within a day
{"type": "Day_schedule", "name": "working_day",
 "time_steps": [8*3600, 5*3600, 2*3600, 4*3600],  # durations; last period = rest of day
 "values": [0, 100, 0, 80, 0],   # len(time_steps)+1 values
 "interpolation": "STEP"}        # "STEP" or "LINEAR"

# Week_schedule — assigns Day_schedules to weekdays
{"type": "Week_schedule", "name": "my_week",
 "days_schedules": ["working_day","working_day","working_day",
                    "working_day","working_day","holiday","holiday"]}
# 7 references (Mon-Sun) OR 1 reference for all days

# Year_schedule — assigns Week_schedules to annual periods
{"type": "Year_schedule", "name": "my_year",
 "periods": ["01/08", "01/09"],   # "DD/MM" change-over dates
 "weeks_schedules": ["working_week", "holiday_week", "working_week"]}
# Variables: values
```

## Weather / File Components

```python
# File_met — reads weather file
{"type": "File_met", "name": "met",
 "file_name": "path/to/weather.met",
 "file_type": "MET",              # "MET", "TMY3", "TMY2", "WYEC2"
 "tilted_diffuse_model": "PEREZ"} # "PEREZ","REINDL","HAY-DAVIES","ISOTROPIC"
# Variables: temperature, relative_humidity, abs_humidity, atmospheric_pressure,
#            wind_speed, wind_direction, E_dir_nor, E_dif_hor, E_global_hor,
#            E_dir_hor, sky_temperature [units: °C, %, g/kg, Pa, m/s, °, W/m²]

# File_data — reads CSV/Excel
{"type": "File_data", "name": "data",
 "file_name": "path/to/data.csv",
 "file_type": "CSV",          # "CSV" or "EXCEL"
 "file_step": "SIMULATION"}   # "SIMULATION" or "OWN" (add initial_time + time_step if OWN)
# Variables: one per data column
```

## Construction Materials

```python
{"type": "Material", "name": "brick",
 "conductivity": 0.9, "density": 1800, "specific_heat": 840}
# OR: "use_resistance": True, "thermal_resistance": 0.2  [m²·K/W]

{"type": "Construction", "name": "ext_wall",
 "solar_alpha": 0.6, "lw_epsilon": 0.9,
 "materials": ["plaster", "brick", "insulation", "plaster"],
 "thicknesses": [0.015, 0.20, 0.08, 0.015]}  # meters

{"type": "Glazing", "name": "double_glass",
 "solar_tau": 0.589, "solar_rho": 0.117, "lw_epsilon": 0.837,
 "g": 0.65, "U": 2.8}

{"type": "Frame", "name": "alu_frame",
 "solar_alpha": 0.6, "lw_epsilon": 0.9, "thermal_resistance": 0.5}

{"type": "Opening_type", "name": "window_type",
 "glazing": "double_glass", "frame": "alu_frame",
 "glazing_fraction": 0.8, "frame_fraction": 0.2}
```

## Building Components

```python
{"type": "Building", "name": "building",
 "azimuth": 0,              # degrees, 0=North, 90=East
 "ref_point": [0, 0, 0],    # [x, y, z] global coordinates in meters
 "initial_temperature": 20, "initial_humidity": 7.3}

# Space_type — occupancy and internal gains (supports math expressions)
{"type": "Space_type", "name": "office",
 "input_variables": ["f = my_year.values"],  # schedule alias
 "people_density": "0.1 * f",  # persons/m², math expression
 "people_sensible": 75, "people_latent": 55, "people_radiant_fraction": 0.5,
 "light_density": "10 * f",    # W/m²
 "light_radiant_fraction": 0.5,
 "other_gains_density": "5 * f",
 "other_gains_radiant_fraction": 0.4, "other_gains_latent_fraction": 0.0,
 "infiltration": "0.5 * f"}    # ACH
# Variables: Q_people_conv/rad/lat, Q_light_conv/rad, Q_other_conv/rad/lat [W/m²]

# Space — thermal zone
{"type": "Space", "name": "zone_1",
 "building": "building", "space_type": "office",
 "floor_area": 50, "volume": 150,   # m², m³
 "furniture_weight": 0,             # kg/m²
 "convergence_DT": 0.01, "convergence_Dw": 0.01}
# Variables: temperature [°C], humidity [g/kg], Q_infiltration, Q_people,
#            Q_light, Q_other, Q_solar, Q_surface_conv, Q_surface_rad,
#            Q_system, Q_system_latent [W], m_infiltration [kg/s]

# Building_surface — wall/roof/floor
{"type": "Building_surface", "name": "south_wall",
 "shape": "RECTANGLE",   # or "POLYGON" (use "polygon": [[x,y],...])
 "width": 5.0, "height": 3.0,      # m
 "ref_point": [0, 0, 0],           # local building coordinates
 "azimuth": 180, "altitude": 90,   # degrees (180=South, 90=vertical)
 "surface_type": "EXTERIOR",       # "EXTERIOR","INTERIOR","UNDERGROUND","VIRTUAL"
 "construction": "ext_wall",
 "spaces": ["zone_1"],             # 1 space (EXTERIOR) or 2 (INTERIOR)
 "h_cv": [25, 7.7]}                # [exterior, interior] W/(m²·K)
# Variables: T_ext, T_int, T_surf_ext, T_surf_int [°C], Q_cond, Q_cv_int,
#            Q_cv_ext, Q_solar_abs, Q_lw_rad_ext, Q_lw_rad_int [W], E_solar [W/m²]

# Opening — window/door
{"type": "Opening", "name": "south_window",
 "surface": "south_wall", "shape": "RECTANGLE",
 "width": 1.5, "height": 1.2,
 "ref_point": [1.0, 0.9, 0],  # position within surface
 "opening_type": "window_type",
 "setback": 0.1, "h_cv": [25, 7.7]}
# Variables: T_ext, T_int, T_surf_ext, T_surf_int [°C], tau_solar,
#            Q_solar_trans, Q_cond, Q_cv_int, Q_cv_ext, Q_lw_rad_ext, Q_lw_rad_int [W]

# Solar_surface — shading (overhang, fin)
{"type": "Solar_surface", "name": "overhang",
 "coordinate_system": "BUILDING",  # or "GLOBAL"
 "building": "building", "shape": "RECTANGLE",
 "width": 2.0, "height": 0.5, "ref_point": [0, 3.0, 0],
 "azimuth": 180, "altitude": 0,    # altitude 0 = horizontal
 "cast_shadows": True, "calculate_solar_radiation": False}
```

## HVAC Systems

```python
# HVAC_perfect_system — ideal loads for load calculations
{"type": "HVAC_perfect_system", "name": "ideal_sys",
 "space": "zone_1",
 "input_variables": ["f = my_year.values"],
 "outdoor_air_flow": 0.05,     # m³/s or math expression
 "heating_setpoint": "20",     # °C, math expression
 "cooling_setpoint": "26",
 "humidifying_setpoint": "-100",   # g/kg, very low = disabled
 "dehumidifying_setpoint": "100",  # g/kg, very high = disabled
 "system_on_off": "f"}             # 1=on, 0=off
# Variables: Q_sensible, Q_latent, Q_total [W], outdoor_air_flow [m³/s],
#            heating_setpoint, cooling_setpoint [°C], state [1/-1/0]

# DX_unit — direct-expansion equipment model
{"type": "DX_unit", "name": "dx_equip",
 "nominal_air_flow": 0.417,                     # m³/s
 "nominal_total_cooling_capacity": 5000,         # W
 "nominal_sensible_cooling_capacity": 3750,
 "nominal_cooling_power": 1500,
 "indoor_fan_power": 150,
 "nominal_cooling_conditions": [27, 19, 35, 24], # [T_idb, T_iwb, T_odb, T_owb] °C
 "total_cooling_capacity_expression": "1.0",     # uses T_idb,T_iwb,T_odb,T_owb,F_air,F_load
 "sensible_cooling_capacity_expression": "1.0",
 "cooling_power_expression": "1.0",
 "nominal_heating_capacity": 5500,
 "nominal_heating_power": 1600,
 "nominal_heating_conditions": [21, 7, 6],       # [T_idb, T_odb, T_owb] °C
 "heating_capacity_expression": "1.0",
 "heating_power_expression": "1.0",
 "indoor_fan_operation": "CONTINUOUS",           # "CONTINUOUS" or "CYCLING"
 "dry_coil_model": "TOTAL"}                      # "SENSIBLE" or "TOTAL"

# HVAC_DX_system — DX system
{"type": "HVAC_DX_system", "name": "dx_sys",
 "space": "zone_1", "equipment": "dx_equip",
 "air_flow": 0.417, "outdoor_air_fraction": 0.1,
 "input_variables": ["f = my_year.values"],
 "heating_setpoint": "20", "cooling_setpoint": "26",
 "system_on_off": "f",
 "economizer": "NO",   # "NO","TEMPERATURE","TEMPERATURE_NOT_INTEGRATED","ENTHALPY","ENTHALPY_LIMITED"
 "economizer_DT": 2}
# Variables: state, Q_sensible, Q_latent, Q_total [W], total_power [W],
#            EER, COP, T_supply, T_mixed, T_outdoor [°C], fan_power [W], ...

# Water_coil — water heating/cooling coil
{"type": "Water_coil", "name": "cool_coil",
 "nominal_air_flow": 0.5,
 "nominal_cooling_water_flow": 0.02, "nominal_total_cooling_capacity": 10000,
 "nominal_sensible_cooling_capacity": 7500,
 "nominal_cooling_conditions": [27, 19, 7, 0.02],  # [T_idb, T_iwb, T_iw, F_water]
 "nominal_heating_water_flow": 0.02, "nominal_heating_capacity": 12000,
 "nominal_heating_conditions": [21, 60, 0.02],     # [T_idb, T_iw, F_water]
 "heating_epsilon_expression": "1.0",
 "cooling_epsilon_expression": "1.0",
 "cooling_adp_epsilon_expression": "1.0"}
# expressions use: T_idb, T_iwb, T_iw, F_air, F_water

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
#            T_supply, T_mixed, T_outdoor [°C], coil_effectiveness, ...

# HVAC_MZW_system — multi-zone water-based HVAC (VAV/Reheat)
{"type": "HVAC_MZW_system", "name": "mzw_sys",
 "spaces": ["zone_1", "zone_2"],
 "air_flow_fractions": [0.5, 0.5], "min_air_flow_fractions": [0.3, 0.3],
 "cooling_coil": "cool_coil", "heating_coil": "heat_coil",
 "supply_fan": "supply_fan", "air_flow": 1.0, "outdoor_air_fraction": 0.15,
 "supply_heating_setpoint": "12", "supply_cooling_setpoint": "14",
 "spaces_setpoint": ["20", "22"],  # one math expression per space
 "system_on_off": "1",
 "vav": True, "reheat": True, "reheat_coils": ["reheat_1", "reheat_2"]}
```

## Utility: Calculator

```python
{"type": "Calculator", "name": "my_calc",
 "input_variables": ["T = met.temperature", "w = met.abs_humidity"],
 "output_variables": ["T_F", "W_kg"],
 "output_units": ["°F", "kg/kg a.s."],
 "output_expressions": ["T * 9/5 + 32", "w / 1000"]}
# Standard Python math functions supported in expressions
```

## Accessing Results

```python
# Single variable — numpy array
values = pro.component("zone_1").variable("temperature").values

# All variables as DataFrame
df = pro.component("zone_1").variable_dataframe(
    units=True,       # include units in column names
    frequency="M",    # None=sim step, "H"=hourly, "D"=daily, "M"=monthly, "Y"=yearly
    value="mean",     # "mean", "max", "min", "sum"
    interval=None     # None=all, or [start_datetime, end_datetime]
)

# Plot
sim.plot(pro.dates(), [
    pro.component("zone_1").variable("temperature"),
    pro.component("met").variable("temperature")
], names=["Zone", "Outdoor"], frequency="D", value="mean")

# Parameter and component inspection
pro.component("zone_1").parameter_dataframe()
pro.component_dataframe("Space")
```

## Key Tips

- **Math expressions**: plain Python syntax using aliases from `input_variables`. E.g. `"0.1 * f"`, `"sin(x)"`, `"t**2"`
- **Schedules drive HVAC**: connect Year_schedule → Space_type and HVAC setpoints via `input_variables`
- **Simulation order**: Space_type → Building_surface → Solar_surface → Opening → Space → Building → HVAC → Calculator
- **Shadow calculation**: `"INTERPOLATION"` for speed, `"INSTANT"` for accuracy
- **Always validate**: call `pro.check()` before `pro.simulate()` to catch reference errors
- **UNDERGROUND surfaces**: use UNE-EN ISO 13370 parameters (`ground_material`, `exterior_perimeter_fraction`, `groundwater_depth`)
