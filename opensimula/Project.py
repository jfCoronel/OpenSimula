import json
import datetime as dt
import numpy as np
import pandas as pd
from opensimula.Component import Component
from opensimula.Parameters import Parameter_int, Parameter_string
from opensimula.components import *


class Project(Component):
    """Project has the following features:
    
    - It is included in one Simulation environment
    - Contain a list of components
    - Contains the following parameters:
        * name (string, "Project_X"): name of the project
        * type (string, "Project"): "Project"
        * description (string, "Description of the project"): Description of the project
        * time_step (int, 600): Time step in seconds
        * n_time_steps (int, 52560): Number of time steps to be simulated
        * initial_time (string, "01/01/2001 00:00:00"): Initial time for the simulation
    """

    def __init__(self, sim):
        """Create new project
        
        Args:
            sim (Simulation): parent Simulation environment
        """
        Component.__init__(self, sim)
        self.parameter["type"].value = "Project"
        self.parameter["name"].value = "Project_X"
        self.parameter["description"].value = "Description of the project"
        self.add_parameter(Parameter_int("time_step", 600, "s", min=1))
        self.add_parameter(Parameter_int("n_time_steps", 52560, min=1))
        self.add_parameter(Parameter_string("initial_time", "01/01/2001 00:00:00"))
        sim.add_project(self)
        self._components_ = []

    def add_component(self, component):
        """Add component to Project
        
        Args:
            component (Component): Component to be added to the project
        """
        component.parent = self
        self._components_.append(component)

    def del_component(self, component):
        """Delete component from Project
        
        Args:
            component (Component): Component to be removed from the project
        """
        self._components_.remove(component)

    def find_component(self, name):
        """Find component
        
        Args:
            name (string): name of the component
        
        Returns:
            component (Component): component found, None if not found.
        """
        for comp in self._components_:
            if comp.parameter["name"].value == name:
                return comp
        return None

    @property
    def components(self):
        """Components list in the project
        
        Returns:
            components (Components list): List of components.
        """
        return self._components_

    @property
    def simulation(self):
        """
        Returns:
            simulation (Simulation): Simulation environment
        """
        return self.parent

    @property
    def project(self):
        """
        Returns:
            project (Project): Parent proyect
        """
        return self

    def components_dataframe(self):
        names = []
        types = []
        descriptions = []
        for comp in self.components:
            names.append(comp.parameter["name"].value)
            types.append(comp.parameter["type"].value)
            descriptions.append(comp.parameter["description"].value)
        data = pd.DataFrame({"name": names, "type": types, "description": descriptions})
        return data

    def new_component(self, type):
        try:
            clase = globals()[type]
            comp = clase()
            self.add_component(comp)
            return comp
        except KeyError:
            return None

    def load_from_dic(self, dic):
        """Load paramaters an components from dictionary
        
        Args:
            dic (dictionary): dictonary with the parameters and componenets to be loaded in the project
        
        """
        for key, value in dic.items():
            if key == "components":  # Lista de componentes
                for component in value:
                    if "type" in component:
                        comp = self.new_component(component["type"])
                        if comp == None:
                            print(
                                "Error: Component type ",
                                component["type"],
                                " does no exist",
                            )
                        else:
                            comp.set_parameters(component)
                    else:
                        print('Error: Component does not contain "type" ', component)
            else:
                if key in self.parameter:
                    self.parameter[key].value = value
                else:
                    print("Error: Project parameter ", key, " does not exist")
        self.check()

    def read_json(self, json_file):
        """Read paramaters an components from dictionary in a json file
        
        Args:
            json_file (string): file name that contains dictonary with the parameters and componenets to be loaded in the project
        
        """
        try:
            f = open(json_file, "r")
        except OSError:
            print("Error: Could not open/read file: ", json_file)
            return False
        with f:
            json_dict = json.load(f)
            self.load_from_dic(json_dict)

    def read_excel(self, excel_file):
        """Read paramaters an components from excel file

        Args:
            excel_file (string): excel file path
        """
        try:
            xls_file = pd.ExcelFile(excel_file)
            json_dict = self._excel_to_json_(xls_file)
            self.load_from_dic(json_dict)
        except Exception as e:
            print("Error: reading file: ", excel_file, " -> ", e)
            return False

    def _excel_to_json_(self, xls_file):
        json = {"components": []}
        sheets = xls_file.sheet_names
        # project sheet
        project_df = xls_file.parse(sheet_name="project")
        for index, row in project_df.iterrows():
            json[row["key"]] = self._value_to_json_(row["value"])
        # rest of sheets
        for sheet in sheets:
            if sheet != "project":
                comp_df = xls_file.parse(sheet_name=sheet)
                column_names = comp_df.columns.values.tolist()
                for index, row in comp_df.iterrows():
                    j = 0
                    comp_json = {}
                    comp_json["type"] = sheet
                    for cell in row:
                        comp_json[column_names[j]] = self._value_to_json_(cell)
                        j += 1
                    json["components"].append(comp_json)
        return json

    def _value_to_json_(self, value):
        if isinstance(value, str):
            if value[0] == "[":
                return value[1:-1].split(",")
            else:
                return value
        else:
            return value

    def check(self):
        """Check if all is correct, for the project and all its components
        
            Prints all errors found

        Returns:
            errors (string list): List of errors
        """
        print("Checking project: ", self.parameter["name"].value)
        errors = super().check()  # Parameters
        names = []
        # Check initial time
        try:
            dt.datetime.strptime(
                self.parameter["initial_time"].value, "%d/%m/%Y %H:%M:%S"
            )
        except ValueError:
            error = f"Error in project: {self.parameter['name'].value},"
            error += f" initial_time: {self.parameter['initial_time'].value} does not match format (dd/mm/yyyy HH:MM:SS)"
            errors.append(error)

        for comp in self.components:
            error_comp = comp.check()
            if (len(error_comp) > 1):
                for e in error_comp:
                    errors.append(e)
            if comp.parameter["name"].value in names:
                error = f"Error in project: {self.parameter['name'].value},"
                error += f" '{comp.parameter['name'].value}' is used by other component as name"
                errors.append(error)
            else:
                names.append(comp.parameter["name"].value)

        if len(errors) == 0:
            print("ok")
        else: 
            for error in errors:
                print(error)
        
        return errors

    def simulate(self):
        """ Project Time Simulation"""
        n = self.parameter["n_time_steps"].value
        date = dt.datetime.strptime(
            self.parameter["initial_time"].value, "%d/%m/%Y %H:%M:%S"
        )
        delta_t = self.parameter["time_step"].value

        self.pre_simulation(n)

        for i in range(n):
            print("Simulation: ", i, " of ", n, end="\r")
            self.pre_iteration(i, date)
            converge = False
            while not converge:
                if self.iteration(i, date):
                    converge = True
            self.post_iteration(i, date)
            date = date + dt.timedelta(0, delta_t)

        print("Simulation: ", n, " of ", n)
        self.post_simulation()

    def pre_simulation(self, n_time_steps):
        for comp in self.components:
            comp.pre_simulation(n_time_steps)

    def post_simulation(self):
        for comp in self.components:
            comp.post_simulation()

    def pre_iteration(self, time_index, date):
        for comp in self.components:
            comp.pre_iteration(time_index, date)

    def iteration(self, time_index, date):
        converge = True
        for comp in self.components:
            if not comp.iteration(time_index, date):
                converge = False
        return converge

    def post_iteration(self, time_index, date):
        for comp in self.components:
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
    
    
    def _repr_html_(self):
        html = f"<h3>Project: {self.parameter['name'].value}</h3><p>{self.parameter['description'].value}</p>"
        html += "<strong>Components list:</strong>"
        html += self.components_dataframe().to_html()
        return html;
