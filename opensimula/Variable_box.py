class Variable_box:
    def __init__(self):
        self._variables = {}

    def addVariable(self, variable):
        """add new Variable"""
        variable._parent = self
        self._variables[variable.name] = variable

    def delVariable(self, variable):
        self._variables.remove(variable)

    @property
    def variable(self):
        return self._variables
