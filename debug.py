import OpenSimula.Simulation as Simulation

sim = Simulation()
pro = sim.new_project("First example project")
pro.read_json('ipynb/docs/getting_started.json')
pro.simulate()

data = [pro.component("year").variable("values")]
sim.plot(pro.dates(), data)
