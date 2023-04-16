class Child():
    """Objects with parent an name"""

    def __init__(self, name, parent=None):
        self._parent = parent
        self._name = name

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, parent):
        self._parent = parent

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name


class Component(Child):
    def __init__(self, name="Component x", parent=None):
        Child.__init__(self, name, parent)
        self._parameters = {}
        self._variables = {}

    def add_parameter(self, param):
        """add Property"""
        param.parent = self
        self._parameters[param.name] = param

    def del_parameter(self, param):
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

    def set(self, dictonary):
        """Read parameters from dictonary"""
        for key, value in dictonary.items():
            self.parameter[key].value = value

    def info(self):
        self.message(type(self).__name__ + ": " + self.name)
        for key, param in self.parameter.items():
            self.message("p-> "+param.info())

    def message(self, msg):
        """Function to print all the messages"""
        self.parent.parent.message(msg)


class Project(Component):
    """Project contains a list of Components"""

    def __init__(self, name, sim):
        """Create new project in the sim Simulation"""
        Component.__init__(self, name, sim)
        sim.add_project(self)
        self._componentes = []

    def add_component(self, component):
        """Add component to the Project"""
        component.parent = self
        self._componentes.append(component)

    def del_component(self, component):
        self._componentes.remove(component)

    def find_component(self, name):
        for comp in self._componentes:
            if (comp.name == name):
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
            if (pro.name == name):
                return pro
        return None

    @property
    def projects(self):
        return self._proyectos

    def message(self, msg):
        """Function to print all the messages"""
        print(str(msg))


class Parameter(Child):
    def __init__(self, name, value=0):
        Child.__init__(self, name)
        self._value = value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    def info(self):
        return self.name + ": " + str(self.value)


class Variable(Child):
    def __init__(self, name):
        Child.__init__(self, name)
