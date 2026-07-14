'use client';

import { Plus, Shuffle } from '@phosphor-icons/react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

const RANDOM_IDEAS = [
  'An appointment booking app for my dental clinic with WhatsApp reminders',
  'A delivery tracking dashboard for my logistics fleet',
  'A client portal for my design agency with project status and invoices',
  'A class schedule and attendance tracker for my tuition centre',
  'An inventory manager for my minimart with low-stock alerts',
  'A room reservation system for my coworking space',
];

export function PromptBox({ hasProjects }: { hasProjects: boolean }) {
  const router = useRouter();
  const [prompt, setPrompt] = useState('');
  const [building, setBuilding] = useState(false);

  const randomIdea = () => {
    const next = RANDOM_IDEAS[Math.floor(Math.random() * RANDOM_IDEAS.length)];
    setPrompt(next);
  };

  const build = async () => {
    if (!prompt.trim() || building) return;
    setBuilding(true);
    try {
      const res = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt.trim() }),
      });
      if (res.ok) {
        const project = await res.json();
        router.push(`/dashboard/project/blueprint/${project.id}`);
        return;
      }
    } finally {
      setBuilding(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-5xl">
      {hasProjects && (
        <p className="mb-2 flex items-center gap-1.5 text-sm font-medium text-slate-600">
          <Plus size={16} /> Build a new app
        </p>
      )}
      <div
        className={`rounded-3xl p-4 ${
          hasProjects
            ? 'border border-slate-200'
            : 'border-2 border-[#2F45FF] shadow-[0px_0px_16px_4px_rgba(47,69,255,0.2)]'
        }`}
      >
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') build();
          }}
          placeholder="Describe the app you want to build…"
          className="min-h-24 w-full resize-none bg-transparent text-base outline-none placeholder:text-slate-400"
        />
        <div className="flex items-center justify-between pt-2">
          <button
            type="button"
            onClick={randomIdea}
            className="flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100"
          >
            <Shuffle size={16} /> Random idea
          </button>
          <button
            type="button"
            onClick={build}
            disabled={!prompt.trim() || building}
            className="rounded-full bg-primary px-4 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-40"
          >
            {building ? 'Building…' : 'Build'}
          </button>
        </div>
      </div>
    </div>
  );
}
