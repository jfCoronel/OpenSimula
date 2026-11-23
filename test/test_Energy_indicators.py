"""Energy_indicators: final energy, primary energy, CO2 and the report."""

import json
import pathlib

import numpy as np
import pytest

import opensimula as osm
from opensimula.energy import ELECTRICITY_FACTORS, FUEL_FACTORS, Energy_report

EXAMPLES = pathlib.Path(osm.__file__).parent / "examples"


def simulate(name, start="01/01/2001 00:00:00", days=14, indicators=None, extra=()):
    data = json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8"))
    data["initial_time"] = start
    data["n_time_steps"] = 24 * days
    for c in data["components"]:
        if c["type"] in ("File_met", "File_data"):
            c["file_name"] = str(EXAMPLES / pathlib.Path(c["file_name"]).name)
    data["components"].append({"type": "Energy_indicators", "name": "energy", **(indicators or {})})
    data["components"] += list(extra)
    sim = osm.Simulation()
    sim.console_print = False
    pro = sim.new_project("p")
    pro.read_dict(data)
    problems = [m.text for m in sim.message_list() if m.level in ("ERROR", "WARNING")]
    assert problems == [], problems
    pro.simulate(progress=lambda i, n: None)
    return pro


@pytest.fixture(scope="module")
def plant():
    # heat pump + backup boiler, two circuits, fan coils, two Load_space (96 m²)
    return simulate("09_water_plant", days=21)


@pytest.fixture(scope="module")
def ideal():
    # ideal system and a Space with lighting and equipment
    return simulate("05_ideal_system", start="01/03/2001 00:00:00")


def kwh(values):
    return values.sum() / 1000  # hourly steps


def test_variables_add_up_the_uses(plant):
    e = plant.component("energy")
    uses = e.get_uses()
    for carrier in ("ELECTRICITY", "NATURAL_GAS", "AMBIENT"):
        expected = sum(u.values for u in uses if u.carrier == carrier)
        assert np.allclose(e.variable(carrier.lower()).values, expected)
    assert kwh(e.variable("natural_gas").values) == pytest.approx(
        kwh(plant.component("water_plant").variable("generators_fuel_power").values))
    services = sum(e.variable(s).values for s in
                   ("heating", "cooling", "water_transport", "air_transport"))
    final = e.variable("electricity").values + e.variable("natural_gas").values
    assert np.allclose(services, final)  # services hold final energy, not AMBIENT
    f_el, f_gas = ELECTRICITY_FACTORS["PENINSULA"], FUEL_FACTORS["NATURAL_GAS"]
    nren = e.variable("electricity").values * f_el[1] + e.variable("natural_gas").values * f_gas[1]
    assert np.allclose(e.variable("primary_nren").values, nren)
    ren = (e.variable("electricity").values * f_el[0] + e.variable("natural_gas").values * f_gas[0]
           + e.variable("ambient").values)
    assert np.allclose(e.variable("primary_ren").values, ren)
    co2 = (e.variable("electricity").values * f_el[2] + e.variable("natural_gas").values * f_gas[2]) / 1000
    assert np.allclose(e.variable("CO2").values, co2)


def test_report_tables_are_consistent(plant):
    e = plant.component("energy")
    r = e.report()
    assert isinstance(r, Energy_report)
    total = r.annual.loc["TOTAL", "TOTAL"]
    assert total == pytest.approx(kwh(e.variable("electricity").values + e.variable("natural_gas").values))
    assert r.annual.loc["TOTAL", "AMBIENT"] == pytest.approx(kwh(e.variable("ambient").values))
    assert r.monthly_carriers.loc["Total", "TOTAL"] == pytest.approx(total)
    assert r.monthly_services.loc["Total", "TOTAL"] == pytest.approx(total)
    assert list(r.monthly_carriers.index[:-1]) == ["Jan 2001"]
    assert r.indicators.loc["TOTAL", "Final [kWh]"] == pytest.approx(total)
    assert r.indicators.loc["TOTAL", "Primary nren [kWh]"] == pytest.approx(
        kwh(e.variable("primary_nren").values))
    assert r.summary["reference_area"] == 96
    assert r.indicators_per_area.loc["TOTAL", "Primary nren [kWh/m²]"] == pytest.approx(
        r.summary["primary_nren"] / 96)
    assert 0 < r.summary["renewable_share"] < 1


def test_transport_kept_apart_by_default_or_assigned_by_mode(plant):
    e = plant.component("energy")
    apart = e.report()
    by_mode = e.report(water_transport="BY_MODE", air_transport="BY_MODE")
    assert by_mode.summary["primary_nren"] == pytest.approx(apart.summary["primary_nren"])
    water = apart.annual.loc["WATER_TRANSPORT", "TOTAL"]
    assert water > 0
    left = by_mode.annual["TOTAL"].get("WATER_TRANSPORT", 0)
    assert left < water
    assert by_mode.annual.loc["TOTAL", "TOTAL"] == pytest.approx(apart.annual.loc["TOTAL", "TOTAL"])
    assert by_mode.annual.loc["HEATING", "TOTAL"] > apart.annual.loc["HEATING", "TOTAL"]
    # only the water: the air stays apart
    water_only = e.report(water_transport="BY_MODE")
    assert water_only.annual.loc["AIR_TRANSPORT", "TOTAL"] == pytest.approx(
        apart.annual.loc["AIR_TRANSPORT", "TOTAL"])
    with pytest.raises(ValueError):
        e.report(water_transport="HALF")


def test_report_as_html(plant):
    html = plant.component("energy").report()._repr_html_()
    assert html.count("<table") == 5
    assert "Final energy by month and carrier" in html and "Jan 2001" in html
    assert "Renewable share" in html


def test_lighting_equipment_and_heat_without_equipment(ideal):
    e = ideal.component("energy")
    r = e.report()
    office = ideal.component("office")
    light = office.variable("light_convective").values + office.variable("light_radiant").values
    assert r.annual.loc["LIGHTING", "ELECTRICITY"] == pytest.approx(kwh(light))
    assert r.annual.loc["EQUIPMENT", "ELECTRICITY"] > 0
    heat = r.annual.loc["HEATING_WITHOUT_EQUIPMENT", "THERMAL"]
    cold = r.annual.loc["COOLING_WITHOUT_EQUIPMENT", "THERMAL"]
    assert heat > 0 and cold > 0
    assert r.annual.loc["HEATING_WITHOUT_EQUIPMENT", "TOTAL"] == 0  # not final energy
    assert any("THERMAL" in n for n in r.notes)
    # reference generators: a gas boiler and an electric chiller
    ref = e.report(reference_heating=("NATURAL_GAS", 0.92), reference_cooling=("ELECTRICITY", 2.6))
    assert "THERMAL" not in ref.annual.columns
    assert ref.annual.loc["HEATING", "NATURAL_GAS"] == pytest.approx(heat / 0.92)
    assert ref.annual.loc["COOLING", "ELECTRICITY"] == pytest.approx(cold / 2.6)
    # a heat pump: the rest of the heat is ambient energy; none in cooling
    hp = e.report(reference_heating=("ELECTRICITY", 3.0))
    assert hp.annual.loc["HEATING", "AMBIENT"] == pytest.approx(heat * 2 / 3)
    assert "COOLING" not in hp.annual.index or hp.annual.loc["COOLING", "AMBIENT"] == 0


def test_equipment_carrier_custom_factors_and_extra_uses():
    pro = simulate(
        "05_ideal_system", days=7,
        indicators={
            "equipment_carrier": "NATURAL_GAS",
            "conversion_factors": "CANARIAS",
            "custom_carriers": ["NATURAL_GAS"],
            "custom_fp_ren": [0.0], "custom_fp_nren": [1.5], "custom_CO2": [0.3],
            "input_variables": ["f = office_hours.values"],
            "extra_services": ["DHW"], "extra_carriers": ["ELECTRICITY"],
            "extra_expressions": ["500 * f"],
        })
    e = pro.component("energy")
    r = e.report()
    assert r.annual.loc["EQUIPMENT", "NATURAL_GAS"] > 0
    assert r.annual.loc["EQUIPMENT", "ELECTRICITY"] == 0
    hours = pro.component("office_hours").variable("values").values
    assert r.annual.loc["DHW", "ELECTRICITY"] == pytest.approx(0.5 * hours.sum())
    assert np.allclose(e.variable("dhw").values, 500 * hours)
    gas = r.annual.loc["TOTAL", "NATURAL_GAS"]
    el = r.annual.loc["TOTAL", "ELECTRICITY"]
    assert r.summary["primary_nren"] == pytest.approx(gas * 1.5 + el * ELECTRICITY_FACTORS["CANARIAS"][1])


def test_check_sizes():
    sim = osm.Simulation()
    sim.console_print = False
    pro = sim.new_project("p")
    pro.read_dict({"components": [{"type": "Energy_indicators", "name": "e",
                                   "extra_services": ["DHW"], "extra_carriers": [],
                                   "extra_expressions": ["1"]}]})
    errors = [m.text for m in pro.check() if m.level == "ERROR"]
    assert any("extra_services" in t for t in errors)
