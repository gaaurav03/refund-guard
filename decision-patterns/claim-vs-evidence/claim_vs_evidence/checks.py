"""Plain-code argument check: do the tool call's amount and order id match what the person typed?

Decider 2B was unreliable at this exact-matching job (it missed both "agent inflated the amount" cases
in our benchmark, and most LLMs misread the question too), so it is done in code instead. Run it as a
pre-check in your `gather` function, before Decider is asked anything.

It only fires when the person actually typed numbers or order ids; when they did not ("refund the mug"),
it stays silent and the Decider questions plus the code cap handle the call. The number extraction is a
heuristic: it skips numbers followed by units or counts ("250g", "200k followers", "3 days").
"""

from __future__ import annotations

import re
from collections.abc import Iterable

ORDER_RE = re.compile(r"\bORD-\d+\b", re.IGNORECASE)
AMOUNT_RE = re.compile(
    r"(?<![\w.])(?:₹\s*|rs\.?\s*|inr\s*)?(\d{2,6}(?:\.\d{1,2})?)"
    r"(?!\s*(?:k\b|m\b|g\b|gm\b|ml\b|%|x\b|\d|followers|people|days|years))",
    re.IGNORECASE,
)


def mentioned(messages: Iterable[str], *, order_re: re.Pattern[str] = ORDER_RE) -> tuple[list[float], list[str]]:
    """Amounts (>= 10) and order ids the person typed. Order ids are removed before reading amounts."""
    text = " ".join(messages)
    orders = sorted({m.upper() for m in order_re.findall(text)})
    amounts = sorted({float(a) for a in AMOUNT_RE.findall(order_re.sub(" ", text)) if float(a) >= 10})
    return amounts, orders


def args_mismatch(messages: Iterable[str], *, amount: float, order_id: str,
                  order_re: re.Pattern[str] = ORDER_RE) -> str | None:
    """A reason string when the call asks for more than any amount typed, or for an order id never typed."""
    amounts, orders = mentioned(messages, order_re=order_re)
    if amounts and amount > max(amounts) + 0.01:
        return f"the call asks for {amount:g} but the person asked for {', '.join(f'{a:g}' for a in amounts)}"
    if orders and order_id.upper() not in orders:
        return f"the call is for {order_id} but the person mentioned {', '.join(orders)}"
    return None
