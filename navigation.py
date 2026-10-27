# =====================================================================
#  navigation.py  -  the autonomous "brain".
#  Combines LiDAR + camera + GPS and returns motor speeds.
#
#  Priority order (highest first):
#    1. finish an escape move (reverse, then turn) if one is running
#    2. front obstacle very close  -> start escape move
#    3. front obstacle near / camera sees big object -> steer away
#    4. side wall too close -> veer away from it
#    5. WAYPOINT mode -> steer towards GPS target
#    6. otherwise -> drive forward
# =====================================================================
import time

import config
from gps import bearing_deg, distance_m


def clamp(v, lo=-100, hi=100):
    return max(lo, min(hi, v))


class Navigator:
    def __init__(self):
        self.phase = None       # None, "reverse" or "turn"
        self.phase_end = 0.0
        self.turn_dir = 1       # 1 = turn right, -1 = turn left
        self.arrived = False

    def reset(self):
        self.phase = None
        self.arrived = False

    def step(self, mode, dist, cam=None, gps=None, waypoint=None):
        """Returns (left_speed, right_speed, reason_text)."""
        now = time.time()
        f, l, r = dist["front"], dist["left"], dist["right"]
        S, T, SL = config.DRIVE_SPEED, config.TURN_SPEED, config.SLOW_SPEED

        # 1. escape move in progress
        if self.phase == "reverse":
            if now < self.phase_end:
                return -SL, -SL, "escape: reversing"
            self.phase, self.phase_end = "turn", now + 0.6
        if self.phase == "turn":
            if now < self.phase_end:
                return (T, -T, "escape: turning right") if self.turn_dir > 0 \
                    else (-T, T, "escape: turning left")
            self.phase = None

        # 2. something very close in front
        if f < config.STOP_DIST:
            self.turn_dir = 1 if r > l else -1
            self.phase, self.phase_end = "reverse", now + 0.5
            return -SL, -SL, "obstacle %.0f cm - backing up" % f

        # 3. something ahead (LiDAR) or big object (camera)
        cam_blocked = bool(cam and cam.blocked)
        if f < config.SLOW_DIST or cam_blocked:
            if cam_blocked and cam.block_side:
                go_right = cam.block_side == "left"   # object on left -> go right
            else:
                go_right = r >= l
            why = "camera sees object" if cam_blocked else "obstacle %.0f cm" % f
            if go_right:
                return SL, -SL // 3, why + " - steering right"
            return -SL // 3, SL, why + " - steering left"

        # 4. too close to a side
        if l < config.SIDE_DIST:
            return S, S // 2, "wall on left - veer right"
        if r < config.SIDE_DIST:
            return S // 2, S, "wall on right - veer left"

        # 5. GPS waypoint
        if mode == "waypoint":
            if not waypoint:
                return 0, 0, "no waypoint set"
            if not (gps and gps.has_fix()):
                return 0, 0, "waiting for GPS fix"
            d = distance_m(gps.lat, gps.lon, waypoint[0], waypoint[1])
            if d < config.WAYPOINT_RADIUS_M:
                self.arrived = True
                return 0, 0, "arrived at waypoint"
            target = bearing_deg(gps.lat, gps.lon, waypoint[0], waypoint[1])
            heading = gps.heading()
            if heading is None:
                # need to move to know which way we face
                return SL, SL, "%.0f m to go - moving to get GPS heading" % d
            err = (target - heading + 540) % 360 - 180   # -180..180, + = target is to the right
            steer = clamp(err * config.STEER_GAIN, -40, 40)
            return clamp(S + steer), clamp(S - steer), \
                "%.0f m to go, heading error %.0f deg" % (d, err)

        # 6. clear road
        return S, S, "path clear - forward"
