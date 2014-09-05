import datetime
import serial

# Settings
PORT = '/dev/cu.usbserial'
BAUD_RATE = 4800

# Dilution of Precision
DOP_EXCELLENT = 1
DOP_GOOD = 2
DOP_MODERATE = 3
DOP_FAIR = 4
DOP_POOR = 5

DOP_STRING = {
    DOP_EXCELLENT: 'excellent',
    DOP_GOOD: 'good',
    DOP_MODERATE: 'moderate',
    DOP_FAIR: 'fair',
    DOP_POOR: 'poor',
}

# Helper Functions
def to_decimal(value, nsew):
    if not value:
        return None
    a, b = value.split('.')
    degrees = int(a) / 100
    minutes = int(a) % 100
    seconds = 60.0 * int(b) / 10 ** len(b)
    result = degrees + minutes / 60.0 + seconds / 3600.0
    if nsew in 'SW':
        result = -result
    return result

def to_dop(value):
    if value < 2:
        return DOP_EXCELLENT
    if value < 5:
        return DOP_GOOD
    if value < 10:
        return DOP_MODERATE
    if value < 20:
        return DOP_FAIR
    return DOP_POOR

def parse_int(x):
    return int(x) if x else None

def parse_float(x):
    return float(x) if x else None

# Model Objects
class Record(object):
    def __init__(self, **kwargs):
        # $GPRMC...
        # valid fix
        self.valid = kwargs['valid']
        # timestamp of fix
        self.timestamp = kwargs['timestamp']
        # latitude of fix
        self.latitude = kwargs['latitude']
        # longitude of fix
        self.longitude = kwargs['longitude']
        # speed over ground in knots
        self.knots = kwargs['knots']
        # true course in degrees
        self.course = kwargs['course']
        # $GPGSA...
        # mode: 1 = no fix, 2 = 2D, 3 = 3D
        self.mode = kwargs['mode']
        # satellite prns used in position fix
        self.prns = kwargs['prns']
        # 3D position DOP
        self.pdop = kwargs['pdop']
        # horizontal DOP
        self.hdop = kwargs['hdop']
        # vertical DOP
        self.vdop = kwargs['vdop']
        # $GPGGA...
        # fix quality: 0 = invalid, 1 = gps fix, 2 = dgps fix
        self.fix = kwargs['fix']
        # number of satellites
        self.count = kwargs['count']
        # altitude above mean sea level
        self.altitude = kwargs['altitude']
        # geoidal separation: height above WGS84 ellipsoid
        self.separation = kwargs['separation']
    def __repr__(self):
        keys = [
            'valid', 'timestamp', 'latitude', 'longitude', 'knots', 'course',
            'mode', 'prns', 'pdop', 'hdop', 'vdop',
            'fix', 'count', 'altitude', 'separation',
        ]
        rows = ['    %s = %r,' % (key, getattr(self, key)) for key in keys]
        rows = '\n'.join(rows)
        return 'Record(\n%s\n)' % rows

class Satellite(object):
    def __init__(self, prn, elevation, azimuth, snr):
        self.prn = prn
        self.elevation = elevation
        self.azimuth = azimuth
        self.snr = snr
    def __repr__(self):
        return 'Satellite(%r, %r, %r, %r)' % (
            self.prn, self.elevation, self.azimuth, self.snr)

# Device Object
class Device(object):
    def __init__(self, port, baud_rate):
        self.port = serial.Serial(port, baud_rate)
        self.handlers = {
            '$GPGGA': self.on_gga,
            '$GPGSA': self.on_gsa,
            '$GPRMC': self.on_rmc,
            '$GPGSV': self.on_gsv,
        }
        self.gga = None
        self.gsa = None
        self.rmc = None
        self.record = None
        self.gsv = {}
        self.satellites = {}
    def read_line(self):
        while True:
            line = self.port.readline().strip()
            if line.startswith('$'):
                return line
    def parse_line(self):
        line = self.read_line()
        data, checksum = line.split('*')
        tokens = data.split(',')
        command, args = tokens[0], tokens[1:]
        handler = self.handlers.get(command)
        if handler:
            handler(args)
    def on_gga(self, args):
        timestamp = datetime.datetime.strptime(args[0], '%H%M%S.%f').time()
        latitude = to_decimal(args[1], args[2])
        longitude = to_decimal(args[3], args[4])
        fix = parse_int(args[5])
        count = parse_int(args[6])
        hdop = parse_float(args[7])
        altitude = parse_float(args[8])
        separation = parse_float(args[10])
        self.gga = dict(
            timestamp=timestamp,
            latitude=latitude,
            longitude=longitude,
            fix=fix,
            count=count,
            hdop=hdop,
            altitude=altitude,
            separation=separation,
        )
    def on_gsa(self, args):
        mode = parse_int(args[1])
        prns = map(int, filter(None, args[2:14]))
        pdop = parse_float(args[14])
        hdop = parse_float(args[15])
        vdop = parse_float(args[16])
        self.gsa = dict(
            mode=mode,
            prns=prns,
            pdop=pdop,
            hdop=hdop,
            vdop=vdop,
        )
    def on_rmc(self, args):
        if self.gga is None or self.gsa is None:
            return
        valid = args[1] == 'A'
        timestamp = datetime.datetime.strptime(args[8] + args[0],
            '%d%m%y%H%M%S.%f')
        latitude = to_decimal(args[2], args[3])
        longitude = to_decimal(args[4], args[5])
        knots = parse_float(args[6])
        course = parse_float(args[7])
        self.rmc = dict(
            valid=valid,
            timestamp=timestamp,
            latitude=latitude,
            longitude=longitude,
            knots=knots,
            course=course,
        )
        data = {}
        data.update(self.gga)
        data.update(self.gsa)
        data.update(self.rmc)
        record = Record(**data)
        self.on_record(record)
    def on_gsv(self, args):
        count = int(args[0])
        index = int(args[1])
        if index == 1:
            self.gsv = {}
        for i in range(3, len(args), 4):
            data = args[i:i+4]
            if all(data):
                data = map(int, data)
                satellite = Satellite(*data)
                self.gsv[satellite.prn] = satellite
        if index == count:
            self.on_satellites(dict(self.gsv))
    def on_record(self, record):
        self.record = record
        print self.record
        print
        for key in sorted(self.satellites):
            print self.satellites[key]
        print
    def on_satellites(self, satellites):
        self.satellites = satellites

# Main
def main():
    device = Device(PORT, BAUD_RATE)
    while True:
        device.parse_line()

if __name__ == '__main__':
    main()
