# =====================================================================
#  microphone.py  -  MAX9814 mic read through the MCP3008 ADC (spidev).
#  Detects a loud sound (a clap) and reports it.
#  Run this file on its own to SEE the sound level and pick CLAP_THRESHOLD.
# =====================================================================
import threading
import time

import spidev

import config


class Microphone(threading.Thread):
    def __init__(self, on_clap=None):
        super().__init__(daemon=True)
        self.on_clap = on_clap
        self.spi = spidev.SpiDev()
        self.spi.open(config.MIC_SPI_BUS, config.MIC_SPI_DEV)
        self.spi.max_speed_hz = 1350000
        self.level = 0          # latest peak-to-peak level (0-1023)
        self.connected = False  # False if the MCP3008 reads stuck at 0 or 1023
        self._stuck = [True] * 30
        self._last_clap = 0.0
        self.running = True

    def read_adc(self):
        ch = config.MIC_CHANNEL
        r = self.spi.xfer2([1, (8 + ch) << 4, 0])
        return ((r[1] & 3) << 8) | r[2]

    def run(self):
        while self.running:
            lo, hi = 1023, 0
            end = time.perf_counter() + 0.03          # 30 ms window
            while time.perf_counter() < end:
                v = self.read_adc()
                lo = min(lo, v)
                hi = max(hi, v)
            self.level = hi - lo
            # an unwired MCP3008 / mic reads stuck at 1023 (or 0). A clap never
            # reaches the ends (the MAX9814 swings about 0.25-2.25V), so ignore those.
            stuck = hi <= 2 or lo >= 1021 or hi >= 1021 or lo <= 2
            self._stuck.append(stuck)
            self._stuck.pop(0)
            self.connected = not all(self._stuck)
            now = time.time()
            if (not stuck and self.connected and self.level > config.CLAP_THRESHOLD
                    and now - self._last_clap > 0.8):
                self._last_clap = now
                if self.on_clap:
                    self.on_clap(self.level)
            time.sleep(0.005)

    def stop(self):
        self.running = False
        time.sleep(0.05)
        self.spi.close()


# ------------------------- TEST -------------------------------------
if __name__ == "__main__":
    print("Be quiet, then clap. Set CLAP_THRESHOLD in config.py between the two levels.")
    mic = Microphone(on_clap=lambda lv: print("   *** CLAP! level", lv))
    mic.start()
    try:
        while True:
            lv = mic.level
            if not mic.connected:
                print("No signal - check the MCP3008 wiring (SPI pins, 3.3V, GND) and mic OUT -> CH0")
            else:
                print("level %4d  %s" % (lv, "#" * (lv // 20)))
            time.sleep(0.1)
    except KeyboardInterrupt:
        mic.stop()
