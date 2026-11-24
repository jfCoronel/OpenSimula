import numpy as np
import pandas as pd

from opensimula.Component import Component
from opensimula.Message import Message
from opensimula.Parameters import (
    Parameter_component,
    Parameter_float,
    Parameter_options,
    Parameter_string,
    Parameter_string_list,
)
from opensimula.cte import (
    EXTRAPENINSULAR_REGIONS,
    HOURS_OUTSIDE_LIMIT,
    HOURS_OUTSIDE_TOLERANCE,
    REFERENCE_COOLING_EER,
    REFERENCE_HEATING_EFFICIENCY_HHV,
    CTE_report,
    he0_limits,
    winter_zone,
)


class CTE_compliance(Component):
    """Verification of the Spanish CTE DB-HE 2019, section HE0 (limitation of the
    energy use), on top of an Energy_indicators and a Comfort_indicators.

    It applies the rules of the DB-HE to the energy of the project: only the EPB
    services count (heating, cooling, DHW, ventilation, humidity control and, in uses
    other than residencial privado, lighting), pumps and fans are assigned to heating
    or cooling by the mode of each hour (the fans running with no load are the
    ventilation), and in residencial privado the heat with no system behind it is
    given by the reference systems of table 4.5-HE0. It compares C_ep,nren and C_ep,tot
    per m² with the limits of the climate zone, use and intervention, and the hours
    outside setpoint of the building with 4 % of the occupation time.

    Not a recognised procedure: HULC remains the official tool.
    """

    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "CTE_compliance"
        self.parameter("description").value = "Verification of CTE DB-HE, section HE0."
        self.add_parameter(Parameter_component("energy_indicators", "not_defined",
                                               ["Energy_indicators"]))
        self.add_parameter(Parameter_component("comfort_indicators", "not_defined",
                                               ["Comfort_indicators"]))
        self.add_parameter(Parameter_string("climate_zone", "B4"))
        self.add_parameter(Parameter_options("building_use", "RESIDENTIAL_PRIVATE",
                                             ["RESIDENTIAL_PRIVATE", "OTHER"]))
        self.add_parameter(Parameter_options("intervention", "NEW_OR_EXTENSION",
                                             ["NEW_OR_EXTENSION", "CHANGE_OF_USE_OR_REFORM"]))
        self.add_parameter(Parameter_float("internal_load", 0, "W/m²", min=0))
        self.add_parameter(Parameter_string_list("non_epb_services", ["EQUIPMENT"]))
        self.add_parameter(Parameter_float("hhv_lhv_ratio", 1.11, "frac", min=1))

    def check(self):
        errors = super().check()
        name = self.parameter("name").value
        if winter_zone(self.parameter("climate_zone").value) is None:
            errors.append(Message(
                f"Error: {name}, climate_zone {self.parameter('climate_zone').value!r} is not "
                "a climate zone of the DB-HE (α, A-E followed by 1-4, e.g. 'B4')", "ERROR"))
        energy = self.parameter("energy_indicators").component
        if energy is None:
            errors.append(Message(f"Error: {name}, energy_indicators must be defined", "ERROR"))
        elif (self.parameter("building_use").value == "OTHER"
              and self.parameter("internal_load").value == 0
              and any(type(z).__name__ != "Space" for z in energy._zones())):
            errors.append(Message(
                f"Error: {name}, internal_load (C_FI) must be given: the zones include "
                "Load_space, whose loads are not split into occupancy, lighting and equipment",
                "ERROR"))
        comfort = self.parameter("comfort_indicators").component
        if comfort is not None and comfort.parameter("tolerance").value != HOURS_OUTSIDE_TOLERANCE:
            errors.append(Message(
                f"Warning: {name}, the tolerance of {comfort.parameter('name').value} is "
                f"{comfort.parameter('tolerance').value} K; the DB-HE counts the hours more "
                f"than {HOURS_OUTSIDE_TOLERANCE} K outside the setpoints", "WARNING"))
        return errors

    # ______________________ Data of the verification ______________________

    def _extrapeninsular(self, energy):
        return energy.parameter("conversion_factors").value in EXTRAPENINSULAR_REGIONS

    def internal_load(self):
        """Carga interna media C_FI (W/m²) and where it comes from.

        The parameter if it is not 0; otherwise the mean over the simulated period of
        the sensible gains of occupancy, lighting and equipment of the Space zones of the
        Energy_indicators, per m² of their floor area.

        Returns:
            tuple: (C_FI, "parameter" or "simulated gains").
        """
        if self.parameter("internal_load").value > 0:
            return self.parameter("internal_load").value, "parameter"
        zones = self.parameter("energy_indicators").component._zones()
        area = sum(z.parameter("floor_area").value for z in zones)
        gains = 0.0
        for z in zones:
            for key in ("people_convective", "people_radiant", "light_convective",
                        "light_radiant", "other_gains_convective", "other_gains_radiant"):
                gains += np.mean(z.variable(key).values)
        return (gains / area if area > 0 else 0.0), "simulated gains"

    # ______________________ Report ______________________

    def report(self):
        """Verification of HE0: C_ep,nren, C_ep,tot and hours outside setpoint.

        Returns:
            opensimula.cte.CTE_report: requirements (value, limit, complies) and the EPB
                services counted, shown as HTML in notebooks.
        """
        energy = self.parameter("energy_indicators").component
        comfort = self.parameter("comfort_indicators").component
        use = self.parameter("building_use").value
        residential = use == "RESIDENTIAL_PRIVATE"
        zone = self.parameter("climate_zone").value
        notes = ["Not a recognised procedure: HULC remains the official tool of the CTE."]

        # energy of the EPB services, transport assigned by mode, reference systems
        reference = {}
        if residential:
            reference = {
                "reference_heating": ("NATURAL_GAS", REFERENCE_HEATING_EFFICIENCY_HHV
                                      * self.parameter("hhv_lhv_ratio").value),
                "reference_cooling": ("ELECTRICITY", REFERENCE_COOLING_EER),
            }
        r = energy.report(water_transport="BY_MODE", air_transport="BY_MODE", **reference)
        excluded = set(self.parameter("non_epb_services").value)
        if residential:
            excluded.add("LIGHTING")
        epb = [s for s in r.indicators.index if s != "TOTAL" and s not in excluded]
        if not residential and any(s.endswith("WITHOUT_EQUIPMENT") for s in epb):
            notes.append("There is heat without equipment (THERMAL): the DB-HE has no reference "
                         "systems for uses other than residencial privado, it is not counted.")
        area = r.summary["reference_area"]
        services = r.indicators.loc[epb, ["Final [kWh]", "Primary nren [kWh]",
                                         "Primary total [kWh]", "CO2 [kg]"]] / area
        services.columns = ["Final [kWh/m²]", "C_ep,nren [kWh/m²]", "C_ep,tot [kWh/m²]",
                            "CO2 [kg/m²]"]
        services.loc["TOTAL"] = services.sum()
        cep_nren = services.loc["TOTAL", "C_ep,nren [kWh/m²]"]
        cep_tot = services.loc["TOTAL", "C_ep,tot [kWh/m²]"]

        c_fi, c_fi_source = (self.internal_load() if not residential else (0.0, "not used"))
        extrapeninsular = self._extrapeninsular(energy)
        nren_lim, tot_lim = he0_limits(zone, use, self.parameter("intervention").value,
                                       c_fi, extrapeninsular)
        rows = [
            ("C_ep,nren (HE0 3.1)", cep_nren, nren_lim, "kWh/m²·year", cep_nren <= nren_lim),
            ("C_ep,tot (HE0 3.2)", cep_tot, tot_lim, "kWh/m²·year", cep_tot <= tot_lim),
        ]
        if comfort is not None:
            c = comfort.report().summary
            occupation = c["period_hours"]
            limit = HOURS_OUTSIDE_LIMIT * occupation
            hours = c["building_hours_outside"]
            rows.append(("Hours outside setpoint (HE0 4.1.6)", hours, limit, "h", hours <= limit))
            notes.append(f"Hours outside setpoint: building hours (any zone more than "
                         f"{c['tolerance']} K outside its setpoints, counted once), limit 4 % of "
                         f"{occupation:,.0f} h of occupation (the period of "
                         f"{comfort.parameter('name').value}).")
        else:
            notes.append("Hours outside setpoint not checked: no comfort_indicators.")
        checks = pd.DataFrame(rows, columns=["requirement", "value", "limit", "unit", "complies"])
        checks = checks.set_index("requirement")
        thermal = any(u.carrier == "THERMAL" and u.values.sum() > 0 for u in energy.get_uses())
        if residential and thermal:
            notes.append("Reference systems of table 4.5-HE0 for the heat without equipment: "
                         f"natural gas {REFERENCE_HEATING_EFFICIENCY_HHV} on the HHV "
                         f"(× {self.parameter('hhv_lhv_ratio').value} on the LHV), electricity "
                         f"EER {REFERENCE_COOLING_EER}.")
        notes.append("EPB services: " + ", ".join(epb) + "; pumps and fans assigned to heating or "
                     "cooling by the mode of each hour, fans with no load as ventilation.")
        summary = {
            "climate_zone": zone,
            "building_use": use,
            "intervention": self.parameter("intervention").value,
            "extrapeninsular": extrapeninsular,
            "reference_area": area,
            "c_fi": c_fi,
            "c_fi_source": c_fi_source,
            "cep_nren": float(cep_nren),
            "cep_nren_limit": float(nren_lim),
            "cep_tot": float(cep_tot),
            "cep_tot_limit": float(tot_lim),
            "complies": bool(checks["complies"].all()),
        }
        return CTE_report(f"CTE DB-HE, HE0: {self.parameter('name').value}", checks, services,
                          summary, notes)
