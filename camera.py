# =====================================================================
#  camera.py  -  Raspberry Pi AI Camera (Sony IMX500).
#  Object detection runs ON the camera chip (MobileNet SSD, COCO classes).
#  This file: grabs frames, draws boxes, makes a JPEG for the phone,
#  and says if something big is in front of the robot.
#  Run this file on its own to TEST (prints what it sees).
# =====================================================================
import threading
import time

import cv2
import numpy as np

import config

try:
    from picamera2 import Picamera2
except ImportError:
    Picamera2 = None

try:
    from picamera2.devices import IMX500
    from picamera2.devices.imx500 import NetworkIntrinsics
except ImportError:
    IMX500 = None


class Camera(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        if Picamera2 is None:
            raise RuntimeError("picamera2 is not installed")
        if not Picamera2.global_camera_info():
            raise RuntimeError(
                "No camera found. Check the ribbon cable (both ends, contacts the right way), "
                "then run in a terminal:  rpicam-hello --list-cameras")

        self.imx500 = None
        self.labels = None
        self.intr = None
        if IMX500 is not None:
            try:
                self.imx500 = IMX500(config.CAMERA_MODEL)
                self.intr = self.imx500.network_intrinsics or NetworkIntrinsics()
                self.intr.task = "object detection"
                try:
                    self.intr.update_with_defaults()
                except Exception:
                    pass
                self.labels = self.intr.labels
            except Exception as e:
                print("[camera] AI model not loaded (%s) - video only" % e)
                self.imx500 = None

        cam_num = self.imx500.camera_num if self.imx500 else 0
        try:
            self.picam2 = Picamera2(cam_num)
        except Exception as e:
            raise RuntimeError("Camera could not be opened (%s)" % e)
        fps = getattr(self.intr, "inference_rate", None) or 30
        cfg = self.picam2.create_preview_configuration(
            main={"format": "RGB888", "size": config.CAMERA_SIZE},
            controls={"FrameRate": fps}, buffer_count=12)
        if self.imx500:
            print("[camera] loading AI model onto the camera (first time can take ~1 min)...")
            self.imx500.show_network_fw_progress_bar()
        self.picam2.start(cfg, show_preview=False)

        self.jpeg = None          # latest frame for the web stream
        self.detections = []      # list of (label, score, (x, y, w, h)) in pixels
        self.blocked = False      # big object in front?
        self.block_side = None    # "left" or "right" = which half the object is in
        self.running = True

    def _parse(self, metadata):
        outs = self.imx500.get_outputs(metadata, add_batch=True)
        if outs is None:
            return self.detections
        in_w, in_h = self.imx500.get_input_size()
        boxes, scores, classes = outs[0][0], outs[1][0], outs[2][0]
        if getattr(self.intr, "bbox_normalization", False):
            boxes = boxes / in_h
        if getattr(self.intr, "bbox_order", "yx") == "xy":
            boxes = boxes[:, [1, 0, 3, 2]]
        dets = []
        for box, score, cls in zip(boxes, scores, classes):
            if score < config.DETECT_THRESHOLD:
                continue
            x, y, w, h = self.imx500.convert_inference_coords(tuple(box), metadata, self.picam2)
            c = int(cls)
            name = self.labels[c] if self.labels and c < len(self.labels) else str(c)
            dets.append((name, float(score), (int(x), int(y), int(w), int(h))))
        return dets

    def run(self):
        W, H = config.CAMERA_SIZE
        while self.running:
            try:
                req = self.picam2.capture_request()
                frame = req.make_array("main")
                md = req.get_metadata()
                req.release()
            except Exception:
                time.sleep(0.1)
                continue

            if self.imx500:
                try:
                    self.detections = self._parse(md)
                except Exception:
                    self.detections = []

            # is something big in the middle of the picture?
            blocked, side = False, None
            c_lo = W * (0.5 - config.CAM_CENTRE_WIDTH / 2)
            c_hi = W * (0.5 + config.CAM_CENTRE_WIDTH / 2)
            for name, score, (x, y, w, h) in self.detections:
                cx = x + w / 2
                close = h > H * config.CAM_BLOCK_HEIGHT
                if close and c_lo < cx < c_hi:
                    blocked = True
                    side = "left" if cx < W / 2 else "right"
                colour = (0, 0, 255) if close else (0, 255, 0)
                cv2.rectangle(frame, (x, y), (x + w, y + h), colour, 2)
                cv2.putText(frame, "%s %.0f%%" % (name, score * 100), (x + 3, max(15, y - 5)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, colour, 1)
            self.blocked, self.block_side = blocked, side

            if frame.ndim == 3 and frame.shape[2] == 4:
                frame = frame[:, :, :3]
            ok, buf = cv2.imencode(".jpg", np.ascontiguousarray(frame),
                                   [cv2.IMWRITE_JPEG_QUALITY, 70])
            if ok:
                self.jpeg = buf.tobytes()

    def stop(self):
        self.running = False
        time.sleep(0.2)
        try:
            self.picam2.stop()
        except Exception:
            pass


# ------------------------- TEST -------------------------------------
if __name__ == "__main__":
    cam = Camera()
    cam.start()
    try:
        while True:
            names = ["%s(%.0f%%)" % (n, s * 100) for n, s, _ in cam.detections]
            print("Sees:", ", ".join(names) or "nothing",
                  "| BLOCKED on %s" % cam.block_side if cam.blocked else "")
            time.sleep(0.5)
    except KeyboardInterrupt:
        cam.stop()
