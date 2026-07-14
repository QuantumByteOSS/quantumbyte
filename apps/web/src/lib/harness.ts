import type {
  HarnessRequirement,
  HarnessResult,
} from '@/generated/prisma/client';

// API wire format mirrors the platform's harness contract:
// lowercase type/severity/status strings, snake_case result fields.
export function serializeRequirement(r: HarnessRequirement) {
  return {
    id: r.id,
    excerpt: r.excerpt,
    description: r.description,
    type: r.type.toLowerCase(),
    severity: r.severity.toLowerCase(),
    locked: r.locked,
  };
}

export function serializeResult(r: HarnessResult) {
  return {
    requirement_id: r.requirementId,
    result: r.result,
    evidence: r.evidence,
    run_status: r.runStatus,
    last_verified_sha: r.lastVerifiedSha,
    watched_paths: r.watchedPaths,
    run_at: r.runAt?.toISOString() ?? null,
    is_stale: r.isStale,
  };
}
