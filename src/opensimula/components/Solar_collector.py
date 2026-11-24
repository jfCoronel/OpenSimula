import math

from opensimula.Component import Component
from opensimula.Message import Message
from opensimula.Parameters import Parameter_float
from opensimula.Variable import Variable


class Solar_collector(Component):
    """Solar thermal collector field (manufacturer data, EN ISO 9806).

    Equipment data, like a Boiler: an HVAC_water_generator uses it as a generator that
    cannot be controlled, whose heat the plant always takes. The quasi-steady model of
    EN ISO 9806 on the aperture area A:

        Q = A · [η0 · (K_b · G_b + K_d · G_d) − a1 · (T_m − T_a) − a2 · (T_m − T_a)²]

    with the beam and diffuse irradiance on the collector plane from the weather file
    (the diffuse with the model of the File_met, plus the ground reflected one), the
    incidence angle modifier of the beam K_b = 1 − b0 · (1/cos θ − 1) and that of the
    diffuse K_d, and T_m the mean temperature of the fluid in the collector. With a
    heat exchanger of effectiveness ε between the collector loop and the water of the
    plant (same flow on both sides), the water entering at T_in:
    T_m = T_in + Q / (m·c) · (1/ε − 1/2). Its pump runs while Q > 0 (the collector is
    hotter than the water it heats) and the water of the plant is below
    ``max_temperature``.
    """

    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Solar_collector"
        self.parameter("description").value = "Solar thermal collector field"
        self.add_parameter(Parameter_float("area", 2, "m²", min=0))
        self.add_parameter(Parameter_float("eta_0", 0.75, "frac", min=0, max=1))
        self.add_parameter(Parameter_float("a1", 3.5, "W/(m²·K)", min=0))
        self.add_parameter(Parameter_float("a2", 0.015, "W/(m²·K²)", min=0))
        self.add_parameter(Parameter_float("b0", 0.15, "-", min=0))
        self.add_parameter(Parameter_float("K_diffuse", 0.9, "frac", min=0, max=1))
        self.add_parameter(Parameter_float("tilt", 45, "°", min=0, max=90))
        self.add_parameter(Parameter_float("azimuth", 0, "°", min=-180, max=180))
        self.add_parameter(Parameter_float("nominal_water_flow", 0.04, "dm³/s", min=0))
        self.add_parameter(Parameter_float("exchanger_effectiveness", 1, "frac", min=0.01, max=1))
        self.add_parameter(Parameter_float("max_temperature", 90, "°C"))
        self.add_variable(Variable("irradiance", unit="W/m²"))  # total on the plane
        self.add_variable(Variable("effective_irradiance", unit="W/m²"))  # with K_b, K_d

    def check(self):
        errors = super().check()
        if self.project().parameter("simulation_file_met").value == "not_defined":
            msg = (f"{self.parameter('name').value}, file_met must be defined in the project "
                   "'simulation_file_met'.")
            errors.append(Message(msg, "ERROR"))
        return errors

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self.props = self._sim_.props
        self.file_met = self.project().parameter("simulation_file_met").component
        self.albedo = self.project().parameter("albedo").value
        self.G_eff = 0.0

    def pre_iteration(self, time_index, date, daylight_saving):
        super().pre_iteration(time_index, date, daylight_saving)
        p = lambda key: self.parameter(key).value  # noqa: E731
        tilt = math.radians(p("tilt"))
        altitude = 90 - p("tilt")  # of the normal of the plane
        met = self.file_met
        G_h = met.variable("sol_direct").values[time_index] + met.variable("sol_diffuse").values[time_index]
        G_b = met.solar_direct_rad(time_index, p("azimuth"), altitude)
        G_d = (met.solar_diffuse_rad(time_index, p("azimuth"), altitude)
               + self.albedo * G_h * (1 - math.cos(tilt)) / 2)
        theta = met.solar_surface_angle(time_index, p("azimuth"), altitude)
        K_b = max(0.0, 1 - p("b0") * (1 / math.cos(theta) - 1)) if theta is not None else 0.0
        self.T_a = met.variable("temperature").values[time_index]
        self.G = G_b + G_d
        self.G_eff = K_b * G_b + p("K_diffuse") * G_d
        self.variable("irradiance").values[time_index] = self.G
        self.variable("effective_irradiance").values[time_index] = self.G_eff

    def get_useful_heat(self, T_in, water_flow):
        """Heat the collector gives to water entering at T_in with its pump running.

        Args:
            T_in (float): temperature of the water of the plant that it heats (°C).
            water_flow (float): flow of the collector loop (dm³/s).

        Returns:
            float: useful heat (W), 0 if the collector would not heat the water or the
                water is at the maximum temperature.
        """
        p = lambda key: self.parameter(key).value  # noqa: E731
        if water_flow <= 0 or self.G_eff <= 0 or T_in >= p("max_temperature"):
            return 0.0
        A, eta0, a1, a2 = p("area"), p("eta_0"), p("a1"), p("a2")
        mc = self.props["RHOCP_W"](T_in) / 1000 * water_flow  # W/K
        k = (1 / p("exchanger_effectiveness") - 0.5) / mc  # T_m = T_in + k · Q
        x0 = T_in - self.T_a
        # Q = (x - x0) / k with x = T_m - T_a: A·a2·k·x² + (1 + A·a1·k)·x - (x0 + A·η0·G·k) = 0
        a, b, c = A * a2 * k, 1 + A * a1 * k, x0 + A * eta0 * self.G_eff * k
        # the root without cancellation: x = 2c / (b + sqrt(b² + 4ac))
        x = 2 * c / (b + math.sqrt(max(b * b + 4 * a * c, 0)))
        return max(0.0, (x - x0) / k)

    def get_efficiency(self, Q):
        """Efficiency of the collector for a useful heat Q: Q / (A · G)."""
        A = self.parameter("area").value
        return Q / (A * self.G) if self.G > 0 else 0.0
