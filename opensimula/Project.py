from opensimula.Component import Component
from opensimula.components import *


class Project(Component):
    """Project is a Compoenent that contains a list of Components"""

    def __init__(self, sim):
        """Create new project in the sim Simulation"""
        Component.__init__(self, sim)
        self.parameter["type"].value = "Project"
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

    def new_component(self, type):
        clase = globals()[type]
        comp = clase()
        self.add_component(comp)
        return comp

    def load_from_json(self, json):
        """Create paramaters an components from json dictionary"""
        for key, value in json.items():
            if (key == "components"):  # Lista de compoenentes
                for component in value:
                    comp = self.new_component(component["type"])
                    comp.set_parameters(component)
            else:   # Debe ser un parámetro
                self.parameter[key].value = value
