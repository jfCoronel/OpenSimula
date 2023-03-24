from opensimula.Simulation import Simulation
from opensimula.Project import Project

simul = Simulation()
print("Versión: ", simul.version)

p1 = Project()

simul.append(p1)
simul.append(Project())
simul.append("Hola")
