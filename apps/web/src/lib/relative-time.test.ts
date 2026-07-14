import { describe, expect, it } from 'vitest';
import { formatRelativeTime } from './relative-time';

// Fixed reference instant so the tests are deterministic (no wall clock).
const NOW = new Date('2026-07-14T12:00:00Z').getTime();
const ago = (ms: number) => new Date(NOW - ms);
const ahead = (ms: number) => new Date(NOW + ms);

const SEC = 1000;
const MIN = 60 * SEC;
const HOUR = 60 * MIN;
const DAY = 24 * HOUR;

describe('formatRelativeTime', () => {
  it('returns "just now" under a minute in either direction', () => {
    expect(formatRelativeTime(ago(59 * SEC), NOW)).toBe('just now');
    expect(formatRelativeTime(ahead(59 * SEC), NOW)).toBe('just now');
    expect(formatRelativeTime(new Date(NOW), NOW)).toBe('just now');
  });

  it('formats past times with the largest fitting unit', () => {
    expect(formatRelativeTime(ago(MIN), NOW)).toBe('1 minute ago');
    expect(formatRelativeTime(ago(90 * SEC), NOW)).toBe('1 minute ago');
    expect(formatRelativeTime(ago(2 * HOUR), NOW)).toBe('2 hours ago');
    expect(formatRelativeTime(ago(3 * DAY), NOW)).toBe('3 days ago');
  });

  it('formats future times', () => {
    expect(formatRelativeTime(ahead(2 * MIN), NOW)).toBe('in 2 minutes');
    expect(formatRelativeTime(ahead(1 * HOUR), NOW)).toBe('in 1 hour');
  });

  it('rolls up at unit boundaries (days -> months -> years)', () => {
    // numeric:'auto' renders the -1 magnitudes idiomatically.
    expect(formatRelativeTime(ago(45 * DAY), NOW)).toBe('last month');
    expect(formatRelativeTime(ago(400 * DAY), NOW)).toBe('last year');
    expect(formatRelativeTime(ago(2 * 365 * DAY), NOW)).toBe('2 years ago');
  });
});
