import opensimula as oms

sim = oms.Simulation()
print(sim.version)
proyecto = oms.Project(sim)
proyecto.set({'name': 'Proyecto 1'})
proyecto.info()

mat1 = oms.Component(proyecto, "Material")
mat1.set({'name': 'Material 1', 'conductivity': 0.4,
          'density': -200, 'simplified_definition': 3})
print(mat1.parameter['conductivity'].value)
mat1.parameter['conductivity'].value = 0.8
mat1.info()
