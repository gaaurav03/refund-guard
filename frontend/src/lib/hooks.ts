import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Health, Meta } from "../types/decision";

let metaCache: Promise<Meta> | null = null;

export function useMeta(): Meta | null {
  const [meta, setMeta] = useState<Meta | null>(null);
  useEffect(() => {
    metaCache ??= api.meta();
    let alive = true;
    metaCache.then((m) => alive && setMeta(m)).catch(() => {
      metaCache = null;
    });
    return () => {
      alive = false;
    };
  }, []);
  return meta;
}

export type HealthState = "checking" | "up" | "asleep" | "budget";

export function useHealth(): HealthState {
  const [state, setState] = useState<HealthState>("checking");
  useEffect(() => {
    let alive = true;
    const check = () =>
      api
        .health()
        .then((h: Health) => alive && setState(h.budget_exhausted ? "budget" : "up"))
        .catch(() => alive && setState("asleep"));
    void check();
    const t = window.setInterval(check, 30_000);
    return () => {
      alive = false;
      window.clearInterval(t);
    };
  }, []);
  return state;
}

export function usePoll<T>(fn: () => Promise<T>, ms: number, enabled = true): T | null {
  const [data, setData] = useState<T | null>(null);
  useEffect(() => {
    if (!enabled) return;
    let alive = true;
    const tick = () => fn().then((d) => alive && setData(d)).catch(() => undefined);
    void tick();
    const t = window.setInterval(tick, ms);
    return () => {
      alive = false;
      window.clearInterval(t);
    };
  }, [ms, enabled]);
  return data;
}
