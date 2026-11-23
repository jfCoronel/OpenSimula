"""Comfort_indicators: hours of the zones outside the setpoints of their systems."""

import json
import pathlib

import numpy as np
import pytest

import opensimula as osm
from opensimula.comfort import Comfort_report

EXAMPLES = pathlib.Path(osm.__file__).parent / "examples"
MZW = pathlib.Path(__file__).parent / "mzw_four_pipe.json"


def simulate(path, start="01/07/2001 00:00:00", days=14, comfort=None):
    data = json.loads(path.read_text(encoding="utf-8"))
    data["initial_time"] = start
    data["n_time_steps"] = 24 * days
    for c in data["components"]:
        if c["type"] in ("File_met", "File_data"):
            c["file_name"] = str(EXAMPLES / pathlib.Path(c["file_name"]).name)
    data["components"].append({"type": "Comfort_indicators", "name": "comfort", **(comfort or {})})
    sim = osm.Simulation()
    sim.console_print = False
    pro = sim.new_project("p")
    pro.read_dict(data)
    problems = [m.text for m in sim.message_list() if m.level in ("ERROR", "WARNING")]
    assert problems == [], problems
    pro.simulate(progress=lambda i, n: None)
    return pro


@pytest.fixture(scope="module")
def dx():
    # September-October: the DX unit falls short in the afternoons
    return simulate(EXAMPLES / "06_dx_system.json", start="01/09/2001 00:00:00", days=61)


def values(pro, component, variable):
    return pro.component(component).variable(variable).values


def test_hours_outside_while_the_system_is_on(dx):
    T = values(dx, "office", "temperature")
    on = values(dx, "dx_system", "state") != 0
    above = on & (T > values(dx, "dx_system", "cooling_setpoint") + 0.5)
    below = on & (T < values(dx, "dx_system", "heating_setpoint") - 0.5)
    assert above.sum() > 0
    r = dx.component("comfort").report()
    assert isinstance(r, Comfort_report)
    row = r.zones.loc["office"]
    assert row["Hours counted"] == on.sum()
    assert row["Hours above"] == above.sum()
    assert row["Hours below"] == below.sum()
    assert row["Outside [%]"] == pytest.approx(100 * (above | below).sum() / on.sum())
    assert row["T max [°C]"] == pytest.approx(T[on].max())
    dh = (T - values(dx, "dx_system", "cooling_setpoint"))[above].sum()
    assert row["Degree-hours above [K·h]"] == pytest.approx(dh)
    assert r.monthly.loc["Total", "office"] == (above | below).sum()
    assert r.summary["share_outside"] == pytest.approx((above | below).sum() / on.sum())
    flag = values(dx, "comfort", "outside_office")
    assert np.array_equal(flag, np.where(above, 1, np.where(below, -1, 0)))
    assert np.array_equal(values(dx, "comfort", "zones_outside"), (flag != 0).astype(float))


def test_tolerance_and_period():
    pro = simulate(EXAMPLES / "06_dx_system.json", start="01/09/2001 00:00:00", days=30,
                   comfort={"tolerance": 0.0, "input_variables": ["f = office_hours.values"],
                            "period": "f"})
    T = values(pro, "office", "temperature")
    counted = (values(pro, "dx_system", "state") != 0) & (values(pro, "office_hours", "values") != 0)
    above = counted & (T > values(pro, "dx_system", "cooling_setpoint"))
    r = pro.component("comfort").report()
    assert r.zones.loc["office", "Hours counted"] == counted.sum()
    assert r.zones.loc["office", "Hours above"] == above.sum()
    assert "period = f" in r.summary["counted"]


def test_multizone_system_each_zone_with_its_setpoint():
    pro = simulate(MZW, start="01/01/2001 00:00:00", days=7)
    r = pro.component("comfort").report()
    zones = [z for z in r.zones.index if z != "TOTAL"]
    assert len(zones) == 2
    on = values(pro, "ahu", "state") != 0
    for i, zone in enumerate(pro.component("ahu").parameter("spaces").value):
        T = values(pro, zone, "temperature")
        sp = values(pro, "ahu", f"spaces_setpoint_{i}")
        outside = on & ((T > sp + 0.5) | (T < sp - 0.5))
        assert r.zones.loc[zone, "Hours outside"] == outside.sum()
    assert r.zones.loc["TOTAL", "Hours counted"] == 2 * on.sum()


def test_zone_without_system():
    pro = simulate(EXAMPLES / "04_windows_and_gains.json", days=3)
    r = pro.component("comfort").report()
    assert r.zones.loc["office", "Hours counted"] == 0
    assert any("no system" in n for n in r.notes)
    free = simulate(EXAMPLES / "04_windows_and_gains.json", days=3, comfort={"only_system_on": False})
    r = free.component("comfort").report()
    assert r.zones.loc["office", "Hours counted"] == 72
    assert r.zones.loc["office", "Hours outside"] == 0  # no setpoints to be outside of
    assert r.zones.loc["office", "T max [°C]"] == pytest.approx(values(free, "office", "temperature").max())


def test_report_as_html(dx):
    html = dx.component("comfort").report()._repr_html_()
    assert html.count("<table") == 2
    assert "Hours outside the setpoints" in html and "Sep 2001" in html
