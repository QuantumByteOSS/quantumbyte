import type { ChatRow, Message } from './types';

/**
 * Map raw API rows onto the ported `Message` shape the bubbles expect, and
 * synthesize the in-flight assistant "thinking" bubble.
 *
 * Current backend only emits USER/ASSISTANT rows. Streaming replies arrive as an
 * ASSISTANT row that starts empty + PROCESSING and fills in (see the worker).
 * A FAILED user turn carries its error on the user row → rendered as a trailing
 * assistant error bubble.
 */
/** User-facing copy for the worker's pipeline stages. AGENT has no copy of its
 * own — the assistant row's live tool activity is richer while the agent runs. */
const STAGE_COPY: Record<string, string> = {
  RECONCILING: 'Updating product docs…',
  COMMITTING: 'Saving your app to GitHub…',
};

export function mapRowsToMessages(rows: ChatRow[]): Message[] {
  const out: Message[] = [];

  // Stage of the turn currently in flight — drives the streaming bubble's
  // status line once the agent itself is done talking (post-turn pipeline).
  const processingUser = [...rows]
    .reverse()
    .find((r) => r.role === 'USER' && r.status === 'PROCESSING');
  const stageCopy = processingUser?.stage
    ? STAGE_COPY[processingUser.stage]
    : undefined;

  for (const row of rows) {
    if (row.role === 'USER') {
      out.push({
        id: row.id,
        role: 'user',
        content: row.content,
        timestamp: row.createdAt,
      });
      if (row.status === 'FAILED') {
        out.push({
          id: `${row.id}-error`,
          role: 'assistant',
          content: row.error || 'The agent failed to respond.',
          message_type: 'error',
          timestamp: row.createdAt,
        });
      }
      continue;
    }

    // ASSISTANT
    const streaming = row.status === 'PROCESSING';
    out.push({
      id: row.id,
      role: 'assistant',
      content: row.content,
      thinking: row.thinking || undefined,
      timestamp: row.createdAt,
      streaming,
      // The worker appends pipeline milestones into the same timeline, so the
      // current activity is always the log's last entry.
      activity: streaming ? row.activity ?? undefined : undefined,
      activitySteps: (row.activityLog ?? []).map((e) => e.text),
    });
  }

  // If a user turn is in flight but no assistant row exists yet, show a
  // standalone "thinking" bubble.
  const lastUser = [...rows].reverse().find((r) => r.role === 'USER');
  const inFlight =
    lastUser &&
    (lastUser.status === 'PENDING' || lastUser.status === 'PROCESSING');
  const hasAssistantAfter =
    lastUser && rows.some((r) => r.role === 'ASSISTANT' && r.createdAt >= lastUser.createdAt);

  if (inFlight && !hasAssistantAfter) {
    // PENDING has two very different reasons: an earlier turn of THIS project is
    // still running (one agent per project — the message is simply queued), or
    // no worker has picked the project up yet. Say which.
    const queuedBehindTurn = rows.some(
      (r) => r.role === 'USER' && r.status === 'PROCESSING' && r.id !== lastUser.id
    );
    out.push({
      id: `${lastUser.id}-thinking`,
      role: 'assistant',
      content: '',
      streaming: true,
      timestamp: lastUser.createdAt,
      activity:
        lastUser.status === 'PENDING'
          ? queuedBehindTurn
            ? 'Queued — finishing your previous request first…'
            : 'Waiting for a builder…'
          : stageCopy,
    });
  }

  return out;
}
