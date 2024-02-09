from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_component, Parameter_float, Parameter_options, Parameter_boolean
from OpenSimula.Variable import Variable


class Opening(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        # Parameters
        self.parameter("type").value = "Opening"
        self.parameter(
            "description").value = "Rectangular opening in building surfaces"
        self.add_parameter(Parameter_component("surface", "not_defined"))
        self.add_parameter(Parameter_component("window", "not_defined"))
        self.add_parameter(Parameter_float("width", 1, "m", min=0.0))
        self.add_parameter(Parameter_float("height", 1, "m", min=0.0))

        # Variables
        self.add_variable(Variable("T_s1", "°C"))
        self.add_variable(Variable("T_s2", "°C"))

    def check(self):
        errors = super().check()
        # Test surface
        if self.parameter("surface").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, its surface must be defined.")
        # Test window defined
        if self.parameter("window").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, opening must define its window."
            )
        return errors

    def building(self):
        return self.parameter("surface").component.building()

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._file_met = self.building().parameter("file_met").component

    def pre_iteration(self, time_index, date):
        super().pre_simulation(time_index, date)
        self._T_ext = self._file_met.variable("temperature").values[time_index]

    @property
    def area(self):
        return self.parameter("width").value * self.parameter("height").value

    def rho_sw(self, face_number=0):
        if (self.parameter("virtual").value):
            return 0
        else:
            alpha = self.parameter(
                "window").component.parameter("solar_absortivity").value
            tau = self.parameter(
                "window").component.parameter("solar_transmisivity").value
            if face_number == 0:
                return 1-alpha[0]-tau[0]
            else:
                return 1-alpha[1]-tau[1]

    def tau_sw(self, face_number=0):
        if (self.parameter("virtual").value):
            return 1
        else:
            tau = self.parameter(
                "window").component.parameter("solar_transmisivity").value
            if face_number == 0:
                return tau[0]
            else:
                return tau[1]

    def alpha_sw(self, face_number=0):
        if (self.parameter("virtual").value):
            return 0
        else:
            alpha = self.parameter("window").component.parameter(
                "solar_absortivity").value
            if face_number == 0:
                return alpha[0]
            else:
                return alpha[1]

    def rho_lw(self, face_number=0):
        if (self.parameter("virtual").value):
            return 0
        else:
            if face_number == 0:
                return 1-self.parameter("window").component.parameter("lw_absortivity").value[0]
            else:
                return 1-self.parameter("window").component.parameter("lw_absortivity").value[1]

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
                return self.parameter("window").component.parameter("lw_absortivity").value[0]
            else:
                return self.parameter("window").component.parameter("lw_absortivity").value[1]
