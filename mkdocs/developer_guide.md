## Developer Guide

Under development ...

The base classes to build new components (`Component`, the parameter types, `Variable`,
`Iterative_process`) are documented in the [API reference](api/index.md).

A new component that uses energy or controls the temperature of zones tells the
indicators components by overriding two methods of `Component` (both return an empty
list by default):

- `get_energy_use()`: a list of `opensimula.energy.Energy_use(carrier, service, values,
  mode)`, the power (W, positive) at each time step, read from its variables after the
  simulation. `mode` (1 heating, -1 cooling, 0 neither) is given for the transport
  services, so that the report can assign them. Report each power only once.
- `get_zone_setpoints()`: a list of `opensimula.comfort.Zone_control(zone,
  heating_setpoint, cooling_setpoint, on)`, for `Comfort_indicators`.

A system that gives heat to a zone by radiation (radiators, radiant panels) uses two
methods of the zone (`Space` or `Load_space`): `radiant_to_air(distribution)`, the part of
1 W of radiant heat that reaches the air in the same time step (computed by the building
for a space: the radiation distributed over its surfaces, by area or among floor, ceiling
and walls, absorbed with the long-wave radiosity and given back to the air; the thermal
mass node of a `Load_space`), and `add_radiant_system(name, Q_radiant, distribution)`,
which puts that heat into the surfaces (or the mass) in each iteration. The system gives
the zone, as an uncontrolled system, its convective heat plus `radiant_to_air()` times
its radiant heat (see `HVAC_radiator_system`).

### Documentation of a component and the help of the app

The parameters and variables of each component are described once, in its section of
the component pages (`mkdocs/component_list_*.md`): a `### <type>` title, then
`#### Parameters` and `#### Variables` with one list item each, in this form:

<pre>
- **volume_flow** [_math_exp_, unit = "l/h", default = "0"]: Hot water used...
- **T_mains** (°C), **T_supply** (°C): Mains water temperature and...
- __Q_sensible__ [W]: Sensible heat supplied by the system...
</pre>

Several names may share an item (`**a** (unit), **b** (unit): ...` or `__a, b__ [unit]:
...`); variables whose name ends in a number or in the name of another component are
documented by their pattern (`T_node_1`, `Q_reheat_i`, `outside_&lt;zone&gt;`).

The app reads the same text: in the editor every parameter has a tooltip with its
description and a "?" that opens the documentation at it, and in the results viewer
every variable. `opensimula/help.py` reads the pages and writes `src/opensimula/help.json`,
shipped with the package; the mkdocs hook `mkdocs_hooks.py` gives each item the anchor
the links point to (`<type>-<parameter>`, `<type>-var-<variable>`). After adding or
changing a parameter or a variable, document it and regenerate the file:

<pre>
uv run python -m opensimula.help mkdocs
</pre>

`test/test_help.py` fails if `help.json` is not up to date with the pages or if a
parameter or variable of a component is not documented.

