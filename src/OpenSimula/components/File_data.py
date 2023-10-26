import pandas as pd
from OpenSimula.Parameters import Parameter_string, Parameter_options
from OpenSimula.Component import Component
from OpenSimula.Variable import Variable


class File_data(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "File_data"
        self.parameter("description").value = "Data file with varables"
        self.add_parameter(Parameter_string("file_name", "data.csv"))
        self.add_parameter(Parameter_options("file_type", "CSV", ["CSV", "EXCEL"]))
        self._df_ = pd.DataFrame()

    def check(self):
        errors = super().check()
        # Read the file
        try:
            if self.parameter("file_type").value == "CSV":
                self._df_ = pd.read_csv(self.parameter("file_name").value)
            elif self.parameter("file_type").value == "EXCEL":
                self._df_ = pd.read_excel(self.parameter("file_name").value)
            return errors

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
        self.del_all_variables()
        # Create Variable
        array = self._df_.to_numpy()
        for col in self._df_.columns:
            self.add_variable(
                Variable(
                    self._extract_name_(col),
                    n_time_steps,
                    unit=self._extract_unit_(col),
                )
            )

        i = 0
        k = 0
        n = len(self._df_)
        for key, var in self._variables_.items():
            for j in range(n_time_steps):
                var.array[j] = array[k][i]
                k = k + 1
                if k == n:
                    k = 0
            i = i + 1

    def _extract_name_(self, name):
        return name[0 : name.rfind("[")].strip()

    def _extract_unit_(self, name):
        if name.rfind("[") == -1:
            return ""
        else:
            return name[name.rfind("[") + 1 : name.rfind("]")].strip()
