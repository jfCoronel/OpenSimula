import pandas as pd
import datetime as dt
import numpy as np
import math
from OpenSimula.Parameters import Parameter_string, Parameter_options, Parameter_int
from OpenSimula.Component import Component
from OpenSimula.Variable import Variable


class File_data(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "File_data"
        self.parameter("description").value = "Data file with varables"
        self.add_parameter(Parameter_string("file_name", "data.csv"))
        self.add_parameter(Parameter_options(
            "file_type", "CSV", ["CSV", "EXCEL"]))
        self.add_parameter(Parameter_options(
            "file_step", "SIMULATION", ["SIMULATION", "OWN"]))
        self.add_parameter(Parameter_string(
            "initial_time", "01/01/2001 00:00:00"))
        self.add_parameter(Parameter_int("time_step", 3600, "s", min=1))
        self._df_ = pd.DataFrame()

    def check(self):
        errors = super().check()
        if self.parameter("file_step").value == "OWN":  # Check initial time
            try:
                dt.datetime.strptime(self.parameter(
                    "initial_time").value, "%d/%m/%Y %H:%M:%S")
            except ValueError:
                error = f"Error in component: {self.parameter('name').value}, initial_time: {self.parameter('initial_time').value} does not match format (dd/mm/yyyy HH:MM:SS)"
                errors.append(error)

        # Read the file
        try:
            if self.parameter("file_type").value == "CSV":
                self._df_ = pd.read_csv(self.parameter("file_name").value)
            elif self.parameter("file_type").value == "EXCEL":
                self._df_ = pd.read_excel(self.parameter("file_name").value)
            # Create Variable
            for col in self._df_.columns:
                self.add_variable(Variable(self._extract_name_(
                    col), unit=self._extract_unit_(col)))

        except Exception as ex:
            if type(ex).__name__ == "FileNotFoundError":
                errors.append(
                    f"Error in component: {self.parameter('name').value}, No such file: {self.parameter('file_name').value}"
                )
            else:
                errors.append(
                    f"Error in component: {self.parameter('name').value}, error reading file: {self.parameter('file_name').value}"
                )
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)

        self.data_array = self._df_.to_numpy()

        if self.parameter("file_step").value == "SIMULATION":
            i = 0
            k = 0
            n = len(self._df_)
            for key, var in self._variables_.items():
                for j in range(n_time_steps):
                    var.values[j] = self.data_array[k][i]
                    k = k + 1
                    if k == n:
                        k = 0
                i = i + 1
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
        if self.parameter("file_step").value == "OWN":
            i, j, f = self._get_interpolation_tuple_(date)
            k = 0
            for key, var in self._variables_.items():
                var.values[time_index] = self.data_array[i][k] * \
                    (1 - f) + self.data_array[j][k] * f
                k = k + 1

    def _extract_name_(self, name):
        if name.rfind("[") == -1:
            return name
        else:
            return name[0: name.rfind("[")].strip()

    def _extract_unit_(self, name):
        if name.rfind("[") == -1:
            return ""
        else:
            return name[name.rfind("[") + 1: name.rfind("]")].strip()

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
