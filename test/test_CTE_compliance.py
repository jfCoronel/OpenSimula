"""CTE_compliance: verification of CTE DB-HE, section HE0."""

import json
import pathlib

import numpy as np
import pytest

import opensimula as osm
from opensimula.cte import he0_limits, internal_load_level, winter_zone

EXAMPLES = pathlib.Path(osm.__file__).parent / "examples"


def simulate(name, cte=None, comfort=None, energy=None, days=14, start="01/07/2001 00:00:00"):
    data = json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8"))
    data["initial_time"] = start
    data["n_time_steps"] = 24 * days
    for c in data["components"]:
        if c["type"] in ("File_met", "File_data"):
            c["file_name"] = str(EXAMPLES / pathlib.Path(c["file_name"]).name)
    # example 10 has its own "energy" and "comfort": update them instead of adding
    existing = {c["name"]: c for c in data["components"]}
    for comp in ({"type": "Energy_indicators", "name": "energy", **(energy or {})},
                 {"type": "Comfort_indicators", "name": "comfort", "tolerance": 1.0,
                  **(comfort or {})},
                 {"type": "CTE_compliance", "name": "cte", "energy_indicators": "energy",
                  "comfort_indicators": "comfort", "climate_zone": "B4", **(cte or {})}):
        if comp["name"] in existing:
            existing[comp["name"]].update(comp)
        else:
            data["components"].append(comp)
    sim = osm.Simulation()
    sim.console_print = False
    pro = sim.new_project("p")
    pro.read_dict(data)
    problems = [m.text for m in sim.message_list() if m.level in ("ERROR", "WARNING")]
    pro.problems = problems
    if not any(m.level == "ERROR" for m in sim.message_list()):
        pro.simulate(progress=lambda i, n: None)
    return pro


def test_limits_of_the_tables():
    assert winter_zone("B4") == "B" and winter_zone("alpha3") == "α" and winter_zone("α2") == "α"
    assert winter_zone("F2") is None and winter_zone("B5") is None and winter_zone("B") is None
    assert he0_limits("B4", "RESIDENTIAL_PRIVATE", "NEW_OR_EXTENSION") == (28, 56)
    assert he0_limits("E1", "RESIDENTIAL_PRIVATE", "CHANGE_OF_USE_OR_REFORM") == (80, 115)
    assert he0_limits("α3", "RESIDENTIAL_PRIVATE", "NEW_OR_EXTENSION", extrapeninsular=True) == \
        pytest.approx((20 * 1.25, 40 * 1.15))
    assert he0_limits("B4", "OTHER", "NEW_OR_EXTENSION", c_fi=4.0) == (50 + 32, 150 + 36)
    assert he0_limits("D3", "OTHER", "CHANGE_OF_USE_OR_REFORM", c_fi=10, extrapeninsular=True) == \
        pytest.approx(((20 + 80) * 1.4, (130 + 90) * 1.4))
    assert [internal_load_level(x) for x in (4, 6, 9, 12)] == ["low", "medium", "high", "very high"]


@pytest.fixture(scope="module")
def office():
    # the office with the DX unit, as a building of other use (tertiary)
    return simulate("06_dx_system", cte={"building_use": "OTHER"})


def test_tertiary_counts_lighting_and_uses_the_internal_load(office):
    cte = office.component("cte")
    r = cte.report()
    e = office.component("energy").report(water_transport="BY_MODE", air_transport="BY_MODE")
    area = r.summary["reference_area"]
    assert area == 48
    epb = [s for s in e.indicators.index if s not in ("TOTAL", "EQUIPMENT")]
    assert "LIGHTING" in epb and "LIGHTING" in r.services.index
    assert "EQUIPMENT" not in r.services.index
    nren = e.indicators.loc[epb, "Primary nren [kWh]"].sum() / area
    assert r.summary["cep_nren"] == pytest.approx(nren)
    # C_FI: mean sensible gains of occupancy, lighting and equipment per m²
    o = office.component("office")
    gains = sum(np.mean(o.variable(k).values) for k in (
        "people_convective", "people_radiant", "light_convective", "light_radiant",
        "other_gains_convective", "other_gains_radiant"))
    assert r.summary["c_fi"] == pytest.approx(gains / 48)
    assert r.summary["cep_nren_limit"] == pytest.approx(50 + 8 * gains / 48)
    assert r.summary["cep_tot_limit"] == pytest.approx(150 + 9 * gains / 48)
    c = office.component("comfort").report().summary
    hours = r.checks.loc["Hours outside setpoint (HE0 4.1.6)"]
    assert hours["value"] == c["building_hours_outside"]
    assert hours["limit"] == pytest.approx(0.04 * 24 * 14)
    assert r.summary["complies"] == bool(r.checks["complies"].all())
    html = r._repr_html_()
    assert html.count("<table") == 2 and "HE0 requirements" in html
    # the results as marks (the table keeps booleans)
    assert r.checks["complies"].dtype == bool
    n_ok = int(r.checks["complies"].sum())
    assert html.count("✔ complies") == n_ok
    assert html.count("✘ does not comply") == len(r.checks) - n_ok
    assert ("✔ Complies with HE0" if r.summary["complies"] else "✘ Does not comply with HE0") in html
    assert "✘ does not comply" in repr(r) or n_ok == len(r.checks)


def test_residential_leaves_lighting_out_and_internal_load_given():
    pro = simulate("06_dx_system", cte={"building_use": "OTHER", "internal_load": 4.0}, days=3)
    assert pro.component("cte").report().summary["c_fi"] == 4.0
    res = simulate("06_dx_system", days=3)
    r = res.component("cte").report()
    assert "LIGHTING" not in r.services.index
    assert r.summary["cep_nren_limit"] == 28 and r.summary["cep_tot_limit"] == 56


def test_residential_reference_systems_for_heat_without_equipment():
    pro = simulate("05_ideal_system", start="01/01/2001 00:00:00", days=14)
    r = pro.component("cte").report()
    e = pro.component("energy").report()
    heat = e.annual.loc["HEATING_WITHOUT_EQUIPMENT", "THERMAL"]
    assert heat > 0
    gas = pro.component("energy").report(
        reference_heating=("NATURAL_GAS", 0.92 * 1.11)).annual.loc["HEATING", "NATURAL_GAS"]
    assert gas == pytest.approx(heat / (0.92 * 1.11))
    assert "HEATING" in r.services.index
    assert any("table 4.5-HE0" in n for n in r.notes)


def test_extrapeninsular_from_the_factors():
    pro = simulate("06_dx_system", energy={"conversion_factors": "CANARIAS"},
                   cte={"climate_zone": "A2"}, days=2)
    s = pro.component("cte").report().summary
    assert s["extrapeninsular"]
    assert s["cep_nren_limit"] == pytest.approx(25 * 1.25)


def test_checks():
    pro = simulate("06_dx_system", cte={"climate_zone": "F9"}, days=1)
    assert any("climate_zone" in t for t in pro.problems)
    pro = simulate("06_dx_system", comfort={"tolerance": 0.5}, days=1)
    assert any("tolerance" in t for t in pro.problems)
    # Load_space zones: C_FI must be given for other uses
    pro = simulate("10_energy_and_comfort", cte={"building_use": "OTHER"}, days=1)
    assert any("internal_load" in t for t in pro.problems)
    pro = simulate("10_energy_and_comfort", cte={"building_use": "OTHER", "internal_load": 5},
                   days=2)
    assert pro.component("cte").report().summary["c_fi"] == 5
