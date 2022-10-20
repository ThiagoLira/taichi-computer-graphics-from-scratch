import taichi as ti

ti.init(arch=ti.vulkan)

#### DEFINE TYPES

# define a type
vec3 = ti.types.vector(3, float)
# dataclass to hold spheres
@ti.dataclass
class Sphere:
    center: vec3
    radius: ti.f32
    color: vec3

### END TYPE DEFINITIONS 

image_res = (500, 500)
img = ti.Vector.field(3, float, image_res)

window = ti.ui.Window("Ray Tracing Test", image_res)
canvas = window.get_canvas()

INFINITY = 1000.0
Vw = 1
Vh = 1
d = 1
viewport_size = 1
projection_plane_z = 1
camera_position = (0,0,0)
# canvas width
Cw = image_res[0]
# canvas height
Ch = image_res[1]





# using coordinate system from https://www.gabrielgambetta.com/computer-graphics-from-scratch/01-common-concepts.html
@ti.func
def put_pixel(x,y,color):
    canvas_x = Cw/2 + x
    canvas_y = Ch/2 - y
    img[int(canvas_x), int(canvas_y)] = color

@ti.func
def canvas_to_viewport(x,y):
    return vec3(x*Vw/Cw, y*Vh/Ch, d)


@ti.kernel
def randomize_canvas():
    # using coordinate system from https://www.gabrielgambetta.com/computer-graphics-from-scratch/01-common-concepts.html
    for x in range(-Cw/2,Cw/2):
        for y in range(-Ch/2,Cw/2):
            put_pixel(x,y,(ti.random(ti.f32),ti.random(ti.f32),ti.random(ti.f32)))

@ti.func
def intersect_ray_sphere(O, D, sphere):
    t1 = 0
    t2 = 0

    r = sphere.radius 
    CO = O - sphere.center

    a = D.dot(D)
    b = 2.0*CO.dot(D)
    c = CO.dot(CO) - r*r

    discriminant = b*b - 4*a*c

    if discriminant < 0:
        t1, t2 =  INFINITY, INFINITY
    else:
        sqrd = ti.sqrt(discriminant)

        t1 = (-b + sqrd) / (2.0*a)
        t2 = (-b - sqrd) / (2.0*a)

    return t1, t2


@ti.func
def trace_ray(O, D, t_min, t_max):
    closest_t = INFINITY
    closest_sphere = Sphere(radius=-1)
    color = vec3(0,0,0)
 
    for i in range(n_balls):
        sphere = scene[i]
        t1, t2 = intersect_ray_sphere(O, D, sphere)

        if (t1 > t_min and t1< t_max) and t1 < closest_t:
            closest_t = t1
            closest_sphere = sphere

        if (t2 > t_min and t2< t_max) and t2 < closest_t:
            closest_t = t2
            closest_sphere = sphere
    
    # TENTAR CHECAR SE É STRUCT VAZIO DEPOIS
    if closest_sphere.radius==-1:
        color = BACKGROUND_COLOR
    else:
        color = closest_sphere.color

    return color

# define scene 
n_balls = 3

scene = Sphere.field(shape=(n_balls,))

# fill balls
scene[0].radius = 1 
scene[0].center = vec3(0, -1, 3)
scene[0].color = vec3(255, 0,0) 

scene[1].radius = 1 
scene[1].center = vec3(2, 0, 4)
scene[1].color = vec3(0, 0,255) 

scene[2].radius = 1 
scene[2].center = vec3(-2, 0, 4)
scene[2].color = vec3(0, 255,0) 

# origin of coordinate system
O = vec3(0,0,0)
BACKGROUND_COLOR = vec3(0,0,0)
@ti.kernel
def draw():
    # using coordinate system from https://www.gabrielgambetta.com/computer-graphics-from-scratch/01-common-concepts.html
    for x in range(-Cw/2,Cw/2):
        for y in range(-Ch/2,Cw/2):
            D = canvas_to_viewport(x,y)
            color = trace_ray(O, D, 1, INFINITY)
            put_pixel(x,y,color)


while window.running:
    window.show()
    draw()
    canvas.set_image(img)