# modules
import pygame
from pygame.locals import *
import sys, math, random

#initialize
pygame.init()
clock = pygame.time.Clock()
pygame.display.set_caption("pygame 2D ball physics")

# screen dimensions/aspect ratios
display_info = pygame.display.Info()
display_width = display_info.current_w
display_height = display_info.current_h
aspect_ratio = display_width / display_height

# internal game resolution
display_mode = (int(aspect_ratio * 392), 392)
display = pygame.Surface(display_mode)

# actual screen window
screen_mode = (int(aspect_ratio * display_height / 2), int(display_height / 2))
screen = pygame.display.set_mode(screen_mode, pygame.RESIZABLE)

font = pygame.font.Font(None, 40)

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
    def draw_vector(self, surf, x, y, n, color):
        pygame.draw.line(surf, color, (x,y), (x + self.x*n, y + self.y*n), 2)

# Grid class: creating and updating a Grid object will render a grid onto the display.
class Grid:
    def __init__(self, unit_length):
        self.unit_length = unit_length

    def draw_grid(self):
        # Visible world bounds (left, top, right, bottom)
        view_left = Player.scroll[0]
        view_right = Player.scroll[0] + display.get_width()
        
        view_top = Player.scroll[1]
        view_bottom = Player.scroll[1] + display.get_height()

        # integer ranges of grid lines
        # vertical lines: x = k * unit_length
        vertical_start = math.floor(view_left/self.unit_length)
        vertical_end = math.ceil(view_right/self.unit_length)
        for i in range(vertical_start, vertical_end):
            x_pos = i*self.unit_length - Player.scroll[0]
            # draw only if within display bounds
            pygame.draw.line(display, (255,255,255), (x_pos, 0), (x_pos, display.get_height()))

        # horizontal lines: y = m * unit_length
        horizontal_start = math.floor(view_top/self.unit_length)
        horizontal_end = math.ceil(view_bottom/self.unit_length)
        for i in range(horizontal_start, horizontal_end):
            y_pos = i*self.unit_length - Player.scroll[1]
            # draw only if within display bounds
            pygame.draw.line(display, (255,255,255), (0, y_pos), (display.get_width(), y_pos))

# PhysicsBody class: a ball. Balls can vary in radius, mass, color, and have collision response.
class PhysicsBody:
    bodies = []
    template_radius = 0
    count = 0
    def collided(b1, b2):
        if(b1.r + b2.r >= b2.pos.subtract(b1.pos).magnitude()):
            return True
        return False
    
    # on collision, calculates the distance that each ball in a pair need to repel based on the ratio of their masses
    def repel(b1, b2):
        distance = b1.pos.subtract(b2.pos)
        depth = b1.r + b2.r - distance.magnitude() # negative value

        mass_ratio = b1.mass/(b1.mass+b2.mass)
        dpos1 = distance.unit().multiply(depth*(1-mass_ratio))
        dpos2 = distance.unit().multiply(depth*(mass_ratio)).multiply(-1) # repel in opposite direction
        # move the balls apart
        b1.pos = b1.pos.add(dpos1)        # try swapping the .multiply(-1) for funny
        b2.pos = b2.pos.add(dpos2)

    def __init__(self, x,y,r, color):
        self.pos = Vector(x,y)
        self.r = r
        self.mass = self.r**(5/4) # r**3 is too imbalanced, raise to 5/4. (4/3)*math.pi is just a constant.
        self.color = color
        
        self.displacement = Vector(0,0)
        self.velocity = Vector(0,0)

        PhysicsBody.count += 1

    def render(self):
        pygame.draw.circle(display, self.color, (self.pos.x-Player.scroll[0], self.pos.y-Player.scroll[1]), self.r)
        self.velocity.draw_vector(display, self.pos.x-Player.scroll[0], self.pos.y-Player.scroll[1], 30, (0,0,0))
        self.displacement.draw_vector(display, self.pos.x-Player.scroll[0], self.pos.y-Player.scroll[1], 10, (255,255,255))

# Player class: control a red ball (PhysicsBody) with WASD or arrow keys. Camera scrolling included.
class Player:
    players = []
    friction = 0.15
    scroll = [0,0]
    def __init__(self, x,y,r,color):
        self.x = x
        self.y = y
        self.r = r
        self.color = color

        self.direction = {'up': False, 'left': False, 'down': False, 'right': False}
        self.speed = 1

        self.ball = PhysicsBody(self.x, self.y, self.r, self.color)
        PhysicsBody.bodies.append(self.ball)

    def update(self):
        self.ball.velocity = Vector(0,0)
        if(self.direction['left']):self.ball.velocity.x = -self.speed
        if(self.direction['up']):self.ball.velocity.y = -self.speed
        if(self.direction['right']):self.ball.velocity.x = self.speed
        if(self.direction['down']):self.ball.velocity.y = self.speed
        
        self.ball.velocity=self.ball.velocity.unit().multiply(self.speed) # velocity magnitude: speed
        self.ball.displacement=self.ball.displacement.add(self.ball.velocity) # add velocity to displacement, displacement is what you see moves the ball position (line after next line)
        self.ball.displacement=self.ball.displacement.multiply(1-Player.friction) # add friction to stop infinite acceleration
        self.ball.pos=self.ball.pos.add(self.ball.displacement) # add displacement to pos

# create entities on load
grid = Grid(40)
player = Player(100,100,25,(255,0,0))
Player.players.append(player)

PhysicsBody.bodies.append(PhysicsBody(100,200,50,(0,150,255)))
PhysicsBody.bodies.append(PhysicsBody(300,200,75,(255,0,255)))
PhysicsBody.bodies.append(PhysicsBody(500,200,100,(100,255,100)))

# 
charging = False
# loop
while True:
    # handling mouse position
    # mouse positions according to changing display dimensions
    window_width, window_height = pygame.display.get_window_size()
    screen_display_ratio_x = display.get_width()/window_width
    screen_display_ratio_y = display.get_height()/window_height
            
    mouse_pos = pygame.mouse.get_pos()
    mouse_coords = list(mouse_pos)
            
    # mouse coords is coordinates on resized display (scaled "pixels"), mouse pos is coordinates on screen relative to (0,0) (top left pygame window)
    mouse_coords[0] *= screen_display_ratio_x
    mouse_coords[1] *= screen_display_ratio_y

    # toggle scroll on/off
    Player.scroll[0] += (player.ball.pos.x-display.get_width()/2-Player.scroll[0])/10
    Player.scroll[1] += (player.ball.pos.y-display.get_height()/2-Player.scroll[1])/10

    # eventhandler
    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
        if event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                pygame.quit()
                sys.exit()
            if event.key == K_w or event.key == K_UP:
                Player.players[0].direction['up'] = True
            if event.key == K_a or event.key == K_LEFT:
                Player.players[0].direction['left'] = True
            if event.key == K_s or event.key == K_DOWN:
                Player.players[0].direction['down'] = True
            if event.key == K_d or event.key == K_RIGHT:
                Player.players[0].direction['right'] = True
                
        if event.type == KEYUP:
            if event.key == K_w or event.key == K_UP:
                Player.players[0].direction['up'] = False
            if event.key == K_a or event.key == K_LEFT:
                Player.players[0].direction['left'] = False
            if event.key == K_s or event.key == K_DOWN:
                Player.players[0].direction['down'] = False
            if event.key == K_d or event.key == K_RIGHT:
                Player.players[0].direction['right'] = False
            # clear all non-player balls
            if event.key == K_c:
                PhysicsBody.bodies = [player.ball]
                PhysicsBody.count=1

        if event.type == MOUSEBUTTONDOWN:
            if event.button == 1:
                charging = True

        if event.type == MOUSEBUTTONUP:
            if event.button == 1:
                PhysicsBody.bodies.append(PhysicsBody(mouse_coords[0]+Player.scroll[0], mouse_coords[1]+Player.scroll[1],PhysicsBody.template_radius,tuple(random.randint(0, 255) for i in range(3))))
                PhysicsBody.template_radius = 0
                charging = False
    
    # update and rendering
    display.fill((0,0,0))
    grid.draw_grid()
    pygame.draw.circle(display, (255,0,0), (0-Player.scroll[0],0-Player.scroll[1]), 5)

    for player in Player.players:
        player.update()
        
    for body in PhysicsBody.bodies:
        body.render()
        
        for i in range(len(PhysicsBody.bodies)):
            if (PhysicsBody.collided(body,PhysicsBody.bodies[i])):
                PhysicsBody.repel(body, PhysicsBody.bodies[i])

    # draw an expanding "blueprint" of a ball when charging (holding down mouse button)
    if charging:
        PhysicsBody.template_radius += 2
        pygame.draw.circle(display, (255,255,255), mouse_coords, PhysicsBody.template_radius, 2)
    
    # display ball count
    display.blit(font.render(f"balls: {PhysicsBody.count}", True, (255, 255, 255)), (0,0))
    #pygame.draw.circle(display, (255,0,0), (mouse_coords[0],mouse_coords[1]), 5)

    # scale and blit display onto screen
    scaled = pygame.transform.scale(display, screen.get_size())
    screen.blit(scaled, (0, 0))
    #screen.blit(display, (0,0))
    pygame.display.update()
    clock.tick(60)