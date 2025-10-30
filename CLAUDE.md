# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenSimula is a component-based time simulation environment in Python for building energy modeling and HVAC system simulation. It implements ASHRAE 140 test cases and provides comprehensive building thermal simulation capabilities.

## Common Commands

### Testing
```bash
# Run all tests
uv run pytest test

# Run a single test file
uv run pytest test/test_Case_600FF.py

# Run specific test
uv run pytest test/test_Project.py::test_project_parameters
```

### Building and Installation
```bash
# Sync dependencies (install all required packages)
uv sync

# Install in development mode (editable)
uv pip install -e .

# Build distribution
uv build

# Build documentation
uv run mkdocs build --clean
```

### Documentation
```bash
# Build MkDocs documentation
uv run mkdocs build --clean

# Documentation is output to docs/ directory
# Source files are in mkdocs/ directory
```

## Architecture Overview

### Core Architecture Pattern

OpenSimula follows a hierarchical component-based simulation architecture:

1. **Simulation** → Top-level environment containing projects
2. **Project** → Contains components and manages time-stepping simulation
3. **Component** → Base class for all simulation components (spaces, HVAC systems, materials, etc.)
4. **Parameter_container** → Parent class that manages parameters for Projects and Components
5. **Variable** → Time-series data storage for component outputs

### Key Concepts

#### Component System
- All components inherit from `Component` class (src/opensimula/Component.py)
- Components are registered in `src/opensimula/components/__init__.py` with `DEFAULT_COMPONENTS_ORDER`
- Each component has:
  - **Parameters**: Configuration values (via `Parameter_container`)
  - **Variables**: Time-series output data
  - Lifecycle methods: `pre_simulation()`, simulation loop, `post_simulation()`

#### Simulation Execution Flow
Located in `src/opensimula/Project.py::simulate()`:

1. **Pre-simulation phase**: Initialize all components, create ordered component list
2. **Time-stepping loop**: For each time step (typically hourly for 8760 hours):
   - `_pre_iteration_()`: Prepare for iteration
   - **Inner iteration loop**: Converge coupled equations (max iterations from `n_max_iteration` parameter)
     - `_iteration_()`: Execute components in order defined by `simulation_order`
   - `_post_iteration_()`: Store results
3. **Post-simulation**: Cleanup and finalization

The simulation order (`DEFAULT_COMPONENTS_ORDER` in components/__init__.py):
- Space_type → Building_surface → Solar_surface → Opening → Space → Building → HVAC systems → Calculator

#### Parameter System
Parameters (src/opensimula/Parameters.py) provide type-safe configuration:
- `Parameter_int`, `Parameter_float`, `Parameter_string`, `Parameter_boolean`
- `Parameter_component`: References to other components
- `Parameter_component_list`: List of component references
- `Parameter_math_exp`: Mathematical expressions evaluated at runtime
- `Parameter_variable_list`: References to component variables
- All parameters support validation with `min`, `max`, units

#### Iterative Convergence
- `Iterative_process` class (src/opensimula/Iterative_process.py) implements fixed-point iteration with adaptive relaxation
- Used for coupled thermal/HVAC calculations that require iteration to converge
- Components like Space and HVAC systems use this for temperature/humidity convergence

### Component Categories

#### Building Components
- **Building**: Container for building geometry and initial conditions
- **Space**: Indoor spaces with thermal zones
- **Building_surface**: Walls, roofs, floors with construction assemblies
- **Solar_surface**: External surfaces receiving solar radiation
- **Opening**: Windows and doors
- **Construction**: Multi-layer construction definitions
- **Material**, **Glazing**, **Frame**: Construction materials

#### HVAC Components
- **HVAC_DX_system**: Direct expansion heating/cooling systems
- **HVAC_SZW_system**: Single-zone water-based HVAC
- **HVAC_MZW_system**: Multi-zone water-based HVAC
- **HVAC_perfect_system**: Ideal loads system for testing
- **HVAC_DX_equipment**, **HVAC_coil_equipment**, **HVAC_fan_equipment**: Equipment models

#### Schedule Components
- **Day_schedule**: Daily schedules with time steps and values
- **Week_schedule**: Weekly patterns referencing day schedules
- **Year_schedule**: Annual schedules with periods and week references

#### Utility Components
- **File_met**: Weather data reader (supports TMY3 format)
- **File_data**: Generic data file reader (CSV, Excel)
- **Calculator**: Custom calculation component using math expressions
- **Space_type**: Space type definitions (occupancy, lighting, equipment)

### Project Configuration

Projects are typically defined as Python dictionaries or JSON files with structure:
```python
{
    "name": "Project name",
    "time_step": 3600,  # seconds
    "n_time_steps": 8760,  # typically annual hourly
    "initial_time": "01/01/2001 00:00:00",
    "simulation_file_met": "weather_component_name",
    "shadow_calculation": "INSTANT",  # or "NO", "INTERPOLATION"
    "components": [
        {
            "type": "ComponentType",
            "name": "component_name",
            # component-specific parameters
        }
    ]
}
```

Load into simulation via:
- `project.read_dict(dictionary)`
- `project.read_json("path/to/file.json")`
- `project.read_excel("path/to/file.xlsx")`

### 3D Visualization and Shadow Calculation
- `Environment_3D` (src/opensimula/visual_3D/Environment_3D.py) handles 3D geometry and shadow calculations
- Shadow calculation modes controlled by Project parameter `shadow_calculation`
- Used for accurate solar radiation calculations on building surfaces

## ASHRAE 140 Test Suite

The `ASHRAE_140/` directory contains comprehensive validation test cases:
- **LOAD_TEST/**: Building load tests (Case 600, 900 series, etc.)
- **HEATING_TEST/**: Heating system tests (HE100-HE230 series)
- **COOLING_TEST/**: Cooling system tests (CE100-CE545 series)
- **AIR_SIDE_HVAC_TEST/**: Air-side HVAC equipment tests (AE series)
- **WEATHER_TEST/**: Weather data validation

These are implemented as Jupyter notebooks and provide examples of system usage.

## Working with Variables and Data

Components generate time-series data stored in Variable objects:
```python
# Access variable data
space.variable("temperature").values  # numpy array of hourly temperatures
space.variable("temperature").unit    # "°C"

# Get DataFrame of all component variables
df = component.variable_dataframe(
    units=True,           # Include units in column names
    frequency="D",        # Resample: None, "H", "D", "M", "Y"
    value="mean",         # Aggregation: "mean", "sum", "max", "min"
    interval=[start, end] # Date range filter
)
```

## Psychrometric Calculations

OpenSimula uses PsychroLib for all psychrometric calculations:
- Import: `import psychrolib as sicro`
- Set to SI units in Project.__init__: `sicro.SetUnitSystem(sicro.SI)`
- Simulation properties stored in `sim.props` dictionary with atmospheric pressure, humidity ratios, air density

## Development Notes

### Adding New Components
1. Create new component class inheriting from `Component` in `src/opensimula/components/`
2. Define parameters in `__init__()` using `add_parameter()`
3. Define output variables using `add_variable()`
4. Implement `check()` for validation
5. Implement simulation lifecycle methods: `pre_simulation()`, iteration methods, `post_simulation()`
6. Register in `src/opensimula/components/__init__.py`
7. Add to `DEFAULT_COMPONENTS_ORDER` if it needs specific execution order
8. Create tests in `test/` directory

### Parameter References Between Components
- Use `Parameter_component` for single component references
- Reference format in JSON/dict: `"component_name"` or `"project_name->component_name"`
- Access referenced component: `self.parameter("param_name").component`
- The Project automatically resolves component references when loading from dict/JSON

### Message System
- Use `self._sim_.message(Message("text", "TYPE"))` for logging
- Message types: "CONSOLE", "ERROR", "WARNING"
- Controlled by `sim.console_print` flag

### Testing Philosophy
- Tests use pytest framework
- Test files typically create Simulation, Project, and Components programmatically or from JSON
- ASHRAE 140 tests in notebooks compare results against standard benchmarks
