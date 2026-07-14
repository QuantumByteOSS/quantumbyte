import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

// Request a real harness run. Sets Project.harnessRunRequested; a worker claims it
// (respecting one-agent-per-project), flips it back, and runs the harness — writing
// live status + verdicts the FE tails over the shared SSE stream (RFC 0003: the
// coordination is the flag on the row, not a broker). Idempotent: re-hitting while a
// run is in flight is a no-op.
export async function POST(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const project = await prisma.project.findUnique({
    where: { id },
    select: { id: true, harnessRunning: true },
  });
  if (!project) {
    return NextResponse.json({ error: 'project not found' }, { status: 404 });
  }

  // Already running → nothing to request; the in-flight run will reflect current state.
  if (!project.harnessRunning) {
    await prisma.project.update({
      where: { id },
      data: { harnessRunRequested: true },
    });
  }

  return NextResponse.json({ status: 'queued' }, { status: 202 });
}
