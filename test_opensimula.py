from opensimula.Simulation import Simulation
from opensimula.Project import Project
from opensimula.Component import Component
from opensimula.Property_string import Property_string
from opensimula.Property_boolean import Property_boolean
from opensimula.Variable import Variable

simul = Simulation()
print("Versión: ", simul.version)

p1 = Project()
c1 = Component()
c1.addProperty(Property_string('nombre', value='Componente 1'))
c1.addProperty(Property_boolean('activo', False, True))
c1.addVariable(Variable('temperature'))
p1.addComponent(c1)

simul.addProject(p1)

print(simul.project[0].component[0].property['nombre'].value)
print(simul.project[0].component[0].property['activo'].value)
