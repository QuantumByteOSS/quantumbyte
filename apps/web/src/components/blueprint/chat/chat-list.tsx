import { forwardRef } from 'react';
import { MessageBubble } from './message-bubble';
import type { Message } from './types';

/**
 * Scrollable message list. Container styling (light-blue panel, 2px border,
 * bottom-anchored stack) ported verbatim from the portal's `ChatList`.
 */
export const ChatList = forwardRef<HTMLDivElement, { messages: Message[] }>(
  function ChatList({ messages }, ref) {
    return (
      <div
        ref={ref}
        id="conversational-area"
        className="custom-scrollbar flex-1 overflow-y-auto rounded-[10px] border-2 border-border bg-[#F1F5F9] px-4 pb-2 pt-3"
      >
        <div className="flex min-h-full flex-col justify-end">
          <div className="space-y-4">
            {messages.map((m, i) => (
              <MessageBubble
                key={m.id}
                message={m}
                isLatest={i === messages.length - 1}
              />
            ))}
          </div>
        </div>
      </div>
    );
  }
);
