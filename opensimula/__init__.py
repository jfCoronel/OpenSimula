from opensimula.core import Simulation, Project
from opensimula.components import *


def Component(project, type):
    """Create component in one project using its type"""
    clase = globals()[type]
    comp = clase()
    project.addComponent(comp)
    return comp
