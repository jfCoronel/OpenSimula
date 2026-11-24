"""Zone control reported by the systems and the comfort report.

Every system that controls the temperature of zones reports it with
``Component.get_zone_setpoints()``: a list of ``Zone_control(zone,
heating_setpoint, cooling_setpoint, on)`` with the values of every time step.
``Comfort_indicators`` uses them to count the hours each zone is outside its
setpoints.
"""

from typing import Any, NamedTuple

import numpy as np

from opensimula.energy import TABLE_STYLE


class Zone_control(NamedTuple):
    """Setpoints a system keeps in a zone.

    Attributes:
        zone (Component): the zone (Space or Load_space).
        heating_setpoint (numpy.ndarray): °C at each time step.
        cooling_setpoint (numpy.ndarray): °C at each time step.
        on (numpy.ndarray): bool, the system is on at each time step.
    """

    zone: Any
    heating_setpoint: np.ndarray
    cooling_setpoint: np.ndarray
    on: np.ndarray


class Comfort_report:
    """Report of a Comfort_indicators component (what ``report()`` returns).

    Shows as formatted tables in notebooks (Jupyter, marimo) and has ``to_html()``.

    Attributes:
        zones (pandas.DataFrame): by zone, "TOTAL" (zone-hours) and "BUILDING" (each
            hour once, when any zone is counted or outside): hours counted, hours above
            and below the setpoints (beyond the tolerance), their share, degree-hours,
            maximum and minimum temperatures while counted.
        monthly (pandas.DataFrame): hours outside the setpoints by month and zone, with
            the zone-hours ("TOTAL") and the building hours ("BUILDING").
        summary (dict): hours counted and outside, and their share, of the zones
            (zone-hours) and of the building (``building_*``), tolerance, period.
    """

    def __init__(self, title, zones, monthly, summary, notes):
        self.title = title
        self.zones = zones
        self.monthly = monthly
        self.summary = summary
        self.notes = notes

    def _summary_lines(self):
        s = self.summary
        return [
            f"Building: {s['building_hours_outside']:,.0f} hours with some zone outside the "
            f"setpoints of {s['building_hours_counted']:,.0f} hours counted "
            f"({s['building_share_outside']:.1%})",
            f"Zones: {s['hours_outside']:,.0f} zone-hours outside of {s['hours_counted']:,.0f} "
            f"counted ({s['share_outside']:.1%})",
            f"Tolerance: {s['tolerance']} K; hours counted: {s['counted']}",
        ]

    def _tables(self):
        return [("Comfort by zone", self.zones),
                ("Hours outside the setpoints by month and zone [h]", self.monthly)]

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
            parts.append(df.to_html(float_format=lambda x: f"{x:,.1f}", border=0, na_rep=""))
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
                out += ["", title, df.to_string(na_rep="")]
        out += ["", *self.notes]
        return "\n".join(out)
