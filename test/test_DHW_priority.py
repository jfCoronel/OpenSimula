"""DHW priority of a water plant (dhw_priority): the DHW loads get water at the heating
setpoint, up to the capacity of the generators, before the other loads."""

import numpy as np
import pytest

import test_Water_tank as tanks


def charging(priority, capacity, days=31):
    """The four-pipe plant (zones with MZW) charging a 200 l DHW tank."""
    data = tanks.charging_circuit(dead_band=5)
    for c in data["components"]:
        if c["name"] == "hot_water":
            c["dhw_priority"] = priority
        if c["name"] == "condensing_boiler":
            c["nominal_heating_capacity"] = capacity
    return tanks.simulate(data, days=days)


def v(pro, component, variable):
    return tanks.values(pro, component, variable)


def test_no_effect_with_enough_capacity():
    off, on = charging(False, 20000, days=7), charging(True, 20000, days=7)
    for component, variable in (("hot_water", "Q_generators"), ("dhw", "Q_supplied"),
                                ("tank", "temperature"), ("hot_water", "Q_heating_coils")):
        assert np.allclose(v(off, component, variable), v(on, component, variable))


def test_dhw_first_when_the_capacity_is_short():
    off, on = charging(False, 4000), charging(True, 4000)
    # with priority the tank is charged as with a big boiler (down to its dead band)
    assert v(on, "tank", "temperature").min() > 55 - 0.5
    assert v(off, "tank", "temperature").min() < 50
    assert v(on, "dhw", "Q_unmet").sum() < v(off, "dhw", "Q_unmet").sum()
    for pro in (off, on):
        assert v(pro, "hot_water", "Q_generators").max() <= 4000 + 1e-6
    p = "hot_water"
    balance = (v(on, p, "Q_generators") + v(on, p, "Q_loads") + v(on, p, "Q_loss")
               + v(on, p, "Q_pump") - v(on, p, "delta_U"))
    assert abs(balance.sum()) < 1e-3 * v(on, p, "Q_generators").sum()


def test_dhw_demand_of_a_combi_plant():
    """A DHW demand directly on the heating plant: water at the setpoint, at most the
    capacity of the generators."""
    import json
    data = json.loads(tanks.MZW.read_text(encoding="utf-8"))
    for c in data["components"]:
        if c["name"] == "hot_water":
            c.update({"heating_water_setpoint": "60", "system_on_off": "1", "dhw_priority": True})
        if c["name"] == "condensing_boiler":
            c["nominal_heating_capacity"] = 1500
    data["components"] += tanks.dhw("hot_water", 400)
    pro = tanks.simulate(data, days=7)
    draw = v(pro, "dhw", "Q_demand") > 0
    on = draw & (v(pro, "hot_water", "mode") == 1)
    assert np.allclose(v(pro, "dhw", "T_supply")[on], 60)
    assert np.all(-v(pro, "hot_water", "Q_dhw") <= 1500 + 1e-6)
    # the peaks of the demand above 1.5 kW are not met
    assert v(pro, "dhw", "Q_unmet").sum() == pytest.approx(
        np.sum(np.clip(v(pro, "dhw", "Q_demand") - 1500, 0, None)), rel=0.05, abs=1)


def test_balance_when_a_time_step_does_not_converge():
    """With the boiler short, the start of a morning does not converge (the load of the
    tank comes and goes with the temperature of the plant): the plant stores the
    temperature that satisfies the balance of the last iteration, not the relaxed one."""
    pro = charging(False, 4000)
    assert not pro._sim_df["converged"].all()
    p = "hot_water"
    residual = (v(pro, p, "Q_generators") + v(pro, p, "Q_loads") + v(pro, p, "Q_process")
                + v(pro, p, "Q_loss") + v(pro, p, "Q_pump") - v(pro, p, "delta_U"))
    assert np.abs(residual).max() < 1
