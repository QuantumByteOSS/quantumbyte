import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

// App-preview status (task T5). The orchestrator allocates Project.previewPort with
// the affinity pin and the pinned worker serves the generated app there; this route
// is the platform's ping test. It proxies the health check server-side (the web app
// and the worker share localhost for now, and this survives the move to real hosts)
// and reduces it to the three UI states (T6):
//   hidden   — no port allocated (no live affinity): the panel stays hidden
//   starting — port allocated but the app doesn't answer yet (installing/booting)
//   ready    — the app answered: render the iframe at previewUrl
// Any HTTP response counts as ready — a dev server's compile-error page is still
// the most useful thing to show in the preview.

const PING_TIMEOUT_MS = 1500;

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const project = await prisma.project.findUnique({
    where: { id },
    select: { previewPort: true },
  });
  if (!project) {
    return NextResponse.json({ error: 'project not found' }, { status: 404 });
  }

  const port = project.previewPort;
  if (port === null) {
    return NextResponse.json({ state: 'hidden', port: null, previewUrl: null });
  }

  const previewUrl = `http://localhost:${port}/`;
  try {
    await fetch(`http://127.0.0.1:${port}/`, {
      method: 'GET',
      signal: AbortSignal.timeout(PING_TIMEOUT_MS),
      cache: 'no-store',
    });
    return NextResponse.json({ state: 'ready', port, previewUrl });
  } catch {
    return NextResponse.json({ state: 'starting', port, previewUrl });
  }
}
