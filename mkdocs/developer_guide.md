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
