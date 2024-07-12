from OpenSimula.components.Surface import Surface
from OpenSimula.Parameters import Parameter_component
from OpenSimula.Variable import Variable


class Shadow_surface(Surface):
    def __init__(self, name, project):
        Surface.__init__(self, name, project)
        # Parameters
        self.parameter("type").value = "Shadow_surface"
        self.parameter("description").value = "Building shadow surface"

        # Variables

    def check(self):
        errors = super().check()

        return errors
