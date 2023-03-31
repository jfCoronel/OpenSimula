from opensimula.core import Simulation, Project
from opensimula.components import *


# OpenSimula
def simulation():
    """Create simulation"""
    sim = Simulation()
    return sim


def project(sim):
    """Create project in the simulation environment"""
    pro = Project()
    sim.addProject(pro)
    return pro


def component(project, type):
    """Create component in one project using its type"""
    clase = globals()[type]
    comp = clase()
    project.addComponent(comp)
    return comp
