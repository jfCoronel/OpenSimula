from opensimula.core import Simulation, Project
from opensimula.components import *


def Component(type, project):
    """Create component in one project using its type"""
    clase = globals()[type]
    comp = clase()
    project.add_component(comp)
    return comp
