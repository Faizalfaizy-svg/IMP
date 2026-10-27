import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle

C = dict(bat="#c62828", v5="#ef6c00", v33="#ad1457", gnd="#212121", mot="#00897b",
         uart="#2e7d32", i2c="#6a1b9a", spi="#6d4c41", ana="#f9a825", usb="#1565c0")
NAVY = "#1a2a4a"
BOX_FC, BOX_EC = "#e8f0fb", "#2f5d8a"

fig = plt.figure(figsize=(16, 11.2), dpi=150)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 160)
ax.set_ylim(0, 112)
ax.axis("off")
fig.patch.set_facecolor("white")


def box(x, y, w, h, title, sub=None, fc=BOX_FC, ec=BOX_EC, tsize=13, tdy=2.4):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2",
                                fc=fc, ec=ec, lw=2.2, zorder=2))
    ax.text(x + w / 2, y + h - tdy, title, ha="center", va="center", fontsize=tsize,
            fontweight="bold", color=NAVY, zorder=5)
    if sub:
        ax.text(x + w / 2, y + h - tdy - 2.6, sub, ha="center", va="center",
                fontsize=9.5, color="#444", zorder=5)


def pin(x, y, label, side, col, fs=9):
    ax.add_patch(Circle((x, y), 0.45, fc="white", ec=col, lw=1.6, zorder=6))
    if side == "in_left":      # label inside the box, to the right of the pin
        ax.text(x + 1.0, y, label, ha="left", va="center", fontsize=fs, color="#222", zorder=6)
    elif side == "in_right":   # label inside the box, to the left of the pin
        ax.text(x - 1.0, y, label, ha="right", va="center", fontsize=fs, color="#222", zorder=6)


def wire(pts, col, lw=2.2, z=3):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=col, lw=lw, solid_capstyle="round", solid_joinstyle="round", zorder=z)


def dot(x, y, col):
    ax.add_patch(Circle((x, y), 0.55, fc=col, ec=col, zorder=7))


ax.text(80, 108.5, "Figure 1: Raspberry Pi 5 Autonomous Robot (RPLIDAR A1) - Wiring / Connection Diagram",
        ha="center", va="center", fontsize=17, fontweight="bold", color=NAVY)

# ---------------- power side ----------------
RED_X, BLK_X = 5, 12
box(22, 92, 22, 11, "XW LiPo 2S 7000mAh", "7.4V nom, 6.6V cut-off", fc="#fbe3e3", ec="#b23a3a", tsize=12)
ax.text(19.3, 99.9, "+", fontsize=15, color=C["bat"], fontweight="bold", va="center")
ax.text(19.5, 95.9, "-", fontsize=15, color=NAVY, fontweight="bold", va="center")
wire([(22, 98.6), (RED_X, 98.6), (RED_X, 37)], C["bat"], 2.6)
wire([(22, 94.6), (BLK_X, 94.6), (BLK_X, 20)], C["gnd"], 2.6)
ax.add_patch(Rectangle((RED_X - 1.2, 83), 2.4, 6, fc="white", ec=C["bat"], lw=2, zorder=4))
ax.text(RED_X + 2.2, 86, "F1\n7.5A", fontsize=11, fontweight="bold", va="center")
ax.plot([RED_X, RED_X], [80, 79.2], color="white", lw=4, zorder=4)
ax.add_patch(Circle((RED_X, 80), 0.6, fc="white", ec=C["bat"], lw=1.8, zorder=5))
ax.add_patch(Circle((RED_X, 76.5), 0.6, fc="white", ec=C["bat"], lw=1.8, zorder=5))
ax.plot([RED_X, RED_X], [77.1, 79.4], color="white", lw=5, zorder=4)
ax.plot([RED_X, RED_X + 2.2], [77.1, 79.6], color=C["bat"], lw=2, zorder=5)
ax.text(RED_X + 3, 78, "SW1", fontsize=11, fontweight="bold", va="center")

# 5V 5A buck
box(22, 57, 22, 15, "HW-688 Buck", "5V 5A step-down")
pin(22, 63, "IN+", "in_left", C["bat"]); pin(22, 60, "IN-", "in_left", C["gnd"])
ax.text(23, 58.2, "IN side = 100uF 50V cap", fontsize=7.5, color="#555", zorder=6)
ax.add_patch(Rectangle((40.2, 61.6), 3.8, 2.8, fc="#cfd8dc", ec="#455a64", lw=1.4, zorder=5))
ax.text(39.6, 63, "USB-A 5V", ha="right", va="center", fontsize=9, zorder=6); pin(44, 60, "OUT- GND", "in_right", C["gnd"])
wire([(RED_X, 63), (22, 63)], C["bat"], 2.4); dot(RED_X, 63, C["bat"])
wire([(BLK_X, 60), (22, 60)], C["gnd"], 2.4); dot(BLK_X, 60, C["gnd"])

# L298N
box(22, 17, 22, 35, "L298N Motor Driver", "Dual H-bridge", tsize=12.5)
pin(22, 40, "VS (12V in)", "in_left", C["bat"]); pin(22, 37, "GND", "in_left", C["gnd"])
wire([(RED_X, 40), (22, 40)], C["bat"], 2.4); dot(RED_X, 40, C["bat"])
wire([(BLK_X, 37), (22, 37)], C["gnd"], 2.4); dot(BLK_X, 37, C["gnd"])
wire([(BLK_X, 38), (BLK_X, 37)], C["gnd"], 2.6)
ax.text(23, 31.5, "5V-EN jumper:", fontsize=8.5, color="#555")
ax.text(23, 29.5, "KEEP ON (7.4V supply)", fontsize=8.5, color="#2e7d32", fontweight="bold")
ax.text(23, 26.5, "ENA/ENB jumpers:", fontsize=8.5, color="#555")
ax.text(23, 24.5, "REMOVED (PWM)", fontsize=8.5, color="#c62828", fontweight="bold")
ax.text(27, 18.6, "OUT1/2", fontsize=8.5, ha="center"); ax.text(39, 18.6, "OUT3/4", fontsize=8.5, ha="center")

drv = ["ENA", "IN1", "IN2", "IN3", "IN4", "ENB"]
drv_y = [47.5, 45.5, 43.5, 41.5, 39.5, 37.5]
for n, y in zip(drv, drv_y):
    pin(44, y, n, "in_right", C["mot"])

# motors
box(22, 3, 10, 9, "Left", "drive motor", fc="#e8f5e9", ec="#2e7d32", tsize=10.5, tdy=3)
box(34, 3, 10, 9, "Right", "drive motor", fc="#e8f5e9", ec="#2e7d32", tsize=10.5, tdy=3)
for x in (26, 28):
    wire([(x, 17), (x, 12)], C["bat"], 2)
for x in (38, 40):
    wire([(x, 17), (x, 12)], C["bat"], 2)

# ---------------- Raspberry Pi ----------------
PI_X0, PI_X1, PI_Y0, PI_Y1 = 58, 116, 22, 90
ax.add_patch(FancyBboxPatch((PI_X0, PI_Y0), PI_X1 - PI_X0, PI_Y1 - PI_Y0,
                            boxstyle="round,pad=0,rounding_size=1.5",
                            fc="#fde3b0", ec="#b8781a", lw=2.6, zorder=2))
ax.text(87, 33, "Raspberry Pi 5 (8GB)", ha="center", fontsize=20, fontweight="bold", color=NAVY, zorder=5)
ax.text(87, 29.5, "Main controller - autonomous navigation (Python 3)", ha="center",
        fontsize=10, color="#333", zorder=5)
ax.text(87, 26.5, "40-pin header: BCM GPIO number (physical pin)", ha="center",
        fontsize=9, color="#666", style="italic", zorder=5)

# battery sense divider (R1 20k / R2 10k)
ax.add_patch(Rectangle((RED_X - 1, 31), 2, 6, fc="white", ec=C["bat"], lw=1.8, zorder=4))
wire([(RED_X, 31), (RED_X, 26.5)], C["ana"], 2.2)
ax.add_patch(Rectangle((RED_X - 1, 21), 2, 5.5, fc="white", ec=C["gnd"], lw=1.8, zorder=4))
wire([(RED_X, 21), (RED_X, 20), (BLK_X, 20)], C["gnd"], 2.2); dot(BLK_X, 20, C["gnd"])
dot(RED_X, 28.5, C["ana"])
wire([(RED_X, 28.5), (13.3, 28.5)], C["ana"], 2.2)
ax.text(3.6, 34, "R1\n20k", ha="right", va="center", fontsize=8.5, fontweight="bold")
ax.text(3.6, 23.7, "R2\n10k", ha="right", va="center", fontsize=8.5, fontweight="bold")
ax.text(13.6, 28.5, "VBAT_SENSE\n(to MCP3008\n CH1)", va="center", fontsize=7.5, color="#a07800", fontweight="bold")

# Pi power in
ax.add_patch(Rectangle((PI_X0, 83.4), 3.6, 3.2, fc="#cfd8dc", ec="#455a64", lw=1.4, zorder=5))
ax.text(PI_X0 + 4.4, 85, "USB-C power in", ha="left", va="center", fontsize=9, zorder=6)
pin(PI_X0, 82, "GND (6)", "in_left", C["gnd"])
wire([(44, 63), (54.5, 63), (54.5, 85), (PI_X0, 85)], C["v5"], 4)
wire([(44, 60), (56, 60), (56, 82), (PI_X0, 82)], C["gnd"], 2.4)
ax.text(45, 87.2, "USB-A -> USB-C cable", color=C["v5"], fontsize=8.5, fontweight="bold")

# motor control pins
pi_mot = ["GPIO12 (32)", "GPIO23 (16)", "GPIO24 (18)", "GPIO27 (13)", "GPIO22 (15)", "GPIO13 (33)"]
pi_mot_y = [57, 54.5, 52, 49.5, 47, 44.5]
jog = [45, 46.2, 47.4, 48.6, 49.8, 51.0]
for (yd, yp, jx, lab) in zip(drv_y, pi_mot_y, jog, pi_mot):
    wire([(44, yd), (jx + 1.5, yd), (jx + 1.5, yp), (PI_X0, yp)], C["mot"], 2)
    pin(PI_X0, yp, lab, "in_left", C["mot"])
ax.text(45, 34.3, "Motor control", color=C["mot"], fontsize=9.5, fontweight="bold")

# right side pins
R = PI_X1
right_pins = [("3V3 (1, 17)", 85, C["v33"]), ("GND (9, 14, 25)", 82, C["gnd"]),
              ("GPIO14 TXD (8)", 77, C["uart"]), ("GPIO15 RXD (10)", 75, C["uart"]),
              ("GPIO2 SDA (3)", 66, C["i2c"]), ("GPIO3 SCL (5)", 64, C["i2c"]),
              ("GPIO10 MOSI (19)", 51, C["spi"]), ("GPIO9 MISO (21)", 49, C["spi"]),
              ("GPIO11 SCLK (23)", 47, C["spi"]), ("GPIO8 CE0 (24)", 45, C["spi"])]
for lab, y, col in right_pins:
    pin(R, y, lab, "in_right", col)

# USB port on the Pi bottom edge
ax.add_patch(Rectangle((99, 22), 12, 3.2, fc="#cfd8dc", ec="#455a64", lw=1.6, zorder=5))
ax.text(105, 23.6, "USB-A port", ha="center", va="center", fontsize=8.5, zorder=6)

# camera
box(70, 95, 34, 9, "Raspberry Pi AI Camera", "Sony IMX500 (CSI-2)", tsize=12.5)
wire([(87, 95), (87, PI_Y1)], "#9e9e9e", 6)
ax.text(89, 92.4, "CSI-2 ribbon -> CAM/DISP 0 or 1 (22-pin port)", fontsize=9, color="#333")

# ---------------- right column ----------------
BX = 129
V33_X, GND_X = 120.5, 123
wire([(R, 85), (V33_X, 85), (V33_X, 24.5)], C["v33"], 2.4)
wire([(R, 82), (GND_X, 82), (GND_X, 22)], C["gnd"], 2.4)
dot(V33_X, 85, C["v33"]); dot(GND_X, 82, C["gnd"])
ax.text(121.5, 89.3, "3V3 rail", ha="right", color=C["v33"], fontsize=9, fontweight="bold")
ax.text(122.3, 89.3, "GND rail", color=C["gnd"], fontsize=9, fontweight="bold")


def module(y0, h, title, sub, pins):
    box(BX, y0, 29, h, title, sub, tsize=12)
    for lab, y, col in pins:
        pin(BX, y, lab, "in_left", col)


def rail_to(y, which):
    x = V33_X if which == "v33" else GND_X
    wire([(x, y), (BX, y)], C[which], 2)
    dot(x, y, C[which])


def sig(y_from, y_to, col, jx=126.5):
    wire([(R, y_from), (jx, y_from), (jx, y_to), (BX, y_to)], col, 2)


# GPS
module(72, 16, "GPS Module", "SparkFun NEO-M9N (GNSS)",
       [("3V3", 85, C["v33"]), ("GND", 82, C["gnd"]), ("RX", 79, C["uart"]), ("TX", 76.5, C["uart"])])
rail_to(85, "v33"); rail_to(82, "gnd")
sig(77, 79, C["uart"]); sig(75, 76.5, C["uart"], 125.5)
ax.text(115, 79.4, "UART0", ha="right", color=C["uart"], fontsize=8.5, fontweight="bold")

# Gesture
module(56, 14, "Gesture Sensor", "SparkFun APDS-9960",
       [("SDA", 66, C["i2c"]), ("SCL", 64, C["i2c"]), ("3V3", 61, C["v33"]), ("GND", 58.5, C["gnd"])])
rail_to(61, "v33"); rail_to(58.5, "gnd")
sig(66, 66, C["i2c"]); sig(64, 64, C["i2c"])
ax.text(115, 68.4, "I2C1", ha="right", color=C["i2c"], fontsize=8.5, fontweight="bold")

# MCP3008
module(33.3, 20.7, "MCP3008 ADC", "10-bit, SPI",
       [("DIN", 51, C["spi"]), ("DOUT", 49, C["spi"]), ("CLK", 47, C["spi"]), ("CS", 45, C["spi"]),
        ("VDD+VREF", 42.5, C["v33"]), ("AGND+DGND", 40.5, C["gnd"]), ("CH0", 37, C["ana"]), ("CH1  <- VBAT_SENSE (batt / 3)", 35, C["ana"])])
rail_to(42.5, "v33"); rail_to(40.5, "gnd")
for yy in (51, 49, 47, 45):
    sig(yy, yy, C["spi"])
ax.text(115, 53.4, "SPI0", ha="right", color=C["spi"], fontsize=8.5, fontweight="bold")

# Microphone
module(17, 15, "Microphone", "Adafruit MAX9814",
       [("OUT", 26.5, C["ana"]), ("VDD", 24.5, C["v33"]), ("GND", 22, C["gnd"])])
rail_to(24.5, "v33"); rail_to(22, "gnd")
wire([(BX, 26.5), (127.6, 26.5), (127.6, 37), (BX, 37)], C["ana"], 2)
ax.text(147, 18.6, "GAIN: float = 60 dB", ha="center", fontsize=8, color="#555")
ax.text(126.4, 31.5, "analogue", color="#a07800", fontsize=8, fontweight="bold", rotation=90, ha="center", va="center")

# ---------------- RPLIDAR ----------------
box(58, 3, 30, 12, "Slamtec RPLIDAR A1", "360 deg LiDAR, 0.15-12 m", fc="#e3f2fd", ec=C["usb"], tsize=12)
box(93, 3, 22, 12, "RPLIDAR USB", "adapter board (CP2102)", fc="#e3f2fd", ec=C["usb"], tsize=10.5)
wire([(88, 9), (93, 9)], C["usb"], 3)
ax.text(90.5, 10.2, "7-pin", ha="center", fontsize=7.5, color=C["usb"])
wire([(105, 15), (105, 22)], C["usb"], 3.2)
ax.text(106, 18.6, "micro-USB -> USB-A\n/dev/ttyUSB0 (data + 5V)", fontsize=8, color=C["usb"], va="center")
ax.text(73, 1.2, "Mount on top, clear 360 deg view, arrow/0 deg facing robot front", ha="center",
        fontsize=8, color="#555")

# ---------------- notes + key ----------------
ax.text(1, 15.6, "F1 = 7.5A fuse", fontsize=9.5, fontweight="bold", color="#333")
ax.text(1, 13.6, "SW1 = master switch", fontsize=9.5, fontweight="bold", color="#333")
for i, line in enumerate(["All grounds are common.", "HW-688 output must read",
                          "5.0-5.2V before the Pi", "is connected. Charge the",
                          "LiPo with a balance charger."]):
    ax.text(1, 11.3 - i * 1.8, line, fontsize=8.2, color="#444")

KX, KY = 118, 1.5
ax.add_patch(FancyBboxPatch((KX, KY), 41, 13.5, boxstyle="round,pad=0,rounding_size=0.8",
                            fc="white", ec="#999", lw=1.2, zorder=2))
ax.text(KX + 1.5, KY + 12, "Wire colour key", fontsize=10, fontweight="bold", zorder=5)
items = [("7.4V battery", "bat"), ("5V", "v5"), ("3.3V", "v33"), ("GND", "gnd"), ("Motor control", "mot"),
         ("UART", "uart"), ("I2C", "i2c"), ("SPI", "spi"), ("Analogue / batt sense", "ana"), ("USB (LiDAR)", "usb")]
for i, (lab, k) in enumerate(items):
    col, row = i // 5, i % 5
    x = KX + 1.5 + col * 20
    y = KY + 9.8 - row * 2.1
    wire([(x, y), (x + 4, y)], C[k], 3, z=5)
    ax.text(x + 5, y, lab, va="center", fontsize=8.5, zorder=5)

fig.savefig("/home/claude/rc_robot/wiring_diagram_lidar.png", dpi=150, facecolor="white")
print("saved")
