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

        
    def converged(self):
        if len(self.x) == 1:
            return False
        else:
            if abs(self.x[-1]-self.x[-2]) < self.tol:
                return True
            else:
                return False

    def estimate_next_x(self, proposed_x):
        x_next = (1 - self.lambda_i) * self.x[-1] + self.lambda_i * proposed_x
        
        # Ajuste dinámico de lambda (reduce si hay oscilaciones)
        if len(self.x)>self.n_ini_relax:
            #if abs(x_next - self.x[-1]) > abs(self.x[-1]- self.x[-2]):
                self.lambda_i = max(self.lambda_min, self.lambda_i * self.rel_vel)  # Reducimos lambda
            #else:
                #self.lambda_i = min(self.lambda_max, self.lambda_i * 1/self.rel_vel)  # Aumentamos lambda

        self.x.append(x_next)
        return x_next
    
    def set_next_x(self, next_x):
        self.x.append(next_x)

