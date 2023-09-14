import opensimula as osm
from opensimula.components.Material import Material

p1_dic = {
    "name": "project 1",
    "type": "Project",
    "components": [
        {
            "type": "Test_component",
            "name": "comp 1",
            "boolean": True,
            "string": "Hola mundo",
            "int": 24,
            "float": 34.5,
            "options": "Two",
            "boolean_list": [True, True],
            "string_list": ["Hola 1", "Hola 2"],
            "int_list": [1, 2],
            "float_list": [1.1, 2.1],
            "options_list": ["Two", "Two"],
        },
        {
            "type": "Test_component",
            "name": "comp 2",
            "boolean": True,
            "string": "Hola mundo",
            "int": 24,
            "float": 34.6,
            "options": "Two",
            "component": "comp 1",
        },
    ],
}

p2_dic = {
    "name": "project 2",
    "type": "Project",
    "components": [
        {
            "type": "Test_component",
            "name": "comp 3",
            "component": "project 1->comp 1",
            "component_list": ["project 1->comp 1", "project 1->comp 2"],
        }
    ],
}


def test_project_parameters():
    sim = osm.Simulation()
    p1 = osm.Project(sim)
    p1.parameter("name").value = "Project 1"
    p1.parameter("description").value = "Project 1 description"

    assert p1.simulation() == sim
    assert p1.parameter("name").value == "Project 1"
    assert p1.parameter("type").value == "Project"
    assert p1.parameter("description").value == "Project 1 description"


def test_managing_components():
    sim = osm.Simulation()
    p1 = osm.Project(sim)
    p1.parameter("name").value = "Project 1"

    m1 = Material(p1)
    m1.parameter("name").value = "Material 1"
    m1.parameter("density").value = 900
    p1.add_component(m1)
    assert p1.component("Material 1") == m1
    assert p1.component("Material 1").parameter("density").value == 900


def test_load_from_dict():
    sim = osm.Simulation()
    p1 = osm.Project(sim)
    p1.read_dict(p1_dic)

    assert len(p1.component_list()) == 2
    assert p1.component("comp 1").parameter("boolean").value == True
    assert p1.component("comp 1").parameter("string").value == "Hola mundo"
    assert p1.component("comp 1").parameter("int").value == 24
    assert p1.component("comp 1").parameter("float").value == 34.5
    assert p1.component("comp 1").parameter("options").value == "Two"
    assert p1.component("comp 1").parameter("boolean_list").value[1] == True
    assert p1.component("comp 1").parameter("string_list").value[0] == "Hola 1"
    assert p1.component("comp 1").parameter("int_list").value[1] == 2
    assert p1.component("comp 1").parameter("float_list").value[1] == 2.1
    assert p1.component("comp 1").parameter("options_list").value[1] == "Two"


def test_load_from_dic_two_projects():
    sim = osm.Simulation()
    p1 = osm.Project(sim)
    p1.read_dict(p1_dic)
    p2 = osm.Project(sim)
    p2.read_dict(p2_dic)

    comp_ref = p2.component("comp 3").parameter("component").component
    assert comp_ref.parameter("name").value == "comp 1"
    comp_ref = p2.component("comp 3").parameter("component_list").component[1]
    assert comp_ref.parameter("name").value == "comp 2"
