"""ASHRAE 140-2023 Section 7 (building thermal envelope and fabric load tests, LOAD_TEST folder).

Defines the cases to simulate, how the Standard's outputs are extracted from an OpenSimula
project and where each output is in the Standard's output form (sheet YourData of
Std140_TF_Results.xlsx). Every reference program has a sheet with the same layout, so the
same cells give the reference results.

Each result is identified by (case, output, point): point is "" for a single value, or the
surface, month, hour or temperature bin of a profile.
"""

from pathlib import Path

import numpy as np
import openpyxl

NAME = "LOAD_TEST"
TITLE = "Building thermal envelope and fabric load tests (Section 7)"
FOLDER = Path(__file__).resolve().parent.parent / "LOAD_TEST"
RESULTS_FILE = FOLDER / "Std140_TF_Results.xlsx"
REFERENCE_PROGRAMS = ["BSIMAC", "CSE", "DeST", "EnergyPlus", "ESP-r", "TRNSYS"]

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
HOURS = [str(h) for h in range(1, 25)]
BINS = [str(t) for t in range(-50, 99)]  # 1 °C bins [t, t+1) of the 900FF zone temperature
DAYS = {"feb01": (2, 1, "Feb 1"), "may04": (5, 4, "May 4"), "jul14": (7, 14, "Jul 14")}
SURFACES = {"horizontal": "roof_wall", "north": "north_wall", "east": "east_wall",
            "south": "south_wall", "west": "west_wall"}
WINDOWS = {"south": "south_window_1", "west": "west_window"}

# Same order as the Standard's output form
LOAD_CASES = [
    "600", "610", "620", "630", "640", "650", "660", "670", "680", "685", "695",
    "900", "910", "920", "930", "940", "950", "960", "980", "985", "995",
    "195", "200", "210", "215", "220", "230", "240", "250", "270", "280", "290",
    "300", "310", "320", "395", "400", "410", "420", "430", "440", "450", "460",
    "470", "800", "810",
]
FREE_FLOAT_CASES = ["600FF", "900FF", "650FF", "950FF", "680FF", "980FF", "960"]

# Case 960 is the two-zone sunspace case: loads are reported for the conditioned back zone
# and free-float temperatures for the unconditioned sun zone.
LOAD_SPACE = {"960": "back_zone"}
FREE_FLOAT_SPACE = {"960": "sun_zone"}
DEFAULT_SPACE = "spaces_1"


def _hourly_outputs():
    """Specific-day hourly outputs: {output: (title, unit)}."""
    out = {}
    for day, (_, _, label) in DAYS.items():
        for surface in ["horizontal", "south", "west"]:
            out[f"incident_{day}_{surface}"] = (f"Incident solar, {surface}, {label}", "Wh/m²")
        out[f"sky_{day}"] = (f"Sky temperature, {label}", "°C")
        out[f"transmitted_{day}"] = (f"Transmitted solar, south window, {label}", "Wh/m²")
        out[f"load_{day}"] = (f"Zone load (+ heating, − cooling), {label}", "kWh")
        out[f"temperature_{day}"] = (f"Zone temperature, {label}", "°C")
    return out


# Output name -> (title, unit)
OUTPUTS = {
    "annual_heating": ("Annual heating load", "MWh"),
    "annual_cooling": ("Annual cooling load", "MWh"),
    "peak_heating": ("Annual hourly integrated peak heating load", "kW"),
    "peak_cooling": ("Annual hourly integrated peak sensible cooling load", "kW"),
    "average_temperature": ("Annual hourly average zone temperature", "°C"),
    "minimum_temperature": ("Annual hourly minimum zone temperature", "°C"),
    "maximum_temperature": ("Annual hourly maximum zone temperature", "°C"),
    "annual_incident": ("Annual incident solar radiation", "kWh/m²"),
    "annual_transmitted": ("Annual transmitted solar radiation, unshaded", "kWh/m²"),
    "annual_transmitted_shaded": ("Annual transmitted solar radiation, shaded", "kWh/m²"),
    "sky_average": ("Annual hourly average sky temperature", "°C"),
    "sky_minimum": ("Annual hourly minimum sky temperature", "°C"),
    "sky_maximum": ("Annual hourly maximum sky temperature", "°C"),
    "monthly_heating": ("Monthly heating load", "kWh"),
    "monthly_cooling": ("Monthly cooling load", "kWh"),
    "monthly_peak_heating": ("Monthly peak heating load", "kW"),
    "monthly_peak_cooling": ("Monthly peak cooling load", "kW"),
    **_hourly_outputs(),
    "temperature_bins": ("Annual hours per 1 °C zone temperature bin", "h"),
}


def _cells():
    """Position (row, column) of every output in the Standard's output form."""
    cells = {}
    # Conditioned zone loads (rows 70-115) and free-float temperatures (rows 130-136)
    for i, case in enumerate(LOAD_CASES):
        for output, col in [("annual_heating", 3), ("annual_cooling", 4), ("peak_heating", 5), ("peak_cooling", 9)]:
            cells[(case, output, "")] = (70 + i, col)
    for i, case in enumerate(FREE_FLOAT_CASES):
        for output, col in [("average_temperature", 3), ("minimum_temperature", 4), ("maximum_temperature", 8)]:
            cells[(case, output, "")] = (130 + i, col)
    # Annual solar radiation and sky temperature
    for i, surface in enumerate(["horizontal", "north", "east", "south", "west"]):
        cells[("600", "annual_incident", surface)] = (155 + i, 3)
    for i, (case, window) in enumerate([("600", "south"), ("660", "south"), ("670", "south"), ("620", "west")]):
        cells[(case, "annual_transmitted", window)] = (163 + i, 3)
    for i, (case, window) in enumerate([("610", "south"), ("630", "west")]):
        cells[(case, "annual_transmitted_shaded", window)] = (170 + i, 3)
    for output, col in [("sky_average", 3), ("sky_minimum", 4), ("sky_maximum", 8)]:
        cells[("600", output, "")] = (178, col)
    # Monthly loads of cases 600 (columns C-J) and 900 (columns K-R), rows 190-201
    for case, first in [("600", 3), ("900", 11)]:
        for output, col in [("monthly_heating", 0), ("monthly_cooling", 1),
                            ("monthly_peak_heating", 2), ("monthly_peak_cooling", 5)]:
            for m, month in enumerate(MONTHS):
                cells[(case, output, month)] = (190 + m, first + col)
    # Specific-day hourly outputs: three tables of 24 rows, one series per column
    columns = {
        230: [("600", "incident_may04_horizontal"), ("600", "incident_may04_south"), ("600", "incident_may04_west"),
              ("600", "incident_jul14_horizontal"), ("600", "incident_jul14_south"), ("600", "incident_jul14_west"),
              ("600", "sky_feb01"), ("600", "sky_may04"), ("600", "sky_jul14")]
             + [(case, f"transmitted_{day}") for day in DAYS for case in ["600", "660", "670"]],
        262: [(case, "load_feb01") for case in
              ["600", "640", "660", "670", "680", "685", "695", "900", "940", "980", "985", "995"]]
             + [(case, "load_jul14") for case in
                ["600", "660", "670", "680", "685", "695", "900", "980", "985", "995"]]
             + [("640", "temperature_feb01"), ("940", "temperature_feb01")],
        294: [("600FF", "temperature_feb01"), ("900FF", "temperature_feb01"), ("650FF", "temperature_jul14"),
              ("950FF", "temperature_jul14"), ("680FF", "temperature_feb01"), ("980FF", "temperature_feb01")],
    }
    for first_row, series in columns.items():
        for col, (case, output) in enumerate(series, 3):
            for h, hour in enumerate(HOURS):
                cells[(case, output, hour)] = (first_row + h, col)
    # 900FF zone temperature bins, rows 330-478
    for i, t in enumerate(BINS):
        cells[("900FF", "temperature_bins", t)] = (330 + i, 3)
    return cells


CELLS = _cells()
OUTPUTS = {o: v for o, v in OUTPUTS.items() if any(o == output for _, output, _ in CELLS)}

# Validation page layout. "annual" groups get a range chart and a table per output;
# "profile" groups get one small chart per series (case, output) and a summary table.
GROUPS = [
    {"title": "Annual loads", "kind": "annual", "outputs": ["annual_heating", "annual_cooling"]},
    {"title": "Peak loads", "kind": "annual", "outputs": ["peak_heating", "peak_cooling"]},
    {"title": "Free-float zone temperatures", "kind": "annual",
     "outputs": ["minimum_temperature", "average_temperature", "maximum_temperature"]},
    {"title": "Solar radiation", "kind": "annual",
     "outputs": ["annual_incident", "annual_transmitted", "annual_transmitted_shaded"]},
    {"title": "Sky temperature", "kind": "annual", "outputs": ["sky_minimum", "sky_average", "sky_maximum"]},
    {"title": "Monthly loads, cases 600 and 900", "kind": "profile",
     "outputs": ["monthly_heating", "monthly_cooling", "monthly_peak_heating", "monthly_peak_cooling"]},
    {"title": "Hourly incident solar radiation and sky temperature, case 600", "kind": "profile",
     "outputs": [o for o in OUTPUTS if o.startswith("incident_")] + [f"sky_{day}" for day in DAYS]},
    {"title": "Hourly transmitted solar radiation", "kind": "profile",
     "outputs": [o for o in OUTPUTS if o.startswith("transmitted_")]},
    {"title": "Hourly zone loads", "kind": "profile", "outputs": ["load_feb01", "load_jul14"]},
    {"title": "Hourly zone temperatures", "kind": "profile", "outputs": ["temperature_feb01", "temperature_jul14"]},
    {"title": "Zone temperature bins, case 900FF", "kind": "profile", "outputs": ["temperature_bins"]},
]


def cases():
    """Cases to simulate, each one once even if it reports several outputs."""
    return list(dict.fromkeys(LOAD_CASES + FREE_FLOAT_CASES))


def case_file(case):
    return FOLDER / "cases" / f"case_{case}.json"


def _date(d, with_month=True):
    """Month, day and hour (1-24, hour ending) of a time step, as the Standard asks for."""
    return f"{d:%b} {d.day} {d.hour + 1}" if with_month else f"{d.day} {d.hour + 1}"


def extract(case, project):
    """Standard's outputs of a simulated case: list of (output, point, value, date) tuples.

    The Standard asks for hourly integrated values, so with sub-hourly time steps every
    variable is averaged over each hour first (the time step must divide the hour).
    """
    steps = round(3600 / project.parameter("time_step").value)  # time steps per hour
    dates = project.dates()[::steps]  # a date within each hour: gives its month, day and hour
    hours = 1  # hourly values: W x 1 h = Wh
    months = np.array([d.month for d in dates])
    days = {day: np.array([d.month == m and d.day == dd for d in dates]) for day, (m, dd, _) in DAYS.items()}
    wanted = {(o, p) for c, o, p in CELLS if c == case}
    rows = []

    def var(component, variable):
        values = project.component(component).variable(variable).values
        return values.reshape(-1, steps).mean(axis=1)

    def add_hourly(output, values):
        """values: function returning the annual hourly values, called only if the series is wanted."""
        if (output, "1") in wanted:
            day = output.split("_")[1]
            rows.extend((output, h, v, "") for h, v in zip(HOURS, values()[days[day]]))

    if case in LOAD_CASES:
        load = var(LOAD_SPACE.get(case, DEFAULT_SPACE), "system_sensible_heat")
        # Round-off loads (~1e-12 W) are zero, so a case with no heating reports its peak on Jan 1 1
        load = np.where(np.abs(load) < 1e-6, 0, load)
        heating = np.where(load > 0, load, 0)
        cooling = np.where(load < 0, -load, 0)
        rows.append(("annual_heating", "", heating.sum() * hours / 1e6, ""))
        rows.append(("annual_cooling", "", cooling.sum() * hours / 1e6, ""))
        i_heat, i_cool = np.argmax(heating), np.argmax(cooling)
        rows.append(("peak_heating", "", heating[i_heat] / 1000, _date(dates[i_heat])))
        rows.append(("peak_cooling", "", cooling[i_cool] / 1000, _date(dates[i_cool])))
        if ("monthly_heating", "Jan") in wanted:
            for m, month in enumerate(MONTHS, 1):
                idx = np.flatnonzero(months == m)
                i_h, i_c = idx[np.argmax(heating[idx])], idx[np.argmax(cooling[idx])]
                rows.append(("monthly_heating", month, heating[idx].sum() * hours / 1000, ""))
                rows.append(("monthly_cooling", month, cooling[idx].sum() * hours / 1000, ""))
                rows.append(("monthly_peak_heating", month, heating[i_h] / 1000, _date(dates[i_h], False)))
                rows.append(("monthly_peak_cooling", month, cooling[i_c] / 1000, _date(dates[i_c], False)))
        for day in DAYS:
            add_hourly(f"load_{day}", lambda: load * hours / 1000)
            add_hourly(f"temperature_{day}", lambda: var(DEFAULT_SPACE, "temperature"))
    if case in FREE_FLOAT_CASES:
        temp = var(FREE_FLOAT_SPACE.get(case, DEFAULT_SPACE), "temperature")
        i_min, i_max = np.argmin(temp), np.argmax(temp)
        rows.append(("average_temperature", "", temp.mean(), ""))
        rows.append(("minimum_temperature", "", temp[i_min], _date(dates[i_min])))
        rows.append(("maximum_temperature", "", temp[i_max], _date(dates[i_max])))
        for day in DAYS:
            add_hourly(f"temperature_{day}", lambda: temp)
        if ("temperature_bins", "0") in wanted:
            counts = np.bincount(np.clip(np.floor(temp).astype(int), -50, 98) + 50, minlength=len(BINS))
            rows.extend(("temperature_bins", t, float(n), "") for t, n in zip(BINS, counts))
    # Solar radiation on the exterior surfaces and windows (hourly integrated: W/m² x h)
    for surface, component in SURFACES.items():
        if ("annual_incident", surface) in wanted or (f"incident_may04_{surface}", "1") in wanted:
            incident = (var(component, "E_dir") + var(component, "E_dif")) * hours
            if ("annual_incident", surface) in wanted:
                rows.append(("annual_incident", surface, incident.sum() / 1000, ""))
            for day in DAYS:
                add_hourly(f"incident_{day}_{surface}", lambda: incident)
    for window, component in WINDOWS.items():
        for output in ["annual_transmitted", "annual_transmitted_shaded"]:
            if (output, window) in wanted:
                transmitted = (var(component, "E_dir_tra") + var(component, "E_dif_tra")) * hours
                rows.append((output, window, transmitted.sum() / 1000, ""))
    if any(o.startswith("transmitted_") for o, _ in wanted):
        transmitted = (var(WINDOWS["south"], "E_dir_tra") + var(WINDOWS["south"], "E_dif_tra")) * hours
        for day in DAYS:
            add_hourly(f"transmitted_{day}", lambda: transmitted)
    # Sky temperature
    if ("sky_average", "") in wanted:
        sky = var(project.parameter("simulation_file_met").value, "sky_temperature")
        i_min, i_max = np.argmin(sky), np.argmax(sky)
        rows.append(("sky_average", "", sky.mean(), ""))
        rows.append(("sky_minimum", "", sky[i_min], _date(dates[i_min])))
        rows.append(("sky_maximum", "", sky[i_max], _date(dates[i_max])))
        for day in DAYS:
            add_hourly(f"sky_{day}", lambda: sky)
    return rows


def read_reference():
    """Example results of the reference programs: {program: {(case, output, point): value}}."""
    wb = openpyxl.load_workbook(RESULTS_FILE, data_only=True)
    reference = {}
    for program in REFERENCE_PROGRAMS:
        ws = wb[program]
        # The loads and free-float tables are labelled by case: check the layout is the expected one
        for (case, output, _), (row, _) in CELLS.items():
            if output in ("annual_heating", "average_temperature"):
                label = str(ws.cell(row, 2).value).strip()
                if label != case:
                    raise ValueError(f"{RESULTS_FILE.name}[{program}] row {row}: case {label}, expected {case}")
        reference[program] = {
            key: float(value)
            for key, (row, col) in CELLS.items()
            if isinstance(value := ws.cell(row, col).value, (int, float))
        }
    return reference
