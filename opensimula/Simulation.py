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
