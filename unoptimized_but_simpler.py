# Unoptimized, but simpler code
# Uses a brute-force method for collision resolution: O(n^2) running time (quadratic growth in run time for every new ball created: problematic in large numbers without optimization)
# Works well with few balls, not in large quantities.

# modules
import pygame
from pygame.locals import *
import sys, math, random
from utils import Vector

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

font = pygame.font.Font(None, 30)

# GridLine class: creating and updating a GridLine object will render a grid onto the display.
class GridLine:
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
            pygame.draw.line(display, (100,100,100), (x_pos, 0), (x_pos, display.get_height()))

        # horizontal lines: y = m * unit_length
        horizontal_start = math.floor(view_top/self.unit_length)
        horizontal_end = math.ceil(view_bottom/self.unit_length)
        for i in range(horizontal_start, horizontal_end):
            y_pos = i*self.unit_length - Player.scroll[1]
            # draw only if within display bounds
            pygame.draw.line(display, (100,100,100), (0, y_pos), (display.get_width(), y_pos))

# PhysicsBody class: a ball. Balls can vary in radius, mass, color, and have collision response.
class PhysicsBody:
    bodies = []
    template_radius = 0
    count = 0

    # variables to manipulate to alter ball interaction
    # all ideally between 0 and 1, but feel free to experiment around with these.
    friction = 0.1
    # 0 =< restitution < 1: inelastic; restitution = 1: elastic: restitution > 1: superelastic
    restitution = 0.7 # we set an initial resitution because we want to have control over the speed of balls after collisions, and thus "bounciness".
    repel_speed_percentage = 0.1
    ##

    def collided(b1, b2):
        if(b1.r + b2.r >= b2.pos.subtract(b1.pos).magnitude()):
            return True
        return False
    
    # on collision, calculates the distance that each ball in a pair need to repel based on the ratio of their masses
    def repel(b1, b2):
        # avoid self-collision
        if b1 == b2: return

        # calculate collision normal and depth
        distance = b1.pos.subtract(b2.pos)
        collision_normal = distance.unit()
        depth = b1.r + b2.r - distance.magnitude()

        # Separate the balls based on mass ratio to prevent overlap
        mass_ratio = b1.mass/(b1.mass+b2.mass)
        dpos1 = collision_normal.multiply(depth*(1-mass_ratio)).multiply(PhysicsBody.repel_speed_percentage)
        dpos2 = collision_normal.multiply(depth*(mass_ratio)).multiply(-1).multiply(PhysicsBody.repel_speed_percentage)
        b1.pos = b1.pos.add(dpos1)
        b2.pos = b2.pos.add(dpos2)

        # Calculate relative velocity
        relative_velocity = b1.velocity.subtract(b2.velocity)
        # Calculate velocity along normal - dot product, relative_velocity dot collision_normal
        velocity_along_normal = (relative_velocity.x*collision_normal.x+relative_velocity.y*collision_normal.y)
        # Don't process collision if objects are moving apart
        if velocity_along_normal > 0: return
        # Calculate impulse scalar
        j = -(1 + PhysicsBody.restitution) * velocity_along_normal / (1/b1.mass + 1/b2.mass)
        # Apply impulse
        impulse = collision_normal.multiply(j)
        b1.velocity = b1.velocity.add(impulse.multiply(1/b1.mass))
        b2.velocity = b2.velocity.add(impulse.multiply(-1/b2.mass))

    def __init__(self, pos ,r, color):
        self.pos = Vector(pos[0],pos[1])
        self.r = r
        self.mass = self.r**(5/4) # r**3 is too imbalanced, raise to 5/4. (4/3)*math.pi is just a constant.
        self.color = color
        
        #self.displacement = Vector(0,0)
        self.velocity = Vector(0,0)

        PhysicsBody.count += 1

    def render(self):
        pygame.draw.circle(display, self.color, (self.pos.x-Player.scroll[0], self.pos.y-Player.scroll[1]), self.r)
        self.velocity.draw_vector(display, self.pos.x-Player.scroll[0], self.pos.y-Player.scroll[1], 10, (255,255,255))

    def update(self):
        # Apply friction to velocity
        if self.velocity.magnitude() > 0:
            friction_force = self.velocity.multiply(-1*PhysicsBody.friction)
            self.velocity = self.velocity.add(friction_force)
            
            # Stop if very slow
            if self.velocity.magnitude() < 0.1:
                self.velocity = Vector(0, 0)
        
        # Update position based on velocity
        self.pos = self.pos.add(self.velocity)

# Player class: control a red ball (PhysicsBody) with WASD or arrow keys. Camera scrolling included.
class Player:
    players = []
    # range from 0 to 1
    scroll = [0,0]
    def __init__(self, pos,r ,color):
        self.x = pos[0]
        self.y = pos[1]
        self.r = r
        self.color = color

        self.direction = {'up': False, 'left': False, 'down': False, 'right': False}
        self.movement = Vector(0,0)
        self.speed = 1

        self.ball = PhysicsBody((self.x, self.y), self.r, self.color)
        PhysicsBody.bodies.append(self.ball)

    def update(self):
        # Create movement vector based on input
        self.movement = Vector(0,0)
        if self.direction['left']: self.movement.x -= self.speed
        if self.direction['right']: self.movement.x += self.speed
        if self.direction['up']: self.movement.y -= self.speed
        if self.direction['down']: self.movement.y += self.speed

        # Apply movement force to velocity
        if self.movement.magnitude() > 0:
            self.movement = self.movement.unit().multiply(self.speed)
        self.ball.velocity = self.ball.velocity.add(self.movement).multiply(1-PhysicsBody.friction)

        self.movement.draw_vector(display, self.ball.pos.x-self.scroll[0], self.ball.pos.y-self.scroll[1], self.r, (0,0,0))

        # Update the ball's physics - done in main game loop
        #self.ball.update()

# create entities on load
gridlines = GridLine(100)
player = Player((150,150),25,(255,0,0))
Player.players.append(player)

PhysicsBody.bodies.append(PhysicsBody((0,0),10,(100,100,200)))
PhysicsBody.bodies.append(PhysicsBody((35,0),25,(0,150,255)))
PhysicsBody.bodies.append(PhysicsBody((110,0),50,(255,0,255)))
PhysicsBody.bodies.append(PhysicsBody((260,0),100,(100,255,100)))
PhysicsBody.bodies.append(PhysicsBody((485,0),125,(215,200,255)))

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
                if (PhysicsBody.template_radius > 0.1):
                    PhysicsBody.bodies.append(PhysicsBody(
                        (mouse_coords[0]+Player.scroll[0], mouse_coords[1]+Player.scroll[1]),
                        PhysicsBody.template_radius,
                        #(215,200,255)
                        tuple(random.randint(0, 255) for i in range(3))
                    ))
                PhysicsBody.template_radius = 0
                charging = False
    
    # update and rendering
    display.fill((0,0,0))
    gridlines.draw_grid()
    pygame.draw.circle(display, (255,0,0), (0-Player.scroll[0],0-Player.scroll[1]), 5)
        
    for body in PhysicsBody.bodies:
        body.update()
        for i in range(len(PhysicsBody.bodies)):
            if (PhysicsBody.collided(body,PhysicsBody.bodies[i])):
                PhysicsBody.repel(body, PhysicsBody.bodies[i])
    for body in PhysicsBody.bodies:
        body.render()
    for player in Player.players:
        player.update()

    # draw an expanding "blueprint" of a ball when charging (holding down mouse button)
    if charging:
        PhysicsBody.template_radius += 2
        pygame.draw.circle(display, (255,255,255), mouse_coords, PhysicsBody.template_radius, 2)
    
    # display ball count
# display ball count
    display.blit(font.render(f"balls: {PhysicsBody.count}", True, (255, 255, 255)), (0,0))
    display.blit(font.render(f"fps: {int(clock.get_fps())}", True, (255, 255, 255)), (0,20))
    #pygame.draw.circle(display, (255,0,0), (mouse_coords[0],mouse_coords[1]), 5)

    # scale and blit display onto screen
    scaled = pygame.transform.scale(display, screen.get_size())
    screen.blit(scaled, (0, 0))
    #screen.blit(display, (0,0))
    pygame.display.update()
    clock.tick(60)