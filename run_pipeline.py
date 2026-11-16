
import csv
import json
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4


# ---------------------------------------
# 1. Configure the pipeline
# ---------------------------------------

PROJECT = Path(__file__).resolve().parent

LOG_DIR = PROJECT / "logs"
RUN_DIR = LOG_DIR / "runs"

LOG_DIR.mkdir(parents=True, exist_ok=True)
RUN_DIR.mkdir(parents=True, exist_ok=True)

RUN_ID = (
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    + "-"
    + uuid4().hex[:8]
)

EVENT_FILE = LOG_DIR / "pipeline_events.jsonl"
LATEST_FILE = LOG_DIR / "latest_run.json"
RUN_LOG = RUN_DIR / f"{RUN_ID}.log"


# ---------------------------------------
# 2. Define the execution sequence
# ---------------------------------------

STAGES = [
    (
        "data_validation",
        ["src/validate_data.py"],
    ),
    (
        "database_loading",
        ["src/load_database.py"],
    ),
    (
        "baseline_forecasting",
        ["src/forecast.py"],
    ),
    (
        "advanced_forecasting",
        ["src/advanced_forecast.py"],
    ),
    (
        "automated_tests",
        ["-m", "unittest", "discover", "-s", "tests", "-v"],
    ),
]


# ---------------------------------------
# 3. Helper functions
# ---------------------------------------

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def save_event(event):
    with EVENT_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event) + "\n")


def save_latest(summary):
    temporary_file = LOG_DIR / "latest_run.tmp"

    temporary_file.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    temporary_file.replace(LATEST_FILE)


def latest_source_date():
    csv_path = PROJECT / "data/raw/workload.csv"

    try:
        with csv_path.open(
            "r", encoding="utf-8", newline=""
        ) as file:
            rows = list(csv.DictReader(file))

        return max(
            date.fromisoformat(row["date"])
            for row in rows
        ).isoformat()

    except (OSError, ValueError, KeyError):
        return None


# ---------------------------------------
# 4. Execute the complete pipeline
# ---------------------------------------

def main():

    print("\nSIGNALBENCH AUTOMATED PIPELINE")
    print("-----------------------------")
    print(f"Run ID: {RUN_ID}")

    started_at = utc_now()
    completed_stages = []
    final_status = "PASS"
    error_message = None

    # A new run must not appear successful
    # until every stage has finished.
    save_latest({
        "run_id": RUN_ID,
        "status": "RUNNING",
        "started_at_utc": started_at,
    })

    for stage_name, arguments in STAGES:

        print(f"\nRUNNING: {stage_name}")

        command = [sys.executable, *arguments]
        stage_start = time.perf_counter()

        try:
            process = subprocess.run(
                command,
                cwd=PROJECT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=240,
                check=False,
            )

            exit_code = process.returncode
            output = process.stdout or ""

        except subprocess.TimeoutExpired:
            exit_code = 124
            output = "Stage timed out after 240 seconds."

        except OSError as exc:
            exit_code = 1
            output = str(exc)

        duration = round(
            time.perf_counter() - stage_start, 2
        )

        status = "PASS" if exit_code == 0 else "FAIL"

        event = {
            "run_id": RUN_ID,
            "timestamp_utc": utc_now(),
            "stage": stage_name,
            "status": status,
            "duration_seconds": duration,
            "exit_code": exit_code,
        }

        save_event(event)

        # Preserve the full output for troubleshooting.
        with RUN_LOG.open(
            "a", encoding="utf-8"
        ) as file:
            file.write(
                f"\n=== {stage_name}: {status} ===\n"
            )
            file.write(output)
            file.write("\n")

        if output:
            print(output)

        print(
            f"{stage_name}: {status} "
            f"({duration:.2f} seconds)"
        )

        completed_stages.append(event)

        if exit_code != 0:
            final_status = "FAIL"
            error_message = (
                f"{stage_name} failed with "
                f"exit code {exit_code}"
            )

            print(f"\nPIPELINE STOPPED: {error_message}")
            break

    # -----------------------------------
    # 5. Save final pipeline health status
    # -----------------------------------

    summary = {
        "run_id": RUN_ID,
        "status": final_status,
        "started_at_utc": started_at,
        "finished_at_utc": utc_now(),
        "stages_completed": len(completed_stages),
        "total_stages": len(STAGES),
        "latest_source_date": latest_source_date(),
        "error": error_message,
        "stage_results": completed_stages,
        "run_log": str(RUN_LOG.relative_to(PROJECT)),
    }

    save_latest(summary)

    save_event({
        "run_id": RUN_ID,
        "timestamp_utc": utc_now(),
        "event": "pipeline_finished",
        "status": final_status,
    })

    print("\nFINAL PIPELINE REPORT")
    print("---------------------")
    print(f"Run ID: {RUN_ID}")
    print(f"Stages executed: {len(completed_stages)}")
    print(f"Pipeline status: {final_status}")
    print(f"Execution log: {RUN_LOG}")
    print(f"Status file: {LATEST_FILE}")

    return 0 if final_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
