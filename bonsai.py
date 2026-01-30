import turtle
import random
import math
import time
import pygame
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
trunk_base= 0
trunk_height=0
x=0
y=0
angle=0
thickness=0
growth_scale=1.4
MIN_GROWTH=0
MAX_GROWTH=1.4
ui_pen=0
BUTTON_Y= SCREEN_HEIGHT//2-100
BUTTON_WIDTH=90
BUTTON_HEIGHT=30

BACKGROUND_COLOR = '#e8f4f8'
TRUNK_COLOR = '#4a2511'
BRANCH_ANGLE = 25
BRANCH_LENGTH = 170
MIN_BRANCH_LENGTH = 8
BRANCH_REDUCTION = 0.7

GRAVITY = 0.15
WIND_STRENGTH = 2.0
WIND_VARIATION = 0.025
FPS = 60
SEASONS=["AUTUMN", "SPRING", "SUMMER", "WINTER"]
season_index=0
season=SEASONS(season_index)
screen = turtle.Screen()
screen.setup(SCREEN_WIDTH, SCREEN_HEIGHT)
screen.title("digital bonsai using python")
screen.bgcolor(BACKGROUND_COLOR)
screen.tracer(0)

def draw_button(x,y,label):
        ui_pen.up()
        ui_pen.goto(x-BUTTON_WIDTH//2, y-BUTTON_HEIGHT//2)
        ui_pen.down()
        ui_pen.fillcolor("#dfe6e9")
        ui_pen.begin_fill("#2d3436")
        for i in range (2):
         ui_pen.forward(BUTTON_WIDTH), 

        ui_pen.left(90)
        ui_pen.forward(BUTTON_HEIGHT)
        ui_pen.left(90)

        ui_pen.endfill()
        ui_pen.up()
        ui_pen.goto(x, y-10)
        ui_pen.color("#2d3436")
        ui_pen.write(label, align="center", font=("Arial", 10, "bold" ))


def prune_tree():
      global growth_scale
      growth_scale= min(MAX_GROWTH, growth_scale-1.0)
prune_tree()


def regrow_tree():
         global growth_scale
         growth_scale= max(MIN_GROWTH, growth_scale+1.0)
regrow_tree()

def reset_tree():
         global growth_scale
         growth_scale=1.0
reset_tree()
  
    
def handle_click (x,y):

      if BUTTON_Y - 15 <y<BUTTON_Y+15:
          if 175<x<265:
              prune_tree()
          elif 275<x<365:
              regrow_tree()
          elif 375<x<465: 
              reset_tree()  

def rgb_to_hex(r, g, b):
    return '#%02x%02x%02x' % (r, g, b)
tree_pen = turtle.Turtle()
tree_pen.hideturtle()
tree_pen.speed(0)

canopy_points = []


def draw_trunk():
    x = 0
    y = -SCREEN_HEIGHT // 2 + 40
    angle = 90

    tree_pen.pensize(12)
    tree_pen.pencolor(TRUNK_COLOR)
    tree_pen.up()
    tree_pen.goto(x, y)
    tree_pen.down()

    for i in range(8):
        angle += random.uniform(-8, 8)   # gentle curve
        length = 15
        x += length * math.cos(math.radians(angle))
        y += length * math.sin(math.radians(angle))
        tree_pen.goto(x, y)

    return x, y, angle


def draw_branch(x, y, angle, length, thickness):
    growth_factor = 0.0
    length *= growth_scale

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

    angle_variation = random.uniform(-5, 5)

    draw_branch(end_x, end_y, angle + BRANCH_ANGLE + angle_variation,
                new_length, new_thickness)
    angle_variation = random.uniform(-5, 5)

    draw_branch(end_x, end_y, angle - BRANCH_ANGLE + angle_variation,
                new_length, new_thickness)

    if random.random() < 0.3 and length > 30:
        angle_variation = random.uniform(-15, 15)
        draw_branch(end_x, end_y, angle + angle_variation,
                    new_length * 0.8, new_thickness)
        
def draw_pot():
    pot = turtle.Turtle()
    pot.hideturtle()
    pot.speed(0)

    base_y = -SCREEN_HEIGHT // 2 + 90

    pot.up()
    pot.goto(-80, base_y)
    pot.down()
    pot.fillcolor('#6d4c41')
    pot.begin_fill()
    pot.goto(80, base_y)
    pot.goto(60, base_y - 40)
    pot.goto(-60, base_y - 40)
    pot.goto(-80, base_y)
    pot.end_fill()


def draw_tree():
    trunk_base_y = -SCREEN_HEIGHT // 2 + 100
    trunk_height = 100

    tree_pen.pensize(15)
    tree_pen.pencolor(TRUNK_COLOR)
    tree_pen.up()
    tree_pen.goto(0, trunk_base_y)
    tree_pen.down()
    tree_pen.goto(0, trunk_base_y + trunk_height)
    for spread in [-35, -10, 15]:
        draw_branch(0, trunk_base_y+trunk_height, 90+spread, BRANCH_LENGTH, 10)
def draw_ui():
 draw_button(220, BUTTON_Y, "PRUNE")
 draw_button(320, BUTTON_Y, "GROW")
 draw_button(420, BUTTON_Y, "RESET")
draw_ui()
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
            self.x = cx + random.uniform(-20, 20)
            self.y = cy + random.uniform(-10, 10)

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
        ui_pen=turtle.Turtle()
        ui_pen.hide_turtle()
        ui_pen.speed(0)
    def redraw_tree():
        global canopy_points, leaves 
        tree_pen.clear()
        static_leaf_pen.clear()
        falling_leaf_pen.clear()
        draw_ground()
        draw_tree()
        for leaf in leaves:
            if leaf.is_static:
             leaf.draw(static_leaf_pen)
            screen.update()

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
