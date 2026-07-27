export const REQUIREMENT_SEVERITIES = [
  'critical',
  'high',
  'medium',
  'low',
] as const;

export type RequirementSeverity = (typeof REQUIREMENT_SEVERITIES)[number];

const SEVERITY_RANK: Record<RequirementSeverity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

export function sortRequirementsBySeverity<
  T extends { severity: RequirementSeverity },
>(requirements: readonly T[]): T[] {
  return [...requirements].sort(
    (left, right) =>
      SEVERITY_RANK[left.severity] - SEVERITY_RANK[right.severity],
  );
}
