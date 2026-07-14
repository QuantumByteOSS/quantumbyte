import type { AgentType, Message } from './types';

/**
 * Per-agent avatar disc colors — ported verbatim from the portal's
 * `SubagentMessageBubble` (`AGENT_THEME`). Full literal class strings so the
 * Tailwind v4 JIT keeps them.
 */
export const AGENT_THEME: Record<AgentType, { disc: string }> = {
  PARTNER: { disc: 'bg-[#85A8FF]' },
  ENGINEER: { disc: 'bg-[#A9F3FA]' },
  DESIGNER: { disc: 'bg-[#A175E4]' },
  STRATEGIST: { disc: 'bg-[#4D4D4D]' },
};

/** `/bears/qbear-${type}-base.png` — the in-bubble bot avatar. */
export function bearSrc(type: AgentType): string {
  return `/bears/qbear-${type.toLowerCase()}-base.png`;
}

/** Resolve the agent type for a message (ported from `agentTypeFromMessage`). */
export function agentTypeFromMessage(message: Message): AgentType {
  const name = (message.subagent_name ?? '').toLowerCase();
  if (name.includes('strategist')) return 'STRATEGIST';
  if (name.includes('engineer')) return 'ENGINEER';
  if (name.includes('design')) return 'DESIGNER';
  if (name.includes('partner')) return 'PARTNER';
  return message.agent_type ?? 'PARTNER';
}
