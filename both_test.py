# =====================================================================
#  both_test.py  -  quick check: BOTH wheels forward, then BOTH backward.
#  Lift the wheels off the ground, then Thonny > Run.
# =====================================================================
import time
import gpio
from motors import Motors

m = Motors()
try:
    print("BOTH wheels FORWARD")
    m.drive(60, 60)
    time.sleep(3)
    m.stop()
    time.sleep(1)

    print("BOTH wheels BACKWARD")
    m.drive(-60, -60)
    time.sleep(3)
    m.stop()
    print("Done")
finally:
    m.close()
    time.sleep(0.1)
    gpio.close()
