from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_float, Parameter_float_list


class Window(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Window"
        self.parameter(
            "description").value = "Window with glazing and frame and shading."

        self.add_parameter(Parameter_float_list(
            "solar_transmisivity", [0.85, 0.85], "frac", min=0, max=1))
        self.add_parameter(Parameter_float_list(
            "solar_absortivity", [0.07, 0.07], "frac", min=0, max=1))
        self.add_parameter(Parameter_float_list(
            "lw_absortivity", [0.9, 0.9], "frac", min=0, max=1))
        self.add_parameter(Parameter_float("R_glazing", 0.001, "m²K/W", min=0))
        self.add_parameter(Parameter_float("R_frame", 0.2, "m²K/W", min=0))
        self.add_parameter(Parameter_float(
            "frame_fraction", 0.1, "frac", min=0, max=1))
