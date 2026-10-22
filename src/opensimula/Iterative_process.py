import math

class Iterative_process:
    def __init__(self, x_0, tol = 1e-5, lambda_min=0.1, lambda_max=1.0, n_ini_relax=2,rel_vel = 0.9):
        """
        Iterative process using the fixed-point method with adaptive relaxation coefficient
    
        Parameters:
        x_0: Initial value
        tol: convergence tolerance
        lambda_min, lambda_max: relaxation coefficient range
        n_ini_relax: Number of iterations in which adaptive relaxation is initiated, must be greater than 1
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
        # Fixed-point residual, not the relaxed step: with relaxation lambda the step is only
        # lambda * residual, so testing the step stopped with residuals up to tol / lambda_min
        # (10 x tol), e.g. zones far from their moisture balance in steady state
        return self.residual is not None and self.residual < self.tol

    def estimate_next_x(self, proposed_x):
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
        self.x.append(next_x)

