import json
from opensimula.Component import Component
from opensimula.components import *


class Project(Component):
    """Project is a Compenent that contains a list of Components"""

    def __init__(self, sim):
        """Create new project in the sim Simulation"""
        Component.__init__(self, sim)
        self.parameter["type"].value = "Project"
        sim.add_project(self)
        self._components_ = []
        self.parameter['name'].value = 'Project_X'

    def add_component(self, component):
        """Add component to the Project"""
        component.parent = self
        self._components_.append(component)

    def del_component(self, component):
        self._components_.remove(component)

    def find_component(self, name):
        for comp in self._components_:
            if (comp.parameter['name'].value == name):
                return comp
        return None

    @property
    def component(self):
        return self._components_

    @property
    def simulation(self):
        """
        Returns:
            Simulation: Simulation environment 
        """
        return self.parent

    @property
    def project(self):
        return self

    def info(self):
        """Print project information 
        """
        self.message("Project info: ")
        self.message("   Parameters:")
        for key, param in self.parameter.items():
            self.message("       "+param.info())
        self.message("   Components number: "+str(len(self._components_)))

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

    def read_json(self, json_file):
        """Read paramaters an components from json file"""
        try:
            f = open(json_file, "r")
        except OSError:
            self.message("Error: Could not open/read file: " +
                         json_file)
            return False
        with f:
            json_dict = json.load(f)
            self.load_from_json(json_dict)

    def check(self):
        """Check if all is correct, for all its components

        Returns:
            int: Number of errors
        """
        names = []
        n_errors = 0
        for comp in self.component:
            error_comp = comp.check()
            n_errors += error_comp
            if comp.parameter["name"].value in names:
                self.message("Error in project: "+self.parameter["name"].value)
                self.message(
                "   "+comp.parameter["name"].value + " is used by other component as name")
                n_errors += 1
            else:
                names.append(comp.parameter["name"].value)
            
        return n_errors
