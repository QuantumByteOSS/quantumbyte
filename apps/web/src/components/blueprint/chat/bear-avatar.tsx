import { cn } from '@/lib/utils';
import { AGENT_THEME, bearSrc } from './agent-theme';
import type { AgentType } from './types';

/**
 * The in-bubble bot avatar: a bear PNG inside a colored disc.
 * Ported verbatim (markup + classes) from the portal's `BearAvatar` /
 * `AgentAvatarColumn`.
 */
export function BearAvatar({
  agentType,
  className,
}: {
  agentType: AgentType;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'relative flex size-[25px] shrink-0 items-center justify-center overflow-hidden rounded-full ring-1 ring-black/10',
        AGENT_THEME[agentType].disc,
        className
      )}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={bearSrc(agentType)}
        alt=""
        aria-hidden="true"
        draggable={false}
        className="size-[150%] max-h-none max-w-none translate-y-2"
      />
    </div>
  );
}

/** Avatar column wrapper used to the left of assistant/subagent bubbles. */
export function AgentAvatarColumn({ agentType }: { agentType: AgentType }) {
  return (
    <div
      aria-hidden="true"
      className="flex shrink-0 flex-col items-center"
    >
      <BearAvatar agentType={agentType} />
    </div>
  );
}
