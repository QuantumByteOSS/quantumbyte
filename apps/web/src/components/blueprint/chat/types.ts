/**
 * Chat message model — ported/adapted from the portal's ChatAgent `_types`.
 *
 * The portal's `Message` is richer than what this open-source slice's backend
 * currently produces (roles user/assistant only, no subagent/admin/tool data
 * yet). We keep the full shape so the ported bubbles render unchanged, and map
 * the current API rows onto it in `map-message.ts`. Fields with no backend yet
 * (subagent_name, admin_name, message_type, attachments/options…) stay optional
 * and are fed static/mock data until wired.
 */

export type AgentType = 'PARTNER' | 'DESIGNER' | 'STRATEGIST' | 'ENGINEER';

export type MessageType =
  | 'message'
  | 'status'
  | 'quick_ack'
  | 'error'
  | 'voice'
  | 'blueprint_edit'
  | 'entity_edit'
  | 'page_edit'
  | 'api_edit'
  | 'harness_fix';

export type MessageRole = 'user' | 'assistant' | 'system' | 'tool' | 'admin';

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  agent_type?: AgentType;
  message_type?: MessageType;
  timestamp: Date | string;
  /** Name of the subagent that generated this message. */
  subagent_name?: string;
  /** ID of the tool call that invoked this subagent. */
  parent_tool_use_id?: string;
  tool_name?: string;
  tool_input?: unknown;
  /** Display name of the staff member, when role === "admin". */
  admin_name?: string | null;
  /** Whether this message is still streaming in (assistant, PROCESSING). */
  streaming?: boolean;
  /** Streamed extended-thinking / reasoning text (assistant), rendered as a
   * collapsible bubble. Fills live during a turn, ahead of `content`. */
  thinking?: string;
  /** Live status line while streaming: the agent's current tool activity
   * ("Editing page.tsx") or the pipeline stage ("Saving your app to GitHub…"). */
  activity?: string;
  /** The turn's full activity timeline (step texts, oldest first). Rendered as
   * the live "working…" step feed while streaming, and a collapsed recap after. */
  activitySteps?: string[];
}

/** Raw row shape returned by GET /api/projects/[id]/chat. */
export interface ChatRow {
  id: string;
  role: 'USER' | 'ASSISTANT';
  content: string;
  thinking: string | null;
  /** Pipeline stage while PROCESSING (USER rows): AGENT / RECONCILING / COMMITTING. */
  stage: string | null;
  /** Current tool activity while streaming (ASSISTANT rows). */
  activity: string | null;
  /** Activity timeline: [{at, text}, …] — `activity` is always the last entry. */
  activityLog: { at: string; text: string }[] | null;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  error: string | null;
  createdAt: string;
}
