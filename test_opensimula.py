import json
import opensimula as oms

sim = oms.Simulation()
print(sim.version)
proyecto = oms.Project(sim)

with open("Proyecto_1.json") as user_file:
    json_project = json.load(user_file)

proyecto.load_from_json(json_project)
proyecto.info()
# mat1 = oms.Component("Material", "Material 1", proyecto)
# mat1.set({'conductivity': 0.4, 'density': -200, 'simplified_definition': 3})
# print(mat1.parameter['conductivity'].value)
# mat1.parameter['conductivity'].value = 0.8
# mat1.info()
# wall1 = oms.Component("Construction", "Wall 1", proyecto)
# wall1.parameter['material'].value = "Material 1"
# wall1.info()
