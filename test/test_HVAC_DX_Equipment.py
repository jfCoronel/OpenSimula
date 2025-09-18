import OpenSimula as osm
import pytest

case_dict = {
    "name": "Test_HVAC_DX_equipment",
    "components": [
        {
            "type": "HVAC_DX_equipment",
            "name": "HVAC_equipment",
            "nominal_air_flow": 0.4248,
            "nominal_total_cooling_capacity": 7951,
            "nominal_sensible_cooling_capacity": 6136,
            "nominal_cooling_power": 2198,
            "indoor_fan_power": 230,
            "nominal_cooling_conditions": [26.7,19.4,35],
            "total_cooling_capacity_expression": "9.099e-04 * T_odb + 4.351e-02 * T_iwb -3.475e-05 * T_odb**2 + 1.512e-04 * T_iwb**2 -4.703e-04 * T_odb * T_iwb + 4.281e-01",
            "sensible_cooling_capacity_expression": "1.148e-03 * T_odb - 7.886e-02 * T_iwb + 1.044e-01 * T_idb - 4.117e-05 * T_odb**2 - 3.917e-03 * T_iwb**2 - 2.450e-03 * T_idb**2 + 4.042e-04 * T_odb * T_iwb - 4.762e-04 * T_odb * T_idb + 5.503e-03 * T_iwb * T_idb  + 2.903e-01",
            "cooling_power_expression": "1.198e-02 * T_odb + 1.432e-02 * T_iwb + 5.656e-05 * T_odb**2 + 3.725e-05 * T_iwb**2 - 1.840e-04 * T_odb * T_iwb + 3.454e-01",
            "EER_expression": "1 - 0.229*(1-F_load)"
        }
    ]
}


def test_points():
    sim = osm.Simulation()
    pro = sim.new_project("pro")
    pro.read_dict(case_dict)

    nominal_Q = pro.component("HVAC_equipment").get_cooling_load(26.7,19.4,35,25,1,-6136)
    nominal_P = pro.component("HVAC_equipment").get_cooling_power(26.7,19.4,35,25,1,-6136)
    wet_coil_Q = pro.component("HVAC_equipment").get_cooling_load(24.4,17.2,32.2,25,1,-4000)
    dry_coil_Q = pro.component("HVAC_equipment").get_cooling_load(26.7,15,46.1,25,1,-3000)

    assert nominal_Q[0] == pytest.approx(5886.04,rel=1e-2) # Q_eq
    assert nominal_Q[1] == pytest.approx(6116.4,rel=1e-2) # Q_sen
    assert nominal_Q[2] == pytest.approx(1827.35,rel=1e-2) # Q_lat
    assert nominal_P[0] == pytest.approx(2429.93,rel=1e-2) # P_tot
    assert nominal_P[1] == pytest.approx(230,rel=1e-2) # P_indoor_fan

    assert wet_coil_Q[0] == pytest.approx(3770,rel=1e-2)
    assert wet_coil_Q[1] == pytest.approx(4000,rel=1e-2)
    assert wet_coil_Q[2] == pytest.approx(860.53,rel=1e-2)

    assert dry_coil_Q[0] == pytest.approx(2770,rel=1e-2)
    assert dry_coil_Q[1] == pytest.approx(3000,rel=1e-2)
    assert dry_coil_Q[2] == pytest.approx(0,rel=1e-2)


