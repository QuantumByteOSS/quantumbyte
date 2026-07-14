'use client';

import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Check, ChevronDown, Cpu, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { BearAvatar } from './bear-avatar';
import type { AgentType } from './types';

/**
 * Subagent activity bubble — ported from the portal's `SubagentMessageBubble`.
 * A collapsible timeline of tool steps under a bear avatar. No backend feeds
 * subagent/tool data in this slice yet, so this renders from the `steps` prop
 * (static/mock for now, wire to real delegation events later).
 */
export interface SubagentStep {
  label: string;
  running?: boolean;
  detail?: string;
}

export function SubagentMessageBubble({
  agentType = 'ENGINEER',
  taskDescription,
  timeLabel,
  steps,
  defaultOpen = false,
}: {
  agentType?: AgentType;
  taskDescription: string;
  timeLabel?: string;
  steps: SubagentStep[];
  defaultOpen?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const isRunning = steps.some((s) => s.running);

  return (
    <div className="flex w-full items-start gap-3">
      <div aria-hidden="true" className="flex shrink-0 flex-col items-center">
        <BearAvatar agentType={agentType} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex min-h-[25px] flex-col justify-center">
          <div className="min-w-0 flex-1">
            <button
              type="button"
              onClick={() => setIsOpen((v) => !v)}
              className="flex w-full items-center justify-between gap-2 text-left"
            >
              <span
                className={cn(
                  'flex flex-1 items-center gap-1.5 truncate text-xs font-medium italic text-slate-500',
                  isRunning && 'animate-pulse'
                )}
              >
                {isRunning && (
                  <Loader2 className="size-3 shrink-0 animate-spin text-slate-400" />
                )}
                <span className="truncate">
                  {isRunning
                    ? `${taskDescription}...`
                    : `${taskDescription}${timeLabel ? ` for ${timeLabel}` : ''}`}
                </span>
              </span>
              <ChevronDown
                className={cn(
                  'size-3.5 shrink-0 text-slate-400 transition-transform',
                  isOpen && 'rotate-180'
                )}
              />
            </button>
            <AnimatePresence>
              {isOpen && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="mt-1.5 overflow-hidden"
                >
                  <div className="flex flex-col gap-px">
                    {steps.length === 0 ? (
                      <div className="text-xs italic text-slate-400">
                        Working on tasks...
                      </div>
                    ) : (
                      steps.map((step, i) => (
                        <ToolStepRow key={i} step={step} />
                      ))
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}

function ToolStepRow({ step }: { step: SubagentStep }) {
  return (
    <div className="flex items-start gap-2.5 rounded-lg px-2 py-1">
      <span
        className={cn(
          'mt-px flex size-5 shrink-0 items-center justify-center rounded-md',
          step.running ? 'bg-blue-50 text-blue-500' : 'bg-slate-100 text-slate-500'
        )}
      >
        {step.running ? (
          <Loader2 className="size-3 animate-spin" />
        ) : (
          <Cpu className="size-3" />
        )}
      </span>
      <div className="min-w-0 flex-1 pt-0.5">
        <div className="flex items-center gap-1.5">
          <span className="truncate text-xs font-medium text-slate-600">
            {step.running ? `${step.label}…` : step.label}
          </span>
          {!step.running && (
            <Check className="size-3 shrink-0 text-slate-300" />
          )}
        </div>
        {step.detail && (
          <div className="truncate text-[11px] leading-relaxed text-slate-400">
            {step.detail}
          </div>
        )}
      </div>
    </div>
  );
}
