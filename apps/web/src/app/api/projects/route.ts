import { NextRequest, NextResponse } from 'next/server';
import { ulid } from 'ulid';
import { prisma } from '@/lib/prisma';

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const search = searchParams.get('search')?.trim();
  const limit = Math.min(Number(searchParams.get('limit')) || 16, 100);
  const offset = Number(searchParams.get('offset')) || 0;

  const where = search
    ? { title: { contains: search, mode: 'insensitive' as const } }
    : {};

  const [nodes, totalCount] = await Promise.all([
    prisma.project.findMany({
      where,
      orderBy: { updatedAt: 'desc' },
      take: limit,
      skip: offset,
    }),
    prisma.project.count({ where }),
  ]);

  return NextResponse.json({
    nodes,
    totalCount,
    hasNextPage: offset + nodes.length < totalCount,
  });
}

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => null);
  const prompt = typeof body?.prompt === 'string' ? body.prompt.trim() : '';
  if (!prompt) {
    return NextResponse.json({ error: 'prompt is required' }, { status: 400 });
  }

  const title = prompt.length > 48 ? `${prompt.slice(0, 48)}…` : prompt;
  const project = await prisma.project.create({
    data: {
      id: ulid(),
      prompt,
      title,
      generationStatus: 'DRAFT',
      // Seed the prompt as the first chat turn (PENDING) so the blueprint
      // chat renders it and the orchestrator triggers the agent immediately.
      chatMessages: {
        create: {
          id: ulid(),
          role: 'USER',
          content: prompt,
          status: 'PENDING',
        },
      },
    },
  });

  return NextResponse.json(project, { status: 201 });
}
