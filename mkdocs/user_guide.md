## User Guide

In this guide you will find information on how to use OpenSimula from an environment that can run Python.

The best environment to start using OpenSimula is with [Jupyter notebooks](https://jupyter.org/).

### Simulation environment

Once we have OpenSimula installed, we can import the package that we will usually name with the alias "osm".

The first step is to create a simulation environment using the `Simulation()` function.

<pre><code class="python">
import OpenSimula as osm

sim = osm.Simulation()
</code></pre>

The simulation object will be used to create and manage the different projects. To create a new project in our simulation environment we will use the `new_project(name)` function. the project name is stored in a parameter of the project that can be changed later.

<pre><code class="python">
import OpenSimula as osm

sim = osm.Simulation()
pro = sim.new_project("Project 1")
</code></pre>

#### Simulation functions
The following is a list of the most useful functions of the Simulation object:

- **new_project(name)**: Create a new project in our simulation environment, with name parameter "name".
- **del_project(pro)**: Deletes the "pro" project.
- **project(name)**: Returns the project with name parameter "name". Returns "None" if not found.
- **project_list()**: Returns the list of projects in simulation environment.
- **project_dataframe()**: Returns pandas DataFrame with all the projects and its parameters as columns.
- **plot(dates,variables,names=[],axis=[],frequency=None,value="mean")**:  Draw variables graph (using plotly). dates is the array of dates to be used on the x-axis (can be obtained with the dates() function of the projects). Varibles is a list of variables to be plotted, each one in a serie. Names is the list of names for the series (if empty variables names will be used).frequency [__None__, "H", "D", "M", "Y"] is the frequency of the data, that of the simulation (None), hourly ("H"), daily ("D"), monthly ("M") or yearly ("Y") and value [__"mean"__,"max","min","sum"], if we use a frequency other than the simulation frequency (e.g. monthly "M"), the value obtained for each point (month) will be the mean ("mean"), the maximum ("max"), the minimum ("min") or the sum ("sum").
- **project_editor()**: When used in Jupyter, it generates a form with a table that allows you to create new projects, delete existing ones and edit the parameters of each project, as shown in the following image.

![Project editor example](img/project_editor.png)

### Projects

Projects contain a set of components defining a case that can be temporarily simulated.

#### Project parameters

- **name** [_string_]: Name of the project.
- **description** [_string_, default = "Description of the project"]: Description of the project.
- **time_step** [_int_, unit = "s", default = 3600, min = 1]: Time step in seconds used for simulation. 
- **n_time_steps** [_int_, default = 8760, min = 1]: Number of time steps to simulate. 
- **initial_time** [_string_, default = "01/01/2001 00:00:00"]: Initial simulation time with format "DD/MM/YYYY hh:mm:ss".
- **daylight_saving** [_boolean_, default = False]: Taking into account daylight saving time in the simulation. If its value is False, the whole simulation is performed in winter time without daylight saving. If True, the daylight saving time change will be taken into account, mainly in the components that define schedules.
- **daylight_saving_start_time** [_string_, default = "25/03/2001 02:00:00"]: daylight saving start time, with format "DD/MM/YYYY hh:mm:ss". It will only be used if the daylight_saving parameter is set to True.
- **daylight_saving_end_time** [_string_, default = "28/10/2001 02:00:00"]: daylight saving start time, time with format "DD/MM/YYYY hh:mm:ss". It will only be used if the daylight_saving parameter is set to True.
- **n_max_iteration** [_int_, default = 1000, min = 1]: Maximum number of iterations in each time step. If after this number of iterations the instant has not converged, it is passed to the next time instant. 
- **simulation_order** [_string-list_, default = [
                    "Space_type",
                    "Exterior_surface",
                    "Underground_surface",
                    "Interior_surface",
                    "Virtual_surface",
                    "Shadow_surface",
                    "Opening",
                    "Space",
                    "Building"
                ]]: Order used for the types of components in the simulation loops. All components not specified are added at the beginning and those defined in this list are added at the end in the established order.

Example of project for the simulation of the first week of june with 15 min time step.

<pre><code class="python">
import OpenSimula as osm

sim = osm.Simulation()
pro = sim.new_project("Project one")
pro.parameter("description").value = "Project example"
pro.parameter("time_step").value = 60*15
pro.parameter("n_time_steps").value = 24*4*7
pro.parameter("initial_time").value = "01/06/2001 00:00:00"
</code></pre>

Project and component parameters can be changed one by one, in bulk using a dictionary and the `set_parameter(dictonaty)` function, or interactively using the project and component editors.

<pre><code class="python">
import OpenSimula as osm

sim = osm.Simulation()
pro = sim.new_project("Project one")
param = {
    "description": "Project example",
    "time_step": 60*15,
    "n_time_steps": 24*4*7,
    "initial_time": "01/06/2001 00:00:00"
}
pro.set_parameters(param)
</code></pre>

#### Project functions
The following is a list of the most useful functions of the Project object:

- **parameter(name)**: Returns the parameter "name".
- **parameter_dataframe()**: Returns pandas DataFrame with the parameters of the project.
- **parameter_dict()**: Returns a dictonary with all the parameters of the project.
- **set_parameters(dict)**: Change project parameters using python dictonary.
- **new_component(type, name)**: Creates a new component of the type specified in the first argument and with the name of the second argument.
- **del_component(comp)**: Deletes the "comp" component.
- **component(name)**: Returns the component with name parameter "name". Returns "None" if not found.
- **component_list()**: Returns the list of components of the project.
- **component_dataframe()**: Returns pandas DataFrame with the components of the project.
- **read_dict(dict)**: Read python dictonary "dict" with the parameters of the project and a list of component to create. See [Getting started](getting_started.md) for definition dictonary example. After reading the dictonary check() function is executed.
- **read_json(file)**: Read json file to define the project. Json file must have the format used for dictionaries in the read_dic function. After reading the file check() function is executed.
- **write_dict()**: Return python dictonary with the definition of the project. The default values of the parameters are written explicitly. 
- **write_json(file)**: Write json file that define the project. The written json file is exactly the same as the dictionary generated by the "write_dict" function.
- **check()**: Returns the list of errors after checking all the components. All the errors returned are also printed.
- **simulate()**: Perform the time simulation of the project, calculating all the varibles of the components
- **simulation_dataframe()**: Returns pandas DataFrame with information from the latest simulation. For each time step it includes the number of iterations performed and the name of the last component that forced the iteration.
- **dates()**: Returns numpy array with the date of each simulation instant, using winter time without daylight saving.
- **component_editor(type)**: When used in Jupyter, it generates a form with a table that allows you to create new compenents, delete existing ones and edit the parameters of each component. If the type is specified, a table with only the components of that type will be displayed. If no type is included or type = “all” all components will be displayed but only with the common parameters. Following image shows an example of the component editor:

![Compoenent editor example](img/component_editor.png)

the first simulation instant is the initial_time plus 1/2 of the time_step. For example, if initial_time = “01/01/2001 00:00:00” and time_step = 3600, then the first simulation instant is: “01/01/2001 00:30:00”, the second: “01/01/2001 01:30:00”, and so on. 


## Components

Components are objects included in projects that contain parameters and variables. [Component list](component_list.md) describe the different types of Components in OpenSimula.

As an example, we will see how to create three different types of components and how to manage them in our project. this code is a continuation of the definition of the previous project.

<pre><code class="python">
...

working_day = pro.new_component("Day_schedule","working_day")
param = {
    "time_steps": [8*3600, 5*3600, 2*3600, 4*3600],
    "values": [0, 100, 0, 80, 0]
}
working_day.set_parameters(param)

holiday_day = pro.new_component("Day_schedule","holiday_day")
param = {
    "time_steps": [],
    "values": [0]
}
holiday_day.set_parameters(param)

week = pro.new_component("Week_schedule","week")
param = {
    "days_schedules": ["working_day","working_day","working_day","working_day","working_day","holiday_day","holiday_day"]
}
week.set_parameters(param)

year = pro.new_component("Year_schedule","year")
param = {
    "periods": [],
    "weeks_schedules": ["week"]
}
year.set_parameters(param)
</code></pre>

To create the components we use project "new_component" function. For example, to create a Day_schedule we will use `pro.new_component("Day_schedule","name")`. Where the first argument is the type of component and the second the name of the component.

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

To obtain the list of components in a project with the parameters as columns use the function `component_dataframe(comp_type="all")`. 
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
- Parameter_variable: This parameter is used to create a variable in the component by copying it from another component. A new name is defined and the unit will be taken from the original variable. e.g.: `"input_variables": "t_1 = meteo.temperature"`, a variable called "t_1" will be created which is a copy of the variable "temperature" of the component "meteo".  
- Parameter_math_exp: parameter defining a mathematical expression. Each of the components knows how to use that mathematical expression within its simulation process. e.g.: `"people_density": "0.1 * f"`, this parameter states that the people density shall be calculated by multiplying by 0.1 a variable called "f" that the component must include.

All of the above types can also be defined as parameter lists, giving rise to the following types:

- Parameter_string_list: List of String of characters, e.g.: ` "authors": ["Juan F.", "Luis", "Ismael"]`.
- Parameter_boolean_list: List of True or False values, e.g.: `"operated": [True, True, False]`.
- Parameter_int_list: List of integer values, e.g.: `"people": [24, 12, 18]`.
- Parameter_float_list: List of floating point values, e.g.: `"solar_alpha": [0.8, 0.75]`.
- Parameter_options_list: List of character strings included in a closed option list, e.g.: `"day_types": ["MONDAY", "TUESDAY"]`.
- Parameter_component_list: List of references to another components, e.g.: `"materials": ["Cement mortar", "Hollow brick"]`.
- Parameter_variable_list: List of parameters used to copy a list of variables. e.g.: `"input_variables": ["t_1 = meteo.temperature","hr = meteo.relative_humidity"]`.
- Parameter_math_exp_list: List of mathematical expressions. e.g.: `"curves": ["0.3 * t + 20","0.04 * t^2 - 0.2 * t + 3 "]`.


The Parameter_component, Parameter_variable, Parameter_component_list and Parameter_variable_list can refer to a component of the same project, in that case it is only necessary to put the name of the component, or a component of another project. In this last case we must write "project_name->component_name". e.g. `"meteo_file": "Project 1->Sevilla"`.

To get or set the value of a parameter we must use the attribute "value" of the parameter. If the parameter contain a list we can set/get each value using index, for example: `pro.component("week").parameter("days_schedules").value[0]` will return "working_day"
<pre><code class="python">
...

pro.component("year").parameter("description").value = "Example of year schedule"
pro.component("year").parameter("description").value
</code></pre>
Jupyter output:
<pre><code class="shell">
'Example of year schedule'
</code></pre>

### Variables

**Variables** are elements included in the components to store the temporal information generated during the simulation.

![Variables](img/variables.png)

Variables are lists of floating values, one for each instant of simulated time.

To access the values of a variable we use the `values` attribute which returns a numpy.array object (NumPy library array object).

<pre><code class="python">
...

pro.component("year").variable("values").values 
</code></pre>
Jupyter output:
<pre><code class="shell">
array([  0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,
         0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,
         0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0., 100.,
       100., 100., 100., 100., 100., 100., 100., 100., 100., 100., 100.,
       100., 100., 100., 100., 100., 100., 100., 100.,   0.,   0.,   0.,
         0.,   0.,   0.,   0.,   0.,  80.,  80.,  80.,  80.,  80.,  80.,
        80.,  80.,  80.,  80.,  80.,  80.,  80.,  80.,  80.,  80.,   0.,
         0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,
         0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,
         0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,
         0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,
         0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,
         0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,
         0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,
         0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,
         0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,
         0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,
         0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,
         0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,
         0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,
         0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,
         0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,
         0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,
         0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,
         0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,
...
       100.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,  80.,  80.,
        80.,  80.,  80.,  80.,  80.,  80.,  80.,  80.,  80.,  80.,  80.,
        80.,  80.,  80.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,
         0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,   0.,
         0.])
Output is truncated. View as a scrollable element or open in a text editor. Adjust cell output settings...
</code></pre>

The `variable_dataframe(units, frequency, value, interval)` method of the components returns a pandas dataframe with all the variables of the component.

with the following possible arguments (In bold the default values):

- units [__False__/True]: Include de units in the name of the variable.
- frequency [__None__, "H", "D", "M", "Y"]: Frequency of the data, that of the simulation (None), hourly ("H"), daily ("D"), monthly ("M") or yearly ("Y").
- value [__"mean"__,"max","min","sum"]: If we use a frequency other than the simulation frequency (e.g. monthly "M"), the value obtained for each row (month) will be the mean ("mean"), the maximum ("max"), the minimum ("min") or the sum ("sum").
- interval [__None__,[start_date, end_date]]: List with the start and end dates of the period to be included in the dataframe, if the value is None all values are included.

As an example we can see how to obtain the monthly average values of the variables of a meteorological file (File_met component):

<pre><code class="python">
...

pro.component("met_file").variable_dataframe(frequency="M",value="mean")
</code></pre>
Jupyter shell:

![variable_dataframe](img/variable_dataframe.png)
















