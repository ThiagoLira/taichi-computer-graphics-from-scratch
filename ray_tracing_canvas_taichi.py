import taichi as ti

ti.init(arch=ti.cuda)

# DEFINE TYPES

# define a type
vec3 = ti.types.vector(3, float)
color_tup = ti.types.vector(3, ti.u8)


@ti.dataclass
class Sphere:
    center: vec3
    radius: ti.f32
    color: vec3
    specular: ti.int32
    reflective: float


@ti.dataclass
class Light:
    # enum
    kind: ti.int32
    intensity: ti.f32
    position: vec3
    direction: vec3

# convention for 'kind' enum
# 0 : ambient
# 1 : point
# 2 : directional

# END TYPE DEFINITIONS


image_res = (500, 500)
img = ti.Vector.field(3, float, image_res)

window = ti.ui.Window("Ray Tracing Test", image_res)
canvas = window.get_canvas()

INFINITY = 100000000.0
Vw = 1
Vh = 1
d = 1

camera_position = (0, 0, 0)
# canvas width
Cw = image_res[0]
# canvas height
Ch = image_res[1]


# using coordinate system from https://www.gabrielgambetta.com/computer-graphics-from-scratch/01-common-concepts.html
@ti.func
def put_pixel(x, y, color):
    canvas_x = Cw/2 + x
    # taichi canvas is inverted in relation to js one!
    canvas_y = -Ch/2 + y + 1

    img[int(canvas_x), int(canvas_y)] = color


# POSSIVEL PERDA DE PERFORMANCE
@ti.func
def clamp(color):
    return vec3(ti.min(1, ti.max(0, color[0])),
                ti.min(1, ti.max(0, color[1])),
                ti.min(1, ti.max(0, color[2])))


@ti.func
def canvas_to_viewport(x, y):
    return vec3(x*Vw/Cw, y*Vh/Ch, d)


@ti.kernel
def randomize_canvas():
    # using coordinate system from https://www.gabrielgambetta.com/computer-graphics-from-scratch/01-common-concepts.html
    for x in range(-Cw/2, Cw/2):
        for y in range(-Ch/2, Cw/2):
            put_pixel(x,y,(ti.random(ti.f32),ti.random(ti.f32),ti.random(ti.f32)))


@ti.func
def compute_lighting(P: vec3, N: vec3, V: vec3, s: int):
    i = 0.0
    L = vec3(0.0, 0.0, 0.0)
    # convention for 'kind' enum
    # 0 : ambient
    # 1 : point
    # 2 : directional
    t_max = 0
    for j in range(n_lights):
        kind = lights[j].kind
        if kind == 0:
            i += lights[j].intensity
        else:
            if kind == 1:
                L = lights[j].position - P
                t_max = 1.0

            elif kind == 2:
                L = lights[j].direction
                t_max = INFINITY

            # shadow check
            shadow_sphere, _ = closest_intersection(P, L, 0.001, t_max)
            if shadow_sphere.radius != -1:
                continue

            # diffuse light
            n_dot_l = N.dot(L)
            if n_dot_l > 0:
                i += lights[j].intensity * n_dot_l/(N.norm() * L.norm())

            # specular light
            if s != -1:
                R = 2 * N * N.dot(L) - L
                r_dot_v = R.dot(V)
                if r_dot_v > 0:
                    i += lights[j].intensity * (r_dot_v/(R.norm() * V.norm()))**s
    return i


@ti.func
def intersect_ray_sphere(Or: vec3, D: vec3, sphere):
    t1 = 0.0
    t2 = 0.0

    r = sphere.radius
    CO = Or - sphere.center

    a = D.dot(D)
    b = 2.0*CO.dot(D)
    c = CO.dot(CO) - r*r

    discriminant = b*b - 4.0*a*c

    if discriminant < 0:
        t1, t2 = INFINITY, INFINITY
    else:
        sqrd = ti.sqrt(discriminant)

        t1 = (-b + sqrd) / (2.0*a)
        t2 = (-b - sqrd) / (2.0*a)

    return t1, t2


@ti.func
def closest_intersection(Or: vec3, D: vec3, t_min: float, t_max: float):
    closest_t = INFINITY
    closest_sphere = Sphere(radius=-1)

    for i in range(n_balls):
        sphere = scene[i]
        t1, t2 = intersect_ray_sphere(Or, D, sphere)

        if (t1 > t_min and t1 < t_max) and t1 < closest_t:
            closest_t = t1
            closest_sphere = sphere

        if (t2 > t_min and t2 < t_max) and t2 < closest_t:
            closest_t = t2
            closest_sphere = sphere

    return closest_sphere, closest_t


@ti.func
def reflect_ray(R, N):
    return 2.0 * N * N.dot(R) - R

@ti.func
def trace_ray(Or: vec3, D: vec3, t_min: float, t_max: float):
    P = vec3(0.0, 0.0, 0.0)
    L = vec3(0.0, 0.0, 0.0)
    N = vec3(0.0, 0.0, 0.0)

    color = vec3(0.0, 0.0, 0.0)
    closest_sphere, closest_t = closest_intersection(Or, D, t_min, t_max)
    # TENTAR CHECAR SE É STRUCT VAZIO DEPOIS
    if closest_sphere.radius == -1:
        color = BACKGROUND_COLOR
    else:
        P = O + closest_t * D
        N = P - closest_sphere.center
        N = N.normalized()
        color = closest_sphere.color * compute_lighting(P, N, -D, closest_sphere.specular)

    
    return color, closest_sphere, P, D, N

# handle reflection
@ti.func
def trace_rays(Or: vec3, D: vec3, t_min: float, t_max: float, N_REFLECTIONS):
        color, closest_sphere, P, D, N = trace_ray(Or, D, t_min, t_max)
        r = closest_sphere.reflective
        while N_REFLECTIONS > 0 and r>0:
            R = reflect_ray(-D, N)
            color_r, closest_sphere, P, D, N = trace_ray(P, R, 0.0001, INFINITY)
            color = color * (1.0 - r) + color_r * r
                
            N_REFLECTIONS-=1
            r = closest_sphere.reflective
        return color
# define scene
n_balls = 4

scene = Sphere.field(shape=(n_balls,))

# fill balls
scene[0].radius = 1
scene[0].center = vec3(0, -1, 3)
scene[0].color = vec3(1.0, 0, 0)
scene[0].specular = 500
scene[0].reflective  = 0.2

scene[1].radius = 1
scene[1].center = vec3(2, 0, 4)
scene[1].color = vec3(0, 0, 1.0)
scene[1].specular = 500
scene[1].reflective  = 0.3

scene[2].radius = 1
scene[2].center = vec3(-2, 0, 4)
scene[2].color = vec3(0, 1.0, 0)
scene[2].specular = 10
scene[2].reflective  = 0.4

scene[3].radius = 1
scene[3].center = vec3(0, -5001, 0)
scene[3].color = vec3(1.0, 1.0, 0)
scene[3].specular = 1000
scene[3].reflective  = 0.5


# define lighting

n_lights = 3

lights = Light.field(shape=(n_lights,))
# fill lights

lights[0].kind = 0
lights[0].intensity = 0.2

lights[1].kind = 1
lights[1].intensity = 0.6
lights[1].position = vec3(2.0, 1.0, 0.0)
lights[1].direction = vec3(1.0, 4.0, 4.0)

lights[2].kind = 2
lights[2].intensity = 0.4
lights[2].direction = vec3(1.0, 4.0, 4.0)


# origin of coordinate system
O = vec3(0.0, 0.0, 0.0)
BACKGROUND_COLOR = vec3(0.0, 0.0, 0.0)
N_REFLECTIONS = 3

# MAIN DRAW LOOP
@ti.kernel
def draw():
    # using coordinate system from https://www.gabrielgambetta.com/computer-graphics-from-scratch/01-common-concepts.html
    for x in range(-Cw/2, Cw/2):
        for y in range(-Ch/2, Cw/2):
            D = canvas_to_viewport(x, y)
            color = trace_rays(O, D, 1.0, INFINITY, N_REFLECTIONS)
            put_pixel(x, y, color)


DEBUG = False

if (not DEBUG):
    while window.running:
        window.show()
        draw()
        canvas.set_image(img)
        scene[2].center[0] += .001
        scene[0].center[2] += .001
else:
    window.show()
    draw()
    canvas.set_image(img)
