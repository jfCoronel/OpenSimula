import opensimula as osm
from opensimula.components.Material import Material

p1_json = {
    "name": "pro 1",
    "type": "Project",
    "components": [
        {
            "type": "Test_component",
            "name": "comp 1",
            "boolean": True,
            "string": "Hola mundo",
            "int": 24,
            "float": 34.6,
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
   
    m1 = Material()
    m1.parameter("name").value = "Material 1"
    m1.parameter("density").value = 900
    p1.add_component(m1)
    assert p1.component("Material 1") == m1
    assert p1.component("Material 1").parameter("density").value == 900
    
def test_load_from_dict():
    sim = osm.Simulation()
    p1 = osm.Project(sim)
    p1.load_from_dict(p1_json)
    
    assert len(p1.component_list()) == 2
    
    
    
   
    
