## Getting Started

`OpenSimula` is a component-based time simulation environment in Python. 

The general object structure provided by OpenSimula is composed of three main elements:

- Simulation: The global environment for simulation.
- Project: A set of components that define a problem that can be temporarily simulated.
- Component: These are the base elements on which the simulation is performed. The types of components currently available can be consulted in section [Component list](component_list.md).

![Global structure](img/global_structure.png)

### Parameters

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


### Variables

**Variables** are elements included in the components to store the temporal 
information generated during the simulation.

![Variables](img/variables.png)

### First example

The best environment to start using OpenSimula is with [Jupyter notebooks](https://jupyter.org/) or [Google Colab](https://colab.research.google.com/).

First we are going to define a Python dictionary that contains the information of our project:

<pre><code class="python">
project_dic = {
    "name": "First example project",
    "time_step": 3600,
    "n_time_steps": 8760,
    "initial_time": "01/01/2001 00:00:00",
    "components": [
        {
            "type": "Day_schedule",
            "name": "working_day",
            "time_steps": [28800, 18000, 7200, 14400],
            "values": [0, 100, 0, 80, 0],
            "interpolation": "STEP",
        },
        {
            "type": "Day_schedule",
            "name": "holiday_day",
            "time_steps": [],
            "values": [0],
            "interpolation": "STEP",
        },
        {
            "type": "Week_schedule",
            "name": "working_week",
            "days_schedules": [
                "working_day",
                "working_day",
                "working_day",
                "working_day",
                "working_day",
                "holiday_day",
                "holiday_day",
            ],
        },
        {
            "type": "Week_schedule",
            "name": "holiday_week",
            "days_schedules": ["holiday_day"],
        },
        {
            "type": "Year_schedule",
            "name": "year",
            "periods": ["01/08", "01/09"],
            "weeks_schedules": ["working_week", "holiday_week", "working_week"],
        },
    ],
}
</code></pre>

All OpenSimula projects must contain the project definition parameters and a key called `components` with the list of project components. The project parameters in this example are:

- `name`: project name.
- `time_step`: Time step used for simulation in seconds.
- `n_time_step`: Number of simulated time steps.
- `initial_time`: Initial time for the simulation.

The project contains two components of type `Day_schedule`, two of type `Week_schedule` and one of type `Year_schedule`. The first Day_schedule component called `working_day` describes how a value changes throughout the day. The day is divided into five periods described in the `time_steps` parameter: 

1. 28800 s (00:00 to 8:00). 
2. 18000 s (8:00 to 13:00)
3. 7200 s (13:00 to 15:00)
4. 14400 s (15:00 to 19:00)
5. Rest of day (19:00 to 24:00)

The values for these periods are defined in the `values` parameter, in our example they are 0, 100, 0, 0, 80 and 0. the `STEP` value of the `interpolation` parameter sets the value to change in steps from 0 to 100 at 8:00. The other option for the interpolation parameter is `LINEAR` which would perform a linear interpolation to obtain the values at each simulation instant. The other `Day_schedule` component called `holiday_day` sets a single all-day period with value 0. 

The `Week_schedule` components define two different types of weeks, the `working_week` in which a `Day_schedule` reference is set through the `days_schedules` parameter setting `working_day` for Monday through Friday and `holiday_day` for Saturday and Sunday. The `holiday_week` component sets a single `Day_schedule` reference to be used for all days of the week equal to `holiday_day`.

Finally, the `Year_schedule` named `year` sets three annual periods using the `periods` parameter and their respective references to `Week_schedule` using `weeks_schedules` parameter which are:

- January 1st to August 1st: `working_week`.
- August 1st to September 1st: `holiday_week`.
- September 1st to December 31st: `working_week`.

To simulate this project that we have defined, we first import the OpenSimula package with the alias osm, create a simulation environment in the `sim` variable, a project within that simulation environment called `pro`. We load the project reading the dictionary that we have explained previously with the `read_dict` function available for projects and we simulate it using the `simulate()` function. 

<pre><code class="python">
import OpenSimula as osm

sim = osm.Simulation()
pro = osm.Project(sim)
pro.read_dict(project_dic)
pro.simulate()
</code></pre>

We will get the following in response to these commands: 

<pre><code class="shell">
Reading project data from dictonary
Reading completed.
Checking project: First example project
ok
Simulation: 10% 20% 30% 40% 50% 60% 70% 80% 90% 100%  End
</code></pre>

After the simulation, each of the components will have its time variables calculated. In our case the `year` component has a temporary variable called `values` that we can obtain. The following code snippet shows how to plot this variable using the `plotly` python library.

<pre><code class="python">
import plotly.express as px

datos = pro.component("year").variable_dataframe()
fig = px.line(datos,x='date',y=['values'],height=600)
fig.show()
</code></pre>

We obtain an interactive graph with the 8760 values on which we can zoom in to show, as an example, the first week of the year.
first week of the year.

![First example plot](img/schedule_plot.png)




















