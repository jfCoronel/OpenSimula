import json
import datetime as dt
import numpy as np
import pandas as pd
from dash import Dash, callback, Input, Output, html, State
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import psychrolib as sicro
from OpenSimula.Message import Message
from OpenSimula.Parameter_container import Parameter_container
from OpenSimula.Parameters import (
    Parameter_component,
    Parameter_int,
    Parameter_string,
    Parameter_string_list,
    Parameter_boolean,
    Parameter_options,
    Parameter_float
)
from OpenSimula.components import *
from OpenSimula.visual_3D.Environment_3D import Environment_3D


class Project(Parameter_container):
    """Project has the following features:

    - It is included in the Simulation environment
    - Contain a list of components
    - Contains parameters for its definition
    - Contains Environment_3D for 3D representation of the project
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
        self.add_parameter(Parameter_string("initial_time", "01/01/2001 00:00:00"))
        self.add_parameter(Parameter_boolean("daylight_saving", False))
        self.add_parameter(
            Parameter_string("daylight_saving_start_time", "25/03/2001 02:00:00")
        )
        self.add_parameter(
            Parameter_string("daylight_saving_end_time", "28/10/2001 02:00:00")
        )
        self.add_parameter(Parameter_int("n_max_iteration", 1000, min=1))
        self.add_parameter(
            Parameter_string_list("simulation_order", DEFAULT_COMPONENTS_ORDER)
        )
        self.add_parameter(
            Parameter_component("simulation_file_met", "not_defined", ["File_met"])
        )
        self.add_parameter(
            Parameter_options(
                "shadow_calculation", "INSTANT", ["NO", "INSTANT", "INTERPOLATION"]
            )
        )
        self.add_parameter(Parameter_float("albedo", 0.2, "frac", min=0, max=1))

        self._sim_ = sim
        self._components_ = []
        sicro.SetUnitSystem(sicro.SI)
        atm_p = sicro.GetStandardAtmPressure(0)
        w_50 = sicro.GetHumRatioFromRelHum(22.5, 0.5, atm_p)

        def rhocp_water(T):
            """
            Returns: Liquid water rho*c_p at 1 atm (J/(m^3·K)), Cubic adjustment

            Parameters:
            T: water temperature (ºC)
            """
            return (
                -6.5515e-08 * T**3 + 7.6219e-06 * T**2 - 1.8564e-03 * T + 4.2125
            ) * 1e6

        # Set simulation properties
        self._sim_.props = {
            "C_PA": 1006,  # J/kg·K
            "C_P_FURNITURE": 1000,  # J/kg·K
            "LAMBDA": 2501,  # J/g Latent heat of water at 0ºC
            "ALTITUDE": 0,  # m
            "ATM_PRESSURE": atm_p,
            "W_50": w_50,
            "RHO_A": sicro.GetMoistAirDensity(22.5, w_50, atm_p),
            "RHOCP_W": rhocp_water,
        }

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

    def component_list(self, comp_type="all"):
        """Components list in the project

        Returns:
            components (Components list): List of components.
        """
        comp_list = []
        for comp in self._components_:
            if comp_type == "all":
                comp_list.append(comp)
            else:
                if comp.parameter("type").value == comp_type:
                    comp_list.append(comp)
        return comp_list

    def component_dataframe(self, comp_type="all", string_format=False):
        data = pd.DataFrame()
        comp_list = self.component_list(comp_type)
        if len(comp_list) > 0:
            parameters = ["name", "type", "description"]
            if comp_type != "all":
                for key, par in comp_list[0]._parameters_.items():
                    if key != "name" and key != "type" and key != "description":
                        parameters.append(key)
            for param in parameters:
                param_array = []
                for comp in comp_list:
                    if string_format:
                        param_array.append(str(comp.parameter(param).value))
                    else:
                        param_array.append(comp.parameter(param).value)
                data[param] = param_array
        return data

    def new_component(self, comp_type, name):
        try:
            clase = globals()[comp_type]
            comp = clase(name, self)
            self._components_.append(comp)
            return comp
        except KeyError:
            return None

    def _get_error_header_(self):
        return f'Project "{self.parameter("name").value}". '

    def _load_from_dict_(self, dic):
        for key, value in dic.items():
            if key == "components":  # Lista de componentes
                for component in value:
                    if "type" in component:
                        name = component["type"] + "_X"
                        if "name" in component:
                            name = component["name"]
                        comp = self.new_component(component["type"], name)
                        if comp == None:
                            msg = (
                                self._get_error_header_()
                                + f'Component type {component["type"]} does not exist.'
                            )
                            self._sim_.message(Message(msg, "ERROR"))
                        else:
                            comp.set_parameters(component)
                    else:
                        msg = (
                            self._get_error_header_()
                            + f'Component does not contain "type" parameter {component}'
                        )
                        self._sim_.message(Message(msg, "ERROR"))
            else:
                if key in self._parameters_:
                    self.parameter(key).value = value
                else:
                    msg = self._get_error_header_() + f"Parameter {key} does not exist."
                    self._sim_.message(Message(msg, "ERROR"))

    def read_dict(self, dict):
        """Load paramaters an components from dictionary

        Args:
            dic (dictionary): dictonary with the parameters and componenets to be loaded in the project

        """
        self._sim_.message(Message("Reading project data from dictonary", "CONSOLE"))
        self._load_from_dict_(dict)
        self._sim_.message(Message("Reading completed.", "CONSOLE"))
        self.check()

    def write_dict(self):
        """Write dictionary with the definition of the project

        Return:
            dic (dictionary): dictonary with the parameters and componenets that define the project

        """
        dict = {"components": []}
        for key, param in self.parameter_dict().items():
            dict[key] = param.value
        for comp in self._components_:
            comp_dict = {}
            for key, param in comp.parameter_dict().items():
                comp_dict[key] = param.value
            dict["components"].append(comp_dict)

        return dict

    def read_json(self, json_file):
        """Read paramaters an components from dictionary in a json file

        Args:
            json_file (string): file name that contains dictonary with the parameters and componenets to be loaded in the project

        """
        try:
            f = open(json_file, "r")
        except OSError:
            msg = self._get_error_header_() + f"Could not open/read file:  {json_file}."
            self._sim_.message(Message(msg, "ERROR"))
            return False
        with f:
            json_dict = json.load(f)
            self._sim_.message(
                Message("Reading project data from file: " + json_file, "CONSOLE")
            )
            self._load_from_dict_(json_dict)
            self._sim_.message(Message("Reading completed.", "CONSOLE"))
            self.check()

    def write_json(self, json_file):
        """Write project definition to json file

        Args:
            json_file (string): file name

        """
        try:
            f = open(json_file, "w")
        except OSError:
            msg = self._get_error_header_() + f"Could not write file:  {json_file}."
            self._sim_.message(Message(msg, "ERROR"))
            return False
        with f:
            self._sim_.message(
                Message("Writing project data to file: " + json_file, "CONSOLE")
            )
            dict = self.write_dict()
            json.dump(dict, f)
            self._sim_.message(Message("Writing completed.", "CONSOLE"))

    def _read_excel_(self, excel_file):
        """Read paramaters an components from excel file

        Args:
            excel_file (string): excel file path
        """
        try:
            xls_file = pd.ExcelFile(excel_file)
            self._sim_.message(
                Message("Reading project data from file: " + excel_file, "CONSOLE")
            )
            json_dict = self._excel_to_json_(xls_file)
            self._load_from_dict_(json_dict)
            self._sim_.message(Message("Reading completed.", "CONSOLE"))
            self.check()
        except Exception as e:
            msg = self._get_error_header_() + f"Reading file:  {excel_file} -> {e}."
            self._sim_.message(Message(msg, "ERROR"))
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
        # Add referenced components
        for comp in self.component_list():
            components = comp.get_all_referenced_components()
            for comp_i in components:
                if comp_i not in all_comp_list:
                    all_comp_list.append(comp_i)
        # order components
        self._ordered_component_list_ = all_comp_list.copy()
        # Remove components and at the end
        for comp_type in self.parameter("simulation_order").value:
            for comp in all_comp_list:
                if comp.parameter("type").value == comp_type:
                    self._ordered_component_list_.remove(comp)
            for comp in all_comp_list:
                if comp.parameter("type").value == comp_type:
                    self._ordered_component_list_.append(comp)

    def check(self):
        """Check if all is correct, for the project and all its components

            Prints all errors found

        Returns:
            errors (string list): List of errors
        """
        self._sim_.message(
            Message("Checking project: " + self.parameter("name").value, "CONSOLE")
        )
        errors = self.check_parameters()  # Parameters
        names = []
        # Check initial time
        try:
            dt.datetime.strptime(
                self.parameter("initial_time").value, "%d/%m/%Y %H:%M:%S"
            )
        except ValueError:
            msg = (
                self._get_error_header_()
                + f"Initial_time: {self.parameter('initial_time').value} does not match format (dd/mm/yyyy HH:MM:SS)"
            )
            errors.append(Message(msg, "ERROR"))
        # Check daylight saving dates
        if self.parameter("daylight_saving").value:
            try:
                dt.datetime.strptime(
                    self.parameter("daylight_saving_start_time").value,
                    "%d/%m/%Y %H:%M:%S",
                )
            except ValueError:
                msg = (
                    self._get_error_header_()
                    + f"Initial_time: {self.parameter('daylight_saving_start_time').value} does not match format (dd/mm/yyyy HH:MM:SS)"
                )
                errors.append(Message(msg, "ERROR"))
            try:
                dt.datetime.strptime(
                    self.parameter("daylight_saving_end_time").value,
                    "%d/%m/%Y %H:%M:%S",
                )
            except ValueError:
                error = (
                    self._get_error_header_()
                    + f"Initial_time: {self.parameter('daylight_saving_end_time').value} does not match format (dd/mm/yyyy HH:MM:SS)"
                )
                errors.append(Message(msg, "ERROR"))

        self._set_ordered_component_list_()
        list = self._ordered_component_list_
        for comp in list:
            error_comp = comp.check()
            if len(error_comp) > 0:
                for e in error_comp:
                    errors.append(e)
            if comp.parameter("name").value in names:
                msg = (
                    self._get_error_header_()
                    + f"'{comp.parameter('name').value}' is used by two or more components as name"
                )
                errors.append(Message(msg, "ERROR"))
            else:
                names.append(comp.parameter("name").value)

        if len(errors) == 0:
            self._sim_.message(Message("Checking completed.", "CONSOLE"))
        else:
            for error in errors:
                self._sim_.message(error)

        return errors

    def simulate(self, show_percentage=10):
        """Project Time Simulation"""
        n = self.parameter("n_time_steps").value
        date = dt.datetime.strptime(
            self.parameter("initial_time").value, "%d/%m/%Y %H:%M:%S"
        )
        delta_t = self.parameter("time_step").value
        date = date + dt.timedelta(0, delta_t / 2)  # Centered in the interval
        if self.parameter("daylight_saving").value:
            date_dls_start = dt.datetime.strptime(
                self.parameter("daylight_saving_start_time").value, "%d/%m/%Y %H:%M:%S"
            )
            date_dls_end = dt.datetime.strptime(
                self.parameter("daylight_saving_end_time").value, "%d/%m/%Y %H:%M:%S"
            )

        # Update props
        if self.parameter("simulation_file_met").value != "not_defined":
            try:
                met_file = self.component(self.parameter("simulation_file_met").value)
                if met_file != None:
                    altitude = met_file.altitude
                    atm_p = sicro.GetStandardAtmPressure(altitude)
                    w_50 = sicro.GetHumRatioFromRelHum(22.5, 0.5, atm_p)
                    self._sim_.props["ATM_PRESSURE"] = atm_p
                    self._sim_.props["ALTITUDE"] = altitude
                    self._sim_.props["W_50"] = w_50
                    self._sim_.props["RHO_A"] = sicro.GetMoistAirDensity(
                        22.5, w_50, atm_p
                    )
            except Exception as e:
                msg = (
                    self._get_error_header_()
                    + f"Error reading file: {self.parameter('simulation_file_met').value} -> {e}"
                )
                self._sim_.message(Message(msg, "ERROR"))

        self._set_ordered_component_list_()
        
        # Initialize 3D environment
        self.env_3D = Environment_3D()
        if self.parameter("shadow_calculation").value != "NO":
            self._load_buildings_3D(self.env_3D)
            self._sim_.message(Message("Calculating solar direct shadows ...", "CONSOLE"))
            self.env_3D.calculate_solar_tables()
        self._pre_simulation_(n, delta_t)
        self._sim_df = pd.DataFrame({"dates": self.dates()})
        self._sim_df["n_iterations"] = 0
        self._sim_df["last_component"] = "None"
        self._sim_df["converged"] = True

        self._sim_.message(
            Message(f"Simulating {self.parameter('name').value}: ...", "CONSOLE")
        )

        show_percent = show_percentage
        n_iter_acum = 0
        for i in range(n):
            if (100.0 * (i + 1) / n) >= show_percent:
                self._sim_.message(
                    Message(
                        f"{int(show_percent)}%: N_iter: {(n_iter_acum/(n*show_percentage/100)):.2f}",
                        "CONSOLE",
                    )
                )
                show_percent = show_percent + show_percentage
                n_iter_acum = 0
            daylight_saving = False
            if self.parameter("daylight_saving").value:
                if date > date_dls_start and date < date_dls_end:
                    daylight_saving = True

            # Update Shadows
            if self.parameter("shadow_calculation").value == "INSTANT":
                cos = met_file.sun_cosines(date)
                if len(cos) == 3:
                    self.env_3D.calculate_shadows(cos,create_polygons=False)
                else:
                    self.env_3D.delete_shadows()

            self._pre_iteration_(i, date, daylight_saving)
            converge = False
            n_iter = 0
            while not converge and n_iter < self.parameter("n_max_iteration").value:
                if self._iteration_(i, date, daylight_saving, n_iter):
                    converge = True
                n_iter += 1
            self._sim_df.at[i, "n_iterations"] = n_iter
            self._sim_df.at[i, "converged"] = converge
            n_iter_acum += n_iter
            self._post_iteration_(i, date, daylight_saving, converge)
            date = date + dt.timedelta(0, delta_t)

        self._sim_.message(Message("Simulation completed.", "CONSOLE"))
        n_not_converged = (
            len(self._sim_df["converged"]) - self._sim_df["converged"].sum()
        )
        if n_not_converged > 0:
            self._sim_.message(
                Message(f"{n_not_converged} time steps did not converge.", "WARNING")
            )
        self._post_simulation_()

    def _pre_simulation_(self, n_time_steps, delta_t):
        for comp in self._ordered_component_list_:
            comp.pre_simulation(n_time_steps, delta_t)

    def _post_simulation_(self):
        for comp in self._ordered_component_list_:
            comp.post_simulation()

    def _pre_iteration_(self, time_index, date, dayligth_saving):
        for comp in self._ordered_component_list_:
            comp.pre_iteration(time_index, date, dayligth_saving)

    def _iteration_(self, time_index, date, dayligth_saving, n_iter):
        converge = True
        for comp in self._ordered_component_list_:
            if not comp.iteration(time_index, date, dayligth_saving, n_iter):
                self._sim_df.at[time_index, "last_component"] = comp.parameter(
                    "name"
                ).value
                converge = False
        return converge

    def _post_iteration_(self, time_index, date, dayligth_saving, converged):
        for comp in self._ordered_component_list_:
            comp.post_iteration(time_index, date, dayligth_saving, converged)

    def dates(self):
        n = self.parameter("n_time_steps").value
        date = dt.datetime.strptime(
            self.parameter("initial_time").value, "%d/%m/%Y %H:%M:%S"
        )
        delta_t = self.parameter("time_step").value
        date = date + +dt.timedelta(0, delta_t / 2)  # Centered in the interval
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

    def simulation_dataframe(self):
        return self._sim_df

    def component_editor(self, comp_type="all"):
        editor = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])
        df = self.component_dataframe(comp_type=comp_type, string_format=True)
        self._n_clicks_new_comp_ = 0
        self._n_clicks_del_comp_ = 0
        disabled_new = False
        if comp_type == "all":
            disabled_new = True

        column_definition = [
            {
                "field": "name",
                "checkboxSelection": True,
                "headerCheckboxSelection": True,
            }
        ]
        for i in df.columns:
            if i != "name":
                column_definition.append({"field": i})

        editor.layout = html.Div(
            [
                dbc.Label("Components editor:"),
                html.Br(),
                dbc.Button(
                    "New component",
                    id="btn-new-comp",
                    disabled=disabled_new,
                    n_clicks=0,
                ),
                dbc.Button(
                    "Delete selected components",
                    id="btn-del-comp",
                    n_clicks=0,
                    style={"margin-left": "15px"},
                ),
                html.Br(),
                html.Br(),
                dag.AgGrid(
                    id="comp-table",
                    rowData=df.to_dict("records"),
                    columnDefs=column_definition,
                    columnSize="sizeToFit",
                    defaultColDef={"filter": True, "editable": True},
                    style={"height": "500px"},
                    dashGridOptions={
                        "rowSelection": "multiple",
                        "suppressRowClickSelection": True,
                        "pagination": True,
                    },
                ),
            ]
        )

        @callback(
            Output("comp-table", "rowData"),
            Input("comp-table", "cellValueChanged"),
            Input("btn-new-comp", "n_clicks"),
            Input("btn-del-comp", "n_clicks"),
            State("comp-table", "selectedRows"),
            prevent_initial_call=True,
        )
        def update_data(changed, n_clicks_new, n_clicks_del, selectedRows):
            if self._n_clicks_new_comp_ < n_clicks_new:
                self.new_component(comp_type, "new_comp_" + str(n_clicks_new))
                self._n_clicks_new_comp_ = n_clicks_new
            elif self._n_clicks_del_comp_ < n_clicks_del:
                for row in selectedRows:
                    self.del_component(self.component(row["name"]))
                self._n_clicks_del_comp_ = n_clicks_del
            else:
                if changed != None:
                    if changed[0]["colId"] == "name":
                        self.component(changed[0]["oldValue"]).parameter(
                            "name"
                        ).value = changed[0]["value"]
                    else:
                        self.component(changed[0]["data"]["name"]).parameter(
                            changed[0]["colId"]
                        ).value = changed[0]["value"]
            df_end = self.component_dataframe(comp_type=comp_type, string_format=True)
            return df_end.to_dict("records")

        editor.run(jupyter_height=600)

    def _load_buildings_3D(self, env_3D):
        building_list = self.component_list("Building")
        for building in building_list:
            building._create_building_3D(env_3D)

    def show_3D(self):
        env_3D = Environment_3D()
        self._load_buildings_3D(env_3D)
        env_3D.show(polygons_type="initial")
    
    def show_3D_shadows(self, date):
        env_3D = Environment_3D()
        self._load_buildings_3D(env_3D)
        file_met = self.parameter("simulation_file_met").component
        cos = file_met.sun_cosines(date)
        if len(cos) == 3:
            env_3D.calculate_shadows(cos)
            env_3D.show(polygons_type="Building_shadows")
        else:
            self._sim_.message(Message(date.strftime("%H:%M,  %d/%m/%Y") + " is night", "WARNING"))

    def show_3D_shadows_animation(self, date):
        env_3D = Environment_3D()
        self._load_buildings_3D(env_3D)
        file_met = self.parameter("simulation_file_met").component
        texts = []
        cosines = []
        for hour in range(24):
            new_date = date.replace(hour=hour, minute=0, second=0)
            cos = file_met.sun_cosines(new_date)
            if len(cos) == 3: # Day time
                texts.append(new_date.strftime("%H:%M,  %d/%m/%Y"))
                cosines.append(cos)
        env_3D.show_animation(texts, cosines, polygons_type="Building_shadows")

            