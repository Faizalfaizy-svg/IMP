# =====================================================================
#  main.py  -  RUN THIS to start the whole robot.
#
#  Modes:
#    manual   - driven from the phone (Droid Vision / web page)
#    auto     - drives by itself and avoids obstacles
#    waypoint - drives to a GPS point and avoids obstacles on the way
#    stop     - motors off
#
#  Phone: connect to the same Wi-Fi and open  http://<pi-ip>:5000
#  Video stream for the app:                  http://<pi-ip>:5000/video
# =====================================================================
import os
import socket
import threading
import time

from flask import Flask, Response, jsonify, request, send_from_directory

import config
import gpio
from motors import Motors
from navigation import Navigator


PROBLEMS = {}   # part name -> why it did not start (shown on the web page)


def try_start(name, make):
    """Start a sensor. If it is missing, print a warning and carry on."""
    try:
        obj = make()
        obj.start()
        print("[ok]   %s" % name)
        return obj
    except Exception as e:
        print("[skip] %s: %s" % (name, e))
        PROBLEMS[name] = str(e)
        return None


class Robot:
    def __init__(self):
        self.motors = Motors()
        self.nav = Navigator()
        self.lock = threading.Lock()
        self.mode = "stop"
        self.reason = "starting"
        self.manual = (0, 0)
        self.manual_time = 0.0
        self.waypoint = None
        self.last_event = ""

        self.lidar = None
        try:
            from lidar import Lidar
            self.lidar = try_start("RPLIDAR A1", Lidar)
        except ImportError as e:
            print("[skip] RPLIDAR A1: %s" % e)

        self.gps = None
        try:
            from gps import GPS
            self.gps = try_start("GPS", GPS)
        except ImportError as e:
            print("[skip] GPS: %s" % e)

        self.gesture = None
        try:
            from gesture import GestureSensor
            self.gesture = try_start("gesture sensor",
                                     lambda: GestureSensor(on_gesture=self.on_gesture))
        except ImportError as e:
            print("[skip] gesture sensor: %s" % e)

        self.mic = None
        try:
            from microphone import Microphone
            self.mic = try_start("microphone", lambda: Microphone(on_clap=self.on_clap))
        except ImportError as e:
            print("[skip] microphone: %s" % e)

        self.battery = None
        try:
            from battery import Battery
            self.battery = try_start("battery monitor", Battery)
        except ImportError as e:
            print("[skip] battery monitor: %s" % e)

        self.cam = None
        if config.CAMERA_ENABLED:
            try:
                from camera import Camera
                self.cam = try_start("AI camera", Camera)
            except ImportError as e:
                print("[skip] AI camera: %s" % e)

        self.running = True
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    # ---------- events from sensors / app ----------
    def set_mode(self, m, source="app"):
        if m not in ("manual", "auto", "waypoint", "stop"):
            return False
        with self.lock:
            self.mode = m
            self.manual = (0, 0)
            self.nav.reset()
            self.last_event = "%s -> %s" % (source, m)
        print("[mode] %s (from %s)" % (m, source))
        return True

    def on_gesture(self, g):
        action = config.GESTURE_ACTIONS.get(g)
        if action:
            self.set_mode(action, "gesture " + g)

    def on_clap(self, level):
        self.set_mode(config.CLAP_ACTION, "clap (%d)" % level)

    def drive_manual(self, left, right):
        with self.lock:
            if self.mode != "manual":
                self.mode = "manual"
                self.nav.reset()
            self.manual = (int(left), int(right))
            self.manual_time = time.time()

    def lidar_ok(self):
        return bool(self.lidar and self.lidar.ok())

    def distances(self):
        if self.lidar_ok():
            return dict(self.lidar.distances)
        return {"front": 1200.0, "left": 1200.0, "right": 1200.0}

    # ---------- main control loop ----------
    def loop(self):
        period = 1.0 / config.LOOP_HZ
        while self.running:
            with self.lock:
                mode, manual, mt, wp = self.mode, self.manual, self.manual_time, self.waypoint
            d = self.distances()

            if mode == "manual":
                l, r = manual
                if config.MANUAL_TIMEOUT and time.time() - mt > config.MANUAL_TIMEOUT:
                    l, r, why = 0, 0, "manual - waiting for command"
                else:
                    why = "manual"
                # safety: do not drive forward into something
                if (l + r) > 0 and self.lidar_ok() and d["front"] < config.STOP_DIST:
                    l, r, why = 0, 0, "manual - blocked in front (%.0f cm)" % d["front"]
            elif mode in ("auto", "waypoint") and not self.lidar_ok():
                # safety: never drive by itself without the LiDAR
                l, r, why = 0, 0, "LiDAR not working - auto driving paused"
            elif mode in ("auto", "waypoint"):
                l, r, why = self.nav.step(mode, d, self.cam, self.gps, wp)
                if self.nav.arrived:
                    self.set_mode("stop", "waypoint reached")
            else:
                l, r, why = 0, 0, "stopped"

            # ---- battery protection ----
            b = self.battery
            if b and b.critical:
                if mode != "stop":
                    self.set_mode("stop", "battery empty")
                l, r = 0, 0
                why = "BATTERY EMPTY (%.2f V) - charge the LiPo, then restart" % (b.volts or 0)
            elif b and b.low and (l or r):
                l = int(l * config.LOW_BATT_SPEED_SCALE)
                r = int(r * config.LOW_BATT_SPEED_SCALE)
                why += "  [battery low %.2f V - slow]" % b.volts

            self.motors.drive(l, r)
            self.reason = why
            time.sleep(period)

    def status(self):
        g = self.gps
        return {
            "mode": self.mode,
            "reason": self.reason,
            "left": self.motors.left,
            "right": self.motors.right,
            "lidar": self.lidar_ok(),
            "distances": {k: round(v, 1) for k, v in self.distances().items()},
            "gps": {
                "fix": bool(g and g.has_fix()),
                "lat": g.lat if g else None,
                "lon": g.lon if g else None,
                "sats": g.sats if g else 0,
                "speed": round(g.speed_mps, 2) if g else 0,
                "heading": g.heading() if g else None,
            },
            "waypoint": self.waypoint,
            "camera": {
                "on": self.cam is not None,
                "error": PROBLEMS.get("AI camera"),
                "blocked": bool(self.cam and self.cam.blocked),
                "objects": [n for n, s, b in self.cam.detections] if self.cam else [],
            },
            "gesture": self.gesture.last if self.gesture else None,
            "mic_level": self.mic.level if self.mic else None,
            "mic_ok": bool(self.mic and self.mic.connected),
            "limits": {"stop": config.STOP_DIST, "slow": config.SLOW_DIST,
                       "side": config.SIDE_DIST},
            "speed_default": config.DRIVE_SPEED,
            "battery": self.battery.status() if self.battery else None,
            "last_event": self.last_event,
            "problems": PROBLEMS,
        }

    def shutdown(self):
        self.running = False
        time.sleep(0.1)
        self.motors.close()
        time.sleep(0.1)
        for part in (self.lidar, self.gps, self.gesture, self.mic, self.battery, self.cam):
            if part:
                try:
                    part.stop()
                except Exception:
                    pass
        gpio.close()


# =====================================================================
#  Web server (Flask) - used by Droid Vision / any phone browser
# =====================================================================
app = Flask(__name__)
robot = None

COMMANDS = {
    "forward": lambda s: (s, s),
    "backward": lambda s: (-s, -s),
    "left": lambda s: (-s, s),
    "right": lambda s: (s, -s),
    "forward_left": lambda s: (s // 3, s),
    "forward_right": lambda s: (s, s // 3),
    "stop": lambda s: (0, 0),
}


@app.route("/cmd/<name>")
def cmd(name):
    """Simple commands, e.g.  /cmd/forward   /cmd/left?speed=70   /cmd/stop"""
    name = name.lower()
    if name in ("auto", "manual", "waypoint", "halt"):
        robot.set_mode("stop" if name == "halt" else name)
        return jsonify(ok=True, mode=robot.mode)
    if name not in COMMANDS:
        return jsonify(ok=False, error="unknown command", commands=list(COMMANDS)), 400
    speed = int(request.args.get("speed", config.DRIVE_SPEED))
    l, r = COMMANDS[name](max(0, min(100, speed)))
    robot.drive_manual(l, r)
    return jsonify(ok=True, left=l, right=r)


@app.route("/drive")
def drive():
    """Tank-style:  /drive?l=60&r=60   (each -100..100)"""
    l = int(float(request.args.get("l", 0)))
    r = int(float(request.args.get("r", 0)))
    robot.drive_manual(max(-100, min(100, l)), max(-100, min(100, r)))
    return jsonify(ok=True)


@app.route("/mode/<m>")
def mode(m):
    return jsonify(ok=robot.set_mode(m.lower()), mode=robot.mode)


@app.route("/waypoint")
def waypoint():
    """/waypoint?lat=51.7520&lon=-0.2400   or  /waypoint?here=1 (save current spot)"""
    if request.args.get("here") and robot.gps and robot.gps.has_fix():
        robot.waypoint = (robot.gps.lat, robot.gps.lon)
    elif "lat" in request.args and "lon" in request.args:
        robot.waypoint = (float(request.args["lat"]), float(request.args["lon"]))
    else:
        return jsonify(ok=False, error="give lat & lon, or here=1 with a GPS fix"), 400
    return jsonify(ok=True, waypoint=robot.waypoint)


@app.route("/status")
def status():
    return jsonify(robot.status())


@app.route("/scan")
def scan():
    """360 LiDAR distances in cm (index = degree, 0 = front, 0 = no reading)"""
    return jsonify(robot.lidar.scan_cm() if robot.lidar else [0] * 360)


@app.route("/video")
def video():
    if not robot.cam:
        return "camera offline", 503

    def gen():
        while True:
            frame = robot.cam.jpeg if robot.cam else None
            if frame:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            time.sleep(1 / 15)
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


def my_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "<pi-ip>"


if __name__ == "__main__":
    robot = Robot()
    print("\n=== Robot ready ===")
    print("Open on the phone:  http://%s:%d" % (my_ip(), config.WEB_PORT))
    print("Video stream:       http://%s:%d/video\n" % (my_ip(), config.WEB_PORT))
    try:
        app.run(host="0.0.0.0", port=config.WEB_PORT, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        pass
    finally:
        print("Stopping...")
        robot.shutdown()
