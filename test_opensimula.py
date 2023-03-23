from opensimula.Simulation import Simulation
from opensimula.Project import Project

simul = Simulation()
print("Versión: ", simul.version)

p1 = Project('Proyecto 1')
print("p1: ", p1.name)

simul.append(p1)
simul.append(Project('Proyecto 1'))
simul.append(Project('Proyecto 1'))
