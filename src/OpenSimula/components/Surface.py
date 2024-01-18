from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_component, Parameter_float, Parameter_options, Parameter_boolean
from OpenSimula.Variable import Variable


class Surface(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        # Parameters
        self.parameter("type").value = "Surface"
        self.parameter("description").value = "Building surface"
        self.add_parameter(Parameter_boolean("virtual", False))
        self.add_parameter(Parameter_options("location", "EXTERNAL", [
                           "EXTERIOR", "INTERIOR", "UNDERGROUND", "ADIABATIC"]))
        self.add_parameter(Parameter_component("construction", "not_defined"))
        self.add_parameter(Parameter_component("space", "not_defined"))
        self.add_parameter(Parameter_component(
            "adjacent_space", "not_defined"))
        self.add_parameter(Parameter_float("area", 1, "m²", min=0.0))
        self.add_parameter(Parameter_float(
            "azimuth", 0, "°", min=-180, max=180))  # N: 0º, E: 90º, W: -90º, S: 180º
        self.add_parameter(Parameter_float(
            "altitude", 0, "°", min=-90, max=90))  # vertical: 0º, facing up: 90º, facing down: -90º

        # Variables
        self.add_variable(Variable("T_s1", "°C"))
        self.add_variable(Variable("T_s2", "°C"))

    def check(self):
        errors = super().check()
        # Test space defined
        if self.parameter("space").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, must define its space.")
        # Test construction defined
        if (not self.parameter("virtual").value) and self.parameter("construction").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, non virtual surfaces must define its construction."
            )
        # Test interior sufaces include adjacent spaces
        if self.parameter("location").value == "INTERIOR" and self.parameter("adjacent_space").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, interior surfaces must define adjacent space"
            )
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._create_openings_list()

    def _create_openings_list(self):
        project_openings_list = self.project().component_list(type="Opening")
        self._openings = []
        for opening in project_openings_list:
            if opening.parameter("surface").component == self:
                opening_dic = {"comp": opening,
                               "area": opening.area,
                               "virtual": opening.parameter("virtual").value
                               }
                self._openings.append(opening_dic)

    @property
    def net_area(self):
        area = self.parameter("area").value
        for opening in self._openings:
            area -= opening["area"]
        return area

    def rho_sw(self, face_number=0):
        if (self.parameter("virtual").value):
            return 0
        else:
            if face_number == 0:
                return 1-self.parameter("construction").component.parameter("solar_absortivity").value[0]
            else:
                return 1-self.parameter("construction").component.parameter("solar_absortivity").value[1]

    def tau_sw(self, face_number=0):
        if (self.parameter("virtual").value):
            return 1
        else:
            return 0

    def alpha_sw(self, face_number=0):
        if (self.parameter("virtual").value):
            return 0
        else:
            if face_number == 0:
                return self.parameter("construction").component.parameter("solar_absortivity").value[0]
            else:
                return self.parameter("construction").component.parameter("solar_absortivity").value[1]

    def rho_lw(self, face_number=0):
        if (self.parameter("virtual").value):
            return 0
        else:
            if face_number == 0:
                return 1-self.parameter("construction").component.parameter("lw_absortivity").value[0]
            else:
                return 1-self.parameter("construction").component.parameter("lw_absortivity").value[1]

    def tau_lw(self, face_number=0):
        if (self.parameter("virtual").value):
            return 1
        else:
            return 0

    def alpha_lw(self, face_number=0):
        if (self.parameter("virtual").value):
            return 0
        else:
            if face_number == 0:
                return self.parameter("construction").component.parameter("lw_absortivity").value[0]
            else:
                return self.parameter("construction").component.parameter("lw_absortivity").value[1]
