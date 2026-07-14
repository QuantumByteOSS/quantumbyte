'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { mapRowsToMessages } from './chat/map-message';
import type { ChatRow } from './chat/types';

// Wire shapes mirror the API serializers (@/lib/harness) — lowercase type/severity,
// snake_case result fields.
export type RequirementWire = {
  id: string;
  excerpt: string | null;
  description: string;
  type: 'explicit' | 'hidden';
  severity: 'critical' | 'high' | 'medium' | 'low';
  locked: boolean;
};

export type ResultWire = {
  requirement_id: string;
  result: 'SUCCESS' | 'FAIL' | null;
  evidence: string | null;
  run_status: 'OK' | 'INCONCLUSIVE';
  last_verified_sha: string | null;
  watched_paths: string[];
  run_at: string | null;
  is_stale: boolean;
};

export type HarnessSnapshot = {
  requirements: RequirementWire[];
  results: ResultWire[];
  is_running: boolean;
};

type ProjectFields = { title?: string | null; desc?: string | null; updatedAt?: string };

/**
 * One SSE connection per project, shared by the chat and harness panels.
 *
 * Browsers cap ~6 concurrent connections per origin, so rather than the chat panel
 * and the harness panel each tailing their own stream, this hook owns the single
 * `/chat/stream` connection (which now also carries the harness snapshot) and hands
 * both panels their slice. It seeds from the plain GET endpoints on mount, then tails
 * the stream whenever a chat turn is in flight OR the harness is running — the worker
 * runs the harness right after a turn settles, and the server keeps the connection
 * open across that hand-off.
 */
export function useProjectStream(
  projectId: string,
  seed: { title: string; updatedAt: string }
) {
  const [rows, setRows] = useState<ChatRow[]>([]);
  const [project, setProject] = useState<ProjectFields>({
    title: seed.title,
    updatedAt: seed.updatedAt,
  });
  const [harness, setHarness] = useState<HarnessSnapshot | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const messages = useMemo(() => mapRowsToMessages(rows), [rows]);
  const hasPending = rows.some((m) => m.status === 'PENDING' || m.status === 'PROCESSING');
  const isRunning = harness?.is_running ?? false;

  const refetch = useCallback(async () => {
    const [chatRes, harnessRes] = await Promise.allSettled([
      fetch(`/api/projects/${projectId}/chat`),
      fetch(`/api/projects/${projectId}/harness`),
    ]);
    if (chatRes.status === 'fulfilled' && chatRes.value.ok) {
      const data = await chatRes.value.json();
      setRows(data.messages);
    }
    if (harnessRes.status === 'fulfilled' && harnessRes.value.ok) {
      const data = await harnessRes.value.json();
      setHarness({
        requirements: data.requirements ?? [],
        results: data.results ?? [],
        is_running: data.is_running ?? false,
      });
    }
  }, [projectId]);

  /**
   * Tail the SSE stream. Uses fetch + a reader (not EventSource) so we control the
   * lifecycle — the server self-closes once neither a turn nor the harness is in
   * flight, and we don't auto-reconnect while idle.
   */
  const startStream = useCallback(async () => {
    if (abortRef.current) return; // already tailing
    const ac = new AbortController();
    abortRef.current = ac;
    try {
      const res = await fetch(`/api/projects/${projectId}/chat/stream`, {
        signal: ac.signal,
        headers: { Accept: 'text/event-stream' },
      });
      if (!res.ok || !res.body) return;
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() ?? '';
        for (const evt of events) {
          const line = evt.split('\n').find((l) => l.startsWith('data:'));
          if (!line) continue;
          try {
            const payload = JSON.parse(line.slice(5).trim());
            if (payload.messages) setRows(payload.messages);
            if (payload.project) setProject(payload.project);
            if (payload.harness) setHarness(payload.harness);
          } catch {
            /* ignore partial/non-json */
          }
        }
      }
    } catch {
      /* aborted or network — ignore */
    } finally {
      if (abortRef.current === ac) abortRef.current = null;
      // Settle after the stream closes; if the harness kicked off (or is still
      // running) the effect below reopens the stream.
      refetch();
    }
  }, [projectId, refetch]);

  // poke: force-open the stream after an action that will make the server busy
  // (sending a message, hitting "Run harness") so its updates stream immediately.
  const poke = useCallback(() => {
    if (!abortRef.current) startStream();
  }, [startStream]);

  useEffect(() => {
    (async () => {
      await refetch();
    })();
    return () => abortRef.current?.abort();
  }, [refetch]);

  useEffect(() => {
    if ((hasPending || isRunning) && !abortRef.current) startStream();
  }, [hasPending, isRunning, startStream]);

  return { rows, messages, project, harness, poke, refetch };
}
