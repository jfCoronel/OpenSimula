### Getting Started

`OpenSimula` is a component-based time simulation environment in Python. 

The general object structure provided by OpenSimula is composed of three main elements:

- Simulation: The global environment for simulation.
- Project: A set of components that define a problem that can be temporarily simulated.
- Component: These are the base elements on which the simulation is performed. The types of components currently available can be consulted in section [Component list](component_list.md).

![Global structure](img/global_structure.png)

#### Parameters

**Parameters** are used to define the characteristics that make up the projects and components. 

![Paremeters](img/parameters.png)


The parameters will be defined as Python dictionary keys (or json format files), that is the format we will use in the examples shown in the documentation. Parameters can be of different types depending on the type of information they contain:

- Parameter_string: String of characters, e.g.: `"name": "Project 1"`.
- Parameter_string_list: List of String of characters, e.g.: ` "authors": ["Juan F.", "Luis", "Ismael"]`.
- Parameter_boolean: True or False value, e.g.: `"simplified_definition": False`.
- Parameter_boolean_list: List of True or False values, e.g.: `"operated": [True, True, False]`.
- Parameter_int: Integer value, e.g.: `"time_step": 3600`.
- Parameter_int_list: List of integer values, e.g.: `"people": [24, 12, 18]`.
- Parameter_float: Floating point value, e.g.: `"conducticity": 1.8`.
- Parameter_float_list: List of floating point values, e.g.: `"solar_absortivity": [0.8, 0.75]`.
- Parameter_options: character string included in a closed option list, e.g.: `"file_type": "EXCEL"`.
- Parameter_options_list: List of character strings included in a closed option list, e.g.: `"day_types": ["MONDAY", "TUESDAY"]`.
- Parameter_component: Reference to another component, e.g.: `"meteo_file": "Sevilla"`.
- Parameter_component_list: List of references to another components, e.g.: `"materials": ["Cement mortar", "Hollow brick"]`.

The Parameter_component and Parameter_component_list can refer to a component of the project itself, in that case it is only necessary to put the name of the component, or a component of another project. In this last case we must write "project_name->component_name". e.g. `"meteo_file": "Project 1->Sevilla"`.


#### Variables

**Variables** are elements included in the components to store the temporal 
information generated during the simulation.

![Variables](img/variables.png)






