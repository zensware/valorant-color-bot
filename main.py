import sys
import threading
import time
import numpy as np
import keyboard
import mss
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget, QGraphicsDropShadowEffect
import pyautogui
import os
import json

with open("config.json", "r") as f:
    config = json.load(f)

SCAN_SIZE = config["SCAN_SIZE"]
TOLERANCE = config["TOLERANCE"]
CLICK_DELAY = config["CLICK_DELAY"]

SHOOT_BIND_OPTIONS = config.get("SHOOT_BIND_OPTIONS", ["7", "8", "9", "0"])
SHOOT_BIND = config.get("SHOOT_BIND", SHOOT_BIND_OPTIONS[0])
if SHOOT_BIND not in SHOOT_BIND_OPTIONS:
    SHOOT_BIND = SHOOT_BIND_OPTIONS[0]

HoldKey = config.get("HOLD_KEY", "e")
ToggleKey = config.get("TOGGLE_KEY", "insert")
QuitKey = config.get("QUIT_KEY", "delete")

MODE = config.get("MODE", "TOGGLE").upper()
DEFAULT_COLORS = [np.array(color) for color in config["DEFAULT_COLORS"]]

running = False
holding = False
bind_index = SHOOT_BIND_OPTIONS.index(SHOOT_BIND)

def make_label(text, size=12, color="#e3dcff", weight="normal"):
    label = QLabel(text)
    label.setStyleSheet(f"color: {color}; font-size: {size}px; font-weight: {weight};")
    label.setAlignment(Qt.AlignCenter)
    return label

class OSD(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setGeometry(20, 40, 160, 160)

        self.bg_widget = QWidget(self)
        self.bg_widget.setObjectName("bg_widget")
        self.bg_widget.setStyleSheet("""
            QWidget#bg_widget {
                background-color: rgba(28, 21, 40, 230);
                border-radius: 15px;
                border: 1px solid #30294a;
            }
        """)
        self.bg_widget.setGeometry(self.rect())

        layout = QVBoxLayout(self.bg_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(6)

        self.label1 = make_label("zensware.com", 14, "#bb86fc", "bold")
        self.label2 = make_label("Color Bot | v0.1", 12, "#cfc4ff")
        self.label3 = make_label(f"Method: {MODE.title()}", 12, "#c0b3e6")
        self.label4 = make_label(f"Shootbind: {SHOOT_BIND}", 12, "#c0b3e6")
        self.status_label = make_label("State: OFF", 12, "#ff4d4d")

        for lbl in [self.label1, self.label2, self.label3, self.label4, self.status_label]:
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(10)
            shadow.setOffset(0, 0)
            shadow.setColor(QtGui.QColor("black"))
            lbl.setGraphicsEffect(shadow)
            layout.addWidget(lbl)

    @pyqtSlot()
    def update_status(self):
        self.status_label.setText(f"State: {'ON' if running else 'OFF'}")
        self.status_label.setStyleSheet(f"color: {'#00ff00' if running else '#ff4d4d'}; font-size: 12px;")
        self.label4.setText(f"Shootbind: {SHOOT_BIND_OPTIONS[bind_index]}")

def find_color(img):
    for color in DEFAULT_COLORS:
        lower_bound = color - TOLERANCE
        upper_bound = color + TOLERANCE
        match = np.all((img >= lower_bound) & (img <= upper_bound), axis=2)
        if np.any(match):
            return True
    return False

def scan_and_click():
    global running
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        region = {
            "top": (monitor['height'] // 2) - SCAN_SIZE,
            "left": (monitor['width'] // 2) - SCAN_SIZE,
            "width": SCAN_SIZE * 2,
            "height": SCAN_SIZE * 2
        }

        buffer_shape = (SCAN_SIZE * 2, SCAN_SIZE * 2, 3)

        while True:
            if running:
                sct_img = sct.grab(region)
                img = np.frombuffer(sct_img.rgb, dtype=np.uint8).reshape(buffer_shape)
                if find_color(img):
                    keyboard.press_and_release(SHOOT_BIND_OPTIONS[bind_index])
                    print('[ACTION] Color detected, shot fired.')
                    if CLICK_DELAY > 0:
                        time.sleep(CLICK_DELAY)
                time.sleep(0.001)
            else:
                time.sleep(0.02)

def toggle_running(osd):
    global running
    running = not running
    QtCore.QMetaObject.invokeMethod(osd, "update_status", QtCore.Qt.QueuedConnection)

def handle_hold_mode(osd):
    global running, holding
    while True:
        if keyboard.is_pressed(HoldKey):
            if not holding:
                holding = True
                running = True
                QtCore.QMetaObject.invokeMethod(osd, "update_status", QtCore.Qt.QueuedConnection)
        else:
            if holding:
                holding = False
                running = False
                QtCore.QMetaObject.invokeMethod(osd, "update_status", QtCore.Qt.QueuedConnection)
        time.sleep(0.01)

def monitor_keys(osd):
    global bind_index
    keyboard.add_hotkey(QuitKey, lambda: os._exit(0))

    if MODE == "TOGGLE":
        keyboard.add_hotkey(ToggleKey, lambda: toggle_running(osd))
    elif MODE == "HOLD":
        threading.Thread(target=handle_hold_mode, args=(osd,), daemon=True).start()

    keyboard.add_hotkey("right", lambda: switch_bind(osd))
    keyboard.wait()

def switch_bind(osd):
    global bind_index
    bind_index = (bind_index + 1) % len(SHOOT_BIND_OPTIONS)
    print("[Update] Shootbind has been switched.")
    QtCore.QMetaObject.invokeMethod(osd, "update_status", QtCore.Qt.QueuedConnection)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    osd = OSD()
    osd.show()

    threading.Thread(target=scan_and_click, daemon=True).start()
    threading.Thread(target=monitor_keys, args=(osd,), daemon=True).start()
    sys.exit(app.exec_())