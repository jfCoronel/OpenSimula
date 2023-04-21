from opensimula.Child import Child
from opensimula.parameters import Parameter_string

# ________________ Component __________________________


class Component(Child):
    """Objtects with paramaters and variables"""

    def __init__(self, parent=None):
        Child.__init__(self, parent)
        self._parameters = {}
        self._variables = {}
        self.add_parameter(Parameter_string("name", "Component_X"))

    def add_parameter(self, param):
        """add Parameter"""
        param.parent = self
        self._parameters[param.key] = param

    def del_parameter(self, param):
        """Deletet parameter"""
        self._parameters.remove(param)

    @property
    def parameter(self):
        return self._parameters

    @property
    def variable(self):
        return self._variables

    @property
    def simulation(self):
        return self.parent.parent

    def add_variable(self, variable):
        """add new Variable"""
        variable._parent = self
        self._variables[variable.name] = variable

    def del_variable(self, variable):
        self._variables.remove(variable)

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
