"""
Create all database tables (dev utility).

WARNING: This drops all tables first. Use only in development.
"""
import asyncio

from app.database import engine, Base

# Import models so they are registered on Base.metadata
from app import models  # noqa: F401


async def main() -> None:
    async with engine.begin() as conn:
        # Dev-only: reset schema
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    print("✅ Tables created successfully")


if __name__ == "__main__":
    asyncio.run(main())
