export type StreamEvent = Record<string, unknown> & { type: string };

/**
 * Drain an SSE body, calling `onEvent` per frame.
 *
 * Frames are split on the blank-line delimiter, not on chunk boundaries: one
 * `data:` line routinely arrives across two network chunks, and splitting on
 * arrival would cut a JSON object in half.
 */
export async function readSseStream(
  body: ReadableStream<Uint8Array>,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const frames = buffer.split("\n\n");
    // The trailing piece is incomplete until the next chunk arrives.
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      const line = frame.split("\n").find((candidate) => candidate.startsWith("data: "));
      if (!line) continue;
      try {
        onEvent(JSON.parse(line.slice(6)) as StreamEvent);
      } catch {
        // A truncated or malformed frame is skipped; the stream continues.
      }
    }
  }
}
