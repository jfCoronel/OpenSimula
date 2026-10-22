"""Validation page (mkdocs/validation.md) and its figures from the stored results."""

import datetime as dt
from importlib.metadata import version
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

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


def compare(suite, results, reference):
    """Table of OpenSimula results against the reference programs' range, in form order."""
    rows = []
    stored = {(r.case, r.output): r for r in results.itertuples()}
    for output in suite.OUTPUTS:
        cases = suite.LOAD_CASES if output in suite.LOAD_OUTPUTS else suite.FREE_FLOAT_CASES
        for case in cases:
            refs = [v[(case, output)] for v in reference.values() if (case, output) in v]
            r = stored.get((case, output))
            if r is None or not refs:
                continue
            low, high = min(refs), max(refs)
            inside = low - ZERO_TOL <= r.value <= high + ZERO_TOL
            rows.append(
                {"case": case, "output": output, "value": r.value, "date": r.date,
                 "min": low, "max": high, "programs": len(refs), "inside": inside}
            )
    return pd.DataFrame(rows)


def _deviation(row, unit):
    """Text for the Result column: inside, or how far outside the range."""
    if row.inside:
        return "✓ inside"
    bound, side = (row.max, "above max") if row.value > row.max else (row.min, "below min")
    diff = row.value - bound
    if unit == "°C" or abs(bound) < ZERO_TOL:
        return f"✗ {diff:+.2f} {unit} {side}"
    return f"✗ {100 * diff / abs(bound):+.1f} % {side}"


def _figure(suite, comparison, title, outputs, path):
    """One panel per output: reference range as a bar, OpenSimula as a dot."""
    cases = list(dict.fromkeys(comparison[comparison["output"].isin(outputs)]["case"]))
    height = 1.2 + 0.2 * len(cases)
    fig, axes = plt.subplots(1, len(outputs), figsize=(3.6 * len(outputs), height), sharey=True, squeeze=False)
    y = {c: i for i, c in enumerate(cases)}
    for ax, output in zip(axes[0], outputs):
        name, unit, _ = suite.OUTPUTS[output]
        df = comparison[comparison["output"] == output]
        yy = df["case"].map(y)
        ax.hlines(yy, df["min"], df["max"], color=RANGE_COLOR, linewidth=6, capstyle="round", zorder=1)
        ok, bad = df[df["inside"]], df[~df["inside"]]
        ax.scatter(ok["value"], ok["case"].map(y), s=22, color=INSIDE_COLOR, edgecolor="white", linewidth=0.8, zorder=2)
        ax.scatter(bad["value"], bad["case"].map(y), s=40, marker="X", color=OUTSIDE_COLOR, edgecolor="white", linewidth=0.8, zorder=3)
        ax.set_title(f"{name} ({unit})", fontsize=9, color=TEXT_COLOR, loc="left", wrap=True)
        ax.grid(axis="x", color=GRID_COLOR, linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ["top", "right", "left"]:
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(GRID_COLOR)
        ax.tick_params(colors=TEXT_COLOR, labelsize=8, length=0)
    axes[0][0].set_yticks(range(len(cases)), cases)
    axes[0][0].set_ylim(len(cases) - 0.5, -0.5)  # first case on top, as in the tables
    legend = [
        Line2D([], [], color=RANGE_COLOR, linewidth=6, solid_capstyle="round", label="Reference programs (min–max)"),
        Line2D([], [], marker="o", linestyle="", color=INSIDE_COLOR, label="OpenSimula, inside range"),
        Line2D([], [], marker="X", linestyle="", color=OUTSIDE_COLOR, markersize=8, label="OpenSimula, outside range"),
    ]
    fig.legend(handles=legend, loc="upper left", ncol=3, frameon=False, fontsize=8, labelcolor=TEXT_COLOR)
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.45 / height))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _suite_section(suite, results):
    reference = suite.read_reference()
    comparison = compare(suite, results, reference)
    slug = suite.NAME.lower()
    lines = [f"## {suite.TITLE}", ""]
    lines += [
        f"Reference programs: {', '.join(suite.REFERENCE_PROGRAMS)} "
        f"(example results from `{suite.RESULTS_FILE.name}`).",
        "",
        "| Output | Cases | Inside range | Outside range |",
        "|---|--:|--:|--:|",
    ]
    for output, (name, unit, _) in suite.OUTPUTS.items():
        df = comparison[comparison["output"] == output]
        lines.append(f"| {name} ({unit}) | {len(df)} | {df['inside'].sum()} | {(~df['inside']).sum()} |")
    total = comparison["inside"]
    lines.append(f"| **Total** | **{len(total)}** | **{total.sum()}** | **{(~total).sum()}** |")
    lines.append("")

    for i, (title, outputs) in enumerate(suite.FIGURES, 1):
        img = f"{slug}_{i}.png"
        _figure(suite, comparison, title, outputs, IMG_DIR / img)
        lines += [f"### {title}", "", f"![{title}](img/validation/{img})", ""]

    lines += ["### Detailed results", ""]
    for output, (name, unit, _) in suite.OUTPUTS.items():
        df = comparison[comparison["output"] == output]
        has_date = (df["date"] != "").any()
        lines += [f"#### {name} ({unit})", ""]
        header = "| Case | OpenSimula |" + (" Date |" if has_date else "") + " Min | Max | Programs | Result |"
        lines += [header, "|---|--:|" + ("---|" if has_date else "") + "--:|--:|--:|---|"]
        for r in df.itertuples():
            date = f" {r.date} |" if has_date else ""
            lines.append(
                f"| {r.case} | {r.value:.3f} |{date} {r.min:.3f} | {r.max:.3f} | {r.programs} | {_deviation(r, unit)} |"
            )
        lines.append("")
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
        "that case, not necessarily an error.",
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
