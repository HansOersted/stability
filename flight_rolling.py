import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import pandas as pd
import numpy as np

HUD_GREEN = "#00FF5A"
HUD_TEXT = "#00FF88"
HUD_GRID = (0.1, 1.0, 0.3, 0.15)
REF_COLOR = "#FFFF66"
ALT_COLOR = "#00FFC8"

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
    ref = df["Reference"].to_numpy()
    alt = df["Altitude"].to_numpy()

    t0 = t[0]
    t_end = t[-1]

    plt.ion()
    fig, ax = plt.subplots(figsize=(10, 4))

    fig.patch.set_facecolor("black")
    ax.set_facecolor("black")

    ax.set_title("ALTITUDE HUD", fontsize=18, color=HUD_GREEN)
    ax.set_xlabel("TIME (s)", fontsize=15, color=HUD_GREEN)
    ax.set_ylabel("HEIGHT (ft)", fontsize=15, color=HUD_GREEN)

    ax.ticklabel_format(style='plain', useOffset=False)

    ax.grid(True, linewidth=0.7, color=HUD_GRID)

    ref_line, = ax.plot([], [], color=REF_COLOR, linewidth=2.4, label="REFERENCE")
    alt_line, = ax.plot([], [], color=ALT_COLOR, linewidth=2.0, alpha=0.85, label="ALTITUDE")

    ax.legend(
        loc="upper right",
        bbox_to_anchor=(0.98, 0.98),
        facecolor="black",
        edgecolor=HUD_GREEN,
        labelcolor=HUD_TEXT,
        fontsize=12
    )

    vline = ax.axvline(t0, color="red", linestyle="--", linewidth=2)

    time_text = ax.text(
        0.02, 0.90, "",
        transform=ax.transAxes,
        color=HUD_TEXT,
        fontsize=16,
        fontweight="bold"
    )

    ax.set_xlim(t0 - window_s/2, t0 + window_s/2)

    wall0 = time.monotonic()

    MIN_RANGE = 50.0

    def update(_):
        vt = now_virtual_time(t0, wall0, scale)
        idx = np.searchsorted(t, vt)

        ax.set_xlim(vt - window_s/2, vt + window_s/2)
        vline.set_xdata([vt, vt])

        ref_line.set_data(t[:idx], ref[:idx])
        alt_line.set_data(t[:idx], alt[:idx])

        mask = (t >= vt - window_s/2) & (t <= vt + window_s/2)
        win_ref = ref[mask]
        win_alt = alt[mask]

        if len(win_ref) > 5:
            ymin = min(win_ref.min(), win_alt.min())
            ymax = max(win_ref.max(), win_alt.max())

            if ymax - ymin < MIN_RANGE:
                mid = (ymin + ymax) / 2
                ymin, ymax = mid - MIN_RANGE/2, mid + MIN_RANGE/2
            else:
                pad = 0.20 * (ymax - ymin)
                ymin -= pad
                ymax += pad

            ax.set_ylim(ymin, ymax)

        time_text.set_text(f"T = {vt:8.2f} SEC")

        if vt >= t_end:
            ani.event_source.stop()

        return ref_line, alt_line, vline, time_text

    ani = FuncAnimation(
        fig, update,
        interval=1000/fps,
        blit=False,
        cache_frame_data=False
    )

    plt.show(block=True)


if __name__ == "__main__":
    run_clock_only()
