import opensimula as osm


def test_simulation():
    sim = osm.Simulation()
    p1 = osm.Project(sim)
    p1.parameter["name"].value = "Project 1"
    p2 = osm.Project(sim)
    p2.parameter["name"].value = "Project 2"

    assert len(sim.projects) == 2
    assert sim.find_project("Project 1") == p1

    sim.del_project(sim.find_project("Project 2"))
    assert len(sim.projects) == 1


def test_project():
    sim = osm.Simulation()
    p1 = osm.Project(sim)
    p1.parameter["name"].value = "Project 1"
    p1.parameter["description"].value = "Project 1 description"

    assert p1.parent == sim
    assert p1.parameter["name"].value == "Project 1"
    assert p1.parameter["type"].value == "Project"
    assert p1.parameter["description"].value == "Project 1 description"
