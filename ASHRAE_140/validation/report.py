"""Validation page (mkdocs/validation.md) and its figures from the stored results."""

import datetime as dt
import math
import textwrap
from importlib.metadata import version
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "mkdocs"
PAGE = DOCS_DIR / "validation.md"
IMG_DIR = DOCS_DIR / "img" / "validation"

# Colors: neutral range, one series hue, status "critical" for results outside the range
RANGE_COLOR = "#c3c2b7"
INSIDE_COLOR = "#2a78d6"
OUTSIDE_COLOR = "#d03b3b"
TEXT_COLOR = "#52514e"
GRID_COLOR = "#e4e3df"
ZERO_TOL = 1e-6  # absolute tolerance, so a load of 1e-12 MWh counts as the reference 0
REL_TOL = 0.001  # 0.1 % of the range bound, for the rounding of the reference spreadsheets


def compare(suite, results, reference):
    """Table of OpenSimula results against the reference programs' range, in form order."""
    rows = []
    stored = {(r.case, r.output, r.point): r for r in results.itertuples()}
    for key in suite.CELLS:
        refs = [v[key] for v in reference.values() if key in v]
        r = stored.get(key)
        if r is None or not refs:
            continue
        low, high = min(refs), max(refs)
        tol = ZERO_TOL + REL_TOL * max(abs(low), abs(high))
        rows.append(
            {"case": r.case, "output": r.output, "point": r.point, "value": r.value, "date": r.date,
             "min": low, "max": high, "programs": len(refs),
             "inside": low - tol <= r.value <= high + tol,
             "distance": max(low - r.value, r.value - high, 0)}
        )
    return pd.DataFrame(rows)


def _label(case, point):
    return f"{case} {point}" if point else case


def _deviation(row, unit):
    """Text for the Result column: inside, or how far outside the range."""
    if row.inside:
        return "✓ inside"
    bound, side = (row.max, "above max") if row.value > row.max else (row.min, "below min")
    diff = row.value - bound
    if unit == "°C" or abs(bound) < ZERO_TOL:
        return f"✗ {diff:+.2f} {unit} {side}"
    return f"✗ {100 * diff / abs(bound):+.1f} % {side}"


def _style(ax):
    ax.set_axisbelow(True)
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID_COLOR)
    ax.tick_params(colors=TEXT_COLOR, labelsize=8, length=0)


def _title(text):
    return textwrap.fill(text, 48)


def _legend(fig, height, range_patch, line=True):
    legend = [
        range_patch,
        Line2D([], [], marker="o", linestyle="-" if line else "", color=INSIDE_COLOR, label="OpenSimula, inside range"),
        Line2D([], [], marker="X", linestyle="", color=OUTSIDE_COLOR, markersize=8, label="OpenSimula, outside range"),
    ]
    fig.legend(handles=legend, loc="upper left", ncol=3, frameon=False, fontsize=8, labelcolor=TEXT_COLOR)
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.45 / height))


def _annual_figure(suite, comparison, outputs, path):
    """One panel per output: reference range as a bar, OpenSimula as a dot."""
    panels = [comparison[comparison["output"] == o] for o in outputs]
    labels = [[_label(c, p) for c, p in zip(df["case"], df["point"])] for df in panels]
    shared = all(lab == labels[0] for lab in labels)
    n_rows = max(len(lab) for lab in labels)
    height = 1.6 + 0.2 * n_rows
    fig, axes = plt.subplots(1, len(outputs), figsize=(3.6 * len(outputs), height), squeeze=False)
    for i, (ax, output, df, lab) in enumerate(zip(axes[0], outputs, panels, labels)):
        name, unit = suite.OUTPUTS[output]
        y = range(len(df))
        ax.hlines(y, df["min"], df["max"], color=RANGE_COLOR, linewidth=6, capstyle="round", zorder=1)
        ok = df["inside"].to_numpy()
        ax.scatter(df["value"][ok], [j for j in y if ok[j]], s=22, color=INSIDE_COLOR,
                   edgecolor="white", linewidth=0.8, zorder=2)
        ax.scatter(df["value"][~ok], [j for j in y if not ok[j]], s=40, marker="X", color=OUTSIDE_COLOR,
                   edgecolor="white", linewidth=0.8, zorder=3)
        ax.set_title(_title(f"{name} ({unit})"), fontsize=9, color=TEXT_COLOR, loc="left")
        ax.grid(axis="x", color=GRID_COLOR, linewidth=0.8)
        ax.set_yticks(list(y), lab if (i == 0 or not shared) else [""] * len(lab))
        ax.set_ylim(n_rows - 0.5, -0.5)  # first case on top, as in the tables
        _style(ax)
    range_patch = Line2D([], [], color=RANGE_COLOR, linewidth=6, solid_capstyle="round",
                         label="Reference programs (min–max)")
    _legend(fig, height, range_patch, line=False)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _profile_figure(suite, comparison, series, path):
    """One small panel per series: reference band (min–max) and OpenSimula line."""
    ncols = min(3, len(series))
    nrows = math.ceil(len(series) / ncols)
    height = 0.8 + 2.4 * nrows
    width = 3.8 * ncols if ncols > 1 else 7.6  # a single panel still fits the legend
    fig, axes = plt.subplots(nrows, ncols, figsize=(width, height), squeeze=False)
    for ax, (case, output) in zip(axes.flat, series):
        name, unit = suite.OUTPUTS[output]
        df = comparison[(comparison["case"] == case) & (comparison["output"] == output)]
        if output == "temperature_bins":  # only the part of the 149 bins with hours
            used = df[(df["max"] > 0) | (df["value"] > 0)].index
            df = df.loc[used.min() - 2: used.max() + 2]
        x = range(len(df))
        ax.fill_between(x, df["min"], df["max"], color=RANGE_COLOR, linewidth=0, alpha=0.8, step=None)
        ax.plot(x, df["value"], color=INSIDE_COLOR, linewidth=1.6, marker="o", markersize=2.5)
        bad = ~df["inside"].to_numpy()
        ax.scatter([j for j in x if bad[j]], df["value"][bad], s=30, marker="X", color=OUTSIDE_COLOR,
                   edgecolor="white", linewidth=0.6, zorder=3)
        ax.set_title(_title(f"Case {case}: {name} ({unit})"), fontsize=8, color=TEXT_COLOR, loc="left")
        points = list(df["point"])
        step = 1 if len(points) <= 12 else (6 if len(points) <= 24 else 5)
        ticks = [j for j in x if (j + 1) % step == 0 or j == 0] if len(points) <= 24 else \
            [j for j in x if int(points[j]) % step == 0]
        ax.set_xticks(ticks, [points[j] for j in ticks])
        ax.grid(axis="y", color=GRID_COLOR, linewidth=0.8)
        _style(ax)
    for ax in list(axes.flat)[len(series):]:
        ax.set_visible(False)
    _legend(fig, height, Patch(color=RANGE_COLOR, label="Reference programs (min–max)"))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _summary_table(suite, comparison, outputs):
    lines = ["| Output | Values | Inside range | Outside range |", "|---|--:|--:|--:|"]
    for output in outputs:
        name, unit = suite.OUTPUTS[output]
        df = comparison[comparison["output"] == output]
        lines.append(f"| {name} ({unit}) | {len(df)} | {df['inside'].sum()} | {(~df['inside']).sum()} |")
    return lines + [""]


def _annual_section(suite, comparison, group, img):
    outputs = group["outputs"]
    _annual_figure(suite, comparison, outputs, IMG_DIR / img)
    lines = [f"### {group['title']}", ""] + _summary_table(suite, comparison, outputs)
    lines += [f"![{group['title']}](img/validation/{img})", ""]
    for output in outputs:
        name, unit = suite.OUTPUTS[output]
        df = comparison[comparison["output"] == output]
        has_date = (df["date"] != "").any()
        lines += [f"#### {name} ({unit})", ""]
        header = "| Case | OpenSimula |" + (" Date |" if has_date else "") + " Min | Max | Programs | Result |"
        lines += [header, "|---|--:|" + ("---|" if has_date else "") + "--:|--:|--:|---|"]
        for r in df.itertuples():
            date = f" {r.date} |" if has_date else ""
            lines.append(
                f"| {_label(r.case, r.point)} | {r.value:.3f} |{date} {r.min:.3f} | {r.max:.3f} "
                f"| {r.programs} | {_deviation(r, unit)} |"
            )
        lines.append("")
    return lines


def _profile_section(suite, comparison, group, img):
    df = comparison[comparison["output"].isin(group["outputs"])]
    series = list(dict.fromkeys(zip(df["case"], df["output"])))
    _profile_figure(suite, comparison, series, IMG_DIR / img)
    lines = [f"### {group['title']}", "", f"![{group['title']}](img/validation/{img})", ""]
    lines += ["| Case | Output | Values | Inside range | Largest distance outside range |", "|---|---|--:|--:|--:|"]
    for case, output in series:
        name, unit = suite.OUTPUTS[output]
        s = df[(df["case"] == case) & (df["output"] == output)]
        worst = s["distance"].max()
        worst = f"{worst:.3g} {unit}" if worst > ZERO_TOL else "–"
        lines.append(f"| {case} | {name} ({unit}) | {len(s)} | {s['inside'].sum()} | {worst} |")
    return lines + [""]


def _suite_section(suite, results):
    comparison = compare(suite, results, suite.read_reference())
    lines = [f"## {suite.TITLE}", ""]
    lines += [
        f"Reference programs: {', '.join(suite.REFERENCE_PROGRAMS)} "
        f"(example results from `{suite.RESULTS_FILE.name}`). "
        f"**{comparison['inside'].sum()} of {len(comparison)} values inside the reference range.**",
        "",
    ]
    for i, group in enumerate(suite.GROUPS, 1):
        img = f"{suite.NAME.lower()}_{i}.png"
        section = _annual_section if group["kind"] == "annual" else _profile_section
        lines += section(suite, comparison, group, img)
    return lines


def write_page(suites, results):
    """Write mkdocs/validation.md (and its figures) for the suites with stored results."""
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Validation: ASHRAE Standard 140",
        "",
        "OpenSimula is tested with the method of test of ANSI/ASHRAE Standard 140-2023, "
        "*Standard Method of Test for the Evaluation of Building Energy Analysis Computer Programs*. "
        "For each output the Standard asks for, the OpenSimula result is compared with the range "
        "(minimum and maximum) of the example results of the reference programs published with the Standard.",
        "",
        "The range shows how much well-established programs differ from each other; it is not the "
        "Standard's formal acceptance criteria. A result outside the range is a prompt to look into "
        "that case, not necessarily an error. A value counts as inside when it is within the range "
        "widened by 0.1 % of its bound, to allow for the rounding of the reference spreadsheets.",
        "",
        f"*Generated by `ASHRAE_140/validation/validate.py` with OpenSimula {version('opensimula')} "
        f"on {dt.date.today():%Y-%m-%d}. The test case definitions are in the `ASHRAE_140` folder "
        "of the repository.*",
        "",
    ]
    for suite in suites:
        lines += _suite_section(suite, results[suite.NAME])
    PAGE.write_text("\n".join(lines), encoding="utf-8")
    return PAGE
