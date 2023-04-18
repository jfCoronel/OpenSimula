import json
import opensimula as oms

sim = oms.Simulation()
print(sim.version)
proyecto = oms.Project(sim)
proyecto.parameter['name'].value = 'Project One'
proyecto.info()

comp_1 = oms.Component("Test_component", proyecto)

with open('Component 1.json') as user_file:
    json_component = json.load(user_file)

comp_1.set_parameters(json_component)
comp_1.info()
# mat1 = oms.Component("Material", "Material 1", proyecto)
# mat1.set({'conductivity': 0.4, 'density': -200, 'simplified_definition': 3})
# print(mat1.parameter['conductivity'].value)
# mat1.parameter['conductivity'].value = 0.8
# mat1.info()
# wall1 = oms.Component("Construction", "Wall 1", proyecto)
# wall1.parameter['material'].value = "Material 1"
# wall1.info()
