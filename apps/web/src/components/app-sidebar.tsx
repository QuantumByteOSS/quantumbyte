'use client';

import {
  HouseSimple,
  MagnifyingGlass,
  SidebarSimple,
} from '@phosphor-icons/react';
import Image from 'next/image';
import Link from 'next/link';
import { useEffect, useState } from 'react';

type ProjectItem = {
  id: string;
  title: string | null;
  updatedAt: string;
};

export function AppSidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const handle = setTimeout(async () => {
      try {
        const params = search ? `?search=${encodeURIComponent(search)}` : '';
        const res = await fetch(`/api/projects${params}`);
        const data = await res.json();
        setProjects(data.nodes ?? []);
      } catch {
        setProjects([]);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => clearTimeout(handle);
  }, [search]);

  return (
    <aside
      className={`flex h-screen shrink-0 flex-col border-r border-slate-200 bg-slate-50 transition-[width] duration-200 ${
        collapsed ? 'w-14' : 'w-64'
      }`}
    >
      <div className="flex items-center justify-between gap-2 p-3">
        <Link
          href="/dashboard/project"
          className="flex items-center overflow-hidden"
        >
          {collapsed ? (
            <Image
              src="/logo_qbits_fav.png"
              alt="QuantumByte"
              width={32}
              height={32}
              className="shrink-0"
            />
          ) : (
            <Image
              src="/logo_qbits_color.png"
              alt="QuantumByte"
              width={120}
              height={32}
              className="shrink-0"
            />
          )}
        </Link>
        {!collapsed && (
          <button
            type="button"
            aria-label="Collapse sidebar"
            onClick={() => setCollapsed(true)}
            className="rounded-md p-1 text-slate-500 hover:bg-slate-200"
          >
            <SidebarSimple size={18} />
          </button>
        )}
      </div>

      {collapsed && (
        <button
          type="button"
          aria-label="Expand sidebar"
          onClick={() => setCollapsed(false)}
          className="mx-auto mb-1 rounded-md p-1 text-slate-500 hover:bg-slate-200"
        >
          <SidebarSimple size={18} />
        </button>
      )}

      <nav className="px-2">
        <Link
          href="/dashboard/project"
          className="flex items-center gap-2 rounded-md px-2 py-2 text-sm text-slate-700 hover:bg-slate-200"
        >
          <HouseSimple size={18} className="shrink-0" />
          {!collapsed && <span>Home</span>}
        </Link>
      </nav>

      {!collapsed && (
        <div className="mt-4 flex min-h-0 flex-1 flex-col px-2">
          <div className="flex items-center justify-between px-2 pb-2">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Recent projects
            </span>
            <button
              type="button"
              aria-label={searchOpen ? 'Hide project search' : 'Search projects'}
              onClick={() => {
                if (searchOpen) setSearch('');
                setSearchOpen(!searchOpen);
              }}
              className={`rounded-md p-1 hover:bg-slate-200 ${
                searchOpen ? 'text-primary' : 'text-slate-500'
              }`}
            >
              <MagnifyingGlass size={14} />
            </button>
          </div>
          {searchOpen && (
            <div className="px-2 pb-2">
              <input
                autoFocus
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search projects"
                className="w-full rounded-md border border-slate-200 bg-white px-2 py-1.5 text-sm outline-none placeholder:text-slate-400 focus:border-primary"
              />
            </div>
          )}
          <ul className="min-h-0 flex-1 overflow-y-auto pb-4">
            {loading ? (
              [0, 1, 2].map((i) => (
                <li
                  key={i}
                  className="mx-2 my-1.5 h-7 animate-pulse rounded-md bg-slate-200"
                />
              ))
            ) : projects.length === 0 ? (
              <li className="px-4 py-2 text-sm text-slate-400">
                {search ? 'No match' : 'No projects yet'}
              </li>
            ) : (
              projects.map((p) => (
                <li key={p.id}>
                  <Link
                    href={`/dashboard/project/blueprint/${p.id}`}
                    className="block truncate rounded-md px-4 py-1.5 text-sm text-slate-700 hover:bg-slate-200"
                  >
                    {p.title || 'Untitled'}
                  </Link>
                </li>
              ))
            )}
          </ul>
        </div>
      )}
    </aside>
  );
}
