import opensimula as oms
import datetime as dt

sim = oms.Simulation()
proyecto = oms.Project(sim)

proyecto.read_json("Proyecto_1.json")

proyecto.component[0].check()
proyecto.component[0].info()
time = dt.datetime(2001, 1, 1, 0, 18)
print(time)
print(proyecto.component[0].get_instant_values(time))
