import opensimula as osm
import math
import pytest

def test_Iterative_process():
    def y(x):
        return math.cos(x)
    x_i = 0.5
    itera = osm.Iterative_process(x_i)    
    while not itera.converged():
        x_i = itera.estimate_next_x(y(x_i))

    assert x_i == pytest.approx(0.73908,abs=1e-4)
