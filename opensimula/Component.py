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
        return self.parent.parent

    def add_variable(self, variable):
        """add new Variable"""
        variable._parent = self
        self._variables_[variable.name] = variable

    def del_variable(self, variable):
        self._variables_.remove(variable)

    def set_parameters(self, dictonary):
        """Read parameters from dictonary"""
        for key, value in dictonary.items():
            self.parameter[key].value = value

    def info(self):
        self.message(type(self).__name__ + ": ")
        for key, param in self.parameter.items():
            self.message("p-> "+param.info())

    def message(self, msg):
        """Function to print all the messages"""
        self.parent.parent.message(msg)

    def check(self):
        """Component check if all is correct"""
        return(True)
