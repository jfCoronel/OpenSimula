"""Energy carriers and services used to report the energy use of the components.

Every component that uses energy reports it with ``Component.get_energy_use()``:
a list of ``Energy_use(carrier, service, values)``, where ``values`` is the power
(W) at each time step of the simulation, positive. ``Energy_indicators`` adds them
up, converts them to primary energy and CO₂ and splits them in its report.
"""

from typing import NamedTuple

import numpy as np

# Carriers: what is used. Fuels as in Boiler.fuel; AMBIENT is the energy taken
# from the environment by heat pumps (renewable); THERMAL is heat supplied with no
# equipment behind it (ideal systems, coils with an unknown water source), not
# final energy until a hypothesis gives it a generator.
CARRIERS = [
    "ELECTRICITY",
    "NATURAL_GAS",
    "LPG",
    "DIESEL",
    "BIOMASS",
    "AMBIENT",
    "SOLAR_THERMAL",
    "THERMAL",
]
# Renewable energy taken from the environment on site (heat pumps, solar collectors):
# it counts in primary energy (renewable) but not in the final energy totals
ENVIRONMENT_CARRIERS = ("AMBIENT", "SOLAR_THERMAL")

# Services: what it is used for. Pumps and fans are their own services; splitting
# them among heating, cooling or DHW is a hypothesis of the report.
SERVICES = [
    "HEATING",
    "COOLING",
    "DHW",
    "WATER_TRANSPORT",
    "AIR_TRANSPORT",
    "LIGHTING",
    "EQUIPMENT",
    "HEATING_WITHOUT_EQUIPMENT",
    "COOLING_WITHOUT_EQUIPMENT",
]


class Energy_use(NamedTuple):
    """Power used by a component for one carrier and service.

    Attributes:
        carrier (str): one of ``CARRIERS``.
        service (str): one of ``SERVICES`` (or a user service, e.g. "DHW").
        values (numpy.ndarray): power (W) at each time step, positive.
        mode (numpy.ndarray or None): for the transport services, what the system
            does at each time step (1 heating, -1 cooling, 2 domestic hot water, 0
            none of them), used by the report to assign the transport to a service.
    """

    carrier: str
    service: str
    values: np.ndarray
    mode: np.ndarray = None


def positive(values):
    """Positive part of an array, as a new float array."""
    return np.clip(np.asarray(values, dtype=float), 0, None)


def mode_from_state(state):
    """Mode (1 heating, -1 cooling, 0 neither) from the state of an air system
    (1, 2 heating; -1, -2 cooling; 0 off; 3 venting)."""
    state = np.asarray(state)
    return np.where(np.isin(state, [1, 2]), 1, np.where(np.isin(state, [-1, -2]), -1, 0))


def mode_from_plant(mode):
    """Mode (1 heating, -1 cooling, 0 neither) from the mode of a water system
    (1 heating, -1 cooling, 0 off, 2 standby)."""
    mode = np.asarray(mode)
    return np.where(mode == 1, 1, np.where(mode == -1, -1, 0))


def split_dhw(carrier, service, values, dhw_share, mode=None):
    """Split a use between its service and DHW by the DHW share of each time step.

    Args:
        carrier (str): carrier of the use.
        service (str): service of the part that is not DHW (e.g. HEATING,
            WATER_TRANSPORT).
        values (numpy.ndarray): power (W) at each time step.
        dhw_share (numpy.ndarray): fraction (0-1) of the use that is DHW.
        mode (numpy.ndarray, optional): mode of a transport use; its DHW part gets
            mode 2 and keeps the service.

    Returns:
        list: one or two `Energy_use` (the DHW part only if not all zero).
    """
    values = np.asarray(values, dtype=float)
    share = np.asarray(dhw_share, dtype=float)
    rest = values * (1 - share)
    uses = [Energy_use(carrier, service, rest, mode)]
    if np.any(share > 0):
        if mode is None:
            uses.append(Energy_use(carrier, "DHW", values * share))
        else:
            uses.append(Energy_use(carrier, service, values * share, np.where(share > 0, 2, 0)))
    return uses


def where(condition, values):
    """Values where condition is true, 0 elsewhere, as a new float array."""
    return np.where(condition, np.asarray(values, dtype=float), 0.0)


# Conversion factors of final energy: (fp,ren, fp,nren, kg CO2) per kWh of final
# energy. Documento reconocido del RITE "Factores de emisión de CO2 y coeficientes
# de paso a energía primaria de diferentes fuentes de energía final consumidas en el
# sector de edificios en España" (in force since 14/01/2016), section 8. Fuels on
# the LHV, as the boilers. BIOMASS is densified biomass (pellets).
FUEL_FACTORS = {
    "NATURAL_GAS": (0.005, 1.190, 0.252),
    "LPG": (0.003, 1.201, 0.254),
    "DIESEL": (0.003, 1.179, 0.311),
    "BIOMASS": (1.028, 0.085, 0.018),
}
ELECTRICITY_FACTORS = {
    "PENINSULA": (0.414, 1.954, 0.331),
    "BALEARES": (0.082, 2.968, 0.932),
    "CANARIAS": (0.070, 2.924, 0.776),
    "CEUTA_MELILLA": (0.072, 2.718, 0.721),
    "NATIONAL": (0.396, 2.007, 0.357),  # statistics only
    "EXTRAPENINSULAR": (0.075, 2.937, 0.833),  # statistics only
}
# Energy taken from the environment by heat pumps and solar thermal collectors (on
# site): renewable
AMBIENT_FACTORS = (1.0, 0.0, 0.0)
SOLAR_THERMAL_FACTORS = (1.0, 0.0, 0.0)


def conversion_factors(region="PENINSULA"):
    """Conversion factors of every carrier for a region (RITE 2016).

    Args:
        region (str): key of ``ELECTRICITY_FACTORS``.

    Returns:
        dict: {carrier: (fp_ren, fp_nren, kg CO2)} per kWh of final energy; THERMAL
            (heat without equipment) has no factors.
    """
    factors = {"ELECTRICITY": ELECTRICITY_FACTORS[region], "AMBIENT": AMBIENT_FACTORS,
               "SOLAR_THERMAL": SOLAR_THERMAL_FACTORS}
    factors.update(FUEL_FACTORS)
    return factors


TABLE_STYLE = """<style>
.os-energy-report {font-family: sans-serif; font-size: 13px}
.os-energy-report h3 {margin: 14px 0 4px 0; font-size: 15px}
.os-energy-report table {border-collapse: collapse; margin-bottom: 6px}
.os-energy-report th, .os-energy-report td {padding: 3px 9px; border-bottom: 1px solid #ccc}
.os-energy-report td {text-align: right}
.os-energy-report th {text-align: left}
.os-energy-report tr:last-child td, .os-energy-report tr:last-child th {font-weight: bold}
.os-energy-report p.note {color: #666; font-size: 12px; margin: 2px 0}
</style>"""


class Energy_report:
    """Report of an Energy_indicators component (what ``report()`` returns).

    Shows as formatted tables in notebooks (Jupyter, marimo) and has ``to_html()``.
    Energies in kWh, CO2 in kg.

    Attributes:
        annual (pandas.DataFrame): final energy of the period by service (rows) and
            carrier (columns), with a "TOTAL" row and column (final energy: AMBIENT, SOLAR_THERMAL
            and THERMAL are not in the totals).
        monthly_carriers (pandas.DataFrame): final energy by month and carrier.
        monthly_services (pandas.DataFrame): final energy by month and service.
        indicators (pandas.DataFrame): by service: final energy, primary energy
            (renewable, non-renewable, total) and CO2.
        indicators_per_area (pandas.DataFrame or None): the same per m² of the
            reference area (None if it is 0).
        summary (dict): reference area, totals, renewable share and the hypotheses.
    """

    def __init__(self, title, annual, monthly_carriers, monthly_services, indicators,
                 area, hypotheses, notes):
        self.title = title
        self.annual = annual
        self.monthly_carriers = monthly_carriers
        self.monthly_services = monthly_services
        self.indicators = indicators
        self.indicators_per_area = indicators / area if area > 0 else None
        if self.indicators_per_area is not None:
            self.indicators_per_area.columns = [
                c.replace("[kWh]", "[kWh/m²]").replace("[kg]", "[kg/m²]")
                for c in indicators.columns
            ]
        total = indicators.loc["TOTAL"]
        tot = total["Primary total [kWh]"]
        self.summary = {
            "reference_area": float(area),
            "final_energy": float(total["Final [kWh]"]),
            "primary_nren": float(total["Primary nren [kWh]"]),
            "primary_total": float(tot),
            "CO2": float(total["CO2 [kg]"]),
            "renewable_share": float(1 - total["Primary nren [kWh]"] / tot) if tot > 0 else 0.0,
            **hypotheses,
        }
        self.notes = notes

    def _summary_lines(self):
        s = self.summary
        a = s["reference_area"]
        lines = [f"Reference area: {a:,.1f} m²"]
        for key, label, unit in (("primary_nren", "Primary energy, non-renewable", "kWh"),
                                 ("primary_total", "Primary energy, total", "kWh"),
                                 ("CO2", "CO₂ emissions", "kg")):
            per = f" ({s[key] / a:,.1f} {unit}/m²)" if a > 0 else ""
            lines.append(f"{label}: {s[key]:,.0f} {unit}{per}")
        lines.append(f"Renewable share of primary energy: {s['renewable_share']:.1%}")
        lines.append("Hypotheses: " + ", ".join(
            f"{k} = {v}" for k, v in s.items()
            if k in ("factors", "water_transport", "air_transport",
                     "reference_heating", "reference_cooling")))
        return lines

    def _tables(self):
        tables = [("Indicators by service", self.indicators)]
        if self.indicators_per_area is not None:
            tables.append(("Indicators by service per m²", self.indicators_per_area))
        tables += [("Final energy by service and carrier [kWh]", self.annual),
                   ("Final energy by month and carrier [kWh]", self.monthly_carriers),
                   ("Final energy by month and service [kWh]", self.monthly_services)]
        return tables

    def to_html(self):
        """The report as an HTML fragment (styles included).

        Returns:
            str: HTML.
        """
        import html
        parts = [TABLE_STYLE, '<div class="os-energy-report">',
                 f"<h3>{html.escape(self.title)}</h3>"]
        parts += [f"<p>{html.escape(line)}</p>" for line in self._summary_lines()]
        for title, df in self._tables():
            parts.append(f"<h3>{html.escape(title)}</h3>")
            parts.append(df.to_html(float_format=lambda x: f"{x:,.1f}", border=0))
        parts += [f'<p class="note">{html.escape(n)}</p>' for n in self.notes]
        parts.append("</div>")
        return "\n".join(parts)

    def _repr_html_(self):
        return self.to_html()

    def __repr__(self):
        import pandas as pd
        out = [self.title, *self._summary_lines()]
        with pd.option_context("display.float_format", "{:,.1f}".format, "display.width", 160,
                               "display.max_columns", 30):
            for title, df in self._tables():
                out += ["", title, df.to_string()]
        out += ["", *self.notes]
        return "\n".join(out)
