import { describe, expect, it } from "vitest";

import {
  buildContext,
  messagesToSummarize,
  needsSummarization,
  SUMMARY_BLOCK,
} from "../lib/memory";
import { generateTitle, groupByDate } from "../lib/storage";
import { readSseStream } from "../lib/sse";
import type { Conversation, Message } from "../lib/types";

function conversation(messageCount: number, summarizedUpTo = 0): Conversation {
  const messages: Message[] = Array.from({ length: messageCount }, (_, index) => ({
    id: String(index),
    role: index % 2 === 0 ? "user" : "assistant",
    content: `m${index}`,
    createdAt: index,
  }));
  return {
    id: "c1",
    title: "Test",
    createdAt: 0,
    updatedAt: 0,
    documentName: null,
    messages,
    summary: null,
    summarizedUpTo,
  };
}

describe("summarization threshold", () => {
  it("is ten messages", () => {
    expect(SUMMARY_BLOCK).toBe(10);
  });

  it("does not trigger at nine unsummarized messages", () => {
    expect(needsSummarization(conversation(9))).toBe(false);
  });

  it("triggers at ten unsummarized messages", () => {
    expect(needsSummarization(conversation(10))).toBe(true);
  });

  it("triggers again ten messages after the previous block", () => {
    expect(needsSummarization(conversation(20, 10))).toBe(true);
    expect(needsSummarization(conversation(19, 10))).toBe(false);
  });

  it("summarizes exactly the next ten unsummarized messages", () => {
    const batch = messagesToSummarize(conversation(25, 10));

    expect(batch).toHaveLength(10);
    expect(batch[0].content).toBe("m10");
    expect(batch[9].content).toBe("m19");
  });
});

describe("context building", () => {
  it("sends only the unsummarized tail as history", () => {
    const { recentMessages } = buildContext(conversation(13, 10));

    expect(recentMessages.map((m) => m.content)).toEqual(["m10", "m11", "m12"]);
  });

  it("passes the stored summary through", () => {
    const source = { ...conversation(11, 10), summary: "önceki özet" };

    expect(buildContext(source).summary).toBe("önceki özet");
  });

  it("returns an empty summary when none exists", () => {
    expect(buildContext(conversation(3)).summary).toBe("");
  });
});

describe("titles and grouping", () => {
  it("keeps a short question intact", () => {
    expect(generateTitle("  Yıllık izin nasıl alınır?  ")).toBe("Yıllık izin nasıl alınır?");
  });

  it("collapses runs of whitespace", () => {
    expect(generateTitle("Yıllık    izin")).toBe("Yıllık izin");
  });

  it("truncates a long question", () => {
    const title = generateTitle("a".repeat(80));

    expect(title.length).toBeLessThanOrEqual(41);
    expect(title.endsWith("…")).toBe(true);
  });

  it("groups today's conversations under Bugün", () => {
    const groups = groupByDate([{ ...conversation(1), updatedAt: Date.now() }]);

    expect(groups[0].label).toBe("Bugün");
  });

  it("omits groups that have no conversations", () => {
    const groups = groupByDate([{ ...conversation(1), updatedAt: Date.now() }]);

    expect(groups.map((g) => g.label)).toEqual(["Bugün"]);
  });

  it("puts an old conversation under Daha eski", () => {
    const groups = groupByDate([{ ...conversation(1), updatedAt: Date.now() - 5 * 86400000 }]);

    expect(groups[0].label).toBe("Daha eski");
  });
});

describe("sse reader", () => {
  function streamOf(...chunks: string[]) {
    const encoder = new TextEncoder();
    return new ReadableStream<Uint8Array>({
      start(controller) {
        for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
        controller.close();
      },
    });
  }

  it("assembles events split across chunks", async () => {
    const seen: unknown[] = [];

    await readSseStream(
      streamOf('data: {"type":"to', 'ken","content":"ab"}\n\n', 'data: {"type":"meta"}\n\n'),
      (event) => seen.push(event),
    );

    expect(seen).toEqual([{ type: "token", content: "ab" }, { type: "meta" }]);
  });

  it("ignores malformed frames rather than throwing", async () => {
    const seen: unknown[] = [];

    await readSseStream(streamOf("data: not-json\n\n", 'data: {"type":"start"}\n\n'), (event) =>
      seen.push(event),
    );

    expect(seen).toEqual([{ type: "start" }]);
  });

  it("preserves Turkish characters across a chunk boundary", async () => {
    const seen: { content?: string }[] = [];

    await readSseStream(streamOf('data: {"type":"token","content":"Yıllık izin"}\n\n'), (event) =>
      seen.push(event as { content?: string }),
    );

    expect(seen[0].content).toBe("Yıllık izin");
  });

  it("emits nothing for an empty stream", async () => {
    const seen: unknown[] = [];

    await readSseStream(streamOf(), (event) => seen.push(event));

    expect(seen).toEqual([]);
  });
});
