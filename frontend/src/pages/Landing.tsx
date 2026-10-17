import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Annotation, DotNav, Terminal } from "../components/Decor";
import { HeroDemo } from "../components/HeroDemo";
import { SectionLabel, VIDEO_URL } from "../components/Layout";
import { OutcomeChip } from "../components/OutcomeChip";
import { WallOfAttempts } from "../components/WallOfAttempts";
import { useHealth, usePoll } from "../lib/hooks";

const REPO = "https://github.com/gaaurav03/refund-guard";

const QUESTIONS: [string, string, string][] = [
  ["args_grounded", "Are the refund's arguments grounded in what the customer actually said?", "catches an LLM inventing the amount"],
  ["contradicted", "Do the store's records contradict the claim?", "catches “it never arrived”"],
  ["concrete_problem", "Does the customer describe a specific, concrete problem?", "the only road to money"],
  ["non_evidence", "Is the customer relying on authority, threats or instructions instead of evidence?", "catches “my manager approved it”"],
  ["over_ask", "Is the amount larger than the value of the affected items?", "turns greed into a partial refund"],
  ["uncertain", "Is the customer unsure, or is it a matter of taste?", "sends “tastes a bit off?” to a human"],
];

const FLOW: [string, string, string][] = [
  ["Chat", "Amazon Bedrock · Nova 2 Lite", "Talks to the customer and decides to call issue_refund."],
  ["Intercept", "Strands InterventionHandler", "Stops the tool call before it runs."],
  ["Pre-checks", "9 plain rules", "Wrong order, amount above the order, already refunded, window closed…"],
  ["Decider 2B", "6 typed yes/no questions", "One call. No text, just probabilities about the evidence."],
  ["Policy", "plain, readable code", "Turns six answers into approve, partial, deny or escalate, and computes the amount."],
  ["Ledger", "pays only what was approved", "issue_refund pays for that exact call, once. Everything is logged."],
];

const SECTIONS: [string, string][] = [
  ["top", "Top"],
  ["problem", "01 Problem"],
  ["decision", "02 The decision"],
  ["how", "03 How it works"],
  ["results", "04 Measured results"],
  ["wall", "05 Wall of attempts"],
  ["pattern", "06 Reusable pattern"],
];

function Section({ id, children, className = "" }: { id: string; children: React.ReactNode; className?: string }) {
  return (
    <section id={id} className={`scroll-mt-20 border-t border-hairline px-4 py-16 sm:px-10 sm:py-20 ${className}`}>
      {children}
    </section>
  );
}

function LiveStats() {
  const health = useHealth();
  const score = usePoll(api.scoreboard, 5000, health === "up");
  const live = health === "up" && score;
  const stats: [string, string, string?][] = [
    ["94%", "accuracy on 34 unseen cases"],
    ["0 / 20", "attacks that got money"],
    ["0 / 8", "genuine customers denied"],
    live ? [String(score.attempts), "live attempts so far", "live"] : ["18%", "sent to a human"],
  ];
  return (
    <dl className="grid grid-cols-2 border-t border-hairline sm:grid-cols-4">
      {stats.map(([v, l, tag], n) => (
        <div key={l} className={`px-4 py-6 sm:px-10 ${n % 2 ? "border-l" : ""} ${n > 1 ? "border-t sm:border-t-0" : ""} sm:border-l border-hairline first:border-l-0`}>
          <dt className="flex items-center gap-2 font-mono text-3xl tabular-nums">
            {v}
            {tag && <span className="h-2 w-2 animate-pulse rounded-full bg-approve" title="live" />}
          </dt>
          <dd className="mt-1 text-[13px] text-muted">{l}</dd>
        </div>
      ))}
    </dl>
  );
}

export function Landing() {
  return (
    <>
      <DotNav sections={SECTIONS} />

      {/* Hero */}
      <section id="top" className="grid gap-10 px-4 pb-14 pt-12 sm:px-10 sm:pt-16 lg:grid-cols-[1fr_1.05fr] lg:items-center">
        <div>
          <p className="label mb-6 flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-hairline bg-surface px-2.5 py-1 normal-case tracking-normal">
              strands decider 2b × amazon bedrock
            </span>
            <span className="rounded-full border border-accent/40 bg-accent/10 px-2.5 py-1 normal-case tracking-normal text-accent">
              #guardrails
            </span>
          </p>
          <h1 className="text-5xl leading-[1.02] sm:text-6xl xl:text-7xl">
            The support agent you <em className="text-accent">can't</em> scam.
          </h1>
          <p className="mt-6 max-w-[52ch] text-lg leading-relaxed text-muted">
            An AI support agent for a small online store. Before any refund moves money, Strands Decider 2B checks the
            claim against the evidence. It doesn't write a single word; it just answers six yes/no questions.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link to="/try" className="btn-primary">Try to scam it →</Link>
            <a href={VIDEO_URL} className="btn-ghost">Watch the video ↗</a>
            <a href="#how" className="btn-ghost">How it works</a>
          </div>
          <div className="mt-8 hidden lg:block">
            <Annotation arrow="right" rotate={-2}>a real scam attempt, replayed with real Decider numbers</Annotation>
          </div>
        </div>
        <HeroDemo />
      </section>

      <LiveStats />

      {/* 01 */}
      <Section id="problem">
        <SectionLabel n="01">The problem</SectionLabel>
        <div className="grid gap-10 md:grid-cols-2">
          <h2 className="text-3xl leading-tight sm:text-[42px]">AI support agents can be talked into giving money away.</h2>
          <div className="space-y-4 text-muted">
            <p>
              Stores are giving LLM agents real tools like <code className="font-mono text-ink">issue_refund</code>. Unlike
              scripted bots, an LLM can be persuaded: a sad story, <em>“my manager approved it”</em>, or instructions hidden
              inside a message.
            </p>
            <div className="card-flat p-4">
              <p className="label mb-2">from our own tests</p>
              <p className="text-[14px] text-ink">
                A capable open model called <code className="font-mono">issue_refund(3200)</code> for a customer who only
                said a manager had approved it.
              </p>
            </div>
            <p>Big retailers have fraud teams. The thousands of small stores adopting AI support agents don't.</p>
          </div>
        </div>
      </Section>

      {/* 02 */}
      <Section id="decision">
        <SectionLabel n="02">The decision handed to Decider 2B</SectionLabel>
        <div className="mb-10 flex flex-wrap items-end justify-between gap-4">
          <h2 className="max-w-2xl text-3xl leading-tight sm:text-[42px]">Six typed questions. Four possible outcomes. Nothing else.</h2>
          <Annotation arrow="down" rotate={3}>it can't be talked into a fifth option</Annotation>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {QUESTIONS.map(([name, q, note], i) => (
            <div key={name} className="card p-5">
              <div className="mb-3 flex items-center justify-between">
                <span className="font-mono text-[12px] text-accent">{name}</span>
                <span className="font-mono text-[11px] text-muted">{String(i + 1).padStart(2, "0")} · yes/no</span>
              </div>
              <p className="font-serif text-[19px] leading-snug">{q}</p>
              <p className="mt-3 annotation not-italic">→ {note}</p>
            </div>
          ))}
        </div>
        <div className="mt-6 flex flex-wrap items-center gap-2">
          <span className="label mr-1">only outcomes</span>
          <OutcomeChip outcome="approve" size="sm" />
          <OutcomeChip outcome="partial" size="sm" />
          <OutcomeChip outcome="deny" size="sm" />
          <OutcomeChip outcome="escalate" size="sm" />
        </div>
      </Section>

      {/* 03 */}
      <Section id="how">
        <SectionLabel n="03">How it works</SectionLabel>
        <h2 className="mb-10 max-w-2xl text-3xl leading-tight sm:text-[42px]">The LLM talks. Decider decides. Code pays.</h2>
        <ol className="grid gap-px overflow-hidden rounded-card border border-hairline bg-hairline sm:grid-cols-2 lg:grid-cols-3">
          {FLOW.map(([title, sub, body], i) => (
            <li key={title} className={`relative p-5 ${title === "Decider 2B" ? "bg-accent/[0.07]" : "bg-surface"}`}>
              <p className="font-mono text-[12px] text-accent">{String(i + 1).padStart(2, "0")}</p>
              <p className="mt-2 font-serif text-2xl">{title}</p>
              <p className="font-mono text-[11px] text-muted">{sub}</p>
              <p className="mt-2 text-[14px] text-muted">{body}</p>
            </li>
          ))}
        </ol>
        <p className="mt-6 flex flex-wrap items-center gap-3 text-[14px] text-muted">
          <span className="rounded-full border border-hairline bg-surface px-3 py-1 font-mono text-[12px] text-ink">fail closed</span>
          If Decider times out, crashes or answers something unexpected, the refund goes to a human, never through.
        </p>
      </Section>

      {/* 04 */}
      <Section id="results">
        <SectionLabel n="04">Measured results</SectionLabel>
        <div className="grid gap-10 lg:grid-cols-[0.9fr_1.1fr]">
          <div>
            <h2 className="text-3xl leading-tight sm:text-[42px]">One big question failed. Six small ones worked.</h2>
            <p className="mt-4 text-muted">
              50 labelled cases. The 34 test cases were written and committed <em>before</em> the first run, so the numbers
              can't have been tuned to them.
            </p>
            <div className="mt-6">
              <Annotation arrow="right" rotate={-2}>the old design paid a scammer ₹1,500</Annotation>
            </div>
          </div>
          <div className="card overflow-x-auto">
            <table className="w-full min-w-[460px] text-left text-[14px]">
              <thead className="label">
                <tr className="border-b border-hairline">
                  <th className="px-5 py-3 font-normal">34 unseen cases</th>
                  <th className="px-5 py-3 font-normal">1 big question</th>
                  <th className="px-5 py-3 font-normal text-accent">6 yes/no questions</th>
                </tr>
              </thead>
              <tbody className="font-mono text-[13px]">
                {[
                  ["Accuracy", "82%", "94%"],
                  ["Attacks that got money", "1 / 20", "0 / 20"],
                  ["Genuine customers denied", "0 / 8", "0 / 8"],
                  ["Sent to a human", "76%", "18%"],
                  ["Correct with no human", "7 / 34", "26 / 34"],
                ].map(([k, a, b]) => (
                  <tr key={k} className="border-b border-dashed border-hairline last:border-0">
                    <td className="px-5 py-3 font-sans">{k}</td>
                    <td className="px-5 py-3 text-muted line-through decoration-muted/40">{a}</td>
                    <td className="px-5 py-3 text-ink">{b}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Section>

      {/* 05 */}
      <Section id="wall">
        <SectionLabel n="05">Wall of attempts</SectionLabel>
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <h2 className="max-w-2xl text-3xl leading-tight sm:text-[42px]">Every test case, and what Decider said.</h2>
          <p className="max-w-sm text-[14px] text-muted">
            Real answers from the held-out run. Misses are marked, not hidden.
          </p>
        </div>
        <WallOfAttempts />
      </Section>

      {/* 06 */}
      <Section id="pattern">
        <SectionLabel n="06">The reusable pattern</SectionLabel>
        <div className="grid gap-10 lg:grid-cols-2">
          <div>
            <h2 className="text-3xl leading-tight sm:text-[42px]">Put a claim-vs-evidence check in front of any risky tool.</h2>
            <p className="mt-4 text-muted">
              <code className="font-mono text-ink">decision-patterns/claim-vs-evidence/</code> packages the typed questions,
              the InterventionHandler wiring and the decision policy. Use it to guard refunds, account credits,
              cancellations or discount codes.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <a href={`${REPO}/tree/main/decision-patterns/claim-vs-evidence`} className="btn-ghost">Read the pattern ↗</a>
              <Link to="/try" className="btn-primary">Now try to beat it →</Link>
            </div>
          </div>
          <div className="space-y-3">
            <Terminal
              title="1 · serve Decider 2B"
              lines={[
                "$ pip install strands-decider strands-agents",
                "$ pip install -e decision-patterns/claim-vs-evidence",
                "$ strands-decider serve StrandsAgents/strands-decider-2B-qwen3.5-v1-2610 --port 8099",
              ]}
            />
            <Terminal
              title="2 · guard your tool"
              copy={
                'guard = ClaimEvidenceGuard(tool="apply_store_credit", decider=HttpDeciderClient(url), gather=gather)\n' +
                "agent = Agent(model=BedrockModel(...), tools=[apply_store_credit], interventions=[guard])"
              }
              lines={[
                "# any risky tool: refunds, credits, cancellations",
                "guard = ClaimEvidenceGuard(",
                '    tool="apply_store_credit",',
                "    decider=HttpDeciderClient(url),",
                "    gather=gather,  # your records + their words",
                ")",
                "agent = Agent(model=BedrockModel(...),",
                "    tools=[apply_store_credit], interventions=[guard])",
              ]}
            />
          </div>
        </div>
      </Section>
    </>
  );
}
