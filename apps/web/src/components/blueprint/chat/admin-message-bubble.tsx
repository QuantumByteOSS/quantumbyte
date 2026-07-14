import { Headset } from 'lucide-react';
import { MarkdownRenderer } from './markdown-renderer';
import type { Message } from './types';

const TEAM_LABEL = 'Quantumbytes Team';

/**
 * Support / staff message (role === "admin"). Ported verbatim from the portal's
 * `AdminMessageBubble`. No backend feeds admin messages in this slice yet — kept
 * for parity and static/mock rendering.
 */
export function AdminMessageBubble({ message }: { message: Message }) {
  return (
    <div className="flex w-full justify-start">
      <div className="flex max-w-[85%] flex-col items-start min-w-0">
        <div className="mb-1 flex items-center gap-1.5 text-[11px] font-semibold text-emerald-700">
          <Headset className="size-3.5 shrink-0" aria-hidden="true" />
          <span>{message.admin_name || TEAM_LABEL}</span>
        </div>
        <div className="rounded-2xl rounded-tl-md border border-emerald-200 bg-emerald-50 px-3.5 py-2.5 text-xs font-normal leading-[1.4em] text-slate-900 min-w-0">
          <MarkdownRenderer content={message.content} className="break-words" />
        </div>
      </div>
    </div>
  );
}
