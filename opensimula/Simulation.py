from opensimula.utils import test_name_in_list

# Contiene la lista de los proyectos


class Simulation():
    version = '0.0.1'

    def __init__(self):
        self.projects = []
        pass

    def append(self, project):
        # Comprobar que no existe ningún proyecto con ese nombre
        new_name = test_name_in_list(project.name, self.projects)
        if (new_name != project.name):
            print(project.name, ' already exists, changed by: ', new_name)
            project.name = new_name
        # si existe modificarle el nombre
        self.projects.append(project)
