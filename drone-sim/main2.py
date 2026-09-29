import math
import random
from ursina import *

# ---------- tunables ----------
G = 9.81               # gravity (m/s^2)
HALF_H = 0.1           # drone half-height, so it rests on the ground
MAX_TILT = 30          # max pitch/roll angle (deg)
CRASH_VSPEED = 4.5     # descending faster than this on touchdown = crash
CRASH_TILT = 15        # touching down tilted more than this = crash

app = Ursina(title='Drone Flight Simulator')
window.exit_button.visible = False
Sky()
Entity(model='plane', scale=600, texture='white_cube',
       texture_scale=(300, 300), color=color.green)

# ---------- landing pads ----------
pads = {'HOME': Vec3(0, 0, 0), 'PAD B': Vec3(70, 0, 60)}
for name, p in pads.items():
    Entity(model='cube', position=(p.x, 0.03, p.z), scale=(10, 0.06, 10),
           color=color.yellow if name == 'HOME' else color.azure)

# ---------- rings (a circuit around the home pad) ----------
rings = []
for i in range(8):
    a = i / 8 * math.tau
    radius = 35 + 10 * (i % 2)
    e = Entity(position=(math.sin(a) * radius, 6 + (i % 3) * 3, math.cos(a) * radius),
               rotation_y=90 + math.degrees(a))
    for k in range(16):
        t = k / 16 * math.tau
        Entity(parent=e, model='cube', color=color.orange, scale=0.5,
               position=(math.cos(t) * 3, math.sin(t) * 3, 0))
    rings.append({'entity': e, 'done': False})

# ---------- buildings (outer "city", clear of pads and rings) ----------
random.seed(7)
buildings = []
while len(buildings) < 30:
    x, z = random.uniform(-140, 140), random.uniform(-140, 140)
    if math.hypot(x, z) < 60:
        continue
    if any(math.hypot(x - p.x, z - p.z) < 20 for p in pads.values()):
        continue
    w, d, h = random.uniform(6, 14), random.uniform(6, 14), random.uniform(10, 35)
    Entity(model='cube', position=(x, h / 2, z), scale=(w, h, d),
           color=random.choice([color.gray, color.light_gray, color.dark_gray, color.brown]))
    buildings.append((x, z, w, d, h))

# ---------- drone model ----------
drone = Entity()
body = Entity(parent=drone, model='cube', color=color.dark_gray, scale=(0.8, 0.15, 0.8))
Entity(parent=drone, model='cube', color=color.red, scale=(0.2, 0.1, 0.3), position=(0, 0, 0.5))  # nose
for sx in (-1, 1):
    for sz in (-1, 1):
        Entity(parent=drone, model='sphere', color=color.light_gray,
               scale=(0.5, 0.03, 0.5), position=(sx * 0.5, 0.1, sz * 0.5))

# ---------- state ----------
class State:
    pass

s = State()
s.score = 0
s.cam = 0
s.orbit = 0.0


def reset():
    s.vel = Vec3(0, 0, 0)
    s.pitch = s.roll = s.yaw = 0.0
    s.throttle = 0.0
    s.crashed = False
    s.grounded = True
    s.msg = ''
    body.color = color.dark_gray
    drone.position = Vec3(0, HALF_H, 0)
    drone.rotation = Vec3(0, 0, 0)


reset()

# ---------- HUD ----------
hud = Text(position=window.top_left + Vec2(0.02, -0.02), origin=(-0.5, 0.5), scale=1.2)
banner = Text(text='', origin=(0, 0), position=(0, 0.3), scale=2, color=color.red)
help_text = Text(
    text='SPACE/SHIFT throttle | W/S pitch | A/D roll | Q/E yaw\n'
         'R reset | C camera | H help | ESC quit',
    origin=(0, 0.5), position=(0, -0.42), scale=1)


def crash(reason):
    s.crashed = True
    s.vel = Vec3(0, 0, 0)
    s.msg = f'CRASH ({reason}) - press R'
    body.color = color.red


def land_score():
    name, p = min(pads.items(), key=lambda kv: math.hypot(drone.x - kv[1].x, drone.z - kv[1].z))
    dist = math.hypot(drone.x - p.x, drone.z - p.z)
    if dist < 5:
        pts = int(100 - dist * 18)
        s.score += pts
        s.msg = f'Landed on {name}: +{pts}'
    else:
        s.msg = 'Landed off-pad'


def fly(dt):
    k = held_keys
    s.throttle = clamp(s.throttle + (k['space'] - k['left shift']) * 0.6 * dt, 0, 1)

    # target tilt; stays level on the ground, self-levels when keys are released
    tp = (k['w'] - k['s']) * MAX_TILT
    tr = (k['d'] - k['a']) * MAX_TILT
    if s.grounded:
        tp = tr = 0
    blend = min(1, 5 * dt)
    s.pitch += (tp - s.pitch) * blend
    s.roll += (tr - s.roll) * blend
    s.yaw += (k['e'] - k['q']) * 90 * dt

    p, r, y = math.radians(s.pitch), math.radians(s.roll), math.radians(s.yaw)
    thrust = s.throttle * 2 * G                      # 50% throttle == gravity -> hover
    a_up = thrust * math.cos(p) * math.cos(r) - G
    a_fwd = thrust * math.sin(p)                     # tilt redirects thrust sideways
    a_right = thrust * math.sin(r)
    ax = a_fwd * math.sin(y) + a_right * math.cos(y)
    az = a_fwd * math.cos(y) - a_right * math.sin(y)

    s.vel += Vec3(ax, a_up, az) * dt
    drag_h, drag_v = 1 - min(1, 0.6 * dt), 1 - min(1, 0.3 * dt)   # air drag
    s.vel = Vec3(s.vel.x * drag_h, s.vel.y * drag_v, s.vel.z * drag_h)

    drone.position += s.vel * dt
    drone.rotation = Vec3(s.pitch, s.yaw, s.roll)    # if roll banks the wrong way, use -s.roll

    # ground contact
    if drone.y <= HALF_H:
        drone.y = HALF_H
        if s.vel.y < 0:
            tilt = max(abs(s.pitch), abs(s.roll))
            if not s.grounded:
                if -s.vel.y > CRASH_VSPEED:
                    return crash('too fast')
                if tilt > CRASH_TILT:
                    return crash('tilted')
                land_score()
            s.vel = Vec3(s.vel.x, 0, s.vel.z)
        f = max(0, 1 - 8 * dt)                       # ground friction
        s.vel = Vec3(s.vel.x * f, s.vel.y, s.vel.z * f)
        s.grounded = True
    else:
        if s.grounded:
            s.msg = ''
        s.grounded = False

    # building collision
    for bx, bz, w, d, h in buildings:
        if abs(drone.x - bx) < w / 2 + 0.4 and abs(drone.z - bz) < d / 2 + 0.4 and drone.y < h + 0.1:
            return crash('building')

    # rings
    for ring in rings:
        e = ring['entity']
        if not ring['done'] and (drone.position - e.position).length() < 2.5:
            ring['done'] = True
            s.score += 100
            for c in e.children:
                c.color = color.green


def move_camera(dt):
    y = math.radians(s.yaw)
    fwd = Vec3(math.sin(y), 0, math.cos(y))
    camera.fov = 100 if s.cam == 1 else 80
    if s.cam == 0:      # chase
        target = drone.position - fwd * 9 + Vec3(0, 3.5, 0)
        camera.position = lerp(camera.position, target, min(1, 6 * dt))
        camera.look_at(drone.position + Vec3(0, 1, 0))
    elif s.cam == 1:    # FPV
        camera.position = drone.position + fwd * 0.4 + Vec3(0, 0.15, 0)
        camera.rotation = drone.rotation
    else:               # high orbit
        s.orbit += dt * 0.2
        camera.position = drone.position + Vec3(math.sin(s.orbit) * 30, 30, math.cos(s.orbit) * 30)
        camera.look_at(drone.position)


def update():
    dt = min(time.dt, 0.05)
    if not s.crashed:
        fly(dt)
    move_camera(dt)
    hud.text = (f'ALT   {drone.y - HALF_H:6.1f} m\n'
                f'SPEED {s.vel.length():6.1f} m/s\n'
                f'THR   {s.throttle * 100:6.0f} %\n'
                f'SCORE {s.score:6d}   rings {sum(r["done"] for r in rings)}/8')
    banner.text = s.msg


def input(key):
    if key == 'r':
        reset()
    elif key == 'c':
        s.cam = (s.cam + 1) % 3
    elif key == 'h':
        help_text.enabled = not help_text.enabled
    elif key == 'escape':
        application.quit()


app.run()