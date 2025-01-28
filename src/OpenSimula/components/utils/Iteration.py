class Iteration():
    def __init__(self,x_0, y_0, x_max, x_min, y_tol):
        self.x = [x_0]
        self.y = [y_0]
        self.x_max = x_max
        self.x_min = x_min
        self.y_tol = y_tol

    def add_point(self,x ,y):
        self.x.append(x)
        self.y.append(y)
               
    def next_x(self):
        n = len (self.x)
        if n == 1:
            next_x = self.x[0]*1.1
        elif n== 2:
            next_x =  (self.x[1]-self.x[0])*0.1 +self.x[1]
        else:
            D_y1 = (self.y[-2]-self.y[-3])/(self.x[-2]-self.x[-3])
            D_y2 = (self.y[-1]-self.y[-2])/(self.x[-1]-self.x[-2])
            if abs(D_y2) < self.y_tol:
                next_x = self.x[-1]
            if D_y1 == D_y2:
                next_x (self.x[-2]-self.x[-1])*0.1 +self.x[-1]
            else:
                next_x = (D_y1 * self.x[-2] - D_y2 * self.x[-3])/(D_y1-D_y2)
        if next_x > self.x_max:
            next_x = self.x_max
        if next_x < self.x_min:
            next_x = self.x_min
        return next_x