"""Create the rg_* DynamoDB tables (idempotent). Use --delete to remove them all.

Usage:
  python scripts/create_tables.py            # create missing tables, wait until ACTIVE
  python scripts/create_tables.py --delete   # delete every rg_* table
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import get_settings  # noqa: E402
from app.store.tables import KEYS, TTL_TABLES, create_table_args, table_name  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--delete", action="store_true")
    args = ap.parse_args()

    s = get_settings()
    ddb = boto3.client("dynamodb", region_name=s.aws_region)
    existing = set(ddb.list_tables()["TableNames"])
    names = [table_name(s.ddb_table_prefix, k) for k in KEYS]

    if args.delete:
        for n in names:
            if n in existing:
                ddb.delete_table(TableName=n)
                print(f"deleting {n}")
        return

    for suffix in KEYS:
        n = table_name(s.ddb_table_prefix, suffix)
        if n in existing:
            print(f"exists   {n}")
            continue
        ddb.create_table(**create_table_args(s.ddb_table_prefix, suffix))
        print(f"creating {n}")

    waiter = ddb.get_waiter("table_exists")
    for n in names:
        waiter.wait(TableName=n)

    for suffix, attr in TTL_TABLES.items():
        n = table_name(s.ddb_table_prefix, suffix)
        try:
            ddb.update_time_to_live(TableName=n, TimeToLiveSpecification={"Enabled": True, "AttributeName": attr})
            print(f"ttl on   {n}.{attr}")
        except ClientError as e:
            if "already enabled" not in str(e):
                raise
    print(f"all {len(names)} tables ACTIVE in {s.aws_region}")


if __name__ == "__main__":
    main()
