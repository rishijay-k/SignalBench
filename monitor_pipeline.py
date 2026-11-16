
import json
from datetime import date
from pathlib import Path


PROJECT = Path(__file__).resolve().parent
STATUS_FILE = PROJECT / "logs/latest_run.json"

print("\nSIGNALBENCH PIPELINE MONITOR")
print("---------------------------")

if not STATUS_FILE.exists():
    raise SystemExit(
        "No pipeline execution found. "
        "Run python run_pipeline.py first."
    )

try:
    status = json.loads(
        STATUS_FILE.read_text(encoding="utf-8")
    )
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"Cannot read pipeline status: {exc}")

run_status = status.get("status", "UNKNOWN")

print(f"Run ID: {status.get('run_id', 'Unknown')}")
print(f"Pipeline status: {run_status}")
print(f"Started: {status.get('started_at_utc', 'Unknown')}")
print(f"Finished: {status.get('finished_at_utc', 'Not yet')}")
print(
    f"Stages executed: "
    f"{status.get('stages_completed', 0)}"
    f"/{status.get('total_stages', 5)}"
)

# Show the result of every stage
print("\nSTAGE HEALTH")

for stage in status.get("stage_results", []):
    print(
        f"{stage['stage']}: {stage['status']} "
        f"({stage['duration_seconds']} seconds)"
    )

# Check how old the original source data is
source_date = status.get("latest_source_date")

print("\nDATA FRESHNESS")

if source_date:
    latest_date = date.fromisoformat(source_date)
    age_days = (date.today() - latest_date).days

    print(f"Latest source date: {source_date}")
    print(f"Source data age: {age_days} days")

    if age_days < 0:
        print("WARNING: Source dates extend into the future.")
    elif age_days > 2:
        print("WARNING: Source data is more than 2 days old.")
    else:
        print("Source freshness: Within demonstration threshold.")
else:
    print("WARNING: Source date unavailable.")

print("\nFINAL HEALTH RESULT")

if run_status == "PASS":
    print("PIPELINE HEALTH: PASS")
elif run_status == "RUNNING":
    raise SystemExit("PIPELINE HEALTH: RUNNING OR INTERRUPTED")
else:
    raise SystemExit("PIPELINE HEALTH: FAIL")
