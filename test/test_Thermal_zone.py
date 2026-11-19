import opensimula as osm
from opensimula.components import Space
from opensimula.components.Thermal_zone import Thermal_zone
from opensimula.editor import component_types


def test_space_is_a_thermal_zone():
    sim = osm.Simulation()
    pro = sim.new_project("p")
    space = pro.new_component("Space", "space")
    assert isinstance(space, Thermal_zone)
    assert isinstance(space, Space)


def test_thermal_zone_is_not_a_component_type():
    # a base class: neither in the editor's list of types nor creatable in a project
    assert "Thermal_zone" not in component_types()
    sim = osm.Simulation()
    pro = sim.new_project("p")
    assert pro.new_component("Thermal_zone", "zone") is None


def test_new_component_only_creates_component_types():
    sim = osm.Simulation()
    pro = sim.new_project("p")
    for name in ("Component", "json", "Not_a_type"):
        assert pro.new_component(name, "x") is None
    assert len(pro.component_list()) == 0
