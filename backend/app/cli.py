"""CLI utilities for CloakHaven platform administration."""

import asyncio
import sys

from sqlalchemy import select
from app.database import engine, async_session_maker, Base
from app.models.user import User


async def _make_admin(email: str) -> None:
    """Promote a user to admin by email address."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            print(f"Error: no user found with email '{email}'")
            sys.exit(1)
        if user.is_admin:
            print(f"'{email}' is already an admin.")
            return
        user.is_admin = True
        await db.commit()
        print(f"'{email}' is now an admin.")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m app.cli <command> [args]")
        print("Commands:")
        print("  make-admin <email>   — promote a user to admin")
        sys.exit(1)

    command = sys.argv[1]

    if command == "make-admin":
        if len(sys.argv) < 3:
            print("Usage: python -m app.cli make-admin <email>")
            sys.exit(1)
        asyncio.run(_make_admin(sys.argv[2]))
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
