"""Plots SIL simulation signal waveforms from results/sil_demo_measurements.csv."""

import csv
from pathlib import Path


def plot_results():
    root_dir = Path(__file__).parent.parent
    csv_path = root_dir / "results" / "sil_demo_measurements.csv"

    if not csv_path.exists():
        print(f"Error: {csv_path} does not exist. Please run python scripts/run_sil_demo.py first.")
        return

    timestamps = []
    throttles = []
    interlocks = []
    torques = []
    speeds = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            timestamps.append(float(row["timestamp_ms"]))
            throttles.append(float(row["Throttle_Input"]))
            interlocks.append(float(row["Brake_Interlock"]))
            torques.append(float(row["Motor_Torque"]))
            speeds.append(float(row["Vehicle_Speed"]))

    print(f"\n==========================================================================")
    print(f"      SIL Telemetry Signal Inspection ({len(timestamps)} data points loaded)")
    print(f"==========================================================================")

    # Try plotting using matplotlib if available
    try:
        import matplotlib.pyplot as plt

        plt.figure(figsize=(10, 6))
        plt.subplot(2, 1, 1)
        plt.plot(timestamps, torques, "r-", label="Motor Torque (Nm)", linewidth=2)
        plt.plot(timestamps, speeds, "b--", label="Vehicle Speed (km/h)", linewidth=2)
        plt.title("SIL C-Code Engine Telemetry Trace")
        plt.ylabel("Output Dynamics")
        plt.grid(True)
        plt.legend()

        plt.subplot(2, 1, 2)
        plt.plot(timestamps, throttles, "g-", label="Throttle Input (%)", linewidth=1.5)
        plt.plot(timestamps, interlocks, "m-.", label="HV Interlock State (1=Closed)", linewidth=1.5)
        plt.xlabel("Time (ms)")
        plt.ylabel("Control Demands")
        plt.grid(True)
        plt.legend()

        plt.tight_layout()
        plot_png = root_dir / "results" / "sil_telemetry_plot.png"
        plt.savefig(str(plot_png))
        print(f"Saved graphical plot image to: {plot_png}")
        plt.show()
        return
    except ImportError:
        pass

    # Terminal ASCII Waveform fallback
    print("\n--- Terminal Telemetry Inspection Table ---")
    print(" Time(ms) | Throttle(%) | Interlock | Torque(Nm) | Speed(km/h)")
    print("------------------------------------------------------------")
    for t, thr, intl, trq, spd in zip(timestamps, throttles, interlocks, torques, speeds):
        print(f"  {t:6.1f}  |    {thr:5.1f}   |    {intl:3.1f}    |   {trq:7.1f}  |   {spd:8.1f}")


if __name__ == "__main__":
    plot_results()
