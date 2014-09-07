## GPS

Real-time 3D renderings of GPS satellite locations.

http://www.michaelfogleman.com/gps/

![Screenshot](http://www.michaelfogleman.com/static/img/project/gps/gps.png)

### Hardware

[GlobalSat BU-353-S4 USB GPS Receiver](http://www.amazon.com/GlobalSat-BU-353-S4-USB-Receiver-Black/dp/B008200LHW/)

### Dependencies

    pip install ephem

`pg` isn't in pip-installable yet! :(

    brew tap homebrew/versions
    brew install glfw3
    git clone https://github.com/fogleman/pg.git
    cd pg
    python setup.py install
