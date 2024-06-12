import pandas as pd
from OpenSimula.Parameters import Parameter_string


class Parameter_container:
    """Class to manage a list of Paramaters

    Superclass for Projects and Components

    Default parameters included:
    - name (string)
    - description (string)

    """

    def __init__(self, sim):
        self._sim_ = sim
        self._parameters_ = {}
        self.add_parameter(Parameter_string("name", "Name"))
        self.add_parameter(Parameter_string("description", "Description"))

    def add_parameter(self, param):
        """add Parameter"""
        param.parent = self
        param._sim_ = self._sim_
        self._parameters_[param.key] = param

    def del_parameter(self, param):
        """Deletet parameter"""
        self._parameters_.remove(param)

    def parameter(self, key):
        return self._parameters_[key]

    def parameter_dict(self):
        return self._parameters_

    def set_parameters(self, dictonary):
        """Read parameters from dictonary"""
        for key, value in dictonary.items():
            if key in self._parameters_:
                self.parameter(key).value = value
            else:
                self._sim_.print(
                    "Error: Component parameter " + key + " does not exist"
                )

    def parameter_dataframe(self, string_format=False):
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
            errors (string list): List of errors
        """
        errors = []
        for key, value in self._parameters_.items():
            param_error = value.check()
            if len(param_error) > 1:
                for e in param_error:
                    errors.append(e)
        return errors
