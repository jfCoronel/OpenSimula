"""Hourly quantities of an HVAC_DX_system as the Standard's cooling tests (CE series) report them."""

import numpy as np


def dx_hourly(project, condenser_fan_power, system="system", space="spaces_1"):
    """Dictionary of hourly arrays (W, °C, kg/kg, %) of the DX system and its zone.

    The condenser fan is not modelled by the component: it runs at condenser_fan_power while
    the compressor runs (run time fraction F_load/efficiency_degradation), as in the
    Standard. The compressor power is the rest of the total power.
    """
    sys_ = project.component(system)
    zone = project.component(space)
    met = project.parameter("simulation_file_met").component

    def var(component, name):
        return component.variable(name).values.astype(float)

    f_load = var(sys_, "F_load")
    degradation = var(sys_, "efficiency_degradation")
    run_fraction = np.divide(f_load, degradation, out=np.zeros_like(f_load), where=degradation > 0)
    power = var(sys_, "power")
    indoor_fan = var(sys_, "indoor_fan_power")
    condenser_fan = run_fraction * condenser_fan_power
    q_sensible = var(sys_, "Q_sensible")
    q_latent = var(sys_, "Q_latent")
    h = {
        "power": power,
        "indoor_fan": indoor_fan,
        "condenser_fan": condenser_fan,
        "compressor": power - indoor_fan - condenser_fan,
        "coil_total": q_sensible + q_latent,
        "coil_sensible": q_sensible,
        "coil_latent": q_latent,
        "zone_total": -(var(zone, "system_sensible_heat") + var(zone, "system_latent_heat")),
        "zone_sensible": -var(zone, "system_sensible_heat"),
        "zone_latent": -var(zone, "system_latent_heat"),
        "zone_temperature": var(zone, "temperature"),
        "zone_humidity_ratio": var(zone, "abs_humidity") / 1000,
        "zone_rh": var(zone, "rel_humidity"),
        "entering_drybulb": var(sys_, "T_MA"),
        "entering_wetbulb": var(sys_, "T_MAwb"),
        "outdoor_temperature": var(met, "temperature"),
        "outdoor_humidity_ratio": var(met, "abs_humidity") / 1000,
    }
    # COP2 (Standard's definition): coil load / (compressor + condenser fan), hours with load
    work = h["compressor"] + h["condenser_fan"]
    h["cop2"] = np.divide(h["coil_total"], work, out=np.full_like(work, np.nan),
                          where=(h["coil_total"] > 0) & (work > 0))
    # COP of the steady-state cases: zone load / total power
    h["cop"] = np.divide(h["zone_total"], power, out=np.full_like(power, np.nan), where=power > 0)
    return h
