import { describe, expect, it } from 'vitest';
import { sortRequirementsBySeverity } from './requirement-severity';

describe('sortRequirementsBySeverity', () => {
  it('orders requirements from critical to low', () => {
    const requirements = [
      { id: 'low', severity: 'low' as const },
      { id: 'medium', severity: 'medium' as const },
      { id: 'critical', severity: 'critical' as const },
      { id: 'high', severity: 'high' as const },
    ];

    expect(sortRequirementsBySeverity(requirements).map(({ id }) => id)).toEqual([
      'critical',
      'high',
      'medium',
      'low',
    ]);
  });

  it('preserves source data, input order within a severity, and the input array', () => {
    const requirements = [
      { id: 'high-first', description: 'first', severity: 'high' as const },
      { id: 'low', description: 'last', severity: 'low' as const },
      { id: 'high-second', description: 'second', severity: 'high' as const },
    ];
    const original = [...requirements];
    const sorted = sortRequirementsBySeverity(requirements);

    expect(sorted).toEqual([
      requirements[0],
      requirements[2],
      requirements[1],
    ]);
    expect(requirements).toEqual(original);
    expect(sorted[0]).toBe(requirements[0]);
    expect(sorted[1]).toBe(requirements[2]);
  });
});
