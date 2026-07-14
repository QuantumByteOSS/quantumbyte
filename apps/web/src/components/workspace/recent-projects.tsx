import Link from 'next/link';
import { formatRelativeTime } from '@/lib/relative-time';
import { StatusBadge } from './status-badge';
import type { Project } from '@/generated/prisma/client';

function ProjectLogo({ project }: { project: Project }) {
  if (project.logo) {
    return (
      <div className="size-12 shrink-0 overflow-hidden rounded-lg">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={project.logo}
          alt=""
          className="size-full object-cover"
        />
      </div>
    );
  }
  return (
    <div className="flex size-12 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-sm font-bold text-primary">
      {(project.title || 'Untitled').substring(0, 2).toUpperCase()}
    </div>
  );
}

export function RecentProjects({ projects }: { projects: Project[] }) {
  if (projects.length === 0) return null;

  return (
    <div className="mx-auto w-full max-w-5xl overflow-hidden rounded-xl border border-slate-200">
      {/* Desktop table */}
      <table className="hidden w-full md:table">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-100 text-left text-xs text-slate-500">
            <th className="px-4 py-3 font-medium">Project name</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Last modified</th>
          </tr>
        </thead>
        <tbody>
          {projects.map((p) => (
            <tr
              key={p.id}
              className="border-b border-slate-100 last:border-0 hover:bg-slate-50"
            >
              <td className="flex items-center gap-3 px-4 py-3">
                <ProjectLogo project={p} />
                <Link
                  href={`/dashboard/project/blueprint/${p.id}`}
                  className="text-sm font-medium hover:underline"
                >
                  {p.title || 'Untitled'}
                </Link>
              </td>
              <td className="px-4 py-3">
                <StatusBadge
                  status={p.status}
                  generationStatus={p.generationStatus}
                />
              </td>
              <td className="px-4 py-3 text-sm text-slate-500">
                {formatRelativeTime(p.updatedAt)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Mobile cards */}
      <div className="divide-y divide-slate-100 md:hidden">
        {projects.map((p) => (
          <article key={p.id} className="flex items-center gap-3 p-4">
            <ProjectLogo project={p} />
            <div className="min-w-0 flex-1">
              <Link
                href={`/dashboard/project/blueprint/${p.id}`}
                className="block truncate text-sm font-medium hover:underline"
              >
                {p.title || 'Untitled'}
              </Link>
              <p className="text-xs text-slate-500">
                {formatRelativeTime(p.updatedAt)}
              </p>
            </div>
            <StatusBadge
              status={p.status}
              generationStatus={p.generationStatus}
            />
          </article>
        ))}
      </div>
    </div>
  );
}
