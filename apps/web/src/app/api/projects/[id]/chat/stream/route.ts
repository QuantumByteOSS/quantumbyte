import { NextRequest } from 'next/server';
import { prisma } from '@/lib/prisma';
import { serializeRequirement, serializeResult } from '@/lib/harness';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const POLL_MS = 400;
const MAX_DURATION_MS = 5 * 60 * 1000; // safety cap on a single SSE connection
const KEEPALIVE_MS = 15_000;

/**
 * Server-Sent Events stream of a project's chat messages.
 *
 * The Next app never runs the agent (an external Python worker does), so this
 * route tails the DB: every ~400ms it re-reads the messages and pushes a
 * snapshot whenever anything changed — which happens as the worker appends
 * streaming deltas to the in-flight ASSISTANT row. Delivers near-real-time
 * token streaming without a broker, reusing Postgres as the channel (RFC 0003).
 *
 * The stream self-closes once no turn is in flight (nothing PENDING/PROCESSING).
 */
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      let closed = false;
      const startedAt = Date.now();
      let lastSnapshot = '';
      let lastKeepalive = Date.now();

      const send = (data: string) => {
        controller.enqueue(encoder.encode(`data: ${data}\n\n`));
      };

      const tick = async (): Promise<boolean> => {
        // Also tail the Project (title/desc/logo) + its assets so product edits
        // made by the worker's qb-designer tools surface live — the worker bumps
        // Project.updatedAt / inserts Asset rows, and this snapshot picks it up.
        // Also tail the harness tables + harnessRunning flag so pass-3 verdicts and
        // the running indicator stream over this same connection (browsers cap ~6
        // per origin, so the harness UI shares the chat stream instead of opening
        // its own). The worker runs the harness right after the turn settles, so
        // the in-flight condition below also keys off harnessRunning to keep this
        // connection open across that hand-off.
        const [messages, project, assets, requirements] = await Promise.all([
          prisma.chatMessage.findMany({
            where: { projectId: id },
            orderBy: { createdAt: 'asc' },
          }),
          prisma.project.findUnique({
            where: { id },
            select: {
              title: true,
              desc: true,
              logo: true,
              status: true,
              updatedAt: true,
              harnessRunning: true,
            },
          }),
          prisma.asset.findMany({
            where: { projectId: id },
            orderBy: { createdAt: 'asc' },
          }),
          prisma.harnessRequirement.findMany({
            where: { projectId: id },
            include: { result: true },
            orderBy: { createdAt: 'asc' },
          }),
        ]);
        const harness = {
          requirements: requirements.map(serializeRequirement),
          results: requirements
            .map((r) => r.result)
            .filter((r) => r !== null)
            .map(serializeResult),
          is_running: project?.harnessRunning ?? false,
        };
        const payload = { messages, project, assets, harness };
        const snapshot = JSON.stringify(payload);
        if (snapshot !== lastSnapshot) {
          lastSnapshot = snapshot;
          send(snapshot);
          lastKeepalive = Date.now();
        } else if (Date.now() - lastKeepalive > KEEPALIVE_MS) {
          controller.enqueue(encoder.encode(': keepalive\n\n'));
          lastKeepalive = Date.now();
        }

        const inFlight =
          messages.some((m) => m.status === 'PENDING' || m.status === 'PROCESSING') ||
          (project?.harnessRunning ?? false);
        return inFlight;
      };

      try {
        // Always emit the current state immediately on connect.
        await tick();

        while (!closed) {
          if (Date.now() - startedAt > MAX_DURATION_MS) break;
          await new Promise((r) => setTimeout(r, POLL_MS));
          if (closed) break;
          const inFlight = await tick();
          // Keep the connection open a little after the turn settles so the
          // final COMPLETED snapshot is guaranteed to have been delivered.
          if (!inFlight) break;
        }
      } catch {
        // swallow — client likely disconnected
      } finally {
        if (!closed) {
          closed = true;
          try {
            controller.close();
          } catch {
            /* already closed */
          }
        }
      }
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
}
