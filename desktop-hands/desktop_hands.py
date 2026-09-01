#!/usr/bin/env python3
"""
Desktop Hands — control your entire Mac with hand gestures via webcam.
Part of the Jarvis stack.

Gestures:
  PINCH (OK sign)        -> left click (tap) or click-and-drag (hold)
  OPEN HAND + MOVE       -> move the mouse cursor
  PINCH + DRAG           -> drag (like holding mouse button)
  FIST (hold 0.5s)       -> right click
  PEACE SIGN (V)         -> double click
  THUMBS UP              -> play/pause media

Controls:
  Q or ESC               -> quit
  M                      -> toggle mouse control on/off
  D                      -> toggle debug overlay
  S                      -> toggle smoothing (less jitter)
  +/-                    -> adjust sensitivity
"""

import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import time
import sys
import math
import os

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

SCREEN_W, SCREEN_H = pyautogui.size()

SMOOTHING = 0.4
PINCH_THRESHOLD = 0.045
CLICK_TIME = 0.3
SENSITIVITY = 1.8

mouse_enabled = True
debug_mode = True
smoothing_on = True

prev_x, prev_y = SCREEN_W // 2, SCREEN_H // 2
pinch_start_time = 0
was_pinching = False
is_dragging = False

fist_start_time = 0
is_fist = False
peace_cooldown = 0
thumbs_cooldown = 0

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hand_landmarker.task")


def dist(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def lm_xy(landmark):
    return (landmark.x, landmark.y)


def is_finger_folded(tip, pip_, wrist):
    return dist(tip, wrist) < dist(pip_, wrist)


def detect_fist(lm):
    wrist = lm_xy(lm[0])
    fingers = [
        (lm_xy(lm[8]), lm_xy(lm[6])),
        (lm_xy(lm[12]), lm_xy(lm[10])),
        (lm_xy(lm[16]), lm_xy(lm[14])),
        (lm_xy(lm[20]), lm_xy(lm[18])),
    ]
    folded = sum(1 for tip, pip_ in fingers if is_finger_folded(tip, pip_, wrist))
    thumb_folded = dist(lm_xy(lm[4]), lm_xy(lm[2])) < dist(lm_xy(lm[3]), lm_xy(lm[2]))
    return folded >= 3 and thumb_folded


def detect_peace(lm):
    wrist = lm_xy(lm[0])
    index_up = not is_finger_folded(lm_xy(lm[8]), lm_xy(lm[6]), wrist)
    middle_up = not is_finger_folded(lm_xy(lm[12]), lm_xy(lm[10]), wrist)
    ring_down = is_finger_folded(lm_xy(lm[16]), lm_xy(lm[14]), wrist)
    pinky_down = is_finger_folded(lm_xy(lm[20]), lm_xy(lm[18]), wrist)
    return index_up and middle_up and ring_down and pinky_down


def detect_thumbs_up(lm):
    wrist = lm_xy(lm[0])
    thumb_up = lm[4].y < lm[3].y < lm[2].y
    fingers_folded = all(
        is_finger_folded(lm_xy(lm[tip]), lm_xy(lm[tip - 2]), wrist)
        for tip in [8, 12, 16, 20]
    )
    return thumb_up and fingers_folded


def draw_hand(frame, landmarks, w, h, pinching):
    connections = [
        (0,1),(1,2),(2,3),(3,4),
        (0,5),(5,6),(6,7),(7,8),
        (5,9),(9,10),(10,11),(11,12),
        (9,13),(13,14),(14,15),(15,16),
        (13,17),(17,18),(18,19),(19,20),
        (0,17),
    ]
    color = (0, 255, 0)
    for c in connections:
        p1 = (int(landmarks[c[0]].x * w), int(landmarks[c[0]].y * h))
        p2 = (int(landmarks[c[1]].x * w), int(landmarks[c[1]].y * h))
        cv2.line(frame, p1, p2, color, 2)
    for i, lm in enumerate(landmarks):
        cx, cy = int(lm.x * w), int(lm.y * h)
        r = 6 if i in [4, 8] else 4
        c = (0, 0, 255) if i in [4, 8] else (0, 255, 0)
        cv2.circle(frame, (cx, cy), r, c, -1)

    tx, ty = int(landmarks[4].x * w), int(landmarks[4].y * h)
    ix, iy = int(landmarks[8].x * w), int(landmarks[8].y * h)
    line_color = (0, 0, 255) if pinching else (0, 255, 0)
    cv2.line(frame, (tx, ty), (ix, iy), line_color, 3)


def main():
    global prev_x, prev_y, pinch_start_time, was_pinching
    global is_dragging, mouse_enabled, debug_mode, smoothing_on
    global SENSITIVITY, fist_start_time, is_fist, peace_cooldown, thumbs_cooldown

    BaseOptions = mp.tasks.BaseOptions
    HandLandmarker = mp.tasks.vision.HandLandmarker
    HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
    RunningMode = mp.tasks.vision.RunningMode

    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=RunningMode.IMAGE,
        num_hands=1,
        min_hand_detection_confidence=0.7,
        min_hand_presence_confidence=0.6,
        min_tracking_confidence=0.6,
    )

    landmarker = HandLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: No camera found. Desktop Hands needs a webcam.")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print(f"Desktop Hands running — screen {SCREEN_W}x{SCREEN_H}")
    print("Gestures: PINCH=click/drag  FIST=right-click  V=double-click  THUMBS-UP=play/pause")
    print("Keys: Q=quit  M=toggle-mouse  D=debug  S=smoothing  +/-=sensitivity")
    print()

    gesture_text = ""
    gesture_time = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect(mp_image)

        now = time.time()
        h, w = frame.shape[:2]

        if result.hand_landmarks and len(result.hand_landmarks) > 0:
            lm = result.hand_landmarks[0]

            thumb_tip = lm_xy(lm[4])
            index_tip = lm_xy(lm[8])
            pinch_dist = dist(thumb_tip, index_tip)
            pinching_now = pinch_dist < PINCH_THRESHOLD

            if debug_mode:
                draw_hand(frame, lm, w, h, pinching_now)

            raw_x = lm[8].x
            raw_y = lm[8].y

            margin = 0.1
            norm_x = (raw_x - margin) / (1.0 - 2 * margin)
            norm_y = (raw_y - margin) / (1.0 - 2 * margin)
            norm_x = max(0.0, min(1.0, norm_x))
            norm_y = max(0.0, min(1.0, norm_y))

            target_x = int(norm_x * SCREEN_W * SENSITIVITY)
            target_y = int(norm_y * SCREEN_H * SENSITIVITY)
            target_x = max(0, min(SCREEN_W - 1, target_x))
            target_y = max(0, min(SCREEN_H - 1, target_y))

            if smoothing_on:
                move_x = int(prev_x + (target_x - prev_x) * SMOOTHING)
                move_y = int(prev_y + (target_y - prev_y) * SMOOTHING)
            else:
                move_x = target_x
                move_y = target_y

            prev_x, prev_y = move_x, move_y

            if mouse_enabled:
                if pinching_now and not was_pinching:
                    pinch_start_time = now
                    pyautogui.moveTo(move_x, move_y)

                elif pinching_now and was_pinching:
                    if now - pinch_start_time > CLICK_TIME and not is_dragging:
                        is_dragging = True
                        pyautogui.mouseDown(move_x, move_y)
                        gesture_text = "DRAGGING"
                        gesture_time = now
                    elif is_dragging:
                        pyautogui.moveTo(move_x, move_y)

                elif not pinching_now and was_pinching:
                    if is_dragging:
                        pyautogui.mouseUp(move_x, move_y)
                        is_dragging = False
                        gesture_text = "DROP"
                        gesture_time = now
                    elif now - pinch_start_time < CLICK_TIME:
                        pyautogui.click(move_x, move_y)
                        gesture_text = "CLICK"
                        gesture_time = now

                elif not pinching_now:
                    pyautogui.moveTo(move_x, move_y)

                    if detect_fist(lm):
                        if not is_fist:
                            is_fist = True
                            fist_start_time = now
                        elif now - fist_start_time > 0.5:
                            pyautogui.rightClick(move_x, move_y)
                            gesture_text = "RIGHT CLICK"
                            gesture_time = now
                            is_fist = False
                            fist_start_time = now + 2
                    else:
                        is_fist = False

                    if detect_peace(lm) and now > peace_cooldown:
                        pyautogui.doubleClick(move_x, move_y)
                        gesture_text = "DOUBLE CLICK"
                        gesture_time = now
                        peace_cooldown = now + 1.0

                    if detect_thumbs_up(lm) and now > thumbs_cooldown:
                        pyautogui.press('playpause')
                        gesture_text = "PLAY/PAUSE"
                        gesture_time = now
                        thumbs_cooldown = now + 2.0

                was_pinching = pinching_now

            if debug_mode:
                status = "ON" if mouse_enabled else "OFF"
                cv2.putText(frame, f"Mouse: {status}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, f"Pinch: {pinch_dist:.3f}", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

                state = "PINCH" if pinching_now else "OPEN"
                color = (0, 0, 255) if pinching_now else (0, 255, 0)
                cv2.putText(frame, state, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

                cv2.putText(frame, f"Sens: {SENSITIVITY:.1f}", (10, 120),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)

                if now - gesture_time < 1.5:
                    cv2.putText(frame, gesture_text, (10, 160),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 200, 255), 2)

        cv2.imshow("Desktop Hands - Jarvis", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
        elif key == ord('m'):
            mouse_enabled = not mouse_enabled
            print(f"Mouse control: {'ON' if mouse_enabled else 'OFF'}")
        elif key == ord('d'):
            debug_mode = not debug_mode
            print(f"Debug: {'ON' if debug_mode else 'OFF'}")
        elif key == ord('s'):
            smoothing_on = not smoothing_on
            print(f"Smoothing: {'ON' if smoothing_on else 'OFF'}")
        elif key == ord('+') or key == ord('='):
            SENSITIVITY = min(3.0, SENSITIVITY + 0.1)
            print(f"Sensitivity: {SENSITIVITY:.1f}")
        elif key == ord('-'):
            SENSITIVITY = max(0.5, SENSITIVITY - 0.1)
            print(f"Sensitivity: {SENSITIVITY:.1f}")

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()
    print("Desktop Hands stopped.")


if __name__ == "__main__":
    main()
