# =====================================================================
#  lidar.py  -  Slamtec RPLIDAR A1 (360 degree LiDAR) on USB.
#  Talks to the LiDAR directly (no extra library needed, only pyserial).
#
#  It splits the 360 degree scan into 3 zones:
#      FRONT  = -25 .. +25 deg
#      RIGHT  = +25 .. +90 deg
#      LEFT   = -90 .. -25 deg
#  and gives the CLOSEST distance (cm) in each zone.
#
#  Run this file on its own to TEST it. Put your hand in front of the
#  robot: "Front" should drop. If "Left" or "Right" drops instead,
#  change LIDAR_ANGLE_OFFSET in config.py (try 90, 180 or 270).
# =====================================================================
import threading
import time

import config

FAR = 1200.0   # cm - nothing seen in a zone


class Lidar(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        import serial
        try:
            self.ser = serial.Serial(config.LIDAR_PORT, config.LIDAR_BAUD, timeout=1)
        except Exception as e:
            raise RuntimeError("Cannot open %s (%s). Is the LiDAR USB plugged in?"
                               % (config.LIDAR_PORT, e))
        self.bins = [0.0] * 360        # distance (cm) for each degree, 0 = none
        self.bin_time = [0.0] * 360
        self.distances = {"front": FAR, "left": FAR, "right": FAR}
        self.last_scan = 0.0
        self.scans = 0
        self.running = True

        self._send(0x25)                # STOP (in case it was still scanning)
        time.sleep(0.05)
        self.ser.reset_input_buffer()
        self.health = self._get_health()
        if self.health == 2:
            raise RuntimeError("LiDAR reports an error. Unplug it, plug back in and retry.")
        self.ser.dtr = False            # A1: DTR low = spin motor ON
        time.sleep(1.0)                 # let the motor reach speed

    # ---------- low level ----------
    def _send(self, cmd):
        self.ser.write(bytes([0xA5, cmd]))

    def _get_health(self):
        self._send(0x52)
        desc = self.ser.read(7)
        if len(desc) != 7 or desc[0] != 0xA5 or desc[1] != 0x5A:
            raise RuntimeError("No answer from LiDAR on %s. Check the USB cable/adapter."
                               % config.LIDAR_PORT)
        data = self.ser.read(3)
        return data[0] if data else 0   # 0 good, 1 warning, 2 error

    def _start_scan(self):
        self.ser.reset_input_buffer()
        self._send(0x20)                # SCAN
        desc = self.ser.read(7)
        if len(desc) != 7 or desc[0] != 0xA5 or desc[1] != 0x5A:
            raise RuntimeError("LiDAR did not start scanning")

    # ---------- zones ----------
    def _zone_min(self, lo, hi, now):
        best = FAR
        for a in range(lo, hi + 1):
            i = a % 360
            d = self.bins[i]
            if d >= config.LIDAR_MIN_CM and now - self.bin_time[i] < 0.6:
                if d < best:
                    best = d
        return best

    def _finish_scan(self):
        now = time.time()
        f_lo, f_hi = config.LIDAR_FRONT
        r_lo, r_hi = config.LIDAR_RIGHT
        l_lo, l_hi = config.LIDAR_LEFT
        self.distances = {
            "front": self._zone_min(f_lo, f_hi, now),
            "right": self._zone_min(r_lo, r_hi, now),
            "left": self._zone_min(l_lo, l_hi, now),
        }
        self.last_scan = now
        self.scans += 1

    def ok(self):
        """True if fresh scans are coming in."""
        return time.time() - self.last_scan < 1.0

    def scan_cm(self):
        """List of 360 distances in cm (0 = no reading) for the web radar."""
        now = time.time()
        return [round(d) if now - t < 0.6 else 0 for d, t in zip(self.bins, self.bin_time)]

    # ---------- reading thread ----------
    def run(self):
        while self.running:
            try:
                self._start_scan()
                self._read_loop()
            except Exception as e:
                print("[lidar] restarting scan:", e)
                time.sleep(0.5)

    def _read_loop(self):
        buf = bytearray()
        empty = 0
        while self.running:
            data = self.ser.read(512)
            if not data:
                empty += 1
                if empty >= 2:
                    raise RuntimeError("no data")
                continue
            empty = 0
            buf += data
            i = 0
            n = len(buf)
            while n - i >= 5:
                b0, b1, b2, b3, b4 = buf[i], buf[i + 1], buf[i + 2], buf[i + 3], buf[i + 4]
                start = b0 & 1
                # each sample has check bits - if wrong, slide 1 byte to re-sync
                if start == ((b0 >> 1) & 1) or (b1 & 1) != 1:
                    i += 1
                    continue
                i += 5
                if start:
                    self._finish_scan()
                quality = b0 >> 2
                dist_cm = ((b4 << 8) | b3) / 4.0 / 10.0
                if quality == 0 or dist_cm == 0:
                    continue
                angle = ((b2 << 7) | (b1 >> 1)) / 64.0
                if config.LIDAR_FLIPPED:
                    angle = -angle
                a = int(angle + config.LIDAR_ANGLE_OFFSET) % 360
                self.bins[a] = dist_cm
                self.bin_time[a] = time.time()
            del buf[:i]

    def stop(self):
        self.running = False
        time.sleep(0.1)
        try:
            self._send(0x25)            # STOP scanning
            self.ser.dtr = True         # motor OFF
            self.ser.close()
        except Exception:
            pass


# ------------------------- TEST -------------------------------------
if __name__ == "__main__":
    lid = Lidar()
    print("LiDAR health:", ["good", "warning", "error"][min(lid.health, 2)])
    lid.start()
    try:
        while True:
            d = lid.distances
            print("Front %6.1f cm   Left %6.1f cm   Right %6.1f cm   (scans %d)"
                  % (d["front"], d["left"], d["right"], lid.scans))
            time.sleep(0.3)
    except KeyboardInterrupt:
        pass
    finally:
        lid.stop()
