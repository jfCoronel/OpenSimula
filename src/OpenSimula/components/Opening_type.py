from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_float, Parameter_component


class Opening_type(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Opening_type"
        self.parameter(
            "description").value = "Window or doors with glazing, construction, frame and shading."

        self.add_parameter(Parameter_component(
            "glazing", "not_defined", "Glazing"))
        self.add_parameter(Parameter_component(
            "frame", "not_defined", "Frame"))
        self.add_parameter(Parameter_component(
            "construction", "not_defined", "Construction"))
        self.add_parameter(Parameter_float(
            "glazing_fraction", 0.9, "frac", min=0, max=1))
        self.add_parameter(Parameter_float(
            "frame_fraction", 0.1, "frac", min=0, max=1))

    def check(self):
        errors = super().check()
        # Test glazing defined
        if self.parameter("glazing").value == "not_defined" and self.parameter("glazing_fraction").value > 0:
            errors.append(
                f"Error: {self.parameter('name').value}, glazing must be defined.")
        # Test frame defined
        if self.parameter("frame").value == "not_defined" and self.parameter("frame_fraction").value > 0:
            errors.append(
                f"Error: {self.parameter('name').value}, frame must be defined.")
        # Test construction defined
        self.construction_fraction = 1 - \
            self.parameter("glazing_fraction").value - \
            self.parameter("frame_fraction").value
        if self.parameter("construction").value == "not_defined" and self.construction_fraction > 0:
            errors.append(
                f"Error: {self.parameter('name').value}, construction must be defined.")
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._calc_thermal_resistance()

    def _calc_thermal_resistance(self):
        f_glazing = self.parameter("glazing_fraction").value
        f_frame = self.parameter("frame_fraction").value
        f_construction = 1 - f_glazing - f_frame
        r_glazing = 0
        r_frame = 0
        r_construction = 0

        if (f_glazing > 0):
            r_glazing = self.parameter(
                "glazing").component.thermal_resistance()
        if (f_frame > 0):
            r_frame = self.parameter("frame").component.parameter(
                "thermal_resistance").value
        if (f_construction > 0):
            r_construction = self.parameter(
                "construction").component.thermal_resistance()

        self._thermal_resistance = r_glazing*f_glazing + \
            r_frame*f_frame + r_construction*f_construction

    def thermal_resistance(self):
        return self._thermal_resistance

    def radiant_property(self, prop, radiation_type, side, theta=0):
        f_glazing = self.parameter("glazing_fraction").value
        f_frame = self.parameter("frame_fraction").value
        f_construction = 1 - f_glazing - f_frame

        value = 0
        if (f_glazing > 0):
            value += f_glazing * \
                self.parameter("glazing").component.radiant_property(
                    prop, radiation_type, side, theta)
        if (f_frame > 0):
            value += f_frame * \
                self.parameter("frame").component.radiant_property(
                    prop, radiation_type, side, theta)
        if (f_construction > 0):
            value += f_construction * \
                self.parameter("construction").component.radiant_property(
                    prop, radiation_type, side, theta)

        return value
