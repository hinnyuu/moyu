import { describe, expect, it } from "vitest";
import { uploadItem } from "./queue";
import type { QueueApi, QueueItem, UploadHooks } from "./queue";

function makeItem(overrides: Partial<QueueItem> = {}): QueueItem {
  return {
    id: "q1",
    name: "frame.bin",
    size: 10,
    type: "application/octet-stream",
    lastModified: 1,
    status: "pending",
    offset: 0,
    ...overrides,
  };
}

function fakeApi() {
  const sessions = new Map<string, { offset: number; size: number; chunks: number[] }>();
  const stats = { created: 0, finished: 0 };
  const api: QueueApi = {
    async createUpload(_name, size) {
      stats.created += 1;
      const id = `s${stats.created}`;
      sessions.set(id, { offset: 0, size, chunks: [] });
      return { id, offset: 0, size };
    },
    async getUpload(id) {
      const session = sessions.get(id);
      if (!session) throw new Error("missing session");
      return { id, offset: session.offset, size: session.size };
    },
    async appendChunk(id, offset, chunk) {
      const session = sessions.get(id);
      if (!session) throw new Error("missing session");
      if (session.offset !== offset) throw new Error("offset mismatch");
      session.chunks.push(chunk.size);
      session.offset += chunk.size;
      return session.offset;
    },
    async finishUpload(id) {
      const session = sessions.get(id);
      if (!session || session.offset !== session.size) throw new Error("incomplete");
      stats.finished += 1;
      return { id: `a${stats.finished}` } as never;
    },
  };
  return { api, sessions, stats };
}

function hooks(events: QueueItem[], pauseAfter = Number.POSITIVE_INFINITY): UploadHooks {
  let updates = 0;
  return {
    onUpdate(item) {
      events.push(item);
      updates += 1;
    },
    shouldPause() {
      return updates >= pauseAfter;
    },
  };
}

describe("upload queue", () => {
  it("uploads in chunks and finishes", async () => {
    const { api, sessions, stats } = fakeApi();
    const events: QueueItem[] = [];
    const result = await uploadItem(makeItem(), new Blob([new Uint8Array(10)]), api, hooks(events), 4);
    expect(result.status).toBe("done");
    expect(result.assetId).toBe("a1");
    expect(sessions.get("s1")?.chunks).toEqual([4, 4, 2]);
    expect(stats.created).toBe(1);
  });

  it("resumes from the server offset without creating a session", async () => {
    const { api, sessions, stats } = fakeApi();
    await api.createUpload("frame.bin", 10, "application/octet-stream");
    sessions.get("s1")!.offset = 4;
    const events: QueueItem[] = [];
    const result = await uploadItem(
      makeItem({ sessionId: "s1", offset: 0, status: "paused" }),
      new Blob([new Uint8Array(10)]),
      api,
      hooks(events),
      4,
    );
    expect(result.status).toBe("done");
    expect(stats.created).toBe(1);
    expect(sessions.get("s1")?.chunks).toEqual([4, 2]);
  });

  it("pauses between chunks", async () => {
    const { api, sessions } = fakeApi();
    const events: QueueItem[] = [];
    const result = await uploadItem(
      makeItem(),
      new Blob([new Uint8Array(10)]),
      api,
      hooks(events, 2),
      4,
    );
    expect(result.status).toBe("paused");
    expect(result.offset).toBe(4);
    expect(sessions.get("s1")?.offset).toBe(4);
  });

  it("propagates chunk errors", async () => {
    const { api } = fakeApi();
    const failing: QueueApi = {
      ...api,
      async appendChunk() {
        throw new Error("network");
      },
    };
    await expect(
      uploadItem(makeItem(), new Blob([new Uint8Array(10)]), failing, hooks([]), 4),
    ).rejects.toThrow("network");
  });
});
