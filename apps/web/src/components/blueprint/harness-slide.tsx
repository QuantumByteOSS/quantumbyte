'use client';

import {
  ArrowCounterClockwise,
  CaretDown,
  CheckCircle,
  CircleNotch,
  HourglassMedium,
  Lock,
  PencilSimple,
  Play,
  Plus,
  Prohibit,
  Question,
  RocketLaunch,
  TrashSimple,
  Warning,
  XCircle,
} from '@phosphor-icons/react';
import { useMemo, useState } from 'react';
import {
  REQUIREMENT_SEVERITIES,
  sortRequirementsBySeverity,
  type RequirementSeverity,
} from '@/lib/requirement-severity';
import type { HarnessSnapshot } from './use-project-stream';

type Requirement = {
  id: string;
  excerpt: string | null;
  description: string;
  type: 'explicit' | 'hidden';
  severity: RequirementSeverity;
  // True once a user has created or edited this row through the UI — it is then
  // manually owned and the worker's auto-derivation leaves it alone. "Reset to
  // auto" clears it.
  locked: boolean;
};

type Result = {
  requirement_id: string;
  result: 'SUCCESS' | 'FAIL' | null;
  evidence: string | null;
  run_status: 'OK' | 'INCONCLUSIVE';
  watched_paths: string[];
  run_at: string | null;
  is_stale: boolean;
};

type StagedOp =
  | { op: 'add'; data: Requirement }
  | { op: 'edit'; data: Requirement }
  | { op: 'delete' };

type Verdict = 'pass' | 'fail' | 'inconclusive' | 'unverified';

const SEVERITY_BADGE: Record<string, string> = {
  critical: 'bg-red-100 text-red-700',
  high: 'bg-orange-100 text-orange-700',
  medium: 'bg-amber-100 text-amber-700',
  low: 'bg-slate-100 text-slate-600',
};

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'fail', label: 'Failing' },
  { key: 'inconclusive', label: 'Inconclusive' },
  { key: 'unverified', label: 'Unverified' },
  { key: 'pass', label: 'Passing' },
] as const;

function verdictOf(result: Result | undefined): Verdict {
  if (!result || !result.run_at) return 'unverified';
  if (result.run_status === 'INCONCLUSIVE') return 'inconclusive';
  return result.result === 'SUCCESS' ? 'pass' : 'fail';
}

function computeGate(requirements: Requirement[], verdicts: Map<string, Verdict>) {
  if (requirements.length === 0) {
    return {
      label: 'No requirements yet',
      reason: 'Add business requirements to gate this app on.',
      grad: 'from-slate-500 to-slate-700',
      Icon: Question,
    };
  }
  const criticals = requirements.filter((r) => r.severity === 'critical');
  const anyCriticalFail = criticals.some((r) => verdicts.get(r.id) === 'fail');
  const anyFail = requirements.some((r) => verdicts.get(r.id) === 'fail');
  const allCriticalPass = criticals.every((r) => verdicts.get(r.id) === 'pass');

  if (anyCriticalFail) {
    return {
      label: 'Do not ship',
      reason: 'A critical requirement is failing.',
      grad: 'from-red-500 to-rose-700',
      Icon: Prohibit,
    };
  }
  if (anyFail || !allCriticalPass) {
    return {
      label: 'Ship with warnings',
      reason: anyFail
        ? 'Non-critical requirements are failing.'
        : 'Critical requirements are not verified yet.',
      grad: 'from-amber-500 to-orange-600',
      Icon: Warning,
    };
  }
  return {
    label: 'Safe to ship',
    reason: 'Every critical requirement passes.',
    grad: 'from-emerald-500 to-green-700',
    Icon: RocketLaunch,
  };
}

function VerdictBadge({ verdict, running }: { verdict: Verdict; running: boolean }) {
  // A re-check with no prior verdict to preserve (first-ever run): nothing to keep,
  // so show a plain "Checking".
  if (running && verdict === 'unverified') {
    return (
      <span className="flex items-center gap-1 text-xs font-medium text-slate-500">
        <CircleNotch size={14} className="animate-spin" /> Checking
      </span>
    );
  }
  const spec = {
    pass: { cls: 'text-emerald-600', Icon: CheckCircle, label: 'Pass', fill: true },
    fail: { cls: 'text-red-600', Icon: XCircle, label: 'Fail', fill: true },
    inconclusive: { cls: 'text-amber-600', Icon: Question, label: 'Inconclusive', fill: true },
    unverified: { cls: 'text-slate-400', Icon: HourglassMedium, label: 'Pending', fill: false },
  }[verdict];
  // A re-check is in flight but this row already has a verdict — keep the verdict
  // icon and label fully readable (it is the last known truth until the run
  // overwrites it; blanking every row to "Checking" throws that away and contradicts
  // the gate, which keeps showing these same verdicts) and APPEND a trailing spinner
  // to signal the re-check. The spinner is additive, not a replacement, so the badge
  // never reads as the contradictory "spinner + Pass".
  return (
    <span
      className={`flex items-center gap-1 text-xs font-medium ${spec.cls} ${running ? 'opacity-70' : ''}`}
      title={running ? 'Re-checking — showing the last result until this run finishes' : undefined}
    >
      <spec.Icon size={14} weight={spec.fill ? 'fill' : undefined} /> {spec.label}
      {running && <CircleNotch size={12} className="ml-0.5 animate-spin" />}
    </span>
  );
}

function RequirementForm({
  initial,
  onSave,
  onCancel,
}: {
  initial?: Requirement;
  onSave: (r: Omit<Requirement, 'id'>) => void;
  onCancel: () => void;
}) {
  const [excerpt, setExcerpt] = useState(initial?.excerpt ?? '');
  const [description, setDescription] = useState(initial?.description ?? '');
  const [type, setType] = useState<Requirement['type']>(initial?.type ?? 'explicit');
  const [severity, setSeverity] = useState<Requirement['severity']>(
    initial?.severity ?? 'medium'
  );

  return (
    <div className="my-2 flex flex-col gap-2 rounded-lg border border-slate-200 bg-white p-3">
      <input
        value={excerpt}
        onChange={(e) => setExcerpt(e.target.value)}
        placeholder="Short summary (optional)"
        className="rounded-md border border-slate-200 px-2 py-1.5 text-sm outline-none focus:border-primary"
      />
      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Describe the requirement…"
        className="min-h-16 resize-none rounded-md border border-slate-200 px-2 py-1.5 text-sm outline-none focus:border-primary"
      />
      <div className="flex items-center gap-2">
        <select
          value={type}
          onChange={(e) => setType(e.target.value as Requirement['type'])}
          className="rounded-md border border-slate-200 px-2 py-1.5 text-sm"
        >
          <option value="explicit">Explicit</option>
          <option value="hidden">Hidden</option>
        </select>
        <select
          value={severity}
          onChange={(e) => setSeverity(e.target.value as Requirement['severity'])}
          className="rounded-md border border-slate-200 px-2 py-1.5 text-sm"
        >
          {REQUIREMENT_SEVERITIES.map((s) => (
            <option key={s} value={s}>
              {s[0].toUpperCase() + s.slice(1)}
            </option>
          ))}
        </select>
        <div className="ml-auto flex gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md px-3 py-1.5 text-sm text-slate-500 hover:bg-slate-100"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={!description.trim()}
            onClick={() =>
              // Saving through the form is a manual edit → the row becomes user-owned
              // so auto-derivation won't revert it.
              onSave({ excerpt: excerpt.trim() || null, description: description.trim(), type, severity, locked: true })
            }
            className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-white disabled:opacity-40"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

export function HarnessSlide({
  projectId,
  harness,
  onPoke,
  onRefetch,
}: {
  projectId: string;
  // Live harness snapshot from the shared SSE stream (useProjectStream). null until
  // the first fetch lands.
  harness: HarnessSnapshot | null;
  onPoke: () => void;
  onRefetch: () => void;
}) {
  const [staged, setStaged] = useState<Map<string, StagedOp>>(new Map());
  const [filter, setFilter] = useState<(typeof FILTERS)[number]['key']>('all');
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [editing, setEditing] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [saving, setSaving] = useState(false);

  const loaded = harness !== null;
  const requirements = useMemo<Requirement[]>(() => harness?.requirements ?? [], [harness]);
  const results = useMemo(
    () => new Map((harness?.results ?? []).map((r) => [r.requirement_id, r] as const)),
    [harness]
  );
  // "Checking…" while the server reports a run in flight, or right after we hit Run
  // (before the worker flips the flag).
  const running = (harness?.is_running ?? false) || triggering;

  const effective = useMemo(() => {
    const list: Requirement[] = [];
    for (const r of requirements) {
      const op = staged.get(r.id);
      if (op?.op === 'delete') continue;
      list.push(op?.op === 'edit' ? op.data : r);
    }
    for (const [, op] of staged) {
      if (op.op === 'add') list.push(op.data);
    }
    return list;
  }, [requirements, staged]);

  const verdicts = useMemo(() => {
    const map = new Map<string, Verdict>();
    for (const r of effective) map.set(r.id, verdictOf(results.get(r.id)));
    return map;
  }, [effective, results]);

  const gate = computeGate(effective, verdicts);

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: effective.length, fail: 0, inconclusive: 0, unverified: 0, pass: 0 };
    for (const r of effective) c[verdicts.get(r.id) ?? 'unverified']++;
    return c;
  }, [effective, verdicts]);

  const grouped = useMemo(
    () => {
      const visible = sortRequirementsBySeverity(
        effective.filter(
          (requirement) =>
            filter === 'all' || verdicts.get(requirement.id) === filter
        )
      );

      return REQUIREMENT_SEVERITIES.map((sev) => ({
        sev,
        items: visible.filter((requirement) => requirement.severity === sev),
      })).filter((group) => group.items.length > 0);
    },
    [effective, filter, verdicts]
  );

  const stage = (id: string, op: StagedOp) =>
    setStaged((prev) => new Map(prev).set(id, op));

  const apply = async () => {
    setSaving(true);
    try {
      const res = await fetch(`/api/projects/${projectId}/harness/requirements`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          requirements: effective.map((r) => ({
            ...r,
            id: r.id.startsWith('tmp-') ? '' : r.id,
          })),
        }),
      });
      if (res.ok) {
        setStaged(new Map());
        onRefetch();
      }
    } finally {
      setSaving(false);
    }
  };

  const runHarness = async () => {
    setTriggering(true);
    try {
      await fetch(`/api/projects/${projectId}/harness/run`, { method: 'POST' });
      // Open the shared stream so the run's status + verdicts land live, and pull a
      // settled snapshot for triggers the stream may not cover.
      onPoke();
      onRefetch();
    } finally {
      setTriggering(false);
    }
  };

  const toggle = (set: Set<string>, id: string) => {
    const next = new Set(set);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    return next;
  };

  return (
    <div className="flex h-full w-full flex-col bg-white">
      {/* Gate decision hero */}
      <div className="border-b border-slate-200 px-6 pb-4 pt-6">
        <div
          className={`rounded-2xl bg-gradient-to-br p-5 text-white shadow-lg ${gate.grad}`}
        >
          <div className="flex items-center gap-3">
            <span className="flex size-11 items-center justify-center rounded-full bg-white/15">
              <gate.Icon size={24} weight="bold" />
            </span>
            <div>
              <p className="text-xs uppercase tracking-wide text-white/70">
                Gate decision
              </p>
              <p className="text-2xl font-bold">{gate.label}</p>
            </div>
          </div>
          <p className="mt-3 text-sm text-white/90">{gate.reason}</p>
        </div>

        {/* Action bar */}
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setAdding(true)}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100"
          >
            <Plus size={16} /> Add requirement
          </button>
          {staged.size > 0 && (
            <>
              <button
                type="button"
                onClick={() => setStaged(new Map())}
                className="rounded-lg px-3 py-1.5 text-sm text-slate-500 hover:bg-slate-100"
              >
                Discard ({staged.size})
              </button>
              <button
                type="button"
                onClick={apply}
                disabled={saving}
                className="rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-white disabled:opacity-40"
              >
                {saving ? 'Applying…' : `Apply (${staged.size})`}
              </button>
            </>
          )}
          <button
            type="button"
            onClick={runHarness}
            disabled={running || effective.length === 0 || staged.size > 0}
            className="ml-auto flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-40"
          >
            {running ? (
              <CircleNotch size={16} className="animate-spin" />
            ) : (
              <Play size={16} weight="fill" />
            )}
            Run Harness Check
          </button>
        </div>
        {adding && (
          <RequirementForm
            onCancel={() => setAdding(false)}
            onSave={(data) => {
              const id = `tmp-${Date.now()}`;
              stage(id, { op: 'add', data: { id, ...data } });
              setAdding(false);
            }}
          />
        )}
      </div>

      {/* Filter pills */}
      <div className="flex gap-1.5 border-b border-slate-200 px-6 py-2">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            onClick={() => setFilter(f.key)}
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              filter === f.key
                ? 'bg-slate-900 text-white'
                : 'text-slate-500 hover:bg-slate-100'
            }`}
          >
            {f.label} {counts[f.key] ?? 0}
          </button>
        ))}
      </div>

      {/* Grouped requirement list */}
      <div className="flex-1 overflow-y-auto px-6 py-2">
        {!loaded ? (
          <p className="py-8 text-center text-sm text-slate-400">Loading…</p>
        ) : effective.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-400">
            No requirements yet. Add one to start gating your app.
          </p>
        ) : (
          grouped.map(({ sev, items }) => (
            <div key={sev} className="mb-2">
              <button
                type="button"
                onClick={() => setCollapsed((prev) => toggle(prev, sev))}
                className="sticky top-0 z-10 flex w-full items-center gap-2 bg-white py-2"
              >
                <CaretDown
                  size={14}
                  className={`text-slate-400 transition-transform ${
                    collapsed.has(sev) ? '-rotate-90' : ''
                  }`}
                />
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${SEVERITY_BADGE[sev]}`}
                >
                  {sev}
                </span>
                <span className="text-xs text-slate-400">{items.length}</span>
              </button>
              {!collapsed.has(sev) &&
                items.map((req) => {
                  const result = results.get(req.id);
                  const stagedOp = staged.get(req.id);
                  if (editing === req.id) {
                    return (
                      <RequirementForm
                        key={req.id}
                        initial={req}
                        onCancel={() => setEditing(null)}
                        onSave={(data) => {
                          stage(req.id, {
                            op: req.id.startsWith('tmp-') ? 'add' : 'edit',
                            data: { id: req.id, ...data },
                          });
                          setEditing(null);
                        }}
                      />
                    );
                  }
                  return (
                    <div
                      key={req.id}
                      className={`mb-1.5 rounded-lg border px-3 py-2 ${
                        stagedOp
                          ? 'border-primary/40 bg-primary/5'
                          : 'border-slate-100 bg-white'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => setExpanded((prev) => toggle(prev, req.id))}
                          className="min-w-0 flex-1 text-left"
                        >
                          <p className="truncate text-sm">
                            {req.excerpt || req.description}
                          </p>
                          <p className="flex items-center gap-1 text-xs text-slate-400">
                            {req.locked && (
                              <Lock
                                size={11}
                                weight="fill"
                                className="text-slate-400"
                                aria-label="Edited by you — kept as-is on re-checks"
                              />
                            )}
                            {req.locked ? 'Yours' : req.type === 'explicit' ? 'Explicit' : 'Hidden'}
                            {result?.run_at &&
                              ` · verified ${new Date(result.run_at).toLocaleString()}`}
                            {result?.is_stale && ' · stale'}
                          </p>
                        </button>
                        <VerdictBadge
                          verdict={verdicts.get(req.id) ?? 'unverified'}
                          running={running}
                        />
                        {req.locked && !req.id.startsWith('tmp-') && (
                          <button
                            type="button"
                            aria-label="Reset to auto"
                            title="Reset to auto — let the builder manage this requirement again"
                            onClick={() => stage(req.id, { op: 'edit', data: { ...req, locked: false } })}
                            className="rounded-md p-1 text-slate-400 hover:bg-slate-100"
                          >
                            <ArrowCounterClockwise size={14} />
                          </button>
                        )}
                        <button
                          type="button"
                          aria-label="Edit requirement"
                          onClick={() => setEditing(req.id)}
                          className="rounded-md p-1 text-slate-400 hover:bg-slate-100"
                        >
                          <PencilSimple size={14} />
                        </button>
                        <button
                          type="button"
                          aria-label="Delete requirement"
                          onClick={() =>
                            req.id.startsWith('tmp-')
                              ? setStaged((prev) => {
                                  const next = new Map(prev);
                                  next.delete(req.id);
                                  return next;
                                })
                              : stage(req.id, { op: 'delete' })
                          }
                          className="rounded-md p-1 text-slate-400 hover:bg-red-50 hover:text-red-500"
                        >
                          <TrashSimple size={14} />
                        </button>
                        <button
                          type="button"
                          aria-label="Expand requirement"
                          onClick={() => setExpanded((prev) => toggle(prev, req.id))}
                          className="rounded-md p-1 text-slate-400 hover:bg-slate-100"
                        >
                          <CaretDown
                            size={14}
                            className={`transition-transform ${
                              expanded.has(req.id) ? 'rotate-180' : ''
                            }`}
                          />
                        </button>
                      </div>
                      {expanded.has(req.id) && (
                        <div className="mt-2 flex flex-col gap-2 border-t border-slate-100 pt-2 text-sm">
                          <div>
                            <p className="text-xs font-medium uppercase text-slate-400">
                              What this means
                            </p>
                            <p className="text-slate-600">{req.description}</p>
                          </div>
                          {result?.evidence && (
                            <div>
                              <p className="text-xs font-medium uppercase text-slate-400">
                                What we found
                              </p>
                              <p className="text-slate-600">{result.evidence}</p>
                            </div>
                          )}
                          {result && result.watched_paths.length > 0 && (
                            <div>
                              <p className="text-xs font-medium uppercase text-slate-400">
                                Files checked
                              </p>
                              <p className="font-mono text-xs text-slate-500">
                                {result.watched_paths.join(', ')}
                              </p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
