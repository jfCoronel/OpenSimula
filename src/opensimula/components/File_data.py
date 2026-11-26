import pandas as pd
import datetime as dt
import numpy as np
import math
import re
from opensimula.Message import Message
from opensimula.Parameters import Parameter_string, Parameter_options, Parameter_int
from opensimula.Component import Component
from opensimula.Variable import Variable


class File_data(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "File_data"
        self.parameter("description").value = "Data file with varables"
        self.add_parameter(Parameter_string("file_name", "data.csv"))
        self.add_parameter(Parameter_options(
            "file_type", "CSV", ["CSV", "EXCEL"]))
        # SIMULATION: row i is time step i of the simulation; ANNUAL: the rows are the
        # time steps of a year from 1 January 00:00, read by the date of each step;
        # OWN: rows from initial_time every time_step, interpolated
        self.add_parameter(Parameter_options(
            "file_step", "SIMULATION", ["SIMULATION", "ANNUAL", "OWN"]))
        self.add_parameter(Parameter_string(
            "initial_time", "01/01/2001 00:00:00"))
        self.add_parameter(Parameter_int("time_step", 3600, "s", min=1))
        self._df_ = pd.DataFrame()

    def check(self):
        errors = super().check()
        if self.parameter("file_step").value == "OWN":  # Check initial time
            try:
                dt.datetime.strptime(self.parameter("initial_time").value, "%d/%m/%Y %H:%M:%S")
            except ValueError:
                msg = f"Error in component: {self.parameter('name').value}, initial_time: {self.parameter('initial_time').value} does not match format (dd/mm/yyyy HH:MM:SS)"
                errors.append(Message(msg, "ERROR"))

        # Read the file
        try:
            if self.parameter("file_type").value == "CSV":
                self._df_ = pd.read_csv(self.parameter("file_name").value)
            elif self.parameter("file_type").value == "EXCEL":
                self._df_ = pd.read_excel(self.parameter("file_name").value)
            # Create Variable
            names = {}
            for col in self._df_.columns:
                if self._is_numeric_(col):
                    name = self._extract_name_(col)
                    if name in names:
                        msg = (f"Error in component: {self.parameter('name').value}, columns "
                               f"{names[name]!r} and {col!r} give the same variable {name!r}")
                        errors.append(Message(msg, "ERROR"))
                    names[name] = col
                    self.add_variable(Variable(name, unit=self._extract_unit_(col)))

        except Exception as ex:
            if type(ex).__name__ == "FileNotFoundError":
                msg = f"Error in component: {self.parameter('name').value}, No such file: {self.parameter('file_name').value}"
                errors.append(Message(msg, "ERROR"))
            else:
                msg = f"Error in component: {self.parameter('name').value}, error reading file: {self.parameter('file_name').value}"
                errors.append(Message(msg, "ERROR"))                
        if not errors and self.parameter("file_step").value == "SIMULATION":
            errors += self._check_annual_file()
        return errors

    def _check_annual_file(self):
        """Warning: a file of one year of rows read with SIMULATION by a simulation that
        does not start on 1 January (its rows would not match the dates)."""
        project = self.project()
        step = project.parameter("time_step").value
        try:
            start = dt.datetime.strptime(project.parameter("initial_time").value, "%d/%m/%Y %H:%M:%S")
        except ValueError:
            return []
        year = {365 * 86400 // step, 366 * 86400 // step}
        if len(self._df_) in year and (start.month, start.day, start.hour, start.minute) != (1, 1, 0, 0):
            msg = (f"Warning: {self.parameter('name').value}, the file has a year of rows but the "
                   f"simulation starts on {start:%d/%m}: with file_step \"SIMULATION\" its first "
                   "row is read for the first time step. Use \"ANNUAL\" if the rows start on "
                   "1 January.")
            return [Message(msg, "WARNING")]
        return []

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)

        self.data_array = self._df_.select_dtypes(include=np.number).to_numpy()

        if self.parameter("file_step").value == "SIMULATION":
            # one row per time step, from the first row of the file for every column,
            # starting again from the first row if the file is shorter than the simulation
            n = len(self._df_)
            for i, var in enumerate(self._variables_.values()):
                for j in range(n_time_steps):
                    var.values[j] = self.data_array[j % n][i]
        elif self.parameter("file_step").value == "OWN":
            n = len(self._df_)
            self._initial_date_ = dt.datetime.strptime(
                self.parameter("initial_time").value, "%d/%m/%Y %H:%M:%S")
            delta_t = self.parameter("time_step").value
            date = self._initial_date_
            self.dates = np.empty(n, dtype=object)
            for i in range(n):
                self.dates[i] = date
                date = date + dt.timedelta(0, delta_t)

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        if self.parameter("file_step").value == "ANNUAL":
            # the row of the date: time steps of the file from 1 January 00:00 of its year
            seconds = (date - dt.datetime(date.year, 1, 1)).total_seconds()
            row = int(seconds // self.parameter("time_step").value) % len(self._df_)
            for k, var in enumerate(self._variables_.values()):
                var.values[time_index] = self.data_array[row][k]
        elif self.parameter("file_step").value == "OWN":
            i, j, f = self._get_interpolation_tuple_(date)
            k = 0
            for key, var in self._variables_.items():
                var.values[time_index] = self.data_array[i][k] * \
                    (1 - f) + self.data_array[j][k] * f
                k = k + 1

    def _extract_name_(self, name):
        """Name of the variable of a column "name [unit]": the characters that cannot be
        in the name of a variable (dots, spaces...) become "_", so that the columns of
        the CSV of the results viewer ("office.system_sensible_heat [W]") can be used in
        input_variables ("load_record.office_system_sensible_heat")."""
        if name.rfind("[") != -1:
            name = name[0: name.rfind("[")]
        return re.sub(r"[^0-9A-Za-z_]+", "_", name.strip()).strip("_")

    def _extract_unit_(self, name):
        if name.rfind("[") == -1:
            return ""
        else:
            return name[name.rfind("[") + 1: name.rfind("]")].strip()
    
    def _is_numeric_(self, name):
        return pd.api.types.is_numeric_dtype(self._df_[name])

    def _get_interpolation_tuple_(self, date):
        seconds = (date-self._initial_date_).total_seconds()
        index = seconds / self.parameter("time_step").value
        n = len(self._df_)
        if index < 0:
            index = 0
        elif index >= n:
            index = n-1
        i = math.floor(index)
        j = i + 1
        if j >= n:
            j = n-1
        f = index - i
        return (i, j, f)
