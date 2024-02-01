from OpenSimula.Component import Component
from OpenSimula.Parameters import Parameter_component, Parameter_float, Parameter_boolean
from OpenSimula.Variable import Variable


class Surface(Component):
    def __init__(self, name, project):
        Component.__init__(self, name, project)
        # Parameters
        self.parameter("type").value = "Ssurface"
        self.parameter("description").value = "Building surface"
        self.add_parameter(Parameter_boolean("virtual", False))
        self.add_parameter(Parameter_component("construction", "not_defined"))
        self.add_parameter(Parameter_float("area", 1, "m²", min=0.0))
        self.add_parameter(Parameter_float(
            "azimuth", 0, "°", min=-180, max=180))  # S: 0º, E: 90º, W: -90º, N: 180º
        self.add_parameter(Parameter_float(
            "altitude", 0, "°", min=-90, max=90))  # vertical: 0º, facing up: 90º, facing down: -90º

        # Variables
        self.add_variable(Variable("T_s0", "°C"))
        self.add_variable(Variable("T_s1", "°C"))
        self.add_variable(Variable("q_cd0", "W/m²"))
        self.add_variable(Variable("q_cd1", "W/m²"))
        self.add_variable(Variable("p_0", "W/m²"))
        self.add_variable(Variable("p_1", "W/m²"))
        self.add_variable(Variable("q_cv0", "W/m²"))
        self.add_variable(Variable("q_cv1", "W/m²"))
        self.add_variable(Variable("q_sol0", "W/m²"))
        self.add_variable(Variable("q_sol1", "W/m²"))
        self.add_variable(Variable("q_swig0", "W/m²"))
        self.add_variable(Variable("q_swig1", "W/m²"))
        self.add_variable(Variable("q_lwig0", "W/m²"))
        self.add_variable(Variable("q_lwig1", "W/m²"))
        self.add_variable(Variable("q_lwt0", "W/m²"))
        self.add_variable(Variable("q_lwt1", "W/m²"))

        # k values must be calculated by each subclass
        self.k = [1.0, 2.0]
        self.k_01 = -1

    def check(self):
        errors = super().check()
        # Test construction defined
        if (not self.parameter("virtual").value) and self.parameter("construction").value == "not_defined":
            errors.append(
                f"Error: {self.parameter('name').value}, non virtual surfaces must define its construction."
            )
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)

    def pre_iteration(self, time_index, date):
        super().pre_iteration(time_index, date)

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

    def radiant_property(self, prop, wave, side):
        if (self.parameter("virtual").value):
            if (prop == "tau"):
                return 1
            else:
                return 0
        else:
            if (wave == "short"):
                if (prop == "rho"):
                    return 1-self.parameter("construction").component.parameter("solar_absortivity").value[side]
                elif (prop == "tau"):
                    return 0
                elif (prop == "alpha"):
                    return self.parameter("construction").component.parameter("solar_absortivity").value[side]
            elif (wave == "long"):
                if (prop == "rho"):
                    return 1-self.parameter("construction").component.parameter("lw_absortivity").value[side]
                elif (prop == "tau"):
                    return 0
                elif (prop == "alpha"):
                    return self.parameter("construction").component.parameter("lw_absortivity").value[side]
