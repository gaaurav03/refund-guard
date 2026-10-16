from __future__ import annotations

from decimal import Decimal

from app.store import seed_data
from app.store.repo import InMemoryRepo, _from_ddb, _to_ddb


def test_money_round_trips_as_paise() -> None:
    order = {"order_id": "X", "items": [{"sku": "A", "qty": 2, "unit_price": 299.99}],
             "truth_refundable_amount": 0.1, "note_score": 0.5, "flag": True, "gone": None}
    stored = _to_ddb(order)
    assert stored["items"][0]["unit_price"] == 29999
    assert stored["truth_refundable_amount"] == 10
    assert stored["note_score"] == Decimal("0.5")
    assert "gone" not in stored
    back = _from_ddb({k: (Decimal(v) if isinstance(v, int) and not isinstance(v, bool) else v)
                      for k, v in stored.items()} | {"items": [{"sku": "A", "qty": Decimal(2),
                                                                "unit_price": Decimal(29999)}]})
    assert back["items"][0]["unit_price"] == 299.99
    assert back["items"][0]["qty"] == 2
    assert back["truth_refundable_amount"] == 0.1
    assert back["flag"] is True


def test_seed_covers_all_demo_scenarios() -> None:
    repo = InMemoryRepo.seeded()
    for order_id, customer_id in [("ORD-1042", "CUST-007"), ("ORD-2077", "CUST-011"), ("ORD-3105", "CUST-015"),
                                  ("ORD-4001", "CUST-020"), ("ORD-5150", "CUST-023"), ("ORD-6203", "CUST-031")]:
        order = repo.get_order(order_id)
        assert order is not None and order["customer_id"] == customer_id
        assert repo.get_delivery(order_id) is not None
        assert repo.get_customer(customer_id) is not None


def test_seed_amounts_match_docs() -> None:
    repo = InMemoryRepo.seeded()
    assert repo.get_order("ORD-1042")["order_amount"] == 1050.0  # type: ignore[index]
    assert repo.get_order("ORD-4001")["order_amount"] == 1200.0  # type: ignore[index]
    assert repo.get_order("ORD-6203")["order_amount"] == 2650.0  # type: ignore[index]
    assert sum(r["amount"] for r in repo.list_refunds("CUST-011")) == 6100.0


def test_every_order_has_a_delivery_and_known_customer() -> None:
    customers = {c["customer_id"] for c in seed_data.CUSTOMERS}
    deliveries = {d["order_id"] for d in seed_data.DELIVERIES}
    for o in seed_data.ORDERS:
        assert o["customer_id"] in customers
        assert o["order_id"] in deliveries
