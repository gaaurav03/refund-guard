import { useEffect, useState, type ReactNode } from "react";

/** A small, slightly rotated mono-italic note with a hand-drawn arrow (devuthman-style). */
export function Annotation({
  children,
  arrow = "down",
  rotate = -3,
  className = "",
}: {
  children: ReactNode;
  arrow?: "down" | "right" | "left" | "none";
  rotate?: number;
  className?: string;
}) {
  const path = {
    down: "M6 2 C 10 10, 4 16, 10 26 M5 21 L10 26 L14 20",
    right: "M2 10 C 10 4, 18 14, 30 8 M24 4 L30 8 L25 13",
    left: "M30 10 C 22 4, 14 14, 2 8 M8 4 L2 8 L7 13",
    none: "",
  }[arrow];
  return (
    <span className={`annotation pointer-events-none inline-flex items-center gap-1 ${className}`} style={{ transform: `rotate(${rotate}deg)` }}>
      {arrow === "left" && <Arrow d={path} />}
      <span>{children}</span>
      {(arrow === "right" || arrow === "down") && <Arrow d={path} />}
    </span>
  );
}

function Arrow({ d }: { d: string }) {
  return (
    <svg viewBox="0 0 32 28" className="h-6 w-7 shrink-0 text-muted" fill="none" stroke="currentColor" strokeWidth="1.4"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d={d} />
    </svg>
  );
}

/** A dark terminal block with a copy button (jev-style). */
export function Terminal({ lines, copy, title }: { lines: string[]; copy?: string; title?: string }) {
  const [done, setDone] = useState(false);
  const text = copy ?? lines.join("\n");
  return (
    <div className="terminal overflow-hidden">
      <div className="flex items-center justify-between border-b border-bg/10 px-3.5 py-2">
        <span className="text-[11px] text-bg/50">{title ?? "terminal"}</span>
        <button
          type="button"
          className="rounded px-2 py-0.5 text-[11px] text-bg/70 hover:bg-bg/10 hover:text-bg"
          onClick={() => {
            void navigator.clipboard?.writeText(text).then(() => {
              setDone(true);
              window.setTimeout(() => setDone(false), 1500);
            });
          }}
        >
          {done ? "copied ✓" : "copy"}
        </button>
      </div>
      <pre className="overflow-x-auto px-3.5 py-3 leading-relaxed">
        {lines.map((l, n) => (
          <div key={n}>
            {l.startsWith("$ ") ? (
              <>
                <span className="text-accent">$ </span>
                {l.slice(2)}
              </>
            ) : l.startsWith("#") ? (
              <span className="text-bg/45">{l}</span>
            ) : (
              l
            )}
          </div>
        ))}
      </pre>
    </div>
  );
}

/** Floating dot navigation on the right edge (desktop only). */
export function DotNav({ sections }: { sections: [string, string][] }) {
  const [active, setActive] = useState(sections[0]?.[0] ?? "");
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && setActive(e.target.id)),
      { rootMargin: "-45% 0px -50% 0px" },
    );
    sections.forEach(([id]) => {
      const el = document.getElementById(id);
      if (el) io.observe(el);
    });
    return () => io.disconnect();
  }, [sections]);
  return (
    <nav
      aria-label="Sections"
      className="fixed right-5 top-1/2 z-40 hidden -translate-y-1/2 flex-col items-end gap-3 rounded-full border border-hairline bg-surface/80 px-2.5 py-4 backdrop-blur xl:flex"
    >
      {sections.map(([id, label]) => (
        <a key={id} href={`#${id}`} className="group flex items-center gap-2" aria-label={label}>
          <span className="pointer-events-none absolute right-10 whitespace-nowrap rounded bg-ink px-2 py-0.5 font-mono text-[10px] text-bg opacity-0 transition-opacity group-hover:opacity-100">
            {label}
          </span>
          <span className={`block h-2 w-2 rounded-full transition-all ${active === id ? "scale-125 bg-accent" : "bg-hairline group-hover:bg-muted"}`} />
        </a>
      ))}
    </nav>
  );
}
