import { notFound } from 'next/navigation';
import { BlueprintLayout } from '@/components/blueprint/blueprint-layout';
import { prisma } from '@/lib/prisma';

export const dynamic = 'force-dynamic';

export default async function BlueprintPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const project = await prisma.project.findUnique({ where: { id: projectId } });
  if (!project) notFound();

  return (
    <BlueprintLayout
      projectId={project.id}
      title={project.title || 'Untitled'}
      updatedAt={project.updatedAt.toISOString()}
    />
  );
}
