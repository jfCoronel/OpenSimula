# OpenSimula — Core Usage, Schedules & Files

OpenSimula is a component-based time simulation environment in Python for building energy modeling and HVAC system simulation. Always provide complete Python code using these patterns.

## Core Usage

```python
import opensimula.Simulation as Simulation

sim = Simulation()
pro = sim.new_project("Project name")
pro.read_dict(project_dict)  # or pro.read_json("file.json")
pro.simulate()

comp = pro.component("name")
comp.variable("variable_name").values                 # numpy array
comp.variable_dataframe(frequency="M", value="mean")  # DataFrame
sim.plot(pro.dates(), [comp.variable("variable_name")])
```

## Project Dictionary

```python
project_dict = {
    "name": "Project name",
    "time_step": 3600,                     # seconds
    "n_time_steps": 8760,                  # 8760 = annual hourly
    "initial_time": "01/01/2001 00:00:00", # DD/MM/YYYY hh:mm:ss
    "simulation_file_met": "met_name",     # File_met reference
    "albedo": 0.3,
    "shadow_calculation": "INSTANT",       # "NO","INSTANT","INTERPOLATION"
    "n_max_iteration": 1000,
    "components": [ ... ]
}
```

Component references: `"component_name"` (same project) or `"project_name->component_name"` (other project).

## Schedules

```python
# Day_schedule — value variation within a day
{"type": "Day_schedule", "name": "working_day",
 "time_steps": [8*3600, 5*3600, 2*3600, 4*3600],  # durations in seconds
 "values": [0, 100, 0, 80, 0],   # len(time_steps)+1 values
 "interpolation": "STEP"}        # "STEP" or "LINEAR"

# Week_schedule — Day_schedules per weekday
{"type": "Week_schedule", "name": "my_week",
 "days_schedules": ["working_day","working_day","working_day",
                    "working_day","working_day","holiday","holiday"]}
# 7 references (Mon-Sun) OR 1 for all days

# Year_schedule — Week_schedules for annual periods
{"type": "Year_schedule", "name": "my_year",
 "periods": ["01/08", "01/09"],   # "DD/MM" change-over dates
 "weeks_schedules": ["working_week","holiday_week","working_week"]}
# Variables: values
```

## File Components

```python
# File_met — reads weather file
{"type": "File_met", "name": "met",
 "file_name": "path/to/weather.met",
 "file_type": "MET",              # "MET","TMY3","TMY2","WYEC2"
 "tilted_diffuse_model": "PEREZ"} # "PEREZ","REINDL","HAY-DAVIES","ISOTROPIC"
# Variables: temperature [°C], relative_humidity [%], abs_humidity [g/kg],
#            atmospheric_pressure [Pa], wind_speed [m/s], wind_direction [°],
#            E_dir_nor, E_dif_hor, E_global_hor, E_dir_hor [W/m²],
#            sky_temperature [°C]

# File_data — reads CSV/Excel
{"type": "File_data", "name": "data",
 "file_name": "path/to/data.csv",
 "file_type": "CSV",          # "CSV" or "EXCEL"
 "file_step": "SIMULATION"}   # "SIMULATION" or "OWN"
# If file_step="OWN", also add: "initial_time": "...", "time_step": 3600
# Variables: one per data column
```

## Math Expressions

Parameters of type `Parameter_math_exp` accept Python expressions. Variables come from `input_variables`:
```python
"input_variables": ["f = my_year.values", "T = met.temperature"]
"people_density": "0.1 * f"      # uses alias 'f'
"heating_setpoint": "20"         # constant is also valid
"cooling_power_expression": "1 - 0.005*(T_idb - 27)"  # component-specific vars
```
Standard Python math functions (`sin`, `cos`, `exp`, `abs`, etc.) are available.
