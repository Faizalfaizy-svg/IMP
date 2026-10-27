# =====================================================================
#  motors.py  -  drives the two motors through the L298N.
#  Run this file on its own (Thonny > Run) to TEST the motors.
# =====================================================================
import threading
import time
import config
import gpio


class Motors:
    """Both motors. Speeds go from -100 (full reverse) to 100 (full forward).

    Soft start: the speed ramps up over about 0.25 s instead of jumping,
    so both big motors don't pull a huge current at the same moment
    (that can make one motor stall while the other one spins).
    """

    def __init__(self):
        for p in (config.ENA, config.IN1, config.IN2,
                  config.ENB, config.IN3, config.IN4):
            gpio.output(p, 0)
        self.left = 0           # target speeds
        self.right = 0
        self._now = [0.0, 0.0]  # actual (ramped) speeds
        self._sent = [None, None]
        self._lock = threading.Lock()
        self._running = True
        threading.Thread(target=self._ramp_loop, daemon=True).start()

    def _set_side(self, idx, speed):
        en, a, b, invert = ((config.ENA, config.IN1, config.IN2, config.LEFT_INVERT),
                            (config.ENB, config.IN3, config.IN4, config.RIGHT_INVERT))[idx]
        speed = max(-100, min(100, int(round(speed))))
        if invert:
            speed = -speed
        if speed == 0:
            state = (0, 0, 0.0)
        else:
            # map 1..100 onto MIN_DUTY..100 so small speeds still move the car
            duty = config.MIN_DUTY + (100 - config.MIN_DUTY) * abs(speed) / 100.0
            state = (1 if speed > 0 else 0, 0 if speed > 0 else 1, round(duty, 1))
        if state == self._sent[idx]:
            return              # nothing changed - don't restart the PWM
        self._sent[idx] = state
        gpio.write(a, state[0])
        gpio.write(b, state[1])
        gpio.pwm(en, state[2], config.PWM_FREQ)

    def _ramp_loop(self):
        dt = 0.02
        step = config.RAMP_PER_SEC * dt
        while self._running:
            with self._lock:
                for i, target in enumerate((self.left, self.right)):
                    cur = self._now[i]
                    if target == 0:
                        cur = 0.0                       # stopping is always instant
                    elif (cur > 0 > target) or (cur < 0 < target):
                        cur = 0.0                       # changing direction: pass through stop
                    elif abs(target - cur) <= step or abs(target) < abs(cur):
                        cur = float(target)             # slowing down is instant
                    else:
                        cur += step if target > cur else -step
                    self._now[i] = cur
                    self._set_side(i, cur)
            time.sleep(dt)

    def drive(self, left, right):
        """left / right speed from -100 (full reverse) to 100 (full forward)"""
        self.left = max(-100, min(100, int(left)))
        self.right = max(-100, min(100, int(right)))
        if self.left == 0 and self.right == 0:
            with self._lock:            # stop right now, don't wait for the ramp thread
                self._now = [0.0, 0.0]
                self._set_side(0, 0)
                self._set_side(1, 0)

    def forward(self, s=None):
        s = config.DRIVE_SPEED if s is None else s
        self.drive(s, s)

    def backward(self, s=None):
        s = config.DRIVE_SPEED if s is None else s
        self.drive(-s, -s)

    def spin_left(self, s=None):
        s = config.TURN_SPEED if s is None else s
        self.drive(-s, s)

    def spin_right(self, s=None):
        s = config.TURN_SPEED if s is None else s
        self.drive(s, -s)

    def stop(self):
        self.drive(0, 0)

    def close(self):
        self.stop()
        self._running = False


# ------------------------- TEST -------------------------------------
if __name__ == "__main__":
    m = Motors()
    try:
        for name, l, r in [("LEFT forward", 60, 0), ("LEFT backward", -60, 0),
                           ("RIGHT forward", 0, 60), ("RIGHT backward", 0, -60),
                           ("BOTH forward", 60, 60), ("spin left", -60, 60),
                           ("spin right", 60, -60)]:
            print(name)
            m.drive(l, r)
            time.sleep(2)
            m.stop()
            time.sleep(1)
        print("Done")
    finally:
        m.close()
        time.sleep(0.1)
        gpio.close()
