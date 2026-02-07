import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import pandas as pd
import numpy as np

HUD_GREEN = "#00FF5A"
HUD_TEXT = "#00FF88"
HUD_GRID = (0.1, 1.0, 0.3, 0.15)
DERIV_COLOR = "#00FFC8"

plt.rcParams.update({
    "text.usetex": False,
    "font.family": "Consolas",
    "xtick.color": HUD_TEXT,
    "ytick.color": HUD_TEXT,
})

ani = None


def now_virtual_time(t0, wall0, scale):
    return t0 + scale * (time.monotonic() - wall0)


def run_clock_only(window_s=20, fps=30, scale=1.0):

    global ani

    df = pd.read_csv("dense_tracking_data.csv")
    t = df["Time (s)"].to_numpy()
    e = df["Tracking Error"].to_numpy()
    de = df["Tracking Error Derivative"].to_numpy()

    t0 = t[0]
    t_end = t[-1]

    plt.ion()
    fig, ax1 = plt.subplots(figsize=(10, 4))

    fig.patch.set_facecolor("black")
    ax1.set_facecolor("black")

    ax1.set_title("TRACKING ERROR HUD", fontsize=18, color=HUD_GREEN)
    ax1.set_xlabel("TIME (s)", fontsize=15, color=HUD_GREEN)
    ax1.set_ylabel("TRACKING ERROR (ft)", fontsize=15, color=HUD_GREEN)

    ax1.ticklabel_format(style='plain', useOffset=False)

    ax1.grid(True, color=HUD_GRID, linewidth=0.7)

    line_e, = ax1.plot([], [], color=HUD_GREEN, linewidth=2.2)

    ax2 = ax1.twinx()
    ax2.set_ylabel("DERIVATIVE (ft/s)", fontsize=15, color=DERIV_COLOR)
    ax2.ticklabel_format(style='plain', useOffset=False)
    ax2.tick_params(colors=DERIV_COLOR)
    line_de, = ax2.plot([], [], color=DERIV_COLOR, linewidth=1.8, alpha=0.8)

    vline = ax1.axvline(t0, color="red", linestyle="--", linewidth=2)

    time_text = ax1.text(
        0.02, 0.90, "",
        transform=ax1.transAxes,
        color=HUD_TEXT,
        fontsize=16,
        fontweight='bold'
    )

    ax1.set_xlim(t0 - window_s/2, t0 + window_s/2)

    wall0 = time.monotonic()

    MIN_E_RANGE = 10.0
    MIN_DE_RANGE = 10.0

    def update(_):
        vt = now_virtual_time(t0, wall0, scale)
        idx = np.searchsorted(t, vt)

        ax1.set_xlim(vt - window_s/2, vt + window_s/2)
        vline.set_xdata([vt, vt])

        line_e.set_data(t[:idx], e[:idx])
        line_de.set_data(t[:idx], de[:idx])

        mask = (t >= vt - window_s/2) & (t <= vt + window_s/2)
        win_e = e[mask]
        win_de = de[mask]

        if len(win_e) > 5:
            ymin, ymax = win_e.min(), win_e.max()

            if ymax - ymin < MIN_E_RANGE:
                mid = (ymin + ymax) / 2
                ymin, ymax = mid - MIN_E_RANGE/2, mid + MIN_E_RANGE/2
            else:
                pad = 0.15 * (ymax - ymin)
                ymin -= pad
                ymax += pad

            ax1.set_ylim(ymin, ymax)

        if len(win_de) > 5:
            dmin, dmax = win_de.min(), win_de.max()

            if dmax - dmin < MIN_DE_RANGE:
                mid = (dmin + dmax) / 2
                dmin, dmax = mid - MIN_DE_RANGE/2, mid + MIN_DE_RANGE/2
            else:
                pad2 = 0.15 * (dmax - dmin)
                dmin -= pad2
                dmax += pad2

            ax2.set_ylim(dmin, dmax)

        time_text.set_text(f"T = {vt:8.2f} SEC")

        if vt >= t_end:
            ani.event_source.stop()

        return line_e, line_de, vline, time_text

    ani = FuncAnimation(
        fig, update,
        interval=1000/fps,
        blit=False,
        cache_frame_data=False
    )

    plt.show(block=True)


if __name__ == "__main__":
    run_clock_only()
