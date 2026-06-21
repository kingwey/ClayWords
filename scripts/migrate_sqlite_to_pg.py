#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script

Usage:
    python migrate_sqlite_to_pg.py --source test.db --target postgresql://...
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from app.models.entities import (
    Base, User, Studio, Session as ChatSession, SessionMessage,
    DesignTemplate, Design, DesignVersion, Order, OrderLog,
    StudioCraftOverride, IdempotencyKey, Task
)


# Table migration order (respecting foreign keys)
TABLE_ORDER = [
    User,
    Studio,
    ChatSession,
    SessionMessage,
    DesignTemplate,
    Design,
    DesignVersion,
    Order,
    OrderLog,
    StudioCraftOverride,
    IdempotencyKey,
    Task,
]


class MigrationStats:
    """Track migration statistics"""
    def __init__(self):
        self.stats = {}

    def record(self, table_name: str, count: int):
        self.stats[table_name] = count

    def report(self):
        print("\n=== Migration Summary ===")
        for table, count in self.stats.items():
            print(f"  {table:25s}: {count:5d} rows")
        print(f"\nTotal: {sum(self.stats.values())} rows migrated")


async def migrate_table(
    source_session: Session,
    target_session: AsyncSession,
    model_class,
    stats: MigrationStats,
    batch_size: int = 100
):
    """Migrate one table from SQLite to Postgres"""
    table_name = model_class.__tablename__
    print(f"Migrating {table_name}...", end=" ", flush=True)

    # Read all rows from SQLite
    stmt = select(model_class)
    result = source_session.execute(stmt)
    rows = result.scalars().all()

    if not rows:
        print("(empty)")
        stats.record(table_name, 0)
        return

    # Insert in batches to Postgres
    count = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]

        for row in batch:
            # Create new instance with same data
            row_dict = {
                c.name: getattr(row, c.name)
                for c in model_class.__table__.columns
            }
            new_row = model_class(**row_dict)
            target_session.add(new_row)

        await target_session.flush()
        count += len(batch)
        print(f"{count}", end="...", flush=True)

    await target_session.commit()
    print(f" ✓ ({count} rows)")
    stats.record(table_name, count)


async def verify_migration(
    source_session: Session,
    target_session: AsyncSession,
    model_class
) -> bool:
    """Verify row counts match"""
    table_name = model_class.__tablename__

    # Count in SQLite
    source_count = source_session.query(model_class).count()

    # Count in Postgres
    stmt = select(model_class)
    result = await target_session.execute(stmt)
    target_count = len(result.scalars().all())

    if source_count != target_count:
        print(f"  ✗ {table_name}: {source_count} (SQLite) != {target_count} (Postgres)")
        return False

    return True


async def main():
    parser = argparse.ArgumentParser(description="Migrate SQLite to PostgreSQL")
    parser.add_argument("--source", required=True, help="SQLite database path")
    parser.add_argument("--target", required=True, help="PostgreSQL connection URL")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for inserts")
    parser.add_argument("--verify", action="store_true", help="Verify counts after migration")
    args = parser.parse_args()

    print("=== SQLite to PostgreSQL Migration ===")
    print(f"Source: {args.source}")
    print(f"Target: {args.target}")
    print()

    # Create engines
    source_engine = create_engine(f"sqlite:///{args.source}")
    target_engine = create_async_engine(args.target)

    # Create sessions
    SourceSession = sessionmaker(bind=source_engine)
    TargetSession = sessionmaker(bind=target_engine, class_=AsyncSession, expire_on_commit=False)

    stats = MigrationStats()

    try:
        source_session = SourceSession()

        async with TargetSession() as target_session:
            # Migrate each table
            for model_class in TABLE_ORDER:
                await migrate_table(
                    source_session,
                    target_session,
                    model_class,
                    stats,
                    args.batch_size
                )

        # Verification
        if args.verify:
            print("\n=== Verification ===")
            all_ok = True
            async with TargetSession() as target_session:
                for model_class in TABLE_ORDER:
                    if not await verify_migration(source_session, target_session, model_class):
                        all_ok = False

            if all_ok:
                print("✓ All tables verified successfully")
            else:
                print("✗ Verification failed")
                return 1

        stats.report()
        print("\n✓ Migration completed successfully")
        return 0

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        source_session.close()
        await target_engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
