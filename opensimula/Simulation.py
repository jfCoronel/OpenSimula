from opensimula.utils import print_message
from opensimula.Project import Project

# Contiene la lista de los proyectos


class Simulation():
    version = '0.0.1'

    def __init__(self):
        """Simulation enviroment, contains a list of Projects"""
        self._proyectos = []
        pass

    def append(self, project):
        """Append new project to Simulation"""
        # Solo comprobar que el objeto es del tipo project
        if (type(project) is Project):
            self._proyectos.append(project)
        else:
            print_message(str(project) + " is not a Project, it can't be added to simulation.")


    def remove(self, project):
        self._proyectos.remove(project)

