"""Interactive viewer of the simulation results.

Built on anywidget, like the project editor, so it works in Jupyter (Lab,
Notebook 7, VS Code, Colab) and, wrapped in mo.ui.anywidget(), in Marimo::

    viewer = project.results()

The components and their variables are listed on the left; the selected
variables are plotted on the right, one chart per unit, after resampling them
to the chosen frequency. The data is prepared here in Python and only the
points to draw are sent to the browser.

The "3D" button shows the geometry of the project above the charts: clicking a
surface opens it, and its spaces, in the list of variables, and the surfaces
and spaces whose variables are plotted are drawn in the colour of their series.
"""

import math
import pathlib

import anywidget
import pandas as pd
import traitlets

_STATIC = pathlib.Path(__file__).parent / "static"

# Periods labelled by their start, so a month is drawn on its first day
FREQUENCIES = {"none": None, "hourly": "h", "daily": "D", "monthly": "MS", "yearly": "YS"}
AGGREGATIONS = ["mean", "sum", "max", "min"]
STATISTICS = ["mean", "max", "min"]  # of the colour variable of the 3D view
MAX_SERIES = 8  # one per hue of the categorical palette


class ResultsViewer(anywidget.AnyWidget):
    """Viewer of the variables of a simulated project.

    Args:
        project (Project): simulated project whose variables are shown.

    Attributes:
        selection (list): selected variables, each a dict with "component",
            "variable" and "slot" (its colour, kept while it stays selected).
        frequency (str): "none", "hourly", "daily", "monthly" or "yearly".
        aggregation (str): "mean", "sum", "max" or "min", used when resampling.
        interval (list): [start, end] as ISO dates ("2001-06-01"), or empty for
            the whole simulation.
        height (int): height of the whole widget, in pixels.
        chart_height (int): height of each chart, in pixels.
        show_3d (bool): whether the 3D view of the project is shown.
        color_variable (str): variable of the surfaces that colours the 3D
            view ("T_s0", "q_sol1"...), or "" for the colours of the series.
        color_statistic (str): "mean", "max" or "min" of that variable over
            the interval shown.
    """

    _esm = _STATIC / "results.js"
    _css = _STATIC / "results.css"

    catalog = traitlets.List([]).tag(sync=True)
    selection = traitlets.List([]).tag(sync=True)
    frequency = traitlets.Unicode("none").tag(sync=True)
    aggregation = traitlets.Unicode("mean").tag(sync=True)
    interval = traitlets.List([]).tag(sync=True)
    period = traitlets.List([]).tag(sync=True)
    series = traitlets.List([]).tag(sync=True)
    message = traitlets.Unicode("").tag(sync=True)
    height = traitlets.Int(600).tag(sync=True)
    chart_height = traitlets.Int(300).tag(sync=True)
    show_3d = traitlets.Bool(False).tag(sync=True)
    # filled the first time the 3D view is opened, not before
    geometry = traitlets.Dict({}).tag(sync=True)
    color_variable = traitlets.Unicode("").tag(sync=True)
    color_statistic = traitlets.Unicode("mean").tag(sync=True)
    # {"variable", "statistic", "unit", "values": {component: value}}
    surface_values = traitlets.Dict({}).tag(sync=True)

    def __init__(self, project, **kwargs):
        super().__init__(**kwargs)
        self._project_ = project
        self.refresh()
        self.observe(self._update_series_, names=["selection", "frequency", "aggregation", "interval"])
        self.on_msg(self._on_message_)
        self.observe(self._update_surface_values_, names=["color_variable", "color_statistic", "interval", "geometry"])

    @property
    def project(self):
        """The project whose results are shown."""
        return self._project_

    def refresh(self):
        """Reload the list of variables from the project, after simulating it again."""
        n = self._project_.parameter("n_time_steps").value
        catalog = []
        for component in self._project_.component_list():
            variables = [
                {"name": key, "unit": var.unit}
                for key, var in component.variable_dict().items()
                if var.values is not None and len(var.values) == n
            ]
            if variables:
                catalog.append({
                    "name": component.parameter("name").value,
                    "type": component.parameter("type").value,
                    "variables": variables,
                })
        self.catalog = catalog
        dates = self._dates_()
        self.period = [dates.iloc[0].isoformat(), dates.iloc[-1].isoformat()] if len(dates) else []
        if not catalog:
            self.message = "No results: simulate the project first."
        if self.geometry:
            self.geometry = self._project_.geometry_dict()
            self._update_surface_values_()
        names = {(c["name"], v["name"]) for c in catalog for v in c["variables"]}
        kept = [s for s in self.selection if (s["component"], s["variable"]) in names]
        if kept != self.selection:
            self.selection = kept
        else:
            self._update_series_()

    def select(self, *variables):
        """Select variables from Python, each as "component.variable".

        Example:
            viewer.select("spaces_1.temperature", "system.Q_sensible")
        """
        selection = list(self.selection)
        used = {s["slot"] for s in selection}
        available = {(c["name"], v["name"]) for c in self.catalog for v in c["variables"]}
        for text in variables:
            component, _, variable = text.partition(".")
            if (component, variable) not in available:
                raise ValueError(f"{text}: no such variable with results in the project")
            if any(s["component"] == component and s["variable"] == variable for s in selection):
                continue
            free = [i for i in range(MAX_SERIES) if i not in used]
            if not free:
                raise ValueError(f"At most {MAX_SERIES} variables can be shown at the same time")
            selection.append({"component": component, "variable": variable, "slot": free[0]})
            used.add(free[0])
        self.selection = selection

    def dataframe(self):
        """The selected variables as shown: resampled and cut to the interval.

        Returns:
            pandas.DataFrame: one column per variable, "component.variable [unit]",
                indexed by date.
        """
        columns = {}
        for item in self.selection:
            data = self._data_(item["component"], item["variable"])
            if data is not None:
                values, unit = data
                label = f"{item['component']}.{item['variable']}"
                columns[f"{label} [{unit}]" if unit else label] = values
        return pd.DataFrame(columns)

    # ____________________ 3D view ____________________

    def _on_message_(self, widget, content, buffers):
        """The front end asks for the 3D view when it is first opened: the
        geometry, and the plotly bundle if the page does not have it yet."""
        if not isinstance(content, dict) or content.get("type") != "load-3d":
            return
        if not self.geometry:
            self.geometry = self._project_.geometry_dict()
        if not content.get("has_plotly"):
            self.send({"type": "plotly"}, [(_STATIC / "plotly3d.js").read_bytes()])

    def _update_surface_values_(self, change=None):
        """One value per surface of the 3D view: the statistic of the colour
        variable over the interval shown."""
        if self.color_statistic not in STATISTICS:
            self.color_statistic = "mean"
            return
        variable = self.color_variable
        if not variable or not self.geometry:
            if self.surface_values:
                self.surface_values = {}
            return
        values, unit = {}, ""
        for name in sorted({mesh["component"] for mesh in self.geometry.get("meshes", [])}):
            data = self._raw_(name, variable)
            if data is None:
                continue
            series, unit = data
            series = series[pd.notna(series)]
            if len(series):
                values[name] = float(getattr(series, self.color_statistic)())
        self.surface_values = {
            "variable": variable,
            "statistic": self.color_statistic,
            "unit": unit,
            "values": values,
        }

    # ____________________ data ____________________

    def _dates_(self):
        return pd.Series(pd.to_datetime(self._project_.dates()))

    def _raw_(self, component_name, variable_name):
        """Values of one variable in the interval, not resampled, and its unit,
        or None if missing."""
        component = self._project_.component(component_name)
        if component is None or variable_name not in component.variable_dict():
            return None
        variable = component.variable(variable_name)
        n = self._project_.parameter("n_time_steps").value
        if variable.values is None or len(variable.values) != n:
            return None
        values = pd.Series(variable.values, index=pd.DatetimeIndex(self._dates_()), dtype=float)
        if len(self.interval) == 2:
            start, end = pd.Timestamp(self.interval[0]), pd.Timestamp(self.interval[1])
            values = values[(values.index >= start) & (values.index < end + pd.Timedelta(days=1))]
        return values, variable.unit

    def _data_(self, component_name, variable_name):
        """Resampled values of one variable and its unit, or None if missing."""
        data = self._raw_(component_name, variable_name)
        if data is None:
            return None
        values, unit = data
        rule = FREQUENCIES.get(self.frequency)
        if rule is not None and len(values):
            values = getattr(values.resample(rule), self.aggregation)()
        return values, unit

    def _update_series_(self, change=None):
        if self.frequency not in FREQUENCIES:
            self.frequency = "none"
            return
        if self.aggregation not in AGGREGATIONS:
            self.aggregation = "mean"
            return
        series = []
        for item in self.selection:
            data = self._data_(item["component"], item["variable"])
            if data is None:
                continue
            values, unit = data
            series.append({
                "component": item["component"],
                "variable": item["variable"],
                "slot": item["slot"],
                "unit": unit,
                # seconds since the epoch, the time axis of the chart
                "x": [t.timestamp() for t in values.index.tz_localize("UTC")],
                "y": [None if not math.isfinite(v) else float(v) for v in values.to_numpy()],
            })
        self.series = series
        if self.catalog:
            self.message = ""
