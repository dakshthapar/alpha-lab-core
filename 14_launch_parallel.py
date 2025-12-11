import subprocess
import argparse
import time
import sys
import math


def launch_workers(total_days, start_seed, cores, script_path, time_limit_hours=None):
    print(f"--- PARALLEL LAUNCHER: {total_days} DAYS | {cores} CORES ---")
    if time_limit_hours:
        print(f"--- TIME LIMIT: {time_limit_hours} HOURS ---")

    start_time = time.time()
    time_limit_sec = time_limit_hours * 3600 if time_limit_hours else None

    chunk_size = math.ceil(total_days / cores)
    procs = []

    for i in range(cores):
        # Calculate range for this worker
        worker_seed = start_seed + (i * chunk_size)

        # Adjust days for the last worker so we don't over-produce (optional, but good practice)
        remaining = total_days - (i * chunk_size)
        if remaining <= 0:
            break
        worker_days = min(chunk_size, remaining)

        # Use venv python to ensure packages are available
        venv_python = ".venv/bin/python"
        cmd = [
            venv_python,
            script_path,
            "--days",
            str(worker_days),
            "--start-seed",
            str(worker_seed),
        ]

        print(
            f"[{i + 1}/{cores}] Launching Worker: Seed {worker_seed} for {worker_days} days..."
        )

        # Launch independent process
        p = subprocess.Popen(cmd)
        procs.append(p)

    print(f"--- ALL {len(procs)} WORKERS LAUNCHED. MONITORING... ---")

    try:
        # Monitor Logic
        while True:
            # 1. Check Time Limit
            if time_limit_sec and (time.time() - start_time) > time_limit_sec:
                print(
                    f"\n⏰ TIME LIMIT REACHED ({time_limit_hours} hrs). TERMINATING WORKERS..."
                )
                for p in procs:
                    if p.poll() is None:  # If still running
                        p.terminate()
                        # We use terminate (SIGTERM) to let them exit gracefully if possible
                        # But since they are python scripts, they might not catch it instantly.

                # Wait a bit then kill if needed?
                # For simplicity, we just break and let the OS cleanup or wait().
                print("Workers terminated. Exiting.")
                sys.exit(0)

            # 2. Check Execution Status
            poll_results = [p.poll() for p in procs]

            # Check if all finished
            if all(r is not None for r in poll_results):
                print("\n--- ALL WORKERS COMPLETED ---")

                # Check exit codes
                failures = [r for r in poll_results if r != 0]
                if failures:
                    print(f"⚠️  WARNING: {len(failures)} workers failed!")
                    sys.exit(1)
                else:
                    print("✅  SUCCESS: All batches finished cleanly.")
                    sys.exit(0)

            time.sleep(5)  # Check every 5s

    except KeyboardInterrupt:
        print("\n🛑 ABORTING: User Interrupt. Killing workers...")
        for p in procs:
            if p.poll() is None:
                p.kill()
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--total-days", type=int, default=16, help="Total days to generate"
    )
    parser.add_argument("--start-seed", type=int, default=8000, help="Starting seed")
    parser.add_argument(
        "--cores", type=int, default=16, help="Number of parallel processes"
    )
    parser.add_argument(
        "--duration", type=float, default=None, help="Stop after N hours (e.g. 4.0)"
    )
    args = parser.parse_args()

    launch_workers(
        args.total_days,
        args.start_seed,
        args.cores,
        "13_regime_factory.py",
        args.duration,
    )
