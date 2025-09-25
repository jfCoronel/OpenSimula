from OpenSimula.Message import Message
from OpenSimula.components.Surface import Surface
from OpenSimula.Parameters import Parameter_component
from OpenSimula.visual_3D.Polygon_3D import Polygon_3D


class Shadow_surface(Surface):
    def __init__(self, name, project):
        Surface.__init__(self, name, project)
        # Parameters
        self.parameter("type").value = "Shadow_surface"
        self.parameter("description").value = "Building shadow surface"
        self.add_parameter(Parameter_component("building", "not_defined", ["Building"]))

        # Variables

    def check(self):
        errors = super().check()
        # Test building is defined
        if self.parameter("building").value == "not_defined":
            msg = f"{self.parameter('name').value}, must define its building."
            errors.append(Message(msg, "ERROR"))
        return errors

    def building(self):
        return self.parameter("building").component

    def get_polygon_3D(self):
        azimuth = self.orientation_angle("azimuth", 0, "global")
        altitude = self.orientation_angle("altitude", 0, "global")
        origin = self.get_origin("global")
        pol_2D = self.get_polygon_2D()
        name = self.parameter("name").value
        return Polygon_3D(
            name,
            origin,
            azimuth,
            altitude,
            pol_2D,
            color="cyan",
            calculate_shadows=False,
        )
