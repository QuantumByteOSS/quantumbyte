import { NextRequest, NextResponse } from 'next/server';
import { ulid } from 'ulid';
import { prisma } from '@/lib/prisma';

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const messages = await prisma.chatMessage.findMany({
    where: { projectId: id },
    orderBy: { createdAt: 'asc' },
  });
  return NextResponse.json({ messages });
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await req.json().catch(() => null);
  const text = typeof body?.text === 'string' ? body.text.trim() : '';
  // Attachments already uploaded via /attachments; here they are just links the
  // agent (and the chat transcript) can follow — appended to the message body so
  // the worker's turn pipeline needs no attachment awareness.
  const attachments: { url: string; filename: string; mimeType?: string }[] =
    Array.isArray(body?.attachments)
      ? body.attachments.filter(
          (a: unknown): a is { url: string; filename: string; mimeType?: string } =>
            typeof a === 'object' &&
            a !== null &&
            typeof (a as { url?: unknown }).url === 'string' &&
            typeof (a as { filename?: unknown }).filename === 'string'
        )
      : [];
  if (!text && attachments.length === 0) {
    return NextResponse.json({ error: 'text is required' }, { status: 400 });
  }

  const attachmentBlock = attachments.length
    ? `\n\nAttachments:\n${attachments
        .map((a) => `- [${a.filename}](${a.url})${a.mimeType ? ` (${a.mimeType})` : ''}`)
        .join('\n')}`
    : '';
  const content = `${text}${attachmentBlock}`.trim();

  const project = await prisma.project.findUnique({ where: { id } });
  if (!project) {
    return NextResponse.json({ error: 'project not found' }, { status: 404 });
  }

  // Persist the user turn as PENDING and stop. The orchestrator assigns it to a
  // worker; the worker (Claude Agent SDK, warm session) runs the turn and writes
  // the ASSISTANT reply + flips this row to COMPLETED/FAILED (RFC 0003). The web
  // app never runs the agent — the client polls the GET endpoint for the result.
  const message = await prisma.chatMessage.create({
    data: {
      id: ulid(),
      projectId: id,
      role: 'USER',
      content,
      status: 'PENDING',
    },
  });

  return NextResponse.json({ message }, { status: 201 });
}
