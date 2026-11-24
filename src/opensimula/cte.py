"""Limits of the Spanish CTE DB-HE 2019 (articulado 14/06/2022) and the report of
CTE_compliance.

Values from the DB-HE con comentarios (22/12/2023) and the Guía de aplicación
DB-HE 2019 (junio 2022).
"""

import html

from opensimula.energy import TABLE_STYLE

WINTER_ZONES = ["α", "A", "B", "C", "D", "E"]

# HE0 table 3.1.a: C_ep,nren,lim [kWh/m²·year], residencial privado
CEP_NREN_RESIDENTIAL = {
    "NEW_OR_EXTENSION": [20, 25, 28, 32, 38, 43],
    "CHANGE_OF_USE_OR_REFORM": [40, 50, 55, 65, 70, 80],
}
# HE0 table 3.2.a: C_ep,tot,lim, residencial privado
CEP_TOT_RESIDENTIAL = {
    "NEW_OR_EXTENSION": [40, 50, 56, 64, 76, 86],
    "CHANGE_OF_USE_OR_REFORM": [55, 75, 80, 90, 105, 115],
}
# HE0 tables 3.1.b and 3.2.b: other uses, base + k · C_FI
CEP_NREN_OTHER = ([70, 55, 50, 35, 20, 10], 8)
CEP_TOT_OTHER = ([165, 155, 150, 140, 130, 120], 9)
# Extrapeninsular territory (Illes Balears, Canarias, Ceuta y Melilla)
EXTRAPENINSULAR_NREN = {"RESIDENTIAL_PRIVATE": 1.25, "OTHER": 1.40}
EXTRAPENINSULAR_TOT = {"RESIDENTIAL_PRIVATE": 1.15, "OTHER": 1.40}
EXTRAPENINSULAR_REGIONS = ["BALEARES", "CANARIAS", "CEUTA_MELILLA", "EXTRAPENINSULAR"]
# HE0 4.1.6: hours outside setpoint, at most 4 % of the occupation time, with a
# margin of 1 °C (Anejo A)
HOURS_OUTSIDE_LIMIT = 0.04
HOURS_OUTSIDE_TOLERANCE = 1.0
# HE0 table 4.5: reference systems (residencial privado)
REFERENCE_HEATING_EFFICIENCY_HHV = 0.92  # natural gas, on the higher heating value
REFERENCE_COOLING_EER = 2.60  # electricity
# Carga interna media levels (Anejo A, table a)
INTERNAL_LOAD_LEVELS = [(6, "low"), (9, "medium"), (12, "high"), (float("inf"), "very high")]
# Anejo D table c: hourly profile of the DHW use of dwellings, % of the daily demand
DHW_PROFILE_RESIDENTIAL = [1, 0, 0, 0, 0, 1, 3, 10, 7, 7, 6, 6, 5, 5, 4, 3, 4, 4, 5, 7, 6,
                           6, 5, 5]
# how the result of a requirement is shown (text and colour)
MARKS = {True: ("✔ complies", "#1a7f37"), False: ("✘ does not comply", "#cf222e")}


def winter_zone(climate_zone):
    """Winter zone letter of a climate zone such as "B4", "α3" or "alpha3".

    Args:
        climate_zone (str): climate zone of the DB-HE (Anejo B).

    Returns:
        str: one of ``WINTER_ZONES``, None if the zone is not valid.
    """
    z = climate_zone.strip()
    if z.lower().startswith("alpha"):
        z = "α" + z[5:]
    if len(z) != 2 or z[0] not in WINTER_ZONES or z[1] not in "1234":
        return None
    return z[0]


def internal_load_level(c_fi):
    """Level of the carga interna media (low, medium, high, very high)."""
    for limit, name in INTERNAL_LOAD_LEVELS:
        if c_fi < limit:
            return name


def dhw_profile_schedules(name="dhw_profile_residential"):
    """Schedules with the hourly DHW profile of dwellings (DB-HE, Anejo D table c).

    A Day_schedule, a Week_schedule and a Year_schedule (the last one called ``name``)
    whose variable ``values`` is the fraction of the daily volume used in each hour
    (it sums 1 over the day). The DHW_demand of a dwelling with 120 l/day then has
    ``input_variables: ["f = <name>.values"]`` and ``volume_flow: "120 * f"`` (l/h).

    Args:
        name (str): name of the Year_schedule; the others are ``<name>_day`` and
            ``<name>_week``.

    Returns:
        list: the three components as dicts, to add to the ``components`` of a project.
    """
    return [
        {"type": "Day_schedule", "name": f"{name}_day",
         "description": "DHW use of dwellings, fraction of the daily volume per hour "
                        "(DB-HE, Anejo D table c)",
         "time_steps": [3600] * 23, "values": [v / 100 for v in DHW_PROFILE_RESIDENTIAL],
         "interpolation": "STEP"},
        {"type": "Week_schedule", "name": f"{name}_week", "days_schedules": [f"{name}_day"]},
        {"type": "Year_schedule", "name": name, "periods": [],
         "weeks_schedules": [f"{name}_week"]},
    ]


def he0_limits(climate_zone, building_use, intervention, c_fi=0.0, extrapeninsular=False):
    """Limits of C_ep,nren and C_ep,tot of HE0 (kWh/m²·year).

    Args:
        climate_zone (str): e.g. "B4".
        building_use (str): "RESIDENTIAL_PRIVATE" or "OTHER".
        intervention (str): "NEW_OR_EXTENSION" or "CHANGE_OF_USE_OR_REFORM" (other
            uses have the same limits for both).
        c_fi (float): carga interna media (W/m²), other uses only.
        extrapeninsular (bool): Illes Balears, Canarias, Ceuta or Melilla.

    Returns:
        tuple: (C_ep,nren,lim, C_ep,tot,lim).
    """
    i = WINTER_ZONES.index(winter_zone(climate_zone))
    if building_use == "RESIDENTIAL_PRIVATE":
        nren = CEP_NREN_RESIDENTIAL[intervention][i]
        tot = CEP_TOT_RESIDENTIAL[intervention][i]
    else:
        nren = CEP_NREN_OTHER[0][i] + CEP_NREN_OTHER[1] * c_fi
        tot = CEP_TOT_OTHER[0][i] + CEP_TOT_OTHER[1] * c_fi
    if extrapeninsular:
        nren *= EXTRAPENINSULAR_NREN[building_use]
        tot *= EXTRAPENINSULAR_TOT[building_use]
    return nren, tot


class CTE_report:
    """Report of a CTE_compliance component (what ``report()`` returns).

    Shows as formatted tables in notebooks (Jupyter, marimo) and has ``to_html()``.

    Attributes:
        checks (pandas.DataFrame): one row per requirement: value, limit, unit and
            whether it complies.
        services (pandas.DataFrame): the EPB services counted: final energy, primary
            energy (non-renewable, total) and CO2 per m².
        summary (dict): the data of the verification (zone, use, intervention, area,
            C_FI, factors...) and ``complies`` (all the requirements).
        notes (list): what was assumed or left out.
    """

    def __init__(self, title, checks, services, summary, notes):
        self.title = title
        self.checks = checks
        self.services = services
        self.summary = summary
        self.notes = notes

    def _summary_lines(self):
        s = self.summary
        lines = [
            f"Climate zone {s['climate_zone']}, {s['building_use']}, {s['intervention']}"
            + (", extrapeninsular" if s["extrapeninsular"] else ""),
            f"Reference area: {s['reference_area']:,.1f} m²",
        ]
        if s["building_use"] == "OTHER":
            lines.append(f"Carga interna media C_FI: {s['c_fi']:.2f} W/m² "
                         f"({internal_load_level(s['c_fi'])}, {s['c_fi_source']})")
        lines.append(("✔ Complies with HE0" if s["complies"] else "✘ Does not comply with HE0"))
        return lines

    def _tables(self, html_marks=False):
        checks = self.checks.copy()
        def mark(ok):
            text, colour = MARKS[bool(ok)]
            if html_marks:
                return f'<span style="color:{colour};font-weight:bold">{html.escape(text)}</span>'
            return text
        checks["complies"] = checks["complies"].map(mark)
        return [("HE0 requirements", checks),
                ("EPB services counted [per m²]", self.services)]

    def to_html(self):
        """The report as an HTML fragment (styles included).

        Returns:
            str: HTML.
        """
        parts = [TABLE_STYLE, '<div class="os-energy-report">',
                 f"<h3>{html.escape(self.title)}</h3>"]
        lines = self._summary_lines()
        colour = MARKS[bool(self.summary["complies"])][1]
        parts += [f"<p>{html.escape(line)}</p>" for line in lines[:-1]]
        parts.append(f'<p style="color:{colour};font-weight:bold">{html.escape(lines[-1])}</p>')
        for title, df in self._tables(html_marks=True):
            parts.append(f"<h3>{html.escape(title)}</h3>")
            parts.append(df.to_html(float_format=lambda x: f"{x:,.2f}", border=0, na_rep="",
                                    escape=False))
        parts += [f'<p class="note">{html.escape(n)}</p>' for n in self.notes]
        parts.append("</div>")
        return "\n".join(parts)

    def _repr_html_(self):
        return self.to_html()

    def __repr__(self):
        import pandas as pd
        out = [self.title, *self._summary_lines()]
        with pd.option_context("display.float_format", "{:,.2f}".format, "display.width", 160):
            for title, df in self._tables():
                out += ["", title, df.to_string(na_rep="")]
        out += ["", *self.notes]
        return "\n".join(out)
