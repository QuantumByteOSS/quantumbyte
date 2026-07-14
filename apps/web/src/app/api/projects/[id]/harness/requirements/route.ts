import { NextRequest, NextResponse } from 'next/server';
import { ulid } from 'ulid';
import { prisma } from '@/lib/prisma';
import { serializeRequirement } from '@/lib/harness';
import type {
  RequirementType,
  Severity,
} from '@/generated/prisma/client';

const TYPES = new Set(['explicit', 'hidden']);
const SEVERITIES = new Set(['critical', 'high', 'medium', 'low']);

type IncomingRequirement = {
  id?: string;
  excerpt?: string | null;
  description?: string;
  type?: string;
  severity?: string;
  // Whether this row is under manual user ownership. The client sets it true for
  // rows the user added or edited and preserves the prior value for untouched rows
  // (the PUT payload is the full set, so an absent flag must not silently unlock a
  // row). Absent → default false only on create.
  locked?: boolean;
};

// Full-replace semantics, mirroring the platform contract:
// the payload is the complete desired requirement set; anything
// missing is deleted, empty/absent id means create.
export async function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const project = await prisma.project.findUnique({ where: { id } });
  if (!project) {
    return NextResponse.json({ error: 'project not found' }, { status: 404 });
  }

  const body = await req.json().catch(() => null);
  const incoming: IncomingRequirement[] = Array.isArray(body?.requirements)
    ? body.requirements
    : [];

  for (const r of incoming) {
    if (!r.description?.trim()) {
      return NextResponse.json(
        { error: 'every requirement needs a description' },
        { status: 400 }
      );
    }
    if (r.type && !TYPES.has(r.type)) {
      return NextResponse.json({ error: `invalid type: ${r.type}` }, { status: 400 });
    }
    if (r.severity && !SEVERITIES.has(r.severity)) {
      return NextResponse.json(
        { error: `invalid severity: ${r.severity}` },
        { status: 400 }
      );
    }
  }

  const keptIds = incoming.filter((r) => r.id).map((r) => r.id as string);

  const requirements = await prisma.$transaction(async (tx) => {
    await tx.harnessRequirement.deleteMany({
      where: { projectId: id, id: { notIn: keptIds } },
    });
    return Promise.all(
      incoming.map((r) => {
        const data = {
          excerpt: r.excerpt?.trim() || null,
          description: (r.description as string).trim(),
          type: (r.type?.toUpperCase() ?? 'EXPLICIT') as RequirementType,
          severity: (r.severity?.toUpperCase() ?? 'MEDIUM') as Severity,
        };
        // A create always claims manual ownership (the user typed it). An update
        // only changes lock state when the client explicitly sends one — true for an
        // edited row, false for a reset-to-auto; an omitted flag leaves the stored
        // value untouched, so a partial payload can never mass-lock the whole set.
        const lockedProvided = typeof r.locked === 'boolean';
        return r.id
          ? tx.harnessRequirement.update({
              where: { id: r.id },
              data: { ...data, ...(lockedProvided ? { locked: r.locked } : {}) },
            })
          : tx.harnessRequirement.create({
              data: { id: ulid(), projectId: id, ...data, locked: r.locked ?? true },
            });
      })
    );
  });

  return NextResponse.json({
    requirements: requirements.map(serializeRequirement),
  });
}
