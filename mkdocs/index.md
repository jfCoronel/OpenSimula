
![Logo](img/logo_opensimula.png) 

This site contains the documentation for the
___OpenSimula___ project. Github site [![Github logo](img/github_logo.png)](https://github.com/jfCoronel/OpenSimula)

`OpenSimula` is a component-based time simulation environment in Python. 

The main objective is the thermal and energy simulation of different systems and installations, mainly in buildings, although it can be used to simulate any component that presents a temporal variation.

![Building shadows example](img/shadows_example.png)

![Plot variables example](img/plot_example.png)


### Structure

The general object structure provided by OpenSimula is composed of three main elements:

- Simulation: The global environment for simulation.
- Project: A set of components that define a problem that can be temporarily simulated.
- Component: These are the base elements on which the simulation is performed. The types of components currently available can be consulted in section [Component list](component_list.md).

![Global structure](img/global_structure.png)

### Parameters

**Parameters** are used to define the characteristics that make up the projects and components. 

![Paremeters](img/parameters.png)

Parameters can be of different types depending on the type of information they contain (strings, boolean, integer, float, options, ...). A list of all parameter types and their possibilities can be found in the [User guide](user_guide.md#parameters). :


### Variables

**Variables** are elements included in the components to store the temporal 
information generated during the simulation.

![Variables](img/variables.png)

## Documentation

1. [Getting started](getting_started.md)
2. [User guide](user_guide.md)
3. [Component list](component_list.md)
3. [Developer guide](developer_guide.md)

## Release notes

This is the list of changes to OpenSimula between each release. For full details, see the commit logs.

 __Version 0.2__

- 0.2.0 (January 1, 2025): First implementation for the building definition components and the HVAC_perfect_system


_© JFC 2024_
