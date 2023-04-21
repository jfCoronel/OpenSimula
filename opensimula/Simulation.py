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
