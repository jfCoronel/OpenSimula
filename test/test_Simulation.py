import OpenSimula


def test_simulation():
    sim = OpenSimula.Simulation()
    p1 = OpenSimula.Project("Project 1",sim)
    p2 = OpenSimula.Project("Project 2",sim)

    assert len(sim.project_list()) == 2
    assert sim.project("Project 1") == p1

    sim.del_project(sim.project("Project 2"))
    assert len(sim.project_list()) == 1
