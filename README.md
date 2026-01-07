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
        angle_variation = random.uniform(-10, 10)
    draw_branch(end_x, end_y, angle + BRANCH_ANGLE + angle_variation, 
                new_length, new_thickness)
    
    
    angle_variation = random.uniform(-10, 10)
    draw_branch(end_x, end_y, angle - BRANCH_ANGLE + angle_variation, 
                new_length, new_thickness)
    
    
    if random.random() < 0.3 and length > 30:
        angle_variation = random.uniform(-15, 15)
        draw_branch(end_x, end_y, angle + angle_variation, 
                    new_length * 0.8, new_thickness)
    
def draw_tree():
    
    trunk_base_y = -SCREEN_HEIGHT // 2 + 100
    trunk_height = 100
    
    
    tree_pen.pensize(15)
    tree_pen.pencolor(TRUNK_COLOR)
    tree_pen.up()
    tree_pen.goto(0, trunk_base_y)
    tree_pen.down()
    tree_pen.goto(0, trunk_base_y + trunk_height)
    
    
    for spread in [-20, 0, 20]:
        draw_branch(0, trunk_base_y + trunk_height, 90 + spread, 
                    BRANCH_LENGTH, 10)

def draw_ground():
    
    ground_pen = turtle.Turtle()
    ground_pen.hideturtle()
    ground_pen.speed(0)

    
    ground_pen.up()
    ground_pen.goto(-SCREEN_WIDTH // 2, -SCREEN_HEIGHT // 2 + 100)
    ground_pen.down()
    ground_pen.pencolor('#2d5016')
    ground_pen.fillcolor('#4a7c2c')
    ground_pen.begin_fill()
    ground_pen.goto(SCREEN_WIDTH // 2, -SCREEN_HEIGHT // 2 + 100)
    ground_pen.goto(SCREEN_WIDTH // 2, -SCREEN_HEIGHT // 2)
    ground_pen.goto(-SCREEN_WIDTH // 2, -SCREEN_HEIGHT // 2)
    ground_pen.goto(-SCREEN_WIDTH // 2, -SCREEN_HEIGHT // 2 + 100)
    ground_pen.end_fill()
    
class Leaf:
    
    
    def __init__(self, is_static=True, color=None):
        
        self.is_static = is_static
        
        if canopy_points:
            cx, cy = random.choice(canopy_points)
            self.x = cx + random.uniform(-35, 35)
            self.y = cy + random.uniform(-25, 25)
        else:
            self.x = random.uniform(-200, 200)
            self.y = 200
                    self.vx = random.uniform(-0.5, 0.5)
        self.vy = 0
        self.rotation = random.uniform(0, 360)
        self.rotation_speed = random.uniform(-5, 5) if not is_static else 0
        self.size = random.uniform(8, 14)
                if color:
            self.color = color
        elif is_static:
            
            green_colors = [
                (34, 139, 34),    
                (50, 205, 50),    
                (46, 125, 50),    
                (76, 175, 80),    
            ]
            self.color = rgb_to_hex(*random.choice(green_colors))
        else:
            
            self.color = rgb_to_hex(205, 133, 63)
        
        self.on_ground = False
        
    def update(self, wind_force):
        if self.is_static or self.on_ground:
            return

        self.vx += wind_force * 0.02
        self.vx += random.uniform(-0.02, 0.02)

        self.vy -= GRAVITY

        self.vx *= 0.99
        self.vy *= 0.99
        
 self.x += self.vx
        self.y += self.vy
        self.rotation += self.rotation_speed

        ground_level = -SCREEN_HEIGHT // 2 + 100

            if self.y <= ground_level:
            self.y = ground_level + random.uniform(0, 5)
            self.on_ground = True
            self.vx = 0
            self.vy = 0
            self.rotation_speed = 0

            def draw(self, pen):
        pen.up()
        pen.goto(self.x, self.y)
        pen.setheading(self.rotation)
        pen.down()

        pen.fillcolor(self.color)
        pen.pencolor(self.color)
        pen.pensize(1)
        pen.begin_fill()

        for _ in range(2):
            pen.circle(self.size, 90)
            pen.circle(self.size / 3, 90)

        pen.end_fill()

    def is_off_screen(self):
        return (self.x < -SCREEN_WIDTH // 2 - 50 or
                self.x > SCREEN_WIDTH // 2 + 50)

draw_ground()
draw_tree()

leaves = []

    
    
