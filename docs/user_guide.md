## User Guide

In this guide you will find information on how to use OpenSimula from an environment that can run Python.

The best environment to start using OpenSimula is with [Jupyter notebooks](https://jupyter.org/) or [Google Colab](https://colab.research.google.com/).

### Installation

    pip install opensimula

### Simulation environment

Once we have OpenSimula installed, we can import the package that we will usually name with the alias "osm".

The first step is to create a simulation environment using the `Simulation()` function.

<pre><code class="python">
import OpenSimula as osm

sim = osm.Simulation()
</code></pre>

The simulation object will be used to create and manage the different projects. To create a new project in our simulation environment we will use the `Project(name, sim)` function. the project name is stored in a parameter that can be changed later.

<pre><code class="python">
import OpenSimula as osm

sim = osm.Simulation()
pro = osm.Project("Project 1",sim)
</code></pre>

#### Simulation functions

- **del_project(pro)**: Deletes the "pro" project.
- **project(name)**: Returns the project with name parameter "name". Returns "None" if not found.
- **project_list()**: Returns the list of projects in simulation environment.

### Projects

Projects contain a set of components defining a case that can be temporarily simulated.

#### Project parameters

- **name** [_string_]: Name of the project.
- **description** [_string_, default = "Description of the project"]: Description of the project.
- **time_step** [_int_, unit = "s", default = 3600, min = 1]: Time step in seconds used for simulation. 
- **n_time_steps** [_int_, default = 8760, min = 1]: Number of time steps to simulate. 
- **initial_time** [_string_, default = "01/01/2001 00:00:00"]: Initial simulation time with format "DD/MM/YYYY hh:mm:ss".
- **simulation_order** [_string-list_, default = [
                    "File_data",
                    "File_met",
                    "Day_schedule",
                    "Week_schedule",
                    "Year_schedule",
                    "Material",
                    "Construction"
                ]]: Order used for the types of components in the simulation loops.

Example of project for the simulation of the first week of june with 15 min time step.

<pre><code class="python">
import OpenSimula as osm

sim = osm.Simulation()
pro = osm.Project("Project one", sim)
pro.parameter("description").value = "Project example"
pro.parameter("time_step").value = 60*15
pro.parameter("n_time_steps").value = 24*4*7
pro.parameter("initial_time").value = "01/06/2001 00:00:00"
</code></pre>

Project and component parameters can be changed one by one or in bulk using a dictionary and the `set_parameter(dictonaty)` function.

<pre><code class="python">
import OpenSimula as osm

sim = osm.Simulation()
pro = osm.Project("Project one",sim)
param = {
    "description": "Project example",
    "time_step": 60*15,
    "n_time_steps": 24*4*7,
    "initial_time": "01/06/2001 00:00:00"
}
pro.set_parameters(param)
</code></pre>

#### Project functions

- **simulation ()**: Returns de simulation enviroment.
- **set_parameters (dict)**: Change project parameters using python dictonary.
- **del_component (comp)**: Deletes the "comp" component.
- **component (name)**: Returns the component with name parameter "name". Returns "None" if not found.
- **component_list ()**: Returns the list of components of the project.
- **read_dic (dict)**: Read python dictonary "dict" with the parameters of the project and a list of component to create. See [Getting started](getting_started.md) for definition dictonary example. After reading the dictonary check() function is executed.
- **read_json (file)**: Read json file to define the project. Json file must have the format used for dictionaries in the read_dic function. After reading the file check() function is executed.
- **component_dataframe ()**: Returns pandas DataFrame with the components of the project.
- **check ()**: Returns the list of errors after checking all the components. All the errors returned are also printed.
- **simulate ()**: Perform the time simulation of the project, calculating all the varibles of the components
- **dates_array ()**: Returns numpy array with the date of each simulation instant.

## Components

Components are objects included in projects that contain parameters and variables. [Component list](component_list.md) describe the different types of Components in OpenSimula.

As an example, we will see how to create three different types of components and how to manage them in our project. this code is a continuation of the definition of the previous project.

<pre><code class="python">
...

working_day = osm.components.Day_schedule("working_day",pro)
param = {
    "time_steps": [8*3600, 5*3600, 2*3600, 4*3600],
    "values": [0, 100, 0, 80, 0]
}
working_day.set_parameters(param)

holiday_day = osm.components.Day_schedule("holiday_day",pro)
param = {
    "time_steps": [],
    "values": [0]
}
holiday_day.set_parameters(param)

week = osm.components.Week_schedule("week",pro)
param = {
    "days_schedules": ["working_day","working_day","working_day","working_day","working_day","holiday_day","holiday_day"]
}
week.set_parameters(param)

year = osm.components.Year_schedule("year",pro)
param = {
    "periods": [],
    "weeks_schedules": ["week"]
}
year.set_parameters(param)
</code></pre>

To create the components we use the objects included in the OpenSimula.components package. For example, to create a Day_schedule we will use `osm.components.Day_schedule("name", pro)`. Where the first argument is the name of the component and the second the project where we want to create it.

After creating the components we can modify any of their parameters.

After defining a project with its components, changing the parameters one by one or using a dictionary to define it, we can check if there is any error using the `check()` function and perform the temporary simulation with the `simulate()` function.

<pre><code class="python">
...

pro.check()
pro.simulate()
</code></pre>

Python shell output:

<pre><code class="shell">
Checking project: Project one
ok
Simulating Project one: 10% 20% 30% 40% 50% 60% 70% 80% 90% 100%  End
</code></pre>

The list of parameters of a project can be obtained in pandas DataFrame format using the project functions `parameter_dataframe()`. For the components we can get parameters and variables dataframes with  `parameter_dataframe()` and `variable_dataframe()`.

To obtain the list of components in a project with the parameters as columns use the function `component_dataframe(type="all")`. 
In the "type" argument of the function we can indicate the type of components we want to list (for example: "Day_schedule"), or indicate "all" (this is the default value), which will show all components including only the three parameters common to all components: "name", "type" and "description". 

With Jupyter notebooks or Google Collab, writing the python variable of a project the parameter and component dataframe will be shown, and writing one component python variable parameter and variable dataframe will be shown. Next example shows the parameter and component dataframes of our project:

<pre><code class="python">
...

pro
</code></pre>
Jupyter shell:

![Project in jupyter](img/project_in_jupyter.png)

### Parameters

**Parameters** are used to define the characteristics that make up the projects and components. 

![Paremeters](img/parameters.png)


The parameters will be defined as Python dictionary keys (or json format files), that is the format we will use in the examples shown in the documentation. Parameters can be of different types depending on the type of information they contain:

- Parameter_string: String of characters, e.g.: `"name": "Project 1"`.
- Parameter_boolean: True or False value, e.g.: `"simplified_definition": False`.
- Parameter_int: Integer value, e.g.: `"time_step": 3600`.
- Parameter_float: Floating point value, e.g.: `"conducticity": 1.8`.
- Parameter_options: character string included in a closed option list, e.g.: `"file_type": "EXCEL"`.
- Parameter_component: Reference to another component, e.g.: `"meteo_file": "Sevilla"`.
- Parameter_variable: This parameter is used to create a variable in the component by copying it from another component. A new name is defined and the unit will be taken from the original variable. e.g.: `"aux_variable": "t_1 = meteo.temperature"`, a variable called "t_1" will be created which is a copy of the variable "temperature" of the component "meteo".  
- Parameter_math_exp: parameter defining a mathematical expression. Each of the components knows how to use that mathematical expression within its simulation process. e.g.: `"people_density": "0.1 * f"`, this parameter states that the people density shall be calculated by multiplying by 0.1 a variable called "f" that the component must include.

All of the above types can also be defined as parameter lists, giving rise to the following types:

- Parameter_string_list: List of String of characters, e.g.: ` "authors": ["Juan F.", "Luis", "Ismael"]`.
- Parameter_boolean_list: List of True or False values, e.g.: `"operated": [True, True, False]`.
- Parameter_int_list: List of integer values, e.g.: `"people": [24, 12, 18]`.
- Parameter_float_list: List of floating point values, e.g.: `"solar_absortivity": [0.8, 0.75]`.
- Parameter_options_list: List of character strings included in a closed option list, e.g.: `"day_types": ["MONDAY", "TUESDAY"]`.
- Parameter_component_list: List of references to another components, e.g.: `"materials": ["Cement mortar", "Hollow brick"]`.
- Parameter_variable_list: List of parameters used to copy a list of variables. e.g.: `"aux_variables": ["t_1 = meteo.temperature","hr = meteo.relative_humidity"]`.
- Parameter_math_exp_list: List of mathematical expressions. e.g.: `"curves": ["0.3 * t + 20","0.04 * t^2 - 0.2 * t + 3 "]`.


The Parameter_component, Parameter_variable, Parameter_component_list and Parameter_variable_list can refer to a component of the same project, in that case it is only necessary to put the name of the component, or a component of another project. In this last case we must write "project_name->component_name". e.g. `"meteo_file": "Project 1->Sevilla"`.










