import OpenSimula.Simulation as Simulation

sim = Simulation()
pro = sim.new_project("First example project")
pro.read_json('docs/getting_started.json')
pro.simulate()

data = [pro.component("year").variable("values")]
sim.plotly(pro.dates(), data)
