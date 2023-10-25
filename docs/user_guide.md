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

The simulation object will be used to create and manage the different projects. To create a new project in our simulation environment we will use the `Project(sim)` function. 

<pre><code class="python">
import OpenSimula as osm

sim = osm.Simulation()
pro = osm.Project(sim)
</code></pre>

#### Simulation functions

- **del_project(pro)**: Deletes the "pro" project.
- **project(name)**: Returns the project with name parameter "name". Returns "None" if not found.
- **project_list()**: Returns the list of projects in simulation environment.

### Projects

Projects are objects that contain a set of components that define a case that can be temporarily simulated.

#### Project parameters

- **name** [_string_,  default = "Project_X"]: Name of the project.
- **description** [_string_, default = "Description of the project"]: Description of the project.
- **time_step** [_int_, unit = "s", default = 3600, min = 1]: Time step in seconds used for simulation. 
- **n_time_steps** [_int_, default = 8760, min = 1]: Number of time steps to simulate. 
- **initial_time** [_string_, default = "01/01/2001 00:00:00"]: Initial simulation time with format "DD/MM/YYYY hh:mm:ss".

Example of project for the simulation of the first of june with 15 min time step.

<pre><code class="python">
import OpenSimula as osm

sim = osm.Simulation()
pro = osm.Project(sim)
pro.parameter("name").value = "Project one"
pro.parameter("description").value = "Project example"
pro.parameter("time_step").value = 60*15
pro.parameter("n_time_steps").value = 24*4
pro.parameter("initial_time").value = "01/06/2001 00:00:00"
</code></pre>



