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

    nominal = pro.component("HVAC_equipment").get_cooling_state(26.7,19.4,35,25,1,1)
    wet_coil = pro.component("HVAC_equipment").get_cooling_state(24.4,17.2,32.2,25,1,1)
    dry_coil = pro.component("HVAC_equipment").get_cooling_state(26.7,15,46.1,25,1,1)
    wet_coil_part_load = pro.component("HVAC_equipment").get_cooling_state(24.4,17.2,32.2,25,1,0.3)


    assert nominal[0] == pytest.approx(7951,rel=1e-2)
    assert nominal[1] == pytest.approx(6136,rel=1e-2)
    assert nominal[2] == pytest.approx(2198+230,rel=1e-2)

    assert wet_coil[0] == pytest.approx(7570,rel=1e-2)
    assert wet_coil[1] == pytest.approx(6280,rel=1e-2)
    assert wet_coil[2] == pytest.approx(2078+230,rel=1e-2)

    assert dry_coil[0] == pytest.approx(6900,rel=1e-2)
    assert dry_coil[1] == pytest.approx(6900,rel=1e-2)
    assert dry_coil[2] == pytest.approx(2480+230,rel=1e-2)

    assert wet_coil_part_load[0] == pytest.approx( wet_coil[0]*.3)
    assert wet_coil_part_load[1] == pytest.approx( wet_coil[1]*.3)
    assert wet_coil_part_load[2] == pytest.approx( (wet_coil[2]-230)*0.3/(1 - 0.229*0.7) +230)

