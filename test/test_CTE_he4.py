"""CTE_compliance, HE4: renewable contribution to the DHW demand; Anejo F and G helpers."""

import sys
import pathlib

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import test_Solar_collector as solar  # noqa: E402
import test_Water_tank as tanks  # noqa: E402
from opensimula.cte import (  # noqa: E402
    dhw_reference_demand,
    he4_minimum_share,
    mains_temperatures,
)


def with_cte(data, **cte):
    for c in data["components"]:
        if c["type"] == "Energy_indicators":
            c["reference_area"] = 90
    data["components"].append({"type": "CTE_compliance", "name": "cte",
                               "energy_indicators": "energy", "climate_zone": "B4", **cte})
    return data


def test_anejo_f_and_g():
    assert dhw_reference_demand(bedrooms=3) == 112  # 4 persons · 28 l
    assert dhw_reference_demand(bedrooms=[1, 2, 7]) == 28 * (1.5 + 3 + 7)
    # 12 dwellings of 3 bedrooms, centralised: factor 0.90
    assert dhw_reference_demand(bedrooms=3, dwellings=12, centralised=True) == pytest.approx(
        12 * 4 * 28 * 0.90)
    assert dhw_reference_demand(use="Oficinas", persons=50) == 100
    with pytest.raises(ValueError):
        dhw_reference_demand(use="Oficina", persons=50)
    assert mains_temperatures("Sevilla") == [11, 11, 13, 14, 16, 19, 21, 21, 20, 16, 13, 11]
    # Granada (683 m) at 1000 m: 0.0066 K/m from October to March, 0.0033 from April
    T = mains_temperatures("Granada", 1000)
    assert T[0] == pytest.approx(8 - 0.0066 * 317) and T[6] == pytest.approx(20 - 0.0033 * 317)
    assert he4_minimum_share(100) == 0 and he4_minimum_share(101) == 0.6
    assert he4_minimum_share(5000) == 0.7


def test_he4_with_solar_thermal():
    pro = solar.simulate(with_cte(solar.solar_dhw()), days=365)
    r = pro.component("cte").report()
    s = r.summary
    Q_solar = solar.values(pro, "solar_gen", "Q").sum() / 1000
    Q_boiler = solar.values(pro, "boiler_gen", "Q").sum() / 1000
    assert s["dhw_renewable"] == pytest.approx(Q_solar)
    assert s["dhw_demand"] == pytest.approx(Q_solar + Q_boiler)
    assert s["dhw_daily_demand"] == pytest.approx(120)
    assert s["dhw_minimum_share"] == 0.6 and s["sections"] == "HE0 and HE4"
    row = r.checks.loc["Renewable share of DHW (HE4 3.1)"]
    assert row["value"] == pytest.approx(100 * Q_solar / (Q_solar + Q_boiler))
    assert bool(row["complies"])
    assert "DHW renewable contribution (HE4)" in r.to_html()


def test_he4_gas_boiler_does_not_comply():
    data = solar.solar_dhw()
    for c in data["components"]:
        if c["type"] == "DHW_demand":
            del c["preheat_system"]
    data["components"] = [c for c in data["components"]
                          if c["name"] not in ("collector", "solar_pump", "solar_gen", "solar_tank",
                                               "solar_plant")]
    pro = solar.simulate(with_cte(data), days=30)
    r = pro.component("cte").report()
    assert r.summary["dhw_renewable"] == 0
    assert not bool(r.checks.loc["Renewable share of DHW (HE4 3.1)", "complies"])
    assert not r.summary["complies"]


def heat_pump_dhw(cop):
    """DHW with an electric heat pump heating a 200 l tank to 55 °C."""
    data = tanks.water_heater({"volume": 200, "dead_band": 5})
    comps = [c for c in data["components"] if c["name"] not in ("resistance", "gen")]
    comps.insert(1, {"type": "Chiller_heat_pump", "name": "hp", "chiller_type": "HEAT_PUMP",
                     "nominal_heating_capacity": 2000, "nominal_heating_power": 2000 / cop,
                     "nominal_water_flow": 0.1})
    comps.insert(2, {"type": "HVAC_water_generator", "name": "gen", "equipment": "hp"})
    for c in comps:
        if c["type"] == "HVAC_water_system":
            c["heating_water_setpoint"] = "55"
        if c["type"] == "DHW_demand":
            c["use_temperature"] = "50"
    data["components"] = comps
    return with_cte(data)


def test_he4_heat_pump_counts_with_scop_dhw():
    for cop, counted in ((3.5, True), (2.0, False)):
        pro = tanks.simulate(heat_pump_dhw(cop), days=30)
        he4 = pro.component("cte").he4()
        Q = tanks.values(pro, "gen", "Q").sum() / 1000
        E = tanks.values(pro, "gen", "power").sum() / 1000
        assert he4["demand"] == pytest.approx(Q, rel=1e-6)
        if counted:
            assert Q / E >= 2.5
            assert he4["renewable"] == pytest.approx(Q - E, rel=1e-6)
        else:
            assert Q / E < 2.5 and he4["renewable"] == 0
        assert "SCOP_dhw" in he4["generators"].loc["gen", "counted as"]


def test_he4_applies_above_100_litres_a_day():
    pro = solar.simulate(with_cte(solar.solar_dhw(), dhw_daily_demand=80), days=7)
    r = pro.component("cte").report()
    assert "Renewable share of DHW (HE4 3.1)" not in r.checks.index
    assert r.summary["sections"] == "HE0"
    assert any("HE4 does not apply" in n for n in r.notes)
    pro = solar.simulate(with_cte(solar.solar_dhw(), dhw_daily_demand=6000), days=7)
    assert pro.component("cte").report().summary["dhw_minimum_share"] == 0.7
