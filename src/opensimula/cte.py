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
# HE4 3.1: renewable contribution to the DHW demand (with distribution, storage and
# recirculation losses); 60 % below 5000 l/day; applies above 100 l/day (Anejo F)
HE4_SHARE = 0.70
HE4_SHARE_REDUCED = 0.60
HE4_REDUCED_BELOW = 5000  # l/day
HE4_APPLIES_ABOVE = 100  # l/day
# HE4 3.1.4: minimum SCOP_dhw of electric heat pumps for their renewable contribution
HE4_MIN_SCOP_DHW = 2.5

# Anejo F: reference DHW demand at 60 °C
DHW_LITRES_PER_PERSON_RESIDENTIAL = 28
# table a: minimum occupation by number of bedrooms (1, 2, 3, 4, 5, 6, more than 6)
DHW_PERSONS_BY_BEDROOMS = [1.5, 3, 4, 5, 6, 6, 7]
# table b: centralisation factor (centralised DHW of several dwellings), up to N dwellings
DHW_CENTRALISATION = [(3, 1.0), (10, 0.95), (20, 0.90), (50, 0.85), (75, 0.80), (100, 0.75),
                      (float("inf"), 0.70)]
# table c: l/day·person for uses other than residencial privado
DHW_LITRES_PER_PERSON_OTHER = {
    "Hospitales y clínicas": 55, "Ambulatorio y centro de salud": 41, "Hotel *****": 69,
    "Hotel ****": 55, "Hotel ***": 41, "Hotel/hostal **": 34, "Camping": 21,
    "Hostal/pensión *": 28, "Residencia": 41, "Centro penitenciario": 28, "Albergue": 24,
    "Vestuarios/Duchas colectivas": 21, "Escuela sin ducha": 4, "Escuela con ducha": 21,
    "Cuarteles": 28, "Fábricas y talleres": 21, "Oficinas": 2, "Gimnasios": 21,
    "Restaurantes": 8, "Cafeterías": 1,
}

# Anejo G table a: altitude (m) and monthly mean mains water temperature (°C) of the
# province capitals
MAINS_TEMPERATURES = {
    "A Coruña": (26, [10, 10, 11, 12, 13, 14, 16, 16, 15, 14, 12, 11]),
    "Albacete": (686, [7, 8, 9, 11, 14, 17, 19, 19, 17, 13, 9, 7]),
    "Alicante/Alacant": (8, [11, 12, 13, 14, 16, 18, 20, 20, 19, 16, 13, 12]),
    "Almería": (16, [12, 12, 13, 14, 16, 18, 20, 21, 19, 17, 14, 12]),
    "Ávila": (1131, [6, 6, 7, 9, 11, 14, 17, 16, 14, 11, 8, 6]),
    "Badajoz": (186, [9, 10, 11, 13, 15, 18, 20, 20, 18, 15, 12, 9]),
    "Barcelona": (12, [9, 10, 11, 12, 14, 17, 19, 19, 17, 15, 12, 10]),
    "Bilbao/Bilbo": (6, [9, 10, 10, 11, 13, 15, 17, 17, 16, 14, 11, 10]),
    "Burgos": (929, [5, 6, 7, 9, 11, 13, 16, 16, 14, 11, 7, 6]),
    "Cáceres": (459, [9, 10, 11, 12, 14, 18, 21, 20, 19, 15, 11, 9]),
    "Cádiz": (14, [12, 12, 13, 14, 16, 18, 19, 20, 19, 17, 14, 12]),
    "Castellón/Castelló": (27, [10, 11, 12, 13, 15, 18, 19, 20, 18, 16, 12, 11]),
    "Ceuta": (40, [11, 11, 12, 13, 14, 16, 18, 18, 17, 15, 13, 12]),
    "Ciudad Real": (628, [7, 8, 10, 11, 14, 17, 20, 20, 17, 13, 10, 7]),
    "Córdoba": (106, [10, 11, 12, 14, 16, 19, 21, 21, 19, 16, 12, 10]),
    "Cuenca": (999, [6, 7, 8, 10, 13, 16, 18, 18, 16, 12, 9, 7]),
    "Girona": (70, [8, 9, 10, 11, 14, 16, 19, 18, 17, 14, 10, 9]),
    "Granada": (683, [8, 9, 10, 12, 14, 17, 20, 19, 17, 14, 11, 8]),
    "Guadalajara": (685, [7, 8, 9, 11, 14, 17, 19, 19, 16, 13, 9, 7]),
    "Huelva": (30, [12, 12, 13, 14, 16, 18, 20, 20, 19, 17, 14, 12]),
    "Huesca": (488, [7, 8, 10, 11, 14, 16, 19, 18, 17, 13, 9, 7]),
    "Jaén": (568, [9, 10, 11, 13, 16, 19, 21, 21, 19, 15, 12, 9]),
    "Las Palmas de Gran Canaria": (13, [15, 15, 16, 16, 17, 18, 19, 19, 19, 18, 17, 16]),
    "León": (838, [6, 6, 8, 9, 12, 14, 16, 16, 15, 11, 8, 6]),
    "Lleida": (182, [7, 9, 10, 12, 15, 17, 20, 19, 17, 14, 10, 7]),
    "Logroño": (385, [7, 8, 10, 11, 13, 16, 18, 18, 16, 13, 10, 8]),
    "Lugo": (454, [7, 8, 9, 10, 11, 13, 15, 15, 14, 12, 9, 8]),
    "Madrid": (655, [8, 8, 10, 12, 14, 17, 20, 19, 17, 13, 10, 8]),
    "Málaga": (11, [12, 12, 13, 14, 16, 18, 20, 20, 19, 16, 14, 12]),
    "Melilla": (15, [12, 13, 13, 14, 16, 18, 20, 20, 19, 17, 14, 13]),
    "Murcia": (39, [11, 11, 12, 13, 15, 17, 19, 20, 18, 16, 13, 11]),
    "Ourense": (139, [8, 10, 11, 12, 14, 16, 18, 18, 17, 13, 11, 9]),
    "Oviedo": (232, [9, 9, 10, 10, 12, 14, 15, 16, 15, 13, 10, 9]),
    "Palencia": (734, [6, 7, 8, 10, 12, 15, 17, 17, 15, 12, 9, 6]),
    "Palma de Mallorca": (15, [11, 11, 12, 13, 15, 18, 20, 20, 19, 17, 14, 12]),
    "Pamplona/Iruña": (490, [7, 8, 9, 10, 12, 15, 17, 17, 16, 13, 9, 7]),
    "Pontevedra": (27, [10, 11, 11, 13, 14, 16, 17, 17, 16, 14, 12, 10]),
    "Salamanca": (800, [6, 7, 8, 10, 12, 15, 17, 17, 15, 12, 8, 6]),
    "San Sebastián": (12, [9, 9, 10, 11, 12, 14, 16, 16, 15, 14, 11, 9]),
    "Santa Cruz de Tenerife": (5, [15, 15, 16, 16, 17, 18, 20, 20, 20, 18, 17, 16]),
    "Santander": (11, [10, 10, 11, 11, 13, 15, 16, 16, 16, 14, 12, 10]),
    "Segovia": (1002, [6, 7, 8, 10, 12, 15, 18, 18, 15, 12, 8, 6]),
    "Sevilla": (11, [11, 11, 13, 14, 16, 19, 21, 21, 20, 16, 13, 11]),
    "Soria": (1063, [5, 6, 7, 9, 11, 14, 17, 16, 14, 11, 8, 6]),
    "Tarragona": (69, [10, 11, 12, 14, 16, 18, 20, 20, 19, 16, 12, 11]),
    "Teruel": (912, [6, 7, 8, 10, 12, 15, 18, 17, 15, 12, 8, 6]),
    "Toledo": (629, [8, 9, 11, 12, 15, 18, 21, 20, 18, 14, 11, 8]),
    "Valencia": (13, [10, 11, 12, 13, 15, 17, 19, 20, 18, 16, 13, 11]),
    "Valladolid": (698, [6, 8, 9, 10, 12, 15, 18, 18, 16, 12, 9, 7]),
    "Vitoria-Gasteiz": (540, [7, 7, 8, 10, 12, 14, 16, 16, 14, 12, 8, 7]),
    "Zamora": (649, [6, 8, 9, 10, 13, 16, 18, 18, 16, 12, 9, 7]),
    "Zaragoza": (199, [8, 9, 10, 12, 15, 17, 20, 19, 17, 14, 10, 8]),
}

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


def mains_temperatures(capital, altitude=None):
    """Monthly mean mains water temperature of the DB-HE (Anejo G), for the
    ``mains_monthly_temperatures`` of a DHW_demand.

    Args:
        capital (str): province capital, as in ``MAINS_TEMPERATURES`` (e.g. "Madrid").
        altitude (float, optional): altitude of the place (m), if not the capital: the
            temperatures are corrected with TAFY = TAFCP − B·Az (B = 0.0066 from October
            to March, 0.0033 from April to September; Az = altitude − that of the capital).

    Returns:
        list: 12 temperatures (°C), January first.
    """
    if capital not in MAINS_TEMPERATURES:
        raise ValueError(f"{capital!r} is not a province capital of Anejo G: "
                         + ", ".join(MAINS_TEMPERATURES))
    z_capital, T = MAINS_TEMPERATURES[capital]
    if altitude is None:
        return list(T)
    dz = altitude - z_capital
    return [t - (0.0033 if 4 <= m <= 9 else 0.0066) * dz for m, t in enumerate(T, start=1)]


def dhw_reference_demand(bedrooms=None, dwellings=None, centralised=False, persons=None,
                         use=None):
    """Reference DHW demand of the DB-HE (Anejo F), in l/day at 60 °C, without the
    losses (distribution, storage and recirculation, to be added).

    Residencial privado: 28 l/day·person with the minimum occupation of table a by the
    bedrooms of each dwelling and, for a centralised installation, the centralisation
    factor of table b. Other uses: the l/day·person of table c times the persons.

    Args:
        bedrooms (int or list, optional): bedrooms of the dwelling, or of each dwelling.
        dwellings (int, optional): number of dwellings with ``bedrooms`` each (if it is
            an int).
        centralised (bool): one DHW installation for all the dwellings.
        persons (float, optional): persons, for uses other than residencial privado
            (or to give the occupation of a dwelling instead of its bedrooms).
        use (str, optional): criterion of table c (e.g. "Oficinas", "Hotel ***"), for
            uses other than residencial privado.

    Returns:
        float: demand (l/day at 60 °C).
    """
    if use is not None:
        if use not in DHW_LITRES_PER_PERSON_OTHER:
            raise ValueError(f"{use!r} is not in table c-Anejo F: "
                             + ", ".join(DHW_LITRES_PER_PERSON_OTHER))
        return DHW_LITRES_PER_PERSON_OTHER[use] * (persons or 0)
    if bedrooms is None:
        return DHW_LITRES_PER_PERSON_RESIDENTIAL * (persons or 0)
    rooms = [bedrooms] * (dwellings or 1) if isinstance(bedrooms, int) else list(bedrooms)
    people = sum(DHW_PERSONS_BY_BEDROOMS[min(max(b, 1), 7) - 1] for b in rooms)
    factor = 1.0
    if centralised:
        factor = next(f for n, f in DHW_CENTRALISATION if len(rooms) <= n)
    return DHW_LITRES_PER_PERSON_RESIDENTIAL * people * factor


def he4_minimum_share(daily_demand):
    """Minimum renewable share of the DHW demand of HE4 (0 if HE4 does not apply).

    Args:
        daily_demand (float): DHW demand (l/day at 60 °C, Anejo F).

    Returns:
        float: 0.70, 0.60 below 5000 l/day, 0 at 100 l/day or less.
    """
    if daily_demand <= HE4_APPLIES_ABOVE:
        return 0.0
    return HE4_SHARE_REDUCED if daily_demand < HE4_REDUCED_BELOW else HE4_SHARE


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

    def __init__(self, title, checks, services, summary, notes, tables=None):
        self.title = title
        self.checks = checks
        self.services = services
        self.summary = summary
        self.notes = notes
        self.tables = tables or []  # more (title, DataFrame), e.g. the HE4 contribution

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
        sections = s.get("sections", "HE0")
        lines.append((f"✔ Complies with {sections}" if s["complies"]
                      else f"✘ Does not comply with {sections}"))
        return lines

    def _tables(self, html_marks=False):
        checks = self.checks.copy()
        def mark(ok):
            text, colour = MARKS[bool(ok)]
            if html_marks:
                return f'<span style="color:{colour};font-weight:bold">{html.escape(text)}</span>'
            return text
        checks["complies"] = checks["complies"].map(mark)
        return [(f"{self.summary.get('sections', 'HE0')} requirements", checks),
                ("EPB services counted [per m²]", self.services), *self.tables]

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
