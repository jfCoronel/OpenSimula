---
title: 'OpenSimula: a component-based time simulation environment in Python for buildings and HVAC systems'
tags:
  - Python
  - building energy simulation
  - HVAC
  - thermal simulation
  - ASHRAE 140
authors:
  - name: Juan F. Coronel
    orcid: 0000-0002-7732-1334
    corresponding: true
    affiliation: 1
  - name: Luis Pérez-Lombard
    orcid: 0000-0002-8887-1833
    affiliation: 1
  - name: Ismael R. Maestre
    orcid: 0000-0002-7322-3825
    affiliation: 2
affiliations:
  - name: Departamento de Ingeniería Energética, Escuela Técnica Superior de Ingeniería, Universidad de Sevilla, Spain
    index: 1
  - name: Departamento de Máquinas y Motores Térmicos, Escuela Politécnica Superior de Algeciras, Universidad de Cádiz, Spain
    index: 2
date: 28 October 2026
bibliography: paper.bib
---

<!-- TODO before submission: complete the research impact statement (courses, theses, projects that use OpenSimula);
     review the AI usage disclosure. -->

# Summary

OpenSimula is an open-source Python package for the dynamic simulation of buildings and
their heating, ventilation and air-conditioning (HVAC) systems. A simulation is a set of
components (weather files, schedules, materials and constructions, spaces and surfaces,
HVAC equipment and systems) that reference each other and are advanced together in time
steps, typically hourly over a year. Models are defined as Python dictionaries or JSON
files, run from a script or a Jupyter or marimo notebook, and their results are returned as
NumPy arrays and pandas DataFrames [@harris2020; @mckinney2010], so they can be analysed,
plotted and post-processed with the scientific Python ecosystem without intermediate files.
The package includes the input definitions of the ANSI/ASHRAE Standard 140-2023 test cases
[@ashrae140] and a script that runs all of them and compares the results with those of the
reference programs published with the Standard.

# Statement of need

Building energy simulation is used to design buildings and HVAC systems, check them against
energy codes, and research new envelope technologies and control strategies. The established
tools, such as EnergyPlus [@crawley2001], TRNSYS [@trnsys] and ESP-r [@clarke2001], are
standalone programs: a model is written in a program-specific input format, the simulation
runs as an external process, and the results are read back from output files. Parametric
studies, optimisation, sensitivity analysis or the coupling with data-driven and machine
learning models therefore require an additional layer that writes input files, launches
runs and parses outputs.

OpenSimula targets researchers, teachers and students who work in Python and want the
building and HVAC models themselves to be Python objects. Every parameter and every result
of every component is accessible in memory between and after simulations; a parametric
study is a loop that changes parameter values and calls `simulate()` again; and a new
physical model is a Python class. Because the source code of the models is short and
readable, the package is also suited to teaching how a building simulation program works
internally, from conduction transfer functions to the iterative coupling of zones and HVAC
systems. The component architecture is not specific to buildings, so other time-varying
thermal systems, such as refrigeration equipment or industrial processes, can be modelled
with the same framework [@coronel2026cytef].

# State of the field

EnergyPlus, TRNSYS and ESP-r are the reference programs of the Standard 140 comparisons and
the most widely used whole-building simulation engines; OpenStudio [@guglielmetti2011] and
Python libraries such as eppy [@eppy] make EnergyPlus scriptable, but the model still runs as
an external executable whose internal state is not accessible during the simulation. The
Modelica Buildings library [@wetter2014] offers equation-based, fully extensible component
models, at the cost of a Modelica toolchain and a modelling paradigm that is far from the
day-to-day tools of most Python users. Within the Python ecosystem there are well-established
packages for parts of the problem, such as PsychroLib for psychrometrics [@meyer2019], which
OpenSimula uses, or pvlib for solar irradiance [@holmgren2018], but no package that covers
the whole chain from weather data and envelope to air-side and water-side HVAC systems and
that has been checked against the full set of Standard 140 test suites. OpenSimula aims to
fill this gap with a pure Python implementation whose models are deliberately close to the
ones used by the reference programs, so that its results can be compared with them case by
case.

# Software design

OpenSimula has three levels. A `Simulation` contains one or more `Project`s; a project holds
the simulation parameters (time step, number of steps, initial date, weather file, shadow
calculation mode) and a list of `Component`s. Each component has typed *parameters*, which
define it and are validated before the simulation (ranges, allowed options, references to
other components of the same or another project), and *variables*, the time series it
produces. Components are coupled by references (a space references its space type and
building, a surface its construction and space, an HVAC system its spaces, equipment and
schedules), and by `Parameter_math_exp` expressions that can use variables of other
components, which allows control laws such as a setpoint that depends on the outdoor
temperature to be written in the project definition without new code.

During the simulation the project calls the components in a fixed order of types
(schedules, surfaces, openings, spaces, buildings, HVAC systems, calculators) and, within
each time step, repeats their `iteration()` method until all of them report convergence.
Coupled quantities, such as the air temperature and humidity of a zone conditioned by an
HVAC system, are solved by fixed-point iteration with an adaptive relaxation coefficient.
The available models include, among others: weather files in MET, TMY2, TMY3 and WYEC2
formats with isotropic, Hay–Davies, Reindl and Perez [@perez1990] sky models; multilayer
constructions solved with conduction transfer functions; exterior, interior, ground-coupled
and virtual surfaces; windows with angle-dependent glazing properties; external shading
computed geometrically with Shapely [@shapely] on a 3D model of the building, which can be
displayed with Plotly [@plotly]; interior long-wave radiation between surfaces by radiosity
[@coronel2012]; ideal loads systems; direct-expansion units and systems; and single-zone and
multi-zone water-based air systems with coils, fans, pumps, chillers and heat pumps.
Psychrometric properties are computed with PsychroLib [@meyer2019]. New component types are
added by subclassing `Component`, declaring parameters and variables and implementing the
simulation methods; the API reference documents these base classes.

The design favours readability and accessibility of every intermediate value over speed:
the core is plain Python and NumPy, and an annual hourly simulation of a single-zone Standard
140 case takes of the order of ten seconds on a laptop.

# Validation

The `ASHRAE_140` folder of the repository contains the definitions of the test cases of
Standard 140-2023 [@ashrae140; @judkoff1995] as project JSON files: weather drivers
(WD100–WD600), building thermal envelope and fabric loads (cases 195–995 and free-floating
cases), ground-coupled slab-on-grade (GC30b–GC80c), space cooling equipment (CE100–CE545),
fuel-fired furnaces (HE100–HE230) and air-side HVAC equipment (AE101–AE445). The script
`validate.py` simulates all of them in parallel, extracts the outputs requested by the
Standard and compares them with the range (minimum to maximum) of the example results of the
reference programs; it also generates the validation page of the documentation. The same
comparison runs in continuous integration on every change to the code, so that any change in
the results of the 135 test projects is detected.

With version 0.8.8, 2,321 of the 2,740 single-valued outputs (85 %) lie inside the range of
the reference programs, and about half of the remaining ones are within 1 % of the nearest
bound. \autoref{fig:loads} shows the annual heating and cooling loads of the building
envelope cases. The cases outside the range and their probable causes, such as the constant
interior convection coefficients that produce a small, systematic overestimation of heating
loads, are documented in the repository. The range of the reference programs is not the
Standard's acceptance criterion, but it shows that the results of OpenSimula are of the same
quality as those of established simulation programs.

![Annual heating and cooling loads of the Standard 140 building envelope cases: range of the
reference programs (grey) and OpenSimula (dots inside the range, crosses outside).\label{fig:loads}](annual_loads.png){ width=80% }

# Research impact statement

OpenSimula has been developed at the Universidad de Sevilla since 2023 and is distributed on
PyPI, with each release archived on Zenodo. It has been presented at the CYTEF 2026 congress
[@coronel2026cytef]. <!-- TODO: courses where it is used, theses or projects that use it,
collaborating groups (e.g. Universidad de Cádiz), number of users or downloads if known. -->

# AI usage disclosure

<!-- TODO: review and adjust. -->
Generative AI tools (Claude Code, Anthropic) were used during the development of recent
versions, mainly to automate the Standard 140 validation workflow, write tests and
documentation, and investigate and fix discrepancies found by the validation, and to prepare
a first draft of this paper. All changes were reviewed by the authors, who take full
responsibility for the software and the paper.

# Author contributions

J. F. Coronel conceived OpenSimula, designed its architecture, wrote most of the code and is
its lead developer and maintainer. L. Pérez-Lombard reviewed and advised on the HVAC
equipment and system models, and I. R. Maestre on the building envelope models. Both have
been the main testers of the software, helped to define the many validation test cases and
contributed to the writing of this paper.

# Acknowledgements

<!-- TODO: funding and acknowledgements, if any. -->

# References
