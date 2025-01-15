## Getting Started

The best environment to start using OpenSimula is with [Jupyter notebooks](https://jupyter.org/) or [Google Colab](https://colab.research.google.com/). We recommend the use of [JupyterLab Desktop](https://github.com/jupyterlab/jupyterlab-desktop)

### Installing OpenSiumula

To install OpenSimula you can use any of the methods that Python makes possible. For example, to install using pip we must use:

<pre>
pip install OpenSimula
</pre>

OpenSimula uses in different parts of the code the following Python packages, which will be installed automatically when OpenSimula is installed:

- NumPy
- pandas
- SciPy
- py-expression-eval
- shapely
- psychrolib
- pyvista[jupyter]
- plotly
- dash
- dash_bootstrap_components
- dash_ag_grid
- triangle


### First example

First we are going to define a Python dictionary that contains the information of our project:

<pre><code class="python">
project_dic = {
    "name": "First example project",
    "time_step": 3600,
    "n_time_steps": 24*365,
    "initial_time": "01/01/2001 00:00:00",
    "components": [
        {
            "type": "Day_schedule",
            "name": "working_day",
            "time_steps": [8*3600, 5*3600, 2*3600, 4*3600],
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

1. 8*3600 s (00:00 to 8:00). 
2. 5*3600 s (8:00 to 13:00)
3. 2*3600 s (13:00 to 15:00)
4. 4*3600 s (15:00 to 19:00)
5. Rest of day (19:00 to 24:00)

The values for these periods are defined in the `values` parameter, in our example they are 0, 100, 0, 0, 80 and 0. the `STEP` value of the `interpolation` parameter sets the value to change in steps from 0 to 100 at 8:00. The other option for the interpolation parameter is `LINEAR` which would perform a linear interpolation to obtain the values at each simulation instant. The other `Day_schedule` component called `holiday_day` sets a single all-day period with value 0. 

The `Week_schedule` components define two different types of weeks, the `working_week` in which a `Day_schedule` reference is set through the `days_schedules` parameter setting `working_day` for Monday through Friday and `holiday_day` for Saturday and Sunday. The `holiday_week` component sets a single `Day_schedule` reference to be used for all days of the week equal to `holiday_day`.

Finally, the `Year_schedule` named `year` sets three annual periods using the `periods` parameter and their respective references to `Week_schedule` using `weeks_schedules` parameter which are:

- January 1st to August 1st: `working_week`.
- August 1st to September 1st: `holiday_week`.
- September 1st to December 31st: `working_week`.

To simulate this project that we have defined, we first import the OpenSimula.Simulation object to create a simulation environment in the `sim` variable, a project within that simulation environment called `pro`. We load the project reading the dictionary that we have explained previously with the `read_dict` function available for projects and we simulate it using the `simulate()` function. 

<pre><code class="python">
import OpenSimula.Simulation as Simulation

sim = Simulation()
pro = sim.new_project("pro")
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

After the simulation, each of the components will have its time variables calculated. In our case the `year` component has a temporary variable called `values` that we can obtain. the Simulation.plot function can be used to draw an interactive graph (plotly library), the first argument are the dates of the simulation steps (pro.dates() return the array of simulated dates) and the second a list of the varibles to draw.

<pre><code class="python">
variables = [pro.component("year").variable("values")]
sim.plot(pro.dates(), variables)
</code></pre>

We obtain an interactive graph with the 8760 values on which we can zoom in to show, as an example, the first week of the year.

![First example plot](img/schedule_plot.png)




















