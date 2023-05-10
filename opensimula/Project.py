import json
import datetime as dt
import numpy as np
import pandas as pd
from opensimula.Component import Component
from opensimula.parameters import Parameter_number, Parameter_string
from opensimula.components import *


class Project(Component):
    """Project is a Compenent that contains a list of Components"""

    def __init__(self, sim):
        """Create new project in the sim Simulation"""
        Component.__init__(self, sim)
        self.parameter["type"].value = "Project"
        self.parameter["name"].value = "Project_X"
        self.add_parameter(Parameter_number("time_step", 600, "s", min=1))
        self.add_parameter(Parameter_number("n_time_steps", 52560, min=1))
        self.add_parameter(Parameter_string("initial_time", "01/01/2001 00:00:00"))
        sim.add_project(self)
        self._components_ = []

    def add_component(self, component):
        """Add component to the Project"""
        component.parent = self
        self._components_.append(component)

    def del_component(self, component):
        self._components_.remove(component)

    def find_component(self, name):
        for comp in self._components_:
            if comp.parameter["name"].value == name:
                return comp
        return None

    @property
    def component(self):
        return self._components_

    @property
    def simulation(self):
        """
        Returns:
            Simulation: Simulation environment
        """
        return self.parent

    @property
    def project(self):
        return self

    def components_dataframe(self):
        names = []
        types = []
        for comp in self.component:
            names.append(comp.parameter["name"].value)
            types.append(comp.parameter["type"].value)
        data = pd.DataFrame({"name": names, "type": types})
        return data

    def info(self):
        """Print project information"""
        print("Project info: ")
        print("   Parameters:")
        for key, param in self.parameter.items():
            print("       ", param.info())
        print("   Components number: ", len(self._components_))

    def new_component(self, type):
        clase = globals()[type]
        comp = clase()
        self.add_component(comp)
        return comp

    def load_from_json(self, json):
        """Create paramaters an components from json dictionary"""
        for key, value in json.items():
            if key == "components":  # Lista de compoenentes
                for component in value:
                    comp = self.new_component(component["type"])
                    comp.set_parameters(component)
            else:  # Debe ser un parámetro
                self.parameter[key].value = value

    def read_json(self, json_file):
        """Read paramaters an components from json file"""
        try:
            f = open(json_file, "r")
        except OSError:
            print("Error: Could not open/read file: ", json_file)
            return False
        with f:
            json_dict = json.load(f)
            self.load_from_json(json_dict)

    def check(self):
        """Check if all is correct, for all its components

        Returns:
            int: Number of errors
        """
        print("Checking project: ", self.parameter["name"].value)
        names = []
        n_errors = 0
        # Check initial time
        try:
            dt.datetime.strptime(
                self.parameter["initial_time"].value, "%d/%m/%Y %H:%M:%S"
            )
        except ValueError:
            print("Error in project: ", self.parameter["name"].value)
            print(
                "   ",
                self.parameter["initial_time"].value,
                " does not match format (dd/mm/yyyy HH:MM:SS)",
            )
            n_errors += 1

        for comp in self.component:
            error_comp = comp.check()
            n_errors += error_comp
            if comp.parameter["name"].value in names:
                print("Error in project: ", self.parameter["name"].value)
                print(
                    "   ",
                    comp.parameter["name"].value,
                    " is used by other component as name",
                )
                n_errors += 1
            else:
                names.append(comp.parameter["name"].value)

        if n_errors == 0:
            print("ok")
        return n_errors

    def simulate(self):
        n = self.parameter["n_time_steps"].value
        date = dt.datetime.strptime(
            self.parameter["initial_time"].value, "%d/%m/%Y %H:%M:%S"
        )
        delta_t = self.parameter["time_step"].value

        self.pre_simulation(n)

        for i in range(n):
            self.pre_iteration(i, date)
            converge = False
            while not converge:
                if self.iteration(i, date):
                    converge = True
            self.post_iteration(i, date)
            date = date + dt.timedelta(0, delta_t)

        self.post_simulation()

    def pre_simulation(self, n_time_steps):
        for comp in self.component:
            comp.pre_simulation(n_time_steps)

    def post_simulation(self):
        for comp in self.component:
            comp.post_simulation()

    def pre_iteration(self, time_index, date):
        for comp in self.component:
            comp.pre_iteration(time_index, date)

    def iteration(self, time_index, date):
        converge = True
        for comp in self.component:
            if not comp.iteration(time_index, date):
                converge = False
        return converge

    def post_iteration(self, time_index, date):
        for comp in self.component:
            comp.post_iteration(time_index, date)

    def dates_array(self):
        n = self.parameter["n_time_steps"].value
        date = dt.datetime.strptime(
            self.parameter["initial_time"].value, "%d/%m/%Y %H:%M:%S"
        )
        delta_t = self.parameter["time_step"].value
        array = np.empty(n, dtype=object)

        for i in range(n):
            array[i] = date
            date = date + dt.timedelta(0, delta_t)

        return array
