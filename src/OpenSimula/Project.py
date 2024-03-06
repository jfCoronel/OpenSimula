import json
import datetime as dt
import numpy as np
import pandas as pd
from OpenSimula.Parameter_container import Parameter_container
from OpenSimula.Parameters import Parameter_int, Parameter_string, Parameter_string_list
from OpenSimula.components import *


class Project(Parameter_container):
    """Project has the following features:

    - It is included in the Simulation environment
    - Contain a list of components
    - Contains parameters for its definition
    """

    def __init__(self, name, sim):
        """Create new project

        Args:
            sim (Simulation): parent Simulation environment
        """
        Parameter_container.__init__(self, sim)
        self.parameter("name").value = name
        self.parameter("description").value = "Description of the project"
        self.add_parameter(Parameter_int("time_step", 3600, "s", min=1))
        self.add_parameter(Parameter_int("n_time_steps", 8760, min=1))
        self.add_parameter(Parameter_string(
            "initial_time", "01/01/2001 00:00:00"))
        self.add_parameter(
            Parameter_string_list(
                "simulation_order",
                [
                    "File_data",
                    "File_met",
                    "Day_schedule",
                    "Week_schedule",
                    "Year_schedule",
                    "Material",
                    "Glazing",
                    "Frame",
                    "Construction",
                    "Opening_type",
                    "Space_type",
                    "Exterior_surface",
                    "Virtual_exterior_surface",
                    "Underground_surface",
                    "Interior_surface",
                    "Virtual_interior_surface",
                    "Opening",
                    "Space",
                    "Building"
                ],
            )
        )
        sim._add_project_(self)
        self._components_ = []

    def _add_component_(self, component):
        """Add component to Project

        Args:
            component (Component): Component to be added to the project
        """
        component._project_ = self
        self._components_.append(component)

    def del_component(self, component):
        """Delete component from Project

        Args:
            component (Component): Component to be removed from the project
        """
        self._components_.remove(component)

    def component(self, name):
        """Find and return component with its name

        Args:
            name (string): name of the component

        Returns:
            component (Component): component found, None if not found.
        """
        for comp in self._components_:
            if comp.parameter("name").value == name:
                return comp
        return None

    def component_list(self, type="all"):
        """Components list in the project

        Returns:
            components (Components list): List of components.
        """
        comp_list = []
        for comp in self._components_:
            if type == "all":
                comp_list.append(comp)
            else:
                if comp.parameter("type").value == type:
                    comp_list.append(comp)
        return comp_list

    def simulation(self):
        """
        Returns:
            simulation (Simulation): Simulation environment
        """
        return self._sim_

    def component_dataframe(self, type="all"):
        data = pd.DataFrame()
        comp_list = self.component_list(type)
        if len(comp_list) > 0:
            parameters = ["name", "type", "description"]
            if type != "all":
                for key, par in comp_list[0]._parameters_.items():
                    if key != "name" and key != "type" and key != "description":
                        parameters.append(key)
            for param in parameters:
                param_array = []
                for comp in comp_list:
                    param_array.append(comp.parameter(param).value)
                data[param] = param_array
        return data

    def _new_component_(self, type, name):
        try:
            clase = globals()[type]
            comp = clase(name, self)
            return comp
        except KeyError:
            return None

    def _get_error_header_(self):
        return f'Error: Project "{self.parameter("name").value}". '

    def _load_from_dict_(self, dic):
        for key, value in dic.items():
            if key == "components":  # Lista de componentes
                for component in value:
                    if "type" in component:
                        name = component["type"]+"_X"
                        if "name" in component:
                            name = component["name"]
                        comp = self._new_component_(component["type"], name)
                        if comp == None:
                            msg = self._get_error_header_(
                            ) + f'Component type {component["type"]} does not exist.'
                            self._sim_.print(msg)
                        else:
                            comp.set_parameters(component)
                    else:
                        msg = self._get_error_header_(
                        ) + f'Component does not contain "type" parameter {component}'
                        self._sim_print(msg)
            else:
                if key in self._parameters_:
                    self.parameter(key).value = value
                else:
                    msg = self._get_error_header_(
                    ) + f'Parameter {key} does not exist.'
                    self._sim_.print(msg)

    def read_dict(self, dict):
        """Load paramaters an components from dictionary

        Args:
            dic (dictionary): dictonary with the parameters and componenets to be loaded in the project

        """
        self._sim_.print("Reading project data from dictonary")
        self._load_from_dict_(dict)
        self._sim_.print("Reading completed.")
        self.check()

    def read_json(self, json_file):
        """Read paramaters an components from dictionary in a json file

        Args:
            json_file (string): file name that contains dictonary with the parameters and componenets to be loaded in the project

        """
        try:
            f = open(json_file, "r")
        except OSError:
            msg = self._get_error_header_(
            ) + f'Could not open/read file:  {json_file}.'
            self._sim_.print(msg)
            return False
        with f:
            json_dict = json.load(f)
            self._sim_.print("Reading project data from file: " + json_file)
            self._load_from_dict_(json_dict)
            self._sim_.print("Reading completed.")
            self.check()

    def _read_excel_(self, excel_file):
        """Read paramaters an components from excel file

        Args:
            excel_file (string): excel file path
        """
        try:
            xls_file = pd.ExcelFile(excel_file)
            self._sim_.print("Reading project data from file: " + excel_file)
            json_dict = self._excel_to_json_(xls_file)
            self._load_from_dict_(json_dict)
            self._sim_.print("Reading completed.")
            self.check()
        except Exception as e:
            msg = self._get_error_header_(
            ) + f'Reading file:  {excel_file} -> {e}.'
            self._sim_.print(msg)
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

    # ____________________

    def _set_ordered_component_list_(self):
        all_comp_list = []
        for comp in self.component_list():
            components = comp.get_all_referenced_components()
            for comp_i in components:
                if comp_i not in all_comp_list:
                    all_comp_list.append(comp_i)
        # order components
        self._ordered_component_list_ = []
        # Add components in simulation order
        for type in self.parameter("simulation_order").value:
            for comp in all_comp_list:
                if comp.parameter("type").value == type:
                    self._ordered_component_list_.append(comp)
        # Add rest of components
        for comp in all_comp_list:
            if comp not in self._ordered_component_list_:
                self._ordered_component_list_.append(comp)

    def check(self):
        """Check if all is correct, for the project and all its components

            Prints all errors found

        Returns:
            errors (string list): List of errors
        """
        self._sim_.print("Checking project: " + self.parameter("name").value)
        errors = self.check_parameters()  # Parameters
        names = []
        # Check initial time
        try:
            dt.datetime.strptime(
                self.parameter("initial_time").value, "%d/%m/%Y %H:%M:%S"
            )
        except ValueError:
            error = self._get_error_header_() + \
                f"Initial_time: {self.parameter('initial_time').value} does not match format (dd/mm/yyyy HH:MM:SS)"
            errors.append(error)

        self._set_ordered_component_list_()
        list = self._ordered_component_list_
        for comp in list:
            error_comp = comp.check()
            if len(error_comp) > 0:
                for e in error_comp:
                    errors.append(e)
            if comp.parameter("name").value in names:
                error = self._get_error_header_() + \
                    f"'{comp.parameter('name').value}' is used by two or more components as name"
                errors.append(error)
            else:
                names.append(comp.parameter("name").value)

        if len(errors) == 0:
            self._sim_.print("ok")
        else:
            for error in errors:
                self._sim_.print(error)

        return errors

    def simulate(self):
        """Project Time Simulation"""
        n = self.parameter("n_time_steps").value
        date = dt.datetime.strptime(
            self.parameter("initial_time").value, "%d/%m/%Y %H:%M:%S"
        )
        delta_t = self.parameter("time_step").value

        self._set_ordered_component_list_()
        self._pre_simulation_(n, delta_t)

        self._sim_.print(
            f"Simulating {self.parameter('name').value}: ", add_new_line=False
        )

        show_percent = 10.0
        for i in range(n):
            if ((100.0*(i+1) / n) >= show_percent):
                self._sim_.print(str(int(show_percent)) +
                                 "% ", add_new_line=False)
                show_percent = show_percent + 10.0
            self._pre_iteration_(i, date)
            converge = False
            while not converge:
                if self._iteration_(i, date):
                    converge = True
            self._post_iteration_(i, date)
            date = date + dt.timedelta(0, delta_t)

        self._sim_.print(" End")
        self._post_simulation_()

    def _pre_simulation_(self, n_time_steps, delta_t):
        for comp in self._ordered_component_list_:
            comp.pre_simulation(n_time_steps, delta_t)

    def _post_simulation_(self):
        for comp in self._ordered_component_list_:
            comp.post_simulation()

    def _pre_iteration_(self, time_index, date):
        for comp in self._ordered_component_list_:
            comp.pre_iteration(time_index, date)

    def _iteration_(self, time_index, date):
        converge = True
        for comp in self._ordered_component_list_:
            if not comp.iteration(time_index, date):
                converge = False
        return converge

    def _post_iteration_(self, time_index, date):
        for comp in self._ordered_component_list_:
            comp.post_iteration(time_index, date)

    def dates_array(self):
        n = self.parameter("n_time_steps").value
        date = dt.datetime.strptime(
            self.parameter("initial_time").value, "%d/%m/%Y %H:%M:%S"
        )
        delta_t = self.parameter("time_step").value
        array = np.empty(n, dtype=object)

        for i in range(n):
            array[i] = date
            date = date + dt.timedelta(0, delta_t)

        return array

    def _repr_html_(self):
        html = f"<h3>Project: {self.parameter('name').value}</h3><p>{self.parameter('description').value}</p>"
        html += "<strong>Parameters:</strong>"
        html += self.parameter_dataframe().to_html()
        html += "<br/><strong>Components list:</strong>"
        html += self.component_dataframe().to_html()
        return html
