from opensimula.Component import Component
from opensimula.Iterative_process import Iterative_process
import psychrolib as sicro


class Thermal_zone(Component):
    """Base class of the zones that air systems can serve (Space, Load_space).

    It holds what the HVAC systems use of a zone: the air or heat they supply
    (one controlled system and any number of uncontrolled ones), the thermal and
    humidity balance equations of the zone, ``K·T = F`` and ``K_hum·w = F_hum``,
    and the iterative solution of temperature and humidity in each time step.

    It is not a component type of its own: it is not registered in
    ``opensimula.components`` and cannot be created in a project.

    A subclass must:

    - define the parameters ``convergence_DT`` and ``convergence_Dw`` and the
      variables ``temperature``, ``abs_humidity``, ``rel_humidity``,
      ``system_sensible_heat``, ``system_latent_heat``,
      ``u_system_sensible_heat`` and ``u_system_latent_heat``;
    - set ``self.props`` and call ``_reset_systems_()`` before each time step;
    - set ``self._T`` and ``self._w`` (first estimate of the step) and call
      ``_create_iterative_processes_()`` in ``pre_iteration``;
    - implement ``_zone_thermal_equation_()`` and ``_zone_humidity_equation_()``,
      the balances of the zone without the systems.

    The dictionaries of the systems have the keys ``M_a`` (supplied dry air, kg/s),
    ``T_a`` (its temperature, °C), ``w_a`` (its humidity, g/kg), ``Q_s`` (sensible
    heat added directly, W) and ``M_w`` (water vapour added directly, g/s);
    uncontrolled systems have also a ``name``.
    """

    # _________________ To be implemented by the zones _________________

    def _zone_thermal_equation_(self):
        """Thermal balance of the zone without systems.

        Returns:
            tuple: (K, F), with K in W/K and F in W, so that K·T = F.
        """
        raise NotImplementedError

    def _zone_humidity_equation_(self):
        """Humidity balance of the zone without systems.

        Returns:
            tuple: (K_hum, F_hum), with K_hum in kg/s and F_hum in g/s, so that
                K_hum·w = F_hum with w in g/kg.
        """
        raise NotImplementedError

    # _________________ Systems _________________

    def _reset_systems_(self):
        """Remove the systems: none supplies anything until they are set again."""
        self.uncontrol_systems = []
        self.control_system = {"M_a": 0, "T_a": 0, "w_a": 0, "Q_s": 0, "M_w": 0}

    def add_uncontrol_system(self, system_dic):
        """Add (or replace, by name) an uncontrolled system: air or heat supplied to the
        zone that is not adjusted to its setpoint.

        Args:
            system_dic (dict): keys name, M_a, T_a, w_a, Q_s and M_w.
        """
        self.del_uncontrol_system(system_dic["name"])
        self.uncontrol_systems.append(system_dic)

    def del_uncontrol_system(self, system_name):
        """Remove the uncontrolled system with that name, if any.

        Args:
            system_name (str): name of the system.
        """
        self.uncontrol_systems = [
            air for air in self.uncontrol_systems if air["name"] != system_name
        ]

    def set_control_system(self, system_dic):
        """Set the controlled system: the air or heat that keeps the zone at its setpoint.

        Args:
            system_dic (dict): keys M_a, T_a, w_a, Q_s and M_w.
        """
        self.control_system = system_dic

    def _acumulate_u_systems(self):
        self._M_a_u_systems = 0
        self._M_T_a_u_systems = 0
        self._M_w_a_u_systems = 0
        self._Q_s_u_systems = 0
        self._M_w_u_systems = 0
        for system in self.uncontrol_systems:
            self._M_a_u_systems += system["M_a"]
            self._M_T_a_u_systems += system["M_a"] * system["T_a"]
            self._M_w_a_u_systems += system["M_a"] * system["w_a"]
            self._Q_s_u_systems += system["Q_s"]
            self._M_w_u_systems += system["M_w"]

    # _________________ Balance equations _________________

    def get_thermal_equation(self, include_control_system):
        """Thermal balance of the zone with its uncontrolled systems.

        Args:
            include_control_system (bool): include also the controlled system.

        Returns:
            tuple: (K, F), with K in W/K and F in W, so that K·T = F. A system that
                adds Q (W) to the zone at temperature T gives K·T = F + Q.
        """
        self._acumulate_u_systems()
        K_zone, F_zone = self._zone_thermal_equation_()
        F_tot = (
            F_zone
            + self._M_T_a_u_systems * self.props["C_PA"]
            + self._Q_s_u_systems
        )
        K_tot = K_zone + self._M_a_u_systems * self.props["C_PA"]
        if include_control_system:
            K_tot += self.control_system["M_a"] * self.props["C_PA"]
            F_tot += (
                self.control_system["M_a"]
                * self.props["C_PA"]
                * self.control_system["T_a"]
                + self.control_system["Q_s"]
            )
        return (K_tot, F_tot)

    def get_humidity_equation(self, include_control_system):
        """Humidity balance of the zone with its uncontrolled systems.

        Args:
            include_control_system (bool): include also the controlled system.

        Returns:
            tuple: (K_hum, F_hum), with K_hum in kg/s and F_hum in g/s, so that
                K_hum·w = F_hum with w in g/kg.
        """
        self._acumulate_u_systems()
        K_zone, F_zone = self._zone_humidity_equation_()
        K_hum = K_zone + self._M_a_u_systems
        F_hum = F_zone + self._M_w_a_u_systems + self._M_w_u_systems
        if include_control_system:
            K_hum += self.control_system["M_a"]
            F_hum += (
                self.control_system["M_a"] * self.control_system["w_a"]
                + self.control_system["M_w"]
            )
        return (K_hum, F_hum)

    def get_Q_required(self, T_cool_sp, T_heat_sp):
        """Sensible heat that keeps the zone between the setpoints.

        Args:
            T_cool_sp (float): cooling setpoint (°C).
            T_heat_sp (float): heating setpoint (°C).

        Returns:
            float: heat to add (W): positive heating, negative cooling, 0 if the zone
                is between the setpoints without the controlled system.
        """
        K_tot, F_tot = self.get_thermal_equation(False)
        T = F_tot / K_tot
        if T > T_cool_sp:
            return K_tot * T_cool_sp - F_tot
        elif T < T_heat_sp:
            return K_tot * T_heat_sp - F_tot
        else:
            return 0

    def get_M_required(self, HR_min, HR_max):
        """Water vapour that keeps the zone between the relative humidity limits.

        Args:
            HR_min (float): minimum relative humidity (%).
            HR_max (float): maximum relative humidity (%).

        Returns:
            float: water vapour to add (g/s): positive humidifying, negative
                dehumidifying, 0 if the zone is between the limits.
        """
        K_hum, F_hum = self.get_humidity_equation(False)
        w = F_hum / K_hum
        if w < 0:
            w = 0
        hr = (
            sicro.GetRelHumFromHumRatio(self._T, w / 1000, self.props["ATM_PRESSURE"])
            * 100
        )
        if hr < HR_min:
            w_min = (
                sicro.GetHumRatioFromRelHum(
                    self._T, HR_min / 100, self.props["ATM_PRESSURE"]
                )
                * 1000
            )
            return K_hum * w_min - F_hum
        elif hr > HR_max:
            w_max = (
                sicro.GetHumRatioFromRelHum(
                    self._T, HR_max / 100, self.props["ATM_PRESSURE"]
                )
                * 1000
            )
            return K_hum * w_max - F_hum
        else:
            return 0

    # _________________ Time step _________________

    def _create_iterative_processes_(self):
        """Start the iterative solution of the step from the estimate self._T, self._w."""
        self.itera_T = Iterative_process(
            self._T,
            tol=self.parameter("convergence_DT").value,
            n_ini_relax=3,
            rel_vel=0.8,
        )
        self.itera_w = Iterative_process(
            self._w,
            tol=self.parameter("convergence_Dw").value,
            n_ini_relax=3,
            rel_vel=0.8,
        )

    def iteration(self, time_index, date, daylight_saving, n_iter):
        super().iteration(time_index, date, daylight_saving, n_iter)

        # Calculate temperature
        K_tot, F_tot = self.get_thermal_equation(True)
        T = F_tot / K_tot
        self.variable("temperature").values[time_index] = self.itera_T.estimate_next_x(
            T
        )

        # Calculate humidity
        K_hum, F_hum = self.get_humidity_equation(True)
        w = F_hum / K_hum
        if w < 0:
            w = 0
        if T > -100 and T < 100:  # Sicro limits
            max_hum = (
                sicro.GetHumRatioFromRelHum(T, 1, self.props["ATM_PRESSURE"]) * 1000
            )
            if w > max_hum:
                w = max_hum

        self.variable("abs_humidity").values[time_index] = self.itera_w.estimate_next_x(
            w
        )

        # Test convergence
        converged = self.itera_T.converged() and self.itera_w.converged()
        return converged

    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        self._T = self.variable("temperature").values[time_index]
        self._w = self.variable("abs_humidity").values[time_index]
        if self._T < 100:  # Sicro limit
            rh = (
                sicro.GetRelHumFromHumRatio(
                    self._T, self._w / 1000, self.props["ATM_PRESSURE"]
                )
                * 100
            )
            self.variable("rel_humidity").values[time_index] = rh

    def _calculate_system_heat_(self, time_i):
        """Store the heat supplied by the systems at the solved T and w of the step.

        Args:
            time_i (int): time index.
        """
        # The uncontrolled systems may have changed since the last thermal solution (e.g. a VAV
        # system replaces its maximum air flow by a controlled flow): report the current ones
        self._acumulate_u_systems()
        self.variable("u_system_sensible_heat").values[time_i] = self.props["C_PA"] * (
            self._M_T_a_u_systems - self._M_a_u_systems * self._T
        ) + self._Q_s_u_systems  # their air and their heat (e.g. radiators)
        self.variable("system_sensible_heat").values[time_i] = (
            self.control_system["M_a"]
            * self.props["C_PA"]
            * (self.control_system["T_a"] - self._T)
            + self.control_system["Q_s"]
        )
        self.variable("u_system_latent_heat").values[time_i] = self.props["LAMBDA"] * (
            self._M_w_a_u_systems - self._M_a_u_systems * self._w + self._M_w_u_systems
        )
        self.variable("system_latent_heat").values[time_i] = (
            self.control_system["M_a"]
            * self.props["LAMBDA"]
            * (self.control_system["w_a"] - self._w)
            + self.control_system["M_w"] * self.props["LAMBDA"]
        )
