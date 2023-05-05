import pandas as pd
from opensimula.Child import Child
from opensimula.parameters import Parameter_string

# ________________ Component __________________________


class Component(Child):
    """Objtects with paramaters and variables"""

    def __init__(self, parent=None):
        Child.__init__(self, parent)
        self._parameters_ = {}
        self._variables_ = {}
        self.add_parameter(Parameter_string("type", "Component"))
        self.add_parameter(Parameter_string("name", "Component_X"))

    def add_parameter(self, param):
        """add Parameter"""
        param.parent = self
        self._parameters_[param.key] = param

    def del_parameter(self, param):
        """Deletet parameter"""
        self._parameters_.remove(param)

    @property
    def parameter(self):
        return self._parameters_

    @property
    def variable(self):
        return self._variables_

    @property
    def simulation(self):
        """
        Returns:
            Simulation: Simulation environment
        """
        return self.parent.parent

    @property
    def project(self):
        return self.parent

    def add_variable(self, variable):
        """add new Variable"""
        variable._parent = self
        self._variables_[variable.key] = variable

    def del_variable(self, variable):
        self._variables_.remove(variable)

    def variables_dataframe(self):
        series = {"dates": self.project.dates_array()}
        for key, var in self.variable.items():
            series[key] = var.array
        data = pd.DataFrame(series)
        return data

    def set_parameters(self, dictonary):
        """Read parameters from dictonary"""
        for key, value in dictonary.items():
            self.parameter[key].value = value

    def parameters_dataframe(self):
        keys = []
        values = []
        for key, par in self.parameter.items():
            keys.append(key)
            values.append(par.value)
        data = pd.DataFrame({"key": keys, "value": values})
        return data

    def info(self):
        """Print component information"""
        self.message("Component info: ")
        self.message("   Parameters:")
        for key, param in self.parameter.items():
            self.message("      " + param.info())

    def message(self, msg):
        """Function to print all the messages"""
        self.parent.parent.message(msg)

    # ____________ Functions that must be overwriten for time simulation _________________
    def check(self):
        """Check if all is correct

        Returns:
            int: Number of errors
        """
        return 0

    def pre_simulation(self, n_time_steps):
        pass

    def post_simulation(self):
        pass

    def pre_iteration(self, time_index, date):
        pass

    def iteration(self, time_index, date):
        return True

    def post_iteration(self, time_index, date):
        pass
