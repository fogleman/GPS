from __future__ import division

from math import sin, cos, tan, asin, atan, radians, degrees
import datetime

Z_TABLE = [
    -0.5,
    30.5,
    58.5,
    89.5,
    119.5,
    150.5,
    180.5,
    211.5,
    242.5,
    272.5,
    303.5,
    333.5,
]

def leap(year):
    if year % 400 == 0:
        return True
    if year % 100 == 0:
        return False
    if year % 4 == 0:
        return True
    return False

def quad(x):
    return x // 90

def _sin(x):
    return sin(radians(x))

def _cos(x):
    return cos(radians(x))

def _tan(x):
    return tan(radians(x))

def _asin(x):
    return degrees(asin(x))

def _atan(x):
    return degrees(atan(x))

def sun(latitude, longitude, timestamp=None):
    timestamp = timestamp or datetime.datetime.utcnow()
    y = timestamp.year - 1900
    z = Z_TABLE[timestamp.month - 1]
    if timestamp.month in (1, 2) and leap(timestamp.year):
        z -= 1
    k = timestamp.day
    ut = timestamp.hour + timestamp.minute / 60 + timestamp.second / 3600
    d = int(365.25 * y) + z + k + ut / 24
    t = d / 36525
    l = (279.697 + 36000.769 * t) % 360
    m = (358.476 + 35999.050 * t) % 360
    epsilon = 23.452 - 0.013 * t
    lamb = l + (1.919 - 0.005 * t) * _sin(m) + 0.020 * _sin(2 * m)
    alpha = _atan(_tan(lamb) * _cos(epsilon))
    alpha = (alpha + (quad(lamb) - quad(alpha)) * 90 + 360) % 360
    delta = _asin(_sin(lamb) * _sin(epsilon))
    ha = l - alpha + 180 + 15 * ut + longitude
    alt = _asin(
        _sin(latitude) * _sin(delta) +
        _cos(latitude) * _cos(delta) * _cos(ha))
    az = _atan(_sin(ha) /
        (_cos(ha) * _sin(latitude) - _tan(delta) * _cos(latitude)))
    az = (az + 360) % 360
    return (alt, az)

if __name__ == '__main__':
    '''
    (a) alt = 49.8, az =  67.5
    (b) alt = 36.8, az = 335.5
    (c) alt = 17.1, az = 277.5
    '''
    print sun(-33.92, 18.37, datetime.datetime(1995, 2, 15, 8, 30))
    print sun(-29.20, 26.12, datetime.datetime(1996, 5, 20, 11, 35))
    print sun(-26.25, 28.00, datetime.datetime(1997, 9, 25, 14, 45))
