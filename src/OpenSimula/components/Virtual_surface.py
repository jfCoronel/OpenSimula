from OpenSimula.Message import Message
from OpenSimula.components.Surface import Surface
from OpenSimula.Parameters import Parameter_component_list
from OpenSimula.visual_3D.Polygon_3D import Polygon_3D


class Virtual_surface(Surface):
    def __init__(self, name, project):
        Surface.__init__(self, name, project)
        # Parameters
        self.parameter("type").value = "Virtual_surface"
        self.parameter("description").value = "Building virtual interior surface"
        self.add_parameter(
            Parameter_component_list("spaces", ["not_defined", "not_defined"])
        )

    def get_building(self):
        return self.parameter("spaces").component[0].get_building()

    def space(self, side=0):
        return self.parameter("spaces").component[side]

    def radiant_property(self, prop, radiation_type, side, theta=0):
        if prop == "tau":
            return 1
        else:
            return 0

    def check(self):
        errors = super().check()
        # Test spaces defined
        if (
            self.parameter("spaces").value[0] == "not_defined"
            or self.parameter("spaces").value[1] == "not_defined"
        ):
            msg = f"{self.parameter('name').value}, must define two spaces."
            errors.append(Message(msg, "ERROR"))
        return errors

    def get_polygon_3D(self):
        azimuth = self.orientation_angle("azimuth", 0, "global")
        altitude = self.orientation_angle("altitude", 0, "global")
        origin = self.get_origin("global")
        pol_2D = self.get_polygon_2D()
        name = self.parameter("name").value
        # holes_2D = []
        # for opening in self.openings:
        #    holes_2D.append(opening.get_polygon_2D())
        return Polygon_3D(
            name,
            origin,
            azimuth,
            altitude,
            pol_2D,
            color="red",
            opacity=0.4,
            shading=False,
            calculate_shadows=False,
        )
