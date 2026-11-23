## Component List for various utilities

### Calculator

Component to perform calculations with the variables of other components.

#### Parameters

- **input_variables** [_variable_list_, default = []]: List of variables from other components used in this component. They can appear in the expressions of the “output_expressions” parameter.
- **output_variables** [_string_list_, default = []]: List of output variable names.
- **output_units** [_string_list_, default = []]: List of output variable units.
- **output_expressions** [_math_exp_list_, default = []]: List of output variable mathematical expressions.

#### Variables
The component will generate a variable for each of the input variables specified in "input_variables" and "output_variables" using the mathematical expressions for the calculation in each time step. The expressions are evaluated at the start of each time step, so that other components can use the outputs during it, and again at its end, with the final values of the time step: the outputs stored can use the variables that other components compute during the time step, such as the loads of a space or the power of a system.

**Example:**
<pre><code class="python">
...

calc = osm.new_component("Calculator","unit_change")
param = {
    "input_variables": ["T = met.temperature", "w = met.abs_humidity"],
    "output_variables": ["T_F","W_kg"],
    "output_units": ["ºF","kg/kg a.s."],
    "output_expressions": ["T * 9/5 + 32", "w / 1000"]
}
calc.set_parameters(param)
</code></pre>

Four variables will be created with names: T, w, T_F and W_kg, two from input_variables and two from output_variables.

### Energy_indicators

Energy use of a project: final energy by carrier and service, primary energy (renewable, non-renewable and total) and CO₂. It reads what every consumer reports at the end of the simulation and does not change it. See the [user guide](user_guide.md#energy-and-comfort-indicators) and [example 10](examples.md#10-energy-and-comfort).

What each component reports (power at each time step):

| Component | Carrier | Service |
|---|---|---|
| `HVAC_DX_system` | ELECTRICITY | HEATING, COOLING (compressor), AIR_TRANSPORT (indoor fan) |
| | AMBIENT | HEATING: heat given minus compressor electricity |
| `HVAC_SZW_system`, `HVAC_MZW_system` | ELECTRICITY | AIR_TRANSPORT (supply and return fans) |
| | THERMAL | HEATING_WITHOUT_EQUIPMENT, COOLING_WITHOUT_EQUIPMENT: heat of the coils with `water_source` (or `reheat_water_source`) "UNKNOWN" |
| `HVAC_perfect_system` | THERMAL | HEATING_WITHOUT_EQUIPMENT, COOLING_WITHOUT_EQUIPMENT (sensible and latent) |
| `HVAC_water_generator` | ELECTRICITY | HEATING or COOLING (equipment), WATER_TRANSPORT (its pump) |
| | fuel of the `Boiler` | HEATING |
| | AMBIENT | HEATING (heat pumps): heat given minus electricity |
| `HVAC_water_system` | ELECTRICITY | WATER_TRANSPORT (its secondary pumps; its generators report their own energy) |
| `HVAC_water_circuit` | ELECTRICITY | WATER_TRANSPORT (its pumps) |
| `Space` | ELECTRICITY | LIGHTING; EQUIPMENT (other gains, carrier given by `equipment_carrier`) |

AMBIENT is the energy heat pumps take from the environment while heating (none in cooling): renewable primary energy, not final energy. THERMAL is heat with no equipment behind it: it is not final energy until `report()` is given a reference generator.

#### Parameters

- **components** [_component_list_, default = []]: Systems to count (`HVAC_DX_system`, `HVAC_SZW_system`, `HVAC_MZW_system`, `HVAC_perfect_system`, `HVAC_water_generator`, `HVAC_water_system`, `HVAC_water_circuit`). Empty: all those of the project.
- **zones** [_component_list_, default = []]: `Space` or `Load_space` whose floor area is the reference area and whose lighting and equipment are counted. Empty: all those of the project.
- **reference_area** [_float_, unit = "m²", default = 0, min = 0]: Area of the indicators per m². 0: the sum of the `floor_area` of the zones.
- **equipment_carrier** [_option_, default = "ELECTRICITY", options = ["ELECTRICITY", "NATURAL_GAS", "LPG", "DIESEL", "BIOMASS"]]: Carrier of the equipment of the spaces (their other gains).
- **conversion_factors** [_option_, default = "PENINSULA", options = ["PENINSULA", "BALEARES", "CANARIAS", "CEUTA_MELILLA", "NATIONAL", "EXTRAPENINSULAR"]]: Region of the factors of the documento reconocido del RITE "Factores de emisión de CO₂ y coeficientes de paso a energía primaria" (2016), table below. NATIONAL and EXTRAPENINSULAR are for statistics only.
- **custom_carriers** [_option_list_, default = []]: Carriers whose factors are given by the next three parameters, replacing those of the region.
- **custom_fp_ren** [_float_list_, unit = "frac", default = []]: Renewable primary energy per kWh of final energy of each custom carrier.
- **custom_fp_nren** [_float_list_, unit = "frac", default = []]: Non-renewable primary energy per kWh of final energy of each custom carrier.
- **custom_CO2** [_float_list_, unit = "kg/kWh", default = []]: CO₂ per kWh of final energy of each custom carrier.
- **input_variables** [_variable_list_, default = []]: Variables of other components used in the expressions of the extra uses.
- **extra_services** [_string_list_, default = []]: Service of each extra use, e.g. "DHW".
- **extra_carriers** [_option_list_, default = []]: Carrier of each extra use.
- **extra_expressions** [_math_exp_list_, unit = "W", default = []]: Power of each extra use, evaluated at the end of each time step.

Factors per kWh of final energy (fuels on the lower heating value; BIOMASS is densified biomass, pellets; AMBIENT: 1 / 0 / 0):

| Carrier | fp,ren | fp,nren | kg CO₂/kWh |
|---|---|---|---|
| ELECTRICITY, PENINSULA | 0.414 | 1.954 | 0.331 |
| ELECTRICITY, BALEARES | 0.082 | 2.968 | 0.932 |
| ELECTRICITY, CANARIAS | 0.070 | 2.924 | 0.776 |
| ELECTRICITY, CEUTA_MELILLA | 0.072 | 2.718 | 0.721 |
| NATURAL_GAS | 0.005 | 1.190 | 0.252 |
| LPG | 0.003 | 1.201 | 0.254 |
| DIESEL | 0.003 | 1.179 | 0.311 |
| BIOMASS | 1.028 | 0.085 | 0.018 |

#### Variables

- **electricity**, **natural_gas**, **lpg**, **diesel**, **biomass**, **ambient**, **thermal** (W): Power of each carrier.
- **heating**, **cooling**, **water_transport**, **air_transport**, **lighting**, **equipment**, **heating_without_equipment**, **cooling_without_equipment** and one per extra service, in lower case (W): Final energy of each service (without AMBIENT; THERMAL for the services without equipment).
- **primary_ren**, **primary_nren**, **primary_total** (W): Primary energy.
- **CO2** (kg/h): CO₂ emissions.

#### Functions

- **report(water_transport="SEPARATE", air_transport="SEPARATE", reference_heating=None, reference_cooling=None)**: Tables of the simulation, an `Energy_report` that a notebook shows as HTML (`to_html()` gives it): `annual` (final energy by service and carrier, kWh), `monthly_carriers` and `monthly_services` (by month), `indicators` and `indicators_per_area` (final, primary and CO₂ by service) and `summary` (a dict with the totals and the hypotheses).
    - `water_transport`, `air_transport`: "SEPARATE", pumps and fans as their own services, or "BY_MODE", the energy of each hour assigned to HEATING or COOLING by the mode of the system that moves the water or air (what runs with neither stays as transport).
    - `reference_heating`, `reference_cooling`: (carrier, efficiency) of the generator that gives the heat without equipment, e.g. `("NATURAL_GAS", 0.92)` and `("ELECTRICITY", 2.6)`. An ELECTRICITY heating one with efficiency above 1 is a heat pump: the heat minus its electricity is AMBIENT.
- **get_uses()**: Every energy use counted, a list of `Energy_use(carrier, service, values, mode)`.

**Example:**
<pre><code class="python">
...

energy = pro.new_component("Energy_indicators", "energy")
energy.set_parameters({
    "conversion_factors": "PENINSULA",
    "input_variables": ["f = office_hours.values"],
    "extra_services": ["DHW"],
    "extra_carriers": ["ELECTRICITY"],
    "extra_expressions": ["400 * f"],
})
pro.simulate()
energy.report(water_transport="BY_MODE")
</code></pre>

### Comfort_indicators

Hours each zone is outside the setpoints of the system that controls it. For every zone it takes the heating and cooling setpoints of its system (`HVAC_DX_system`, `HVAC_SZW_system`, `HVAC_perfect_system`; `HVAC_MZW_system` gives each zone its `spaces_setpoint`) and counts the hours its air temperature is above the cooling setpoint or below the heating setpoint by more than a tolerance.

#### Parameters

- **zones** [_component_list_, default = []]: `Space` or `Load_space` to look at. Empty: all those of the project.
- **tolerance** [_float_, unit = "K", default = 0.5, min = 0]: Temperature beyond the setpoint that counts as outside. Keep it above the convergence of the zones (0.01 K): with 0 the hours held at the setpoint would count.
- **only_system_on** [_boolean_, default = True]: Count only the hours the system of the zone is on. A zone with no system has then no hours counted; with False its hours are counted, but with no setpoints it is never outside.
- **input_variables** [_variable_list_, default = []]: Variables of other components used in `period`.
- **period** [_math_exp_, default = "1"]: Hours counted only while it is not 0, e.g. the occupied hours.

#### Variables

- **outside_&lt;zone&gt;** (flag): For each zone, 1 above the cooling setpoint, -1 below the heating setpoint, 0 inside or not counted.
- **zones_outside** (-): Number of zones outside the setpoints.

#### Functions

- **report()**: Tables of the simulation, a `Comfort_report` that a notebook shows as HTML: `zones` (by zone and TOTAL: hours counted, above, below and outside, their percentage, degree-hours above and below, maximum and minimum temperature while counted), `monthly` (hours outside by month and zone) and `summary`.
