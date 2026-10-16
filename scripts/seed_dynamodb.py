"""Load the Chai & Clay seed data into the rg_* tables (overwrites items with the same keys).

Usage: python scripts/seed_dynamodb.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import get_settings  # noqa: E402
from app.store import seed_data  # noqa: E402
from app.store.repo import DynamoRepo  # noqa: E402


def main() -> None:
    s = get_settings()
    repo = DynamoRepo(region=s.aws_region, prefix=s.ddb_table_prefix)
    for c in seed_data.CUSTOMERS:
        repo.put_customer(c)
    for o in seed_data.ORDERS:
        repo.put_order(o)
    for d in seed_data.DELIVERIES:
        repo.put_delivery(d)
    for r in seed_data.REFUNDS:
        repo.put_refund(r)
    print(
        f"seeded {len(seed_data.CUSTOMERS)} customers, {len(seed_data.ORDERS)} orders, "
        f"{len(seed_data.DELIVERIES)} deliveries, {len(seed_data.REFUNDS)} refunds into {s.aws_region}"
    )


if __name__ == "__main__":
    main()
