'use client';

import { FileText, PaperPlaneTilt, Plus, SidebarSimple, X } from '@phosphor-icons/react';
import Image from 'next/image';
import { useEffect, useRef, useState } from 'react';
import { formatRelativeTime } from '@/lib/relative-time';
import { ChatList } from './chat/chat-list';
import type { Message } from './chat/types';

export function ChatPanel({
  projectId,
  title,
  updatedAt,
  messages,
  onSent,
  onCollapse,
}: {
  projectId: string;
  title: string;
  updatedAt: string;
  // Chat + stream now live in the shared useProjectStream hook (one SSE connection
  // for chat + harness). This panel is controlled: it renders `messages` and, on
  // send, pokes the shared stream via `onSent`.
  messages: Message[];
  onSent: () => void;
  onCollapse: () => void;
}) {
  const liveTitle = title;
  const liveUpdatedAt = updatedAt;
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages.length]);

  const send = async () => {
    const text = input.trim();
    if ((!text && files.length === 0) || sending) return;
    setSending(true);
    setUploadError(null);
    try {
      // Upload attachments first; their URLs ride along in the chat POST and end
      // up as markdown links in the message body (the agent follows them).
      let attachments: { url: string; filename: string; mimeType: string }[] = [];
      if (files.length > 0) {
        const form = new FormData();
        for (const file of files) form.append('files', file);
        const uploadRes = await fetch(`/api/projects/${projectId}/attachments`, {
          method: 'POST',
          body: form,
        });
        if (!uploadRes.ok) {
          const data = await uploadRes.json().catch(() => null);
          setUploadError(data?.error ?? 'Attachment upload failed');
          return; // keep input + files so the user can retry
        }
        attachments = (await uploadRes.json()).attachments ?? [];
      }

      const res = await fetch(`/api/projects/${projectId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, attachments }),
      });
      if (res.ok) {
        setInput('');
        setFiles([]);
        onSent();
      }
    } finally {
      setSending(false);
    }
  };

  const addFiles = (picked: FileList | null) => {
    if (!picked) return;
    setUploadError(null);
    // Mirror the API's limits so failures surface before the network call.
    const next = [...files, ...Array.from(picked)].slice(0, 5);
    setFiles(next.filter((f) => f.size <= 10 * 1024 * 1024));
  };

  return (
    <div className="flex h-full flex-col gap-3 ps-3 py-3 pe-2">
      {/* Project card */}
      <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white p-3">
        <Image
          src="/logo_qbits_fav.png"
          alt=""
          width={36}
          height={36}
          className="shrink-0 rounded-lg"
        />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold">{liveTitle}</p>
          <p className="text-xs text-slate-400">
            Last updated {formatRelativeTime(new Date(liveUpdatedAt))}
          </p>
        </div>
        <button
          type="button"
          aria-label="Collapse chat"
          onClick={onCollapse}
          className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100"
        >
          <SidebarSimple size={16} />
        </button>
      </div>

      {/* Messages */}
      {messages.length === 0 ? (
        <div className="flex flex-1 items-center justify-center rounded-[10px] border-2 border-border bg-[#F1F5F9]">
          <p className="max-w-52 text-center text-sm text-slate-400">
            Ask the agent to build, fix, or improve anything on your project.
          </p>
        </div>
      ) : (
        <ChatList ref={scrollRef} messages={messages} />
      )}

      {/* Composer */}
      <div className="rounded-2xl border border-slate-200 bg-white p-3">
        {files.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-1.5">
            {files.map((file, i) => (
              <span
                key={`${file.name}-${i}`}
                className="flex max-w-48 items-center gap-1 rounded-full bg-slate-100 py-1 pl-2 pr-1 text-xs text-slate-600"
              >
                <FileText size={12} className="shrink-0 text-slate-400" />
                <span className="truncate">{file.name}</span>
                <button
                  type="button"
                  aria-label={`Remove ${file.name}`}
                  onClick={() => setFiles(files.filter((_, j) => j !== i))}
                  className="rounded-full p-0.5 hover:bg-slate-200"
                >
                  <X size={10} />
                </button>
              </span>
            ))}
          </div>
        )}
        {uploadError && (
          <p className="mb-2 text-xs text-red-500">{uploadError}</p>
        )}
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          placeholder="Ask me to build, fix, or improve anything on your project"
          className="min-h-20 w-full resize-none bg-transparent text-sm outline-none placeholder:text-slate-400"
        />
        <div className="flex items-center gap-2 pt-1">
          {/* Hidden file input backing the attach button. Voice Mode is hidden
              until it actually works (task T9). */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => {
              addFiles(e.target.files);
              e.target.value = ''; // allow re-picking the same file
            }}
          />
          <button
            type="button"
            aria-label="Attach files"
            onClick={() => fileInputRef.current?.click()}
            className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100"
          >
            <Plus size={16} />
          </button>
          <button
            type="button"
            aria-label="Send"
            onClick={send}
            disabled={(!input.trim() && files.length === 0) || sending}
            className="ml-auto rounded-xl bg-primary/80 p-2.5 text-white hover:bg-primary disabled:opacity-40"
          >
            <PaperPlaneTilt size={16} weight="fill" />
          </button>
        </div>
      </div>
    </div>
  );
}
