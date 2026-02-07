# usr_receiver.py
import os
import time
import threading
import numpy as np
import requests
import tkinter as tk
import re

from io import BytesIO
from PIL import Image, ImageTk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa

SRV_BASE = "http://45.63.101.248:8000"
NPZ_PATH = "input_data.npz"
TRIGGER_DELAY = 1
MIN_POINTS = 1

last_mtime = None
pending_timer = None

ui_started = False
ui_root = None
ui_title_label = None
ui_formula_label = None
ui_surface_label = None

def render_formula_latex_to_label(formula: str, target_label: tk.Label):
    formula = formula.strip() or r"V = \text{N/A}"

    fig, ax = plt.subplots(figsize=(5.6, 0.75))
    ax.text(
        0.5, 0.5,
        f"${formula}$",
        fontsize=10,
        ha="center",
        va="center"
    )
    ax.axis("off")

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=140, pad_inches=0.005)
    buf.seek(0)

    img = Image.open(buf)
    photo = ImageTk.PhotoImage(img)

    target_label.configure(image=photo)
    target_label.image = photo
    plt.close(fig)


def parse_quadratic_coeffs(formula: str):
    a = b = c = 0.0
    patterns = {
        "a": r"([+-]?\d*\.?\d+)\s*\\cdot\s*e\^2",
        "b": r"([+-]?\d*\.?\d+)\s*\\cdot\s*e\s*\\cdot\s*\\dot\{\{?e\}?\}",
        "c": r"([+-]?\d*\.?\d+)\s*\\cdot\s*\\dot\{\{?e\}?\}\^2",
    }
    for k, p in patterns.items():
        m = re.search(p, formula)
        if m:
            if k == "a":
                a = float(m.group(1))
            elif k == "b":
                b = float(m.group(1))
            elif k == "c":
                c = float(m.group(1))
    return a, b, c


def render_lyapunov_surface_to_label(formula: str, target_label: tk.Label):
    a, b, c = parse_quadratic_coeffs(formula)

    e = np.linspace(-1, 1, 45)
    de = np.linspace(-1, 1, 45)
    E, DE = np.meshgrid(e, de)
    V = a * E**2 + b * E * DE + c * DE**2

    V_disp = V - V.min()
    z_max = V_disp.max() * 1.05

    fig = plt.figure(figsize=(4.4, 3.0))
    ax = fig.add_subplot(111, projection="3d")

    surf = ax.plot_surface(
        E, DE, V_disp,
        cmap="plasma",
        linewidth=0,
        antialiased=True,
        alpha=0.95
    )

    ax.set_xlabel("e", fontname="Times New Roman",
                  fontstyle="italic", fontsize=8, labelpad=4)
    ax.set_ylabel("ė", fontname="Times New Roman",
                  fontstyle="italic", fontsize=8, labelpad=4)
    ax.set_zlabel("V", fontname="Times New Roman",
                  fontstyle="italic", fontsize=8, labelpad=4)

    ax.tick_params(axis="both", labelsize=7)
    ax.tick_params(axis="z", labelsize=7)

    ax.set_zlim(0, z_max)
    ax.view_init(elev=25, azim=-60)

    cbar = fig.colorbar(
        surf,
        ax=ax,
        shrink=0.55,
        aspect=20,
        pad=0.20
    )
    cbar.ax.tick_params(labelsize=7)
    cbar.set_label(
        "V",
        fontname="Times New Roman",
        fontstyle="italic",
        fontsize=8
    )

    fig.subplots_adjust(left=0.04, right=0.86, bottom=0.05, top=0.96)

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=120, pad_inches=0.02)
    buf.seek(0)

    img = Image.open(buf)
    photo = ImageTk.PhotoImage(img)

    target_label.configure(image=photo)
    target_label.image = photo
    plt.close(fig)


def start_waiting_ui():
    global ui_root, ui_title_label, ui_formula_label, ui_surface_label

    ui_root = tk.Tk()
    ui_root.title("Controller Status")
    ui_root.geometry("900x700")
    ui_root.configure(bg="white")

    frame = tk.Frame(ui_root, bg="white")
    frame.pack(expand=True, fill="both", padx=20, pady=20)

    ui_title_label = tk.Label(
        frame,
        text="⏳ WAITING ⏳\n\nReceiving data...\n\nStability analysis is running.",
        font=("Times New Roman", 22),
        fg="green",
        bg="white",
        justify="center",
    )
    ui_title_label.pack(pady=(20, 8))

    ui_formula_label = tk.Label(frame, bg="white")
    ui_formula_label.pack(pady=(0, 2))

    ui_surface_label = tk.Label(frame, bg="white")
    ui_surface_label.pack(pady=(2, 0))

    ui_root.mainloop()


def switch_to_fail_ui():
    if ui_root is None:
        return

    def _update():
        ui_root.configure(bg="#ffecec")
        ui_title_label.configure(
            text="🚨 ALERT 🚨\n\nController may be unstable.",
            fg="red",
            bg="#ffecec",
            font=("Times New Roman", 24),
        )
        ui_formula_label.configure(image="")
        ui_surface_label.configure(image="")

    ui_root.after(0, _update)


def switch_to_success_ui():
    if ui_root is None:
        return

    formula = ""
    if os.path.exists("formula_from_srv.txt"):
        with open("formula_from_srv.txt", "r", encoding="utf-8") as f:
            formula = f.read().strip()

    def _update():
        ui_root.configure(bg="white")
        ui_title_label.configure(
            text="✅ CONTROLLER IS FUNCTIONAL ✅\n\n"
                 "The controller is proved stable.\n\n"
                 "Stability certificate:",
            fg="green",
            bg="white",
            font=("Times New Roman", 18),
        )
        render_formula_latex_to_label(formula, ui_formula_label)
        render_lyapunov_surface_to_label(formula, ui_surface_label)

    ui_root.after(0, _update)


def query_srv_once():
    try:
        r = requests.get(f"{SRV_BASE}/result/status", timeout=2)
        status = r.json().get("status", "unknown")
        print("[USR] status =", status)

        if status == "fail":
            switch_to_fail_ui()
        elif status == "success":
            r = requests.get(f"{SRV_BASE}/result/formula", timeout=2)
            formula = r.json().get("formula", "")
            if formula:
                with open("formula_from_srv.txt", "w", encoding="utf-8") as f:
                    f.write(formula)
            switch_to_success_ui()

    except Exception as e:
        print("[USR] query failed:", e)


def schedule_query():
    global pending_timer
    if pending_timer:
        pending_timer.cancel()
    pending_timer = threading.Timer(TRIGGER_DELAY, query_srv_once)
    pending_timer.start()


def monitor_npz():
    global last_mtime, ui_started

    while True:
        if os.path.exists(NPZ_PATH):
            mtime = os.path.getmtime(NPZ_PATH)
            if last_mtime is None or mtime != last_mtime:
                last_mtime = mtime
                data = np.load(NPZ_PATH)
                n = len(data["e"])

                if n >= 1 and not ui_started:
                    ui_started = True
                    threading.Thread(
                        target=start_waiting_ui,
                        daemon=True
                    ).start()

                if n >= MIN_POINTS:
                    schedule_query()

        time.sleep(0.1)

if __name__ == "__main__":
    monitor_npz()
