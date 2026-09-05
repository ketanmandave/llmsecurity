"""Create a short-lived JWT for local API testing only."""

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt


# Allow this script to import the app package when executed from the repository.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.models.enums import AccessRole  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", default="local-admin")
    parser.add_argument(
        "--roles",
        nargs="+",
        choices=[role.value for role in AccessRole],
        default=[AccessRole.ADMIN.value],
    )
    parser.add_argument("--minutes", type=int, default=60)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    if settings.environment.lower() != "development":
        raise SystemExit("Development tokens can only be created in development mode.")
    if args.minutes < 1 or args.minutes > 1440:
        raise SystemExit("--minutes must be between 1 and 1440.")

    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": args.user_id,
            "roles": args.roles,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": now + timedelta(minutes=args.minutes),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    print(token)


if __name__ == "__main__":
    main()
