## Release notes

This is the list of changes to opensimula between each release. For full details, see the commit logs.

### Next version (not released yet)

#### New

- **Radiators**: `Radiator` (EN 442 characteristic equation) and `HVAC_radiator_system`, the radiators of a zone fed by a water plant or circuit, with a thermostatic valve or without control; an uncontrolled system of the zone, so it can share it with a cooling system. Their radiant part goes to the surfaces of the zone (by area, or among floor, ceiling and walls) with the long-wave radiosity of the building, or to the thermal mass of a `Load_space`; any system can do the same (`radiant_to_air()`, `add_radiant_system()` of the zones).

#### Fixes that change results

- `Space` and `Load_space`: `u_system_sensible_heat` (and `u_system_latent_heat`) did not include the direct heat (and water) of the uncontrolled systems, only that of their air: the reheat of `HVAC_MZW_system` was missing from them, and from the `unmet_sensible_heat` of a `Load_space`. Only these variables change: the balance of the zone already included that heat.

### 0.11.0 (November 26, 2026)

Domestic hot water and solar thermal on the water plants, energy and comfort indicators, verification of the Spanish CTE DB-HE (HE0 and HE4), and help in the app. **One variable of the water plants and circuits has a new name**: see [Upgrading from 0.10](#upgrading-from-010).

#### New

- **Domestic hot water**: `DHW_demand`, the hot water used (l/h) and its temperature as expressions, the mains temperature by month and the distribution losses, hanging from a water plant or circuit as one more coil. The energy of the generators and pumps is split between the services HEATING and DHW by the heat that goes to each one. A preheating by another system (`preheat_system`), e.g. a central solar plant with a boiler in each flat.
- **`Water_tank`**: storage tanks (DHW tanks, electric water heaters, buffer tanks) as the water of a plant or of a DHW charging circuit, with losses, a thermostat with dead band and stratification (`number_of_nodes`).
- **`Solar_collector`**: solar thermal collectors (EN ISO 9806) as generators of a plant with a tank; new carrier SOLAR_THERMAL, renewable.
- **Generators in series** (`connection` "SERIES" of `HVAC_water_generator`): at the outlet of a plant with a tank they heat the water that leaves to the loads up to the setpoint, e.g. an instantaneous boiler after a solar tank, in one plant.
- **DHW priority** of a water plant (`dhw_priority`): the DHW loads take the heat of the generators first, and the heating gets the rest.
- **Variable water flow** in plants and circuits (`flow_control`, `minimum_flow`), with staged secondary pumps; an instantaneous boiler sees only the water drawn.
- **`Energy_indicators`** (final and primary energy and CO₂ by carrier and service, factors of the RITE), **`Comfort_indicators`** (hours outside the setpoints) and **`CTE_compliance`** (CTE DB-HE, HE0 and HE4), with their reports in notebooks and in the app; helpers of the DB-HE in `opensimula.cte` (hourly DHW profile, reference DHW demand and mains water temperatures of Anejos D, F and G).
- **Help in the app**: every parameter in the editor and every variable in the results viewer shows its description as a tooltip, and a "?" opens the documentation at it.
- `File_data`: `file_step` "ANNUAL", the rows of a year from 1 January read by the date of each time step, whatever the start of the simulation; "SIMULATION" warns when a file of a year is read by a simulation that does not start on 1 January. The characters that cannot be in the name of a variable become "_", so the CSV of the results viewer can be read and used in `input_variables`.
- Gallery: examples 10 (energy and comfort) and 11 (domestic hot water and solar).

#### Fixes that change results

- `HVAC_SZW_system` and `HVAC_MZW_system`: the cooling coils fed by a water system gave the plant only their sensible heat; now also the latent heat of the condensed water (fan coil test: cooling generation +11.8 %; examples 07 and 09: electricity of the chiller +3.6 % and +3.8 %).
- `HVAC_water_system`: in a time step that does not converge (it ends at `n_max_iteration`, e.g. a plant short of capacity whose loads come and go with its temperature), the plant stored the relaxed estimate of its temperature, which did not satisfy its energy balance; now the temperature of the balance of the last iteration. Time steps that converge do not change.
- The ASHRAE 140 validation results do not change.

#### Upgrading from 0.10

1. `HVAC_water_system` and `HVAC_water_circuit`: the variable `Q_coils` is now **`Q_loads`** (the load of the coils, the circuits and the DHW demands), split into the new **`Q_heating_coils`**, **`Q_cooling_coils`** and `Q_dhw`. Expressions and scripts that read `Q_coils` must use `Q_loads`.
2. The examples copied with `opensimula examples` from 0.10 are not overwritten: copy them again to a new folder to get examples 10 and 11 (examples 08-10 now read their load file with `file_step` "ANNUAL", with the same results).
3. A project that lists its own `simulation_order` gets the new component types (`DHW_demand`, `Water_tank`, `Solar_collector`, `Energy_indicators`, `Comfort_indicators`, `CTE_compliance`) at the beginning; add them to the list to place them (the indicators, at the end).

### 0.10.0 (November 19, 2026)

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

### Earlier versions

- 0.9.0 (November 13, 2026): Graphical interface. New results viewer, "pro.results()", a widget for Jupyter, VS Code and marimo notebooks: the variables of the components listed on the left and the selected ones plotted one chart per unit, with frequency, aggregation and interval, zoom shared by all the charts, a table and CSV export; its 3D view of the building opens the variables of a surface when it is clicked, draws the plotted surfaces in the colour of their series, and can colour every surface by one of its variables, as a mean, maximum or minimum over the interval or at the time under the cursor of the charts. The project editor, "pro.editor()", has a new graph view of the components, with arrows from each parameter that refers to another component to the component it names, linked with the list, the form and the 3D view. New app, "opensimula gui project.json" (install with pip install "opensimula[gui]"), that puts the editor, a Simulate button with a progress bar and the results viewer together in the browser, with no notebook to write; "simulate()" takes an optional "progress" function, called after each time step, for progress bars like that one. Fixed: the surface temperatures of openings were never stored (their "T_s1" stayed at 0 and "T_s0", "q_cd", "q_cv1" and "q_lwt1" were wrong) and, since 0.8.10, the exterior long wave exchange of windows used that wrong "T_s0"; annual heating of the ASHRAE 140 building cases changes by -0.5 to -1.5 % and cooling by +0.1 %, and 1219 of the 1397 profile points of the building load tests lie inside the reference range (1213 before).
- 0.8.10 (October 29, 2026): The exterior long wave exchange of surfaces and openings with the sky and the ground was linearized with a radiant coefficient at 20 °C, which in winter overestimates the loss to the sky by 25-35 %; the difference with the exact exchange is now added, and the annual heating of the ASHRAE 140 building cases, which was 4-8 % above the mean of the reference programs, is now 2-4 % above (heating loads decrease, typically by 2-4 %). The annual oscillation of the ground in "UNDERGROUND" surfaces now uses the periodic external coefficient of ISO 13370, proportional to the exposed perimeter; the previous one hardly depended on the shape of the slab. New "dry_coil_model" option "ADP" in "DX_unit" (apparatus dew point / bypass factor) to decide when the coil is dry, instead of the crossing of the extrapolated capacity curves. New "outdoor_air_flow" parameter in "HVAC_SZW_system" and constant-volume "HVAC_MZW_system": minimum outdoor air as a volumetric flow at zone conditions, as an alternative to "outdoor_air_fraction"; their return air flow now follows the zone mass balance. With these changes 2,446 of the 2,740 single-valued outputs of the ASHRAE 140 validation lie inside the range of the reference programs (2,379 in 0.8.9).
- 0.8.9 (October 28, 2026): New "API reference" section in the documentation, generated from the docstrings of "Simulation", "Project", "Component", the parameter types, "Variable", "Message" and "Iterative_process". The beam radiation of the weather file is now kept down to 1° of solar altitude (it was moved to the diffuse radiation below 3°), which lost the low-sun beam on vertical surfaces; results with sun change slightly (annual loads of the test cases by -0.9 to +0.5 %) and the ASHRAE 140 weather and building load results improve. The adiabatic envelope of the ASHRAE 140 air-side HVAC cases is now really adiabatic. "Opening.check()" reports an opening whose surface is not EXTERIOR or INTERIOR, which was left out of the simulation without notice, and "del_parameter()" no longer fails. Luis Pérez-Lombard and Ismael R. Maestre join as authors, and the repository includes the paper submitted to the Journal of Open Source Software.
- 0.8.8 (October 22, 2026): OpenSimula is now validated automatically against ANSI/ASHRAE Standard 140-2023: "ASHRAE_140/validation/validate.py" simulates the cases of the six test groups (building loads, furnace, space cooling, ground coupling, air-side HVAC and weather drivers), compares the results with the reference programs and writes the new "Validation" page; the continuous integration checks that results do not change unexpectedly. The ASHRAE 140 cases are now project JSON files. The validation found and fixed several issues, so some results change: the conduction transfer functions of thin, light constructions did not reproduce their U-value in steady state; the "INTERPOLATION" shadow calculation gave unshaded surfaces sunny fractions between 0.84 and 1.11; with sub-hourly time steps the radiation of TMY weather files was spread over neighbouring hours (it now keeps each hour's total); the anisotropic diffuse radiation models (Perez, the default, Hay-Davies and Reindl) gave surfaces facing away from the sun the circumsolar radiation, overestimating the diffuse radiation on north walls by about 20 %; the iterative solution of spaces and water systems could stop before converging, leaving two-zone air systems far from their moisture balance ("convergence_Dw" of Space now defaults to 0.01 g/kg); "HVAC_SZW_system" failed when heating or cooling with "water_source" "UNKNOWN"; spaces served by a VAV system reported the loads of the maximum air flow; and buildings whose surfaces neither absorb nor emit radiation raised a "Singular matrix" error.
- 0.8.7 (September 11, 2026): 3D visualization is now Plotly-only: the "vedo" and VTK dependencies have been removed, together with "get_vedo_mesh()", "get_vedo_meshes()" and the desktop 3D window. "show_3D()", "show_3D_shadows()" and "show_3D_shadows_animation()" no longer take a "jupyter" argument: Plotly draws inline in a notebook and opens a browser tab otherwise. "show_3D()" only shows the view, which it drew twice in a notebook cell; the new "plotly_figure_3D()" returns the figure to compose or save it. The project editor, "pro.editor()", now also loads in VS Code notebooks, whose security policy blocked the validation library it fetched from the internet: that library now ships bundled inside the widget.
- 0.8.6 (September 7, 2026): Fixed the wheel published on PyPI, which installed the package as "OpenSimula" instead of "opensimula", so "import opensimula" failed. Openings flush with the edge of their wall no longer produce false polygon-validity warnings.
- 0.8.5 (September 4, 2026): The view factors between the surfaces of a space are now closed with a symmetric scaling, F_ij = x_i * (A_j/A_total) * x_j, solved with biproportional steps and Newton over log(x). The iteration used until now only converged for a shoebox with equal opposite faces: perturbing the areas of the ASHRAE 140 case 600 by 0.1% was already enough for it to run out of its 500 iterations, and it then returned, without saying so, rows adding up to as little as 0.71 instead of 1, so up to 29% of the long wave radiation a surface emitted reached no other surface and disappeared from the surface energy balance. Every space of the two example buildings converted from HULC failed that way. Closure, each row adding up to 1, and reciprocity, A_i*F_ij = A_j*F_ji, are now both met to machine precision. They cannot both be met when a surface sees no other one, or when the surfaces of a single plane hold more than half of the area of the space: that is now checked before solving, reported as a warning naming the space, and the matrix falls back to closure alone rather than to a silently wrong one. Azimuths are also compared modulo 360 and with a tolerance, so surfaces of the same plane written as 180 and -180 are recognised as coplanar. Results change slightly for every building: the reference values of the tests have been updated, annual loads move by less than 0.3%.
- 0.8.4 (August 23, 2026): Editing a value in the project editor now reaches the project as you type: changing a number is a local assignment, so the component stays the same object and a variable holding it does not go stale. Only renaming, adding or removing a component, or changing its type, still needs the project rebuilt, and those wait for "apply()": the bar says what is missing and the new Apply button asks for it without leaving the editor. A value that does not satisfy the schema is not put in until it is corrected. Fixed three ways a broken reference could bring the kernel down instead of being reported: "get_all_referenced_components()" followed a reference cycle until the stack ran out, "get_building()" chased anything a surface named as its space, and the 3D view raised on a component whose space or surface did not resolve. A reference of the wrong type was already checked; it just never got the chance to say so.
- 0.8.3 (August 23, 2026): The project editor gained a 3D view of the building, under the parameter form, drawn with Plotly and loaded only when it is opened. The bottom bar chooses what to see: the parameters, the view, or both. Picking a space in the view shows only its surfaces, which is the way to see interior partitions, since from outside the exterior walls hide everything behind them; the rest of the building stays as a grey wireframe, so the space keeps its place and its size, and only the surfaces of the chosen space answer the mouse. Selection is linked both ways: a component picked in the list is painted orange in the view, and a surface clicked in the view is selected in the list. New "pro.geometry_dict()" returns the geometry as plain data, one mesh per polygon with the component and the spaces it belongs to, and "show_3D(jupyter=True)" now returns its figure instead of only drawing it.
- 0.8.2 (August 8, 2026): New interactive project editor, "pro.editor()", built on anywidget so the same widget works in Jupyter and in Marimo. It shows the components grouped by type and the parameters of the selected one as a form generated from a JSON Schema derived from the component classes, so every field carries its unit and its limits, options become dropdowns and references to other components become dropdowns of the components of the accepted types. "editor.apply()" loads the edited definition back into the project, rebuilding it from the document and leaving it untouched if the document does not satisfy the schema. New "pro.clear()" removes every component from a project, needed to reload a definition since "read_dict()" and "read_json()" add components rather than replacing them. It replaces the previous Dash table editors, "component_editor()" and "project_editor()", removing the "dash", "dash-ag-grid" and "dash-bootstrap-components" dependencies. Fixed the "Chiller_heat_pump" type name, which prevented that component from being read back from a written project.
- 0.8.1 (August 7, 2026): Faster shadow calculation, an 8-zone building went from 4m55s to 1m16s with shadow_calculation = "INSTANT". Openings flush with the edge of their surface no longer produce invalid polygons, and list parameters no longer share the list given by the caller, which broke "duplicate_component" and a second "simulate()" in the same process.
- 0.8.0 (July 29, 2026): New water side HVAC components: "Pump", "Chiller_heat_pump" and "HVAC_water_system", allowing "HVAC_SZW_system" and "HVAC_MZW_system" coils (including reheat) to be fed from a shared water loop.
- 0.7.1 (April 29, 2026): Removing "triangle" package from dependencies, updating 3D jupyter integrated view with plotly.
- 0.7.0 (April 20, 2026): Renaming DX_unit, Water_coil and Fan components, adding 3D jupyter integrated view with plotly.
- 0.6.1 (February 17, 2026): Building_surface ground-coupled "UNDERGROUND" surfeca passed ASHHRAE 140 Section 8 Tests.
- 0.6.0 (October 30, 2025): HVAC_MZW_system passed ASHHRAE 140 Tests.
- 0.5.2 (October 2, 2025): Changed the name of the pypi package from OpenSimula to opensimula. HVAC_MZW_system under development.
- 0.5.0 (September 30, 2025): Surfaces grouped into Building_surface and Solar_surface. Use of the VEDO library for 3D visualization 
- 0.4.1 (March 13, 2025): Stable versions of HVAC_DX_system and DX_unit. Passed all cases of section 9. 
- 0.4.2 (June 11, 2025): WYEC2 Files added to “File_met”, New “Water_coil” and “Fan” added, HVAC_DX_system and DX_unit adjusted, New HVAC_SZW_system (Single Zone Water System) created.
- 0.3.2 (February 20, 2025): Debugging HVAC_DX_system and DX_unit. Passed cases CE100 to CE340 of section 9. “Space-cooling equipment performance tests” of ASHRAE 140-2023.
- 0.3.1 (January 24, 2025): Implementation HVAC_DX_system and DX_unit
- 0.2.0 (January 1, 2025): First implementation for the building definition components and the HVAC_perfect_system
