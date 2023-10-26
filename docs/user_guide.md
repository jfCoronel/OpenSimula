## User Guide

In this guide you will find information on how to use OpenSimula from an environment that can run Python.

The best environment to start using OpenSimula is with [Jupyter notebooks](https://jupyter.org/) or [Google Colab](https://colab.research.google.com/).

### Instalation

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

Projects are objects that contain a set of components that define a case that can be temporarily simulated.

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

#### Project functions

- **simulation()**: Returns de simulation enviroment.
- **del_component(comp)**: Deletes the "comp" component.
- **component(name)**: Returns the component with name parameter "name". Returns "None" if not found.
- **component_list()**: Returns the list of components of the project.
- **read_dic(dict)**: Read python dictonary "dict" with the parameters of the project and a list of component to create. See [Getting started](getting_started.md) for definition dictonary example. After reading the dictonary check() function is executed.
- **read_json(file)**: Read json file to define the project. Json file must have the format used for dictionaries in the read_dic function. After reading the file check() function is executed.
- **component_dataframe()**: Returns pandas DataFrame with the components of the project.
- **check()**: Returns the list of errors after checking all the components. All the errors returned are also printed.
- **simulate()**: Perform the time simulation of the project, calculating all the varibles of the components
- **dates_array()**: Returns numpy array with the date of each simulation instant.

## Components

Components are objects included in projects that contain parameters and variables. [Component list](component_list.md) describe the different types of Components in OpenSimula.

As an example, we will see how to create three different types of components and how to manage them in our project. this code is a continuation of the definition of the previous project.

<pre><code class="python">
...

working_day = osm.components.Day_schedule("working_day",pro)
working_day.parameter("time_steps").value = [8*3600, 5*3600, 2*3600, 4*3600]
working_day.parameter("values").value = [0, 100, 0, 80, 0]

holiday_day = osm.components.Day_schedule("holiday_day",pro)
holiday_day.parameter("time_steps").value = []
holiday_day.parameter("values").value = [0]

week = osm.components.Week_schedule("week",pro)
week.parameter("days_schedules").value = ["working_day","working_day","working_day","working_day","working_day","holiday_day","holiday_day"]

year = osm.components.Year_schedule("year",pro)
year.parameter("periods").value = []
year.parameter("weeks_schedules").value = ["week"]
</code></pre>

To create the components we use the objects included in the OpenSimula.components package. For example, to create a Day_schedule we will use `osm.components.Day_schedule("name", pro)`. Where the first argument is the name of the component and the second the project where we want to create it.

After creating the components we can modify any of their parameters.

## Simulate, parameters and variables

After defining a project with its components, changing the parameters one by one or using a dictionary to define it, we can check if there is any error using the `check()` function and perform the temporary simulation with the `simulate()` function.

<pre><code class="python">
...

pro.check()
pro.simulate()
</code></pre>

Python shell:

<pre><code class="shell">
Checking project: Project one
ok
Simulating Project one: 10% 20% 30% 40% 50% 60% 70% 80% 90% 100%  End
</code></pre>

The list of parameters and components of a project can be obtained in pandas DataFrame format using the project functions `parameter_dataframe()` and `component_dataframe()`. For the components we can get parameters and variables list with  `parameter_dataframe()` and `variable_dataframe()`.

With Jupyter notebooks or Google Collab, projects show the parameter and component dataframe, and components show parameter and variable dataframe, as shown in the next example:

<pre><code class="python">
...

pro
</code></pre>
Jupyter shell:

![Project in jupyter](img/project_in_jupyter.png)








