import opensimula as oms

simul = oms.simulation()
proyecto = oms.project(simul)
proyecto.info()

mat1 = oms.component(proyecto, "Material")
mat1.parameter['conductivity'].value = 0.4
mat1.parameter['density'].value = -200
mat1.info()
