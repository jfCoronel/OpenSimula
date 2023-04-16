import opensimula as oms

sim = oms.Simulation()
print(sim.version)
proyecto = oms.Project('Proyecto 1', sim)
proyecto.info()

mat1 = oms.Component("Material", "Material 1", proyecto)
mat1.set({'conductivity': 0.4, 'density': -200, 'simplified_definition': 3})
print(mat1.parameter['conductivity'].value)
mat1.parameter['conductivity'].value = 0.8
mat1.info()
wall1 = oms.Component("Construction", "Wall 1", proyecto)
wall1.parameter['material'].value = "Material 1"
wall1.info()
