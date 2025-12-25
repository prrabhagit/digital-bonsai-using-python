# digital-bonsai-using-python
import turtle
import random
import math
import time

SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
BACKGROUND_COLOR = '#e8f4f8'  # Light sky blue

TRUNK_COLOR ='#4a2511'
BRANCH_ANGLE = 25
BRANCH_LENGTH = 120
MIN_BRANCH_LENGTH = 10
BRANCH_REDUCTION = 0.7

GRAVITY = 0.15
WIND_STRENGTH = 2.0
WIND_VARIATION = 0.025

FPS = 60
screen = turtle.Screen()
screen.setup(SCREEN_WIDTH, SCREEN_HEIGHT)
screen.title("Banyan")
screen.bgcolor(BACKGROUND_COLOR)
screen.tracer(0)

def rgb_to_hex(r, g, b):
    
    return '#%02x%02x%02x' % (r, g, b)

tree_pen = turtle.Turtle()
tree_pen.hideturtle()
tree_pen.speed(0)

canopy_points = []
tree_pen.speed(0)

canopy_points = []
def draw_branch(x, y, angle, length, thickness):
    
    if length < MIN_BRANCH_LENGTH:
        
        canopy_points.append((x, y))
        return
    
    
    end_x = x + length * math.cos(math.radians(angle))
    end_y = y + length * math.sin(math.radians(angle))
    
    
    tree_pen.pensize(thickness)
    tree_pen.pencolor(TRUNK_COLOR)
    tree_pen.up()
    tree_pen.goto(x, y)
    tree_pen.down()
    tree_pen.goto(end_x, end_y)
    
    
    new_length = length * BRANCH_REDUCTION
    new_thickness = max(1, thickness - 0.5)
    
    
