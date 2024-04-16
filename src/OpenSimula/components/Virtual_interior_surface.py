from OpenSimula.components.Virtual_surface import Virtual_surface
from OpenSimula.Parameters import Parameter_component_list


class Virtual_interior_surface(Virtual_surface):
    def __init__(self, name, project):
        Virtual_surface.__init__(self, name, project)
        # Parameters
        self.parameter("type").value = "Virtual_interior_surface"
        self.parameter(
            "description").value = "Building virtual interior surface"
        self.add_parameter(Parameter_component_list(
            "spaces", ["not_defined", "not_defined"]))

    def building(self):
        return self.parameter("spaces").component[0].building()

    def space(self, side=0):
        return self.parameter("spaces").component[side]

    def check(self):
        errors = super().check()
        # Test spaces defined
        if self.parameter("spaces").value[0] == "not_defined" or self.parameter("spaces").value[1] == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, must define two spaces.")
        return errors
