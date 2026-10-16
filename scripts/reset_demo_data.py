"""Reset the public demo to a clean start: no decisions, empty review queue, only the seeded past refunds.

Deletes every item in rg_decisions, rg_review_queue and rg_sessions, removes refunds that are not part of the
seed data, then re-seeds customers, orders, deliveries and past refunds. Run it before the judging window
(and after your own testing) so the scoreboard starts at zero. It does NOT touch the benchmark results.

Usage: python scripts/reset_demo_data.py --yes
"""

from __future__ import annotations

import sys
from pathlib import Path

import boto3

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import get_settings  # noqa: E402
from app.store import seed_data  # noqa: E402
from app.store.tables import KEYS, table_name  # noqa: E402

WIPE = ("decisions", "review_queue", "sessions")


def _keys(table, suffix: str):  # type: ignore[no-untyped-def]
    pk, sk = KEYS[suffix]
    attrs = [pk] + ([sk] if sk else [])
    kwargs = {"ProjectionExpression": ", ".join(f"#{i}" for i in range(len(attrs))),
              "ExpressionAttributeNames": {f"#{i}": a for i, a in enumerate(attrs)}}
    while True:
        page = table.scan(**kwargs)
        yield from ({a: item[a] for a in attrs} for item in page.get("Items", []))
        if "LastEvaluatedKey" not in page:
            return
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def main() -> None:
    if "--yes" not in sys.argv:
        sys.exit("This deletes all demo decisions and the review queue. Re-run with --yes.")
    s = get_settings()
    ddb = boto3.resource("dynamodb", region_name=s.aws_region)
    for suffix in WIPE:
        t = ddb.Table(table_name(s.ddb_table_prefix, suffix))
        n = 0
        with t.batch_writer() as w:
            for k in list(_keys(t, suffix)):
                w.delete_item(Key=k)
                n += 1
        print(f"{t.name}: deleted {n}")

    seeded = {r["refund_id"] for r in seed_data.REFUNDS}
    t = ddb.Table(table_name(s.ddb_table_prefix, "refunds"))
    extra = [k for k in _keys(t, "refunds") if k["refund_id"] not in seeded]
    with t.batch_writer() as w:
        for k in extra:
            w.delete_item(Key=k)
    print(f"{t.name}: removed {len(extra)} demo refunds, kept {len(seeded)} seeded")

    import runpy
    runpy.run_path(str(Path(__file__).with_name("seed_dynamodb.py")), run_name="__main__")


if __name__ == "__main__":
    main()
