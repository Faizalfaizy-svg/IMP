# RC Robot – Raspberry Pi 5 + RPLIDAR A1 (code for the updated Figure 1)

## Files
| File | What it does | Test it alone? |
|---|---|---|
| `config.py` | All pins and settings (change things here only) | – |
| `gpio.py` | Finds the right GPIO chip by itself (gpiochip15 on this Pi) | – |
| `motors.py` | L298N, both motors, speed control (PWM) | Yes |
| `lidar.py` | RPLIDAR A1 360° LiDAR on USB (front / left / right zones) | Yes |
| `gps.py` | NEO-M9N GPS over UART | Yes (outside) |
| `gesture.py` | APDS-9960 hand swipes | Yes |
| `microphone.py` | MAX9814 via MCP3008, clap = stop | Yes |
| `camera.py` | AI Camera (IMX500) object detection + video | Yes |
| `battery.py` | LiPo voltage (MCP3008 CH1) + Pi 5V supply check | Yes |
| `navigation.py` | Autonomous brain (avoid obstacles, go to GPS point) | – |
| `main.py` | **Runs everything** + web server for the phone | **Run this** |
| `web/index.html` | The control dashboard (radar, camera, drive pad, status) | – |
| `both_test.py` | Quick check: both wheels forward, then backward | Yes |
| `setup.sh` | Installs libraries, turns on I2C/SPI/UART (run once) | – |

## First time
1. Copy the whole `rc_robot` folder to the Pi (e.g. Desktop).
2. In Thonny: Tools → Open system shell, then:
   `cd ~/Desktop/rc_robot && bash setup.sh`
3. `sudo reboot`

## Testing order (one at a time, in Thonny → Run)
`battery.py` → `motors.py` → `lidar.py` → `gesture.py` → `microphone.py` → `camera.py` → `gps.py` → `main.py`

## Phone control
Run `main.py`. The Shell shows `http://<pi-ip>:5000`. Open it on the phone (same Wi-Fi).

| Command | URL |
|---|---|
| Drive | `/cmd/forward` `/cmd/backward` `/cmd/left` `/cmd/right` `/cmd/stop` (add `?speed=70`) |
| Tank drive | `/drive?l=60&r=60` (-100..100 each) |
| Mode | `/mode/manual` `/mode/auto` `/mode/waypoint` `/mode/stop` |
| GPS target | `/waypoint?lat=51.7520&lon=-0.2400` or `/waypoint?here=1` |
| Video (MJPEG) | `/video` |
| Status (JSON) | `/status` |
| LiDAR scan (JSON, 360 values in cm) | `/scan` |

In manual mode the robot stops if no command arrives for 1 s (safety). The web page
repeats the command while a button is held. If your app sends only one command per
press, set `MANUAL_TIMEOUT = 0` in `config.py`.

## Gestures and sound
- Swipe UP = auto, DOWN = stop, LEFT = manual, RIGHT = waypoint (change in `config.py`)
- Loud clap = stop (tune `CLAP_THRESHOLD` using `microphone.py`)

## LiDAR notes
- Plug the RPLIDAR A1 USB adapter into any Pi USB port. It shows up as `/dev/ttyUSB0`.
- Run `lidar.py` and put a hand in front of the robot. **Front** should drop.
  If Left or Right drops instead, change `LIDAR_ANGLE_OFFSET` in `config.py` (try 90, 180, 270).
- If the LiDAR stops working, AUTO and WAYPOINT modes pause the motors (safety).
- The web page shows a live radar view of the scan.

## Power (XW LiPo 2S 7.4V 7000 mAh + HW-688)
- HW-688 **input** = blue terminal next to the 100µF 50V capacitor (battery, after F1 + SW1).
- HW-688 **output** = its USB-A port → USB-A to USB-C cable → Pi 5 power port.
- One extra wire: HW-688 output GND (blue terminal by the 470µF cap) → Pi GND (pin 6), so the Pi and L298N share ground.
- Before plugging in the Pi, check the HW-688 output with a multimeter: 5.0–5.2 V.
- Battery sense: battery + → **R1 20k** → MCP3008 **CH1** → **R2 10k** → GND.
- Battery ≤ 7.0 V for 5 s → warning and the robot drives slower.
- Battery ≤ 6.6 V for 5 s → robot stops and stays stopped. Charge with a LiPo **balance** charger.
- Fuse F1 = 7.5 A.

## Camera not found?
If the dashboard says "Camera off - No camera found":
1. Power off the Pi. Re-seat the ribbon cable at both ends (camera and Pi CAM/DISP port).
   The metal contacts must face the right way (towards the board on the Pi 5 connector).
2. Power on and run in a terminal:  `rpicam-hello --list-cameras`
3. It should list `imx500`. If it lists nothing, the cable or port is the problem.
4. If it lists the camera but AI detection fails, run:  `sudo apt install -y imx500-all` and reboot.

## Battery shows "Check wiring" or 9.9 V?
9.9 V is the highest number the ADC can show, so the MCP3008 is either not answering
(check DIN/DOUT/CLK/CS, 3.3V and GND) or CH1 gets more than 3.3 V (R1 and R2 swapped).
