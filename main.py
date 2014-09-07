from math import radians, degrees, pi, asin, sin, cos, atan2
from OpenGL.GL import *
import ephem
import gps
import pg

EARTH_RADIUS = 6371
MOON_RADIUS = 1737.1
AU = 149597870.7
ALTITUDE = 20200
SPEED = 10000
SATELLITE_SCALE = 20
FONT = '/Library/Fonts/Arial.ttf'

ZNEAR = 1
ZFAR = 1000000

def to_xyz(lat, lng, elevation, azimuth, altitude=ALTITUDE):
    r1 = EARTH_RADIUS
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
        self.device = gps.Device()
        pg.async(self.device.run)
        self.fix = False
        self.font = pg.Font(self, 3, FONT, 18, bg=(0, 0, 0))
        self.wasd = pg.WASD(self, speed=SPEED)
        self.wasd.look_at((0, 0, EARTH_RADIUS + ALTITUDE * 2), (0, 0, 0))
        # stars
        self.stars = pg.Context(StarsProgram())
        self.stars.sampler = pg.Texture(2, 'resources/stars.png')
        self.stars_sphere = pg.Sphere(4).reverse_winding()
        # earth
        self.earth = pg.Context(EarthProgram())
        self.earth.day = pg.Texture(0, 'resources/earth_day.jpg')
        self.earth.night = pg.Texture(1, 'resources/earth_night.jpg')
        self.earth.ambient_color = (0.4, 0.4, 0.4)
        self.earth.light_color = (1.25, 1.25, 1.25)
        self.earth.specular_power = 20.0
        self.earth.specular_multiplier = 0.3
        self.earth_sphere = pg.Sphere(5, EARTH_RADIUS)
        # moon
        self.moon = pg.Context(pg.DirectionalLightProgram())
        self.moon.use_texture = True
        self.moon.sampler = pg.Texture(4, 'resources/moon.jpg')
        self.moon.ambient_color = (0.1, 0.1, 0.1)
        self.moon.light_color = (1.3, 1.3, 1.3)
        self.moon.specular_power = 20.0
        self.moon.specular_multiplier = 0.3
        self.moon_sphere = pg.Sphere(4, MOON_RADIUS)
        # satellites
        self.context = pg.Context(pg.DirectionalLightProgram())
        self.context.object_color = (1, 1, 1)
        m = SATELLITE_SCALE
        self.satellite = pg.STL('resources/dawn.stl').center()
        self.satellite = pg.Matrix().scale((m, m, m)) * self.satellite
        # lines
        self.lines = pg.Context(pg.SolidColorProgram())
        self.lines.color = (1, 1, 1, 0.25)
    def get_lat_lng(self):
        record = self.device.record
        valid = record and record.valid
        lat = record.latitude if valid else 0
        lng = record.longitude if valid else 0
        return (lat, lng)
    def get_position(self):
        lat, lng = self.get_lat_lng()
        return to_xyz(lat, lng, 0, 0, 0)
    def get_positions(self):
        result = []
        lat, lng = self.get_lat_lng()
        for satellite in self.device.satellites.values():
            result.append(to_xyz(
                lat, lng, satellite.elevation, satellite.azimuth))
        return result
    def get_sun(self):
        lat, lng = self.get_lat_lng()
        observer = ephem.Observer()
        observer.lat = radians(lat)
        observer.lon = radians(lng)
        sun = ephem.Sun(observer)
        elevation = degrees(sun.alt)
        azimuth = degrees(sun.az)
        return pg.normalize(to_xyz(lat, lng, elevation, azimuth))
    def get_moon(self):
        lat, lng = self.get_lat_lng()
        observer = ephem.Observer()
        observer.lat = radians(lat)
        observer.lon = radians(lng)
        moon = ephem.Moon(observer)
        elevation = degrees(moon.alt)
        azimuth = degrees(moon.az)
        distance = moon.earth_distance * AU
        altitude = distance - EARTH_RADIUS
        return to_xyz(lat, lng, elevation, azimuth, altitude)
    def rotate_satellite(self, position):
        dx, dy, dz = pg.normalize(position)
        rx = atan2(dz, dx) + pi / 2
        ry = asin(dy) - pi / 2
        matrix = pg.Matrix()
        matrix = matrix.rotate((0, 1, 0), rx)
        matrix = matrix.rotate((cos(rx), 0, sin(rx)), -ry)
        return matrix
    def rotate_moon(self, position):
        # TODO: account for libration
        dx, dy, dz = pg.normalize(position)
        rx = atan2(dz, dx) + pi / 2
        ry = asin(dy)
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
        matrix = matrix.perspective(65, self.aspect, ZNEAR, ZFAR)
        self.lines.matrix = matrix
        data = []
        x1, y1, z1 = self.get_position()
        for x2, y2, z2 in self._positions:
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
        self.context.light_direction = self._sun
        matrix = self.rotate_satellite(position)
        self.context.normal_matrix = matrix.inverse().transpose()
        matrix = matrix.translate(position)
        self.context.model_matrix = matrix
        matrix = self.wasd.get_matrix(matrix)
        matrix = matrix.perspective(65, self.aspect, ZNEAR, ZFAR)
        self.context.matrix = matrix
        self.satellite.draw(self.context)
    def draw_earth(self):
        self.earth.camera_position = self.wasd.position
        self.earth.light_direction = self._sun
        matrix = self.wasd.get_matrix()
        matrix = matrix.perspective(65, self.aspect, ZNEAR, ZFAR)
        self.earth.matrix = matrix
        self.earth_sphere.draw(self.earth)
    def draw_moon(self):
        self.moon.camera_position = self.wasd.position
        self.moon.light_direction = self._sun
        position = self.get_moon()
        matrix = self.rotate_moon(position)
        self.moon.normal_matrix = matrix.inverse().transpose()
        matrix = matrix.translate(position)
        self.moon.model_matrix = matrix
        matrix = self.wasd.get_matrix(matrix)
        matrix = matrix.perspective(65, self.aspect, ZNEAR, ZFAR)
        self.moon.matrix = matrix
        self.moon_sphere.draw(self.moon)
    def draw_stars(self):
        matrix = self.wasd.get_matrix(translate=False)
        matrix = matrix.perspective(65, self.aspect, 0.1, 1)
        self.stars.matrix = matrix
        self.stars_sphere.draw(self.stars)
    def draw_text(self):
        w, h = self.size
        record = self.device.record
        if record and record.timestamp:
            self.font.render(record.timestamp.isoformat(), (5, 0))
    def update(self, t, dt):
        # position camera on first gps fix
        lat, lng = self.get_lat_lng()
        if not self.fix and any((lat, lng)):
            camera = to_xyz(lat, lng, 90, 0, ALTITUDE * 2)
            self.wasd.look_at(camera, (0, 0, 0))
            self.fix = True
        # cache some values for the draw step
        self._sun = self.get_sun()
        self._positions = self.get_positions()
    def draw(self):
        self.clear()
        self.draw_stars()
        self.clear_depth_buffer()
        self.draw_earth()
        self.draw_moon()
        for position in self._positions:
            self.draw_satellite(position)
        self.draw_lines()
        self.draw_text()

class EarthProgram(pg.BaseProgram):
    VS = '''
    #version 120

    uniform mat4 matrix;

    attribute vec4 position;
    attribute vec3 normal;
    attribute vec2 uv;

    varying vec3 frag_position;
    varying vec3 frag_normal;
    varying vec2 frag_uv;

    void main() {
        gl_Position = matrix * position;
        frag_position = vec3(position);
        frag_normal = normal;
        frag_uv = uv;
    }
    '''
    FS = '''
    #version 120

    uniform sampler2D day;
    uniform sampler2D night;
    uniform vec3 camera_position;

    uniform vec3 light_direction;
    uniform vec3 ambient_color;
    uniform vec3 light_color;
    uniform float specular_power;
    uniform float specular_multiplier;

    varying vec3 frag_position;
    varying vec3 frag_normal;
    varying vec2 frag_uv;

    void main() {
        float diffuse = max(dot(frag_normal, light_direction), 0.0);
        vec3 day_color = vec3(texture2D(day, frag_uv));
        vec3 night_color = vec3(texture2D(night, frag_uv));
        float pct = 1.0 - pow(1.0 - diffuse, 4.0);
        vec3 color = mix(night_color, day_color, pct);
        float specular = 0.0;
        if (diffuse > 0.0) {
            vec3 camera_vector = normalize(camera_position - frag_position);
            specular = pow(max(dot(camera_vector,
                reflect(-light_direction, frag_normal)), 0.0), specular_power);
        }
        vec3 light = ambient_color + light_color * diffuse;
        vec3 spec = vec3(1.0, 1.0, 0.9) * specular * specular_multiplier;
        gl_FragColor = vec4(min(color * light + spec, vec3(1.0)), 1.0);
    }
    '''

class StarsProgram(pg.BaseProgram):
    VS = '''
    #version 120

    uniform mat4 matrix;

    attribute vec4 position;
    attribute vec2 uv;

    varying vec2 frag_uv;

    void main() {
        gl_Position = matrix * position;
        frag_uv = uv;
    }
    '''
    FS = '''
    #version 120

    uniform sampler2D sampler;

    varying vec2 frag_uv;

    void main() {
        vec3 color = vec3(texture2D(sampler, frag_uv));
        color = pow(color, vec3(2.0));
        color = mix(vec3(0.0), color, 0.5);
        gl_FragColor = vec4(color, 1.0);
    }
    '''

if __name__ == "__main__":
    pg.run(Window)
