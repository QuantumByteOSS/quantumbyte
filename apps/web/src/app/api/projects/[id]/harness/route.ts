import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { serializeRequirement, serializeResult } from '@/lib/harness';

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const project = await prisma.project.findUnique({
    where: { id },
    include: { requirements: { include: { result: true }, orderBy: { createdAt: 'asc' } } },
  });
  if (!project) {
    return NextResponse.json({ error: 'project not found' }, { status: 404 });
  }

  return NextResponse.json({
    requirements: project.requirements.map(serializeRequirement),
    results: project.requirements
      .map((r) => r.result)
      .filter((r) => r !== null)
      .map(serializeResult),
    is_running: project.harnessRunning,
  });
}
