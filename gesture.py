# =====================================================================
#  gesture.py  -  SparkFun APDS-9960 gesture sensor over I2C (smbus2).
#  Swipe a hand over it ~5-10 cm away: UP / DOWN / LEFT / RIGHT.
#  Run this file on its own to TEST it.
# =====================================================================
import threading
import time

from smbus2 import SMBus

import config

# APDS-9960 registers
ENABLE, WTIME, PPULSE, CONTROL, CONFIG2, ID = 0x80, 0x83, 0x8E, 0x8F, 0x90, 0x92
GPENTH, GEXTH, GCONF1, GCONF2 = 0xA0, 0xA1, 0xA2, 0xA3
GOFFSET_U, GOFFSET_D, GPULSE, GOFFSET_L, GOFFSET_R = 0xA4, 0xA5, 0xA6, 0xA7, 0xA9
GCONF3, GCONF4, GFLVL, GSTATUS, GFIFO_U = 0xAA, 0xAB, 0xAE, 0xAF, 0xFC

MIN_LEVEL = 10      # ignore weak samples
SENSITIVITY = 15    # how big the swipe must be


class GestureSensor(threading.Thread):
    def __init__(self, on_gesture=None):
        super().__init__(daemon=True)
        self.on_gesture = on_gesture
        self.last = None
        self.running = True
        self.bus = SMBus(config.I2C_BUS)
        self.addr = config.APDS_ADDR

        dev_id = self._r(ID)
        if dev_id not in (0xAB, 0xA8, 0x9C):
            raise RuntimeError("APDS-9960 not found (ID 0x%02X). Check SDA/SCL wires." % dev_id)

        self._w(ENABLE, 0x00)       # everything off while setting up
        self._w(WTIME, 0xFF)
        self._w(PPULSE, 0x89)       # 16 us, 10 pulses
        self._w(CONTROL, 0x09)      # LED 100 mA, prox gain 4x, ALS gain 4x
        self._w(CONFIG2, 0x01)
        self._w(GPENTH, 40)         # gesture starts when hand is this close
        self._w(GEXTH, 30)          # gesture ends below this
        self._w(GCONF1, 0x40)       # FIFO interrupt after 4 datasets
        self._w(GCONF2, 0x41)       # gesture gain 4x, LED 100 mA, wait 2.8 ms
        for reg in (GOFFSET_U, GOFFSET_D, GOFFSET_L, GOFFSET_R):
            self._w(reg, 0)
        self._w(GPULSE, 0xC9)       # 32 us, 10 pulses
        self._w(GCONF3, 0x00)       # use all 4 photodiodes
        self._w(GCONF4, 0x04)       # clear FIFO
        self._w(ENABLE, 0x4D)       # power on + wait + proximity + gesture

    def _r(self, reg):
        return self.bus.read_byte_data(self.addr, reg)

    def _w(self, reg, val):
        self.bus.write_byte_data(self.addr, reg, val)

    def read_gesture(self):
        """Returns 'UP', 'DOWN', 'LEFT', 'RIGHT' or None."""
        if not (self._r(GSTATUS) & 0x01):
            return None
        samples = []
        last_data = time.time()
        while time.time() - last_data < 0.10:   # keep reading until the hand has gone
            if self._r(GSTATUS) & 0x01:
                level = self._r(GFLVL)
                n = level * 4
                data = []
                while n > 0:
                    chunk = min(32, n)
                    data += self.bus.read_i2c_block_data(self.addr, GFIFO_U, chunk)
                    n -= chunk
                for i in range(0, len(data) - 3, 4):
                    samples.append(data[i:i + 4])   # U, D, L, R
                if level:
                    last_data = time.time()
            time.sleep(0.005)
        return self._decode(samples)

    @staticmethod
    def _decode(samples):
        good = [s for s in samples if min(s) > MIN_LEVEL]
        if len(good) < 4:
            return None
        u1, d1, l1, r1 = good[0]
        u2, d2, l2, r2 = good[-1]
        ud_first = (u1 - d1) * 100.0 / (u1 + d1)
        lr_first = (l1 - r1) * 100.0 / (l1 + r1)
        ud_last = (u2 - d2) * 100.0 / (u2 + d2)
        lr_last = (l2 - r2) * 100.0 / (l2 + r2)
        ud = ud_last - ud_first
        lr = lr_last - lr_first
        if max(abs(ud), abs(lr)) < SENSITIVITY:
            return None
        if abs(ud) > abs(lr):
            return "DOWN" if ud > 0 else "UP"
        return "RIGHT" if lr > 0 else "LEFT"

    def run(self):
        while self.running:
            try:
                g = self.read_gesture()
            except OSError:
                g = None
                time.sleep(0.5)
            if g:
                self.last = g
                if self.on_gesture:
                    self.on_gesture(g)
            time.sleep(0.03)

    def stop(self):
        self.running = False


# ------------------------- TEST -------------------------------------
if __name__ == "__main__":
    print("Swipe your hand over the sensor (Ctrl+C or Stop to quit)")
    gs = GestureSensor(on_gesture=lambda g: print("Gesture:", g))
    gs.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        gs.stop()
