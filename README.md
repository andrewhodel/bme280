requires https://pypi.org/project/RPi.bme280/ with python 3

# install the required libraries
sudo pip3 install RPi.bme280
# also install as root to allow the program to run from /etc/rc.local
sudo su
pip3 install RPi.bme280

# bme280 to raspberry pi wiring

## raspberry pi zero w v1.1

Look at the bottom side of the board with the HDMI port on the left side.

The main header pins are two rows that span the length of the board and are next to one another on the right side of the board.

The bottom pin on the left row is a square and provides +3.3vdc.

blue	GPIO 9	SCL 1	**	ground, black
green	GPIO 8	SDA 1	**
white	+3.3vdc		**
