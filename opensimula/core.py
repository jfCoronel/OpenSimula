from .base import Child
from .parameters import Parameter_string


class Component(Child):
    def __init__(self):
        Child.__init__(self)
        self._parameters = {}
        self._variables = {}
        self.addParameter(Parameter_string("name", "Component_x"))

    def addParameter(self, param):
        """add Property"""
        param._parent = self
        self._parameters[param.name] = param

    def delParameter(self, param):
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

    def addVariable(self, variable):
        """add new Variable"""
        variable._parent = self
        self._variables[variable.name] = variable

    def delVariable(self, variable):
        self._variables.remove(variable)

    def info(self):
        self.simulation.message(type(self).__name__ + ": ")
        for key, param in self.parameter.items():
            self.simulation.message(param.info())


class Project(Component):
    """Project contains a list of Components"""

    def __init__(self):
        Component.__init__(self)
        self.parameter['name'].value = 'Project_x'
        self._componentes = []

    def addComponent(self, component):
        """Add component to the Project"""
        component._parent = self
        self._componentes.append(component)

    def delComponent(self, component):
        self._componentes.remove(component)

    @property
    def component(self):
        return self._componentes

    @property
    def simulation(self):
        return self.parent


class Simulation():
    """Simulation contains a list of Projects"""
    version = '0.0.1'

    def __init__(self):
        """Simulation enviroment, contains a list of Projects"""
        self._proyectos = []

    def addProject(self, project):
        """Add project to Simulation"""
        project._parent = self
        self._proyectos.append(project)

    def delProject(self, project):
        self._proyectos.remove(project)

    @property
    def project(self):
        return self._proyectos

    def message(self, msg):
        """Function to print all the messages"""
        print(str(msg))
