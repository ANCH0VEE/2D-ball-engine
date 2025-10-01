import pygame
from pygame.locals import *
import sys, math, random

pygame.init()
clock = pygame.time.Clock()
pygame.display.set_caption("pygame circle physics")

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
        if(self.magnitude() == 0):
            return Vector(0,0)
        else:
            return Vector(self.x/self.magnitude(), self.y/self.magnitude())
    def draw_vector(self, surf, x, y, n, color):
        pygame.draw.line(surf, color, (x,y), (x + self.x*n, y + self.y*n), 2)

class Grid:
    def __init__(self):
        pass

    def draw_grid(self):
        unit_length = 40

        # Visible world bounds (left, top, right, bottom)
        view_left = Player.scroll[0]
        view_right = Player.scroll[0] + display.get_width()
        
        view_top = Player.scroll[1]
        view_bottom = Player.scroll[1] + display.get_height()

        # integer ranges of grid lines
        # vertical lines: x = k * unit_length
        vertical_start = math.floor(view_left / unit_length)
        vertical_end = math.ceil(view_right / unit_length)

        for i in range(vertical_start, vertical_end + 1):
            x_pos = i*unit_length - Player.scroll[0]
            # draw only if within screen bounds
            if -1 <= x_pos <= display.get_width() + 1:
                pygame.draw.line(display, (255,255,255), (x_pos, 0), (x_pos, display.get_height()))

        # horizontal lines: y = m * unit_length
        horizontal_start = math.floor(view_top / unit_length)
        horizontal_end = math.ceil(view_bottom / unit_length)

        for i in range(horizontal_start, horizontal_end + 1):
            y_pos = i*unit_length - Player.scroll[1]
            if -1 <= y_pos <= display.get_height() + 1:
                pygame.draw.line(display, (255,255,255), (0, y_pos), (display.get_width(), y_pos))

class PhysicsBody:
    bodies = []
    template_radius = 0
    count = 0
    def collided(b1, b2):
        if(b1.r + b2.r >= b2.pos.subtract(b1.pos).magnitude()):
            return True
        return False
    
    def repel(b1, b2):
        distance = b1.pos.subtract(b2.pos)
        depth = b1.r + b2.r - distance.magnitude() # negative value

        mass_ratio = b1.mass/(b1.mass+b2.mass)
        displacement1 = distance.unit().multiply(depth*(1-mass_ratio)) # each ball separates by this amount in opposite directions (which is why the second ball's code has a multiply(-1).)
        displacement2 = distance.unit().multiply(depth*(mass_ratio))
        # move the balls apart
        b1.pos = b1.pos.add(displacement1)        # try swapping the .multiply(-1) for funny
        b2.pos = b2.pos.add(displacement2.multiply(-1))

    def __init__(self, x,y,r, color):
        self.pos = Vector(x,y)
        self.r = r
        self.mass = self.r**(5/4) # r**3 is too imbalanced. (4/3)*math.pi is just a constant.
        self.color = color
        
        self.vel = Vector(0,0)
        self.acc = Vector(0,0)

        PhysicsBody.count += 1
        
    def render(self):
        pygame.draw.circle(display, self.color, (self.pos.x-Player.scroll[0], self.pos.y-Player.scroll[1]), self.r)
        self.acc.draw_vector(display, self.pos.x-Player.scroll[0], self.pos.y-Player.scroll[1], 30, (0,0,0))
        self.vel.draw_vector(display, self.pos.x-Player.scroll[0], self.pos.y-Player.scroll[1], 10, (255,255,255))

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
        self.ball.acc = Vector(0,0)
        if(self.direction['left']):self.ball.acc.x = -self.speed
        if(self.direction['up']):self.ball.acc.y = -self.speed
        if(self.direction['right']):self.ball.acc.x = self.speed
        if(self.direction['down']):self.ball.acc.y = self.speed
        
        self.ball.acc=self.ball.acc.unit().multiply(self.speed)
        self.ball.vel=self.ball.vel.add(self.ball.acc) # add acc to vel, vel is what you see moves the ball position (line after next line)
        self.ball.vel=self.ball.vel.multiply(1-Player.friction) # add friction to stop infinite acceleration
        self.ball.pos=self.ball.pos.add(self.ball.vel) # add vel to pos

grid = Grid()
player = Player(100,100,25,(255,0,0))
Player.players.append(player)

PhysicsBody.bodies.append(PhysicsBody(100,200,50,(0,150,255)))
PhysicsBody.bodies.append(PhysicsBody(300,200,75,(255,0,255)))
PhysicsBody.bodies.append(PhysicsBody(500,200,100,(100,255,100)))

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
            
    # mouse coords is coordinates on game pixel dimensions on display, mouse pos is coordinates on screen relative to (0,0)
    mouse_coords[0] *= screen_display_ratio_x
    mouse_coords[1] *= screen_display_ratio_y
    pygame.draw.circle(display, (255,0,0), (mouse_coords[0],mouse_coords[1]), 5)

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

        if event.type == MOUSEBUTTONDOWN:
            if event.button == 1:
                charging = True

        if event.type == MOUSEBUTTONUP:
            if event.button == 1:
                PhysicsBody.bodies.append(PhysicsBody(mouse_coords[0]+Player.scroll[0], mouse_coords[1]+Player.scroll[1],PhysicsBody.template_radius,tuple(random.randint(0, 255) for i in range(3))))
                PhysicsBody.template_radius = 0
                charging = False
    
    # updates
    display.fill((0,0,0))
    grid.draw_grid()
    pygame.draw.circle(display, (255,0,0), (0-Player.scroll[0],0-Player.scroll[1]), 5)

    Player.scroll[0] += (player.ball.pos.x-display.get_width()/2-Player.scroll[0])/10
    Player.scroll[1] += (player.ball.pos.y-display.get_height()/2-Player.scroll[1])/10

    for player in Player.players:
        player.update()
        
    for body in PhysicsBody.bodies:
        body.render()
        
        for i in range(len(PhysicsBody.bodies)):
            if (PhysicsBody.collided(body,PhysicsBody.bodies[i])):
                PhysicsBody.repel(body, PhysicsBody.bodies[i])

    if charging:
        PhysicsBody.template_radius += 2
        pygame.draw.circle(display, (255,255,255), mouse_coords, PhysicsBody.template_radius, 2)

    
    display.blit(font.render(f"balls: {PhysicsBody.count}", True, (255, 255, 255)), (0,0))

    # Update ------------------------------------------------- #
    # scale and blit display onto screen
    scaled = pygame.transform.scale(display, screen.get_size())
    screen.blit(scaled, (0, 0))
    pygame.display.update()
    clock.tick(60)