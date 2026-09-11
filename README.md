![Logo](https://jfcoronel.github.io/OpenSimula/img/logo_opensimula.png)

# OpenSimula

[![PyPI version](https://img.shields.io/pypi/v/opensimula)](https://pypi.org/project/opensimula/)
[![Python versions](https://img.shields.io/pypi/pyversions/opensimula)](https://pypi.org/project/opensimula/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**OpenSimula** is a component-based time simulation environment in Python, focused on the
thermal and energy simulation of buildings and their HVAC installations — though it can be
used to simulate any system whose state evolves over time. It implements the [ASHRAE
140](https://www.ashrae.org/technical-resources/bookstore/method-of-test-for-the-evaluation-of-building-energy-analysis-computer-programs)
standard test suite to validate its building load and HVAC calculations.

[**Documentation**](https://jfcoronel.github.io/OpenSimula/) · [Getting started](https://jfcoronel.github.io/OpenSimula/getting_started/) · [User guide](https://jfcoronel.github.io/OpenSimula/user_guide/) · [Component list](https://jfcoronel.github.io/OpenSimula/component_list/)

## What it does

A project is built from **components** — spaces, walls, windows, constructions, schedules,
HVAC equipment, weather files — wired together and simulated hour by hour (or at any other
time step). OpenSimula takes care of:

- **Building thermal simulation**: multi-space heat balance, constructions with thermal mass,
  windows and solar gains, ground-coupled surfaces, internal gains and schedules.
- **HVAC systems**: from an ideal loads system (`HVAC_perfect_system`) to direct-expansion and
  water-based single- and multi-zone systems, coils, fans, pumps, chillers and heat pumps.
- **Solar geometry and shadows**: direct and diffuse shadow calculations between the surfaces
  of a project, with an interactive 3D [Plotly](https://plotly.com/python/) view — including
  an animated view of shadows changing throughout the day.
- **Everything else a simulation needs**: psychrometrics (via
  [PsychroLib](https://github.com/psychrometrics/psychrolib)), day/week/year schedules,
  arbitrary math expressions as inputs, and reading weather data (TMY3, MET) or generic data
  files (CSV, Excel).
- **Validation against ASHRAE 140**: the `ASHRAE_140/` folder in this repository reproduces
  the standard's load, heating, cooling, air-side HVAC and weather test cases as runnable
  notebooks, comparing OpenSimula's results against the reference values.

Projects can be defined as plain Python dictionaries, JSON or Excel files, and results come
back as component `Variable` time series or pandas `DataFrame`s, ready to plot or export.

## Installation

```bash
pip install opensimula
```

Requires Python 3.12 or later.

## Quick example

```python
import opensimula as osm

project_dict = {
    "name": "First example",
    "time_step": 3600,
    "n_time_steps": 24 * 7,
    "initial_time": "01/01/2001 00:00:00",
    "components": [
        {
            "type": "Day_schedule",
            "name": "working_day",
            "time_steps": [8 * 3600, 5 * 3600, 2 * 3600, 4 * 3600],
            "values": [0, 100, 0, 80, 0],
            "interpolation": "STEP",
        },
        {
            "type": "Day_schedule",
            "name": "holiday_day",
            "time_steps": [],
            "values": [0],
            "interpolation": "STEP",
        },
        {
            "type": "Week_schedule",
            "name": "office_week",
            "days_schedules": ["working_day"] * 5 + ["holiday_day"] * 2,
        },
    ],
}

sim = osm.Simulation()
pro = sim.new_project("First example")
pro.read_dict(project_dict)
pro.simulate()

sim.plot(pro.dates(), [pro.component("office_week").variable("values")])
```

This is deliberately minimal — the [Getting started](https://jfcoronel.github.io/OpenSimula/getting_started/)
guide walks through a full building, and the `jupyter_test/` and `ASHRAE_140/` folders in
this repository contain complete, runnable building and HVAC examples.

## Working in Jupyter

OpenSimula ships an interactive project editor as a [Jupyter
widget](https://jfcoronel.github.io/OpenSimula/user_guide/#project-editor) (`pro.editor()`),
built on [anywidget](https://anywidget.dev/) so it works the same in Jupyter, JupyterLab, VS
Code notebooks and Marimo. It shows every component's parameters as a form generated from
each component's own schema, together with an interactive 3D view of the building.

![Project editor example](https://jfcoronel.github.io/OpenSimula/img/editor_3d.png)

## Component types

Components are grouped by what they define:

- **Building**: `Building`, `Space_type`, `Space`, `Building_surface`, `Opening`, `Solar_surface`.
- **Constructions**: `Material`, `Construction`, `Glazing`, `Frame`, `Opening_type`.
- **HVAC (air side)**: `HVAC_perfect_system`, `DX_unit`, `HVAC_DX_system`, `Water_coil`, `Fan`, `HVAC_SZW_system`, `HVAC_MZW_system`.
- **HVAC (water side)**: `Pump`, `Chiller_heat_pump`, `HVAC_water_system`.
- **Schedules**: `Day_schedule`, `Week_schedule`, `Year_schedule`.
- **Files**: `File_met`, `File_data`.
- **Utilities**: `Calculator`.

See the [Component list](https://jfcoronel.github.io/OpenSimula/component_list/) for every
parameter and variable of each one.

## Package dependencies

- numpy
- pandas
- scipy
- shapely
- psychrolib
- plotly
- matplotlib
- anywidget
- jsonschema
- nbformat
- openpyxl
- tqdm

These are installed automatically with `pip install opensimula`.

## Documentation and support

Full documentation, including the getting started guide, user guide and component
reference, is at [jfcoronel.github.io/OpenSimula](https://jfcoronel.github.io/OpenSimula/).
Bugs and feature requests are tracked on
[GitHub Issues](https://github.com/jfCoronel/OpenSimula/issues).

## Main Developers

* [Juan F. Coronel](http://jfc.us.es), Universidad de Sevilla

## License

OpenSimula is released under the [MIT License](LICENSE).
