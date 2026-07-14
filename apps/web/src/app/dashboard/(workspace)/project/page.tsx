import { PromptBox } from '@/components/workspace/prompt-box';
import { RecentProjects } from '@/components/workspace/recent-projects';
import { prisma } from '@/lib/prisma';
import type { Project } from '@/generated/prisma/client';

export const dynamic = 'force-dynamic';

export default async function ProjectWorkspacePage() {
  let projects: Project[] = [];
  try {
    projects = await prisma.project.findMany({
      orderBy: { updatedAt: 'desc' },
      take: 3,
    });
  } catch {
    // Database unreachable — render the empty workspace rather than crash.
  }
  const hasProjects = projects.length > 0;

  return (
    <section className="mx-auto flex w-full max-w-4xl flex-col gap-5 px-4 py-4 md:max-w-6xl md:gap-8 md:py-24">
      <p className="text-center text-xl text-slate-900 md:text-3xl">
        {hasProjects
          ? 'Welcome back. What are we building next?'
          : 'What should we build today?'}
      </p>

      <RecentProjects projects={projects} />

      <PromptBox hasProjects={hasProjects} />
    </section>
  );
}
