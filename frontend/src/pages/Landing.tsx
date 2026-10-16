import { Link } from "react-router-dom";
import { SectionLabel } from "../components/Layout";
import { SignalReadout } from "../components/SignalReadout";
import { OutcomeChip } from "../components/OutcomeChip";
import { useMeta } from "../lib/hooks";
import type { Signals } from "../types/decision";

// Real Decider answers for S2 ("never arrived", but delivered with proof), dev case B-006.
const EXAMPLE: Signals = {
  args_grounded: 0.689,
  contradicted: 0.726,
  concrete_problem: 0.298,
  non_evidence: 0.279,
  over_ask: 0.181,
  uncertain: 0.129,
};

const QUESTIONS: [string, string][] = [
  ["args_grounded", "Are the refund's arguments grounded in what the customer actually said?"],
  ["contradicted", "Do the store's records contradict the claim?"],
  ["concrete_problem", "Does the customer describe a specific, concrete problem?"],
  ["non_evidence", "Is the customer relying on authority, threats or instructions instead of evidence?"],
  ["over_ask", "Is the amount larger than the value of the affected items?"],
  ["uncertain", "Is the customer unsure, or is it a matter of taste?"],
];

const FLOW: [string, string][] = [
  ["Chat", "Amazon Bedrock (Nova 2 Lite) talks to the customer and decides to call issue_refund."],
  ["Intercept", "A Strands InterventionHandler stops the call before it runs."],
  ["Pre-checks", "Nine plain rules: wrong order, amount above the order, already refunded, window closed…"],
  ["Decider 2B", "Six typed yes/no questions about the evidence, answered in one call. No text, just probabilities."],
  ["Policy", "Plain code turns the six answers into approve, partial, deny or escalate, and computes the amount."],
  ["Ledger", "issue_refund only pays what the guard approved for that exact call. Everything is logged."],
];

const SECTION = "mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20";

export function Landing() {
  const meta = useMeta();
  return (
    <>
      {/* Hero */}
      <section className="mx-auto max-w-6xl px-4 pb-16 pt-16 sm:px-6 sm:pt-24">
        <p className="label mb-6">strands decider 2b × amazon bedrock · guardrails</p>
        <h1 className="max-w-3xl text-5xl leading-[1.05] sm:text-7xl">The support agent you can't scam.</h1>
        <p className="mt-6 max-w-prose text-lg text-muted">
          <span className="cursor">
            An AI support agent for a small online store. Before any refund moves money, Strands Decider 2B checks the claim
            against the evidence.
          </span>
        </p>
        <div className="mt-10 flex flex-wrap gap-3">
          <Link to="/try" className="btn-primary">Try to scam it →</Link>
          <a href="#how-it-works" className="btn-ghost">How it works</a>
        </div>
        <dl className="mt-16 grid max-w-3xl grid-cols-2 gap-6 sm:grid-cols-4">
          {[
            ["94%", "accuracy on 34 unseen cases"],
            ["0 / 20", "attacks that got money"],
            ["0 / 8", "genuine customers denied"],
            ["18%", "sent to a human"],
          ].map(([v, l]) => (
            <div key={l}>
              <dt className="font-mono text-2xl">{v}</dt>
              <dd className="mt-1 text-[13px] text-muted">{l}</dd>
            </div>
          ))}
        </dl>
      </section>

      <div className="rule mx-auto max-w-6xl" />

      {/* 01 The problem */}
      <section className={SECTION}>
        <SectionLabel n="01">The problem</SectionLabel>
        <div className="grid gap-10 md:grid-cols-2">
          <h2 className="text-3xl leading-tight sm:text-4xl">AI support agents can be talked into giving money away.</h2>
          <div className="space-y-4 text-muted">
            <p>
              Stores are giving LLM agents real tools like <code className="font-mono text-ink">issue_refund</code>. Unlike
              scripted bots, an LLM can be persuaded: fake stories, "my manager approved it", or instructions hidden in a
              message.
            </p>
            <p>
              In our own tests, a capable open model called <code className="font-mono text-ink">issue_refund</code> for a
              customer who simply claimed a manager had approved it. Big retailers have fraud teams. Small stores don't.
            </p>
          </div>
        </div>
      </section>

      {/* 02 The decision */}
      <section className={SECTION}>
        <SectionLabel n="02">The decision handed to Decider 2B</SectionLabel>
        <h2 className="mb-10 max-w-3xl text-3xl leading-tight sm:text-4xl">
          Six typed questions. One fixed set of outcomes.
        </h2>
        <div className="grid gap-8 lg:grid-cols-[1.1fr_1fr]">
          <div className="card divide-y divide-hairline">
            {QUESTIONS.map(([name, q], i) => (
              <div key={name} className="flex gap-4 px-5 py-3.5">
                <span className="font-mono text-[12px] text-muted">{String(i + 1).padStart(2, "0")}</span>
                <div>
                  <p className="font-mono text-[12px] text-accent">{name}</p>
                  <p className="text-[14px]">{q}</p>
                </div>
              </div>
            ))}
            <div className="flex flex-wrap items-center gap-2 px-5 py-4">
              <span className="label mr-1">outcomes</span>
              <OutcomeChip outcome="approve" size="sm" />
              <OutcomeChip outcome="partial" size="sm" />
              <OutcomeChip outcome="deny" size="sm" />
              <OutcomeChip outcome="escalate" size="sm" />
            </div>
          </div>
          <div className="card p-5">
            <p className="label mb-1">real readout · “my order never arrived”</p>
            <p className="mb-4 text-[13px] text-muted">The delivery record shows it was delivered with photo proof.</p>
            {meta ? (
              <SignalReadout signals={EXAMPLE} meta={meta} policyStep="decider:contradicted" />
            ) : (
              <p className="font-mono text-[12px] text-muted">loading…</p>
            )}
            <div className="rule mt-4 flex items-center justify-between pt-3">
              <OutcomeChip outcome="deny" />
              <span className="text-[13px] text-muted">Records contradict the claim</span>
            </div>
          </div>
        </div>
      </section>

      {/* 03 How it works */}
      <section id="how-it-works" className={SECTION}>
        <SectionLabel n="03">How it works</SectionLabel>
        <h2 className="mb-10 max-w-3xl text-3xl leading-tight sm:text-4xl">The LLM talks. Decider decides. Code pays.</h2>
        <ol className="grid gap-px overflow-hidden rounded-card border border-hairline bg-hairline sm:grid-cols-2 lg:grid-cols-3">
          {FLOW.map(([title, body], i) => (
            <li key={title} className="bg-surface p-5">
              <p className="font-mono text-[12px] text-accent">{String(i + 1).padStart(2, "0")}</p>
              <p className="mt-2 font-serif text-xl">{title}</p>
              <p className="mt-1.5 text-[14px] text-muted">{body}</p>
            </li>
          ))}
        </ol>
        <p className="mt-6 max-w-prose text-[14px] text-muted">
          Every error fails closed: if Decider times out or answers something unexpected, the refund goes to a human, never
          through.
        </p>
      </section>

      {/* 04 Measured results */}
      <section className={SECTION}>
        <SectionLabel n="04">Measured results</SectionLabel>
        <h2 className="mb-4 max-w-3xl text-3xl leading-tight sm:text-4xl">One big question failed. Six small ones worked.</h2>
        <p className="mb-8 max-w-prose text-muted">
          50 labelled cases: genuine claims, false claims, social engineering, prompt injection and ambiguous cases. The 34
          test cases were written and committed before the first run.
        </p>
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-[14px]">
            <thead className="label">
              <tr className="border-b border-hairline">
                <th className="px-5 py-3 font-normal">Held-out test set (34 cases)</th>
                <th className="px-5 py-3 font-normal">One choice question</th>
                <th className="px-5 py-3 font-normal text-accent">Six yes/no questions</th>
              </tr>
            </thead>
            <tbody className="font-mono text-[13px]">
              {[
                ["Accuracy", "82%", "94%"],
                ["Attacks that got money", "1 / 20", "0 / 20"],
                ["Genuine customers denied", "0 / 8", "0 / 8"],
                ["Sent to a human", "76%", "18%"],
                ["Decided correctly with no human", "7 / 34", "26 / 34"],
              ].map(([k, a, b]) => (
                <tr key={k} className="border-b border-dashed border-hairline last:border-0">
                  <td className="px-5 py-3 font-sans">{k}</td>
                  <td className="px-5 py-3 text-muted">{a}</td>
                  <td className="px-5 py-3">{b}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-4 max-w-prose text-[13px] text-muted">
          Reported honestly: one unsure customer was auto-approved, and the per-item cap overpaid on a half-damaged set. The
          comparison against Bedrock LLM judges and the GPU latency numbers are in the{" "}
          <a className="link" href="https://github.com/gaaurav03/refund-guard/blob/main/docs/tests.md">benchmark</a>.
        </p>
      </section>

      {/* 05 Reusable pattern */}
      <section className={SECTION}>
        <SectionLabel n="05">The reusable pattern</SectionLabel>
        <div className="grid gap-10 md:grid-cols-2">
          <h2 className="text-3xl leading-tight sm:text-4xl">Put a claim-vs-evidence check in front of any risky tool.</h2>
          <div className="space-y-4 text-muted">
            <p>
              <code className="font-mono text-ink">decision-patterns/claim-vs-evidence/</code> packages the typed questions,
              the InterventionHandler wiring and the decision policy, so you can guard refunds, account credits,
              cancellations or discount codes.
            </p>
            <Link to="/try" className="btn-primary">Now try to beat it →</Link>
          </div>
        </div>
      </section>
    </>
  );
}
