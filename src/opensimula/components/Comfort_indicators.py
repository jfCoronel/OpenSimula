import numpy as np
import pandas as pd

from opensimula.Component import Component
from opensimula.Message import Message
from opensimula.Parameters import (
    Parameter_boolean,
    Parameter_component_list,
    Parameter_float,
    Parameter_math_exp,
    Parameter_variable_list,
)
from opensimula.Variable import Variable
from opensimula.comfort import Comfort_report

ZONE_TYPES = ["Space", "Load_space"]
SYSTEM_TYPES = ["HVAC_DX_system", "HVAC_SZW_system", "HVAC_MZW_system", "HVAC_perfect_system"]


class Comfort_indicators(Component):
    """Hours each zone is outside the setpoints of the system that controls it.

    For every zone (Space or Load_space) it takes the heating and cooling setpoints
    of its system (`get_zone_setpoints()`) and counts the hours its air temperature
    is above the cooling setpoint or below the heating setpoint by more than a
    tolerance (K; keep it above the convergence of the zones, 0.01 K, or the hours
    held at the setpoint would count). Hours are counted while the system is on (`only_system_on`) and the
    expression `period` is not 0 (e.g. occupied hours). A zone served by no system
    is counted only by its temperatures.

    Its variables give, at each time step, the state of each zone (1 above, -1
    below, 0 inside the setpoints or not counted). `report()` gives the tables by
    zone and month.
    """

    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Comfort_indicators"
        self.parameter("description").value = (
            "Hours the zones are outside the setpoints of their systems."
        )
        self.add_parameter(Parameter_component_list("zones", [], ZONE_TYPES))
        self.add_parameter(Parameter_float("tolerance", 0.5, "K", min=0))
        self.add_parameter(Parameter_boolean("only_system_on", True))
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_math_exp("period", "1", "on/off"))

    def check(self):
        self._variables_ = {}
        errors = super().check()
        zones = self._zones()
        if not zones:
            errors.append(Message(
                f"Warning: {self.parameter('name').value}, there are no zones to count", "WARNING"))
        for zone in zones:
            name = zone.parameter("name").value
            self.add_variable(Variable(f"outside_{name}", "flag",
                                       f"{name}: 1 above, -1 below the setpoints, 0 inside"))
        self.add_variable(Variable("zones_outside", "-", "Number of zones outside the setpoints"))
        return errors

    def _zones(self):
        zones = [c for c in self.parameter("zones").component if c is not None]
        if not self.parameter("zones").value:
            zones = [c for c in self.project().component_list() if type(c).__name__ in ZONE_TYPES]
        return zones

    def _controls(self):
        """{zone: Zone_control} of the systems of the project (the first one found)."""
        controls = {}
        for comp in self.project().component_list():
            if type(comp).__name__ in SYSTEM_TYPES:
                for control in comp.get_zone_setpoints():
                    controls.setdefault(id(control.zone), control)
        return controls

    # ______________________ Simulation ______________________

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._delta_t = delta_t
        self._period = np.ones(n_time_steps, dtype=bool)

    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        if self.parameter("period").value.strip() != "1":
            Component.pre_iteration(self, time_index, date, daylight_saving)
            var_dic = self.get_parameter_variable_dictionary(time_index)
            self._period[time_index] = self.parameter("period").evaluate(var_dic) != 0

    def post_simulation(self):
        super().post_simulation()
        total = np.zeros(len(self._period))
        for zone, state in self._states().items():
            self.variable(f"outside_{zone.parameter('name').value}").values[:] = state["flag"]
            total += state["flag"] != 0
        self.variable("zones_outside").values[:] = total

    def _states(self):
        """Per zone: counted hours, temperature, setpoints and flag (1, -1, 0)."""
        controls = self._controls()
        tol = self.parameter("tolerance").value
        states = {}
        for zone in self._zones():
            T = np.asarray(zone.variable("temperature").values, dtype=float)
            control = controls.get(id(zone))
            counted = self._period.copy()
            if control is None:
                heating = cooling = None
                if self.parameter("only_system_on").value:
                    counted[:] = False
            else:
                heating, cooling = control.heating_setpoint, control.cooling_setpoint
                if self.parameter("only_system_on").value:
                    counted &= control.on
            above = np.zeros(len(T), dtype=bool) if cooling is None else counted & (T > cooling + tol)
            below = np.zeros(len(T), dtype=bool) if heating is None else counted & (T < heating - tol)
            flag = np.where(above, 1, np.where(below, -1, 0))
            states[zone] = {"T": T, "counted": counted, "above": above, "below": below,
                            "flag": flag, "heating": heating, "cooling": cooling,
                            "system": control is not None}
        return states

    # ______________________ Report ______________________

    def report(self):
        """Tables of the hours outside the setpoints, by zone and by month.

        Returns:
            opensimula.comfort.Comfort_report: tables, shown as HTML in notebooks.
        """
        if not hasattr(self, "_delta_t"):
            raise RuntimeError("report() needs the project simulated first")
        h = self._delta_t / 3600
        states = self._states()
        dates = pd.DatetimeIndex(self.project().dates())
        rows, monthly = {}, {}
        for zone, s in states.items():
            name = zone.parameter("name").value
            c, T = s["counted"], s["T"]
            dh_above = np.where(s["above"], T - s["cooling"], 0).sum() * h if s["cooling"] is not None else 0
            dh_below = np.where(s["below"], s["heating"] - T, 0).sum() * h if s["heating"] is not None else 0
            row = {
                "Hours counted": c.sum() * h,
                "Hours above": s["above"].sum() * h,
                "Hours below": s["below"].sum() * h,
                "Hours outside": (s["above"] | s["below"]).sum() * h,
                "Outside [%]": np.nan,
                "Degree-hours above [K·h]": dh_above,
                "Degree-hours below [K·h]": dh_below,
                "T max [°C]": T[c].max() if c.any() else np.nan,
                "T min [°C]": T[c].min() if c.any() else np.nan,
            }
            rows[name] = row
            monthly[name] = (s["above"] | s["below"]) * h
        table = pd.DataFrame.from_dict(rows, orient="index")
        total = table.sum(numeric_only=True, min_count=1)
        total["T max [°C]"] = table["T max [°C]"].max()
        total["T min [°C]"] = table["T min [°C]"].min()
        table.loc["TOTAL"] = total
        counted = table["Hours counted"]
        table["Outside [%]"] = np.where(counted > 0, 100 * table["Hours outside"] / counted.where(counted > 0, 1), np.nan)
        table.index.name = "zone"
        month = pd.DataFrame(monthly, index=dates).resample("ME").sum()
        month.index = month.index.strftime("%b %Y")
        month.index.name = "month"
        month["TOTAL"] = month.sum(axis=1)
        month.loc["Total"] = month.sum()
        t = table.loc["TOTAL"]
        summary = {
            "hours_counted": float(t["Hours counted"]),
            "hours_outside": float(t["Hours outside"]),
            "share_outside": float(t["Hours outside"] / t["Hours counted"]) if t["Hours counted"] > 0 else 0.0,
            "tolerance": self.parameter("tolerance").value,
            "counted": ("system on" if self.parameter("only_system_on").value else "all")
            + ("" if self.parameter("period").value.strip() == "1"
               else f" and period = {self.parameter('period').value}"),
        }
        notes = ["Hours of each zone counted while its system is on (and the period is not 0); "
                 "the TOTAL row adds the zone-hours of every zone."]
        free = [z.parameter("name").value for z, s in states.items() if not s["system"]]
        if free:
            notes.append("Zones with no system controlling them: " + ", ".join(free) + ".")
        return Comfort_report(f"Comfort indicators: {self.parameter('name').value}",
                              table, month, summary, notes)
