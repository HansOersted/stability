import os
import time
import numpy as np
import pandas as pd
import requests

SRV_URL = "http://45.63.101.248:8000/upload_npz"

def upload_npz_to_server(npz_path):
    try:
        with open(npz_path, "rb") as f:
            resp = requests.post(SRV_URL, files={"file": f}, timeout=3)
        print("📤 Uploaded:", resp.json())
    except Exception as e:
        print("⚠️ Upload failed:", e)

CFG = {
    "scale": 1.0,
    "T": 0.1,
    "input_csv": "dense_tracking_data.csv",
    "output_npz": "input_data.npz",
    "interval": 30.0,
}

EPS = 1e-6


def _find_column(df: pd.DataFrame, candidates) -> str:
    cols = [c.strip() for c in df.columns]
    for name in candidates:
        for c in cols:
            if c == name or c.lower() == name.lower():
                return c
    for name in candidates:
        for c in cols:
            if name.lower() in c.lower():
                return c
    raise KeyError(f"Cannot find column: {candidates}, existing: {list(df.columns)}")


def load_and_prepare(cfg):
    df = pd.read_csv(cfg["input_csv"])
    df.columns = df.columns.str.strip()

    time_col = _find_column(df, ["Time (s)", "Timestamp", "time", "t"])
    df[time_col] = pd.to_numeric(df[time_col], errors="coerce")

    te_col = _find_column(df, ["Tracking Error"])
    dte_col = _find_column(df, ["Tracking Error Derivative"])
    ddte_col = _find_column(df, ["Tracking Error Second Derivative"])

    start_time = float(df[time_col].iloc[0])
    interval = cfg["interval"]

    rel = df[time_col] - start_time
    k = np.floor((rel / interval) + EPS).astype(int)
    keep = np.isclose(rel, k * interval, atol=1e-6)
    df = df.loc[keep].reset_index(drop=True)

    return df, time_col, te_col, dte_col, ddte_col, start_time


def update_input_data():
    df, time_col, te_col, dte_col, ddte_col, start_time = load_and_prepare(CFG)
    total_length = len(df)

    print(f"[INFO] Data length: {total_length}, interval={CFG['interval']}")

    wall0 = time.monotonic()
    next_idx = 0
    next_tick = start_time

    while True:
        vt = start_time + (time.monotonic() - wall0) * CFG["scale"]

        updated_any = False

        while next_idx < total_length and vt + EPS >= next_tick:
            data_points = df.iloc[:next_idx + 1]
            e_data = data_points[[te_col, dte_col]].to_numpy()
            de_data = data_points[[dte_col, ddte_col]].to_numpy()

            np.savez(CFG["output_npz"], e=e_data, de=de_data)

            print(f"[UPDATE] input_data.npz updated at virtual time {next_tick}")

            upload_npz_to_server(CFG["output_npz"])

            next_idx += 1
            next_tick = start_time + next_idx * CFG["interval"]
            updated_any = True

        if next_idx >= total_length:
            print("Finished all updates.")
            break

        if not updated_any:
            time.sleep(CFG["T"])


if __name__ == "__main__":
    update_input_data()
