from OpenSimula.components.Surface import Surface
from OpenSimula.Parameters import Parameter_component, Parameter_float, Parameter_boolean
from OpenSimula.Variable import Variable


class Virtual_surface(Surface):
    def __init__(self, name, project):
        Surface.__init__(self, name, project)
        # Parameters
        self.parameter("type").value = "Virtual_surface"

        # Variables

    def radiant_property(self, prop, radiation_type, side, theta=0):
        if (prop == "tau"):
            return 1
        else:
            return 0

    def isVirtual(self):
        return True
