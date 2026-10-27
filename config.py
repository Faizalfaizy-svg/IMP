# =====================================================================
#  config.py  -  ALL settings for the robot are in this one file.
#  Pin numbers are BCM GPIO numbers, taken from Figure 1 (updated LiDAR wiring diagram).
#  (The physical header pin number is in the comment next to each one.)
# =====================================================================

# ---------------- L298N motor driver --------------------------------
# ENA / IN1 / IN2 -> OUT1/OUT2 -> LEFT motor
# ENB / IN3 / IN4 -> OUT3/OUT4 -> RIGHT motor
# Number after "=" is the GPIO number. "pin" in the comment is the physical pin.
ENA = 12   # pin 32  (PWM = left motor speed)
IN1 = 17   # pin 11
IN2 = 27   # pin 13
IN3 = 22   # pin 15
IN4 = 5    # pin 29
ENB = 13   # pin 33  (PWM = right motor speed)

PWM_FREQ = 1000      # Hz
MIN_DUTY = 35        # % - below this the motors only hum, so speeds are scaled from here
LEFT_INVERT = False  # set True if the left wheel spins the wrong way
RIGHT_INVERT = False # set True if the right wheel spins the wrong way

DRIVE_SPEED = 60     # normal forward speed in AUTO mode (0-100)
TURN_SPEED = 60      # speed used when spinning on the spot
SLOW_SPEED = 45      # speed when something is getting close
RAMP_PER_SEC = 250    # soft start: speed rises 250 per second (0 -> 60 in ~0.25 s)

# ---------------- RPLIDAR A1 (360 deg LiDAR, USB) --------------------
LIDAR_PORT = "/dev/ttyUSB0"  # the LiDAR's USB adapter board shows up here
LIDAR_BAUD = 115200
LIDAR_ANGLE_OFFSET = 0       # turn the scan so 0 deg = robot front (try 90/180/270)
LIDAR_FLIPPED = False        # True if the LiDAR is mounted upside down
LIDAR_MIN_CM = 12            # ignore anything closer (the robot's own body)
# zones in degrees (0 = front, + = clockwise/right, - = left)
LIDAR_FRONT = (-25, 25)
LIDAR_RIGHT = (26, 90)
LIDAR_LEFT = (-90, -26)

STOP_DIST = 25       # cm - closer than this in front: back up and turn
SLOW_DIST = 60       # cm - closer than this in front: slow down and steer away
SIDE_DIST = 20       # cm - closer than this on a side: steer away from that side

# ---------------- Power: XW LiPo 2S 7.4V 7000 mAh + HW-688 5V 5A buck --
# Battery + -> R1 20k -> MCP3008 CH1 -> R2 10k -> GND   (divides by 3)
BATT_CELLS = 2
BATT_ADC_CHANNEL = 1       # MCP3008 CH1 (CH0 is the microphone)
ADC_VREF = 3.3             # MCP3008 VREF is on 3.3V
BATT_DIVIDER = 3.0         # (R1 + R2) / R2 = (20k + 10k) / 10k
BATT_CAL = 1.0             # fine-tune so the reading matches a multimeter
BATT_FULL_V = 8.4          # 4.20 V per cell
BATT_WARN_V = 7.0          # 3.50 V per cell -> warning, slow down
BATT_CUTOFF_V = 6.6        # 3.30 V per cell -> robot stops (protects the LiPo)
BATT_LOW_SECONDS = 5       # must stay low this long (ignores motor start dips)
LOW_BATT_SPEED_SCALE = 0.7 # drive slower when the battery is LOW

# ---------------- GPS (SparkFun NEO-M9N on UART0) --------------------
GPS_PORT = "/dev/ttyAMA0"   # GPIO14 TXD (pin 8) / GPIO15 RXD (pin 10)
GPS_BAUDS = [38400, 9600]   # NEO-M9N default is 38400; 9600 is tried as backup
WAYPOINT_RADIUS_M = 3.0     # "arrived" when closer than this (metres)
MIN_SPEED_FOR_COURSE = 0.5  # m/s - GPS heading is only trusted above this speed
STEER_GAIN = 0.8            # how hard to steer towards the waypoint

# ---------------- APDS-9960 gesture sensor (I2C1) --------------------
I2C_BUS = 1          # GPIO2 SDA (pin 3) / GPIO3 SCL (pin 5)
APDS_ADDR = 0x39
# What each hand swipe does. If UP/DOWN or LEFT/RIGHT feel swapped
# (depends how the sensor is mounted), just swap the words here.
GESTURE_ACTIONS = {
    "UP": "auto",        # start autonomous obstacle avoidance
    "DOWN": "stop",      # stop the robot
    "LEFT": "manual",    # back to app control
    "RIGHT": "waypoint", # drive to the saved GPS waypoint
}

# ---------------- MAX9814 mic via MCP3008 (SPI0) ---------------------
MIC_SPI_BUS = 0      # MOSI pin 19, MISO pin 21, SCLK pin 23
MIC_SPI_DEV = 0      # CE0 pin 24
MIC_CHANNEL = 0      # mic OUT -> MCP3008 CH0
CLAP_THRESHOLD = 400 # peak-to-peak level (0-1023). Run microphone.py to tune it.
CLAP_ACTION = "stop" # a loud clap = emergency stop

# ---------------- Raspberry Pi AI Camera (IMX500) --------------------
CAMERA_ENABLED = True
CAMERA_MODEL = "/usr/share/imx500-models/imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk"
CAMERA_SIZE = (640, 480)
DETECT_THRESHOLD = 0.55   # min confidence for a detection
CAM_BLOCK_HEIGHT = 0.40   # object taller than 40% of the image = close
CAM_CENTRE_WIDTH = 0.40   # middle 40% of the image = "in front of the robot"

# ---------------- Web server for the phone app ----------------------
WEB_PORT = 5000
MANUAL_TIMEOUT = 1.0  # s - stop if no command arrives for this long (0 = never)
LOOP_HZ = 20          # control loop speed
