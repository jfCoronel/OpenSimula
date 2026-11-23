import numpy as np
import pandas as pd

from opensimula.Component import Component
from opensimula.Message import Message
from opensimula.Parameters import (
    Parameter_component_list,
    Parameter_float,
    Parameter_float_list,
    Parameter_math_exp_list,
    Parameter_options,
    Parameter_options_list,
    Parameter_string_list,
    Parameter_variable_list,
)
from opensimula.Variable import Variable
from opensimula.energy import (
    CARRIERS,
    ELECTRICITY_FACTORS,
    SERVICES,
    Energy_report,
    Energy_use,
    conversion_factors,
)

CONSUMER_TYPES = [
    "HVAC_DX_system",
    "HVAC_SZW_system",
    "HVAC_MZW_system",
    "HVAC_perfect_system",
    "HVAC_water_generator",
    "HVAC_water_system",
    "HVAC_water_circuit",
]
ZONE_TYPES = ["Space", "Load_space"]
# Carriers a user can give (equipment, extra uses, custom factors)
FINAL_CARRIERS = [c for c in CARRIERS if c not in ("AMBIENT", "THERMAL")]
TRANSPORT_OPTIONS = ["SEPARATE", "BY_MODE"]


class Energy_indicators(Component):
    """Energy use of a project: final energy by carrier and service, primary
    energy and CO₂.

    It adds up what the consumers report (`get_energy_use()`: systems, water
    generators, plants and circuits, and the lighting and equipment of the zones),
    plus extra uses given as expressions (e.g. domestic hot water), and converts the
    final energy with the factors of a region (documento reconocido del RITE, 2016)
    or custom ones. It is neutral: no rules of a regulation (a CTE_compliance
    component will apply them on top of it).

    Its variables are hourly powers (W; CO2 in kg/h) by carrier and service, with
    the pumps and fans as their own services. `report()` gives the tables (annual,
    monthly and per m²), with the hypotheses as arguments: transport assigned to
    heating/cooling or not, reference generators for the heat without equipment.
    """

    def __init__(self, name, project):
        Component.__init__(self, name, project)
        self.parameter("type").value = "Energy_indicators"
        self.parameter("description").value = (
            "Final energy by carrier and service, primary energy and CO2 of the project."
        )
        self.add_parameter(Parameter_component_list("components", [], CONSUMER_TYPES))
        self.add_parameter(Parameter_component_list("zones", [], ZONE_TYPES))
        self.add_parameter(Parameter_float("reference_area", 0, "m²", min=0))
        self.add_parameter(Parameter_options("equipment_carrier", "ELECTRICITY", FINAL_CARRIERS))
        self.add_parameter(Parameter_options(
            "conversion_factors", "PENINSULA", list(ELECTRICITY_FACTORS)))
        self.add_parameter(Parameter_options_list("custom_carriers", [], FINAL_CARRIERS))
        self.add_parameter(Parameter_float_list("custom_fp_ren", [], "frac", min=0))
        self.add_parameter(Parameter_float_list("custom_fp_nren", [], "frac", min=0))
        self.add_parameter(Parameter_float_list("custom_CO2", [], "kg/kWh", min=0))
        self.add_parameter(Parameter_variable_list("input_variables", []))
        self.add_parameter(Parameter_string_list("extra_services", []))
        self.add_parameter(Parameter_options_list("extra_carriers", [], FINAL_CARRIERS))
        self.add_parameter(Parameter_math_exp_list("extra_expressions", [], "W"))

    # ______________________ Check and variables ______________________

    def check(self):
        self._variables_ = {}
        errors = super().check()
        name = self.parameter("name").value
        n_extra = [len(self.parameter(k).value)
                   for k in ("extra_services", "extra_carriers", "extra_expressions")]
        if len(set(n_extra)) > 1:
            errors.append(Message(
                f"Error: {name}, extra_services, extra_carriers and extra_expressions "
                "size must be equal", "ERROR"))
        n_custom = [len(self.parameter(k).value)
                    for k in ("custom_carriers", "custom_fp_ren", "custom_fp_nren", "custom_CO2")]
        if len(set(n_custom)) > 1:
            errors.append(Message(
                f"Error: {name}, custom_carriers, custom_fp_ren, custom_fp_nren and custom_CO2 "
                "size must be equal", "ERROR"))
        if not self._consumers() and not self._zones() and not n_extra[0]:
            errors.append(Message(
                f"Warning: {name}, there are no consumers, zones or extra uses to count",
                "WARNING"))
        for carrier in CARRIERS:
            self.add_variable(Variable(carrier.lower(), "W", f"Final energy, {carrier}"))
        for service in self._services():
            self.add_variable(Variable(service.lower(), "W", f"Final energy of {service}"))
        self.add_variable(Variable("primary_ren", "W", "Primary energy, renewable"))
        self.add_variable(Variable("primary_nren", "W", "Primary energy, non-renewable"))
        self.add_variable(Variable("primary_total", "W", "Primary energy, total"))
        self.add_variable(Variable("CO2", "kg/h", "CO2 emissions"))
        return errors

    def _services(self):
        extra = [s for s in self.parameter("extra_services").value if s not in SERVICES]
        return SERVICES + list(dict.fromkeys(extra))

    def _consumers(self):
        components = [c for c in self.parameter("components").component if c is not None]
        if not self.parameter("components").value:
            components = [c for c in self.project().component_list()
                          if type(c).__name__ in CONSUMER_TYPES]
        return components

    def _zones(self):
        zones = [c for c in self.parameter("zones").component if c is not None]
        if not self.parameter("zones").value:
            zones = [c for c in self.project().component_list()
                     if type(c).__name__ in ZONE_TYPES]
        return zones

    def reference_area(self):
        """Reference area (m²): the parameter, or the floor area of the zones if 0."""
        area = self.parameter("reference_area").value
        if area > 0:
            return area
        return sum(z.parameter("floor_area").value for z in self._zones())

    def factors(self):
        """Conversion factors used: {carrier: (fp_ren, fp_nren, kg CO2 per kWh)}."""
        factors = conversion_factors(self.parameter("conversion_factors").value)
        p = self.parameter
        for i, carrier in enumerate(p("custom_carriers").value):
            factors[carrier] = (p("custom_fp_ren").value[i], p("custom_fp_nren").value[i],
                                p("custom_CO2").value[i])
        return factors

    # ______________________ Simulation ______________________

    def pre_simulation(self, n_time_steps, delta_t):
        super().pre_simulation(n_time_steps, delta_t)
        self._delta_t = delta_t
        self._extra = np.zeros((len(self.parameter("extra_expressions").value), n_time_steps))

    def post_iteration(self, time_index, date, daylight_saving, converged):
        super().post_iteration(time_index, date, daylight_saving, converged)
        if len(self._extra):
            # final values of the input variables of the time step
            Component.pre_iteration(self, time_index, date, daylight_saving)
            var_dic = self.get_parameter_variable_dictionary(time_index)
            for i in range(len(self._extra)):
                self._extra[i, time_index] = self.parameter("extra_expressions").evaluate(i, var_dic)

    def post_simulation(self):
        super().post_simulation()
        uses = self._uses()
        for carrier in CARRIERS:
            self.variable(carrier.lower()).values[:] = sum(
                (u.values for u in uses if u.carrier == carrier), np.zeros(self._n()))
        for service in self._services():
            self.variable(service.lower()).values[:] = sum(
                (u.values for u in uses if u.service == service and u.carrier != "AMBIENT"),
                np.zeros(self._n()))
        ren, nren, co2 = self._primary(uses)
        self.variable("primary_ren").values[:] = ren
        self.variable("primary_nren").values[:] = nren
        self.variable("primary_total").values[:] = ren + nren
        self.variable("CO2").values[:] = co2

    def _n(self):
        return self.project().parameter("n_time_steps").value

    # ______________________ Energy uses ______________________

    def get_uses(self):
        """Every energy use counted, as reported (transport as its own service).

        Returns:
            list: `opensimula.energy.Energy_use` items (W at each time step).
        """
        return self._uses()

    def _uses(self):
        uses = []
        for comp in self._consumers():
            uses += comp.get_energy_use()
        carrier = self.parameter("equipment_carrier").value
        for zone in self._zones():
            for u in zone.get_energy_use():
                uses.append(u._replace(carrier=carrier) if u.service == "EQUIPMENT" else u)
        p = self.parameter
        for i in range(len(getattr(self, "_extra", []))):
            uses.append(Energy_use(p("extra_carriers").value[i], p("extra_services").value[i],
                                   np.clip(self._extra[i], 0, None)))
        return uses

    def _primary(self, uses):
        factors = self.factors()
        n = self._n()
        ren, nren, co2 = np.zeros(n), np.zeros(n), np.zeros(n)
        for u in uses:
            if u.carrier in factors:
                f = factors[u.carrier]
                ren += u.values * f[0]
                nren += u.values * f[1]
                co2 += u.values * f[2] / 1000 * self._delta_t / 3600  # kg per time step
        return ren, nren, co2 * 3600 / self._delta_t  # kg/h

    # ______________________ Report ______________________

    def report(self, water_transport="SEPARATE", air_transport="SEPARATE",
               reference_heating=None, reference_cooling=None):
        """Tables of the energy use of the simulation, with the chosen hypotheses.

        Args:
            water_transport (str): "SEPARATE" (default), the pumps as their own
                service WATER_TRANSPORT; or "BY_MODE", the energy of each hour assigned
                to HEATING or COOLING by the mode of the system that moves the water
                (what runs with no heating or cooling stays in WATER_TRANSPORT).
            air_transport (str): the same for the fans (AIR_TRANSPORT).
            reference_heating (tuple, optional): (carrier, efficiency) of the generator
                that gives the heat without equipment (ideal systems, coils with no
                water system), e.g. ("NATURAL_GAS", 0.92). An ELECTRICITY one with
                efficiency > 1 is a heat pump: Q - E is counted as AMBIENT. Without
                it that heat is shown as THERMAL, out of the final and primary totals.
            reference_cooling (tuple, optional): (carrier, EER) for the cooling
                without equipment, e.g. ("ELECTRICITY", 2.6).

        Returns:
            opensimula.energy.Energy_report: tables (kWh, kg), shown as HTML in notebooks.
        """
        for key, value in (("water_transport", water_transport), ("air_transport", air_transport)):
            if value not in TRANSPORT_OPTIONS:
                raise ValueError(f"{key} must be one of {TRANSPORT_OPTIONS}, not {value!r}")
        if not hasattr(self, "_delta_t"):
            raise RuntimeError("report() needs the project simulated first")
        uses = self._assign_transport(self._uses(), water_transport, air_transport)
        uses, notes = self._reference_generators(uses, reference_heating, reference_cooling)
        to_kwh = self._delta_t / 3600 / 1000
        dates = pd.DatetimeIndex(self.project().dates())
        factors = self.factors()
        services = [s for s in self._services() if any(u.service == s for u in uses)]
        services = [s for s in services if sum(u.values.sum() for u in uses if u.service == s) > 0]

        # annual final energy: service x carrier
        annual = pd.DataFrame(0.0, index=services, columns=CARRIERS)
        for u in uses:
            if u.service in services:
                annual.loc[u.service, u.carrier] += u.values.sum() * to_kwh
        annual = annual.loc[:, annual.sum() > 0]
        final_carriers = [c for c in annual.columns if c not in ("AMBIENT", "THERMAL")]
        annual["TOTAL"] = annual[final_carriers].sum(axis=1)
        annual.loc["TOTAL"] = annual.sum()
        annual.index.name, annual.columns.name = "service", "carrier"

        # monthly final energy
        def monthly(key, names):
            series = {}
            for name in names:
                values = sum((u.values for u in uses if getattr(u, key) == name
                              and (key == "carrier" or u.carrier in final_carriers)),
                             np.zeros(len(dates)))
                series[name] = values * to_kwh
            df = pd.DataFrame(series, index=dates).resample("ME").sum()
            df.index = df.index.strftime("%b %Y")
            df.index.name = "month"
            df = df.loc[:, df.sum() > 0]
            if key == "carrier":
                df["TOTAL"] = df[[c for c in df.columns if c in final_carriers]].sum(axis=1)
            else:
                df["TOTAL"] = df.sum(axis=1)
            df.loc["Total"] = df.sum()
            return df

        monthly_carriers = monthly("carrier", [c for c in annual.columns if c != "TOTAL"])
        monthly_services = monthly("service", [s for s in services
                                               if annual.loc[s, final_carriers].sum() > 0])

        # indicators by service
        rows = {}
        for s in services:
            final = ren = nren = co2 = 0.0
            for u in uses:
                if u.service == s and u.carrier in factors:
                    e = u.values.sum() * to_kwh
                    f = factors[u.carrier]
                    final += e if u.carrier != "AMBIENT" else 0
                    ren += e * f[0]
                    nren += e * f[1]
                    co2 += e * f[2]
            rows[s] = (final, ren, nren, ren + nren, co2)
        indicators = pd.DataFrame.from_dict(
            rows, orient="index",
            columns=["Final [kWh]", "Primary ren [kWh]", "Primary nren [kWh]",
                     "Primary total [kWh]", "CO2 [kg]"])
        indicators.loc["TOTAL"] = indicators.sum()
        indicators.index.name = "service"

        hypotheses = {
            "factors": self.parameter("conversion_factors").value
            + (" + custom" if self.parameter("custom_carriers").value else ""),
            "water_transport": water_transport,
            "air_transport": air_transport,
            "reference_heating": reference_heating,
            "reference_cooling": reference_cooling,
        }
        notes = notes + [
            "Final energy totals do not include AMBIENT (energy taken from the environment "
            "by heat pumps, renewable primary energy) nor THERMAL (heat without equipment).",
        ]
        return Energy_report(f"Energy indicators: {self.parameter('name').value}", annual,
                             monthly_carriers, monthly_services, indicators,
                             self.reference_area(), hypotheses, notes)

    def _assign_transport(self, uses, water, air):
        result = []
        for u in uses:
            option = {"WATER_TRANSPORT": water, "AIR_TRANSPORT": air}.get(u.service)
            if option == "BY_MODE" and u.mode is not None:
                heating, cooling = u.mode == 1, u.mode == -1
                result.append(u._replace(service="HEATING", values=np.where(heating, u.values, 0.0)))
                result.append(u._replace(service="COOLING", values=np.where(cooling, u.values, 0.0)))
                result.append(u._replace(values=np.where(heating | cooling, 0.0, u.values)))
            else:
                result.append(u)
        return result

    def _reference_generators(self, uses, heating, cooling):
        result, notes = [], []
        refs = {"HEATING_WITHOUT_EQUIPMENT": ("HEATING", heating),
                "COOLING_WITHOUT_EQUIPMENT": ("COOLING", cooling)}
        for u in uses:
            if u.carrier == "THERMAL" and u.service in refs and refs[u.service][1] is not None:
                service, (carrier, efficiency) = refs[u.service][0], refs[u.service][1]
                if carrier not in FINAL_CARRIERS or efficiency <= 0:
                    raise ValueError(f"reference generator {(carrier, efficiency)} not valid")
                final = u.values / efficiency
                result.append(Energy_use(carrier, service, final))
                if service == "HEATING" and carrier == "ELECTRICITY" and efficiency > 1:
                    result.append(Energy_use("AMBIENT", service, u.values - final))
            else:
                result.append(u)
        if any(u.carrier == "THERMAL" and u.values.sum() > 0 for u in result):
            notes.append("There is heat without equipment (THERMAL): give reference_heating / "
                         "reference_cooling to count it as final and primary energy.")
        return result, notes
