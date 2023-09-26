import OpenSimula


def test_simulation():
    sim = OpenSimula.Simulation()
    p1 = OpenSimula.Project(sim)
    p1.parameter("name").value = "Project 1"
    p2 = OpenSimula.Project(sim)
    p2.parameter("name").value = "Project 2"

    assert len(sim.project_list()) == 2
    assert sim.project("Project 1") == p1

    sim.del_project(sim.project("Project 2"))
    assert len(sim.project_list()) == 1
