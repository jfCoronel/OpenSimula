import opensimula as osim
import math
import pytest

def test_Iterative_process():
    def y(x):
        return math.cos(x)
    x_i = 0.5
    itera = osim.Iterative_process(x_i)    
    while not itera.converged():
        x_i = itera.estimate_next_x(y(x_i))

    assert x_i == pytest.approx(0.73908,abs=1e-4)


def test_Iterative_process_residual():
    # Slowly contracting fixed point (x = 0.95 x + 0.05, solution 1): at convergence the
    # fixed-point residual must be below the tolerance. Testing the relaxed step instead
    # stopped with residuals up to tol / lambda_min.
    def y(x):
        return 0.95 * x + 0.05
    tol = 1e-4
    x_i = 0.0
    itera = osim.Iterative_process(x_i, tol=tol, n_ini_relax=3, rel_vel=0.8)
    n = 0
    while not itera.converged() and n < 10000:
        x_i = itera.estimate_next_x(y(x_i))
        n += 1
    assert abs(y(x_i) - x_i) < tol
    assert x_i == pytest.approx(1, abs=tol / (1 - 0.95))
