"""Energy carriers and services used to report the energy use of the components.

Every component that uses energy reports it with ``Component.get_energy_use()``:
a list of ``Energy_use(carrier, service, values)``, where ``values`` is the power
(W) at each time step of the simulation, positive. ``Energy_indicators`` adds them
up, converts them to primary energy and CO₂ and splits them in its report.
"""

from typing import NamedTuple

import numpy as np

# Carriers: what is used. Fuels as in Boiler.fuel; AMBIENT is the energy taken
# from the environment by heat pumps (renewable); THERMAL is heat supplied with no
# equipment behind it (ideal systems, coils with an unknown water source), not
# final energy until a hypothesis gives it a generator.
CARRIERS = [
    "ELECTRICITY",
    "NATURAL_GAS",
    "LPG",
    "DIESEL",
    "BIOMASS",
    "AMBIENT",
    "THERMAL",
]

# Services: what it is used for. Pumps and fans are their own services; splitting
# them among heating, cooling or DHW is a hypothesis of the report.
SERVICES = [
    "HEATING",
    "COOLING",
    "WATER_TRANSPORT",
    "AIR_TRANSPORT",
    "LIGHTING",
    "EQUIPMENT",
    "HEATING_WITHOUT_EQUIPMENT",
    "COOLING_WITHOUT_EQUIPMENT",
]


class Energy_use(NamedTuple):
    """Power used by a component for one carrier and service.

    Attributes:
        carrier (str): one of ``CARRIERS``.
        service (str): one of ``SERVICES`` (or a user service, e.g. "DHW").
        values (numpy.ndarray): power (W) at each time step, positive.
    """

    carrier: str
    service: str
    values: np.ndarray


def positive(values):
    """Positive part of an array, as a new float array."""
    return np.clip(np.asarray(values, dtype=float), 0, None)


def where(condition, values):
    """Values where condition is true, 0 elsewhere, as a new float array."""
    return np.where(condition, np.asarray(values, dtype=float), 0.0)
