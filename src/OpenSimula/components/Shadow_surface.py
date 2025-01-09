from OpenSimula.components.Surface import Surface
from OpenSimula.Parameters import Parameter_component

class Shadow_surface(Surface):
    def __init__(self, name, project):
        Surface.__init__(self, name, project)
        # Parameters
        self.parameter("type").value = "Shadow_surface"
        self.parameter("description").value = "Building shadow surface"
        self.add_parameter(Parameter_component(
            "building", "not_defined", ["Building"]))

        # Variables

    def check(self):
        errors = super().check()
        # Test building is defined
        if self.parameter("building").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, must define its building.")
        return errors

    def building(self):
        return self.parameter("building").component
