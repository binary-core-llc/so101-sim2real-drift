#!/usr/bin/env python3
"""A small live viewer for the calibration tools: Tk window (Tk 9 and PIL are in the venv; OpenCV here is
headless), or a headless loop for tests and remote use.

    run(step, keys, title, headless=False, max_frames=None)
step() -> (rgb_image_to_show, status_lines); keys = {"space": fn, "q": fn, ...}; a key fn may return "quit".
Mouse clicks call keys["click"](x, y) in image pixels, if given.
Headless: step() is called max_frames times (or until a key fn returns "quit" via feed_keys) and nothing is shown.
"""
import os

import cv2
import numpy as np


def put_lines(rgb, lines, org=(8, 20), scale=0.5, color=(255, 255, 0)):
    out = rgb.copy()
    for i, line in enumerate(lines):
        y = org[1] + i * int(22 * scale / 0.5)
        cv2.putText(out, line, (org[0], y), cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(out, line, (org[0], y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)
    return out


def wrap_lines(lines, width_px, scale=0.5):
    """Break each line at spaces so no drawn line is wider than width_px; items are text or (text, colour)."""
    out = []
    for item in lines:
        text, color = item if isinstance(item, tuple) else (item, None)
        cur = ""
        for word in text.split(" "):
            t = word if not cur else cur + " " + word
            if cur.strip() and cv2.getTextSize(t, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)[0][0] > width_px:
                out.append((cur, color))
                cur = "    " + word
            else:
                cur = t
        out.append((cur, color))
    return out


def text_panel(lines, width, scale=0.5, color=(255, 255, 0)):
    """Black panel below an image: the lines wrapped to its width, so nothing is cut off at the image edge."""
    rows = wrap_lines(lines, width - 16, scale)
    step = int(22 * scale / 0.5)
    out = np.zeros((step * len(rows) + 12, width, 3), np.uint8)
    for i, (text, c) in enumerate(rows):
        cv2.putText(out, text, (8, step * (i + 1)), cv2.FONT_HERSHEY_SIMPLEX, scale, c or color, 1, cv2.LINE_AA)
    return out


def run(step, keys, title="gtc", headless=False, max_frames=None, feed_keys=None, period_ms=30):
    """feed_keys: {frame_index: key} to press keys in headless tests."""
    if headless:
        n = 0
        while max_frames is None or n < max_frames:
            step()
            k = (feed_keys or {}).get(n)
            if k and keys.get(k) and keys[k]() == "quit":
                break
            n += 1
        return n
    import tkinter as tk
    from PIL import Image, ImageTk
    if os.environ.get("GTC_GUI_SMOKE"):          # dry run: open the real window, close it after N frames
        max_frames = int(os.environ["GTC_GUI_SMOKE"])
    root = tk.Tk()
    root.title(title)
    label = tk.Label(root)
    label.pack()
    state = {"n": 0, "photo": None, "scale": 1.0}

    def tick():
        img, _ = step()
        h, w = img.shape[:2]
        s = min(1.0, (root.winfo_screenheight() - 120) / h)
        state["scale"] = s
        if s != 1.0:
            img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
        state["photo"] = ImageTk.PhotoImage(Image.fromarray(np.ascontiguousarray(img)))
        label.configure(image=state["photo"])
        state["n"] += 1
        if max_frames is not None and state["n"] >= max_frames:
            root.destroy()
            return
        root.after(period_ms, tick)

    def on_key(ev):
        name = {" ": "space", "\r": "enter"}.get(ev.char, ev.char or ev.keysym)
        fn = keys.get(name) or keys.get(ev.keysym)
        if fn and fn() == "quit":
            root.destroy()

    def on_click(ev):
        if keys.get("click"):
            keys["click"](ev.x / state["scale"], ev.y / state["scale"])

    root.bind("<Key>", on_key)
    label.bind("<Button-1>", on_click)
    root.after(0, tick)
    root.mainloop()
    return state["n"]

