# A more optimized 2D ball engine
# 1. Filters out off-screen balls, so only on-screen ones are rendered.
# 2. Uses spatial hashing to reduce the brute-force O(n^2) running time of collision resolution (quadratic growth in run time for every new ball created: problematic in large numbers without optimization)
# Partitions map into grid cells of side length of largest ball's diameter
# Checks collisions normally, but with a smaller group that consists only of balls contained within neighboring grid cells.
# Better performance with larger ball quantities, especially when smaller and more spread out. Balls too large still cause significant increase in run-time.

# modules
import pygame
from pygame.locals import *
import sys, math, random
from utils import Vector

#initialize
pygame.init()
clock = pygame.time.Clock()
pygame.display.set_caption("2D ball engine")

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

# PhysicsBody class: a ball. Balls can vary in radius, mass, color, and have collision response.
class PhysicsBody:
    bodies = []
    template_radius = 0
    charging = False
    count = 0

    ## variables to manipulate types of ball interaction
    # all ideally between 0 and 1, but feel free to experiment around with these.
    friction = 0.05
    # restitution = 0: perfectly inelastic (not bouncy)
    # 0 < restitution < 1: inelastic (a bit bouncy)
    # restitution = 1: perfectly elastic (bouncy)
    # restitution > 1: superelastic (extreme bounciness)
    # restitution < 0: objects pass through each other
    restitution = 0.7 # we set an initial resitution because we want to have control over the speed of balls after collisions, and thus "bounciness".
    repel_speed_percentage = 0.1
    ##

    # collision detection: comparing distance between two balls to the sum of their radii
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

        # separate the balls based on mass ratio to prevent overlap
        mass_ratio = b1.mass/(b1.mass+b2.mass)
        dpos1 = collision_normal.multiply(depth*(1-mass_ratio)).multiply(PhysicsBody.repel_speed_percentage)
        dpos2 = collision_normal.multiply(depth*(mass_ratio)).multiply(-1).multiply(PhysicsBody.repel_speed_percentage)
        b1.pos = b1.pos.add(dpos1)
        b2.pos = b2.pos.add(dpos2)

        # calculate relative velocity: velocity relative to each other
        relative_velocity = b1.velocity.subtract(b2.velocity)
        # calculate velocity along normal "axis": dot product of relative_velocity and collision_normal
        velocity_along_normal = (relative_velocity.x*collision_normal.x+relative_velocity.y*collision_normal.y)
        # don't process collision if objects are moving apart (a positive velocity)
        if velocity_along_normal > 0: return

        # calculate impulse scalar
        j = -(1 + PhysicsBody.restitution) * velocity_along_normal / (1/b1.mass + 1/b2.mass)
        # apply impulse
        impulse = collision_normal.multiply(j)
        b1.velocity = b1.velocity.add(impulse.multiply(1/b1.mass))
        b2.velocity = b2.velocity.add(impulse.multiply(-1/b2.mass))

    # add new ball to PhysicsBody.bodies
    def add_new_ball(b):
        PhysicsBody.bodies.append(b)
        #PhysicsBody.template_radius = b.r # this adjusts grid for if balls are made in code, and not through mouse clicks
        if (2*b.r > SpatialPartitioner.largest):
            SpatialPartitioner.largest = 2*b.r
            sp.set_unit_length(SpatialPartitioner.largest)

    def __init__(self, pos, r, color):
        self.pos = Vector(pos[0],pos[1])
        self.r = r
        self.color = color

        # calculate grid position(s) after radius is set
        self.all_gridpos = self.recalculate_gridpos(SpatialPartitioner.largest)
        self.mass = self.r**(3/2) # r**3 or r**2 feels too imbalanced, raise to power of 3/2. (4/3)*math.pi is just a constant: omit.
        self.velocity = Vector(0,0)
        PhysicsBody.count += 1

    # draw both ball and velocity vector
    def render(self):
        pygame.draw.circle(display, self.color, (self.pos.x-Player.scroll[0], self.pos.y-Player.scroll[1]), self.r)
        self.velocity.draw_vector(display, self.pos.x-Player.scroll[0], self.pos.y-Player.scroll[1], 10, (255,255,255))

    # calculate the grid cells the ball overlaps
    def recalculate_gridpos(self, grid_size):
        # get the bounding box of the ball
        left = (self.pos.x - self.r)//grid_size
        right = (self.pos.x + self.r)//grid_size
        top = (self.pos.y - self.r)//grid_size
        bottom = (self.pos.y + self.r)//grid_size
        
        # generate all grid positions the ball overlaps
        grid_positions = []
        for x in range(int(left), int(right) + 1):
            for y in range(int(top), int(bottom) + 1):
                grid_positions.append((x, y))
        return grid_positions

    # apply friction to velocity
    def apply_friction(self):
        if self.velocity.magnitude() > 0:
            friction_force = self.velocity.multiply(-1*PhysicsBody.friction)
            self.velocity = self.velocity.add(friction_force)
            
            # stop if very slow
            if self.velocity.magnitude() < 0.1:
                self.velocity = Vector(0, 0)

    #  update method for movement
    def update(self):
        self.apply_friction()
        # update position based on velocity
        self.pos = self.pos.add(self.velocity)

# Player class: control a red ball (PhysicsBody) with WASD or arrow keys. Camera scrolling included.
class Player:
    radius = 25
    players = []
    scroll = [0,0]
    def __init__(self, pos, r,color):
        self.pos = Vector(pos[0],pos[1])
        self.r = r
        self.color = color

        self.direction = {'up': False, 'left': False, 'down': False, 'right': False}
        self.movement = Vector(0,0)
        self.speed = 1

        self.ball = PhysicsBody((self.pos.x, self.pos.y), self.r, self.color)
        PhysicsBody.bodies.append(self.ball)

    # main update method
    def update(self):
        # create movement vector based on input
        self.movement = Vector(0,0)
        if self.direction['left']: self.movement.x -= self.speed
        if self.direction['right']: self.movement.x += self.speed
        if self.direction['up']: self.movement.y -= self.speed
        if self.direction['down']: self.movement.y += self.speed

        # apply movement force to velocity
        if self.movement.magnitude() > 0:
            self.movement = self.movement.unit().multiply(self.speed)
        self.ball.velocity = self.ball.velocity.add(self.movement).multiply(1-PhysicsBody.friction)

        self.movement.draw_vector(display, self.ball.pos.x-self.scroll[0], self.ball.pos.y-self.scroll[1], self.r, (0,0,0))

# GridLine class: creating and updating a GridLine object will render a grid onto the display.
# displays grid positions created in by spatial partitioning.
class GridLine:
    def __init__(self, unit_length):
        self.unit_length = unit_length

    def set_unit_length(self, val):
        self.unit_length = val

    def draw_grid(self):
        # visible world bounds (left, top, right, bottom)
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

# SpatialPartitioner class: handles spatial hashing, grid size, and also onscreen rendering.
class SpatialPartitioner:
    # largest ball diameter will be the grid size
    largest = 2*Player.radius
    neighbor_offset = [(-1,-1), (0,-1), (1,-1),
                        (-1,0), (0,0), (1,0),
                        (-1,1), (0,1), (1,1)]
    def __init__(self):
        #(x,y): [balls]
        self.grid = {}
        self.gridlines = GridLine(self.largest)
        self.occupied_cells = set()

    # spatial hashing: clear the grid and re-insert every ball into the correct cells.
    def rehash_all_ball_gridpos(self):
        self.grid.clear()
        # add each ball to all grid cells it overlaps
        for b in PhysicsBody.bodies:
            # now gridpos is a list of all grid cells the ball overlaps
            grid_positions = b.recalculate_gridpos(SpatialPartitioner.largest)
            b.all_gridpos = grid_positions  # store all positions
            # add ball to all grid cells it overlaps
            for pos in grid_positions:
                self.grid.setdefault(pos, []).append(b)

    # given a ball and the grid dictionary, return a list of neighboring balls located in the 3x3 area around the ball's center cell.
    def filter_ball(self, ball, list):
        neighbors = []
        # coordinates of cell containing ball center
        center_x = int(ball.pos.x // SpatialPartitioner.largest)
        center_y = int(ball.pos.y // SpatialPartitioner.largest)
        
        # add cells the ball occupies to set
        for pos in ball.all_gridpos:
            self.occupied_cells.add(pos)
        
        # check the 3x3 area around the center cell
        for offset in SpatialPartitioner.neighbor_offset:
            check_x = center_x + offset[0]
            check_y = center_y + offset[1]
            check_loc = (check_x, check_y)
            
            if check_loc in list:
                # extend with the balls present in this cell
                neighbors.extend(list[check_loc])

        # remove self
        neighbors = [b for b in neighbors if b != ball]
        return neighbors

    # frustrum culling: using spatial partitioner's grid cells
    def filter_onscreen_tiles(self):
        onscreen_tiles = []
        # visible grid bounds
        left = int(Player.scroll[0] // self.largest)
        right = int((Player.scroll[0] + display.get_width()) // self.largest)
        top = int(Player.scroll[1] // self.largest)
        bottom = int((Player.scroll[1] + display.get_height()) // self.largest)

        for x in range(left, right + 1):
            for y in range(top, bottom + 1):
                if (x, y) in self.grid:
                    onscreen_tiles.extend(self.grid[(x, y)])
        return onscreen_tiles
    
    def set_unit_length(self, val):
        self.gridlines.unit_length = val
    
    def draw_grid(self):
        self.gridlines.draw_grid()

    def draw_occupied_cells(self):
        for pos in self.occupied_cells:
            pygame.draw.rect(display, (30,30,30), Rect(pos[0]*SpatialPartitioner.largest-Player.scroll[0]+1, pos[1]*SpatialPartitioner.largest-Player.scroll[1]+1, SpatialPartitioner.largest-2,SpatialPartitioner.largest-2))
        self.occupied_cells.clear()


# create entities on load
sp = SpatialPartitioner()
player = Player((0,50),Player.radius,(255,0,0))
Player.players.append(player)

PhysicsBody.add_new_ball(PhysicsBody((0,0),10,(100,100,200)))
PhysicsBody.add_new_ball(PhysicsBody((35,0),25,(0,150,255)))
PhysicsBody.add_new_ball(PhysicsBody((110,0),50,(255,0,255)))
PhysicsBody.add_new_ball(PhysicsBody((260,0),100,(100,255,100)))
PhysicsBody.add_new_ball(PhysicsBody((485,0),125,(215,200,255)))

#PhysicsBody.add_new_ball(PhysicsBody((-25,150),25,(215,200,255)))

# build initial grid hash
sp.rehash_all_ball_gridpos()

# main loop
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
            # clear all non-player balls: c
            if event.key == K_c:
                PhysicsBody.bodies = [player.ball]
                PhysicsBody.count=1
                SpatialPartitioner.largest = 2*player.r # player is the only ball that exists when you clear all
                sp.set_unit_length(SpatialPartitioner.largest)

        if event.type == MOUSEBUTTONDOWN:
            if event.button == 1:
                PhysicsBody.charging = True

        if event.type == MOUSEBUTTONUP:
            if event.button == 1:
                if (PhysicsBody.template_radius > 0.1):
                    new = PhysicsBody(
                        (mouse_coords[0]+Player.scroll[0], mouse_coords[1]+Player.scroll[1]),
                        PhysicsBody.template_radius,
                        tuple(random.randint(0, 255) for i in range(3))
                    )
                    PhysicsBody.add_new_ball(new)

                PhysicsBody.template_radius = 0
                PhysicsBody.charging = False
    
    # update and rendering
    display.fill((0,0,0))
    sp.draw_grid()
    sp.draw_occupied_cells()
        
    # update physics and check collisions only against neighboring cells
    for ball in PhysicsBody.bodies:
        ball.update()
        for other_ball in sp.filter_ball(ball, sp.grid):
            # avoid duplicate pair checks in separate iterations of loop: only handle each unordered pair once
            if id(ball) >= id(other_ball):
                continue
            if PhysicsBody.collided(ball, other_ball):
                PhysicsBody.repel(ball, other_ball)
                
    # render only onscreen balls
    for body in sp.filter_onscreen_tiles():
        body.render()

    for player in Player.players:
        player.update()

    sp.rehash_all_ball_gridpos()

    # draw an expanding "blueprint" of a ball when charging (holding down mouse button)
    if PhysicsBody.charging:
        PhysicsBody.template_radius += 2
        pygame.draw.circle(display, (255,255,255), mouse_coords, PhysicsBody.template_radius, 2)
    
    # display ball count, FPS
    display.blit(font.render(f"balls: {PhysicsBody.count}", False, (255, 255, 255)), (10,display.get_height()-50))
    display.blit(font.render(f"fps: {int(clock.get_fps())}", False, (255, 255, 255)), (10,display.get_height()-30))
    display.blit(font.render("left click: make ball", False, (255, 255, 255)), (10,10))
    display.blit(font.render("c: clear", False, (255, 255, 255)), (10,30))

    # origin: (0,0) location
    pygame.draw.circle(display, (100,100,100), (0-Player.scroll[0],0-Player.scroll[1]), 5)

    # scale and blit display onto screen
    scaled = pygame.transform.scale(display, screen.get_size())
    screen.blit(scaled, (0, 0))

    pygame.display.update()
    clock.tick(60)