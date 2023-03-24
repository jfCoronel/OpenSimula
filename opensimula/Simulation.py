from opensimula.utils import print_message
from opensimula.Project import Project

# Contiene la lista de los proyectos


class Simulation():
    version = '0.0.1'

    def __init__(self):
        self._proyectos = []
        pass

    def append(self, project):
        # Comprobar que no existe ningún proyecto con ese nombre
        # new_name = test_name_in_list(project.name, self.projects)
        # Todas las comprobaciones en la función check
        
        # Solo comprobar que el objeto es del tipo project
        if (type(project) is Project):
            self._proyectos.append(project)
        else:
            print_message(str(project) + " is not a Project, it can't be added to simulation.")

