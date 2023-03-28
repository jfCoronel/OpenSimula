from opensimula.Simulation import Simulation
from opensimula.Project import Project
from opensimula.components.Material import Material

simul = Simulation()
p1 = Project()
m1 = Material()
m1.property["name"].value = "Material 1"
m1.property["conductivity"].value = 0.01
p1.addComponent(m1)
simul.addProject(p1)

p1.component[0].print()
