﻿# TODO:
# fix plane collision fp error jerkiness
# .chf Convex Heirarcy File (limit checks to PVS)
# ABCD Plane and AABB defines a surface
# SWEPT LAST-POS COLLISION DETECTION

# PROPER GRAVITY AND PLANE COLISIONS:
# if aabb is intersecting plane, move out of plane along velociy vector
# gravity for given time falling:
# distance = 0.5 * 9.81 * time**2
# Quake 3 Gravity is 800 inches/second
# approx. 20.32 m/s

# bhop physics variants:
# Quake
# Source (w/ ABH?)
# Titanfall (w/ Wallrun, Stim, Grapple & G-Star?)
# Apex (w/ Wallhops)

# ENSURE JUMP IS DETERMINISTIC
# RECORD PEAK HEIGHTS AND TEST AT DIFFERENT TICKRATES

# FLOOR COLLISION IS ROUGH
# VELOCITY ESPECIALLY
import ctypes
import math
from time import time

import OpenGL.GL as gl
import OpenGL.GLU as glu
import sdl2

from utilities import camera
from utilities import physics
from utilities import vector


# NOTE: all units are in metres


camera.sensitivity = 2


class plane_struct:
    def __init__(self, normal, distance, BBmin, BBmax):
        self.normal = vector.vec3(normal).normalise()
        self.distance = distance
        self.aabb = physics.aabb(BBmin, BBmax)

    def __repr__(self):
        P = str((self.normal, self.distance))
        return str(P + " " + str(self.aabb))


class client:
    def __init__(self, name):
        self.aabb = physics.aabb((-.5, -.5, 0), (.5, .5, 2))
        self.swept_aabb = physics.aabb((0, 0, 0), (0, 0, 0))
        # ^ could be local to update?
        self.camera = camera.firstperson()
        self.position = vector.vec3(0, 0, 0)
        self.old_position = vector.vec3(0, 0, 0)
        self.rotation = vector.vec3(0, 0, 0)
        self.front = vector.vec3(0, 1, 0)
        self.speed = 10
        self.name = name
        self.onGround = False
        self.velocity = vector.vec3()

    def update(self, mouse, keys, dt):
        """gravity, velocity & acceleration"""
        self.camera.update(mouse)
        self.rotation = self.camera.rotation
        wish_vector = vector.vec3()
        wish_vector.x = ((sdl2.SDLK_d in keys) - (sdl2.SDLK_a in keys))
        wish_vector.y = ((sdl2.SDLK_w in keys) - (sdl2.SDLK_s in keys))
        true_wish = wish_vector.rotate(0, 0, -self.rotation.z)
        self.front = vector.vec3(0, 1, 0).rotate(0, 0, -self.rotation.z)
        # GET CURRENT FRICTION (FROM SURFACE CONTACT)
        true_speed = self.speed * (1 if self.onGround else 1.75)
        self.position += true_wish * true_speed * dt  # NEED FRICTION
        if not self.onGround:
            G = vector.vec3(0, 0, -9.81)  # GRAVITY
            self.velocity += 0.5 * G * dt
            # ^ 9.81 meters per second per second
            # - need actual acceleration, this is just an approximation
        self.onGround = False
        self.old_position = self.position
        self.position += self.velocity
        mins = (min(self.old_position.x, self.position.x),
                min(self.old_position.y, self.position.y),
                min(self.old_position.z, self.position.z))
        maxs = (max(self.old_position.x, self.position.x),
                max(self.old_position.y, self.position.y),
                max(self.old_position.z, self.position.z))
        self.swept_aabb = physics. aabb(self.aabb.min + vector.vec3(*mins),
                                        self.aabb.max + vector.vec3(*maxs))
        global planes
        for plane in planes:  # filtered with position & bsp nodes
            # also should combine results rather than applying in order
            if self.swept_aabb.intersects(plane.aabb):
                p = vector.dot(self.position, plane.normal)
                max_p = self.swept_aabb.depth_along_axis(plane.normal)
                if p <= max_p and p <= abs(plane.distance):  # simplify
                    # push out of the plane, without changing velocity
                    self.position += math.fsum([plane.distance, -p]) * plane.normal
                    # reset jump? (45 degree check)
                    if vector.dot(plane.normal, vector.vec3(z=1)) <= math.sqrt(2):
                        self.onGround = True
                    self.velocity = vector.vec3()
                    # friction, surf & bounce
                    # self.velocity -= self.velocity * plane.normal
                    if sdl2.SDLK_SPACE in keys:  # JUMP
                        self.velocity.z += 0.6

    def draw_aabb(self, aabb):  # why isn't this a physics.aabb method?
        gl.glBegin(gl.GL_QUADS)
        gl.glVertex(aabb.min.x, aabb.max.y, aabb.max.z)
        gl.glVertex(aabb.max.x, aabb.max.y, aabb.max.z)
        gl.glVertex(aabb.max.x, aabb.min.y, aabb.max.z)
        gl.glVertex(aabb.min.x, aabb.min.y, aabb.max.z)

        gl.glVertex(aabb.min.x, aabb.max.y, aabb.max.z)
        gl.glVertex(aabb.max.x, aabb.max.y, aabb.max.z)
        gl.glVertex(aabb.max.x, aabb.max.y, aabb.min.z)
        gl.glVertex(aabb.min.x, aabb.max.y, aabb.min.z)

        gl.glVertex(aabb.min.x, aabb.min.y, aabb.max.z)
        gl.glVertex(aabb.max.x, aabb.min.y, aabb.max.z)
        gl.glVertex(aabb.max.x, aabb.min.y, aabb.min.z)
        gl.glVertex(aabb.min.x, aabb.min.y, aabb.min.z)

        gl.glVertex(aabb.min.x, aabb.max.y, aabb.min.z)
        gl.glVertex(aabb.max.x, aabb.max.y, aabb.min.z)
        gl.glVertex(aabb.max.x, aabb.min.y, aabb.min.z)
        gl.glVertex(aabb.min.x, aabb.min.y, aabb.min.z)
        gl.glEnd()

    def draw(self):
        gl.glPushMatrix()
        gl.glTranslate(self.position.x, self.position.y, self.position.z)
        gl.glBegin(gl.GL_LINES)
        # facing vector
        gl.glColor(1, 0, 1)
        gl.glVertex(0, 0, (self.aabb.min.z + self.aabb.max.z) / 2)
        gl.glVertex(self.front.x, self.front.y, (self.aabb.min.z + self.aabb.max.z) / 2)
        # velocity vector
        gl.glColor(0, 1, 0.1)
        gl.glVertex(0, 0, (self.aabb.min.z + self.aabb.max.z) / 2)
        gl.glVertex(self.velocity.x, self.velocity.y, (self.velocity.z + (self.aabb.min.z + self.aabb.max.z)) / 2)
        # wish vector
        gl.glColor(0, 0.1, 1)
        gl.glVertex(0, 0, (self.aabb.min.z + self.aabb.max.z) / 2)
        gl.glVertex(self.velocity.x, self.velocity.y, (self.aabb.min.z + self.aabb.max.z) / 2)
        gl.glEnd()
        # center
        gl.glColor(1, 0, 1)
        gl.glBegin(gl.GL_POINTS)
        gl.glVertex(0, 0, 0)
        gl.glEnd()
        # aabb
        self.draw_aabb(self.aabb)
        gl.glPopMatrix()
        # gl.glPushMatrix()
        # gl.glTranslate(self.old_position.x, self.old_position.y, self.old_position.z)
        # gl.glColor(0, 1, 1)
        # gl.glBegin(gl.GL_POINTS)
        # gl.glVertex(0, 0, 0)
        # gl.glEnd()
        # gl.glBegin(gl.GL_LINES)
        # gl.glVertex(0, 0, 0)
        # sweep_line = self.position - self.old_position
        # gl.glVertex(sweep_line.x, sweep_line.y, sweep_line.z)
        # gl.glEnd()
        # self.draw_aabb(self.aabb)
        # gl.glPopMatrix()
        # gl.glColor(1, 0, 0)
        # self.draw_aabb(self.swept_aabb)

    def set_view(self):
        self.camera.set(self.position + (0, 0, 1.75))

    def spawn(self, position=vector.vec3()):
        self.position = position
        self.velocity = vector.vec3()

    def report(self):
        print("@", self.position.z, "with velocity of:", self.velocity)


def main(width, height):
    sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)
    window_spec = (*[sdl2.SDL_WINDOWPOS_CENTERED] * 2, width, height)
    window_mode = sdl2.SDL_WINDOW_OPENGL | sdl2.SDL_WINDOW_BORDERLESS
    window = sdl2.SDL_CreateWindow(b"SDL2 OpenGL - bhop.py", *window_spec, window_mode)
    glContext = sdl2.SDL_GL_CreateContext(window)
    sdl2.SDL_GL_SetSwapInterval(0)
    gl.glClearColor(0.1, 0.1, 0.1, 0.0)
    glu.gluPerspective(90, width / height, 0.1, 4096)
    gl.glPointSize(8)
    # transparency
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

    mouse = vector.vec2(0, 0)
    keys = []

    global planes
    planes = [plane_struct((0, 0, 1), 0, (-8, -16, -0.1), (8, 16, 0.1)),
              plane_struct((0, 0, 1), -16, (-32, -32, -15.9), (32, 32, -16.1)),
              plane_struct((1, 0, 1), 0, (-16, -16, 0), (16, 16, 4))]

    # convert planes within aabbs to drawable geo
    # slice planes with other planes to create ngons

    client0 = client("b!scuit")
    # TODO: draw client names over clients
    spectator_camera = camera.fixed((0, 0, 16), (90, 0, 0))
    cameras = [client0.set_view, spectator_camera.set]
    active = 0
    # ^ camera is selected from a list, cycled by clicking RMB

    sdl2.SDL_SetRelativeMouseMode(sdl2.SDL_TRUE)
    sdl2.SDL_SetWindowGrab(window, sdl2.SDL_TRUE)
    sdl2.SDL_CaptureMouse(sdl2.SDL_TRUE)

    oldtime = time()
    tickrate = 125
    dt = 1 / tickrate
    event = sdl2.SDL_Event()
    while True:
        while sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            if event.type == sdl2.SDL_QUIT or event.key.keysym.sym == sdl2.SDLK_ESCAPE:
                sdl2.SDL_GL_DeleteContext(glContext)
                sdl2.SDL_DestroyWindow(window)
                sdl2.SDL_Quit()
                return False
            if event.type == sdl2.SDL_KEYDOWN:
                keys.append(event.key.keysym.sym)
            if event.type == sdl2.SDL_KEYUP:
                while event.key.keysym.sym in keys:
                    keys.remove(event.key.keysym.sym)
            if event.type == sdl2.SDL_MOUSEMOTION:
                mouse = vector.vec2(event.motion.xrel, event.motion.yrel)
                sdl2.SDL_WarpMouseInWindow(window, width // 2, height // 2)
            if event.type == sdl2.SDL_MOUSEBUTTONDOWN:
                if event.button.button == sdl2.SDL_BUTTON_RIGHT:
                    # cycle camera functions
                    active = 0 if active == 1 else 1
            # handle keypresses
            if sdl2.SDLK_r in keys:  # respawn
                client0.spawn()
            if sdl2.SDLK_BACKQUOTE in keys:  # debug info
                client0.report()
        dt = time() - oldtime
        if dt >= 1 / tickrate:
            client0.update(mouse, keys, 1 / tickrate)
            mouse = vector.vec2(0, 0)
            dt -= 1 / tickrate
            oldtime = time()

        # RENDER
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glLoadIdentity()
        glu.gluPerspective(90, width / height, 0.1, 128)
        cameras[active]()  # ew, camera system is nasty

        # planes
        gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_FILL)
        gl.glColor(1, 0.5, 0, 0.25)
        gl.glBegin(gl.GL_QUADS)
        gl.glVertex(-8, 16)
        gl.glVertex(8, 16)
        gl.glVertex(8, -16)
        gl.glVertex(-8, -16)
        gl.glEnd()
        gl.glBegin(gl.GL_TRIANGLE_FAN)
        gl.glVertex(-32, 32, -16)
        gl.glVertex(32, 32, -16)
        gl.glVertex(32, -32, -16)
        gl.glVertex(-32, -32, -16)
        gl.glEnd()
        gl.glBegin(gl.GL_QUADS)
        gl.glVertex(-8, 16, 4)
        gl.glVertex(8, 16, -4)
        gl.glVertex(8, -16, -4)
        gl.glVertex(-8, -16, 4)
        gl.glEnd()
        # plane normals
        gl.glColor(0, 0.5, 1)
        gl.glBegin(gl.GL_LINES)
        for plane in planes:
            gl.glVertex(*(plane.normal * plane.distance))
            gl.glVertex(*(plane.normal * (plane.distance + 1)))
        gl.glEnd()
        # player
        gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_LINE)
        client0.draw()
        sdl2.SDL_GL_SwapWindow(window)
        # frame rendered


if __name__ == '__main__':
    try:
        main(1280, 720)
    except Exception as exc:
        sdl2.SDL_Quit()  # close window if the script breaks
        raise exc
