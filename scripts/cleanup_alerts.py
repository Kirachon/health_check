import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "server"))

from config import settings  # noqa: E402
from db.models import SessionLocal, AlertEvent  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup old alert events.")
    parser.add_argument("--days", type=int, default=settings.ALERT_EVENT_RETENTION_DAYS)
    args = parser.parse_args()

    if args.days < 1:
        print("Days must be >= 1")
        return 1

    cutoff = datetime.utcnow() - timedelta(days=args.days)
    db = SessionLocal()
    try:
        deleted = (
            db.query(AlertEvent)
            .filter(AlertEvent.created_at < cutoff)
            .delete(synchronize_session=False)
        )
        db.commit()
        print(f"Deleted {deleted} alert events older than {args.days} days.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
