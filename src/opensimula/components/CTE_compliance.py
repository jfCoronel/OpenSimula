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
    HE4_MIN_SCOP_DHW,
    HOURS_OUTSIDE_LIMIT,
    HOURS_OUTSIDE_TOLERANCE,
    REFERENCE_COOLING_EER,
    REFERENCE_HEATING_EFFICIENCY_HHV,
    CTE_report,
    he0_limits,
    he4_minimum_share,
    winter_zone,
)


class CTE_compliance(Component):
    """Verification of the Spanish CTE DB-HE 2019, sections HE0 (limitation of the
    energy use) and HE4 (renewable contribution to the DHW demand), on top of an
    Energy_indicators and a Comfort_indicators.

    It applies the rules of the DB-HE to the energy of the project: only the EPB
    services count (heating, cooling, DHW, ventilation, humidity control and, in uses
    other than residencial privado, lighting), pumps and fans are assigned to heating
    or cooling by the mode of each hour (the fans running with no load are the
    ventilation), and in residencial privado the heat with no system behind it is
    given by the reference systems of table 4.5-HE0. It compares C_ep,nren and C_ep,tot
    per m² with the limits of the climate zone, use and intervention, and the hours
    outside setpoint of the building with 4 % of the occupation time.

    HE4: the DHW demand is the heat the generators give to DHW (with the losses of
    distribution, storage and recirculation) plus the demand not met; its renewable
    part is the heat of the solar collectors, the ambient energy of electric heat pumps
    whose seasonal SCOP_dhw (from the simulation) is at least 2.5, and the heat of
    biomass boilers times fp,ren / fp,tot. It applies above 100 l/day (Anejo F), with a
    minimum share of 70 % (60 % below 5000 l/day).

    Not a recognised procedure: HULC remains the official tool.
    """

    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "CTE_compliance"
        self.parameter("description").value = "Verification of CTE DB-HE, sections HE0 and HE4."
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
        # HE4: DHW demand of Anejo F (l/day at 60 °C); 0: from the DHW_demand components
        self.add_parameter(Parameter_float("dhw_daily_demand", 0, "l/day", min=0))

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

    # ______________________ HE4 ______________________

    def dhw_daily_demand(self):
        """DHW demand (l/day at 60 °C) and where it comes from: the parameter, or the
        mean of the simulated period of the DHW_demand components (their volume at
        their use temperature taken to 60 °C with the mains temperature, Anejo F 3)."""
        if self.parameter("dhw_daily_demand").value > 0:
            return self.parameter("dhw_daily_demand").value, "parameter"
        demands = [c for c in self.project().component_list()
                   if c.parameter("type").value == "DHW_demand"]
        total = 0.0
        n = 0
        for d in demands:
            V = np.asarray(d.variable("volume_flow").values, dtype=float)  # l/h
            T = np.asarray(d.variable("T_use").values, dtype=float)
            T_m = np.asarray(d.variable("T_mains").values, dtype=float)
            V60 = np.divide(V * (T - T_m), 60 - T_m, out=np.zeros_like(V), where=T_m < 60)
            total += V60.sum()
            n = len(V)
        hours = n * self.project().parameter("time_step").value / 3600
        return (total / hours * 24 if hours > 0 else 0.0), "DHW_demand components"

    def he4(self):
        """Renewable contribution to the DHW demand (HE4) over the simulated period.

        Returns:
            dict: ``demand`` and ``renewable`` (kWh), ``share``, ``daily_demand``
                (l/day at 60 °C) and its ``daily_source``, ``minimum`` share (0 if HE4
                does not apply) and ``generators`` (pandas.DataFrame: DHW heat,
                renewable part and how it is counted, per generator).
        """
        energy = self.parameter("energy_indicators").component
        factors = energy.factors()
        dt_h = self.project().parameter("time_step").value / 3600
        rows = {}
        demand = renewable = 0.0
        for g in energy._consumers():
            if g.parameter("type").value != "HVAC_water_generator" or getattr(g, "plant", None) is None:
                continue
            share = g.plant.dhw_share()
            Q = np.asarray(g.variable("Q").values, dtype=float)
            Q_dhw = float(np.sum(np.where(Q > 0, Q, 0) * share)) * dt_h / 1000
            if Q_dhw <= 0:
                continue
            equipment = g.parameter("equipment").component
            kind = equipment.parameter("type").value
            ren, how = 0.0, "not renewable"
            if kind == "Solar_collector":
                ren, how = Q_dhw, "solar thermal"
            elif kind == "Chiller_heat_pump":
                power = np.asarray(g.variable("power").values, dtype=float)
                E = float(np.sum(np.where(Q > 0, power, 0) * share)) * dt_h / 1000
                scop = Q_dhw / E if E > 0 else float("inf")
                if scop >= HE4_MIN_SCOP_DHW:
                    ren, how = Q_dhw - E, f"heat pump, SCOP_dhw {scop:.2f}: Q·(1 − 1/SCOP)"
                else:
                    how = f"heat pump, SCOP_dhw {scop:.2f} < {HE4_MIN_SCOP_DHW}: not counted"
            elif kind == "Boiler" and equipment.parameter("fuel").value == "BIOMASS":
                fp_ren, fp_nren, _ = factors["BIOMASS"]
                ren, how = Q_dhw * fp_ren / (fp_ren + fp_nren), "biomass: Q·fp,ren/fp,tot"
            rows[g.parameter("name").value] = (Q_dhw, ren, how)
            demand += Q_dhw
            renewable += ren
        unmet = sum(float(np.sum(c.variable("Q_unmet").values)) * dt_h / 1000
                    for c in self.project().component_list()
                    if c.parameter("type").value == "DHW_demand")
        if unmet > 0:
            rows["DHW demand not met"] = (unmet, 0.0, "not renewable")
            demand += unmet
        table = pd.DataFrame.from_dict(rows, orient="index",
                                       columns=["DHW heat [kWh]", "renewable [kWh]", "counted as"])
        table.index.name = "generator"
        if len(table):
            table.loc["TOTAL"] = [demand, renewable, ""]
        daily, source = self.dhw_daily_demand()
        return {"demand": demand, "renewable": renewable,
                "share": renewable / demand if demand > 0 else 0.0,
                "daily_demand": daily, "daily_source": source,
                "minimum": he4_minimum_share(daily), "generators": table}

    # ______________________ Report ______________________

    def report(self):
        """Verification of HE0 (C_ep,nren, C_ep,tot and hours outside setpoint) and HE4
        (renewable share of the DHW demand, if there is DHW).

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
        # HE4
        tables = []
        sections = "HE0"
        he4 = self.he4()
        if he4["demand"] > 0:
            if he4["minimum"] > 0:
                sections = "HE0 and HE4"
                rows.append(("Renewable share of DHW (HE4 3.1)", 100 * he4["share"],
                             100 * he4["minimum"], "%", he4["share"] >= he4["minimum"]))
                notes.append(
                    f"HE4: DHW demand {he4['daily_demand']:,.0f} l/day at 60 °C "
                    f"({he4['daily_source']}), {he4['demand']:,.0f} kWh with the losses of "
                    "distribution, storage and recirculation; only renewable energy produced on "
                    "site or nearby counts.")
            else:
                notes.append(f"HE4 does not apply: DHW demand {he4['daily_demand']:,.0f} l/day "
                             "at 60 °C, not above 100 l/day.")
            tables.append(("DHW renewable contribution (HE4)", he4["generators"]))
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
            "sections": sections,
            "dhw_demand": he4["demand"],
            "dhw_renewable": he4["renewable"],
            "dhw_renewable_share": he4["share"],
            "dhw_daily_demand": he4["daily_demand"],
            "dhw_minimum_share": he4["minimum"],
        }
        return CTE_report(f"CTE DB-HE, {sections}: {self.parameter('name').value}", checks,
                          services, summary, notes, tables)
