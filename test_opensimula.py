import opensimula as oms

sim = oms.Simulation()
print(sim.version)
proyecto = oms.Project(sim)

proyecto.read_json("Proyecto_1.json")

proyecto.component[0].check()
proyecto.component[0].info()
