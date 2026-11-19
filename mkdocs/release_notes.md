## Release notes

### 0.10.0

Water plants with several generators, primary / secondary circuits and boilers; zones defined by load records; a gallery of examples. **It breaks the compatibility of the water systems** with 0.9: see [Upgrading from 0.9](#upgrading-from-09).

#### New

- **Gallery of examples** ([Examples](examples.md)): nine projects that build on each other, from a schedule to a water plant, shipped with the package; `opensimula examples [folder]` copies them (with the weather and load files they read) to a folder.
- **`Load_space`**: a zone defined by its load records instead of by its building, served by the air systems like a `Space`: an installation can be simulated from precalculated loads. A model of two nodes (air and thermal mass, construction classes of ISO 13790) gives the response when the systems do not supply the load, and the infiltration of the record can be replaced by another one. Example 08.
- **`Boiler`**: equipment data of a boiler, efficiency on the lower heating value as a function of the part load and of the water temperatures (condensing boilers), fuel, auxiliary power.
- **`HVAC_water_generator`**: the generators of a water plant, with a `Chiller_heat_pump` or a `Boiler`, their own pump and availability, and several identical units (`number_of_units`). A plant has several generators sharing the load in order of priority or at the same part load (`sequencing`).
- **Header** (primary / secondary) in `HVAC_water_system` when it has secondary `pumps`: the generators move water only while they run, and the mixing in the header (bypass in both directions) is simulated.
- **`HVAC_water_circuit`**: secondary circuits fed by a plant, each with its own pumps, availability and, with a mixing valve, its own supply temperature. Example 09.
- **`HVAC_MZW_system` connected to its water systems** (coils and reheat): with `water_source` "WATER_SYSTEM" it takes the water temperature from the plant and gives it its load (before it used the fixed temperatures).
- Coils take heat or cold from a plant only if it can give it in its mode (`can_heat()`, `can_cool()`).
- At full load the capacity of the generators is the one at the actual water temperature.
- Results viewer: monthly and yearly values drawn as bars, and the aggregations "Mean without zeros", "Sum of positives" and "Sum of negatives".
- Editor: numeric fields always with the decimal point (the browser showed a comma in some languages); Plotly bundled with the package (no download).

#### Fixes that change results

- `Calculator` read as 0 the variables of other components computed in the same time step (now the values of the step).
- `HVAC_water_system`: `Q_coils` was always stored as 0.
- `File_data` with `file_step` "SIMULATION": when the number of time steps was not a multiple of the rows of the file, the second and later columns were shifted.
- `HVAC_MZW_system` VAV: the outdoor air fraction is limited to 0-1 (rounding could leave it slightly negative and stop the simulation).
- The ASHRAE 140 validation results do not change.

#### Upgrading from 0.9

The water systems changed. A project of 0.9 with an `HVAC_water_system` must be updated by hand (the others need nothing):

1. The generator, its pump and the water flow are no longer parameters of the plant: create an `HVAC_water_generator` with the equipment and the pump, and refer to it in `generators`. The water flow is the `nominal_water_flow` of the equipment (it was `design_water_flow`).

    0.9:
    <pre><code class="json">
    {"type": "HVAC_water_system", "name": "water_system",
     "water_thermal_generator": "heat_pump", "pump": "pump", "design_water_flow": 0.4137,
     "heating_water_setpoint": "50", ...}
    </code></pre>

    0.10:
    <pre><code class="json">
    {"type": "HVAC_water_generator", "name": "generator", "equipment": "heat_pump", "pump": "pump"},
    {"type": "HVAC_water_system", "name": "water_system", "generators": ["generator"],
     "heating_water_setpoint": "50", ...}
    </code></pre>

2. The variables of `HVAC_water_system` have new names:

    | 0.9 | 0.10 |
    |---|---|
    | `T_WCI`, `T_WCO` | `T_supply`, `T_return` |
    | `T_WGO`, `T_WGI` | `T_generators_out`, `T_generators_in` |
    | `T_WAVG` | `T_mean` |
    | `water_flow` | `secondary_flow` (and `primary_flow`) |
    | `Q_gen` | `Q_generators` |
    | `generator_power` | `generators_power` (and the new `generators_fuel_power`, `electric_power`) |
    | `pump_power` | `pumps_power` |
    | `generator_efficiency`, `generator_part_load` | `efficiency`, `F_load` of each `HVAC_water_generator` |

3. The examples copied with `opensimula examples` from 0.9 are not overwritten: delete `07_fan_coil.json` (or the whole folder) and copy them again.

4. A project that lists its own `simulation_order` gets the new component types (`Load_space`, `HVAC_water_circuit`, `HVAC_water_generator`) at the beginning, which is a valid order; add them to the list to place them.

### 0.9.0

Graphical interface: results viewer with a 3D view, graph view of the components in the editor, and the `opensimula gui` app (with the `gui` extra). Fix of the surface temperatures of openings.
