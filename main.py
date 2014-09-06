from math import radians, pi, asin, sin, cos, atan2
from OpenGL.GL import *
from sun import sun
import gps
import pg

RADIUS = 6371
ALTITUDE = 20200
SPEED = 10000
SATELLITE_SCALE = 20
LATITUDE = 36
LONGITUDE = -79
SIMULATE = False
FONT = '/Library/Fonts/Arial.ttf'

def to_xyz(lat, lng, elevation, azimuth, altitude=ALTITUDE):
    r1 = RADIUS
    r2 = r1 + altitude
    aa = radians(elevation) + pi / 2
    ar = asin(r1 * sin(aa) / r2)
    ad = pi - aa - ar
    angle = pi / 2 - ad
    x = cos(angle) * r2
    z = sin(angle) * r2
    matrix = pg.Matrix()
    matrix = matrix.rotate((0, 0, -1), pi / 2 - radians(azimuth))
    matrix = matrix.rotate((-1, 0, 0), -radians(lat))
    matrix = matrix.rotate((0, -1, 0), radians(lng))
    return matrix * (x, 0, z)

class Window(pg.Window):
    def setup(self):
        if not SIMULATE:
            self.device = gps.Device()
            pg.async(self.device.run)
        self.font = pg.Font(self, 1, FONT, 18, bg=(0, 0, 0))
        self.wasd = pg.WASD(self, speed=SPEED)
        camera = to_xyz(LATITUDE, LONGITUDE, 90, 0, ALTITUDE * 2)
        self.wasd.look_at(camera, (0, 0, 0))
        self.earth = pg.Context(pg.DirectionalLightProgram())
        self.earth.sampler = pg.Texture(0, 'earth.jpg')
        self.earth.use_texture = True
        self.earth.ambient_color = (0.1, 0.1, 0.1)
        self.earth.light_color = (0.9, 0.9, 0.9)
        self.earth.specular_multiplier = 0.5
        self.earth_sphere = pg.Sphere(4, RADIUS)
        self.context = pg.Context(pg.DirectionalLightProgram())
        self.context.object_color = (1, 1, 1)
        m = SATELLITE_SCALE
        self.satellite = pg.STL('dawn.stl').center()
        # self.satellite = pg.Sphere(3, SATELLITE_SCALE)
        self.satellite = pg.Matrix().scale((m, m, m)) * self.satellite
        self.lines = pg.Context(pg.SolidColorProgram())
        self.lines.color = (1, 1, 1, 0.25)
    def get_lat_lng(self):
        if SIMULATE:
            lat = LATITUDE
            lng = LONGITUDE
        else:
            record = self.device.record
            valid = record and record.valid
            lat = record.latitude if valid else LATITUDE
            lng = record.longitude if valid else LONGITUDE
        return (lat, lng)
    def get_position(self):
        lat, lng = self.get_lat_lng()
        return to_xyz(lat, lng, 0, 0, 0)
    def get_positions(self):
        result = []
        lat, lng = self.get_lat_lng()
        if SIMULATE:
            data = []
            data += [(i, 0) for i in range(0, 91, 15)]
            data += [(i, 90) for i in range(0, 90, 15)]
            data += [(i, 180) for i in range(0, 90, 15)]
            data += [(i, 270) for i in range(0, 90, 15)]
            data += [(0, i) for i in range(0, 361, 15)]
            for elevation, azimuth in data:
                result.append(to_xyz(lat, lng, elevation, azimuth))
        else:
            for satellite in self.device.satellites.values():
                elevation = satellite.elevation
                azimuth = satellite.azimuth
                result.append(to_xyz(lat, lng, elevation, azimuth))
        return result
    def get_sun(self):
        lat, lng = self.get_lat_lng()
        elevation, azimuth = sun(lat, lng)
        return pg.normalize(to_xyz(lat, lng, elevation, azimuth))
    def rotate_satellite(self, position):
        dx, dy, dz = pg.normalize(position)
        rx = atan2(dz, dx) + pi / 2
        ry = asin(dy) - pi / 2
        matrix = pg.Matrix()
        matrix = matrix.rotate((0, 1, 0), rx)
        matrix = matrix.rotate((cos(rx), 0, sin(rx)), -ry)
        return matrix
    def draw_lines(self):
        bits = ('0' * 4 + '1' * 4) * 2
        shift = int(self.t * 16) % len(bits)
        bits = bits[shift:] + bits[:shift]
        glLineStipple(1, int(bits, 2))
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        matrix = self.wasd.get_matrix()
        matrix = matrix.perspective(65, self.aspect, 1, 100000)
        self.lines.matrix = matrix
        data = []
        x1, y1, z1 = self.get_position()
        for x2, y2, z2 in self.get_positions():
            data.append((x2, y2, z2))
            data.append((x1, y1, z1))
        if data:
            self.lines.position = pg.VertexBuffer(data)
            glEnable(GL_BLEND)
            glEnable(GL_LINE_STIPPLE)
            self.lines.draw(pg.GL_LINES)
            glDisable(GL_LINE_STIPPLE)
            glDisable(GL_BLEND)
            self.lines.position.delete()
    def draw_satellite(self, position):
        self.context.camera_position = self.wasd.position
        self.context.light_direction = self.get_sun()
        matrix = self.rotate_satellite(position)
        self.context.normal_matrix = matrix.inverse().transpose()
        matrix = matrix.translate(position)
        self.context.model_matrix = matrix
        matrix = self.wasd.get_matrix(matrix)
        matrix = matrix.perspective(65, self.aspect, 1, 100000)
        self.context.matrix = matrix
        self.satellite.draw(self.context)
    def draw_earth(self):
        self.earth.camera_position = self.wasd.position
        self.earth.light_direction = self.get_sun()
        matrix = self.wasd.get_matrix()
        matrix = matrix.perspective(65, self.aspect, 1, 100000)
        self.earth.matrix = matrix
        self.earth_sphere.draw(self.earth)
    def draw(self):
        self.clear()
        self.draw_earth()
        for position in self.get_positions():
            self.draw_satellite(position)
        self.draw_lines()
        # w, h = self.size
        # self.font.render('%.1f fps' % self.fps, (w - 5, 0), (1, 0))
        # text = '%.2f, %.2f, %.2f' % self.wasd.position
        # self.font.render(text, (5, 0))

if __name__ == "__main__":
    pg.run(Window)
