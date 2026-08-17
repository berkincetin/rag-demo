import { Conversation, Message } from "./types";

/** How many messages are folded into the summary at a time. */
export const SUMMARY_BLOCK = 10;

/**
 * What the model receives: the cumulative summary plus everything not yet
 * folded into it.
 */
export function buildContext(c: Conversation): { summary: string; recentMessages: Message[] } {
  return { summary: c.summary ?? "", recentMessages: c.messages.slice(c.summarizedUpTo) };
}

/** True once ten messages have accumulated since the last summary. */
export function needsSummarization(c: Conversation): boolean {
  return c.messages.length - c.summarizedUpTo >= SUMMARY_BLOCK;
}

export function messagesToSummarize(c: Conversation): Message[] {
  return c.messages.slice(c.summarizedUpTo, c.summarizedUpTo + SUMMARY_BLOCK);
}
