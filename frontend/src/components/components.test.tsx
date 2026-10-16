import { render, screen } from "@testing-library/react";
import { ApiError, errorKind, friendlyMessage } from "../api/client";
import { decidingSignal, explain, fires } from "../lib/decision";
import type { Decision, Meta, Signals } from "../types/decision";
import { DecisionPanel } from "./DecisionPanel";
import { OutcomeChip } from "./OutcomeChip";
import { SignalReadout } from "./SignalReadout";

const META: Meta = {
  signals: [
    { name: "args_grounded", label: "Args grounded", instructions: "", threshold: 0.5, fires_when: "below" },
    { name: "contradicted", label: "Contradicted", instructions: "", threshold: 0.6, fires_when: "above" },
    { name: "concrete_problem", label: "Concrete", instructions: "", threshold: 0.7, fires_when: "above" },
    { name: "non_evidence", label: "Pressure", instructions: "", threshold: 0.6, fires_when: "above" },
    { name: "over_ask", label: "Over-ask", instructions: "", threshold: 0.6, fires_when: "above" },
    { name: "uncertain", label: "Unsure", instructions: "", threshold: 0.6, fires_when: "above" },
  ],
  policy_steps: { "decider:contradicted": "Store records contradict the claim" },
  rules: { "PC-03": "Amount is zero or larger than the order" },
  max_messages: 20,
};

const SIGNALS: Signals = {
  args_grounded: 0.69, contradicted: 0.73, concrete_problem: 0.3, non_evidence: 0.28, over_ask: 0.18, uncertain: 0.13,
};

const DECISION: Decision = {
  decision_id: "D-1", created_at: "2026-10-16T10:00:00Z", order_id: "ORD-2077", requested_amount: 2400,
  outcome: "deny", approved_amount: 0, decided_by: "decider", policy_step: "decider:contradicted", rule_id: null,
  signals: SIGNALS, key_facts: ["The customer says the order did not arrive, but the delivery record says it was delivered."],
  gullible: true, decision_latency_ms: 212,
};

describe("SignalReadout", () => {
  it("highlights the signal that decided and places ticks at the thresholds", () => {
    render(<SignalReadout signals={SIGNALS} meta={META} policyStep="decider:contradicted" />);
    expect(screen.getByTestId("signal-contradicted")).toHaveAttribute("data-deciding", "true");
    expect(screen.getByTestId("signal-concrete_problem")).not.toHaveAttribute("data-deciding");
    expect(screen.getByTestId("tick-concrete_problem")).toHaveStyle({ left: "70%" });
    expect(screen.getByText("0.73")).toBeInTheDocument();
  });
});

describe("OutcomeChip", () => {
  it.each([
    ["approve", "Approved"],
    ["partial", "Partially approved"],
    ["deny", "Denied"],
    ["escalate", "Sent to a human"],
  ] as const)("renders %s with icon and label", (outcome, label) => {
    render(<OutcomeChip outcome={outcome} amount={outcome === "partial" ? 700 : undefined} />);
    expect(screen.getByTestId(`outcome-${outcome}`)).toHaveTextContent(label);
  });
});

describe("DecisionPanel", () => {
  it("shows key facts, signals and the plain-language reason", () => {
    render(<DecisionPanel d={DECISION} meta={META} />);
    expect(screen.getByText(/delivery record says/)).toBeInTheDocument();
    expect(screen.getByText("Store records contradict the claim")).toBeInTheDocument();
    expect(screen.getByText(/9\/9 passed/)).toBeInTheDocument();
  });

  it("says Decider was not needed when a pre-check fired", () => {
    const d: Decision = { ...DECISION, decided_by: "precheck", rule_id: "PC-03", signals: null, key_facts: [],
      policy_step: "precheck:PC-03" };
    render(<DecisionPanel d={d} meta={META} />);
    expect(screen.getByText(/PC-03 fired/)).toBeInTheDocument();
    expect(screen.getByText(/Decider not needed/)).toBeInTheDocument();
  });
});

describe("decision helpers", () => {
  it("maps policy steps to the deciding signal", () => {
    expect(decidingSignal("decider:args_ungrounded")).toBe("args_grounded");
    expect(decidingSignal("decider:partial")).toBe("over_ask");
    expect(decidingSignal("policy:no_concrete_problem")).toBe("concrete_problem");
    expect(decidingSignal("precheck:PC-03")).toBeNull();
  });

  it("fires in the right direction", () => {
    const args = META.signals[0]!;
    expect(fires(args, 0.49)).toBe(true);
    expect(fires(args, 0.5)).toBe(false);
    expect(fires(META.signals[1]!, 0.6)).toBe(true);
  });

  it("explains fallbacks as fail-closed", () => {
    expect(explain({ ...DECISION, decided_by: "fallback", policy_step: "fallback:x" }, META)).toMatch(/failed closed/);
  });
});

describe("api errors", () => {
  it("maps statuses to kinds and never promises money on error", () => {
    expect(errorKind(429)).toBe("rate_limited");
    expect(errorKind(503)).toBe("budget");
    expect(errorKind(404)).toBe("expired");
    expect(friendlyMessage(new ApiError("server", "boom", 500))).toMatch(/Nothing was refunded/);
    expect(friendlyMessage(new ApiError("offline", "x"))).toMatch(/asleep/);
  });
});

describe("WallOfAttempts", () => {
  it("shows all held-out cases and filters by category", async () => {
    const { WallOfAttempts } = await import("./WallOfAttempts");
    const { fireEvent } = await import("@testing-library/react");
    render(<WallOfAttempts />);
    expect(screen.getAllByRole("row")).toHaveLength(1 + 34);
    fireEvent.click(screen.getByRole("tab", { name: /Prompt injection/ }));
    expect(screen.getAllByRole("row")).toHaveLength(1 + 6);
  });
});

describe("ChatPanel", () => {
  it("re-renders and unmounts cleanly when scroll APIs return Promises (Chromium)", async () => {
    const { ChatPanel } = await import("./ChatPanel");
    const orig = Element.prototype.scrollTo;
    Element.prototype.scrollTo = (() => Promise.resolve()) as unknown as typeof orig;
    try {
      const props = { busy: false, placeholder: "type", onSend: () => undefined };
      const { rerender, unmount } = render(<ChatPanel {...props} messages={[]} />);
      rerender(<ChatPanel {...props} messages={[{ role: "user", text: "hi" }]} />);
      expect(screen.getByText("hi")).toBeTruthy();
      unmount();
    } finally {
      Element.prototype.scrollTo = orig;
    }
  });
});

describe("Markdown", () => {
  it("renders bold, lists and code without raw asterisks, and never injects HTML", async () => {
    const { Markdown } = await import("./Markdown");
    const { container } = render(
      <Markdown text={"Found **ORD-2077**, delivered.\n\n- item `MUG`\n- second\n\n<img src=x onerror=alert(1)>"} />,
    );
    expect(container.querySelector("strong")?.textContent).toBe("ORD-2077");
    expect(container.querySelectorAll("li")).toHaveLength(2);
    expect(container.querySelector("code")?.textContent).toBe("MUG");
    expect(container.textContent).not.toContain("**");
    expect(container.querySelector("img")).toBeNull();
  });
});
