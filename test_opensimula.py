import opensimula as oms

simul = oms.simulation()
proyecto = oms.project(simul)
proyecto.set({'name': 'Proyecto 1'})
proyecto.info()

mat1 = oms.component(proyecto, "Material")
mat1.set({'name': 'Material 1', 'conductivity': 0.4, 'density': -200, 'hola': 34})
mat1.info()
