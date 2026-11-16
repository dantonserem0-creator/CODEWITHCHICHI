#!/usr/bin/env python3
"""
RETROLENS - hand-gesture retro camera (OpenCV + MediaPipe)

MODE LENSA  (camera frame)
  * Raise BOTH index fingers (middle + ring fingers folded). The two index tips
    become the top corners of a 16:9 frame that follows your hands (rolls with them).
  * Everything inside the frame gets the active filter (MONO / KONTRAS / FILM).
  * Hold still ~0.8 s -> frame turns magenta -> 3-2-1 countdown -> flash -> photo
    is saved to ./foto/  (cropped + straightened, filter applied).
  * Raise ONE index finger and hold ~1 s  -> switch to MODE GAMBAR.

MODE GAMBAR (draw)
  * Index finger up (other fingers folded) = neon pen, trail fades after a few seconds.
  * Open palm held ~1 s  -> back to MODE LENSA.
  * Fist held ~1.2 s     -> clear the canvas (HAPUS).

Keys:  q/ESC quit | f next filter | m toggle mode | c clear drawing
       s snap now (when a frame is showing) | r toggle retro effect
"""
import math
import os
import sys
import time
import urllib.request
from collections import deque
from datetime import datetime

import cv2
import numpy as np

# ============================== CONFIG ======================================
CAM_INDEX = 0
CAP_W, CAP_H = 1280, 720          # camera capture size (photos are cut from this)
LEBAR, TINGGI = 960, 540          # processing / display size
WIN = "RETROLENS"
OUT_DIR = "foto"
ASPECT = 16 / 9                   # lens frame aspect ratio

HOLD_SWITCH = 1.0                 # seconds to hold a gesture to switch mode
HOLD_CLEAR = 1.2                  # seconds to hold a fist to clear drawing
STABLE_TIME = 0.8                 # seconds of holding still before frame locks
STABLE_PX = 14                    # movement tolerance (px) for "holding still"
COUNTDOWN = 3                     # seconds of 3-2-1
TRAIL_LIFE = 4.0                  # seconds before neon trail fades away
RETRO_FX = True                   # scanlines + vignette + grain

# BGR colours
YELLOW = (0, 190, 255)
CYAN = (255, 230, 0)
MAGENTA = (200, 0, 255)
RED = (60, 60, 255)
WHITE = (255, 255, 255)

LENSA, GAMBAR = "LENSA", "GAMBAR"
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
             "hand_landmarker/float16/latest/hand_landmarker.task")
MODEL_PATH = "hand_landmarker.task"

# ============================== FILTERS =====================================
_rng = np.random.default_rng(7)
_NOISE = np.clip(_rng.normal(0, 1, (1500, 2600)) * 32, -127, 127).astype(np.int8)
_clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
_x = np.arange(256) / 255.0
_s = 1 / (1 + np.exp(-(_x - 0.5) * 6.0))
_LUT_S = (255 * (_s - _s.min()) / (_s.max() - _s.min())).astype(np.uint8)


def noise(h, w, amt):
    h, w = min(h, 1500), min(w, 2600)
    oy = int(_rng.integers(0, 1500 - h + 1))
    ox = int(_rng.integers(0, 2600 - w + 1))
    return (_NOISE[oy:oy + h, ox:ox + w].astype(np.int16) * amt) // 32


def grain(img, amt):
    n = noise(img.shape[0], img.shape[1], amt)
    if img.ndim == 3:
        n = n[..., None]
    return np.clip(img.astype(np.int16) + n, 0, 255).astype(np.uint8)


def abu(roi):                       # -> grayscale
    return cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)


def ke_bgr(g):                      # grayscale -> BGR
    return cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)


def m_mono(roi):
    g = _clahe.apply(abu(roi))
    g = cv2.LUT(g, _LUT_S)
    return ke_bgr(grain(g, 14))


def m_kontras(roi):
    lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
    lab[..., 0] = _clahe.apply(lab[..., 0])
    out = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.int16)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.35, 0, 255)
    out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    return grain(cv2.LUT(out, _LUT_S), 8)


_SEPIA = np.array([[0.131, 0.534, 0.272],
                   [0.168, 0.686, 0.349],
                   [0.189, 0.769, 0.393]], np.float32)


def m_film(roi):
    sep = cv2.transform(roi, _SEPIA)
    out = cv2.addWeighted(roi, 0.55, sep, 0.45, 0)
    out = cv2.convertScaleAbs(out, alpha=0.88, beta=16)       # faded blacks
    h, w = out.shape[:2]
    yy, xx = np.ogrid[:h, :w]
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    vig = np.clip(1.08 - 0.45 * r ** 2, 0.5, 1.0).astype(np.float32)
    out = (out.astype(np.float32) * vig[..., None]).astype(np.uint8)
    return grain(out, 16)


FILTERS = [("MONO", m_mono), ("KONTRAS", m_kontras), ("FILM", m_film)]

# ============================== HANDS =======================================


class Hand:
    def __init__(self, pts):
        self.pts = pts              # (21, 2) float array in display pixels


def _d(a, b):
    return float(np.hypot(a[0] - b[0], a[1] - b[1]))


def finger_states(h):
    """[thumb, index, middle, ring, pinky] -> True if extended."""
    p = h.pts
    palm = _d(p[0], p[9]) + 1e-6
    thumb = _d(p[4], p[17]) > _d(p[3], p[17]) * 1.05 and _d(p[4], p[5]) > 0.55 * palm
    ext = [thumb]
    for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18)):
        ext.append(_d(p[0], p[tip]) > _d(p[0], p[pip]) * 1.12)
    return ext


def is_index_only(h):
    e = finger_states(h)
    return e[1] and not (e[2] or e[3] or e[4])


def is_frame_pose(h):
    e = finger_states(h)
    return e[1] and not (e[2] or e[3])


def is_open_palm(h):
    e = finger_states(h)
    return all(e[1:5])


def is_fist(h):
    return not any(finger_states(h)[1:5])


class HandTracker:
    """MediaPipe wrapper: legacy `solutions` API if present, else Tasks API."""

    def __init__(self):
        import mediapipe as mp
        self.mp = mp
        self.legacy = hasattr(mp, "solutions")
        if self.legacy:
            self.det = mp.solutions.hands.Hands(
                static_image_mode=False, max_num_hands=2, model_complexity=0,
                min_detection_confidence=0.6, min_tracking_confidence=0.5)
        else:
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision
            if not os.path.exists(MODEL_PATH):
                print("Downloading hand_landmarker.task ...")
                urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
            opts = vision.HandLandmarkerOptions(
                base_options=mp_python.BaseOptions(model_asset_path=MODEL_PATH),
                running_mode=vision.RunningMode.VIDEO, num_hands=2,
                min_hand_detection_confidence=0.6,
                min_hand_presence_confidence=0.5,
                min_tracking_confidence=0.5)
            self.det = vision.HandLandmarker.create_from_options(opts)
            self.t0 = time.time()
            self.last_ts = -1

    def __call__(self, bgr):
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        h, w = bgr.shape[:2]
        if self.legacy:
            rgb.flags.writeable = False
            res = self.det.process(rgb)
            lms = [hl.landmark for hl in (res.multi_hand_landmarks or [])]
        else:
            ts = int((time.time() - self.t0) * 1000)
            ts = max(ts, self.last_ts + 1)
            self.last_ts = ts
            img = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb)
            lms = self.det.detect_for_video(img, ts).hand_landmarks
        return [Hand(np.array([[l.x * w, l.y * h] for l in hl], np.float32)) for hl in lms]


# ============================== DRAWING HELPERS =============================
FONT = cv2.FONT_HERSHEY_DUPLEX


def glitch_text(img, text, org, scale=0.6, color=WHITE, thick=2, center=False):
    (tw, th), _ = cv2.getTextSize(text, FONT, scale, thick)
    x, y = int(org[0]), int(org[1])
    if center:
        x -= tw // 2
    cv2.putText(img, text, (x + 2, y + 1), FONT, scale, MAGENTA, thick + 1, cv2.LINE_AA)
    cv2.putText(img, text, (x - 2, y - 1), FONT, scale, CYAN, thick + 1, cv2.LINE_AA)
    cv2.putText(img, text, (x, y), FONT, scale, color, thick, cv2.LINE_AA)


def ring(img, c, r, p, col):
    c = (int(c[0]), int(c[1]))
    cv2.circle(img, c, r, (70, 70, 70), 3, cv2.LINE_AA)
    if p > 0:
        cv2.ellipse(img, c, (r, r), -90, 0, 360 * p, col, 4, cv2.LINE_AA)


class Dwell:
    """Progress 0..1 while a condition is held."""

    def __init__(self, hold, grace=0.25):
        self.hold, self.grace = hold, grace
        self.start = None
        self.last = 0.0

    def update(self, active, now):
        if active:
            self.last = now
            if self.start is None:
                self.start = now
        elif self.start is not None and now - self.last > self.grace:
            self.start = None
        return 0.0 if self.start is None else min(1.0, (now - self.start) / self.hold)

    def reset(self):
        self.start = None


def make_quad(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    w = np.linalg.norm(d)
    n = np.array([-d[1], d[0]]) / w
    h = w / ASPECT
    return np.array([a, b, b + n * h, a + n * h], np.float32)


# ============================== APP =========================================


class RetroLens:
    def __init__(self, tracker=None):
        self.tracker = tracker
        self.mode = LENSA
        self.fi = 0
        self.fotos = 0
        self.fps = 0.0
        self.last_t = time.time()
        self.flash = 0.0
        self.toast = ("", 0.0)
        self.retro = RETRO_FX
        # lens state
        self.quad = None
        self.lost_at = None
        self.ref = None
        self.still_since = 0.0
        self.locked_at = None
        self.cooldown_until = 0.0
        # draw state
        self.strokes = []
        self.pen_down = False
        self.pen_pos = None
        # dwell
        self.d_draw = Dwell(HOLD_SWITCH)
        self.d_lens = Dwell(HOLD_SWITCH)
        self.d_clear = Dwell(HOLD_CLEAR)
        self.fx_map = self._build_fx_map()
        self.full = None

    # ---- retro overlay map (scanlines + vignette) ----
    @staticmethod
    def _build_fx_map():
        yy, xx = np.mgrid[:TINGGI, :LEBAR]
        r = np.sqrt(((xx - LEBAR / 2) / (LEBAR / 2)) ** 2 + ((yy - TINGGI / 2) / (TINGGI / 2)) ** 2)
        vig = np.clip(1.05 - 0.38 * r ** 2, 0.5, 1.0)
        scan = np.where(yy % 3 == 0, 0.88, 1.0)
        m = (vig * scan * 255).astype(np.uint8)
        return np.dstack([m, m, m])

    @property
    def filt(self):
        return FILTERS[self.fi]

    # ---- LENS ----
    def reset_lens(self):
        self.quad = None
        self.lost_at = None
        self.ref = None
        self.locked_at = None

    def update_lens(self, hands, now):
        cand = sorted([h for h in hands if is_frame_pose(h)], key=lambda h: h.pts[0][0])
        if len(cand) >= 2:
            a, b = cand[0].pts[8], cand[-1].pts[8]
            if _d(a, b) > 60:
                q = make_quad(a, b)
                self.quad = q if self.quad is None else (self.quad * 0.5 + q * 0.5)
                self.lost_at = None
                self._lock_logic(now)
                return
        if self.quad is not None:
            if self.lost_at is None:
                self.lost_at = now
            if now - self.lost_at > 0.3:
                self.reset_lens()

    def _lock_logic(self, now):
        q = self.quad
        if self.ref is None:
            self.ref, self.still_since = q.copy(), now
        move = float(np.max(np.linalg.norm(q - self.ref, axis=1)))
        if self.locked_at is None:
            if move > STABLE_PX:
                self.ref, self.still_since = q.copy(), now
            elif now - self.still_since >= STABLE_TIME and now >= self.cooldown_until:
                self.locked_at = now
        else:
            if move > STABLE_PX * 2.2:                       # moved -> unlock
                self.locked_at = None
                self.ref, self.still_since = q.copy(), now
            elif now - self.locked_at >= COUNTDOWN:
                self.capture(now)
                self.locked_at = None
                self.cooldown_until = now + 2.0
                self.ref, self.still_since = q.copy(), now

    def capture(self, now):
        if self.full is None or self.quad is None:
            return
        sx, sy = self.full.shape[1] / LEBAR, self.full.shape[0] / TINGGI
        q = (self.quad * np.array([sx, sy], np.float32)).astype(np.float32)
        w = max(16, int(np.linalg.norm(q[1] - q[0])))
        h = max(16, int(np.linalg.norm(q[3] - q[0])))
        dst = np.float32([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]])
        M = cv2.getPerspectiveTransform(q, dst)
        crop = cv2.warpPerspective(self.full, M, (w, h), flags=cv2.INTER_CUBIC)
        crop = self.filt[1](crop)
        os.makedirs(OUT_DIR, exist_ok=True)
        path = f"{OUT_DIR}/{self.filt[0]}_{datetime.now():%Y%m%d_%H%M%S}.png"
        cv2.imwrite(path, crop)
        self.fotos += 1
        self.flash = 1.0
        self.toast = (f"TERSIMPAN {path} {w}x{h}", now + 2.5)
        print("Tersimpan:", path, f"{w}x{h}")

    def apply_lens_effect(self, img):
        q = self.quad.astype(np.int32)
        x0, y0 = max(int(q[:, 0].min()), 0), max(int(q[:, 1].min()), 0)
        x1, y1 = min(int(q[:, 0].max()), LEBAR), min(int(q[:, 1].max()), TINGGI)
        if x1 - x0 < 4 or y1 - y0 < 4:
            return
        roi = img[y0:y1, x0:x1]
        filt = self.filt[1](roi)
        mask = np.zeros(roi.shape[:2], np.uint8)
        cv2.fillConvexPoly(mask, q - np.array([x0, y0], np.int32), 255)
        img[y0:y1, x0:x1] = np.where(mask[..., None] > 0, filt, roi)

    def draw_lens_ui(self, img, now):
        q = self.quad
        locked = self.locked_at is not None
        col = MAGENTA if locked else YELLOW
        for i in range(4):
            p = q[i]
            for nb in (q[i - 1], q[(i + 1) % 4]):
                v = nb - p
                u = v / (np.linalg.norm(v) + 1e-6)
                cv2.line(img, tuple(p.astype(int)), tuple((p + u * 30).astype(int)), col, 4, cv2.LINE_AA)
        # horizon line through the middle
        m1, m2 = (q[0] + q[3]) / 2, (q[1] + q[2]) / 2
        cv2.line(img, tuple(m1.astype(int)), tuple(m2.astype(int)), (200, 200, 0), 1, cv2.LINE_AA)
        for i in (0, 1):
            cv2.circle(img, tuple(q[i].astype(int)), 9, CYAN, 2, cv2.LINE_AA)
        w = int(np.linalg.norm(q[1] - q[0]))
        h = int(np.linalg.norm(q[3] - q[0]))
        glitch_text(img, f"{self.filt[0]} {w}x{h}", (q[0][0] + 6, q[0][1] - 12), 0.5,
                    MAGENTA if locked else YELLOW, 1)
        if locked:
            n = COUNTDOWN - int(now - self.locked_at)
            c = q.mean(0)
            glitch_text(img, str(max(n, 1)), (c[0], c[1] + 28), 3.0, YELLOW, 6, center=True)

    def tilt(self):
        q = self.quad
        d = q[1] - q[0]
        roll = math.degrees(math.atan2(d[1], d[0]))
        c = q.mean(0)
        pitch = (0.5 - c[1] / TINGGI) * 90      # virtual camera angles from frame position
        yaw = (c[0] / LEBAR - 0.5) * 90
        return int(roll), int(pitch), int(yaw)

    # ---- DRAW ----
    def update_draw(self, hands, now):
        pen = next((h for h in hands if is_index_only(h)), None)
        if pen is not None:
            tip = pen.pts[8]
            self.pen_pos = tip if self.pen_pos is None or not self.pen_down else (
                self.pen_pos * 0.4 + tip * 0.6)
            if not self.pen_down:
                self.strokes.append(deque())
                self.pen_down = True
            s = self.strokes[-1]
            if not s or _d((s[-1][0], s[-1][1]), self.pen_pos) > 2:
                s.append((float(self.pen_pos[0]), float(self.pen_pos[1]), now))
        else:
            self.pen_down = False
            self.pen_pos = None
        for s in self.strokes:
            while s and now - s[0][2] > TRAIL_LIFE:
                s.popleft()
        self.strokes = [s for i, s in enumerate(self.strokes)
                        if s or (i == len(self.strokes) - 1 and self.pen_down)]

    def draw_neon(self, img, now):
        if not any(len(s) > 1 for s in self.strokes):
            return
        glow = np.zeros_like(img)
        core = np.zeros_like(img)
        for s in self.strokes:
            pts = list(s)
            for i in range(1, len(pts)):
                x0, y0, _ = pts[i - 1]
                x1, y1, t1 = pts[i]
                a = max(0.0, 1 - (now - t1) / TRAIL_LIFE) ** 0.5
                p0, p1 = (int(x0), int(y0)), (int(x1), int(y1))
                cv2.line(glow, p0, p1, tuple(int(c * a) for c in CYAN), 16, cv2.LINE_AA)
                cv2.line(core, p0, p1, tuple(int(c * a) for c in CYAN), 6, cv2.LINE_AA)
                cv2.line(core, p0, p1, tuple(int(255 * a) for _ in range(3)), 2, cv2.LINE_AA)
        glow = cv2.GaussianBlur(glow, (0, 0), 8)
        cv2.add(img, glow, dst=img)
        cv2.add(img, core, dst=img)

    # ---- MAIN STEP ----
    def step(self, raw, hands=None):
        now = time.time()
        dt = max(now - self.last_t, 1e-3)
        self.last_t = now
        self.fps = self.fps * 0.9 + (1 / dt) * 0.1 if self.fps else 1 / dt

        full = cv2.flip(raw, 1)
        self.full = full
        img = cv2.resize(full, (LEBAR, TINGGI))
        if hands is None:
            hands = self.tracker(img) if self.tracker else []

        ui = []                                   # deferred UI draws (after fx)
        if self.mode == LENSA:
            self.update_lens(hands, now)
            if self.quad is not None:
                self.apply_lens_effect(img)
            single = next((h for h in hands if is_index_only(h)), None)
            p = self.d_draw.update(single is not None and self.quad is None and len(hands) == 1, now)
            if p > 0 and single is not None:
                tip = single.pts[8]
                ui.append(lambda im, t=tip, p=p: (ring(im, t, 22, p, CYAN),
                                                  glitch_text(im, "MODE GAMBAR", (t[0], t[1] - 34), 0.55, WHITE, 2, True)))
            if p >= 1:
                self.mode = GAMBAR
                self.reset_lens()
                self.d_draw.reset()
        else:
            self.update_draw(hands, now)
            palm = next((h for h in hands if is_open_palm(h)), None)
            fist = next((h for h in hands if is_fist(h)), None)
            p = self.d_lens.update(palm is not None, now)
            if p > 0 and palm is not None:
                c = palm.pts[9]
                ui.append(lambda im, c=c, p=p: (ring(im, c, 36, p, YELLOW),
                                                glitch_text(im, "MODE LENSA", (c[0], c[1] - 50), 0.55, WHITE, 2, True)))
            if p >= 1:
                self.mode = LENSA
                self.d_lens.reset()
            pc = self.d_clear.update(fist is not None and palm is None, now)
            if pc > 0 and fist is not None:
                c = fist.pts[9]
                ui.append(lambda im, c=c, p=pc: (ring(im, c, 30, p, RED),
                                                 glitch_text(im, "HAPUS", (c[0], c[1] - 44), 0.55, WHITE, 2, True)))
            if pc >= 1:
                self.strokes.clear()
                self.d_clear.reset()

        if self.retro:
            cv2.multiply(img, self.fx_map, dst=img, scale=1 / 255.0)
            img = grain(img, 6)
        if self.mode == GAMBAR:
            self.draw_neon(img, now)
            for h in hands:                         # red fingertip dots
                if self.pen_down and is_index_only(h):
                    cv2.circle(img, tuple(h.pts[8].astype(int)), 11, CYAN, 2, cv2.LINE_AA)
                else:
                    for t in (4, 8, 12, 16, 20):
                        cv2.circle(img, tuple(h.pts[t].astype(int)), 4, RED, -1, cv2.LINE_AA)

        # ---- HUD ----
        if int(now * 2) % 2 == 0:
            cv2.circle(img, (30, 36), 9, RED, -1, cv2.LINE_AA)
        glitch_text(img, "REC", (50, 46), 0.9, WHITE, 2)
        stamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        (tw, _), _ = cv2.getTextSize(stamp, FONT, 0.6, 2)
        glitch_text(img, stamp, (LEBAR - tw - 20, 42), 0.6, WHITE, 2)
        cx, cy = LEBAR // 2, TINGGI // 2
        cv2.line(img, (cx - 10, cy), (cx + 10, cy), WHITE, 2, cv2.LINE_AA)
        cv2.line(img, (cx, cy - 10), (cx, cy + 10), WHITE, 2, cv2.LINE_AA)

        if self.quad is not None and self.mode == LENSA:
            self.draw_lens_ui(img, now)
            r, p_, y = self.tilt()
            glitch_text(img, f"ROLL {r:+d} PITCH {p_:+d} YAW {y:+d}", (LEBAR - 330, TINGGI - 18), 0.55, YELLOW, 2)
        for f in ui:
            f(img)

        glitch_text(img, f"{self.mode} | {self.filt[0]} | FPS {int(self.fps)} | FOTO {self.fotos}",
                    (20, TINGGI - 18), 0.6, WHITE, 2)
        if now < self.toast[1]:
            glitch_text(img, self.toast[0], (LEBAR // 2, TINGGI - 52), 0.6, YELLOW, 2, True)
        if self.flash > 0:
            img = cv2.addWeighted(img, 1 - self.flash, np.full_like(img, 255), self.flash, 0)
            self.flash = max(0.0, self.flash - dt * 3.0)
        return img


# ============================== MAIN LOOP ===================================


def open_camera():
    for backend in ((cv2.CAP_DSHOW, 0) if sys.platform == "win32" else (0,)):
        cap = cv2.VideoCapture(CAM_INDEX, backend) if backend else cv2.VideoCapture(CAM_INDEX)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAP_W)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAP_H)
            return cap
    return None


def main():
    cap = open_camera()
    if cap is None:
        sys.exit("Kamera tidak bisa dibuka (camera not found). Ubah CAM_INDEX di bagian CONFIG.")
    app = RetroLens(HandTracker())
    cv2.namedWindow(WIN, cv2.WINDOW_AUTOSIZE)
    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        out = app.step(frame)
        cv2.imshow(WIN, out)
        k = cv2.waitKey(1) & 0xFF
        if k in (ord("q"), 27) or cv2.getWindowProperty(WIN, cv2.WND_PROP_VISIBLE) < 1:
            break
        elif k == ord("f"):
            app.fi = (app.fi + 1) % len(FILTERS)
        elif k == ord("m"):
            app.mode = GAMBAR if app.mode == LENSA else LENSA
            app.reset_lens()
        elif k == ord("c"):
            app.strokes.clear()
        elif k == ord("s") and app.quad is not None:
            app.capture(time.time())
        elif k == ord("r"):
            app.retro = not app.retro
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
