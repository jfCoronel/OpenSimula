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
| `HVAC_water_generator` | ELECTRICITY | HEATING or COOLING (equipment), WATER_TRANSPORT (its pump); the heat its plant gives to DHW demands as DHW |
| | fuel of the `Boiler` | HEATING |
| | AMBIENT | HEATING (heat pumps): heat given minus electricity |
| | SOLAR_THERMAL | HEATING (solar collectors): heat given; DHW its share |
| `HVAC_water_system` | ELECTRICITY | WATER_TRANSPORT (its secondary pumps; its generators report their own energy) |
| `HVAC_water_circuit` | ELECTRICITY | WATER_TRANSPORT (its pumps) |
| `Space` | ELECTRICITY | LIGHTING; EQUIPMENT (other gains, carrier given by `equipment_carrier`) |

AMBIENT is the energy heat pumps take from the environment while heating (none in cooling), and SOLAR_THERMAL the heat of solar collectors: renewable energy produced on site, renewable primary energy, not in the totals of final energy. THERMAL is heat with no equipment behind it: it is not final energy until `report()` is given a reference generator.

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

Factors per kWh of final energy (fuels on the lower heating value; BIOMASS is densified biomass, pellets; AMBIENT and SOLAR_THERMAL: 1 / 0 / 0, renewable produced on site as the DB-HE considers the ambient energy of heat pumps; the documento reconocido of the RITE gives no factors for them):

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
- **heating**, **cooling**, **dhw**, **water_transport**, **air_transport**, **lighting**, **equipment**, **heating_without_equipment**, **cooling_without_equipment** and one per extra service, in lower case (W): Final energy of each service (without AMBIENT; THERMAL for the services without equipment).
- **primary_ren**, **primary_nren**, **primary_total** (W): Primary energy.
- **CO2** (kg/h): CO₂ emissions.

#### Functions

- **report(water_transport="SEPARATE", air_transport="SEPARATE", reference_heating=None, reference_cooling=None)**: Tables of the simulation, an `Energy_report` that a notebook shows as HTML (`to_html()` gives it): `annual` (final energy by service and carrier, kWh), `monthly_carriers` and `monthly_services` (by month), `indicators` and `indicators_per_area` (final, primary and CO₂ by service) and `summary` (a dict with the totals and the hypotheses).
    - `water_transport`, `air_transport`: "SEPARATE", pumps and fans as their own services, or "BY_MODE", the energy of each hour assigned to HEATING, COOLING or DHW by the mode of the system that moves the water or air (what runs with none of them stays as transport).
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
- **building_outside** (flag): 1 when any zone is outside the setpoints.

#### Functions

- **report()**: Tables of the simulation, a `Comfort_report` that a notebook shows as HTML: `zones` (by zone, TOTAL and BUILDING: hours counted, above, below and outside, their percentage, degree-hours above and below, maximum and minimum temperature while counted), `monthly` (hours outside by month and zone, TOTAL and BUILDING) and `summary`. TOTAL adds the zone-hours of every zone; BUILDING counts each hour once, when any zone is counted or outside: it measures time, not zone-hours, as the hours outside setpoint of the CTE DB-HE (several zones outside at the same time count once).

### CTE_compliance

Verification of the Spanish CTE DB-HE 2019, sections HE0 (limitation of the energy use) and HE4 (renewable contribution to the DHW demand), on top of an `Energy_indicators` and a `Comfort_indicators`. It is not a recognised procedure (HULC remains the official tool); it applies to the hourly results of OpenSimula the rules of the DB-HE:

- Only the EPB services count: heating, cooling, DHW, ventilation, humidity control and, in uses other than residencial privado, lighting. Equipment is left out (`non_epb_services`).
- Pumps and fans are assigned to heating or cooling by the mode of each hour; fans running with no load are the ventilation (`report(water_transport="BY_MODE", air_transport="BY_MODE")` of the energy component).
- In residencial privado, the heat with no system behind it (ideal systems, coils with no water system) is given by the reference systems of table 4.5-HE0: natural gas, 0.92 on the higher heating value (× `hhv_lhv_ratio` on the lower heating value, the one of the final energy), and electricity, EER 2.60.
- C_ep,nren and C_ep,tot per m² of the reference area of the energy component are compared with the limits of tables 3.1 and 3.2-HE0 for the winter climate zone, the use and the intervention; for other uses the limits depend on the carga interna media C_FI. The extrapeninsular multipliers apply when the energy component uses the factors of Baleares, Canarias or Ceuta y Melilla.
- The hours outside setpoint of the building (each hour once, when any zone is more than 1 K outside its setpoints) must not exceed 4 % of the occupation time, the hours of the `period` of the comfort component (all hours for residencial privado; the occupied hours for other uses).
- **HE4**, if the building has DHW: the renewable part of the DHW demand must be at least 70 % (60 % below 5000 l/day); it applies above 100 l/day at 60 °C (Anejo F). The demand is the heat the water generators give to DHW, which includes the losses of distribution, storage and recirculation, plus the demand not met. Its renewable part, following the procedure of HE4 3.1 (only on site or nearby): the heat of the solar collectors; the ambient energy of electric heat pumps, Q·(1 − 1/SCOP_dhw), if their seasonal SCOP_dhw over the simulated period is at least 2.5; the heat of biomass boilers times fp,ren / fp,tot. Electricity from the grid and fossil fuels give none. Thermally driven heat pumps, district heating, photovoltaics and waste heat are not modelled.

#### Parameters

- **energy_indicators** [_component_, default = "not_defined"]: The `Energy_indicators` of the building or part of the building checked (one `CTE_compliance` per use: no compensation between uses).
- **comfort_indicators** [_component_, default = "not_defined"]: The `Comfort_indicators` for the hours outside setpoint (its `tolerance` should be 1 K). If not defined, the hours are not checked.
- **climate_zone** [_string_, default = "B4"]: Climate zone of the DB-HE (Anejo B): winter zone α, A, B, C, D or E followed by the summer zone 1 to 4 ("alpha3" also valid).
- **building_use** [_option_, default = "RESIDENTIAL_PRIVATE", options = ["RESIDENTIAL_PRIVATE", "OTHER"]]: Use of the building.
- **intervention** [_option_, default = "NEW_OR_EXTENSION", options = ["NEW_OR_EXTENSION", "CHANGE_OF_USE_OR_REFORM"]]: New building or extension, or change of use and reform (residential limits only).
- **internal_load** [_float_, unit = "W/m²", default = 0, min = 0]: Carga interna media C_FI for other uses. 0: the mean over the simulated period of the sensible gains of occupancy, lighting and equipment of the `Space` zones of the energy component; required when the zones include `Load_space`.
- **non_epb_services** [_string_list_, default = ["EQUIPMENT"]]: Services of the energy component that are not EPB (e.g. lifts given as extra uses).
- **hhv_lhv_ratio** [_float_, unit = "frac", default = 1.11, min = 1]: Ratio of the higher to the lower heating value of natural gas, for the reference boiler.
- **dhw_daily_demand** [_float_, unit = "l/day", default = 0, min = 0]: DHW demand of Anejo F (at 60 °C) that decides whether HE4 applies and its minimum share (e.g. from `cte.dhw_reference_demand()`). 0: the mean over the simulated period of the `DHW_demand` components, their volume taken to 60 °C with the mains temperature (Anejo F, 3).

#### Functions

- **report()**: A `CTE_report` that a notebook shows as HTML: `checks` (C_ep,nren, C_ep,tot, hours outside setpoint and, with DHW, the renewable share of HE4: value, limit, unit, complies), `services` (the EPB services counted: final energy, C_ep,nren, C_ep,tot and CO₂ per m²), `tables` (the DHW renewable contribution per generator), `summary` (zone, use, intervention, area, C_FI, values and limits, DHW demand and renewable share, `complies`) and `notes`.
- **he4()**: The HE4 figures as a dict: `demand`, `renewable` (kWh), `share`, `daily_demand` (l/day), `minimum` (0 if HE4 does not apply) and `generators` (table).

**Helpers of the DB-HE** (module `opensimula.cte`):

- `dhw_reference_demand(bedrooms=None, dwellings=None, centralised=False, persons=None, use=None)`: reference DHW demand of Anejo F in l/day at 60 °C (without losses): 28 l/day·person with the minimum occupation of table a by bedrooms (a number, or a list with the bedrooms of each dwelling) and the centralisation factor of table b; for other uses the l/day·person of table c (`use`, e.g. "Oficinas", "Hotel ***") times `persons`.
- `mains_temperatures(capital, altitude=None)`: the 12 monthly mains water temperatures of Anejo G for a province capital, corrected for the altitude of another place; for the `mains_monthly_temperatures` of a `DHW_demand`.
- `he4_minimum_share(daily_demand)`: 0.70, 0.60 below 5000 l/day, 0 at 100 l/day or less.
- `dhw_profile_schedules(name)`: the hourly DHW profile of dwellings (Anejo D) as schedules.

**Example:**
<pre><code class="python">
...

pro.new_component("Energy_indicators", "energy")
pro.new_component("Comfort_indicators", "comfort").set_parameters({"tolerance": 1.0})
pro.new_component("CTE_compliance", "cte").set_parameters({
    "energy_indicators": "energy",
    "comfort_indicators": "comfort",
    "climate_zone": "B4",
    "building_use": "RESIDENTIAL_PRIVATE",
})
pro.simulate()
pro.component("cte").report()
</code></pre>
