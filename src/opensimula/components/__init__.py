from opensimula.components.Test_component import Test_component
from opensimula.components.Material import Material
from opensimula.components.Glazing import Glazing
from opensimula.components.Frame import Frame
from opensimula.components.Construction import Construction
from opensimula.components.Opening_type import Opening_type
from opensimula.components.File_data import File_data
from opensimula.components.Day_schedule import Day_schedule
from opensimula.components.Week_schedule import Week_schedule
from opensimula.components.Year_schedule import Year_schedule
from opensimula.components.File_met import File_met
from opensimula.components.Space_type import Space_type
from opensimula.components.Building import Building
from opensimula.components.Space import Space
from opensimula.components.Load_space import Load_space
from opensimula.components.Building_surface import Building_surface
from opensimula.components.Solar_surface import Solar_surface
from opensimula.components.Opening import Opening
from opensimula.components.Calculator import Calculator
from opensimula.components.DX_unit import DX_unit
from opensimula.components.Water_coil import Water_coil
from opensimula.components.Fan import Fan
from opensimula.components.Pump import Pump
from opensimula.components.HVAC_DX_system import HVAC_DX_system
from opensimula.components.HVAC_SZW_system import HVAC_SZW_system
from opensimula.components.HVAC_MZW_system import HVAC_MZW_system
from opensimula.components.HVAC_perfect_system import HVAC_perfect_system
from opensimula.components.Chiller_heat_pump import Chiller_heat_pump
from opensimula.components.Boiler import Boiler
from opensimula.components.HVAC_water_generator import HVAC_water_generator
from opensimula.components.HVAC_water_circuit import HVAC_water_circuit
from opensimula.components.DHW_demand import DHW_demand
from opensimula.components.Water_tank import Water_tank
from opensimula.components.HVAC_water_system import HVAC_water_system
from opensimula.components.Energy_indicators import Energy_indicators
from opensimula.components.Comfort_indicators import Comfort_indicators
from opensimula.components.CTE_compliance import CTE_compliance

DEFAULT_COMPONENTS_ORDER = [
                    "Space_type",
                    "Building_surface",
                    "Solar_surface",
                    "Opening",
                    "Space",
                    "Load_space",
                    "Building",
                    "HVAC_MZW_system",
                    "HVAC_perfect_system",
                    "HVAC_DX_system",
                    "HVAC_SZW_system",
                    "DHW_demand",
                    "HVAC_water_circuit",
                    "HVAC_water_generator",
                    "HVAC_water_system",
                    "Calculator",
                    "Energy_indicators",
                    "Comfort_indicators",
                    "CTE_compliance"
                ]

