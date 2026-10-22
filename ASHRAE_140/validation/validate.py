"""Automated ASHRAE Standard 140 validation of OpenSimula.

Simulates the test cases, stores the Standard's outputs in results/<SUITE>.csv and generates
the "Validation" page of the documentation (mkdocs/validation.md) comparing them with the
range of the reference programs' example results.

Usage (from the repository root):
    uv run python ASHRAE_140/validation/validate.py                  # simulate all, write page
    uv run python ASHRAE_140/validation/validate.py --cases 600 900  # re-simulate some cases
    uv run python ASHRAE_140/validation/validate.py --report-only    # page from stored CSV
    uv run python ASHRAE_140/validation/validate.py --check --quick  # CI: compare with stored CSV

--check simulates and compares the results with the stored CSV files instead of writing them;
it fails if any value changed beyond CHECK_RTOL/CHECK_ATOL. After an intended change, run the
script without --check and commit the updated CSV files and page.
"""

import os

os.environ.setdefault("TQDM_DISABLE", "1")  # no progress bars from the parallel simulations

import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

import airside_test
import cooling_a_test
import cooling_b_test
import ground_test
import heating_test
import load_test
import report
import weather_test

SUITES = {suite.NAME: suite for suite in [load_test, heating_test, cooling_a_test, cooling_b_test, ground_test, airside_test, weather_test]}
RESULTS_DIR = Path(__file__).resolve().parent / "results"
# Representative cases of every suite for a quick check (CI on every pull request)
QUICK_CASES = {
    "LOAD_TEST": ["600", "900", "600FF", "640", "960"],
    "HEATING_TEST": ["HE100", "HE210"],
    "COOLING_TEST_A": ["CE100", "CE150"],
    "COOLING_TEST_B": ["CE300", "CE500"],
    "GROUND_TEST": ["GC30b", "GC40b"],
    "AIR_SIDE_HVAC_TEST": ["AE101", "AE204", "AE303", "AE403"],
    "WEATHER_TEST": ["WD100"],
}
# Allowed difference with the stored results: relative, plus an absolute floor for values
# near zero (the CSV files keep 6 decimals)
CHECK_RTOL = 1e-3
CHECK_ATOL = 1e-4


def simulate_case(suite_name, case):
    """Simulate one case and return its outputs as a list of row dicts (runs in a worker)."""
    import opensimula as osm

    suite = SUITES[suite_name]
    os.chdir(suite.FOLDER)  # weather file paths in the case files are relative to it
    sim = osm.Simulation()
    sim.console_print = False
    pro = sim.new_project("pro")
    pro.read_json(str(suite.case_file(case)))
    pro.simulate()
    errors = [m.text for m in sim.message_list() if m.level == "ERROR"]
    if errors:
        raise RuntimeError("\n".join(errors))
    return [
        {"case": case, "output": output, "point": point, "value": value, "date": date}
        for output, point, value, date in suite.extract(case, pro)
    ]


def read_results(csv):
    return pd.read_csv(csv, dtype={"case": str, "point": str}, keep_default_na=False, float_precision="round_trip")


def run_suite(suite, cases, jobs):
    """Simulate the cases in parallel; returns (rows, failed cases)."""
    rows, failed = [], []
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        futures = {pool.submit(simulate_case, suite.NAME, c): c for c in cases}
        for n, future in enumerate(as_completed(futures), 1):
            case = futures[future]
            try:
                rows.extend(future.result())
                print(f"[{n}/{len(cases)}] {suite.NAME} case {case}: ok")
            except Exception as e:
                failed.append(case)
                print(f"[{n}/{len(cases)}] {suite.NAME} case {case}: FAILED\n{e}")
    return rows, failed


def check_results(suite, new, csv):
    """Differences between new results and the stored ones beyond the tolerance (DataFrame)."""
    old = read_results(csv) if csv.exists() else pd.DataFrame(columns=new.columns)
    merged = new.merge(old, on=["case", "output", "point"], how="left", suffixes=("", "_stored"))
    diff = (merged["value"] - merged["value_stored"]).abs()
    allowed = CHECK_RTOL * merged["value_stored"].abs() + CHECK_ATOL
    bad = merged[merged["value_stored"].isna() | (diff > allowed)]
    return bad[["case", "output", "point", "value_stored", "value"]]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--suite", choices=SUITES, nargs="+", default=list(SUITES))
    parser.add_argument("--cases", nargs="+", help="only these cases (results of the rest are kept)")
    parser.add_argument("--jobs", type=int, default=os.cpu_count(), help="parallel simulations")
    parser.add_argument("--report-only", action="store_true", help="do not simulate, only write the page")
    parser.add_argument("--check", action="store_true",
                        help="compare with the stored results instead of writing them (CI)")
    parser.add_argument("--quick", action="store_true", help="only the representative cases (QUICK_CASES)")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(exist_ok=True)
    all_failed, all_changed = [], []
    for name in args.suite:
        suite = SUITES[name]
        csv = RESULTS_DIR / f"{name}.csv"
        if args.report_only:
            continue
        cases = [c for c in suite.cases() if (not args.cases or c in args.cases)
                 and (not args.quick or c in QUICK_CASES.get(name, []))]
        if not cases:
            continue
        start = time.time()
        rows, failed = run_suite(suite, cases, args.jobs)
        all_failed += [f"{name} {c}" for c in failed]
        print(f"{name}: {len(cases)} cases in {time.time() - start:.0f} s")
        new = pd.DataFrame(rows, columns=["case", "output", "point", "value", "date"])
        if args.check:
            changed = check_results(suite, new, csv)
            print(f"{name}: {len(new)} values checked, {len(changed)} changed")
            if len(changed):
                print(changed.head(30).to_string(index=False))
                all_changed.append(name)
            continue
        if args.cases and csv.exists():  # keep the stored results of the other cases
            old = read_results(csv)
            new = pd.concat([old[~old["case"].isin(cases)], new])
        # Same order as the Standard's output form
        order = {key: i for i, key in enumerate(suite.CELLS)}
        new["position"] = [order[key] for key in zip(new["case"], new["output"], new["point"])]
        new = new.sort_values("position").drop(columns="position")
        new.to_csv(csv, index=False, float_format="%.6f")

    if args.check:
        if all_failed:
            print("Failed cases: " + ", ".join(all_failed))
        if all_changed:
            print("Results changed in: " + ", ".join(all_changed) + ". If the change is intended, run "
                  "validate.py without --check and commit the updated results and page.")
        sys.exit(1 if all_failed or all_changed else 0)

    results = {
        name: read_results(RESULTS_DIR / f"{name}.csv")
        for name in SUITES
        if (RESULTS_DIR / f"{name}.csv").exists()
    }
    page = report.write_page([SUITES[n] for n in results], results)
    print(f"Validation page written: {page}")
    if all_failed:
        print("Failed cases: " + ", ".join(all_failed))
        sys.exit(1)


if __name__ == "__main__":
    main()
