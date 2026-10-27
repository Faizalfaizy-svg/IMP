# =====================================================================
#  gpio.py  -  opens the Pi 5 GPIO chip with lgpio.
#  It FINDS the right chip by itself (on this Pi it was gpiochip15,
#  "pinctrl-rp1"), so no chip number needs typing anywhere.
# =====================================================================
import os
import sys
import threading

# keep this project folder importable after we change folder below
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# lgpio makes small helper files in the working folder. Thonny sometimes
# runs code from a folder where that is not allowed, so use the home folder.
_HOME = os.path.expanduser("~")
os.environ.setdefault("LG_WD", _HOME)
try:
    os.chdir(_HOME)
except OSError:
    pass

import lgpio  # noqa: E402

_lock = threading.Lock()
_handle = None
_claimed = set()


def _find_chip():
    # You can force a chip with:  export GPIO_CHIP=15
    forced = os.environ.get("GPIO_CHIP")
    if forced:
        return int(forced)

    backup = None
    for n in range(0, 64):
        if not os.path.exists("/dev/gpiochip%d" % n):
            continue
        try:
            h = lgpio.gpiochip_open(n)
        except Exception:
            continue
        try:
            info = lgpio.gpio_get_chip_info(h)
            lines, label = info[1], str(info[3])
        except Exception:
            lines, label = 0, ""
        finally:
            lgpio.gpiochip_close(h)

        if "pinctrl-rp1" in label or label.startswith("pinctrl-bcm"):
            return n
        if lines in (54, 58) and backup is None:
            backup = n

    if backup is not None:
        return backup
    raise RuntimeError("Could not find the GPIO header chip. Run 'gpiodetect' to check.")


def handle():
    global _handle
    if _handle is None:
        chip = _find_chip()
        _handle = lgpio.gpiochip_open(chip)
        print("[gpio] using /dev/gpiochip%d" % chip)
    return _handle


def output(pin, value=0):
    with _lock:
        h = handle()
        if pin not in _claimed:
            lgpio.gpio_claim_output(h, pin, value)
            _claimed.add(pin)
        else:
            lgpio.gpio_write(h, pin, value)


def input(pin):  # noqa: A001
    with _lock:
        h = handle()
        if pin not in _claimed:
            lgpio.gpio_claim_input(h, pin)
            _claimed.add(pin)


def write(pin, value):
    with _lock:
        lgpio.gpio_write(handle(), pin, 1 if value else 0)


def read(pin):
    # no lock here: reads are fast
    return lgpio.gpio_read(handle(), pin)


def pwm(pin, duty, freq=1000):
    """duty is 0-100 (%)"""
    duty = max(0.0, min(100.0, float(duty)))
    with _lock:
        lgpio.tx_pwm(handle(), pin, freq, duty)


def close():
    global _handle
    with _lock:
        if _handle is not None:
            for p in list(_claimed):
                try:
                    lgpio.gpio_write(_handle, p, 0)
                    lgpio.gpio_free(_handle, p)
                except Exception:
                    pass
            _claimed.clear()
            lgpio.gpiochip_close(_handle)
            _handle = None
