import pandas as pd
from opensimula.Parameters import Parameter_string
from opensimula.Message import Message

class Parameter_container:
    """Class to manage a list of Parameters

    Superclass for Projects and Components

    Default parameters included:

    - name (string)
    - description (string)
    """

    def __init__(self, sim):
        """Create the container with the parameters name and description

        Args:
            sim (Simulation): simulation environment, used to report messages
        """
        self._sim_ = sim
        self._parameters_ = {}
        self.add_parameter(Parameter_string("name", "Name"))
        self.add_parameter(Parameter_string("description", "Description"))

    def add_parameter(self, param):
        """Add a parameter

        Args:
            param (Parameter): parameter to add, replaces any parameter with the same key
        """
        param.parent = self
        param._sim_ = self._sim_
        self._parameters_[param.key] = param

    def del_parameter(self, param):
        """Delete a parameter

        Args:
            param (Parameter): parameter to delete
        """
        self._parameters_.pop(param.key, None)

    def parameter(self, key):
        """Find and return a parameter using its key

        Args:
            key (str): key of the parameter, e.g. "name"

        Returns:
            Parameter: the parameter (KeyError if it does not exist); read or change its
                value with `.value`
        """
        return self._parameters_[key]

    def parameter_dict(self):
        """Parameters of the container

        Returns:
            dict: {key: Parameter}
        """
        return self._parameters_

    def set_parameters(self, dictonary):
        """Set parameter values from a dictionary

        Args:
            dictonary (dict): {key: value}; unknown keys are reported as errors
        """
        for key, value in dictonary.items():
            if key in self._parameters_:
                self.parameter(key).value = value
            else:
                self._sim_.message(Message("Component parameter " + key + " does not exist","ERROR"))

    def parameter_dataframe(self, string_format=False):
        """Parameters as a table

        Args:
            string_format (bool, optional): Convert every value to string. Defaults to False.

        Returns:
            pandas.DataFrame: key, type, value and unit of each parameter
        """
        keys = []
        values = []
        types = []
        units = []
        for key, par in self._parameters_.items():
            keys.append(key)
            if string_format:
                values.append(str(par.value))
            else:
                values.append(par.value)
            types.append(par.type)
            if hasattr(par, "unit"):
                units.append(par.unit)
            else:
                units.append("")

        data = pd.DataFrame(
            {"key": keys, "type": types, "value": values, "unit": units}
        )
        return data

    def check_parameters(self):
        """Check if all is correct

        Returns:
            list of Message: errors found
        """
        errors = []
        for key, value in self._parameters_.items():
            param_error = value.check()
            if len(param_error) > 1:
                for e in param_error:
                    errors.append(e)
        return errors
