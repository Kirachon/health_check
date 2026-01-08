import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "server"))

from db.models import SessionLocal, User  # noqa: E402
from services.auth_service import get_password_hash  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an admin user.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--role", default="admin")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == args.username).first()
        if existing:
            print(f"User already exists: {args.username}")
            return 1

        user = User(
            username=args.username,
            password_hash=get_password_hash(args.password),
            role=args.role,
        )
        db.add(user)
        db.commit()
        print(f"Created user: {args.username} (role: {args.role})")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
