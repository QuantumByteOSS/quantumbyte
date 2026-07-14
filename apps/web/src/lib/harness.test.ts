import { describe, expect, it } from 'vitest';
import type {
  HarnessRequirement,
  HarnessResult,
} from '@/generated/prisma/client';
import { serializeRequirement, serializeResult } from './harness';

// The Prisma enums are erased at runtime; these fixtures only need the shape the
// serializers read. Cast through unknown so the string enums type-check.
function requirement(
  over: Partial<HarnessRequirement> = {},
): HarnessRequirement {
  return {
    id: 'req_1',
    excerpt: 'must send a receipt email',
    description: 'A receipt email is sent after checkout',
    type: 'FUNCTIONAL',
    severity: 'BLOCKER',
    locked: false,
    ...over,
  } as unknown as HarnessRequirement;
}

function result(over: Partial<HarnessResult> = {}): HarnessResult {
  return {
    requirementId: 'req_1',
    result: 'PASS',
    evidence: 'checkout_test.ts asserts the email',
    runStatus: 'DONE',
    lastVerifiedSha: 'abc123',
    watchedPaths: ['src/checkout.ts'],
    runAt: new Date('2026-07-14T12:00:00Z'),
    isStale: false,
    ...over,
  } as unknown as HarnessResult;
}

describe('serializeRequirement', () => {
  it('lowercases type and severity and keeps the rest verbatim', () => {
    expect(serializeRequirement(requirement())).toEqual({
      id: 'req_1',
      excerpt: 'must send a receipt email',
      description: 'A receipt email is sent after checkout',
      type: 'functional',
      severity: 'blocker',
      locked: false,
    });
  });

  it('preserves the locked flag', () => {
    expect(serializeRequirement(requirement({ locked: true })).locked).toBe(
      true,
    );
  });
});

describe('serializeResult', () => {
  it('maps camelCase fields to the snake_case wire format', () => {
    expect(serializeResult(result())).toEqual({
      requirement_id: 'req_1',
      result: 'PASS',
      evidence: 'checkout_test.ts asserts the email',
      run_status: 'DONE',
      last_verified_sha: 'abc123',
      watched_paths: ['src/checkout.ts'],
      run_at: '2026-07-14T12:00:00.000Z',
      is_stale: false,
    });
  });

  it('emits null run_at when runAt is null', () => {
    expect(serializeResult(result({ runAt: null })).run_at).toBeNull();
  });
});
