import math

class Iterative_process:
    """Iterative process using the fixed-point method with adaptive relaxation coefficient

    Used by the components to converge a value coupled with other components (e.g. the
    temperature or humidity of a space) within the iterations of a time step:

    ```python
    it = Iterative_process(x_0, tol=0.01)
    # in each iteration, with the value proposed by the component's equations
    x = it.estimate_next_x(proposed_x)
    converged = it.converged()
    ```
    """

    def __init__(self, x_0, tol = 1e-5, lambda_min=0.1, lambda_max=1.0, n_ini_relax=2,rel_vel = 0.9):
        """Create new iterative process

        Args:
            x_0 (float): Initial value
            tol (float, optional): convergence tolerance of the residual. Defaults to 1e-5.
            lambda_min (float, optional): minimum relaxation coefficient. Defaults to 0.1.
            lambda_max (float, optional): maximum (and initial) relaxation coefficient.
                Defaults to 1.0.
            n_ini_relax (int, optional): Number of iterations in which adaptive relaxation
                is initiated, must be greater than 1. Defaults to 2.
            rel_vel (float, optional): factor that reduces (or, divided, recovers) the
                relaxation coefficient. Defaults to 0.9.
        """
        self.x = [x_0]
        self.tol = tol
        self.lambda_min = lambda_min
        self.lambda_max = lambda_max
        self.lambda_i = lambda_max
        self.n_ini_relax = n_ini_relax
        self.rel_vel = rel_vel
        self.residual = None  # |proposed_x - x| of the last iteration

    def converged(self):
        """The residual of the last iteration is below the tolerance

        Returns:
            bool: converged
        """
        # Fixed-point residual, not the relaxed step: with relaxation lambda the step is only
        # lambda * residual, so testing the step stopped with residuals up to tol / lambda_min
        # (10 x tol), e.g. zones far from their moisture balance in steady state
        return self.residual is not None and self.residual < self.tol

    def estimate_next_x(self, proposed_x):
        """Relaxed next value from the value proposed by the fixed-point equation

        Args:
            proposed_x (float): value given by the equations from the last value

        Returns:
            float: next value, `(1 - lambda) * x + lambda * proposed_x`
        """
        residual = proposed_x - self.x[-1]
        x_next = (1 - self.lambda_i) * self.x[-1] + self.lambda_i * proposed_x

        # Adaptive relaxation: reduce lambda when the iteration oscillates (the residual
        # changes sign) or does not contract (the residual grows), and recover it while it
        # contracts; reducing it unconditionally made well-behaved iterations crawl
        # (lambda_min after ~10 iterations)
        if len(self.x) > self.n_ini_relax and self.residual is not None:
            if residual * self._last_residual < 0 or abs(residual) > self.residual:
                self.lambda_i = max(self.lambda_min, self.lambda_i * self.rel_vel)
            else:
                self.lambda_i = min(self.lambda_max, self.lambda_i / self.rel_vel)
        self._last_residual = residual
        self.residual = abs(residual)

        self.x.append(x_next)
        return x_next
    
    def set_next_x(self, next_x):
        """Set the next value directly, without relaxation

        Args:
            next_x (float): next value
        """
        self.x.append(next_x)

