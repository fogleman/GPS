from math import radians, pi, asin, sin, cos, atan2
import gps
import pg

R1 = 6371
R2 = R1 + 20200

SPEED = 20000
SATELLITE_SCALE = 20

LATITUDE = 36
LONGITUDE = -79

def to_xyz(lat, lng, elevation, azimuth):
    aa = radians(elevation) + pi / 2
    ar = asin(R1 * sin(aa) / R2)
    ad = pi - aa - ar
    angle = pi / 2 - ad
    x = cos(angle) * R2
    z = sin(angle) * R2
    matrix = pg.Matrix()
    matrix = matrix.rotate((0, 0, -1), pi / 2 - radians(azimuth))
    matrix = matrix.rotate((-1, 0, 0), -radians(lat))
    matrix = matrix.rotate((0, -1, 0), radians(lng))
    return matrix * (x, 0, z)

def look_at(position, target):
    px, py, pz = position
    tx, ty, tz = target
    dx, dy, dz = pg.normalize((tx - px, ty - py, tz - pz))
    rx = 2 * pi - (atan2(dx, dz) + pi)
    ry = asin(dy) + pi / 2
    matrix = pg.Matrix()
    matrix = matrix.rotate((0, 1, 0), rx)
    matrix = matrix.rotate((cos(rx), 0, sin(rx)), -ry)
    return matrix

class Window(pg.Window):
    def setup(self):
        self.device = gps.Device()
        pg.async(self.device.run)
        self.font = pg.Font(self, 1, '/Library/Fonts/Arial.ttf', 24)
        self.wasd = pg.WASD(self, speed=SPEED)
        self.wasd.look_at((0, 0, R2 + R2), (0, 0, 0))
        self.earth = pg.Context(pg.DirectionalLightProgram())
        self.earth.sampler = pg.Texture(0, 'earth.jpg')
        self.earth.use_texture = True
        self.earth.ambient_color = (0.1, 0.1, 0.1)
        self.earth.light_color = (0.9, 0.9, 0.9)
        self.earth.specular_multiplier = 0.5
        self.earth_sphere = pg.Sphere(4, R1)
        self.context = pg.Context(pg.DirectionalLightProgram())
        self.context.object_color = (1, 1, 1)
        m = SATELLITE_SCALE
        self.satellite = pg.STL('dawn.stl').center()
        self.satellite = pg.Matrix().scale((m, m, m)) * self.satellite
    def get_positions(self):
        record = self.device.record
        satellites = self.device.satellites
        if record and record.valid:
            lat = record.latitude
            lng = record.longitude
        else:
            lat = LATITUDE
            lng = LONGITUDE
        result = []
        for satellite in satellites.values():
            result.append(to_xyz(
                lat, lng, satellite.elevation, satellite.azimuth))
        return result
    def get_model_matrix(self, matrix=None):
        matrix = matrix or pg.Matrix()
        # matrix = matrix.rotate((0, 1, 0), -self.t / 4)
        matrix = matrix.rotate((0, 1, 0), radians(LONGITUDE))
        # matrix = matrix.rotate((1, 0, 0), -radians(LATITUDE))
        return matrix
    def draw_satellite(self, x, y, z):
        matrix = look_at((x, y, z), (0, 0, 0))
        matrix = matrix.translate((x, y, z))
        matrix = self.get_model_matrix(matrix)
        inverse = self.get_model_matrix().inverse()
        self.context.light_direction = inverse * pg.normalize((1, 1, 1))
        self.context.camera_position = matrix.inverse() * self.wasd.position
        matrix = self.wasd.get_matrix(matrix)
        matrix = matrix.perspective(65, self.aspect, 1, 100000)
        self.context.matrix = matrix
        self.satellite.draw(self.context)
    def draw_earth(self):
        matrix = self.get_model_matrix()
        inverse = self.get_model_matrix().inverse()
        self.earth.light_direction = inverse * pg.normalize((1, 1, 1))
        self.earth.camera_position = matrix.inverse() * self.wasd.position
        matrix = self.wasd.get_matrix(matrix)
        matrix = matrix.perspective(65, self.aspect, 1, 100000)
        self.earth.matrix = matrix
        self.earth_sphere.draw(self.earth)
    def update(self, t, dt):
        pass
    def draw(self):
        self.clear()
        self.draw_earth()
        for x, y, z in self.get_positions():
            self.draw_satellite(x, y, z)
        w, h = self.size
        self.font.render('%.1f fps' % self.fps, (w - 5, 0), (1, 0))
        text = 'x=%.2f, y=%.2f, z=%.2f' % self.wasd.position
        self.font.render(text, (5, 0))

if __name__ == "__main__":
    pg.run(Window)
