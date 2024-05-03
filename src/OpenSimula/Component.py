import pandas as pd
from OpenSimula.Parameter_container import Parameter_container
from OpenSimula.Parameters import Parameter_string
from OpenSimula.Variable import Variable


class Component(Parameter_container):
    """Base Class for all the components"""

    def __init__(self, name, proj):
        Parameter_container.__init__(self, proj._sim_)
        self._variables_ = {}
        self.add_parameter(Parameter_string("type", "Component"))
        self.parameter("name").value = name
        self.parameter("description").value = "Description of the component"
        proj._add_component_(self)
        self._project_ = proj

    def project(self):
        return self._project_

    def simulation(self):
        return self._sim_

    def print(self, msg):
        self._sim_.print(msg)

    def add_variable(self, variable):
        """add new Variable"""
        variable.parent = self
        variable._sim_ = self._sim_
        self._variables_[variable.key] = variable

    def del_variable(self, variable):
        self._variables_.remove(variable)

    def variable(self, key):
        return self._variables_[key]

    def variable_dict(self):
        return self._variables_

    def variable_dataframe(self, with_unit=True, frequency=None, value="mean"):
        """_summary_

        Args:
            with_unit (bool, optional): Includes unit in the name of the variable. Defaults to True.
            frequency (None or str, optional): frequency of the values: None, "H" Hour, "D" Day, "M" Month, "Y" Year . Defaults to None.
            value (str, optional): "mean", "sum", "max" or "min". Defaults to "mean".

        Returns:
            pandas DataFrame: Returns all the variables 
        """
        series = {}
        series["date"] = self.project().dates_array()
        for key, var in self._variables_.items():
            if var.unit == "":
                series[key] = var.values
            else:
                if with_unit:
                    series[key + " [" + var.unit + "]"] = var.values
                else:
                    series[key] = var.values
        data = pd.DataFrame(series)
        if frequency == None:
            return data
        else:
            if value == "mean":
                return data.resample(frequency, on='date').mean()
            elif value == "sum":
                return data.resample(frequency, on='date').sum()
            elif value == "max":
                return data.resample(frequency, on='date').max()
            elif value == "min":
                return data.resample(frequency, on='date').min()

    # ____________ Functions that must be overwriten for time simulation _________________

    def get_all_referenced_components(self):
        """Get list of all referenced components, first itself. Look recursively at the referenced components

        Returns:
            component_list (component[])
        """
        comp_list = []
        for key, value in self.parameter_dict().items():
            if value.type == "Parameter_component":
                if value.component is not None:
                    sublist = value.component.get_all_referenced_components()
                    for subcomp in sublist:
                        comp_list.append(subcomp)
            elif value.type == "Parameter_component_list":
                for comp in value.component:
                    if comp is not None:
                        sublist = comp.get_all_referenced_components()
                        for subcomp in sublist:
                            comp_list.append(subcomp)
            if value.type == "Parameter_variable":
                if value.variable is not None:
                    sublist = value.variable.parent.get_all_referenced_components()
                    for subcomp in sublist:
                        comp_list.append(subcomp)
            elif value.type == "Parameter_variable_list":
                for var in value.variable:
                    if var is not None:
                        sublist = var.parent.get_all_referenced_components()
                        for subcomp in sublist:
                            comp_list.append(subcomp)
        comp_list.append(self)
        return comp_list

    def check(self):
        """Check if all is correct

        Returns:
            errors (string list): List of errors
        """
        errors = []
        # Parameter errors
        for key, value in self.parameter_dict().items():
            param_error = value.check()
            for e in param_error:
                errors.append(e)
            # Create variables in paramater_variable
            if value.type == "Parameter_variable":
                if value.variable is not None:
                    self.add_variable(
                        Variable(value.symbol, value.variable.unit))
            if value.type == "Parameter_variable_list":
                for i in range(len(value.variable)):
                    if value.variable[i] is not None:
                        self.add_variable(
                            Variable(value.symbol[i], value.variable[i].unit))

        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        # Initilise all variables to 0
        for key, var in self._variables_.items():
            var.initialise(n_time_steps)

    def post_simulation(self):
        pass

    def pre_iteration(self, time_index, date, daylight_saving):
        # Initilise all variables to 0
        for key, value in self.parameter_dict().items():
            # Copy variables in paramater_variable
            if value.type == "Parameter_variable":
                if value.variable is not None:
                    self.variable(
                        value.symbol).values[time_index] = value.variable.values[time_index]
            if value.type == "Parameter_variable_list":
                for i in range(len(value.variable)):
                    if value.variable[i] is not None:
                        self.variable(
                            value.symbol[i]).values[time_index] = value.variable[i].values[time_index]

    def iteration(self, time_index, date, daylight_saving):
        return True

    def post_iteration(self, time_index, date, daylight_saving, converged):
        pass

    def _repr_html_(self):
        html = f"<h3>Component: {self.parameter('name').value}</h3><p>{self.parameter('description').value}</p>"
        html += "<strong>Parameters:</strong>"
        html += self.parameter_dataframe().to_html()
        if (len(self._variables_) > 0):
            html += "<br/><strong>Variables:</strong>"
            html += self.variable_dataframe().head(10).to_html()
        return html
