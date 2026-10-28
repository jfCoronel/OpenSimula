import pandas as pd
from opensimula.Parameter_container import Parameter_container
from opensimula.Parameters import Parameter_string
from opensimula.Variable import Variable


class Component(Parameter_container):
    """Base Class for all the components

    A component has parameters (inherited from Parameter_container, with `name`,
    `description` and `type`) and variables (time series filled during the simulation).
    Components are created by the project (`Project.new_component()`, `read_dict()`,
    `read_json()`), not directly.

    New component types inherit from this class: they add their parameters and variables
    in `__init__()`, validate them in `check()` and override the simulation methods
    (`pre_simulation()`, `pre_iteration()`, `iteration()`, `post_iteration()`,
    `post_simulation()`) that the project calls in this order. See the developer guide.
    """

    def __init__(self, name, proj):
        """Create new component

        Args:
            name (str): name of the component
            proj (Project): project the component belongs to
        """
        Parameter_container.__init__(self, proj._sim_)
        self._variables_ = {}
        self.add_parameter(Parameter_string("type", "Component"))
        self.parameter("name").value = name
        self.parameter("description").value = "Description of the component"
        self._project_ = proj

    def project(self):
        """Project the component belongs to

        Returns:
            Project: parent project
        """
        return self._project_

    def add_variable(self, variable):
        """Add a new variable to the component

        Args:
            variable (Variable): variable to add, replaces any variable with the same key
        """
        variable.parent = self
        variable._sim_ = self._sim_
        self._variables_[variable.key] = variable

    def del_variable(self, variable):
        """Remove a variable from the component

        Args:
            variable (Variable): variable to remove
        """
        self._variables_.pop(variable.key,None)

    def variable(self, key):
        """Find and return a variable using its key

        Args:
            key (str): key of the variable, e.g. "temperature"

        Returns:
            Variable: the variable (KeyError if it does not exist)
        """
        return self._variables_[key]

    def variable_dict(self):
        """Variables of the component

        Returns:
            dict: {key: Variable}
        """
        return self._variables_

    def variable_dataframe(self, units=False, frequency=None, value="mean", interval=None, pos_neg_columns=[]):
        """Variables of the component as a table

        Args:
            units (bool, optional): Includes unit in the name of the variable. Defaults to False.
            frequency (None or str, optional): frequency of the values: None, "hourly", "daily", "monthly", "yearly". Defaults to None.
            value (str, optional): "mean", "sum", "sum_pos", "sum_neg", "max" or "min". Defaults to "mean".
            interval (None or list of two dates): List with the start and end dates of the period to be included in the dataframe, if the value is None all values are included.
            pos_neg_columns (list of str, optional): List of variables that will be included in separate columns positive and negative values. Defaults to [].

        Returns:
            pandas.DataFrame: column "date" and one column per variable
        """
        series = {}
        series["date"] = self.project().dates()
        for key, var in self._variables_.items():
            if var.unit == "":
                series[key] = var.values
            else:
                if units:
                    series[key + " [" + var.unit + "]"] = var.values
                else:
                    series[key] = var.values
        data = pd.DataFrame(series)
        if pos_neg_columns != []:
            for col in pos_neg_columns:
                data[col + "_pos"] = data[col].apply(lambda x: x if x > 0 else 0)
                data[col + "_neg"] = data[col].apply(lambda x: x if x < 0 else 0)
        if frequency is not None:
            freq={"hourly": "h", "daily": "D", "monthly": "ME", "yearly": "YE"}
            if value == "mean":
                data = data.resample(freq[frequency], on='date').mean()
            elif value == "sum":
                data = data.resample(freq[frequency], on='date').sum()
            elif value == "sum_pos":
                data = data.resample(freq[frequency], on='date').apply(lambda x: x.clip(lower=0).sum())
            elif value == "sum_neg":
                data = data.resample(freq[frequency], on='date').apply(lambda x: x.clip(upper=0).sum())
            elif value == "max":
                data = data.resample(freq[frequency], on='date').max()
            elif value == "min":
                data = data.resample(freq[frequency], on='date').min()
        if interval is not None:
            data = data[(data['date'] > interval[0]) &
                        (data['date'] < interval[1])]
        return data

    # ____________ Functions that must be overwriten for time simulation _________________

    def get_all_referenced_components(self, _seen=None):
        """Get list of all referenced components, first itself. Look recursively at the referenced components

        Args:
            _seen (set, optional): components already walked, used internally.
                References can form a cycle, if only because a wrong name gets
                typed into a reference, and without remembering where it has
                been the walk follows it until the stack runs out.

        Returns:
            list of Component: referenced components and, last, the component itself
        """
        if _seen is None:
            _seen = set()
        if id(self) in _seen:
            return []
        _seen.add(id(self))

        comp_list = []

        def walk(component):
            if component is not None:
                comp_list.extend(component.get_all_referenced_components(_seen))

        for key, value in self.parameter_dict().items():
            if value.type == "Parameter_component":
                walk(value.component)
            elif value.type == "Parameter_component_list":
                for comp in value.component:
                    walk(comp)
            if value.type == "Parameter_variable":
                if value.variable is not None:
                    walk(value.variable.parent)
            elif value.type == "Parameter_variable_list":
                for var in value.variable:
                    if var is not None:
                        walk(var.parent)
        comp_list.append(self)
        return comp_list

    def check(self):
        """Check if all is correct

        Checks every parameter and creates the variables of the `Parameter_variable` and
        `Parameter_variable_list` parameters. Components that override it call this one
        first and add their own checks.

        Returns:
            list of Message: errors found
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
                    if (value.symbol in self._variables_):  # Delete
                        self.del_variable(self.variable(value.symbol))
                    self.add_variable(
                        Variable(value.symbol, value.variable.unit))
            if value.type == "Parameter_variable_list":
                for i in range(len(value.variable)):
                    if value.variable[i] is not None:
                        if (value.symbol[i] in self._variables_):  # Delete
                            self.del_variable(self.variable(value.symbol[i]))
                        self.add_variable(
                            Variable(value.symbol[i], value.variable[i].unit))

        return errors

    def get_parameter_variable_dictionary(self,time_index):
        """Values of the variables taken from `Parameter_variable` parameters at a time step

        Used to evaluate `Parameter_math_exp` expressions.

        Args:
            time_index (int): index of the time step

        Returns:
            dict: {symbol: value}
        """
        # variables dictonary
        var_dic = {}
        for i in range(len(self._var_from_parameter_symbol)):
            var_dic[self._var_from_parameter_symbol[i]] = self._var_from_parameter_variable[i].values[time_index]
        return var_dic

    def pre_simulation(self, n_time_steps, delta_t):
        """Prepare the component before the time loop of the simulation

        The base method sets up the variables of the `Parameter_variable` parameters and
        initialises every variable to zeros. Overriding methods call it first.

        Args:
            n_time_steps (int): number of time steps of the simulation
            delta_t (int): time step (s)
        """
        # Create variables from paramater "Parameter_variable" and "Parameter_variable_list"
        self._var_from_parameter_symbol = []
        self._var_from_parameter_variable = []
        for param in self.parameter_dict().values():
            if param.type == "Parameter_variable":
                self._var_from_parameter_symbol.append(param.symbol)
                self._var_from_parameter_variable.append(param.variable)
            elif param.type == "Parameter_variable_list":
                for i in range(len(param.variable)):
                    self._var_from_parameter_symbol.append(param.symbol[i])
                    self._var_from_parameter_variable.append(param.variable[i])

        # Initilise all variables to 0
        for key, var in self._variables_.items():
            var.initialise(n_time_steps)

    def post_simulation(self):
        """Finish the component after the time loop of the simulation"""
        pass

    def pre_iteration(self, time_index, date, daylight_saving):
        """Prepare the time step, before its iterations

        The base method copies the values of the `Parameter_variable` parameters at the
        time step. Overriding methods call it first.

        Args:
            time_index (int): index of the time step
            date (datetime): date of the time step (center of the interval)
            daylight_saving (bool): daylight saving time is in effect
        """
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

    def iteration(self, time_index, date, daylight_saving, n_iter):
        """Calculate one iteration of the time step

        The project repeats the iterations of every component until all of them return
        True or the maximum number of iterations is reached.

        Args:
            time_index (int): index of the time step
            date (datetime): date of the time step (center of the interval)
            daylight_saving (bool): daylight saving time is in effect
            n_iter (int): number of the iteration in the time step, from 0

        Returns:
            bool: the component has converged
        """
        return True

    def post_iteration(self, time_index, date, daylight_saving, converged):
        """Finish the time step, after its iterations

        Args:
            time_index (int): index of the time step
            date (datetime): date of the time step (center of the interval)
            daylight_saving (bool): daylight saving time is in effect
            converged (bool): every component converged in the time step
        """
        pass

    def _repr_html_(self):
        html = f"<h3>Component: {self.parameter('name').value}</h3><p><strong>Desciption: </strong>{self.parameter('description').value}</p>"
        html += "<strong>Parameters:</strong>"
        html += self.parameter_dataframe().to_html()
        if (len(self._variables_) > 0):
            html += "<br/><strong>Variables:</strong>"
            html += self.variable_html()
        return html

    def variable_html(self):
        """Key, description and unit of the variables as an HTML table

        Returns:
            str: HTML table
        """
        keys = []
        descriptions = []
        units = []
        for key, var in self._variables_.items():
            keys.append(key)
            descriptions.append(var.description)
            units.append(var.unit)

        data = pd.DataFrame(
            {"key": keys, "description": descriptions, "unit": units}
        )
        return data.to_html()

    def function_html(self):
        """Short HTML help of the component's table methods

        Returns:
            str: HTML text
        """
        html = "<p><strong>parameter_dataframe():</strong> Return pandas DataFrame with the component parametes.</p>"
        html += "<p><strong>variable_dataframe():</strong> Return pandas DataFrame with the component variables.</p>"
