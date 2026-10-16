import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";

const REPO_URL = "https://github.com/gaaurav03/refund-guard";

function ThemeToggle() {
  const [theme, setTheme] = useState(() => document.documentElement.getAttribute("data-theme") ?? "light");
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("rg-theme", theme);
    } catch {
      /* storage blocked: theme still applies for this visit */
    }
  }, [theme]);
  const next = theme === "dark" ? "light" : "dark";
  return (
    <button
      type="button"
      onClick={() => setTheme(next)}
      className="flex h-9 w-9 items-center justify-center rounded-md border border-hairline text-muted hover:text-ink"
      aria-label={`Switch to ${next} theme`}
      title={`Switch to ${next} theme`}
    >
      <span aria-hidden className="font-mono text-sm">{theme === "dark" ? "☀" : "☾"}</span>
    </button>
  );
}

const navClass = ({ isActive }: { isActive: boolean }) =>
  `text-sm transition-colors ${isActive ? "text-ink" : "text-muted hover:text-ink"}`;

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-hairline">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <Link to="/" className="flex items-center gap-2.5">
            <img src="/favicon.svg" alt="" className="h-6 w-6" />
            <span className="font-serif text-lg">Refund Guard</span>
          </Link>
          <nav className="flex items-center gap-4 sm:gap-6" aria-label="Main">
            <NavLink to="/try" className={navClass}>Try to scam it</NavLink>
            <NavLink to="/chat" className={`${navClass({ isActive: false })} hidden sm:inline`}>Chat</NavLink>
            <NavLink to="/review" className={`${navClass({ isActive: false })} hidden sm:inline`}>Review</NavLink>
            <a href={REPO_URL} className="hidden text-sm text-muted hover:text-ink md:inline">GitHub ↗</a>
            <ThemeToggle />
          </nav>
        </div>
      </header>
      <main className="flex-1">{children}</main>
      <footer className="border-t border-hairline">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-8 text-sm text-muted sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <p>
            Declared decision pattern: <span className="text-ink">Guardrails</span>
            <span className="mx-2">·</span>
            <span className="font-mono text-[12px]">#strands-decider-2b #guardrails</span>
          </p>
          <p className="font-mono text-[12px]">
            Apache-2.0 · <a className="link" href={REPO_URL}>source</a> · refunds are simulated
          </p>
        </div>
      </footer>
    </div>
  );
}

export function SectionLabel({ n, children }: { n: string; children: ReactNode }) {
  return (
    <p className="label mb-3">
      <span className="text-accent">{n}</span> · {children}
    </p>
  );
}

export function DemoSleeping({ reason }: { reason: "asleep" | "budget" }) {
  return (
    <div className="mx-auto max-w-xl px-4 py-24 text-center sm:px-6">
      <p className="label mb-4">demo status</p>
      <h1 className="mb-4 text-4xl">{reason === "budget" ? "Today's demo budget is used up." : "The demo is sleeping."}</h1>
      <p className="mb-8 text-muted">
        {reason === "budget"
          ? "The live agent pauses once it reaches its daily Bedrock spending cap. It's back tomorrow."
          : "To keep costs low, the live agent (Bedrock + Decider 2B on a GPU) runs 09:00–21:00 IST."}
        {" "}In the meantime, everything it does is shown in the video and the measured results.
      </p>
      <div className="flex justify-center gap-3">
        <Link to="/" className="btn-ghost">See how it works</Link>
        <a href={REPO_URL} className="btn-primary">Read the code ↗</a>
      </div>
    </div>
  );
}
