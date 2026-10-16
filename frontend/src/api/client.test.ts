import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, chatViaJob, errorKind } from "./client";

const json = (body: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } }));

afterEach(() => vi.unstubAllGlobals());

describe("chatViaJob", () => {
  it("starts a job, polls until done and returns the turn", async () => {
    const result = { reply: "Denied.", decisions: [], messages_left: 19 };
    const fetchMock = vi
      .fn()
      .mockReturnValueOnce(json({ job_id: "J-1", status: "pending", result: null, error: null }, 202))
      .mockReturnValueOnce(json({ job_id: "J-1", status: "pending", result: null, error: null }))
      .mockReturnValueOnce(json({ job_id: "J-1", status: "done", result, error: null }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(chatViaJob("S-1", "refund", 1)).resolves.toEqual(result);
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/chat/jobs");
    expect(fetchMock.mock.calls[2]?.[0]).toBe("/api/chat/jobs/J-1");
  });

  it("surfaces a failed job as an error, never as a refund", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockReturnValueOnce(json({ job_id: "J-2", status: "pending", result: null, error: null }, 202))
        .mockReturnValueOnce(json({ job_id: "J-2", status: "error", result: null, error: "boom" })),
    );
    await expect(chatViaJob("S-1", "refund", 1)).rejects.toBeInstanceOf(ApiError);
  });
});

describe("errorKind", () => {
  it("treats CloudFront 502/504 (instance stopped) as the demo being asleep", () => {
    expect(errorKind(502)).toBe("offline");
    expect(errorKind(504)).toBe("offline");
    expect(errorKind(503)).toBe("budget");
  });
});
