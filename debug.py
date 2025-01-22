import OpenSimula as osm
import numpy as np

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
            "no_load_cooling_power": 230,
            "nominal_cooling_conditions": [26.7,19.4,35],
            "total_cooling_capacity_expression": "9.099e-04 * T_odb + 4.351e-02 * T_iwb -3.475e-05 * T_odb^2 + 1.512e-04 * T_iwb^2 -4.703e-04 * T_odb * T_iwb + 4.281e-01",
            "sensible_cooling_capacity_expression": "1.148e-03 * T_odb - 7.886e-02 * T_iwb + 1.044e-01 * T_idb - 4.117e-05 * T_odb^2 - 3.917e-03 * T_iwb^2 - 2.450e-03 * T_idb^2 + 4.042e-04 * T_odb * T_iwb - 4.762e-04 * T_odb * T_idb + 5.503e-03 * T_iwb * T_idb  + 2.903e-01",
            "cooling_power_expression": "1.198e-02 * T_odb + 1.432e-02 * T_iwb + 5.656e-05 * T_odb^2 + 3.725e-05 * T_iwb^2 - 1.840e-04 * T_odb * T_iwb + 3.454e-01",
            "EER_expression": "1 - 0.229*(1-F_load)"
        }
    ]
}


sim = osm.Simulation()
pro = sim.new_project("pro")
pro.read_dict(case_dict)
print (pro.component("HVAC_equipment").get_cooling_state(26.7,19.4,35,25,1,1))
print (pro.component("HVAC_equipment").get_cooling_state(24.4,17.2,32.2,25,1,1))
print (pro.component("HVAC_equipment").get_cooling_state(26.7,15,46.1,25,1,1))
print (pro.component("HVAC_equipment").get_cooling_state(24.4,17.2,32.2,25,1,0.3))