import pandas as pd

class Variable_container():
    """Class to manage a list of Variables
    
    Superclass for Projects and Components
    
    """
    
    def __init__(self):
        self._variables_ = {}
        
    def add_variable(self, variable):
        """add new Variable"""
        variable._parent = self
        self._variables_[variable.key] = variable

    def del_variable(self, variable):
        self._variables_.remove(variable)

    def del_all_variables(self):
        self._variables_ = {}

    def variable(self, key):
        return self._variables_[key]
    
    def variable_dict(self):
        return self._variables_

    def variables_dataframe(self):
        series = {}
        for key, var in self._variables_.items():
            series[key] = var.array
        data = pd.DataFrame(series)
        return data