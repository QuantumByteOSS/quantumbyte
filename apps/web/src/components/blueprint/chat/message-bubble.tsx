import { useState } from 'react';
import { cn } from '@/lib/utils';
import { AgentAvatarColumn } from './bear-avatar';
import { AdminMessageBubble } from './admin-message-bubble';
import { MarkdownRenderer } from './markdown-renderer';
import { agentTypeFromMessage } from './agent-theme';
import type { Message } from './types';

/**
 * Chat message bubble — ported from the portal's `MessageBubble`.
 * Dispatch order mirrors the source: admin → error → user → assistant.
 * Subagent / attachment / options variants exist as separate components and are
 * fed static data until the backend produces them (see chat/README intent).
 */
export function MessageBubble({
  message,
  isLatest,
}: {
  message: Message;
  isLatest?: boolean;
}) {
  const isUser = message.role === 'user';

  if (message.role === 'admin') {
    return <AdminMessageBubble message={message} />;
  }

  if (message.message_type === 'error') {
    return <ErrorMessageCard content={message.content} />;
  }

  if (isUser) {
    return <UserBubble message={message} />;
  }

  // Assistant
  const agentType = agentTypeFromMessage(message);
  const isStatus = message.message_type === 'status';
  const hasThinking = !!message.thinking && message.thinking.length > 0;
  const steps = message.activitySteps ?? [];
  // Generic shimmer only until *something* (steps, reasoning or reply) lands.
  const isThinking =
    !!message.streaming &&
    message.content.length === 0 &&
    !hasThinking &&
    steps.length === 0;

  return (
    <div className="group flex w-full items-start gap-3">
      <AgentAvatarColumn agentType={agentType} />
      <div className="flex flex-1 min-w-0 flex-col overflow-hidden text-sm leading-relaxed text-slate-900">
        {hasThinking && (
          <ReasoningDisclosure
            thinking={message.thinking as string}
            streaming={!!message.streaming && message.content.length === 0}
          />
        )}
        {steps.length > 0 && (
          <ActivityTimeline steps={steps} streaming={!!message.streaming} />
        )}
        <div className="flex min-h-[25px] flex-col justify-center">
          {isThinking ? (
            <ThinkingLine label={message.activity} />
          ) : isStatus ? (
            <StatusMessageContent content={message.content} isLatest={isLatest} />
          ) : message.content.length > 0 ? (
            <div className="min-w-0">
              <MarkdownRenderer content={message.content} className="break-words" />
              {message.streaming && <StreamingCaret />}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

/** The turn's step feed — what the agent/pipeline is actually doing in the
 * background. While streaming: recent finished steps dimmed with a check, the
 * current one shimmering with a spinner. After the turn: a collapsed "N steps"
 * recap the user can expand. */
function ActivityTimeline({
  steps,
  streaming,
}: {
  steps: string[];
  streaming: boolean;
}) {
  const [open, setOpen] = useState(false);
  const VISIBLE_WHILE_STREAMING = 3;

  if (!streaming) {
    return (
      <div className="mb-1.5">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-400 hover:text-slate-600"
        >
          <svg
            className={cn('size-3 transition-transform', open && 'rotate-90')}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            aria-hidden="true"
          >
            <polyline points="9 6 15 12 9 18" />
          </svg>
          {steps.length} step{steps.length === 1 ? '' : 's'}
        </button>
        {open && (
          <ul className="mt-1 space-y-0.5 border-l-2 border-slate-200 pl-2.5">
            {steps.map((step, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs text-slate-500">
                <CheckDot />
                <span className="[overflow-wrap:anywhere]">{step}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  const current = steps[steps.length - 1];
  const done = steps.slice(0, -1);
  const hidden = Math.max(0, done.length - VISIBLE_WHILE_STREAMING);
  const visibleDone = open ? done : done.slice(-VISIBLE_WHILE_STREAMING);

  return (
    <div className="mb-1.5 rounded-xl border border-slate-100 bg-slate-50/70 px-3 py-2">
      <ul className="space-y-1">
        {hidden > 0 && !open && (
          <li>
            <button
              type="button"
              onClick={() => setOpen(true)}
              className="text-[11px] font-semibold text-slate-400 hover:text-slate-600"
            >
              +{hidden} earlier step{hidden === 1 ? '' : 's'}
            </button>
          </li>
        )}
        {visibleDone.map((step, i) => (
          <li key={`${i}-${step}`} className="flex items-start gap-1.5 text-xs text-slate-400">
            <CheckDot />
            <span className="line-clamp-1 [overflow-wrap:anywhere]">{step}</span>
          </li>
        ))}
        <li className="flex items-start gap-1.5 text-xs">
          <span className="mt-0.5 inline-block size-3 shrink-0 animate-spin rounded-full border-[1.5px] border-slate-300 border-t-slate-500" />
          <span className="qb-text-shine line-clamp-1 font-medium [overflow-wrap:anywhere]">
            {current}
          </span>
        </li>
      </ul>
    </div>
  );
}

function CheckDot() {
  return (
    <svg
      className="mt-0.5 size-3 shrink-0 text-emerald-500/80"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="3"
      aria-hidden="true"
    >
      <polyline points="4 12 10 18 20 6" />
    </svg>
  );
}

/** Collapsible "reasoning" disclosure for streamed extended-thinking text.
 * Auto-expands while reasoning is still streaming (before the reply lands),
 * collapses once the reply is in; the user can toggle either way. */
function ReasoningDisclosure({
  thinking,
  streaming,
}: {
  thinking: string;
  streaming: boolean;
}) {
  const [open, setOpen] = useState(false);
  const expanded = open || streaming;

  return (
    <div className="mb-1.5">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          'flex items-center gap-1.5 text-[11px] font-semibold',
          streaming ? 'qb-text-shine' : 'text-slate-400 hover:text-slate-600'
        )}
      >
        <svg
          className={cn(
            'size-3 transition-transform',
            expanded && 'rotate-90'
          )}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          aria-hidden="true"
        >
          <polyline points="9 6 15 12 9 18" />
        </svg>
        {streaming ? 'Reasoning…' : 'Reasoning'}
      </button>
      {expanded && (
        <div className="mt-1 border-l-2 border-slate-200 pl-2.5 text-xs italic leading-relaxed text-slate-500 [overflow-wrap:anywhere] whitespace-pre-wrap">
          {thinking}
        </div>
      )}
    </div>
  );
}

/* -------------------------------------------------------------------------- */

function UserBubble({ message }: { message: Message }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const text = message.content;
  const isLong = text.length > 300;

  return (
    <div className="group flex w-full justify-end">
      <div className="flex max-w-[85%] flex-col items-end min-w-0">
        <div className="rounded-2xl rounded-tr-md bg-[#e8f1ff] px-3.5 py-2.5 text-xs font-normal leading-[1.333em] tracking-[-0.03em] text-slate-900 min-w-0">
          <div
            className={cn(
              'whitespace-pre-wrap break-words [overflow-wrap:anywhere]',
              !isExpanded && isLong && 'line-clamp-4'
            )}
          >
            {text}
          </div>
        </div>
        {isLong && (
          <button
            type="button"
            onClick={() => setIsExpanded((v) => !v)}
            className="mt-1 text-[11px] font-semibold text-[#2f45ff] hover:underline"
          >
            {isExpanded ? 'See less' : 'See more'}
          </button>
        )}
      </div>
    </div>
  );
}

/** Animated shimmer "thinking" line (uses `.qb-text-shine`). `label` swaps in
 * the live pipeline status ("Waiting for a builder…", "Running `npm install`"). */
function ThinkingLine({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="qb-text-shine text-xs italic">{label || 'Thinking…'}</span>
      <span className="flex items-center gap-1">
        <span className="qb-meatball-dot inline-block size-1.5 rounded-full bg-slate-400" />
        <span className="qb-meatball-dot inline-block size-1.5 rounded-full bg-slate-400 [animation-delay:150ms]" />
        <span className="qb-meatball-dot inline-block size-1.5 rounded-full bg-slate-400 [animation-delay:300ms]" />
      </span>
    </div>
  );
}

/** Live activity line under a streaming reply — what the agent/pipeline is doing
 * right now ("Editing page.tsx", "Saving your app to GitHub…"). */
function ActivityLine({ label }: { label: string }) {
  return (
    <div className="mt-1.5 flex items-center gap-1.5">
      <span className="qb-text-shine line-clamp-1 text-[11px] italic">{label}</span>
    </div>
  );
}

/** Blinking caret shown at the tail of a streaming assistant reply. */
function StreamingCaret() {
  return (
    <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-[#2f45ff]/60 align-text-bottom" />
  );
}

/** Status ("thinking out loud") line — collapsed shimmer when latest. */
function StatusMessageContent({
  content,
  isLatest,
}: {
  content: string;
  isLatest?: boolean;
}) {
  return (
    <div className="w-full min-w-0">
      <div
        className={cn(
          'text-xs italic line-clamp-2',
          isLatest ? 'qb-text-shine' : 'text-slate-500'
        )}
      >
        {content}
      </div>
    </div>
  );
}

/** Assistant error card — ported from the portal's `ErrorMessageCard`. */
function ErrorMessageCard({ content }: { content: string }) {
  return (
    <div className="w-full max-w-xl overflow-hidden rounded-2xl border border-red-200/70 bg-gradient-to-b from-red-50/90 to-rose-50/60 shadow-[0_1px_2px_rgba(220,38,38,0.06)]">
      <div className="flex items-start gap-3 px-4 py-3">
        <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-red-100 ring-1 ring-red-200/80">
          <svg
            className="size-4 text-red-500"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[13px] font-semibold leading-snug text-red-800">
            Something went wrong
          </p>
          <p className="mt-0.5 text-[13px] leading-relaxed text-red-700 [overflow-wrap:anywhere]">
            {content || 'The agent failed to respond.'}
          </p>
        </div>
      </div>
    </div>
  );
}
