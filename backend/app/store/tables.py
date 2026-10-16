"""DynamoDB table specs (docs/architecture.md section 3). All on-demand, all tagged."""

from __future__ import annotations

from typing import Any

TAGS = [{"Key": "project", "Value": "refund-guard"}]

# name suffix -> (partition key, sort key or None)
KEYS: dict[str, tuple[str, str | None]] = {
    "customers": ("customer_id", None),
    "orders": ("order_id", None),
    "deliveries": ("order_id", None),
    "refunds": ("customer_id", "refund_id"),
    "decisions": ("decision_id", None),
    "review_queue": ("decision_id", None),
    "sessions": ("session_id", None),
}

TTL_TABLES = {"sessions": "ttl"}


def table_name(prefix: str, suffix: str) -> str:
    return f"{prefix}{suffix}"


def create_table_args(prefix: str, suffix: str) -> dict[str, Any]:
    pk, sk = KEYS[suffix]
    schema = [{"AttributeName": pk, "KeyType": "HASH"}]
    attrs = [{"AttributeName": pk, "AttributeType": "S"}]
    if sk:
        schema.append({"AttributeName": sk, "KeyType": "RANGE"})
        attrs.append({"AttributeName": sk, "AttributeType": "S"})
    return {
        "TableName": table_name(prefix, suffix),
        "KeySchema": schema,
        "AttributeDefinitions": attrs,
        "BillingMode": "PAY_PER_REQUEST",
        "Tags": TAGS,
    }
