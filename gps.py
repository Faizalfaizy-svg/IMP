# =====================================================================
#  gps.py  -  reads the SparkFun NEO-M9N over UART (pyserial + pynmea2).
#  Run this file on its own to TEST the GPS (go outside for a fix).
#
#  Note: the NEO-M9N is a GNSS receiver only (no gyro/compass inside),
#  so the robot's heading comes from the GPS "course over ground",
#  which is only valid while the robot is moving.
# =====================================================================
import math
import threading
import time

import config


def distance_m(lat1, lon1, lat2, lon2):
    """Haversine distance in metres."""
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def bearing_deg(lat1, lon1, lat2, lon2):
    """Compass bearing (0 = north, 90 = east) from point 1 to point 2."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


class GPS(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.lat = None
        self.lon = None
        self.fix = False
        self.sats = 0
        self.speed_mps = 0.0
        self.course = None
        self.last_update = 0.0
        self.running = True
        self.ser = self._open()

    def _open(self):
        import serial
        # try each baud rate until real NMEA sentences come in
        for baud in config.GPS_BAUDS:
            try:
                ser = serial.Serial(config.GPS_PORT, baud, timeout=1)
            except Exception as e:
                raise RuntimeError("Cannot open %s (%s). Is the serial port enabled?"
                                   % (config.GPS_PORT, e))
            end = time.time() + 2.5
            while time.time() < end:
                line = ser.readline().decode("ascii", errors="ignore").strip()
                if line.startswith("$G"):
                    print("[gps] found GPS at %d baud" % baud)
                    return ser
            ser.close()
        raise RuntimeError("No GPS data on %s. Check TX/RX wires (TX->RX, RX->TX)."
                           % config.GPS_PORT)

    def run(self):
        import pynmea2
        while self.running:
            try:
                line = self.ser.readline().decode("ascii", errors="ignore").strip()
                if not line.startswith("$"):
                    continue
                msg = pynmea2.parse(line)
            except Exception:
                continue

            t = getattr(msg, "sentence_type", "")
            if t == "RMC":
                if msg.status == "A":
                    self.lat, self.lon = msg.latitude, msg.longitude
                    self.fix = True
                    self.speed_mps = float(msg.spd_over_grnd or 0) * 0.514444
                    self.course = float(msg.true_course) if msg.true_course else None
                    self.last_update = time.time()
                else:
                    self.fix = False
            elif t == "GGA":
                try:
                    self.sats = int(msg.num_sats or 0)
                    if int(msg.gps_qual or 0) == 0:
                        self.fix = False
                except ValueError:
                    pass

    def has_fix(self):
        return self.fix and (time.time() - self.last_update) < 3

    def heading(self):
        """Heading in degrees, or None if not moving fast enough to know."""
        if self.has_fix() and self.speed_mps >= config.MIN_SPEED_FOR_COURSE:
            return self.course
        return None

    def stop(self):
        self.running = False


# ------------------------- TEST -------------------------------------
if __name__ == "__main__":
    g = GPS()
    g.start()
    try:
        while True:
            if g.has_fix():
                print("FIX  lat %.6f  lon %.6f  sats %d  speed %.2f m/s  course %s"
                      % (g.lat, g.lon, g.sats, g.speed_mps, g.course))
            else:
                print("No fix yet... sats %d (go outside, can take 1-5 min)" % g.sats)
            time.sleep(1)
    except KeyboardInterrupt:
        g.stop()
