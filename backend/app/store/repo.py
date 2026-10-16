"""Data access for the rg_* tables.

Money is stored in DynamoDB as integer paise (docs/rules.md section 3) and converted to INR
floats at this boundary, so the rest of the app only sees rupees.
"""

from __future__ import annotations

import copy
from decimal import Decimal
from typing import Any, Protocol

import boto3
from boto3.dynamodb.conditions import Key

from .seed_data import order_amount
from .tables import table_name

MONEY_KEYS = frozenset(
    {"unit_price", "amount", "truth_refundable_amount", "approved_amount", "requested_amount", "order_amount"}
)


def _to_ddb(value: Any, key: str = "") -> Any:
    if isinstance(value, dict):
        return {k: _to_ddb(v, k) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_to_ddb(v, key) for v in value]
    if isinstance(value, bool):
        return value
    if key in MONEY_KEYS and isinstance(value, int | float):
        return round(value * 100)
    if isinstance(value, float):
        return Decimal(str(value))
    return value


def _from_ddb(value: Any, key: str = "") -> Any:
    if isinstance(value, dict):
        return {k: _from_ddb(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_from_ddb(v, key) for v in value]
    if isinstance(value, Decimal):
        if key in MONEY_KEYS:
            return float(value) / 100
        return int(value) if value == value.to_integral_value() else float(value)
    return value


class Repo(Protocol):
    def get_customer(self, customer_id: str) -> dict[str, Any] | None: ...
    def get_order(self, order_id: str) -> dict[str, Any] | None: ...
    def get_delivery(self, order_id: str) -> dict[str, Any] | None: ...
    def list_refunds(self, customer_id: str) -> list[dict[str, Any]]: ...
    def put_refund(self, refund: dict[str, Any]) -> None: ...
    def put_decision(self, decision: dict[str, Any]) -> None: ...
    def put_review(self, item: dict[str, Any]) -> None: ...
    def update_decision(self, decision_id: str, fields: dict[str, Any]) -> None: ...
    def list_decisions(self) -> list[dict[str, Any]]: ...
    def get_review(self, decision_id: str) -> dict[str, Any] | None: ...
    def update_review(self, decision_id: str, fields: dict[str, Any]) -> None: ...
    def list_reviews(self, status: str | None = None) -> list[dict[str, Any]]: ...
    def list_customers(self) -> list[dict[str, Any]]: ...


def _with_amount(order: dict[str, Any] | None) -> dict[str, Any] | None:
    if order is not None:
        order["order_amount"] = order_amount(order)
    return order


class DynamoRepo:
    def __init__(self, region: str, prefix: str) -> None:
        ddb = boto3.resource("dynamodb", region_name=region)
        self._t = {s: ddb.Table(table_name(prefix, s)) for s in
                   ("customers", "orders", "deliveries", "refunds", "decisions", "review_queue", "sessions")}

    def _get(self, table: str, key: dict[str, str]) -> dict[str, Any] | None:
        item = self._t[table].get_item(Key=key).get("Item")
        return _from_ddb(item) if item else None

    def _put(self, table: str, item: dict[str, Any]) -> None:
        self._t[table].put_item(Item=_to_ddb(item))

    def get_customer(self, customer_id: str) -> dict[str, Any] | None:
        return self._get("customers", {"customer_id": customer_id})

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        return _with_amount(self._get("orders", {"order_id": order_id}))

    def get_delivery(self, order_id: str) -> dict[str, Any] | None:
        return self._get("deliveries", {"order_id": order_id})

    def list_refunds(self, customer_id: str) -> list[dict[str, Any]]:
        resp = self._t["refunds"].query(KeyConditionExpression=Key("customer_id").eq(customer_id))
        return [_from_ddb(i) for i in resp.get("Items", [])]

    def put_customer(self, c: dict[str, Any]) -> None:
        self._put("customers", c)

    def put_order(self, o: dict[str, Any]) -> None:
        self._put("orders", {k: v for k, v in o.items() if k != "order_amount"})

    def put_delivery(self, d: dict[str, Any]) -> None:
        self._put("deliveries", d)

    def put_refund(self, refund: dict[str, Any]) -> None:
        self._put("refunds", refund)

    def put_decision(self, decision: dict[str, Any]) -> None:
        self._put("decisions", decision)

    def put_review(self, item: dict[str, Any]) -> None:
        self._put("review_queue", item)

    def _scan(self, table: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        kwargs: dict[str, Any] = {}
        while True:
            resp = self._t[table].scan(**kwargs)
            items.extend(_from_ddb(i) for i in resp.get("Items", []))
            if "LastEvaluatedKey" not in resp:
                return items
            kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

    def _merge(self, table: str, key: dict[str, str], fields: dict[str, Any]) -> None:
        current = self._get(table, key)
        if current is None:
            raise KeyError(f"{table} {key} not found")
        self._put(table, current | fields)

    def update_decision(self, decision_id: str, fields: dict[str, Any]) -> None:
        self._merge("decisions", {"decision_id": decision_id}, fields)

    def list_decisions(self) -> list[dict[str, Any]]:
        return self._scan("decisions")

    def get_review(self, decision_id: str) -> dict[str, Any] | None:
        return self._get("review_queue", {"decision_id": decision_id})

    def update_review(self, decision_id: str, fields: dict[str, Any]) -> None:
        self._merge("review_queue", {"decision_id": decision_id}, fields)

    def list_reviews(self, status: str | None = None) -> list[dict[str, Any]]:
        items = self._scan("review_queue")
        return [i for i in items if status is None or i.get("status") == status]

    def list_customers(self) -> list[dict[str, Any]]:
        return self._scan("customers")


class InMemoryRepo:
    """Same interface, backed by dicts. Used by tests and offline development."""

    def __init__(self, customers: list[dict[str, Any]], orders: list[dict[str, Any]],
                 deliveries: list[dict[str, Any]], refunds: list[dict[str, Any]]) -> None:
        self.customers = {c["customer_id"]: copy.deepcopy(c) for c in customers}
        self.orders = {o["order_id"]: copy.deepcopy(o) for o in orders}
        self.deliveries = {d["order_id"]: copy.deepcopy(d) for d in deliveries}
        self.refunds = [copy.deepcopy(r) for r in refunds]
        self.decisions: list[dict[str, Any]] = []
        self.review_queue: list[dict[str, Any]] = []

    @classmethod
    def seeded(cls) -> InMemoryRepo:
        from . import seed_data as sd
        return cls(sd.CUSTOMERS, sd.ORDERS, sd.DELIVERIES, sd.REFUNDS)

    def get_customer(self, customer_id: str) -> dict[str, Any] | None:
        return copy.deepcopy(self.customers.get(customer_id))

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        return _with_amount(copy.deepcopy(self.orders.get(order_id)))

    def get_delivery(self, order_id: str) -> dict[str, Any] | None:
        return copy.deepcopy(self.deliveries.get(order_id))

    def list_refunds(self, customer_id: str) -> list[dict[str, Any]]:
        return [copy.deepcopy(r) for r in self.refunds if r["customer_id"] == customer_id]

    def put_refund(self, refund: dict[str, Any]) -> None:
        self.refunds.append(copy.deepcopy(refund))

    def put_decision(self, decision: dict[str, Any]) -> None:
        self.decisions.append(copy.deepcopy(decision))

    def put_review(self, item: dict[str, Any]) -> None:
        self.review_queue.append(copy.deepcopy(item))

    def _find(self, rows: list[dict[str, Any]], decision_id: str) -> dict[str, Any]:
        for r in rows:
            if r["decision_id"] == decision_id:
                return r
        raise KeyError(decision_id)

    def update_decision(self, decision_id: str, fields: dict[str, Any]) -> None:
        self._find(self.decisions, decision_id).update(copy.deepcopy(fields))

    def list_decisions(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self.decisions)

    def get_review(self, decision_id: str) -> dict[str, Any] | None:
        try:
            return copy.deepcopy(self._find(self.review_queue, decision_id))
        except KeyError:
            return None

    def update_review(self, decision_id: str, fields: dict[str, Any]) -> None:
        self._find(self.review_queue, decision_id).update(copy.deepcopy(fields))

    def list_reviews(self, status: str | None = None) -> list[dict[str, Any]]:
        return [copy.deepcopy(r) for r in self.review_queue if status is None or r.get("status") == status]

    def list_customers(self) -> list[dict[str, Any]]:
        return [copy.deepcopy(c) for c in self.customers.values()]
