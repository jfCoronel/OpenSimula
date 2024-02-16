from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_component, Parameter_float, Parameter_boolean
from OpenSimula.Variable import Variable


class Surface(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        # Parameters
        self.parameter("type").value = "Surface"
        self.parameter("description").value = "Building surface"
        self.add_parameter(Parameter_float("area", 1, "m²", min=0.0))
        self.add_parameter(Parameter_float(
            "azimuth", 0, "°", min=-180, max=180))  # S: 0º, E: 90º, W: -90º, N: 180º
        self.add_parameter(Parameter_float(
            "altitude", 0, "°", min=-90, max=90))  # vertical: 0º, facing up: 90º, facing down: -90º

    @property
    def area(self):
        return self.parameter("area").value

    def orientation_angle(self, angle, side):
        if angle == "azimuth":
            az = self.parameter("azimuth").value
            if side == 0:
                return az
            elif side == 1:
                if az > 0:
                    return az-180
                else:
                    return az+180
        elif angle == "altitude":
            alt = self.parameter("altitude").value
            if side == 0:
                return alt
            elif side == 1:
                return -alt

    def radiant_property(self, prop, radiation_type, side, theta=0):
        """It maus be redefined by child classes

        Args:
            prop (_type_): _description_
            radiation_type (_type_): _description_
            side (_type_): _description_

        Returns:
            _type_: _description_
        """
        return 0

    def isVirtual(self):
        return False
