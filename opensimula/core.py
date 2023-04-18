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

# ___________________ Project __________________________________


class Project(Component):
    """Project is a Compoenent that contains a list of Components"""

    def __init__(self, sim):
        """Create new project in the sim Simulation"""
        Component.__init__(self, sim)
        sim.add_project(self)
        self._componentes = []
        self.parameter['name'].value = 'Project_X'

    def add_component(self, component):
        """Add component to the Project"""
        component.parent = self
        self._componentes.append(component)

    def del_component(self, component):
        self._componentes.remove(component)

    def find_component(self, name):
        for comp in self._componentes:
            if (comp.parameter['name'].value == name):
                return comp
        return None

    @property
    def component(self):
        return self._componentes

    @property
    def simulation(self):
        return self.parent

    def message(self, msg):
        """Function to print all the messages"""
        self.parent.message(msg)

# _________________ Simulation _______________________________


class Simulation():
    """Simulation contains a list of Projects"""
    version = '0.0.1'

    def __init__(self):
        """Simulation enviroment, contains a list of Projects"""
        self._proyectos = []

    def add_project(self, project):
        """Add project to Simulation"""
        project.parent = self
        self._proyectos.append(project)

    def del_project(self, project):
        self._proyectos.remove(project)

    def find_project(self, name):
        for pro in self._proyectos:
            if (pro.parameter['name'] == name):
                return pro
        return None

    @property
    def projects(self):
        return self._proyectos

    def message(self, msg):
        """Function to print all the messages"""
        print(str(msg))
