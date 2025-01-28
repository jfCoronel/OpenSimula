from OpenSimula.components.utils.Iteration import Iteration

def func(x): 
    return (x-10)**2 + 5


iter = Iteration(0,func(0),1000, -1000, 0.0001)

iter.add_point(1,func(1))
for i in range(10):
    n_x = iter.next_x()
    iter.add_point(n_x,func(n_x))

