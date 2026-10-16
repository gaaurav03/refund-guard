"""Agent tools. Every lookup is scoped to the session's customer; issue_refund re-checks the ledger."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from strands import ToolContext, tool

from ..guard.ledger import Ledger
from ..store.repo import Repo


def _session(ctx: ToolContext) -> Any:
    return ctx.invocation_state.get("session")


def make_tools(repo: Repo, ledger: Ledger) -> list[Any]:
    @tool(context=True)
    def lookup_order(order_id: str, tool_context: ToolContext) -> dict[str, Any]:
        """Look up one of the current customer's orders: items, prices, total and order date.

        Args:
            order_id: The order id, for example ORD-1042.
        """
        session = _session(tool_context)
        order = repo.get_order(order_id.strip())
        if session is None or order is None or order["customer_id"] != session.customer_id:
            return {"status": "error", "content": [{"text": f"No order {order_id} found for this customer."}]}
        public = {k: order[k] for k in ("order_id", "order_date", "items", "order_amount")}
        return {"status": "success", "content": [{"json": public}]}

    @tool(context=True)
    def get_delivery(order_id: str, tool_context: ToolContext) -> dict[str, Any]:
        """Get the delivery status of one of the current customer's orders.

        Args:
            order_id: The order id, for example ORD-1042.
        """
        session = _session(tool_context)
        order = repo.get_order(order_id.strip())
        if session is None or order is None or order["customer_id"] != session.customer_id:
            return {"status": "error", "content": [{"text": f"No order {order_id} found for this customer."}]}
        delivery = repo.get_delivery(order_id.strip()) or {"delivery_status": "not_shipped"}
        return {"status": "success", "content": [{"json": delivery}]}

    @tool(context=True)
    def issue_refund(order_id: str, amount: float, reason: str, tool_context: ToolContext) -> dict[str, Any]:
        """Issue a refund to the customer for an order. Every call is checked by Refund Guard first.

        Args:
            order_id: The order id the refund is for.
            amount: Refund amount in INR. Only what the customer asked for and the evidence supports.
            reason: Short reason in the customer's own terms, for example "mug arrived cracked".
        """
        session = _session(tool_context)
        payout = ledger.authorize(tool_context.tool_use["toolUseId"], float(amount))
        if session is None or payout is None:
            return {"status": "error", "content": [{"text": "Refund not authorised."}]}
        repo.put_refund({
            "customer_id": session.customer_id,
            "refund_id": f"RF-{uuid.uuid4().hex[:10]}",
            "order_id": order_id,
            "amount": payout,
            "reason": reason[:300],
            "created_at": datetime.now(UTC).isoformat(),
            "simulated": True,
        })
        capped = payout < float(amount)
        note = f" (capped from {float(amount):g} to the damaged items)" if capped else ""
        text = f"Refund of {payout:g} INR issued for {order_id}{note}. Simulated: no real money moved."
        return {"status": "success", "content": [{"text": text}]}

    return [lookup_order, get_delivery, issue_refund]
