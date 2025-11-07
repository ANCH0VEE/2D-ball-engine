import pygame
import math

# Vector class: 2-dimensional. vector operations
class Vector:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def add(self, v):
        return Vector(self.x+v.x, self.y+v.y)
    def subtract(self, v):
        return Vector(self.x-v.x, self.y-v.y)
    def multiply(self, n):
        return Vector(self.x*n, self.y*n)
    def magnitude(self):
            return math.sqrt(self.x**2 + self.y**2)
    def unit(self):
        # avoid division by zero
        if(self.magnitude() == 0):
            return Vector(0,0)
        else:
            return Vector(self.x/self.magnitude(), self.y/self.magnitude())
    def draw_vector(self, surf, xpos, ypos, n, color):
        pygame.draw.line(surf, color, (xpos,ypos), (xpos + self.x*n, ypos + self.y*n), 2)