from ursina import *
import math


# ============================================================
# INITIALIZATION
# ============================================================

app = Ursina()

window.title = "Technical Drone Simulator"
window.borderless = False
window.fps_counter.enabled = True


# ============================================================
# DRONE PARAMETERS
# ============================================================

MAX_SPEED = 15
VERTICAL_SPEED = 8

YAW_SPEED = 70
PITCH_SPEED = 35
ROLL_SPEED = 35

GRAVITY = 9.81

# Drone state
velocity = Vec3(0, 0, 0)

pitch = 0
roll = 0
yaw = 0

throttle = 0.55

camera_mode = 0


# ============================================================
# ENVIRONMENT
# ============================================================

ground = Entity(
    model='plane',
    scale=150,
    texture='grass',
    texture_scale=(75, 75),
    collider='box'
)

# Sky
Sky()

# Buildings / obstacles

obstacles = [
    ((15, 3, 15), (6, 6, 6)),
    ((-15, 4, 10), (8, 8, 8)),
    ((20, 2, -15), (10, 4, 10)),
    ((-20, 5, -15), (7, 10, 7)),
]

for position, scale in obstacles:

    Entity(
        model='cube',
        position=position,
        scale=scale,
        color=color.gray,
        collider='box'
    )


# ============================================================
# DRONE
# ============================================================

drone = Entity(
    position=(0, 5, 0)
)

# Main body

body = Entity(
    parent=drone,
    model='cube',
    scale=(2.2, 0.4, 1),
    color=color.black
)

# Center electronics housing

Entity(
    parent=drone,
    model='cube',
    scale=(0.8, 0.35, 0.7),
    y=0.35,
    color=color.dark_gray
)


# ============================================================
# MOTORS AND PROPELLERS
# ============================================================

motor_positions = [
    (-1.0, 0.3, -0.55),
    (1.0, 0.3, -0.55),
    (-1.0, 0.3, 0.55),
    (1.0, 0.3, 0.55)
]

motors = []
propellers = []


for x, y, z in motor_positions:

    # Arm

    Entity(
        parent=drone,
        model='cube',
        scale=(1.1, 0.12, 0.12),
        position=(x / 2, 0, z / 2),
        rotation_y=45 if x * z > 0 else -45,
        color=color.dark_gray
    )

    # Motor

    motor = Entity(
        parent=drone,
        model='cylinder',
        scale=(0.18, 0.2, 0.18),
        position=(x, y, z),
        color=color.black
    )

    motors.append(motor)

    # Propeller

    prop = Entity(
        parent=drone,
        model='cube',
        scale=(0.9, 0.03, 0.08),
        position=(x, y + 0.15, z),
        color=color.white
    )

    propellers.append(prop)


# ============================================================
# CAMERA SYSTEM
# ============================================================

camera_modes = [
    "CHASE",
    "FPV",
    "TOP",
    "SIDE"
]


def update_camera():

    global camera_mode

    # --------------------------------------------------------
    # CHASE CAMERA
    # --------------------------------------------------------

    if camera_mode == 0:

        target_position = drone.position + Vec3(
            0,
            4,
            -10
        )

        camera.position = lerp(
            camera.position,
            target_position,
            5 * time.dt
        )

        camera.look_at(drone.position)


    # --------------------------------------------------------
    # FPV CAMERA
    # --------------------------------------------------------

    elif camera_mode == 1:

        camera.position = drone.position + Vec3(
            0,
            0.35,
            0.8
        )

        camera.rotation = drone.rotation


    # --------------------------------------------------------
    # TOP CAMERA
    # --------------------------------------------------------

    elif camera_mode == 2:

        camera.position = drone.position + Vec3(
            0,
            15,
            0
        )

        camera.rotation = (90, 0, 0)


    # --------------------------------------------------------
    # SIDE CAMERA
    # --------------------------------------------------------

    elif camera_mode == 3:

        camera.position = drone.position + Vec3(
            10,
            3,
            0
        )

        camera.look_at(drone.position)


# ============================================================
# CAMERA SWITCH
# ============================================================

def input(key):

    global camera_mode

    if key == '1':
        camera_mode = 0

    if key == '2':
        camera_mode = 1

    if key == '3':
        camera_mode = 2

    if key == '4':
        camera_mode = 3

    # Emergency stop

    if key == 'x':

        global velocity
        velocity = Vec3(0, 0, 0)

    # Reset drone

    if key == 'r':

        global throttle
        drone.position = Vec3(0, 5, 0)
        drone.rotation = Vec3(0, 0, 0)
        velocity = Vec3(0, 0, 0)
        throttle = 0.55


# ============================================================
# DRONE PHYSICS
# ============================================================

def update_physics():

    global velocity
    global throttle

    # --------------------------------------------------------
    # THROTTLE
    # --------------------------------------------------------

    if held_keys['space']:
        throttle += 0.35 * time.dt

    if held_keys['shift']:
        throttle -= 0.35 * time.dt

    throttle = clamp(throttle, 0, 1)


    # --------------------------------------------------------
    # GRAVITY
    # --------------------------------------------------------

    vertical_force = (
        throttle * 2 * GRAVITY
        - GRAVITY
    )

    velocity.y += vertical_force * time.dt


    # --------------------------------------------------------
    # FORWARD VECTOR
    # --------------------------------------------------------

    forward = drone.forward

    right = drone.right


    # --------------------------------------------------------
    # PITCH
    # --------------------------------------------------------

    if held_keys['w']:

        drone.rotation_x -= PITCH_SPEED * time.dt

    if held_keys['s']:

        drone.rotation_x += PITCH_SPEED * time.dt

    # Keep pitch within a practical flight envelope.
    drone.rotation_x = clamp(drone.rotation_x, -60, 60)


    # --------------------------------------------------------
    # ROLL
    # --------------------------------------------------------

    if held_keys['a']:

        drone.rotation_z += ROLL_SPEED * time.dt

    if held_keys['d']:

        drone.rotation_z -= ROLL_SPEED * time.dt

    # Keep roll within a practical flight envelope.
    drone.rotation_z = clamp(drone.rotation_z, -60, 60)


    # --------------------------------------------------------
    # YAW
    # --------------------------------------------------------

    if held_keys['q']:

        drone.rotation_y -= YAW_SPEED * time.dt

    if held_keys['e']:

        drone.rotation_y += YAW_SPEED * time.dt


    # --------------------------------------------------------
    # FORWARD MOVEMENT
    # --------------------------------------------------------

    if held_keys['w']:

        velocity += forward * 5 * time.dt

    if held_keys['s']:

        velocity -= forward * 5 * time.dt


    # --------------------------------------------------------
    # SIDE MOVEMENT
    # --------------------------------------------------------

    if held_keys['a']:

        velocity -= right * 3 * time.dt

    if held_keys['d']:

        velocity += right * 3 * time.dt


    # --------------------------------------------------------
    # AIR DRAG
    # --------------------------------------------------------

    velocity *= 0.98


    # Limit speed

    if velocity.length() > MAX_SPEED:

        velocity = velocity.normalized() * MAX_SPEED


    # Move drone

    drone.position += velocity * time.dt


    # --------------------------------------------------------
    # GROUND COLLISION
    # --------------------------------------------------------

    if drone.y < 1:

        drone.y = 1

        velocity.y = 0


# ============================================================
# PROPULSOR ANIMATION
# ============================================================

def update_propellers():

    # Different motors rotate in different directions

    for i, prop in enumerate(propellers):

        direction = 1 if i % 2 == 0 else -1

        prop.rotation_y += (
            direction *
            (800 + throttle * 1200) *
            time.dt
        )


# ============================================================
# TELEMETRY
# ============================================================

telemetry = Text(
    text="",
    position=(-0.86, 0.42),
    scale=0.85
)


def update_telemetry():

    speed = velocity.length()

    altitude = drone.y

    heading = drone.rotation_y % 360

    pitch_angle = drone.rotation_x

    roll_angle = drone.rotation_z

    telemetry.text = (
        "DRONE TELEMETRY\n"
        "-------------------------\n"
        f"ALTITUDE : {altitude:6.2f} m\n"
        f"SPEED    : {speed:6.2f} m/s\n"
        f"THROTTLE : {throttle * 100:6.1f} %\n"
        f"HEADING  : {heading:6.1f} deg\n"
        f"PITCH    : {pitch_angle:6.1f} deg\n"
        f"ROLL     : {roll_angle:6.1f} deg\n"
        f"VERTICAL : {velocity.y:6.2f} m/s\n"
        "-------------------------\n"
        f"CAMERA   : {camera_modes[camera_mode]}"
    )


# ============================================================
# HELP PANEL
# ============================================================

help_text = Text(
    text=(
        "CONTROLS\n"
        "W/S  - Pitch / Forward\n"
        "A/D  - Roll / Strafe\n"
        "Q/E  - Yaw\n"
        "SPACE - Increase throttle\n"
        "SHIFT - Decrease throttle\n"
        "1 - Chase Camera\n"
        "2 - FPV Camera\n"
        "3 - Top Camera\n"
        "4 - Side Camera\n"
        "X - Emergency Stop\n"
        "R - Reset Drone"
    ),
    position=(0.58, 0.42),
    scale=0.7
)


# ============================================================
# CROSSHAIR
# ============================================================

crosshair = Text(
    text="+",
    origin=(0, 0),
    scale=1.5
)


# ============================================================
# LIGHTING
# ============================================================

DirectionalLight(
    rotation=(45, -45, 45)
)

AmbientLight(
    color=color.rgba(120, 120, 120, 0.5)
)


# ============================================================
# MAIN UPDATE LOOP
# ============================================================

def update():

    update_physics()

    update_propellers()

    update_camera()

    update_telemetry()


# ============================================================
# START SIMULATOR
# ============================================================

app.run()