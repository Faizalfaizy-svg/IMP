# =====================================================================
#  battery.py  -  watches the 2S LiPo (7.4V, 7000 mAh) and the 5V supply.
#
#  Battery voltage: battery + -> R1 20k -> CH1 of the MCP3008 -> R2 10k -> GND
#  The divider makes the voltage 3x smaller (8.4V full -> 2.8V, safe for 3.3V).
#
#  5V supply (HW-688): the Pi itself reports if its 5V input is too low.
#
#  Run this file on its own to TEST: it prints battery volts, % and 5V status.
#  Compare with a multimeter on the battery. If it is a bit off, change
#  BATT_CAL in config.py (e.g. multimeter 7.80V, screen 7.70V -> 7.80/7.70 = 1.013).
# =====================================================================
import subprocess
import threading
import time

import config

# LiPo resting voltage per cell -> rough % left
_TABLE = [(3.30, 0), (3.50, 5), (3.60, 10), (3.70, 30), (3.75, 45), (3.80, 55),
          (3.85, 65), (3.90, 72), (4.00, 85), (4.10, 95), (4.20, 100)]


def cell_to_percent(v):
    if v <= _TABLE[0][0]:
        return 0
    for (v1, p1), (v2, p2) in zip(_TABLE, _TABLE[1:]):
        if v <= v2:
            return round(p1 + (p2 - p1) * (v - v1) / (v2 - v1))
    return 100


class Battery(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        import spidev
        self.spi = spidev.SpiDev()
        self.spi.open(config.MIC_SPI_BUS, config.MIC_SPI_DEV)   # same MCP3008 as the mic
        self.spi.max_speed_hz = 1350000
        self.volts = None          # filtered battery voltage
        self.percent = None
        self.connected = False     # False if the divider is not wired
        self.adc_error = None      # text if the reading looks wrong
        self.low = False           # below BATT_WARN_V
        self.critical = False      # below BATT_CUTOFF_V -> robot stops (stays stopped)
        self.pi_undervolt = False  # Pi says its 5V input is too low
        self.pi_undervolt_seen = False
        self._low_since = None
        self._crit_since = None
        self._last_pi_check = 0.0
        self.running = True

    def _adc(self, ch):
        r = self.spi.xfer2([1, (8 + ch) << 4, 0])
        return ((r[1] & 3) << 8) | r[2]

    def read_volts_now(self):
        total = 0
        for _ in range(16):
            total += self._adc(config.BATT_ADC_CHANNEL)
        raw = total / 16.0
        self.last_raw = raw
        return raw / 1023.0 * config.ADC_VREF * config.BATT_DIVIDER * config.BATT_CAL

    def _check_pi_power(self):
        # 'vcgencmd get_throttled' -> bit 0 = under-voltage now, bit 16 = happened since boot
        try:
            out = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True,
                                 text=True, timeout=2).stdout
            val = int(out.strip().split("=")[1], 16)
            self.pi_undervolt = bool(val & 0x1)
            self.pi_undervolt_seen = bool(val & 0x10000)
        except Exception:
            pass

    def run(self):
        while self.running:
            now = time.time()
            try:
                v = self.read_volts_now()
            except Exception:
                v = 0.0

            # under ~2V means nothing is wired to CH1 - do not stop the robot for that.
            # 1023 (the maximum) means the MCP3008 is not answering, or CH1 sees
            # more than 3.3V (R1/R2 swapped). Both are wiring problems.
            raw = getattr(self, "last_raw", 0)
            if raw >= 1015:
                self.adc_error = ("reading is at maximum - check the MCP3008 wiring and "
                                  "that R1 20k goes to battery + and R2 10k to GND")
                self.connected = False
            elif v > config.BATT_CUTOFF_V + 2.5:
                self.adc_error = "reading %.1fV is too high for a 2S LiPo - check BATT_DIVIDER" % v
                self.connected = False
            else:
                self.adc_error = None
                self.connected = v > 2.0
            if self.connected:
                # smooth it, because the motors make the voltage jump around
                self.volts = v if self.volts is None else self.volts * 0.8 + v * 0.2
                self.percent = cell_to_percent(self.volts / config.BATT_CELLS)

                # must stay low for a few seconds (ignores short dips when motors start)
                if self.volts < config.BATT_WARN_V:
                    self._low_since = self._low_since or now
                    self.low = now - self._low_since > config.BATT_LOW_SECONDS
                else:
                    self._low_since, self.low = None, False

                if self.volts < config.BATT_CUTOFF_V:
                    self._crit_since = self._crit_since or now
                    if now - self._crit_since > config.BATT_LOW_SECONDS:
                        self.critical = True        # latches: charge the battery and restart
                else:
                    self._crit_since = None
            else:
                self.volts, self.percent = None, None

            if now - self._last_pi_check > 5:
                self._last_pi_check = now
                self._check_pi_power()

            time.sleep(0.5)

    def status(self):
        return {
            "connected": self.connected,
            "error": self.adc_error,
            "volts": round(self.volts, 2) if self.volts else None,
            "percent": self.percent,
            "low": self.low,
            "critical": self.critical,
            "pi_5v_low": self.pi_undervolt,
            "pi_5v_low_since_boot": self.pi_undervolt_seen,
        }

    def stop(self):
        self.running = False
        time.sleep(0.6)
        try:
            self.spi.close()
        except Exception:
            pass


# ------------------------- TEST -------------------------------------
if __name__ == "__main__":
    b = Battery()
    b.start()
    try:
        while True:
            time.sleep(1)
            s = b.status()
            if s["error"]:
                print("Battery: WIRING PROBLEM -", s["error"])
            elif not s["connected"]:
                print("Battery: no reading on CH%d (check the 20k/10k divider)"
                      % config.BATT_ADC_CHANNEL)
            else:
                state = "CRITICAL - charge now!" if s["critical"] else \
                        "LOW" if s["low"] else "OK"
                print("Battery %.2f V  (%d%%)  %s" % (s["volts"], s["percent"], state))
            print("   Pi 5V supply (HW-688):",
                  "TOO LOW now!" if s["pi_5v_low"] else "OK",
                  "(was low earlier)" if s["pi_5v_low_since_boot"] and not s["pi_5v_low"] else "")
    except KeyboardInterrupt:
        b.stop()
